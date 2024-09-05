import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class Learner(object):
    quorum_size = None

    proposals = None  # maps proposal_id => [accept_count, retain_count, value]
    acceptors = None  # maps from_uid => last_accepted_proposal_id
    final_value = None
    final_proposal_id = None

    @property
    def complete(self):
        return self.final_proposal_id is not None

    def recv_accepted(self, from_uid, proposal_id, accepted_value):
        '''
        Called when an Accepted message is received from an acceptor
        '''
        logging.debug(f"Received 'accepted' from {from_uid}: proposal_id={proposal_id}, accepted_value={accepted_value}")

        if self.final_value is not None:
            if accepted_value == self.final_value:
                logging.info(f"Value already finalized. Adding {from_uid} to final_acceptors.")
                self.final_acceptors.add(from_uid)
            return  # already done

        if self.proposals is None:
            logging.debug("Initializing proposals and acceptors maps.")
            self.proposals = dict()
            self.acceptors = dict()

        last_pn = self.acceptors.get(from_uid)
        if last_pn is not None:
            logging.info(f"Last accepted proposal for {from_uid}: {last_pn}")

        if last_pn is not None and not proposal_id > last_pn:
            logging.info(f"Discarding old message from {from_uid}: proposal_id={proposal_id} <= last_pn={last_pn}")
            return  # Old message

        self.acceptors[from_uid] = proposal_id
        logging.debug(f"Updated acceptors: {from_uid} now has proposal_id={proposal_id}")

        if last_pn is not None:
            oldp = self.proposals.get(last_pn)
            if oldp:
                logging.debug(f"Removing {from_uid} from retainers of old proposal_id={last_pn}")
                oldp[1].remove(from_uid)
                if len(oldp[1]) == 0:
                    logging.debug(f"No more retainers for old proposal_id={last_pn}, deleting proposal.")
                    del self.proposals[last_pn]

        if proposal_id not in self.proposals:
            logging.debug(f"New proposal received: proposal_id={proposal_id}, accepted_value={accepted_value}")
            self.proposals[proposal_id] = [set(), set(), accepted_value]

        t = self.proposals[proposal_id]
        assert accepted_value == t[2], 'Value mismatch for single proposal!'

        logging.debug(f"Adding {from_uid} to acceptors and retainers for proposal_id={proposal_id}")
        t[0].add(from_uid)  # acceptors
        t[1].add(from_uid)  # retainers

        if len(t[0]) == self.quorum_size:
            logging.info(f"Quorum reached for proposal_id={proposal_id}. Finalizing value={accepted_value}.")
            self.final_value = accepted_value
            self.final_proposal_id = proposal_id
            self.final_acceptors = t[0]
            self.proposals = None
            self.acceptors = None

            logging.debug(f"Resetting proposals and acceptors after resolution.")
            self.messenger.on_resolution(proposal_id, accepted_value)
