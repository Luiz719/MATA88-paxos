import argparse
import os
import time
import random
import multiprocessing
from typing import Dict

from src.proposal import ProposalID
from src.socket_messenger import SocketHeartbeatMessenger
from src.socket_node import PaxosNode

def read_values():
    filename = os.path.join('src', 'shared_values.txt')
    if not os.path.exists(filename):
        print(f"{filename} do not exists")
        return
    with open(filename, 'r') as f:
        proposed_values = f.read().splitlines()
    return proposed_values

def read_commands_from_file(command_file='commands.txt'):
    """Read and parse commands from a command file."""
    command_file = os.path.join('src', command_file)
    node_commands = {}
    if not os.path.exists(command_file):
        print(f"{command_file} do not exists")
        return
    with open(command_file, 'r') as f:
        lines = f.read().splitlines()

    for line in lines:
        node_name, command = line.split(":")
        node_name = node_name.strip().upper()
        command = command.strip().lower()
        if node_name not in node_commands:
            node_commands[node_name] = []
        node_commands[node_name].append(command)
    return node_commands


def run_node(node_id: tuple, nodes: Dict[str, tuple], quorum_size: int, node_name: str, is_leader: bool, node_commands: list):
    messenger = SocketHeartbeatMessenger(node_id, nodes, node_name)
    node = PaxosNode(messenger, node_id.uid, quorum_size)
    messenger.node = node
    messenger.start()

    proposed_values = read_values()
    commands = node_commands

    if(not is_leader and not commands): 
        while True:
            pass
    
    i = 0
    time.sleep(5)
    while True:
        if i < len(commands):
            command = commands[i]
            i += 1
        if command == "propose":
            value = random.choice(proposed_values)  # Randomly select a value to propose
            print(f"Node {node_id.uid} proposes value: {value}")
            node.set_proposal(value)
        elif command == "prepare":
            node.prepare()
        elif command == "acquire":
            print(f"Node {node_id.uid} is trying to acquire leadership.")
            node.acquire_leadership()
        elif command == "quit":
            break
        else:
            time.sleep(5) #wait

        if i == len(commands):
            command = "quit"
            time.sleep(10)

        time.sleep(5)  

def start_nodes(node_count: int):
    nodes = {chr(65 + i): ("localhost", 5000 + i) for i in range(node_count)}
    quorum_size = node_count // 2 + 1

    print(f"Creating {node_count} nodes...")

    # Read the list of commands for each node from the provided file
    node_commands = read_commands_from_file()

    # Create a process for each node
    processes = []
    for i in range(node_count):
        node_name = chr(65 + i)
        proposal_id = ProposalID(1, node_name)
        is_leader = i == 0
        commands_for_node = node_commands.get(node_name, [])  # Get commands for the current node
        process = multiprocessing.Process(target=run_node, args=(proposal_id, nodes, quorum_size, node_name, is_leader, commands_for_node))
        processes.append(process)
        process.start()

    # Wait for all processes to finish
    for process in processes:
        process.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Running Paxos nodes.")
    parser.add_argument('--node_count', type=int, default=3, help="Number of nodes to create.")
 
    args = parser.parse_args()

    node_count = args.node_count

    if node_count < 3:
        node_count = 3
    if node_count > 26:
        node_count = 26
    start_nodes(node_count)
