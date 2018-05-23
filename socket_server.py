##
## Current implementation of Controller Coordination
##

import asyncore
import asynchat
import socket
import threading
import os

import comm
#from pox.core import core

import logging as log
##
## Handles socket bring-up and take-down
##
class BackendServer(asyncore.dispatcher):
    """Receives connections and establishes handlers for each backend.
    """
    def __init__(self, backend, family, address, map):
        asyncore.dispatcher.__init__(self, map = map)
        self.family = family
        self.create_socket(family, socket.SOCK_STREAM)

        if self.family == socket.AF_UNIX:
            try:
                os.unlink(address)
            except OSError:
                if os.path.exists(address):
                    raise RuntimeError("cannot remove domain socket %s" % str(address))

        self.set_reuse_addr()
        self.bind(address)
        self.address = self.socket.getsockname()
        self.listen(5)
        self.backend = backend
        self.clients = []
        return

    def is_client_present(self):
        if len(self.clients) != 0:
            return True
        else:
            return False

    def create_socket(self, family, type):
        self.family_and_type = family, type
        sock = socket.socket(family, type)
        sock.setblocking(0)
        self.set_socket(sock, self._map)

    def handle_accept(self):
        # Called when a backend connects to our socket
        connection_info = self.accept()
        if connection_info is not None:
            sock, addr = connection_info

            log.info("accepted client from: %s", repr(addr))

            self.backend.backend_channel = BackendChannel(self.backend,
                                                          address=self.address,
                                                          sock=sock,
                                                          map=self._map)
            self.clients.append(sock) #FIXME: remove disconnected GUI

##
## subclass async_chat to implement a custom protocol
##
class BackendChannel(asynchat.async_chat):
    """Handles echoing messages from a single backend.
    """
    def __init__(self, backend, address, sock, map):
        self.sock = sock
        self.backend = backend
        self.address = address
        # note that received_data is a list, not a byte array, hence, if you
        # refer to received_data[0], you may get a long string
        self.received_data = []
        asynchat.async_chat.__init__(self, sock, map)
        self.ac_in_buffer_size = 4096 * 32
        self.ac_out_buffer_size = 4096 * 32
        self.set_terminator('\n')

    def collect_incoming_data(self, data):
        """Read an incoming message from the backend and put it into our outgoing queue."""
        if len(data) == 0:
            return
        # insert a string read from socket to list.
        self.received_data.append(data)

    def found_terminator(self):
        """The end of a command or message has been seen."""
        # if the received_data list has no elements in it.
        if len(self.received_data) == 0:
            return
        msg = comm.deserialize(self.received_data)

        # USE DESERIALIZED MSG
        if msg is None or len(msg) == 0:
            log.error("Received empty message from %s", self.address)
        elif msg[0] == "start-client":
            ip_list = msg[1]
            print "ip list", ip_list
            dpid = int(msg[2])
            #core.router[dpid].start_control_client(ip_list)
            #core.start_client(ip_list)
        #elif msg[0] == "set-stepsize":
            #core.stepsize = msg[1]
        elif msg[0] == "set-weight":
            switch_dpid = int(msg[1])
            portNumber = int(msg[2])
            linkWeight = int(msg[3])
            #core.router[switch_dpid].set_link_weight(portNumber, linkWeight)
        elif msg[0] == "test":
            print "received test from %s" %msg[0]
        else:
            log.error('Unknown message from %s; %s', self.address, msg)

##
## A separate thread handling controllers communication
##
class CtrlSockServer(object):

    class asyncore_loop(threading.Thread):
        def __init__(self, sock):
            self.sock = sock
            threading.Thread.__init__(self)

        def run(self):
            asyncore.loop(map = self.sock)

    def __init__(self, port):
        self.backend_channel = None

        address = ('', port) # USE KNOWN PORT

        socketmap = {}
        self.backend_server = BackendServer(self, socket.AF_INET, address, socketmap)
        socketmap[self.backend_server._fileno] = self.backend_server

        self.al = self.asyncore_loop(socketmap)
        self.al.daemon = True
        self.al.start()

    def send_stats(self, switch, stats):
        ## pickle python object
        ## send to gui
        self.send_to_neighbor(['port_stats', switch, stats])

    def send_connection_up(self, dpid):
        self.send_to_neighbor(['connection_up', '%s'%dpid])

    def send_to_neighbor(self, msg):
        serialized_msg = comm.serialize(msg)
        try:
            if (self.backend_server.is_client_present()):
                self.backend_channel.push(serialized_msg)
            else:
                log.info("GUI not connected yet")
        except IndexError as e:
            log.error("Pushing message: %s", msg)
