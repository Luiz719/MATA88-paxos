from typing import Dict
import uuid

from src.proposal import ProposalID
from src.socket_messenger import SocketHeartbeatMessenger
from src.socket_node import PaxosNode


def run_node(node_id: tuple, nodes: Dict[str, tuple], quorum_size: int, node_name: str):
    messenger = SocketHeartbeatMessenger(node_id, nodes, node_name)
    node = PaxosNode(messenger, node_id.uid, quorum_size)
    messenger.node = node
    messenger.start()

    while True:
        command = input(f"Node {node_id.uid}> ").strip().lower()
        if command == "propose":
            value = input("Enter value to propose: ")
            node.set_proposal(value)
        elif command == "prepare":
            node.prepare()
        elif command == "acquire":
            node.acquire_leadership()
        elif command == "quit":
            break
        else:
            print("Unknown command. Available commands: propose, prepare, acquire, quit")


def generate_uid():
    return str(uuid.uuid4())


if __name__ == "__main__":

    nodes = {
        "A": ("localhost", 5000),
        "B": ("localhost", 5001),
        "C": ("localhost", 5002),
    }
    quorum_size = 2

    node_id = input("Enter node ID (A, B, or C): ").strip().upper()
    if node_id not in nodes:
        print("Invalid node ID")
    else:
        proposal_id = ProposalID(1, node_id)
        run_node(proposal_id, nodes, quorum_size, node_id)