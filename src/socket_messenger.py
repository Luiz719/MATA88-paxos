import json
import socket
import threading
import logging
from typing import Any, Dict
from src.messenger import HeartbeatMessenger, Messenger

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SocketMessenger(Messenger):
    """
    The `SocketMessenger` class implements a messaging system using sockets for communication between
    nodes, supporting message broadcasting and various message types for a distributed system.
    """
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
        """
        The `_listen` function continuously receives messages from a socket, decodes them as JSON, logs
        the message and sender, and then notifies all listeners with the message.
        """
        while True:
            data, addr = self.socket.recvfrom(4096)
            message = json.loads(data.decode())
            logging.debug(f"Received message: {message} from {addr}")
            for listener in self.listeners:
                listener(message)

    def add_listener(self, listener):
        """
        The function `add_listener` appends a listener to a list of listeners.
        
        :param listener: The `listener` to be added
        """
        self.listeners.append(listener)

    def _send(self, to_node: str, message: Dict[str, Any]):
        """
        The function `_send` sends a message to a specified node with the sender's node ID included in
        the message.
        
        :param to_node: The `to_node` parameter in the `_send` method is a string that represents the
        destination node to which the message will be sent. It is the identifier of the node that will
        receive the message
        :type to_node: str
        :param message: The `message` parameter is a dictionary containing information to
        be sent to the destination node
        :type message: Dict[str, Any]
        """

        message['from'] = self.node_id
        logging.debug(f"Sending message: {message} to {to_node} at {self.nodes[to_node]}")
        self.socket.sendto(json.dumps(message).encode(), self.nodes[to_node])

    def broadcast(self, message: Dict[str, Any]):
        """
        The `broadcast` function sends a message to all nodes except for the current node.
        
        :param message: The message to be broadcasted.
        :type message: Dict[str, Any]
        """

        logging.debug(f"Broadcasting message: {message} to all nodes except {self.node_name}")
        for node in self.nodes:
            if node != self.node_name:
                self._send(node, message)

    def send_prepare(self, proposal_id):
        """
        The function `send_prepare` constructs and broadcasts a prepare message with a given proposal
        ID.
        
        :param proposal_id: The `proposal_id` parameter is a `ProposalID` namedtuple
        """
        message = {
            'type': 'prepare',
            'proposal_id': proposal_id._asdict()
        }
        logging.debug(f"Sending prepare message: {message}")
        self.broadcast(message)

    def send_promise(self, proposer_uid, proposal_id, previous_id, accepted_value):
        """
        The function `send_promise` sends a promise message with specific details to a proposer
        identified by `proposer_uid`.
        
        :param proposer_uid: The `proposer_uid` parameter in the `send_promise` method is the unique
        identifier of the proposer to whom the promise message will be sent. It is used to specify the
        recipient of the message
        :param proposal_id: The `proposal_id` parameter is the identifier of the new proposal to be sent
        :param previous_id: The `previous_id` parameter in the `send_promise` method is a unique
        identifier for the previous proposal.
        :param accepted_value: The `accepted_value` parameter in the `send_promise` method represents
        the value that has been accepted by the proposers.
        """
        message = {
            'type': 'promise',
            'proposal_id': proposal_id._asdict(),
            'previous_id': previous_id._asdict() if previous_id else None,
            'accepted_value': accepted_value
        }
        logging.debug(f"Sending promise message: {message} to {proposer_uid}")
        self._send(proposer_uid, message)

    def send_accept(self, proposal_id, proposal_value):
        """
        The function `send_accept` sends an accept message with a proposal ID and value to the acceptors.
        
        :param proposal_id: The id of the accepted proposal
        :param proposal_value: The value of the accepted proposal
        """
        message = {
            'type': 'accept',
            'proposal_id': proposal_id._asdict(),
            'value': proposal_value
        }
        logging.debug(f"Sending accept message: {message}")
        self.broadcast(message)

    def send_accepted(self, proposal_id, accepted_value):
        """
        The function `send_accepted` sends an accepted message with the proposal ID and accepted value
        to all learners.
        
        :param proposal_id: The id of the accepted proposal
        :param proposal_value: The value of the accepted proposal
        """
        message = {
            'type': 'accepted',
            'proposal_id': proposal_id._asdict(),
            'value': accepted_value
        }
        logging.debug(f"Sending accepted message: {message}")
        self.broadcast(message)

    def send_prepare_nack(self, to_uid, proposal_id, promised_id):
        """
        The function `send_prepare_nack` sends a prepare_nack message with proposal_id and promised_id
        to a specified proposer.
        
        :param to_uid: The `to_uid` parameter is the uid of the proposer
        :param proposal_id: The identifier of proposal.
        :param promised_id: The identifier of promise.
        """
        message = {
            'type': 'prepare_nack',
            'proposal_id': proposal_id._asdict(),
            'promised_id': promised_id._asdict()
        }
        logging.debug(f"Sending prepare_nack message: {message} to {to_uid}")
        self._send(to_uid, message)

    def send_accept_nack(self, to_uid, proposal_id, promised_id):
        """
        This function sends an accept_nack message to a specified user with the given proposal and
        promised IDs.
        
        :param to_uid: The `to_uid` parameter is the uid of the proposer
        :param proposal_id: The identifier of proposal.
        :param promised_id: The identifier of promise.
        """
        message = {
            'type': 'accept_nack',
            'proposal_id': proposal_id._asdict(),
            'promised_id': promised_id._asdict()
        }
        logging.debug(f"Sending accept_nack message: {message} to {to_uid}")
        self._send(to_uid, message)

    def on_resolution(self, proposal_id, value):
        """
        This function logs a message indicating that a resolution has been reached for a specific
        proposal with its ID and value.
        
        :param proposal_id: The `proposal_id` parameter is used to identify a specific proposal or
        decision being made within the context of the function `on_resolution`.
        :param value: The `value` parameter in the `on_resolution` method represents the outcome or
        decision that was reached for a specific proposal.
        """
        logging.info(f"Resolution reached: Proposal {proposal_id} with value {value}")

    def on_leadership_acquired(self):
        """
        The function logs a message indicating that a node has acquired leadership.
        """
        logging.info(f"Node {self.node_id} has acquired leadership")


class SocketHeartbeatMessenger(SocketMessenger, HeartbeatMessenger):
    '''
    This class `SocketHeartbeatMessenger` extends `SocketMessenger` and `HeartbeatMessenger`,
    implementing methods for sending heartbeats, scheduling tasks, and handling leadership changes.
    '''
    def __init__(self, node_id: str, nodes: Dict[str, tuple], node_name, heartbeat_interval: float = 1.0):
        super().__init__(node_id, nodes, node_name)
        self.heartbeat_interval = heartbeat_interval
        self.leader_uid = None
        self.scheduled_tasks = {}

    def send_heartbeat(self, leader_proposal_id):
        """
        The function `send_heartbeat` sends a heartbeat message with the leader's proposal ID to all
        nodes in the network.
        
        :param leader_proposal_id: The leader proposal identifier
        """
        message = {
            'type': 'heartbeat',
            'proposal_id': leader_proposal_id._asdict()
        }
        logging.debug(f"Sending heartbeat message: {message}")
        self.broadcast(message)

    def schedule(self, msec_delay, func_obj):
        """
        The `schedule` function schedules a task to be executed after a specified delay in milliseconds
        using threading in Python.
        
        :param msec_delay: Represents the delay in
        milliseconds before the `func_obj` function object is executed. It is used to schedule a task to
        run after a specified delay
        :param func_obj: The function object that
        you want to schedule for execution after a specified delay in milliseconds. This function object
        will be called after the specified delay when the scheduled task is triggered
        """
        task = threading.Timer(msec_delay / 1000, func_obj)
        task.start()
        logging.debug(f"Scheduled task {func_obj} with a delay of {msec_delay}ms")
        self.scheduled_tasks[func_obj] = task

    def cancel_scheduled_task(self, func_obj):
        """
        The function `cancel_scheduled_task` cancels a scheduled task associated with a given function
        object.
        
        :param func_obj: The function object representing the scheduled task that you want to cancel.
        """
        if func_obj in self.scheduled_tasks:
            logging.debug(f"Cancelling scheduled task {func_obj}")
            self.scheduled_tasks[func_obj].cancel()
            del self.scheduled_tasks[func_obj]

    def on_leadership_lost(self):
        """
        Logs a warning message when a node loses leadership and cancels a scheduled
        task.
        """
        logging.warning(f"Node {self.node_id} has lost leadership")
        self.cancel_scheduled_task(self.node.pulse)

    def on_leadership_change(self, prev_leader_uid, new_leader_uid):
        """
        The function `on_leadership_change` logs the change in leadership from the previous leader to
        the new leader and updates the `leader_uid` attribute accordingly.
        
        :param prev_leader_uid: The uid of previous leader
        :param new_leader_uid: The uid of new leader
        """
        logging.info(f"Leadership changed from {prev_leader_uid} to {new_leader_uid}")
        self.leader_uid = new_leader_uid
