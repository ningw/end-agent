import logging
import threading
import controller_communicator as communicator
#from port_stats import PortStatsTruncated

class CtrlChannel(communicator.TCPChannel):

    def __init__(self, host, port, portstats):
        communicator.TCPChannel.__init__(self, host, port)
        self.portstats = portstats
        self.connected = False

    def handle_connect(self):
        self.connected = True

    def recv_command(self, cmd):
        #if cmd[0] == "port_stats":
        #    self.portstats.update_rate(cmd[1], cmd[2])
        if cmd[0] == "test":
            print "received test from %s" %cmd[1]
        else:
            self.channel_status[cmd[1]] = cmd[0]

class CtrlClient(communicator.TCPMultiChannel):

    def __init__(self, pox_ip, port):
        communicator.TCPMultiChannel.__init__(self, pox_ip, port)
        #self.port_stats = PortStatsTruncated()
        self.port_stats = {}
    def create_channel(self, ip, port):
        return CtrlChannel(ip, port, self.port_stats)

    def send_controller_protocol(self, protocol):
        for channel in self.all_channels():
            channel.send_command(('set-mode', protocol))

    def send_test_command(self,msg):
        if not self.all_channels():
            self.create_connections()
        if self.all_channels():
            for channel in self.all_channels():
                print channel
                channel.send_command(msg)
        else:
            print "Server is not up"

    def send_halo_stepsize(self, stepsize):
        for channel in self.all_channels():
            channel.send_command(('set-stepsize', stepsize))

    def check_statuses(self):
        for channel in self.all_channels():
            channel.send_command(('get-statuses'))

    def send_link_weight(self, switch_dpid, port, weight):
        for channel in self.all_channels():
            if switch_dpid in self.pox_ip[channel.host]:
                channel.send_command((['set-weight', switch_dpid, port, weight]))
                # Safe to assume, two controllers don't control the same switch
                # node; so I break early
                #
                # TODO: would be faster if we just maitain a reverse dict for
                # pox_ip.
                break

    def send_switch_config(self, configs, pox_ip):
        for channel in self.all_channels():
            for switch_dpid in pox_ip[channel.host]:
                channel.send_command(('set-switch-config', switch_dpid, configs[switch_dpid]))

    def disable_link(self, switch_dpid, port_no, pox_ip):
        for channel in self.all_channels():
            if switch_dpid in pox_ip[channel.host]:
                channel.send_command(('disable-link', switch_dpid, port_no))

    def enable_link(self, switch_dpid, port_no, pox_ip):
        for channel in self.all_channels():
            if switch_dpid in pox_ip[channel.host]:
                channel.send_command(('enable-link', switch_dpid, port_no))

    def stop_pox(self):
        for channel in self.all_channels():
            if channel.connected:
                channel.send_command(['stop-pox'])
