from src.node import HeartbeatNode
from src.proposal import ProposalID


class PaxosNode(HeartbeatNode):
    '''
    The `PaxosNode` class extends `HeartbeatNode` and implements message handling methods for the Paxos
    consensus algorithm.
    '''
    def __init__(self, messenger, node_uid, quorum_size, leader_uid=None,
                 hb_period=None, liveness_window=None):
        super().__init__(messenger, node_uid, quorum_size, leader_uid, hb_period, liveness_window)
        self.messenger.add_listener(self.handle_message)

    def handle_message(self, message):
        """
        The function `handle_message` processes different types of messages in paxos
        based on the message type.
        
        :param message: The `handle_message` method is designed to handle different types of messages
        received by an object. The method takes in a `message` parameter, which is expected to be a
        dictionary containing "type" (the type of message) and "from" (the uid that sends this message).
        """
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
