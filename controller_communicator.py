import logging
import traceback
import asyncore
import asynchat
import threading
import socket
import comm
import errno

TERM_CHAR='\n'

class TCPChannel(asynchat.async_chat):
    """
    Handles talking to one backend port.
    """
    def __init__(self, host, port):
        # note that received_data is a list, not a byte array, hence, if you
        # refer to received_data[0], you may get a long string
        asynchat.async_chat.__init__(self)
        self.host = host
        self.received_data = []
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))
        self.ac_in_buffer_size = 4096 * 32
        self.ac_out_buffer_size = 4096 * 32
        self.set_terminator(TERM_CHAR)

    def collect_incoming_data(self, data):
        """Read an incoming message from the backend and put it into our outgoing queue."""
        if len(data) == 0:
            return
        self.received_data.append(data)

    def found_terminator(self):
        """The end of a command or message has been seen."""
        # if the received_data list has no elements in it.
        if len(self.received_data) == 0:
            return

        msg = comm.deserialize(self.received_data)
        if msg is None or len(msg) == 0:
            pass
        else:
            logging.info("controller %s replied %s", self.host, msg)
            self.recv_command(msg)

    def handle_error(self):
        #asynchat.async_chat.handle_error(self)
        pass

    def send_command(self, msg):
        try:
            logging.info("sending %s to %s", msg, self.host)
            self.push(comm.serialize(msg))
        except IndexError as e:
            logging.info(traceback.format_exc())

class TCPMultiChannel(threading.Thread):
    """
    Manages multiple TCPChannels using asyncore inside a separate thread.

    To use this, subclass it, and provide 2 methods
    - create_channel: Creates an instance of TCPChannel (or subclass)
    - post_connect: Any actions to take after connecting to TCPChannel
    """

    def __init__(self, pox_ip, port):
        threading.Thread.__init__(self)
        self.pox_ip = pox_ip #array
        self.pox_port = port
        self.backend_channels = {}

    def run(self):
        self.create_connections()
        self.post_connect()
        asyncore.loop()

    def create_connections(self):
        for ip_addr in self.pox_ip:
            print "Creating connections"
            try:
                self.backend_channels[ip_addr] = self.create_channel(ip_addr, self.pox_port)
            except socket.error as serr:
                if serr.errno != errno.ECONNREFUSED:
                    raise serr
                else:
                    print "catch error"
                    del self.backend_channels[ip_addr]

    def post_connect(self):
        pass

    def stop(self):
        for channel in self.all_channels():
            channel.close()

    def all_channels(self):
        for ip_addr, channel in self.backend_channels.iteritems():
            yield(channel)
