import logging
from src.proposal import ProposalID

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Proposer(object):
    messenger = None
    proposer_uid = None
    quorum_size = None

    proposed_value = None
    proposal_id = ProposalID(0, 'a')
    last_accepted_id = ProposalID(0, 'a')
    next_proposal_number = 1
    promises_rcvd = None

    leader = False
    active = True

    def set_proposal(self, value):
        '''
        Sets the proposal value for this node if this node is not already aware of
        another proposal having already been accepted.
        '''
        if self.proposed_value is None:
            self.proposed_value = value
            logging.info(f"Proposer {self.proposer_uid} set proposed value: {value}")
            if self.leader and self.active:
                logging.info(f"Proposer {self.proposer_uid} is leader and active, sending accept message.")
                self.messenger.send_accept(self.proposal_id, value)

    def prepare(self, increment_proposal_number=True):
        '''
        Sends a prepare request to all Acceptors as the first step in
        attempting to acquire leadership of the Paxos instance.
        '''
        if increment_proposal_number:
            self.leader = False
            self.promises_rcvd = set()
            self.proposal_id = ProposalID(self.next_proposal_number, self.proposer_uid)
            logging.debug(f"Proposer {self.proposer_uid} generated new proposal ID: {self.proposal_id}")
            self.next_proposal_number += 1

        if self.active:
            logging.info(f"Proposer {self.proposer_uid} sending prepare message with proposal ID: {self.proposal_id}")
            self.messenger.send_prepare(self.proposal_id)

    def observe_proposal(self, from_uid, proposal_id):
        '''
        Optional method used to update the proposal counter as proposals are
        seen on the network.
        '''
        if from_uid != self.proposer_uid:
            logging.debug(f"Proposer {self.proposer_uid} observing proposal from {from_uid}: {proposal_id}")
            if proposal_id >= (self.next_proposal_number, self.proposer_uid):
                self.next_proposal_number = proposal_id.number + 1
                logging.debug(f"Proposer {self.proposer_uid} updated next proposal number to {self.next_proposal_number}")

    def recv_prepare_nack(self, from_uid, proposal_id, promised_id):
        '''
        Called when an explicit NACK is sent in response to a prepare message.
        '''
        logging.info(f"Proposer {self.proposer_uid} received prepare NACK from {from_uid}: proposal_id={proposal_id}, promised_id={promised_id}")
        self.observe_proposal(from_uid, promised_id)

    def recv_accept_nack(self, from_uid, proposal_id, promised_id):
        '''
        Called when an explicit NACK is sent in response to an accept message.
        '''
        logging.info(f"Proposer {self.proposer_uid} received accept NACK from {from_uid}: proposal_id={proposal_id}, promised_id={promised_id}")
        # Handle accept NACK if necessary (implementation can be added here)

    def resend_accept(self):
        '''
        Retransmits an Accept message if this node is the leader and has
        a proposal value.
        '''
        if self.leader and self.proposed_value and self.active:
            logging.info(f"Proposer {self.proposer_uid} resending accept message with proposal ID: {self.proposal_id}")
            self.messenger.send_accept(self.proposal_id, self.proposed_value)

    def recv_promise(self, from_uid, proposal_id, prev_accepted_id, prev_accepted_value):
        '''
        Called when a Promise message is received from the network.
        '''
        logging.info(f"Proposer {self.proposer_uid} received promise from {from_uid}: proposal_id={proposal_id}, prev_accepted_id={prev_accepted_id}, prev_accepted_value={prev_accepted_value}")
        self.observe_proposal(from_uid, proposal_id)

        if self.leader or proposal_id != self.proposal_id or from_uid in self.promises_rcvd:
            logging.debug(f"Proposer {self.proposer_uid} ignoring promise from {from_uid} due to leader status or mismatched proposal ID.")
            return

        self.promises_rcvd.add(from_uid)
        logging.debug(f"Proposer {self.proposer_uid} added {from_uid} to promises received.")

        if prev_accepted_id is not None and prev_accepted_id > self.last_accepted_id:
            self.last_accepted_id = prev_accepted_id
            logging.debug(f"Proposer {self.proposer_uid} updated last accepted ID to {self.last_accepted_id}")

            # If the Acceptor has already accepted a value, we MUST set our proposal to that value.
            if prev_accepted_value is not None:
                logging.debug(f"Proposer {self.proposer_uid} updating proposed value to {prev_accepted_value} based on acceptor's accepted value.")
                self.proposed_value = prev_accepted_value

        if len(self.promises_rcvd) >= self.quorum_size:
            self.leader = True
            logging.info(f"Proposer {self.proposer_uid} has acquired leadership with proposal ID: {self.proposal_id}")

            self.messenger.on_leadership_acquired()

            if self.proposed_value is not None and self.active:
                logging.info(f"Proposer {self.proposer_uid} sending accept message with proposal ID: {self.proposal_id} and value: {self.proposed_value}")
                self.messenger.send_accept(self.proposal_id, self.proposed_value)
