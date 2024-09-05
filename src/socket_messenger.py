import json
import socket
import threading
import logging
from typing import Any, Dict
from src.messenger import HeartbeatMessenger, Messenger

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SocketMessenger(Messenger):
    def __init__(self, node_id: str, nodes: Dict[str, tuple], node_name):
        self.node_id = node_id.uid
        self.node_name = node_name
        self.nodes = nodes
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(self.nodes[self.node_name])
        self.listeners = []

    def start(self):
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        while True:
            data, addr = self.socket.recvfrom(4096)
            message = json.loads(data.decode())
            logging.debug(f"Received message: {message} from {addr}")
            for listener in self.listeners:
                listener(message)

    def add_listener(self, listener):
        self.listeners.append(listener)

    def _send(self, to_node: str, message: Dict[str, Any]):
        message['from'] = self.node_id
        logging.debug(f"Sending message: {message} to {to_node} at {self.nodes[to_node]}")
        self.socket.sendto(json.dumps(message).encode(), self.nodes[to_node])

    def broadcast(self, message: Dict[str, Any]):
        logging.debug(f"Broadcasting message: {message} to all nodes except {self.node_name}")
        for node in self.nodes:
            if node != self.node_name:
                self._send(node, message)

    def send_prepare(self, proposal_id):
        message = {
            'type': 'prepare',
            'proposal_id': proposal_id._asdict()
        }
        logging.debug(f"Sending prepare message: {message}")
        self.broadcast(message)

    def send_promise(self, proposer_uid, proposal_id, previous_id, accepted_value):
        message = {
            'type': 'promise',
            'proposal_id': proposal_id._asdict(),
            'previous_id': previous_id._asdict() if previous_id else None,
            'accepted_value': accepted_value
        }
        logging.debug(f"Sending promise message: {message} to {proposer_uid}")
        self._send(proposer_uid, message)

    def send_accept(self, proposal_id, proposal_value):
        message = {
            'type': 'accept',
            'proposal_id': proposal_id._asdict(),
            'value': proposal_value
        }
        logging.debug(f"Sending accept message: {message}")
        self.broadcast(message)

    def send_accepted(self, proposal_id, accepted_value):
        message = {
            'type': 'accepted',
            'proposal_id': proposal_id._asdict(),
            'value': accepted_value
        }
        logging.debug(f"Sending accepted message: {message}")
        self.broadcast(message)

    def send_prepare_nack(self, to_uid, proposal_id, promised_id):
        message = {
            'type': 'prepare_nack',
            'proposal_id': proposal_id._asdict(),
            'promised_id': promised_id._asdict()
        }
        logging.debug(f"Sending prepare_nack message: {message} to {to_uid}")
        self._send(to_uid, message)

    def send_accept_nack(self, to_uid, proposal_id, promised_id):
        message = {
            'type': 'accept_nack',
            'proposal_id': proposal_id._asdict(),
            'promised_id': promised_id._asdict()
        }
        logging.debug(f"Sending accept_nack message: {message} to {to_uid}")
        self._send(to_uid, message)

    def on_resolution(self, proposal_id, value):
        logging.info(f"Resolution reached: Proposal {proposal_id} with value {value}")

    def on_leadership_acquired(self):
        logging.info(f"Node {self.node_id} has acquired leadership")


class SocketHeartbeatMessenger(SocketMessenger, HeartbeatMessenger):
    def __init__(self, node_id: str, nodes: Dict[str, tuple], node_name, heartbeat_interval: float = 1.0):
        super().__init__(node_id, nodes, node_name)
        self.heartbeat_interval = heartbeat_interval
        self.leader_uid = None
        self.scheduled_tasks = {}

    def send_heartbeat(self, leader_proposal_id):
        message = {
            'type': 'heartbeat',
            'proposal_id': leader_proposal_id._asdict()
        }
        logging.debug(f"Sending heartbeat message: {message}")
        self.broadcast(message)

    def schedule(self, msec_delay, func_obj):
        task = threading.Timer(msec_delay / 1000, func_obj)
        task.start()
        logging.debug(f"Scheduled task {func_obj} with a delay of {msec_delay}ms")
        self.scheduled_tasks[func_obj] = task

    def cancel_scheduled_task(self, func_obj):
        if func_obj in self.scheduled_tasks:
            logging.debug(f"Cancelling scheduled task {func_obj}")
            self.scheduled_tasks[func_obj].cancel()
            del self.scheduled_tasks[func_obj]

    def on_leadership_lost(self):
        logging.warning(f"Node {self.node_id} has lost leadership")
        self.cancel_scheduled_task(self.node.pulse)

    def on_leadership_change(self, prev_leader_uid, new_leader_uid):
        logging.info(f"Leadership changed from {prev_leader_uid} to {new_leader_uid}")
        self.leader_uid = new_leader_uid
