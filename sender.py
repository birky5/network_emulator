from optparse import OptionParser
import socket
import struct
import time
from os.path import exists
import datetime

port = None
reqport = None
rate = 0
seq_no = 0
length = 0

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
    global port, reqport, rate, seq_no, length
    ip_address = socket.gethostbyname(socket.gethostname())
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # sock.bind(("127.0.0.1", port))

    sock.bind((ip_address, port))
    # print(socket.gethostbyname(socket.gethostname()))

    receiver_addr = (ip_address, reqport) # For now, it is just an arbitary address
    # sender ip, and port that is waiting for the packets

    notEnd = True
    while notEnd:
        full_packet, sender_addr = sock.recvfrom(1024) # buffer size is 1024 bytes
        current_time = datetime.datetime.now()

        header = full_packet[:9]
        payload = full_packet[9:]

        header = struct.unpack("!cII", header)
        packet_type = header[0].decode()
        payload = payload.decode()

        chunks_of_file = chunk_file(payload)
        # print(1 / rate) # number of packets to send per second

        # this for loop sends over the chunks of the file
        for i in range(0,len(chunks_of_file)):
            # time.sleep((rate / len(chunks_of_file)))
            time.sleep(1 / rate)
            # print(chunks_of_file[i])
            packet = chunks_of_file[i].encode()
            prev_seq_no = seq_no
            seq_no += len(chunks_of_file[i])

            # if length of the chunk is less than the length to send
            # over in bytes, then we need to follow that last DATA
            # packet with an END packet
            if i == len(chunks_of_file) - 1:
                # we need to send a data packet then an end packet
                packet_type = b"D"
                sequence_number = seq_no
                length_of_packet = len(packet)

                udp_header = struct.pack("!cII", packet_type, sequence_number, length_of_packet)
                packet_with_header = udp_header + packet
                sock.sendto(packet_with_header, sender_addr)
                current_time = datetime.datetime.now()

                print_information(packet_type.decode(), current_time, sender_addr, prev_seq_no, len(packet), packet)

                # now the end packet
                packet_type = b"E"
                udp_header = struct.pack("!cII", packet_type, sequence_number, 0)
                packet_with_header = udp_header + "".encode()
                sock.sendto(packet_with_header, sender_addr)
                current_time = datetime.datetime.now()

                print_information(packet_type.decode(), current_time, sender_addr, seq_no, len(""), "")

                notEnd = False
            else:
                # otherwise, just a DATA packet is sent
                packet_type = b"D"
                
                sequence_number = seq_no
                length_of_packet = len(packet)

                udp_header = struct.pack("!cII", packet_type, sequence_number, length_of_packet)
                packet_with_header = udp_header + packet

                sock.sendto(packet_with_header, sender_addr)
                current_time = datetime.datetime.now()

                print_information(packet_type.decode(), current_time, sender_addr, prev_seq_no, len(packet), packet)

            if len(chunks_of_file) < length:
                notEnd = False
        # we got the file name from the requester, now we need to 
        # send the file to the requester in chunks

### getting options from command line
def get_options():
    parser = OptionParser()
    parser.add_option('-p', dest='port', help='port is the port on which the sender waits for requests', action='store', type='int')
    parser.add_option('-g', dest='reqport', help='requester port is the port on which the requester is waiting', action='store', type='int')
    parser.add_option('-r', dest='rate', help='rate is the number of packets to be sent per second', action='store', type='int')
    parser.add_option('-q', dest='seq_no', help='seq_no is the initial sequence of the packet exchange', action='store', type='int')
    parser.add_option('-l', dest='length', help='length is the length of the payload (in bytes) in the packets', action='store', type='int')

    (options, args) = parser.parse_args()

    global port, reqport, rate, seq_no, length
    port = options.port
    reqport = options.reqport
    rate = options.rate
    seq_no = options.seq_no
    length = options.length

def main():
    get_options()
    udp()
    
if __name__ == "__main__":
    main()