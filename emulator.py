from optparse import OptionParser

port, queue_size, file_name, log = None, None, None, None

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
    
if __name__ == "__main__":
    main()