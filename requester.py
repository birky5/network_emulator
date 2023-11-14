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

    sender_data = {}

    for line in sorted_and_parsed_tracker: # where we get each section of the file
        line = line.split() # splits the line into a list
        priority = 0x01 # 1 byte
        source_port = port # 1 byte
        dest_addr = int(ipaddress.ip_address(socket.gethostbyname(line[2])))
        dest_port = int(line[3])
        inner_length = window
        source_addr_int = int(ipaddress.ip_address(source_addr))

        outer_header = struct.pack("!BIHIHI", priority, source_addr_int, source_port, dest_addr, dest_port, inner_length)

        address = (socket.gethostbyname(line[2]), int(line[3]))

        if address not in sender_data:
            sender_data[address] = {}

        packet_type = "R".encode()
        sequence_number = 0
        packet = file_option.encode()

        inner_header = struct.pack("!cII", packet_type, sequence_number, len(packet)) + packet

        sock.sendto(outer_header + inner_header, (f_hostname, f_port))


    notEnd = True
    end_packet_count = 0

    while notEnd: # now we receive all the packets we are waiting on
        full_packet, sender_addr = sock.recvfrom(1024)

        # print(sender_data)

        outer_header = full_packet[:17]
        inner_header = full_packet[17:26]
        payload = full_packet[26:].decode()

        unpacked_outer_header = struct.unpack("!BIHIHI", outer_header)
        unpacked_inner_header = struct.unpack("!cII", inner_header)

        packet_type = unpacked_inner_header[0].decode()

        src_ip = str(ipaddress.ip_address(unpacked_outer_header[1]))
        src_port = unpacked_outer_header[2]
        source_info = (src_ip, src_port)

        dest_ip = str(ipaddress.ip_address(unpacked_outer_header[3]))
        host_ip = socket.gethostbyname(socket.gethostname())
        
        if dest_ip == host_ip:
            if packet_type == "E":
                end_packet_count += 1

                if end_packet_count == len(sorted_and_parsed_tracker):
                    # if this is the last end packet, then write to the file
                    for key in sender_data:
                        sorted_data = dict(sorted(sender_data[key].items()))
                        
                        for sequence in sorted_data:
                            with open(file_option, "a") as f:
                                f.write(sorted_data[sequence])
                        
                    notEnd = False
            else:
                sender_data[source_info][unpacked_inner_header[1]] = payload

                # Acknowledge all the packets I am receiving
                packet_type = "A".encode()
                sequence_number = unpacked_inner_header[1]

                ack_inner_header = struct.pack("!cII", packet_type, sequence_number, 0) + "".encode()
                ack_outer_header = struct.pack("!BIHIHI", 0x01, unpacked_outer_header[3], unpacked_outer_header[4], unpacked_outer_header[1], unpacked_outer_header[2], 0)
                sock.sendto(ack_outer_header + ack_inner_header, (f_hostname, f_port))

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
