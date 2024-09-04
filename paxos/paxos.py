import collections
from time import time
import uuid


ProposalID = collections.namedtuple('ProposalID', ['number', 'uid'])


class Messenger (object):
    def send_prepare(self, proposal_id):
        '''
        Broadcasts a Prepare message to all Acceptors
        '''

    def send_promise(self, proposer_uid, proposal_id, previous_id, accepted_value):
        '''
        Sends a Promise message to the specified Proposer
        '''

    def send_accept(self, proposal_id, proposal_value):
        '''
        Broadcasts an Accept! message to all Acceptors
        '''

    def send_accepted(self, proposal_id, accepted_value):
        '''
        Broadcasts an Accepted message to all Learners
        '''

    def on_resolution(self, proposal_id, value):
        '''
        Called when a resolution is reached
        '''

    def send_prepare_nack(self, to_uid, proposal_id, promised_id):
        '''
        Sends a Prepare Nack message for the proposal to the specified node
        '''

    def send_accept_nack(self, to_uid, proposal_id, promised_id):
        '''
        Sends a Accept! Nack message for the proposal to the specified node
        '''

    def on_leadership_acquired(self):
        '''
        Called when leadership has been acquired. This is not a guaranteed
        position. Another node may assume leadership at any time and it's
        even possible that another may have successfully done so before this
        callback is executed. Use this method with care.

        The safe way to guarantee leadership is to use a full Paxos instance
        with the resolution value being the UID of the leader node. To avoid
        potential issues arising from timing and/or failure, the election
        result may be restricted to a certain time window. Prior to the end of
        the window the leader may attempt to re-elect itself to extend its
        term in office.
        '''

    
class Proposer (object):

    messenger            = None
    proposer_uid         = None
    quorum_size          = None

    proposed_value       = None
    proposal_id          = ProposalID(0, 'a') 
    last_accepted_id     = ProposalID(0, 'a') 
    next_proposal_number = 1
    promises_rcvd        = None

    
    leader = False 
    active = True  

    
    def set_proposal(self, value):
        '''
        Sets the proposal value for this node iff this node is not already aware of
        another proposal having already been accepted. 
        '''
        if self.proposed_value is None:
            self.proposed_value = value

            if self.leader and self.active:
                self.messenger.send_accept( self.proposal_id, value )


    def prepare(self, increment_proposal_number=True):
        '''
        Sends a prepare request to all Acceptors as the first step in
        attempting to acquire leadership of the Paxos instance. If the
        'increment_proposal_number' argument is True (the default), the
        proposal id will be set higher than that of any previous observed
        proposal id. Otherwise the previously used proposal id will simply be
        retransmitted.
        '''
        if increment_proposal_number:
            self.leader        = False
            self.promises_rcvd = set()
            self.proposal_id   = ProposalID(self.next_proposal_number, self.proposer_uid)        
            self.next_proposal_number += 1

        if self.active:
            self.messenger.send_prepare(self.proposal_id)

    
    def observe_proposal(self, from_uid, proposal_id):
        '''
        Optional method used to update the proposal counter as proposals are
        seen on the network.  When co-located with Acceptors and/or Learners,
        this method may be used to avoid a message delay when attempting to
        assume leadership (guaranteed NACK if the proposal number is too low).
        '''
        if from_uid != self.proposer_uid:
            if proposal_id >= (self.next_proposal_number, self.proposer_uid):
                self.next_proposal_number = proposal_id.number + 1

            
    def recv_prepare_nack(self, from_uid, proposal_id, promised_id):
        '''
        Called when an explicit NACK is sent in response to a prepare message.
        '''
        self.observe_proposal( from_uid, promised_id )

    
    def recv_accept_nack(self, from_uid, proposal_id, promised_id):
        '''
        Called when an explicit NACK is sent in response to an accept message
        '''
        
    def resend_accept(self):
        '''
        Retransmits an Accept! message iff this node is the leader and has
        a proposal value
        '''
        if self.leader and self.proposed_value and self.active:
            self.messenger.send_accept(self.proposal_id, self.proposed_value)


    def recv_promise(self, from_uid, proposal_id, prev_accepted_id, prev_accepted_value):
        '''
        Called when a Promise message is received from the network
        '''
        self.observe_proposal( from_uid, proposal_id )

        if self.leader or proposal_id != self.proposal_id or from_uid in self.promises_rcvd:
            return

        self.promises_rcvd.add( from_uid )
        if(prev_accepted_id is None):
            self.proposed_value = prev_accepted_value

        if prev_accepted_id > self.last_accepted_id:
            self.last_accepted_id = prev_accepted_id
            # If the Acceptor has already accepted a value, we MUST set our proposal
            # to that value. Otherwise, we may retain our current value.
            if prev_accepted_value is not None:
                self.proposed_value = prev_accepted_value

        if len(self.promises_rcvd) == self.quorum_size:
            self.leader = True

            self.messenger.on_leadership_acquired()
            
            if self.proposed_value is not None and self.active:
                self.messenger.send_accept(self.proposal_id, self.proposed_value)

        
class Acceptor (object):

    messenger      = None    
    promised_id    = None
    accepted_id    = None
    accepted_value = None
    pending_promise  = None # None or the UID to send a promise message to
    pending_accepted = None # None or the UID to send an accepted message to
    active           = True
    
    @property
    def persistance_required(self):
        return self.pending_promise is not None or self.pending_accepted is not None

    def recover(self, promised_id, accepted_id, accepted_value):
        self.promised_id    = promised_id
        self.accepted_id    = accepted_id
        self.accepted_value = accepted_value
    
    def recv_prepare(self, from_uid, proposal_id):
        '''
        Called when a Prepare message is received from the network
        '''
        if self.promised_id is None:
            if self.active:
                self.messenger.send_promise(from_uid, proposal_id, self.accepted_id, self.accepted_value)
            return 
        
        if proposal_id == self.promised_id:
            # Duplicate prepare message. No change in state is necessary so the response
            # may be sent immediately
            if self.active:
                self.messenger.send_promise(from_uid, proposal_id, self.accepted_id, self.accepted_value)
        
        elif proposal_id > self.promised_id:
            if self.pending_promise is None:
                self.promised_id = proposal_id
                if self.active:
                    self.pending_promise = from_uid

        else:
            if self.active:
                self.messenger.send_prepare_nack(from_uid, proposal_id, self.promised_id)

                    
    def recv_accept_request(self, from_uid, proposal_id, value):
        '''
        Called when an Accept! message is received from the network
        '''
        if proposal_id == self.accepted_id and value == self.accepted_value:
            # Duplicate accepted proposal. No change in state is necessary so the response
            # may be sent immediately
            if self.active:
                self.messenger.send_accepted(proposal_id, value)
            
        elif proposal_id >= self.promised_id:
            if self.pending_accepted is None:
                self.promised_id      = proposal_id
                self.accepted_value   = value
                self.accepted_id      = proposal_id
                if self.active:
                    self.pending_accepted = from_uid
            
        else:
            if self.active:
                self.messenger.send_accept_nack(from_uid, proposal_id, self.promised_id)

    def persisted(self):
        '''
        This method sends any pending Promise and/or Accepted messages. Prior to
        calling this method, the application must ensure that the promised_id
        accepted_id, and accepted_value variables have been persisted to stable
        media.
        '''
        if self.active:
            
            if self.pending_promise:
                self.messenger.send_promise(self.pending_promise,
                                            self.promised_id,
                                            self.accepted_id,
                                            self.accepted_value)
                
            if self.pending_accepted:
                self.messenger.send_accepted(self.accepted_id,
                                             self.accepted_value)
                
        self.pending_promise  = None
        self.pending_accepted = None


    
class Learner (object):

    quorum_size       = None

    proposals         = None # maps proposal_id => [accept_count, retain_count, value]
    acceptors         = None # maps from_uid => last_accepted_proposal_id
    final_value       = None
    final_proposal_id = None


    @property
    def complete(self):
        return self.final_proposal_id is not None
    
    def recv_accepted(self, from_uid, proposal_id, accepted_value):
        '''
        Called when an Accepted message is received from an acceptor
        '''
        if self.final_value is not None:
            if accepted_value == self.final_value:
                self.final_acceptors.add( from_uid )
            return # already done
            
        if self.proposals is None:
            self.proposals = dict()
            self.acceptors = dict()
            
        last_pn = self.acceptors.get(from_uid)

        if not proposal_id > last_pn:
            return # Old message

        self.acceptors[ from_uid ] = proposal_id
        
        if last_pn is not None:
            oldp = self.proposals[ last_pn ]
            oldp[1].remove( from_uid )
            if len(oldp[1]) == 0:
                del self.proposals[ last_pn ]

        if not proposal_id in self.proposals:
            self.proposals[ proposal_id ] = [set(), set(), accepted_value]

        t = self.proposals[ proposal_id ]

        assert accepted_value == t[2], 'Value mismatch for single proposal!'
        
        t[0].add( from_uid )
        t[1].add( from_uid )

        if len(t[0]) == self.quorum_size:
            self.final_value       = accepted_value
            self.final_proposal_id = proposal_id
            self.final_acceptors   = t[0]
            self.proposals         = None
            self.acceptors         = None

            self.messenger.on_resolution( proposal_id, accepted_value )



class Node (Proposer, Acceptor, Learner):
    '''
    This class supports the common model where each node on a network preforms
    all three Paxos roles, Proposer, Acceptor, and Learner.
    '''

    def __init__(self, messenger, node_uid, quorum_size):
        self.messenger   = messenger
        self.node_uid    = node_uid
        self.quorum_size = quorum_size


    @property
    def proposer_uid(self):
        return self.node_uid
            

    def change_quorum_size(self, quorum_size):
        self.quorum_size = quorum_size

        
    def recv_prepare(self, from_uid, proposal_id):
        self.observe_proposal( from_uid, proposal_id )
        return super(Node,self).recv_prepare( from_uid, proposal_id )


class HeartbeatNode (Node):

    hb_period       = 1
    liveness_window = 5

    timestamp       = time

    
    def __init__(self, messenger, my_uid, quorum_size, leader_uid=None,
                 hb_period=None, liveness_window=None):
        
        super(HeartbeatNode, self).__init__(messenger, my_uid, quorum_size)

        self.leader_uid          = leader_uid
        self.leader_proposal_id  = ProposalID(1, leader_uid)
        self._tlast_hb           = self.timestamp()
        self._tlast_prep         = self.timestamp()
        self._acquiring          = False
        self._nacks              = set()

        if hb_period:       self.hb_period       = hb_period
        if liveness_window: self.liveness_window = liveness_window

        if self.node_uid == leader_uid:
            self.leader                = True
            self.proposal_id           = ProposalID(self.next_proposal_number, self.node_uid)
            self.next_proposal_number += 1


    def prepare(self, *args, **kwargs):
        self._nacks.clear()
        return super(HeartbeatNode, self).prepare(*args, **kwargs)
        
        
    def leader_is_alive(self):
        return self.timestamp() - self._tlast_hb <= self.liveness_window


    def observed_recent_prepare(self):
        return self.timestamp() - self._tlast_prep <= self.liveness_window * 1.5

    
    def poll_liveness(self):
        '''
        Should be called every liveness_window. This method checks to see if the
        current leader is active and, if not, will begin the leadership acquisition
        process.
        '''
        if not self.leader_is_alive() and not self.observed_recent_prepare():
            if self._acquiring:
                self.prepare()
            else:
                self.acquire_leadership()

            
    def recv_heartbeat(self, from_uid, proposal_id):

        if proposal_id > self.leader_proposal_id:
            # Change of leadership            
            self._acquiring = False
            
            old_leader_uid = self.leader_uid

            self.leader_uid         = from_uid
            self.leader_proposal_id = proposal_id

            if self.leader and from_uid != self.node_uid:
                self.leader = False
                self.messenger.on_leadership_lost()
                self.observe_proposal( from_uid, proposal_id )

            self.messenger.on_leadership_change( old_leader_uid, from_uid )

        if self.leader_proposal_id == proposal_id:
            self._tlast_hb = self.timestamp()
                
            
    def pulse(self):
        '''
        Must be called every hb_period while this node is the leader
        '''
        if self.leader:
            self.recv_heartbeat(self.node_uid, self.proposal_id)
            self.messenger.send_heartbeat(self.proposal_id)
            self.messenger.schedule(self.hb_period, self.pulse)

            
    def acquire_leadership(self):
        '''
        Initiates the leadership acquisition process if the current leader
        appears to have failed.
        '''
        if self.leader_is_alive():
            self._acquiring = False

        else:
            self._acquiring = True
            self.prepare()


    def recv_prepare(self, node_uid, proposal_id):
        super(HeartbeatNode, self).recv_prepare( node_uid, proposal_id )
        if node_uid != self.node_uid:
            self._tlast_prep = self.timestamp()
    
        
    def recv_promise(self, acceptor_uid, proposal_id, prev_proposal_id, prev_proposal_value):

        pre_leader = self.leader
        
        super(HeartbeatNode, self).recv_promise(acceptor_uid, proposal_id, prev_proposal_id, prev_proposal_value)

        if not pre_leader and self.leader:
            old_leader_uid = self.leader_uid

            self.leader_uid         = self.node_uid
            self.leader_proposal_id = self.proposal_id
            self._acquiring         = False
            self.pulse()
            self.messenger.on_leadership_change( old_leader_uid, self.node_uid )

            
    def recv_prepare_nack(self, from_uid, proposal_id, promised_id):
        super(HeartbeatNode, self).recv_prepare_nack(from_uid, proposal_id, promised_id)
        if self._acquiring:
            self.prepare()


    def recv_accept_nack(self, from_uid, proposal_id, promised_id):
        if proposal_id == self.proposal_id:
            self._nacks.add(from_uid)

        if self.leader and len(self._nacks) >= self.quorum_size:
            self.leader             = False
            self.promises_rcvd      = set()
            self.leader_uid         = None
            self.leader_proposal_id = None
            self.messenger.on_leadership_lost()
            self.messenger.on_leadership_change(self.node_uid, None)
            self.observe_proposal( from_uid, promised_id )



class HeartbeatMessenger (Messenger):

    def send_heartbeat(self, leader_proposal_id):
        '''
        Sends a heartbeat message to all nodes
        '''

    def schedule(self, msec_delay, func_obj):
        '''
        While leadership is held, this method is called by pulse() to schedule
        the next call to pulse(). If this method is not overridden appropriately, 
        subclasses must use the on_leadership_acquired()/on_leadership_lost() callbacks
        to ensure that pulse() is called every hb_period while leadership is held.
        '''

    def on_leadership_lost(self):
        '''
        Called when loss of leadership is detected
        '''

    def on_leadership_change(self, prev_leader_uid, new_leader_uid):
        '''
        Called when a change in leadership is detected. Either UID may
        be None.
        '''


import collections
import socket
import threading
import json
import time
from typing import Dict, Any



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
            for listener in self.listeners:
                listener(message)

    def add_listener(self, listener):
        self.listeners.append(listener)

    def _send(self, to_node: str, message: Dict[str, Any]):
        message['from'] = self.node_id
        self.socket.sendto(json.dumps(message).encode(), self.nodes[to_node])

    def broadcast(self, message: Dict[str, Any]):
        for node in self.nodes:
            if node != self.node_name:
                self._send(node, message)

    def send_prepare(self, proposal_id):
        message = {
            'type': 'prepare',
            'proposal_id': proposal_id._asdict()
        }
        self.broadcast(message)

    def send_promise(self, proposer_uid, proposal_id, previous_id, accepted_value):
        message = {
            'type': 'promise',
            'proposal_id': proposal_id._asdict(),
            'previous_id': previous_id._asdict() if previous_id else None,
            'accepted_value': accepted_value
        }
        self._send(proposer_uid, message)

    def send_accept(self, proposal_id, proposal_value):
        message = {
            'type': 'accept',
            'proposal_id': proposal_id._asdict(),
            'value': proposal_value
        }
        self.broadcast(message)

    def send_accepted(self, proposal_id, accepted_value):
        message = {
            'type': 'accepted',
            'proposal_id': proposal_id._asdict(),
            'value': accepted_value
        }
        self.broadcast(message)

    def send_prepare_nack(self, to_uid, proposal_id, promised_id):
        message = {
            'type': 'prepare_nack',
            'proposal_id': proposal_id._asdict(),
            'promised_id': promised_id._asdict()
        }
        self._send(to_uid, message)

    def send_accept_nack(self, to_uid, proposal_id, promised_id):
        message = {
            'type': 'accept_nack',
            'proposal_id': proposal_id._asdict(),
            'promised_id': promised_id._asdict()
        }
        self._send(to_uid, message)

    def on_resolution(self, proposal_id, value):
        print(f"Resolution reached: Proposal {proposal_id} with value {value}")

    def on_leadership_acquired(self):
        print(f"Node {self.node_id} has acquired leadership")


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
        self.broadcast(message)

    def schedule(self, msec_delay, func_obj):
        task = threading.Timer(msec_delay / 1000, func_obj)
        task.start()
        self.scheduled_tasks[func_obj] = task

    def cancel_scheduled_task(self, func_obj):
        if func_obj in self.scheduled_tasks:
            self.scheduled_tasks[func_obj].cancel()
            del self.scheduled_tasks[func_obj]

    def on_leadership_lost(self):
        print(f"Node {self.node_id} has lost leadership")
        self.cancel_scheduled_task(self.node.pulse)

    def on_leadership_change(self, prev_leader_uid, new_leader_uid):
        print(f"Leadership changed from {prev_leader_uid} to {new_leader_uid}")
        self.leader_uid = new_leader_uid



class PaxosNode(HeartbeatNode):
    def __init__(self, messenger, node_uid, quorum_size, leader_uid=None,
                 hb_period=None, liveness_window=None):
        super().__init__(messenger, node_uid, quorum_size, leader_uid, hb_period, liveness_window)
        self.messenger.add_listener(self.handle_message)

    def handle_message(self, message):
        msg_type = message['type']
        from_uid = message['from']

        if msg_type == 'prepare':
            proposal_id = ProposalID(**message['proposal_id'])
            self.recv_prepare(from_uid, proposal_id)
        elif msg_type == 'promise':
            proposal_id = ProposalID(**message['proposal_id'])
            previous_id = ProposalID(**message['previous_id']) if message['previous_id'] else None
            self.recv_promise(from_uid, proposal_id, previous_id, message['accepted_value'])
        elif msg_type == 'accept':
            proposal_id = ProposalID(**message['proposal_id'])
            self.recv_accept_request(from_uid, proposal_id, message['value'])
        elif msg_type == 'accepted':
            proposal_id = ProposalID(**message['proposal_id'])
            self.recv_accepted(from_uid, proposal_id, message['value'])
        elif msg_type == 'prepare_nack':
            proposal_id = ProposalID(**message['proposal_id'])
            promised_id = ProposalID(**message['promised_id'])
            self.recv_prepare_nack(from_uid, proposal_id, promised_id)
        elif msg_type == 'accept_nack':
            proposal_id = ProposalID(**message['proposal_id'])
            promised_id = ProposalID(**message['promised_id'])
            self.recv_accept_nack(from_uid, proposal_id, promised_id)
        elif msg_type == 'heartbeat':
            proposal_id = ProposalID(**message['proposal_id'])
            self.recv_heartbeat(from_uid, proposal_id)

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

ProposalID = collections.namedtuple('ProposalID', ['number', 'uid'])


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