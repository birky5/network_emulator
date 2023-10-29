from optparse import OptionParser
from queue import Queue
import socket
import select

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

def emulator():
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

            # step #2: once you receive a packet, decide whether is to be forwarded by consulting forwarding table
            # step #3: queue packet according to pracket priority level if the queue is not full


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
    
if __name__ == "__main__":
    main()