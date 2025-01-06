import socket
import sys
import threading


# ljust(32, b'0x00') - function to pad username field with zero bytes until 32 is reached
class Datagram:
    def __init__(self, type, sequence, username, payload=None, operation=None):
        # type conditions
        if type == 1:
            self.type = int.to_bytes(1, 1, byteorder="big")
        elif type == 2:
            self.type = int.to_bytes(2, 1, byteorder="big")
        # sequence conditions
        if sequence == 0:
            self.sequence = int.to_bytes(0, 1, byteorder='big')
        elif sequence == 1:
            self.sequence = int.to_bytes(1, 1, byteorder='big')
        # operation conditions
        if operation != None:
            self.operation = operation.to_bytes(1, byteorder='big')
        else:
            self.operation = int(1).to_bytes(1, byteorder='big')
        # username format
        self.username = username.encode("ascii").ljust(32, int(0).to_bytes(1, byteorder='big'))
        # payload conditions
        if payload != None:
            self.payload = payload.encode("ascii")
            self.length = int.to_bytes(len(payload), 4, byteorder='big')
        else:
            self.payload = b""
        # calculate length of payload
        self.length = len(self.payload).to_bytes(1, byteorder='big')

    def __repr__(self):
        return "".join([str(self.type), str(self.operation), str(self.sequence), str(self.username), str(self.payload)])

    def bytearray(self):
        return b''.join([self.type, self.operation, self.sequence, self.username, self.length, self.payload])


datagram1 = Datagram(type=2, operation=1, sequence=0, username="Chris", payload="Test_message")


class ExampleDaemon:
    def __init__(self, ip_address):
        self.ip_address = ip_address
        self.DAEMON_PORT = 7777
        self.CLIENT_PORT = 7778
        self.daemon_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host_address = ""
        self.receiver_address = ""
        self.daemon_sock.bind((self.ip_address, self.DAEMON_PORT))
        self.client_sock.bind((self.ip_address, self.CLIENT_PORT))
        self.daemon_connection = False
        self.client_connection = False
        self.client_username = ""
        self.idle = False
        self.shutdown = False

    def start(self):
        print(f"Daemon running at {self.ip_address}")
        daemon_thread = threading.Thread(target=self.daemon_listen)
        client_thread = threading.Thread(target=self.client_listen)

        daemon_thread.start()
        client_thread.start()

        daemon_thread.join()
        client_thread.join()

    # convert bytes to datagram instance
    def format_data(self, bytes) -> Datagram:
        type = bytes[0]
        operation = bytes[1]
        sequence = bytes[2]
        username = bytes[3:33].strip(b'\x00').decode('ascii')
        payload = bytes[36:].decode('ascii')

        return Datagram(type=type, operation=operation, sequence=sequence, username=username, payload=payload)

    def client_receive(self):
        message, _ = self.client_sock.recvfrom(1024)
        return message.decode("ascii")

    # function to handle incoming datagrams on daemon port
    def daemon_receive(self, message, address):

        if not self.daemon_connection:
            # message from Client
            if address == self.ip_address:
                self.handshake(message, address)
            # message from other Daemon
            else:
                message = self.format_data(message)
                self.handshake(message, address)


        # check if message is coming from client or daemon and forward it
        elif self.daemon_connection:
            print(f"chat connection with {self.receiver_address}, address: {address}")

            # message coming from connected client - send to receiver
            if address == self.ip_address:
                if message == b'!exit':
                    self.handshake(message, address)
                else:
                    self.daemon_sock.sendto(message, (self.receiver_address, self.DAEMON_PORT))

            # message coming from connected daemon - send to client
            elif address == self.receiver_address:

                if len(message) < 22:
                    self.daemon_sock.sendto(message, (self.host_address, self.CLIENT_PORT))

                elif len(message) > 21:
                    message = self.format_data(message)
                    self.handshake(message, address)

    def connection_request(self, msg, ip_address):

        if msg.decode() == "connectionrequest" and not self.client_connection:
            message = b'connected'
            self.host_address = ip_address
            self.client_sock.sendto(message, (ip_address, self.CLIENT_PORT))
            self.client_connection = True
            return True

        elif msg.decode() == "connectionrequest" and self.client_connection:
            error = b'This daemon is already connected to a client'
            self.client_sock.sendto(error, (ip_address, self.CLIENT_PORT))
            return False

        else:
            error = b'Connection request failed'
            self.client_sock.sendto(error, (ip_address, self.CLIENT_PORT))
            return False

    def handshake(self, message, address):

        if not self.daemon_connection:

            if not isinstance(message, Datagram):
                if message.startswith(b'request_connection'):
                    daemon_address = message.decode("ascii").split(" ")[1]
                    if daemon_address != self.ip_address:
                        print(f"receiver address {self.receiver_address}")
                        syn = Datagram(type=1, operation=2, sequence=0, username=self.client_username).bytearray()
                        self.daemon_sock.sendto(syn, (daemon_address, self.DAEMON_PORT))
                    else:
                        error = f"Already connected to daemon with address {self.ip_address}"
                        self.daemon_sock.sendto(error.encode("ascii"), (self.host_address, self.CLIENT_PORT))


                elif message == b'Wait':
                    self.idle = True

                elif message.upper() == b'Y':
                    syn_ack = Datagram(type=1, operation=6, sequence=0, username=self.client_username).bytearray()
                    self.daemon_sock.sendto(syn_ack, (self.receiver_address, self.DAEMON_PORT))
                    print(f"Sending back ACK + SYN")

                elif message.upper() == b'N':
                    fin = Datagram(type=1, operation=8, sequence=0, username=self.client_username).bytearray()
                    self.daemon_sock.sendto(fin, (self.receiver_address, self.DAEMON_PORT))
                    print(f"Sending back FIN")
                    self.receiver_address = ""


                elif message == b'!shutdown':
                    print("received shutdown in handshake")
                    self.shutdown = True


            elif isinstance(message, Datagram):

                if self.idle and message.operation == b'\x02':
                    print("syn received")
                    request = f"Connection Request from {address}, accept? [Y/N]"
                    self.daemon_sock.sendto(request.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                    self.receiver_address = address

                elif message.operation == b'\x06':
                    print(f" message {message} address {address}")
                    ack = Datagram(type=1, operation=4, sequence=0, username=self.client_username).bytearray()
                    self.daemon_sock.sendto(ack, (address, self.DAEMON_PORT))
                    print(f"Sending back {ack}")
                    self.daemon_connection = True
                    confirmation = f"Connected with {address}, please enter your message, type !exit to leave conversation"
                    self.daemon_sock.sendto(confirmation.encode("ascii"), (self.host_address, self.CLIENT_PORT))

                elif self.receiver_address and message.operation == b'\x04':
                    self.daemon_connection = True
                    self.receiver_address = address
                    confirmation = f"Connected with {address}, type !exit to leave conversation"
                    self.daemon_sock.sendto(confirmation.encode("ascii"), (self.host_address, self.CLIENT_PORT))

                elif message.operation == b'\x08':
                    error = f"User with {address}, declined your request"
                    self.daemon_sock.sendto(error.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                    ack = Datagram(type=1, operation=4, sequence=0, username=self.client_username).bytearray()
                    self.daemon_sock.sendto(ack, (address, self.DAEMON_PORT))
                    self.receiver_address = ""


        elif self.daemon_connection:

            if not isinstance(message, Datagram):

                # receive exit command from active chat
                if message == b'!exit':
                    fin = Datagram(type=1, operation=8, sequence=0, username=self.client_username).bytearray()
                    end = f"End conversation with {self.receiver_address}, press Enter to go to main menu or type !shutdown to exit program"
                    self.daemon_sock.sendto(fin, (self.receiver_address, self.DAEMON_PORT))
                    self.daemon_sock.sendto(end.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                    self.receiver_address = ""
                    self.daemon_connection = False
                    print(f"Sending FIN to end conversation")



            elif isinstance(message, Datagram):

                if message.operation == b'\x02':
                    error = Datagram(type=1, operation=1, sequence=0, username=self.client_username, payload="User already in another chat").bytearray()
                    fin = Datagram(type=1, operation=8, sequence=0, username=self.client_username).bytearray()
                    self.daemon_sock.sendto(fin, (address, self.DAEMON_PORT))
                    self.daemon_sock.sendto(error, (address, self.DAEMON_PORT))

                elif message.operation == b'\x04':
                    self.daemon_connection = False


                elif message.operation == b'\x08':
                    print("received FIN")
                    ack = Datagram(type=1, operation=4, sequence=0, username=self.client_username).bytearray()
                    print("Sending back ACK")
                    information = "User ended conversation, press enter to go to main menu or type !shutdown to exit program"
                    self.daemon_sock.sendto(information.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                    self.daemon_sock.sendto(ack, (address, self.DAEMON_PORT))
                    self.receiver_address = ""
                    self.daemon_connection = False

    def daemon_listen(self):
        print(f"Listening for messages from daemons on port 7777 ")

        while not self.shutdown:

            data, host_from = self.daemon_sock.recvfrom(1024)
            address, _ = host_from
            print(f'Message from {address}: {data}')


            self.daemon_receive(data, address)

        # close socket if self.shutdown gets switched
        self.daemon_sock.close()


    def client_listen(self):

        print("Listening for messages from clients on port 7778")

        data, host_from = self.client_sock.recvfrom(1024)
        address, _ = host_from
        print(f"host_address = {address}")

        if self.connection_request(data, address):

            user_request = b'Please enter your username'
            self.client_sock.sendto(user_request, (self.host_address, self.CLIENT_PORT))
            username = self.client_receive()
            print(f"username {username}")
            self.client_username = username

            while not self.shutdown:


                options = b'Press 1 to start a new chat or 2 to wait for incoming chat requests'
                self.client_sock.sendto(options, (self.host_address, self.CLIENT_PORT))

                # capture user input
                user_choice = self.client_receive()

                if user_choice == "1":

                    ip_request = b'Please enter IP address to connect to'

                    self.client_sock.sendto(ip_request, (self.host_address, self.CLIENT_PORT))

                    daemon_address = self.client_receive()
                    self.receiver_address = daemon_address

                    print(f"User entered ip address: {daemon_address}")

                    request = f"request_connection {daemon_address}"

                    self.client_sock.sendto(request.encode("ascii"), (self.ip_address, self.DAEMON_PORT))

                    while True:

                        if not self.daemon_connection and self.receiver_address:

                            message = self.client_receive()
                            print(f"message received: {message}")
                            self.client_sock.sendto(message.encode("ascii"), (self.ip_address, self.DAEMON_PORT))

                        elif not self.daemon_connection and not self.receiver_address:
                            break


                        elif self.daemon_connection:

                            if self.receiver_address:

                                message = self.client_receive()

                                print(f"received as sender {message}")

                                if message == "!shutdown":
                                    self.client_sock.sendto(message.encode("ascii"),(self.host_address, self.CLIENT_PORT))
                                    self.shutdown = True


                                self.client_sock.sendto(message.encode("ascii"), (self.ip_address, self.DAEMON_PORT))

                                # Send datagram class in form of bytes to other Daemon
                                # self.client_sock.sendto(datagram1.bytearray(), (self.ip_address, self.DAEMON_PORT))

                            elif not self.receiver_address:
                                break

                elif user_choice == "2":

                    client_information = b'Waiting for incoming chat requests, please wait or press q to exit'

                    self.client_sock.sendto(client_information, (self.host_address, self.CLIENT_PORT))

                    self.client_sock.sendto(b'Wait', (self.ip_address, self.DAEMON_PORT))

                    while True:

                        if self.idle:

                            data = self.client_receive()

                            if data.upper() == "Y":
                                self.idle = False

                            if data.upper() == "N":
                                self.client_sock.sendto(data.encode("ascii"), (self.ip_address, self.DAEMON_PORT))
                                break

                            self.client_sock.sendto(data.encode("ascii"), (self.ip_address, self.DAEMON_PORT))

                        elif not self.daemon_connection and not self.receiver_address:
                            break


                        elif self.daemon_connection:

                            data = self.client_receive()
                            print(f"received as receiver {data}")

                            if data == "!shutdown":
                                self.client_sock.sendto(data.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                                self.shutdown = True


                            self.client_sock.sendto(data.encode("ascii"), (self.ip_address, self.DAEMON_PORT))


                else:

                    error = b'Wrong input'
                    self.client_sock.sendto(error, (self.host_address, self.CLIENT_PORT))
                    continue

        # close socket if self.shutdown gets switched
        self.client_sock.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit(1)

    daemon = ExampleDaemon(sys.argv[1])
    daemon.start()



