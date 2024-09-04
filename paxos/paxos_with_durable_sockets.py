
import os
import socket
import threading
import pickle

class Durable:
    def __init__(self, path):
        self.path = path
        if not os.path.exists(self.path):
            with open(self.path, 'wb') as f:
                pickle.dump(None, f)
    
    def save(self, data):
        with open(self.path, 'wb') as f:
            pickle.dump(data, f)
    
    def load(self):
        with open(self.path, 'rb') as f:
            return pickle.load(f)

class Messenger:
    def __init__(self, uid, port):
        self.uid = uid
        self.port = port
        self.sockets = {}

    def send(self, uid, message):
        if uid not in self.sockets:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('localhost', uid))
            self.sockets[uid] = s
        self.sockets[uid].sendall(pickle.dumps(message))

    def receive(self, callback):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('localhost', self.port))
        s.listen()
        while True:
            conn, _ = s.accept()
            threading.Thread(target=self.handle_connection, args=(conn, callback)).start()

    def handle_connection(self, conn, callback):
        data = conn.recv(4096)
        message = pickle.loads(data)
        callback(message)

class Proposer:
    def __init__(self, uid, messenger, durable):
        self.uid = uid
        self.messenger = messenger
        self.durable = durable
        self.promises_rcvd = set()
        self.proposal_id = 0
        self.proposed_value = None
        self.leader = False

    def propose(self, value):
        self.proposed_value = value
        self.proposal_id += 1
        self.messenger.send(self.uid, ('prepare', self.proposal_id))

    def receive(self, message):
        if message[0] == 'promise':
            self.handle_promise(message[1:])

    def handle_promise(self, args):
        from_uid, proposal_id = args
        if self.leader or proposal_id != self.proposal_id or from_uid in self.promises_rcvd:
            return
        self.promises_rcvd.add(from_uid)
        if len(self.promises_rcvd) > 1:  # assuming a simple quorum size of 2
            self.leader = True
            self.messenger.send(self.uid, ('accept', self.proposal_id, self.proposed_value))

class Acceptor:
    def __init__(self, uid, messenger, durable):
        self.uid = uid
        self.messenger = messenger
        self.durable = durable
        self.promised_id = None
        self.accepted_id = None
        self.accepted_value = None

    def receive(self, message):
        if message[0] == 'prepare':
            self.handle_prepare(message[1:])
        elif message[0] == 'accept':
            self.handle_accept(message[1:])

    def handle_prepare(self, args):
        proposal_id = args[0]
        if not self.promised_id or proposal_id > self.promised_id:
            self.promised_id = proposal_id
            self.messenger.send(self.uid, ('promise', self.uid, proposal_id))

    def handle_accept(self, args):
        proposal_id, value = args
        if proposal_id >= self.promised_id:
            self.accepted_id = proposal_id
            self.accepted_value = value
            self.durable.save((self.accepted_id, self.accepted_value))
            self.messenger.send(self.uid, ('accepted', self.uid, proposal_id, value))

def run_node(uid, is_proposer=False):
    messenger = Messenger(uid, 9000 + uid)
    durable = Durable('/tmp/durable_%d' % uid)
    if is_proposer:
        node = Proposer(uid, messenger, durable)
        pre_defined_value = "ProposedValue"  # pre-defined proposition
        node.propose(pre_defined_value)
    else:
        node = Acceptor(uid, messenger, durable)

    messenger.receive(node.receive)

