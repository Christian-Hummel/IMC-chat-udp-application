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
        self.conn_wait = False
        self.shutdown = False
        self.ack = False
        self.sequence = 0

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


    def format_message(self, message: str):


        if message == "!exit":
            print("exit command received")
            fin = Datagram(type=1, operation=8, sequence=0, username=self.client_username)
            end = f"End conversation with {self.receiver_address}, press Enter to go to main menu or type !shutdown to exit program"
            self.daemon_sock.sendto(fin.bytearray(), (self.receiver_address, self.DAEMON_PORT))
            self.daemon_sock.sendto(end.encode("ascii"), (self.host_address, self.CLIENT_PORT))
            self.receiver_address = ""
            self.daemon_connection = False
            return None

        else:

            return Datagram(type=2, operation=1, sequence=0, username=self.client_username, payload=message)


    def receive_message(self, message: Datagram):


        # Send chat datagram to client
        if message.type == b'\x02':

            message = b': '.join([message.username, message.payload])

            self.daemon_sock.sendto(message, (self.host_address, self.CLIENT_PORT))

            return None

        # Control Datagram
        elif message.type == b'\x01':

            # Message of Type Error
            if message.operation == b'\x01':

                self.daemon_sock.sendto(message.payload, (self.host_address, self.CLIENT_PORT))

                return None

            elif message.operation != b'\x01':

                return self.handshake(message)

    def client_receive(self):
        message, _ = self.client_sock.recvfrom(1024)
        return message.decode("ascii")


    def convert_client_input(self, command):


        if command.startswith(b'request_connection'):
            self.receiver_address = command.decode("ascii").split(" ")[1]
            if self.receiver_address != self.ip_address:
                print(f"receiver address {self.receiver_address}")
                return Datagram(type=1, operation=2, sequence=0, username=self.client_username)

            else:
                error = f"Already connected to daemon with address {self.ip_address}"
                self.daemon_sock.sendto(error.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                return False

        elif command == b'Wait':
            self.conn_wait = True
            return None

        elif self.conn_wait:

            # send SYN + ACK if chat request accepted
            if command.upper() == b'Y':
                return Datagram(type=1, operation=6, sequence=0, username=self.client_username)

            # send FIN if chat request rejected
            if command.upper() == b'N':
                fin = Datagram(type=1, operation=8, sequence=0, username=self.client_username)
                self.daemon_sock.sendto(fin.bytearray(), (self.receiver_address, self.DAEMON_PORT))
                self.receiver_address = ""
                self.conn_wait = False
                return None

            else:
                error = "Wrong input, please type Y to accept request or N to reject request"
                self.daemon_sock.sendto(error.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                return None







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

    def handshake(self, message:Datagram):

        if not self.daemon_connection:

            if self.conn_wait and message.operation == b'\x02':
                print("syn received")
                request = f"Connection Request from User {message.username.strip(b'x\00').decode("ascii")} on address {self.receiver_address}, accept? [Y/N]"
                self.daemon_sock.sendto(request.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                return None

            elif self.conn_wait and message.operation == b'\x04':
                print("received ack")
                confirmation = f"Connected with {self.receiver_address}, type !exit to leave conversation"
                self.daemon_sock.sendto(confirmation.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                self.daemon_connection = True
                self.conn_wait = False
                return None

            elif message.operation == b'\x06':
                print(f" message {message} address {self.receiver_address}")
                print(f"Sending back ACK")
                self.daemon_connection = True
                confirmation = f"Connected with {self.receiver_address}, please enter your message, type !exit to leave conversation"
                self.daemon_sock.sendto(confirmation.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                return Datagram(type=1, operation=4, sequence=0, username=self.client_username)

            # If FIN gets received, send error message to client and ACK to daemon of receiver
            elif message.operation == b'\x08':
                ack = Datagram(type=1, operation=4, sequence=0, username=self.client_username)
                error = f"User with address {self.receiver_address}, declined your request, press enter to get back to main menu type !shutdown to exit program"
                self.daemon_sock.sendto(error.encode("ascii"), (self.host_address, self.CLIENT_PORT))

                self.daemon_sock.sendto(ack.bytearray(), (self.receiver_address, self.DAEMON_PORT))
                self.receiver_address = ""
                return None


        elif self.daemon_connection:


            if message.operation == b'\x02':
                # error should not be sent by receiver of this datagram,
                # will be forwarded by the sender daemon to the corresponding client
                #error = Datagram(type=1, operation=1, sequence=0, username=self.client_username, payload="User already in another chat").bytearray()
                #self.daemon_sock.sendto(error, (address, self.DAEMON_PORT))
                return Datagram(type=1, operation=8, sequence=0, username=self.client_username).bytearray()


            elif message.operation == b'\x04':
                print("ack while connection")


            elif message.operation == b'\x08':
                print("received FIN")
                print("Sending back ACK")

                information = f"User {message.username.strip(b'x\00').decode("ascii")} ended conversation, press enter to go to main menu or type !shutdown to exit program"
                self.daemon_sock.sendto(information.encode("ascii"), (self.host_address, self.CLIENT_PORT))

                self.receiver_address = ""
                self.daemon_connection = False

                return Datagram(type=1, operation=4, sequence=0, username=self.client_username)


    def daemon_listen(self):
        print(f"Listening for messages from daemons on port 7777 ")

        while not self.shutdown:

            data, host_from = self.daemon_sock.recvfrom(1024)
            address, _ = host_from
            print(f'Message from {address}: {data}')

            if not self.daemon_connection:


                # message from Client
                if address == self.ip_address:

                    response = self.convert_client_input(data)
                    print(f"response {response}")

                    if response:

                        self.daemon_sock.sendto(response.bytearray(), (self.receiver_address, self.DAEMON_PORT))

                    else:
                        continue



                # message from other Daemon
                else:

                    if not self.receiver_address:
                        self.receiver_address = address


                    #self.handshake(data)

                    response = self.handshake(self.format_data(data))

                    if response:
                        self.daemon_sock.sendto(response.bytearray(), (self.receiver_address, self.DAEMON_PORT))

                    else:
                        continue

            elif self.daemon_connection:

                # message from Client
                if address == self.ip_address:

                    # check for chat message or exit command
                    message = self.format_message(data.decode("ascii"))

                    # if no exit command - send chat message to receiver
                    if message:

                        self.daemon_sock.sendto(message.bytearray(), (self.receiver_address, self.DAEMON_PORT))

                # message from connected chat user daemon
                elif address == self.receiver_address:

                    response = self.receive_message(self.format_data(data))

                    if response:
                        self.daemon_sock.sendto(response.bytearray(), (self.receiver_address, self.DAEMON_PORT))

                    else:
                        continue

                else:

                    # block for handling incoming requests while occupied
                    print("incoming request while busy")



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


                        if not self.receiver_address:
                            break

                        elif self.receiver_address:

                            message = self.client_receive()

                            if message == "!shutdown":
                                self.client_sock.sendto(message.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                                self.shutdown = True

                            self.client_sock.sendto(message.encode("ascii"), (self.ip_address, self.DAEMON_PORT))


                        elif self.daemon_connection:

                            if self.receiver_address:

                                message = self.client_receive()

                                print(f"received as sender {message}")
                                # needs adjustment as well - this block should only be reached
                                # if there is no daemon_connection
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

                    self.conn_wait = True

                    while True:

                        if self.conn_wait:

                            data = self.client_receive()

                            if data.upper() == "Y":
                                self.client_sock.sendto(data.encode("ascii"), (self.ip_address, self.DAEMON_PORT))

                            if data.upper() == "N":
                                self.client_sock.sendto(data.encode("ascii"), (self.ip_address, self.DAEMON_PORT))
                                break

                            self.client_sock.sendto(data.encode("ascii"), (self.ip_address, self.DAEMON_PORT))


                        elif not self.conn_wait and not self.receiver_address:
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


        # close socket if self.shutdown gets switched
        self.client_sock.close()



# concept for stop and wait in daemon listen
#
# while not self.shutdown:
#
#     if not self.daemon_connection:
#
#         # message from Client
#         if address == self.ip_address:
#             self.handshake(message, address)
#         # message from other Daemon
#         else:
#             message = self.format_data(message)
#             self.handshake(message, address)
#
#
#     elif self.daemon_connection:
#
#
#     data, host_from = self.daemon_sock.recvfrom(1024)
#     address, _ = host_from
#     print(f'Message from {address}: {data}')
#
#     response = self.build_message()
#
#
#     acknowledged = False
#
#     while not acknowledged:
#         try:
#             if response:
#
#                 self.daemon.sock.sendto(response, (self.receiver_address, self.DAEMON_PORT))
#
#             else:
#                 continue
#
#         except socket.timeout:
#
#             if resend_count < 0:
#
#                 self.daemon_sock.sendto(response, (self.receiver_address, self.DAEMON_PORT))
#
#             elif resend_count == 3:
#
#                 send error message to client
#                 clear self.receiver_address
#                 self.daemon_connection = False
#
#
# self.daemon_sock.close()





if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit(1)

    daemon = ExampleDaemon(sys.argv[1])
    daemon.start()



