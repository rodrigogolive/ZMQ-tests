import zmq
import time
import json
import sys

from threading import Thread
from threading import current_thread

from zmq.eventloop.ioloop import ZMQIOLoop
from zmq.eventloop.ioloop import PeriodicCallback
from zmq.eventloop.zmqstream import ZMQStream

import utils

jsonData = [
        {'name': 'Zoiao', 'id': 23},
        {'name': 'Ratao', 'id': 69}
        ]

class Worker(Thread):
    def __init__(self, context, ident):
        Thread.__init__(self)

        self.context = context
        self.last_ping = 0

        self.worker = self.context.socket(zmq.DEALER)
        self.worker.setsockopt(zmq.IDENTITY, ident)
        self.worker.connect("inproc://backend")

        # ioloop
        self.loop = ZMQIOLoop.instance()
        socket_stream = ZMQStream(self.worker, self.loop)
        socket_stream.on_recv(self.handle_recv)

    def handle_recv(self, msg):
        ident, message = msg
        message = json.loads(message)

        utils.log("<<", ident, message)

        reply_message = ""
        if message["type"] == "message" and message["data"] == "Yo!":
            reply_message = utils.create_message('list', jsonData)

        # XXX simple heartbeat, not working yet
        if message["type"] == "message" and message["data"] == "PING":
            ping_now = time.time() * 1000.0
            print "\t\t %s" % (ping_now - self.last_ping)
            #print "(%s | %s)" % (ping_now - self.last_ping, current_thread())
            accepting = 1000.0 + 10.0
            reply_message = utils.create_message('message', 'PONG')

            ## simple test for ping
            ##if (ping_now - self.last_ping <= accepting
                ##or self.last_ping == 0):
                ##reply_message = utils.create_message('list', 'PONG')
                ##self.last_ping = ping_now
            ##else:
                ##print "DISCONNECT!"

        if reply_message:
            self.worker.send(ident, zmq.SNDMORE)
            self.worker.send_json(reply_message)

            utils.log(">>", ident, reply_message)

    def wat(self):
        print "WAT"

    def run(self):
        print "Server worker thread started"

        #self.loop.add_callback(self.wat)
        self.loop.start()

        #while True:
            #print "pong?"

            #time.sleep(1.0)

if __name__ == '__main__':
    print "Initializing server on port 5555"

    # zmq setup
    context = zmq.Context()
    # will accept incoming connections
    frontend = context.socket(zmq.ROUTER)
    frontend.bind("tcp://*:5555")
    # will connect to the worker threads
    backend = context.socket(zmq.DEALER)
    backend.bind("inproc://backend")

    # pool sockets for activity
    poll = zmq.Poller()
    poll.register(frontend, zmq.POLLIN)
    poll.register(backend,  zmq.POLLIN)

    # TODO disconnection
    clients = []

    # run baby, run
    running = True
    while running:
        try:
            sockets = dict(poll.poll())

            # received a message from some client
            if frontend in sockets:
                ident, message = frontend.recv_multipart()

                if ident not in clients:
                    clients.append(ident)

                    worker = Worker(context, ident)
                    worker.start()

                backend.send_multipart([ident, message])

            # received a message from some worker thread
            if backend in sockets:
                ident, message = backend.recv_multipart()
                frontend.send_multipart([ident, message])
        except KeyboardInterrupt:
            print "Exiting like a sir"
            running = False

    frontend.close()
    backend.close()
    context.term()
