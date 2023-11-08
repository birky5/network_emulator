from optparse import OptionParser
import ipaddress
from queue import Queue
import socket
import select
import struct

port, queue_size, file_name, log = None, None, None, None

def read_static_forwarding_table():
    table = open(file_name, "r")

    # filter only the lines that apply to them, such as the port in the
    # table of the emulator is the port of the emulator we are running
    # (the port variable)
    table_lines = table.readlines()
    table.close()

    table_lines = [x.strip() for x in table_lines if int(x.split()[1]) == port]

    # remove all lines that where the "hostname port" pair doesn't have
    # a port that is equal to the port of the emulator we are running

    return table_lines

def emulator(parsed_table):
    low_queue = Queue(maxsize = queue_size)
    mid_queue = Queue(maxsize = queue_size)
    high_queue = Queue(maxsize = queue_size)
    # .put(thing to add) to add, .get() to remove, .full() to see if full

    ip_address = socket.gethostbyname(socket.gethostname())
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((ip_address, port))

    sock.setblocking(0) # set the socket to non-blocking mode (don't wait to do something until you get a packet)

    while True:
        ready = select.select([sock], [], [], 0.1) # wait for 0.1 seconds for a packet to arrive

        if ready[0]: # if ready[0] is not empty, then there is a packet to be received
            data, addr = sock.recvfrom(1024)
            # the if statement is step #1 from 2.3 from the write up
            # print(parsed_table)
            ## for right now, just for the sake of being simple I am going to forward right to the sender

            unpacked_outer_header = struct.unpack("!BIHIHI", data[:17])

            match_found = False

            for line in parsed_table:
                line = line.split()
                forward_table_hostname = socket.gethostbyname(line[2])
                forward_table_port = int(line[3])

                packet_hostname = str(ipaddress.ip_address(unpacked_outer_header[3]))
                packet_port = unpacked_outer_header[4]

                # compare destination of incoming packet with destination in forwarding table to find a match
                # if a match is found, then queue the packet, otherwise drop the packet and log it

                if (forward_table_hostname == packet_hostname) and (forward_table_port == packet_port):
                    print("match found, packet queued in queue number: ", unpacked_outer_header[0])
                    if unpacked_outer_header[0] == 1:
                        high_queue.put(data)
                        match_found = True
                        break
                    elif unpacked_outer_header[0] == 2:
                        mid_queue.put(data)
                        match_found = True
                        break
                    elif unpacked_outer_header[0] == 3:
                        low_queue.put(data)
                        match_found = True
                        break
            
                if not match_found:
                    print("match not found, packet dropped")
                    # log the packet drop

            ready = None # go back out and wait for more packets to arrive

        else:
            print("waiting for something to do...")


### getting options from command line
def get_options():
    parser = OptionParser()
    parser.add_option('-p', dest='port', help='the port of the emulator', action='store', type='int')
    parser.add_option('-q', dest='queue_size', help='the size of each of the three queues', action='store', type='int')
    parser.add_option('-f', dest='file_name', help='the name of the file containing the static forwardin table in the format specified', action='store', type='string')
    parser.add_option('-l', dest='log', help='the name of the log file', action='store', type='string')

    (options, args) = parser.parse_args()

    global port, queue_size, file_name, log
    port = options.port
    queue_size = options.queue_size
    file_name = options.file_name
    log = options.log

    # print("port: ", port)
    # print("queue_size: ", queue_size)
    # print("file_name: ", file_name)
    # print("log: ", log)

def main():
    get_options()
    parsed_table = read_static_forwarding_table()
    emulator(parsed_table)
    
if __name__ == "__main__":
    main()