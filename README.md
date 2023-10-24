# Network Emulator and Reliable Transfer

## 1. Overview
Implemented a network emulator and add reliable transfer to your distributed file transfer in the previously made Distributed File System

## 1.1 Network Emulator
The network emulator receives a packet, decide where it is to be forwarded, and, based on the packet priority level, queue it for sending. 
Upon sending, you will delay the packet to simulate link bandwidth, and randomly drop packets to simulate a lossy link.

Also implemented packet priority queues, a common feature of many packet queueing algorithms. There will be three packet 
priority levels, and there will be a separate sending queue for each priority level. Each queue will have a fixed size. If the outbound queue for a 
particular priority level is full, the packet will be dropped. Higher priority packets are always forwarded before lower priority packets.

## 1.2 Reliable Transfer
To achieve the reliable transfer, the requester will advertise a window size (see the requester specification of this write up for more info) 
to the sender with the request packet. The sender will send a full "window" of packets and wait for ACKs of each packet before sending more packets. 
After a certain timeout, the sender will retransmit the packets that it has not received an ack for.

## 2. Details
## 2.1 Forwarding Encapsulation and Packet Structure
Adding an 8-bit priority, a 32-bit source IP address, a 16-bit source port, a 32-bit destination IP address, a 16-bit destination port and a 32-bit 
length to the front of the packet layout from “programming assignment #1”. Compare this with how UDP datagrams are encapsulated inside IP datagrams 
(which are then encapsulated in a layer 2 protocol, such as Ethernet). The length field of the outer packet is set to the total size of the inner packet, 
i.e. inner packet header size + inner packet payload size.
Note that:
- Valid values for priority levels are:
1. 0x01 - highest priority
2. 0x02 - medium priority
3. 0x03 - lowest priority
- For the ack packet, the packet type will be A (capital a) and the sequence field will contain the sequence number of the packet that is being acknowledged.
- All the packets sent by the requester should have priority 1.
- The priority of the END packet is the same as the other packets in the flow.

## 2.2 Logical Functions of Emulator
The logical functions of the emulator consist of routing, queueing, sending, and logging. Each sub-function is detailed below.

**Static forwarding table:**

The logical functions depend on the static forwarding table provided to the emulators through a file. The file contain lines in the format below, with space as delimiter between the various fields:

<emulator> <destination> <nexthop> <delay> <loss probability>

- emulator: a "<Host name> <Port>" pair that identifies the emulator for which the current entry is associated with. Multiple emulators may be specified in a single table, and so they must filter only the lines that apply to them,
- destination: a "<Host name> <Port>" pair that identifies the final destination of the packet,
- next hop: a "<Host name> <Port>" pair that identifies the next entity to forward the packet to. It can be an emulator, sender or requester.
- delay: in milliseconds, and identifies how long the emulator will delay before sending a packet to the corresponding destination.
- loss probability: in percentage, and identifies the probability that the emulator will drop a packet when sending pockets to the corresponding destination.

**Routing function:**
The routing function is based on the static forwarding table that you provide to your program through the file described above. The destination of an 
incoming packet is compared with the destination in the forwarding table to find a match. If a match is found, the packet is queued for forwarding to the next hop. 
If a match is not found, the packet is dropped and the event should be logged (see logging function below).

The emulator reads this file once it starts running and then only refers to its version of the file in memory for every packet. The emulator ignores lines 
in the table that do not correspond to its own hostname and port. Note that emulator, sender, and requester are all uniquely identified with a "<Host name, Port>" 
pair and thus multiple of them can run on the same host.

**Queueing function:**
The queueing function should examine the priority field on the packet and place the packet in an appropriate queue. All the three queues are of fixed size. 
This queue size is specified on the command line of the emulator startup. If a queue is full, the packet is dropped and this event is logged (see logging function below).

**Send function:**
The send function accepts packets from the three queues defined above and simulates network link conditions for each destination. Packets bound for a destination 
are first delayed to simulate link bandwidth. The delay is defined in the forwarding table and is specified in milliseconds. After a packet has been delayed, it 
may be dropped to simulate a lossy link based on the loss probability provided in the forwarding table, and the event is logged (see logging function below). If a 
packet is not dropped, it is then sent to the network.

**Logging function:**
The logging function is integral to all functions of the emulator. A packet may be dropped in the emulator in the routing function, the queueing function, or 
in the send function. Any and all packet drop events must be logged to a file. Loss events must provide a textual reason for the loss (e.g., "no forwarding entry 
found", "priority queue 1 was full'', "loss event occurred.") Each log event must include the source hostname and port, the intended destination host name and port, 
the time of loss (to millisecond resolution), the priority level of the packet, and the size of the payload.


## 2.3 Forwarding Summary
The order of processing should be similar to the following. Your emulator can simply follow the steps below in an infinite loop and no threading is required for 
this assignment. Note that logging is not an explicit part of this sequence.

1. Receive packet from network in a non-blocking way. This means that you should not wait/get blocked in the recvfrom function until you get a packet. Check if you have received a packet; If not jump to 4,
2. Once you receive a packet, decide whether packet is to be forwarded by consulting the forwarding table,
3. Queue packet according to packet priority level if the queue is not full,
4. If a packet is currently being delayed and the delay has not expired, goto Step 1.
5. If no packet is currently being delayed, select the packet at the front of the queue with highest priority, remove that packet from the queue and delay it,
6. When the delay expires, randomly determine whether to drop the packet,
7. Otherwise, send the packet to the proper next hop.
8. Goto Step 1.

## 2.4 Reliable Transfer
The procedure is as follows:

- Upon receipt of a request packet, the sender sends a full window of packets at the rate specified by the user.
- The sender keeps this set of data in a buffer, and keeps a timeout for each of the packets. If it does not receive an ack for a packet and its timeout expires, it will retransmit that packet. The timeout is fixed and is specified by one of the sender's parameters.
- If an ack packet is not received after re-transmitting the packet 5 times, the sender will print an error stating that it gave up on the packet with that specific sequence number, and continue with the next packet.
- Once all packets of that window have been acked the sender sends another window of packets.
- The requester should have a buffer and make sure that it saves the data to the file in the order of the packets' sequence numbers. It should also make sure that it does not print duplicate packets into the file.
- The requester acks every packet that it receives, even if it has already written that packet to the file (may happen if the sender retransmitted a packet due to its timeout, but the original packet actually made it to the requester).

## 2.5 Specification
**Emulator:**

The network emulator should be invoked in the following way:

```python3 emulator.py -p <port> -q <queue_size> -f <filename> -l <log>```

- **port:** the port of the emulator.
- **queue_size:** the size of each of the three queues.
- **filename:** the name of the file containing the static forwarding table in the format specified above.
- **log:** the name of the log file.

The network emulator must implement the routing, queueing, sending, and logging logical functions described above. Your program must be able to support 
forwarding packets through one or multiple emulators (ex. sender to emulator1 to emulator2 to requester). If you have implemented your emulator correctly, 
this is automatically satisfied.

Note that your emulator should NOT drop END packets. This is because testing is made harder when END packets get dropped.

**Sender**
Note that the following requirements for your sender and requester are in addition to requirements stated for programming assignment 1.

Sender is invoked as followed:

```python3 sender.py -p <port> -g <requester port> -r <rate> -q <seq_no> -l <length> -f <f_hostname> -e <f_port> -i <priority> -t <timeout>```

- **f_hostname:** the host name of the emulator.
- **f_port:** the port of the emulator.
- **priority:** the priority of the sent packets.
- **timeout:** the timeout for retransmission for lost packets in the unit of milliseconds.
  
The behavior of the sender should be modified to:
1. Always start at sequence number 1
2. Increment the sequence number by 1 for each packet sent, instead of by the packet length
3. Print out the observed percentage of packets lost. The loss rate that the sender prints out is not necessarily the same as the loss rate that we identify in the forwarding table since the sender might miss some ACKs. This loss rate is computed by (number of retransmissions / total number of transmissions), where total number of transmissions including both normal transmissions and retransmissions.
4. The end packet is sent after ensuring that all data packets have been received by the receiver (or if max number of retries have reached for sending all packets in the last window).

**Requester**
Requester will be invoked as followed:

```python3 requester.py -p <port> -o <file option> -f <f_hostname> -e <f_port> -w <window>```

- **f_hostname:** the host name of the emulator.
- **f_port:** the port of the emulator.
- **window:** the requester's window size.

You will also have to modify your requester to:

1. The inner length field of the request packet will be filled with this window size so that the sender can extract and use this value for sending.
2. Verify that the destination IP address in the packet is indeed its own IP address, and
3. Suppress display of individual DATA packet information.
