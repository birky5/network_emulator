from optparse import OptionParser
import ipaddress
import socket
import struct
import time
from os.path import exists
import datetime

# TODO
    # Modify the sender from Lab 1 to:
        # Always start at sequence number 1

        # Increment the sequence number by 1 for each packet sent, instead of by the packet length

        # Print out the observed percentage of packets lost. The loss rate that the sender prints out is not necessarily 
        # the same as the loss rate that we identify in the forwarding table since the sender might miss some ACKs. This 
        # loss rate is computed by (number of retransmissions / total number of transmissions), where total number of 
        # transmissions including both normal transmissions and retransmissions.

        # The end packet is sent after ensuring that all data packets have been received by the receiver 
        # (or if max number of retries have reached for sending all packets in the last window).

port = None
reqport = None
rate = 0
seq_no = 0
length = 0
f_hostname = None
f_port = None
priority = None
timeout = None

def print_information(packet_type, current_time, sender_addr, sequence_number, length_of_packet, payload):
    if packet_type == "D":
        print("DATA Packet:")
    elif packet_type == "R":
        print("REQUEST Packet:")
    elif packet_type == "E":
        print("END Packet:")
    print("  send time:                             %s" % current_time)
    print("  requester address and port:            {0}:{1}".format(sender_addr[0], sender_addr[1]))
    print("  sequence number:                       %s" % sequence_number)
    print("  length:                                %s" % length_of_packet)
    if type(payload) == bytes:
        print("  payload:                               %s" % payload.decode()[:4])
    else:
        print("  payload:                               %s" % "")
    print()

def chunk_file(file_name):
    # chunk the file
    chunks = []

    with open(file_name, 'r') as f:
        while True:
            chunk = f.read(length)
            if chunk:
                chunks.append(chunk)
            else:
                break

    return chunks

def udp():
    global port, reqport, rate, seq_no, length, priority, f_hostname, f_port, timeout
    source_addr = socket.gethostbyname(socket.gethostname())
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # sock.bind(("127.0.0.1", port))

    sock.bind((source_addr, port))
    # print(socket.gethostbyname(socket.gethostname()))

    receiver_addr = (source_addr, reqport) # For now, it is just an arbitary address
    # sender ip, and port that is waiting for the packets

    notEnd = True
    while notEnd:
        full_packet, sender_addr = sock.recvfrom(1024) # buffer size is 1024 bytes
        current_time = datetime.datetime.now()

        outer_header = full_packet[:17]
        inner_header = full_packet[17:26]
        payload = full_packet[26:].decode()

        unpacked_outer_header = struct.unpack("!BIHIHI", outer_header)
        unpacked_inner_header = struct.unpack("!cII", inner_header)

        window = unpacked_outer_header[5]

        chunks_of_file = chunk_file(payload)
        max_sequence_number = len(chunks_of_file) - 1
        sequence = 0

        src_addr_int = int(ipaddress.ip_address(source_addr))
        dest_addr = unpacked_outer_header[1]
        dest_port = unpacked_outer_header[2]

        buffer = []
        ack_received = {}
        transmission_count = {}

        while True:
            for _ in range(window):
                if sequence > max_sequence_number:
                    break
                time.sleep(1 / rate)
                packet = chunks_of_file[sequence].encode()
                length_of_packet = len(packet)
                packet_type = "D".encode()
                inner_header_with_payload = struct.pack("!cII", packet_type, sequence, length_of_packet) + packet
                outer_header = struct.pack("!BIHIHI", priority, src_addr_int, port, dest_addr, dest_port, length_of_packet)

                complete_packet = outer_header + inner_header_with_payload
                buffer.append(sequence)
                ack_received[sequence] = False
                transmission_count[sequence] = 0
                sequence += 1
                sock.sendto(complete_packet, (f_hostname, f_port))

            start_time = time.time()
            while not all(ack_received[sequence] for sequence in buffer):
                current_time = time.time()
                #print(transmission_count)

                if current_time - start_time > timeout / 1000:
                # while not all acknowledged
                    for sequence in buffer:
                        if not ack_received[sequence]:
                            if transmission_count[sequence] < 6:
                                packet = chunks_of_file[sequence].encode()
                                length_of_packet = len(packet)
                                packet_type = "D".encode()
                                inner_header_with_payload = struct.pack("!cII", packet_type, sequence, length_of_packet) + packet
                                outer_header = struct.pack("!BIHIHI", priority, src_addr_int, port, dest_addr, dest_port, length_of_packet)
                                complete_packet = outer_header + inner_header_with_payload
                                sock.sendto(complete_packet, (f_hostname, f_port))
                                transmission_count[sequence] += 1
                            else:
                                ack_received[sequence] = True
                                print("Packet with sequence number {0} is lost".format(sequence))
                                
                    start_time = time.time()
                
                try:
                    sock.settimeout(0.1)
                    ack_packet, sender_addr = sock.recvfrom(1024)

                    ack_inner_header = ack_packet[17:26]
                    unpacked_ack_inner_header = struct.unpack("!cII", ack_inner_header)
                    unpacked_sequence_number = unpacked_ack_inner_header[1]

                    if unpacked_sequence_number in buffer:
                        ack_received[unpacked_sequence_number] = True
                        # print(ack_received)
                except socket.timeout:
                    pass



            if sequence > max_sequence_number:
                # send an end packet
                packet_type = "E".encode()
                end_inner_header_with_payload = struct.pack("!cII", packet_type, sequence, 0) + "".encode()
                outer_header = struct.pack("!BIHIHI", priority, src_addr_int, port, dest_addr, dest_port, 0)
                complete_packet = outer_header + end_inner_header_with_payload
                sock.sendto(complete_packet, (f_hostname, f_port))
                break
        notEnd = False

    # right now we are just receiving the packets, nothing else currently.

### getting options from command line
def get_options():
    parser = OptionParser()
    parser.add_option('-p', dest='port', help='port is the port on which the sender waits for requests', action='store', type='int')
    parser.add_option('-g', dest='reqport', help='requester port is the port on which the requester is waiting', action='store', type='int')
    parser.add_option('-r', dest='rate', help='rate is the number of packets to be sent per second', action='store', type='int')
    parser.add_option('-q', dest='seq_no', help='seq_no is the initial sequence of the packet exchange', action='store', type='int')
    parser.add_option('-l', dest='length', help='length is the length of the payload (in bytes) in the packets', action='store', type='int')
    parser.add_option('-f', dest='f_hostname', help='the host name of the emulator', action='store', type='string')
    parser.add_option('-e', dest='f_port', help='the port of the emulator', action='store', type='int')
    parser.add_option('-i', dest='priority', help='the priority of the sent packets', action='store', type='int')
    parser.add_option('-t', dest='timeout', help='the timeout for retransmission for lost packets in the unit of milliseconds', action='store', type='int')

    (options, args) = parser.parse_args()

    global port, reqport, rate, seq_no, length, f_hostname, f_port, priority, timeout
    port = options.port
    reqport = options.reqport
    rate = options.rate
    seq_no = options.seq_no
    length = options.length
    f_hostname = options.f_hostname
    f_port = options.f_port
    priority = options.priority
    timeout = options.timeout


def main():
    get_options()
    udp()
    
if __name__ == "__main__":
    main()