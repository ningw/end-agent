import socket  
from comm import *
def talk_to_neighbor_controller():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('132.236.59.36', 2200))
    s.send(serialize(['test']))
    #s.send(serialize(['start-client', ['132.236.59.36'], '1']))
    s.close()

def main():
    talk_to_neighbor_controller()

if __name__ == "__main__":
    main()

