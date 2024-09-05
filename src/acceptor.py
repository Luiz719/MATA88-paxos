import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Acceptor(object):
    messenger = None    
    promised_id = None
    accepted_id = None
    accepted_value = None
    pending_promise = None  # None or the UID to send a promise message to
    pending_accepted = None  # None or the UID to send an accepted message to
    active = True

    @property
    def persistence_required(self):
        return self.pending_promise is not None or self.pending_accepted is not None

    def recover(self, promised_id, accepted_id, accepted_value):
        self.promised_id = promised_id
        self.accepted_id = accepted_id
        self.accepted_value = accepted_value
        logging.debug(f"Acceptor recovered with promised_id: {promised_id}, accepted_id: {accepted_id}, accepted_value: {accepted_value}")

    def recv_prepare(self, from_uid, proposal_id):
        '''
        Called when a Prepare message is received from the network.
        '''
        logging.info(f"Acceptor received Prepare message from {from_uid} with proposal_id: {proposal_id}")

        if self.promised_id is None:
            logging.debug(f"No promise made yet, sending Promise to {from_uid} with accepted_id: {self.accepted_id} and accepted_value: {self.accepted_value}")
            self.promised_id = proposal_id
            self.pending_promise = from_uid
            if self.active:
                self.messenger.send_promise(from_uid, proposal_id, self.accepted_id, self.accepted_value)
            return

        if proposal_id == self.promised_id:
            # Duplicate prepare message
            logging.info(f"Duplicate Prepare received, resending Promise to {from_uid}")
            if self.active:
                self.messenger.send_promise(from_uid, proposal_id, self.accepted_id, self.accepted_value)

        elif proposal_id > self.promised_id:
            logging.debug(f"New proposal_id {proposal_id} is greater than current promised_id {self.promised_id}")
            if self.pending_promise is None:
                self.promised_id = proposal_id
                if self.active:
                    logging.info(f"Pending Promise set for {from_uid}")
                    self.pending_promise = from_uid
        else:
            logging.info(f"Prepare NACK sent to {from_uid} for proposal_id: {proposal_id}")
            if self.active:
                self.messenger.send_prepare_nack(from_uid, proposal_id, self.promised_id)

    def recv_accept_request(self, from_uid, proposal_id, value):
        '''
        Called when an Accept! message is received from the network.
        '''
        logging.info(f"Acceptor received Accept request from {from_uid} with proposal_id: {proposal_id} and value: {value}")

        if proposal_id == self.accepted_id and value == self.accepted_value:
            # Duplicate accept request
            logging.info(f"Duplicate accept request received, resending Accepted message for proposal_id: {proposal_id}")
            if self.active:
                self.messenger.send_accepted(proposal_id, value)

        elif proposal_id >= self.promised_id:
            logging.debug(f"Accept request valid, proposal_id {proposal_id} >= promised_id {self.promised_id}")
            if self.pending_accepted is None:
                self.promised_id = proposal_id
                self.accepted_value = value
                self.accepted_id = proposal_id
                if self.active:
                    logging.info(f"Pending Accepted set for {from_uid}")
                    self.pending_accepted = from_uid
                    self.messenger.send_accepted(proposal_id, self.accepted_value)
        else:
            logging.info(f"Accept NACK sent to {from_uid} for proposal_id: {proposal_id}")
            if self.active:
                self.messenger.send_accept_nack(from_uid, proposal_id, self.promised_id)

    def persisted(self):
        '''
        This method sends any pending Promise and/or Accepted messages. Prior to
        calling this method, the application must ensure that the promised_id,
        accepted_id, and accepted_value variables have been persisted to stable
        media.
        '''
        logging.info("Acceptor persisting state and sending pending messages if any.")
        
        if self.active:
            if self.pending_promise:
                logging.info(f"Sending pending Promise to {self.pending_promise} with promised_id: {self.promised_id}")
                self.messenger.send_promise(self.pending_promise,
                                            self.promised_id,
                                            self.accepted_id,
                                            self.accepted_value)

            if self.pending_accepted:
                logging.info(f"Sending pending Accepted message with accepted_id: {self.accepted_id} and accepted_value: {self.accepted_value}")
                self.messenger.send_accepted(self.accepted_id, self.accepted_value)

        self.pending_promise = None
        self.pending_accepted = None
        logging.debug("Cleared pending messages after persisting.")
