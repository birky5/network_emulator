import socket
import struct
import datetime
import ipaddress
from optparse import OptionParser

# TODO
    # Modify the requester from Lab 1 to:
        # Verify that the destination IP address in the packet is indeed its own IP address

        # Suppress display of individual DATA packet information.

port = None
file_option = "default.txt"
f_hostname = None
f_port = None
window = None

def print_information(packet_type, current_time, sender_addr, sequence_number, length_of_packet, payload):
    if packet_type == "D":
        print("DATA Packet:")
    elif packet_type == "R":
        print("REQUEST Packet:")
    elif packet_type == "E":
        print("END Packet:")
    print("  recv time:                 %s" % current_time)
    print("  sender address and port:   {0}:{1}".format(sender_addr[0], sender_addr[1]))
    print("  sequence:                  %s" % sequence_number)
    print("  length:                    %s" % length_of_packet)
    if type(payload) == bytes:
        print("  payload:                    %s" % payload.decode()[:4])
    else:
        print("  payload:                   %s" % "")
    print()

def read_tracker_file_by_column():
    tracker_file = open("tracker.txt", "r")
    tracker_file_lines = tracker_file.readlines()
    tracker_file.close()

    tracker_file_lines.sort(key=lambda x: int(x.split()[1]))
    # sort by the sequence number
    tracker_file_lines = [x.strip() for x in tracker_file_lines if file_option and file_option in x]
    # then remove all lines that do not contain the file that we are requesting

    return tracker_file_lines

def udp(sorted_and_parsed_tracker):
    source_addr = socket.gethostbyname(socket.gethostname()) # host where requester is running
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # sock.bind((UDP_IP, port))
    sock.bind((source_addr, port))

    for line in sorted_and_parsed_tracker: # where we get each section of the file
        line = line.split() # splits the line into a list
        priority = 0x01 # 1 byte
        source_port = port # 1 byte
        dest_addr = int(ipaddress.ip_address(socket.gethostbyname(line[2])))
        dest_port = int(line[3])
        inner_length = window
        source_addr_int = int(ipaddress.ip_address(source_addr))

        outer_header = struct.pack("!BIHIHI", priority, source_addr_int, source_port, dest_addr, dest_port, inner_length)

        packet_type = "R".encode()
        sequence_number = 0
        packet = file_option.encode()

        inner_header = struct.pack("!cII", packet_type, sequence_number, len(packet)) + packet

        sock.sendto(outer_header + inner_header, (f_hostname, f_port))

    while True: # now we receive all the packets we are waiting on
        full_packet, sender_addr = sock.recvfrom(1024)

        outer_header = full_packet[:17]
        inner_header = full_packet[17:26]
        payload = full_packet[26:].decode()

        unpacked_outer_header = struct.unpack("!BIHIHI", outer_header)
        unpacked_inner_header = struct.unpack("!cII", inner_header)

        print(unpacked_outer_header)
        print(unpacked_inner_header)
        print(payload)

### getting options from command line
def get_options():
    parser = OptionParser()
    parser.add_option('-p', dest='port', help='port is the port on which the requester waits for packets.', action='store', type='int')
    parser.add_option('-o', dest='fileoption', help='file option is the name of the file that is being requested.', action='store', type='string')
    parser.add_option('-f', dest='f_hostname', help='the host name of the emulator', action='store', type='string')
    parser.add_option('-e', dest='f_port', help='the port number of the emulator', action='store', type='int')
    parser.add_option('-w', dest='window', help='the requesters window size', action='store', type='int')

    (options, args) = parser.parse_args()

    global port, file_option, f_hostname, f_port, window
    port = options.port
    file_option = options.fileoption
    f_hostname = options.f_hostname
    f_port = options.f_port
    window = options.window

def main():
    get_options()
    sorted_and_parsed_tracker = read_tracker_file_by_column()
    udp(sorted_and_parsed_tracker)

if __name__ == "__main__":
    main()
