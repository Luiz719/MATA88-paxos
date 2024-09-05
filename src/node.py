from time import time
from src.proposal import ProposalID
from src.proposer import Proposer
from src.acceptor import Acceptor
from src.learner import Learner


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
        self.leader_proposal_id  = ProposalID(0, leader_uid)
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

