import socket
import struct
import datetime
from optparse import OptionParser

### requester.py per write up,
### The requester will receive these packets, subsequently write it to a file and print receipt information

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

def inet_ntop(af, addr):
    # Convert an IP address in binary format to string format.

    if af == socket.AF_INET:
        return socket.inet_ntoa(addr)
    elif af == socket.AF_INET6:
        return socket.inet_ntop(af, addr)
    else:
        raise ValueError('Unknown address family: {}'.format(af))

def udp(sorted_and_parsed_tracker):
    ip_address = socket.gethostbyname(socket.gethostname())
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # sock.bind((UDP_IP, port))
    sock.bind((ip_address, port))

    for line in sorted_and_parsed_tracker:
        line = line.split()
        # print(line)

        hostname = line[2]
        ip_address = socket.gethostbyname(hostname)

        receiver_addr = (ip_address, int(line[3]))
        # table host names need to be the CSL machine you are currently on

        packet = file_option # payload
        if packet is not None:
            packet = packet.encode()

        packet_type = "R".encode() # packet type
        sequence_number = 0 # seq number in network byte order
        if packet is not None:
            length = len(packet) # length of the payload
        else:
            length = 0

        header = struct.pack("!cII", packet_type, sequence_number, length)
        if packet is not None:
            packet_with_header = header + packet
        else:
            packet_with_header = header

        total_packets, total_packet_bytes = 0, 0
        sender_address = None

        # sender ip, and port that is waiting for the packets
        sock.sendto(packet_with_header, receiver_addr)

        print("--------------------")
        print("Requester's print information:")
        print()

        start_time = datetime.datetime.now()
        notEnd = True
        while notEnd:
            full_packet, sender_addr = sock.recvfrom(1024) # buffer size is 1024 bytes
            current_time = datetime.datetime.now()

            udp_header = full_packet[:9]
            data = full_packet[9:]

            udp_header = struct.unpack("!cII", udp_header)
            packet_type = udp_header[0].decode()

            if packet_type == "D":
                total_packets += 1
                total_packet_bytes += udp_header[2]
                sender_address = sender_addr

            print_information(packet_type, current_time, sender_addr, udp_header[1], udp_header[2], data)

            # write to a new file of the same name we are asking for
            with open(file_option, "a") as output_file:
                output_file.write(data.decode())

            if packet_type == "E":
                notEnd = False
        end_time = datetime.datetime.now()
        elapsed_time = (end_time - start_time)
        packets_per_second = total_packets / elapsed_time.total_seconds()

        print()
        print("Summary:")
        if sender_address:
            print("  sender address:             {0}:{1}".format(sender_address[0], sender_address[1]))
        print("  Total DATA packets:         %s" % total_packets)
        print("  Total DATA bytes:           %s" % total_packet_bytes)
        print("  Average packets per second: %s" % packets_per_second)
        print("  Duration of the test:       %s ms" % elapsed_time)
        print()

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
