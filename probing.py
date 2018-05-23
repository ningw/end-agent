import os, sys, subprocess
import multiprocessing
from time import sleep

config = [{"edge_server_ip":"132.236.59.103",
        "edge_server_id":"sf"
        },
        {"edge_server_ip":"132.236.59.76",
        "edge_server_id":"den"
        }
        ]

edge_server_loss = {}
edge_server_rtt = {}

INTVAL = 0.01
COUNT = 300#3minutes, every 10 ms 180s/0.01s=18000

def start_probing():
    try:
        #while 1:
            for server_info in config:
                print "ping start", server_info["edge_server_id"]
                ping_edge_server(server_info)
                print "ping stop", server_info["edge_server_id"]
            #duration = COUNT*INTVAL/1000+30
            #sleep(duration)
            sleep(5)
            for server_info in config:
                update_stats(server_info)
            print "latest stats", edge_server_loss, edge_server_rtt
            #recompute routes
    except KeyboardInterrupt:
        print("interrupted!")
    return

def ping_edge_server(server_info):
    edge_server_ip = server_info["edge_server_ip"]
    edge_server_id = server_info["edge_server_id"]
    log = "data/log_%s"%(edge_server_id)
    proc1=subprocess.Popen(["sudo ping %s -i %s -c %s > %s"%(edge_server_ip,INTVAL,COUNT,log)], shell=True)

def update_stats(server_info):
    edge_server_id = server_info["edge_server_id"]
    log = "data/log_%s"%(edge_server_id)
    proc2=subprocess.Popen(["sudo echo `tail %s -n 2` > %s"%(log,log)], shell=True)
    sleep(0.5)
    ping_file = open(log)
    line = ping_file.readlines()
    fields = line[0].split()
    if fields[1] != "packets":
        print "Wrong ping results!"
        print line[0]
    else:
        transmitted = float(fields[0])
        received = float(fields[3])
        loss_rate = (transmitted-received)/transmitted
        fields_rtt = line[0].split('/')
        rtt = float(fields_rtt[4])
        #update stats dictionary
        edge_server_loss[edge_server_id] = loss_rate
        edge_server_rtt[edge_server_id] = rtt
    ping_file.close()

if __name__ == '__main__':
    start_probing()
