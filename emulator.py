from optparse import OptionParser
import ipaddress
from queue import Queue
import socket
import select
import struct
import datetime
import time
import random

port, queue_size, file_name, log = None, None, None, None

def read_static_forwarding_table():
    table = open(file_name, "r")

    # filter only the lines that apply to them, such as the port in the
    # table of the emulator is the port of the emulator we are running
    # (the port variable)
    table_lines = table.readlines()
    table.close()

    hostname = socket.gethostbyname(socket.gethostname())

    #for line in table_lines:
    #    new_line = line.split()
    #    if int(new_line[1]) != port and socket.gethostbyname(new_line[0]) != hostname:
    #        table_lines.remove(line)

    table_lines = [x.strip() for x in table_lines if int(x.split()[1]) == port and socket.gethostbyname(x.split()[0]) == hostname]
    print(table_lines)

    # remove all lines that where the "hostname port" pair doesn't have
    # a port that is equal to the port of the emulator we are running

    return table_lines

def log_packet_loss(reason, source_hostname, source_port, dest_hostname, dest_port, time_of_loss, priority, size):
    with open(log, "a") as log_file:
        log_file.write("Reason: " + reason + "\n")
        log_file.write("Source hostname and port: " + source_hostname + ":" + str(source_port) + "\n")
        log_file.write("Destination hostname and port: " + dest_hostname + ":" + str(dest_port) + "\n")
        log_file.write("Time of loss: " + time_of_loss + "\n")
        log_file.write("Priority: " + str(priority) + "\n")
        log_file.write("Size: " + str(size) + "\n")
        log_file.write("\n")

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
            # print(unpacked_outer_header)

            match_found = False

            for line in parsed_table:
                line = line.split()
                forward_table_hostname = socket.gethostbyname(line[2])
                forward_table_port = int(line[3])

                packet_hostname = str(ipaddress.ip_address(unpacked_outer_header[3]))
                packet_port = unpacked_outer_header[4]

                source_hostname = str(ipaddress.ip_address(unpacked_outer_header[1]))
                source_port = unpacked_outer_header[2]

                # compare destination of incoming packet with destination in forwarding table to find a match
                # if a match is found, then queue the packet, otherwise drop the packet and log it

                if (forward_table_hostname == packet_hostname) and (forward_table_port == packet_port):
                    print("match found, packet queued in queue number: ", unpacked_outer_header[0])
                    if unpacked_outer_header[0] == 1:
                        if high_queue.full():
                            log_packet_loss("High queue is full", source_hostname, source_port, packet_hostname, packet_port, str(datetime.datetime.now()), unpacked_outer_header[0], unpacked_outer_header[5])
                        else:
                            high_queue.put(data)
                            match_found = True
                            break
                    elif unpacked_outer_header[0] == 2:
                        if mid_queue.full():
                            log_packet_loss("Mid queue is full", source_hostname, source_port, packet_hostname, packet_port, str(datetime.datetime.now()), unpacked_outer_header[0], unpacked_outer_header[5])
                        else:
                            mid_queue.put(data)
                            match_found = True
                            break
                    elif unpacked_outer_header[0] == 3:
                        if low_queue.full():
                            log_packet_loss("Low queue is full", source_hostname, source_port, packet_hostname, packet_port, str(datetime.datetime.now()), unpacked_outer_header[0], unpacked_outer_header[5])
                        else:
                            low_queue.put(data)
                            match_found = True
                            break
            
            if not match_found:
                log_packet_loss("No match found in forwarding table", source_hostname, source_port, packet_hostname, packet_port, str(datetime.datetime.now()), unpacked_outer_header[0], unpacked_outer_header[5])  

            ready = None # go back out and wait for more packets to arrive

        else:
            print("waiting for something to do...")

            if not high_queue.empty():
                data = high_queue.get()
                unpacked_data = struct.unpack("!BIHIHI", data[:17])
                packet_type = struct.unpack("!cII", data[17:26])
                # find line in the forwarding table that is on the emulator host and has same destination
                # as the packet we are forwarding
                forwarding = [x for x in parsed_table if (socket.gethostbyname(x.split()[2]) == str(ipaddress.ip_address(unpacked_data[3]))) and (int(x.split()[3]) == unpacked_data[4])]
                nexthop = forwarding[0].split()

                time.sleep(int(nexthop[6]) / 1000)

                number = random.randint(1, 100)

                if number <= int(nexthop[7]) and int(nexthop[7]) != 0 and packet_type[0].decode() != "E":
                    # drop the packet
                    log_packet_loss("Loss event occurred", str(ipaddress.ip_address(unpacked_data[1])), unpacked_data[2], str(ipaddress.ip_address(unpacked_data[3])), unpacked_data[4], str(datetime.datetime.now()), unpacked_data[0], unpacked_data[5])
                else:
                    sock.sendto(data, (nexthop[4], int(nexthop[5])))
                # print(forwarding)

            elif not mid_queue.empty() and high_queue.empty():
                data = mid_queue.get()
                unpacked_data = struct.unpack("!BIHIHI", data[:17])
                packet_type = struct.unpack("!cII", data[17:26])

                # find line in the forwarding table that is on the emulator host and has same destination
                # as the packet we are forwarding
                forwarding = [x for x in parsed_table if (socket.gethostbyname(x.split()[2]) == str(ipaddress.ip_address(unpacked_data[3]))) and (int(x.split()[3]) == unpacked_data[4])]
                nexthop = forwarding[0].split()

                time.sleep(int(nexthop[6]) / 1000)

                number = random.randint(1, 100)

                if number <= int(nexthop[7]) and int(nexthop[7]) != 0 and packet_type[0].decode() != "E":
                    # drop the packet
                    log_packet_loss("Loss event occurred", str(ipaddress.ip_address(unpacked_data[1])), unpacked_data[2], str(ipaddress.ip_address(unpacked_data[3])), unpacked_data[4], str(datetime.datetime.now()), unpacked_data[0], unpacked_data[5])
                else:
                    sock.sendto(data, (nexthop[4], int(nexthop[5])))
                # print(forwarding)

            elif not low_queue.empty() and mid_queue.empty() and high_queue.empty():
                data = low_queue.get()
                unpacked_data = struct.unpack("!BIHIHI", data[:17])
                packet_type = struct.unpack("!cII", data[17:26])

                # find line in the forwarding table that is on the emulator host and has same destination
                # as the packet we are forwarding
                forwarding = [x for x in parsed_table if (socket.gethostbyname(x.split()[2]) == str(ipaddress.ip_address(unpacked_data[3]))) and (int(x.split()[3]) == unpacked_data[4])]
                nexthop = forwarding[0].split()

                time.sleep(int(nexthop[6]) / 1000)

                number = random.randint(1, 100)

                if number <= int(nexthop[7]) and int(nexthop[7]) != 0 and packet_type[0].decode() != "E":
                    # drop the packet
                    log_packet_loss("Loss event occurred", str(ipaddress.ip_address(unpacked_data[1])), unpacked_data[2], str(ipaddress.ip_address(unpacked_data[3])), unpacked_data[4], str(datetime.datetime.now()), unpacked_data[0], unpacked_data[5])
                else:
                    sock.sendto(data, (nexthop[4], int(nexthop[5])))
                # print(forwarding)

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