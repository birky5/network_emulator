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

        ack_received = {}
        transmission_count = {}
        last_send_ts = {}
        dont_do_this_again = 0

        transmissions = 0
        retransmissions = 0

        while True:
            if dont_do_this_again:
                # send an end packet
                packet_type = "E".encode()
                end_inner_header_with_payload = struct.pack("!cII", packet_type, sequence, 0) + "".encode()
                outer_header = struct.pack("!BIHIHI", priority, src_addr_int, port, dest_addr, dest_port, 0)
                complete_packet = outer_header + end_inner_header_with_payload
                sock.sendto(complete_packet, (f_hostname, f_port))
                loss_rate = (retransmissions / transmissions) * 100
                print("Observed LOSS rate: %f" % loss_rate)
                notEnd = False
                break
            else:
                for _ in range(window):
                    if sequence > max_sequence_number:
                        dont_do_this_again += 1
                        # if we reached the last window, set dont_do_this_again to 1
                        # so after the next batch of retrying transmission, just send an end packet
                        break
                    else:
                        time.sleep(1 / rate)
                        packet = chunks_of_file[sequence].encode()
                        length_of_packet = len(packet)
                        packet_type = "D".encode()
                        inner_header_with_payload = struct.pack("!cII", packet_type, sequence, length_of_packet) + packet
                        outer_header = struct.pack("!BIHIHI", priority, src_addr_int, port, dest_addr, dest_port, length_of_packet)

                        complete_packet = outer_header + inner_header_with_payload
                        ack_received[sequence] = False
                        transmission_count[sequence] = 0
                        last_send_ts[sequence] = datetime.datetime.now()
                        sequence += 1
                        sock.sendto(complete_packet, (f_hostname, f_port))
                        transmissions += 1

                start_time = datetime.datetime.now()
                while not all(ack_received.values()):
                    current_time = datetime.datetime.now()
                    # print(current_time - start_time > timeout / 1000)
                    if current_time - start_time > timeout / 1000:
                        for sequence in ack_received:
                            if not ack_received[sequence]:
                                if transmission_count[sequence] == 6:
                                    ack_received[sequence] = True
                                    # just set it equal to true so we don't have to send it again
                                    print("ERROR: Gave up on packet %s, >5 retransmissions." % sequence)
                                else:
                                    time_since_last_send = current_time - last_send_ts[sequence]
                                    if time_since_last_send.total_seconds() >= (1 / rate):
                                        # we need to send the packet immediately
                                        transmission_count[sequence] += 1
                                        last_send_ts[sequence] = datetime.datetime.now()
                                        packet = chunks_of_file[sequence].encode()
                                        length_of_packet = len(packet)
                                        packet_type = "D".encode()
                                        inner_header_with_payload = struct.pack("!cII", packet_type, sequence, length_of_packet) + packet
                                        outer_header = struct.pack("!BIHIHI", priority, src_addr_int, port, dest_addr, dest_port, length_of_packet)
                                        complete_packet = outer_header + inner_header_with_payload
                                        sock.sendto(complete_packet, (f_hostname, f_port))
                                        transmissions += 1
                                        retransmissions += 1
                                    else:
                                        time_to_wait = (1 / rate) - time_since_last_send.total_seconds()
                                        if time_to_wait > 0:
                                            time.sleep(time_to_wait)
                                        # after we sleep to keep with the rate resend the packet
                                        transmission_count[sequence] += 1
                                        last_send_ts[sequence] = datetime.datetime.now()
                                        packet = chunks_of_file[sequence].encode()
                                        length_of_packet = len(packet)
                                        packet_type = "D".encode()
                                        inner_header_with_payload = struct.pack("!cII", packet_type, sequence, length_of_packet) + packet
                                        outer_header = struct.pack("!BIHIHI", priority, src_addr_int, port, dest_addr, dest_port, length_of_packet)
                                        complete_packet = outer_header + inner_header_with_payload
                                        sock.sendto(complete_packet, (f_hostname, f_port))
                                        transmissions += 1
                                        retransmissions += 1
                        start_time = datetime.datetime.now()

                    try:
                        sock.settimeout(0.1)
                        ack_packet, sender_addr = sock.recvfrom(1024)

                        ack_inner_header = ack_packet[17:26]
                        unpacked_ack_inner_header = struct.unpack("!cII", ack_inner_header)
                        ack_sequence_number = unpacked_ack_inner_header[1]

                        ack_received[ack_sequence_number] = True
                        # print(transmission_count)
                    except socket.timeout:
                        pass
    

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