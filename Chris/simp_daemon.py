import socket
import threading
import sys



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



class Daemon:
    def __init__(self, ip_address):
        self.ip_address = ip_address
        self.DAEMON_PORT = 7777
        self.CLIENT_PORT = 7778
        self.daemon_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.daemon_sock.bind((self.ip_address, self.DAEMON_PORT))
        self.client_sock.bind((self.ip_address, self.CLIENT_PORT))
        self.host_address = ""
        self.receiver_address = ""
        self.daemon_connection = False
        self.client_connection = False
        self.client_username = ""
        self.conn_wait = False
        self.chat_request = False
        self.shutdown = False
        self.ack = False
        self.sequence = 0
        self.resend = 0


    def start(self):

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

    def switch_sequence(self, sequence:bytes) -> int:

        if sequence == b'\x00':
            return 1
        else:
            return 0


    def format_message(self, message: str):

        if message == "!exit":

            fin = Datagram(type=1, operation=8, sequence=self.sequence, username=self.client_username)
            end = f"End conversation with {self.receiver_address}, press Enter to go to main menu or type !shutdown to exit program"
            self.daemon_sock.sendto(fin.bytearray(), (self.receiver_address, self.DAEMON_PORT))
            self.daemon_sock.sendto(end.encode("ascii"), (self.host_address, self.CLIENT_PORT))
            self.receiver_address = ""
            self.daemon_connection = False
            return None

        else:

            return Datagram(type=2, operation=1, sequence=self.sequence, username=self.client_username, payload=message)


    def receive_message(self, message: Datagram):


        # Send chat datagram to client and ACK to sender if operation is chat
        if message.type == b'\x02':

            ack = Datagram(type=1, operation=4, sequence=self.switch_sequence(message.sequence), username=self.client_username)

            message = b': '.join([message.username, message.payload])

            self.daemon_sock.sendto(message, (self.host_address, self.CLIENT_PORT))

            return ack

        # Control Datagram
        elif message.type == b'\x01':

            # Message of Type Error - send message to client and ACK to sender
            if message.operation == b'\x01':

                ack = Datagram(type=1, operation=4, sequence=self.switch_sequence(message.sequence),username=self.client_username)

                self.daemon_sock.sendto(message.payload, (self.host_address, self.CLIENT_PORT))

                return ack

            elif message.operation != b'\x01':

                return self.handshake(message)

    def client_receive(self):
        message, _ = self.client_sock.recvfrom(1024)
        return message.decode("ascii")


    def convert_client_input(self, command):

        if command.startswith(b'request_connection'):
            self.receiver_address = command.decode("ascii").split(" ")[1]
            if self.receiver_address != self.ip_address:

                return Datagram(type=1, operation=2, sequence=self.sequence, username=self.client_username)

            else:
                error = f"Already connected to daemon with address {self.ip_address}"
                self.daemon_sock.sendto(error.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                return False

        elif command == b'Wait':
            self.conn_wait = True
            return None

        elif self.conn_wait or self.chat_request:

            # send SYN + ACK if chat request accepted
            if command.upper() == b'Y':

                return Datagram(type=1, operation=6, sequence=self.sequence, username=self.client_username)


            # send FIN if chat request rejected
            if command.upper() == b'N':

                if self.chat_request:
                    self.chat_request = False

                fin = Datagram(type=1, operation=8, sequence=self.sequence, username=self.client_username)
                self.daemon_sock.sendto(fin.bytearray(), (self.receiver_address, self.DAEMON_PORT))
                self.receiver_address = ""
                self.conn_wait = False
                return None

            else:
                error = "Wrong input, please type Y to accept request or N to reject request"
                self.daemon_sock.sendto(error.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                return None


    # establish connection with client
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
                request = f"Connection Request from User {message.username.strip(b'x\00').decode("ascii")} on address {self.receiver_address}, accept? [Y/N]"
                self.daemon_sock.sendto(request.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                return None

            elif not self.conn_wait and not self.chat_request and message.operation == b'\x02':
                request = f"Pending Connection Request from User {message.username.strip(b'x\00').decode("ascii")} on address {self.receiver_address}, accept? [Y/N]"
                self.daemon_sock.sendto(request.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                self.chat_request = True
                return None

            elif self.conn_wait or self.chat_request and message.operation == b'\x04':

                if self.chat_request:
                    self.chat_request = False

                confirmation = f"Connected with {self.receiver_address}, type !exit to leave conversation"
                self.daemon_sock.sendto(confirmation.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                self.daemon_connection = True
                self.conn_wait = False

                return None

            elif not self.conn_wait and not self.chat_request and message.operation == b'\x04':

                return None

            elif message.operation == b'\x06':
                self.daemon_connection = True
                confirmation = f"Connected with {self.receiver_address}, please enter your message, type !exit to leave conversation"
                self.daemon_sock.sendto(confirmation.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                return Datagram(type=1, operation=4, sequence=self.switch_sequence(message.sequence), username=self.client_username)

            # If FIN gets received, send error message to client and ACK to daemon of receiver
            elif message.operation == b'\x08':
                ack = Datagram(type=1, operation=4, sequence=self.switch_sequence(message.sequence), username=self.client_username)
                error = f"User with address {self.receiver_address}, declined your request, press enter to get back to main menu type !shutdown to exit program"
                self.daemon_sock.sendto(error.encode("ascii"), (self.host_address, self.CLIENT_PORT))

                self.daemon_sock.sendto(ack.bytearray(), (self.receiver_address, self.DAEMON_PORT))
                self.receiver_address = ""
                return None


            elif message.operation == b'\x01':
                self.daemon_sock.sendto(message.payload, (self.host_address, self.CLIENT_PORT))
                return None


        elif self.daemon_connection:


            if message.operation == b'\x02':

                return Datagram(type=1, operation=8, sequence=self.switch_sequence(message.sequence), username=self.client_username), Datagram(type=1, operation=1, sequence=self.switch_sequence(message.sequence), username=self.client_username, payload="git y in another chat")


            elif message.operation == b'\x04':
                pass


            elif message.operation == b'\x08':

                ack = Datagram(type=1, operation=4, sequence=self.switch_sequence(message.sequence), username=self.client_username)
                information = f"User {message.username.strip(b'x\00').decode("ascii")} ended conversation, press enter to go to main menu or type !shutdown to exit program"
                self.daemon_sock.sendto(information.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                self.daemon_sock.sendto(ack.bytearray(), (self.receiver_address, self.DAEMON_PORT))

                self.receiver_address = ""
                self.daemon_connection = False

                return None


    def check_acknowledged(self, message1: Datagram, message2: Datagram, address):

        # check for current chat user, control datagram type and ACK operation and for different sequence number
        if message2.type == b'\x01' and message2.operation == b'\x04' and message1.sequence != message2.sequence and address == self.receiver_address:

            if self.sequence == 0:
                self.sequence = 1
            else:
                self.sequence = 0

            # reset timeout to wait for response from receiver
            self.daemon_sock.settimeout(None)

            return True

        else:
            return False





    def handle_chat_request(self):

        while True:

            if self.chat_request and not self.daemon_connection:

                message = self.client_receive()

                self.client_sock.sendto(message.encode("ascii"), (self.ip_address, self.DAEMON_PORT))

            elif self.daemon_connection:


                data = self.client_receive()



                if data == "!shutdown":
                    self.client_sock.sendto(data.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                    self.shutdown = True

                self.client_sock.sendto(data.encode("ascii"), (self.ip_address, self.DAEMON_PORT))

            elif not self.chat_request and not self.daemon_connection:
                break


    def daemon_listen(self):


        while not self.shutdown:

            data, host_from = self.daemon_sock.recvfrom(1024)
            address, _ = host_from


            if not self.daemon_connection:

                # message from Client
                if address == self.ip_address:

                    response = self.convert_client_input(data)


                    if response:

                        self.daemon_sock.sendto(response.bytearray(), (self.receiver_address, self.DAEMON_PORT))

                    else:
                        continue



                # message from other Daemon
                else:

                    if not self.receiver_address:
                        self.receiver_address = address


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
                        self.ack = False
                        self.resend = 0


                        if not self.ack:
                            self.daemon_sock.settimeout(5)
                            try:

                                data, host_from = self.daemon_sock.recvfrom(1024)
                                address, _ = host_from

                                if self.check_acknowledged(message,self.format_data(data), address):
                                    self.ack = True


                            except self.daemon_sock.timeout:

                                if self.resend < 4:
                                    self.resend += 1
                                    self.daemon_sock.sendto(message.bytearray(), (self.receiver_address, self.DAEMON_PORT))

                                self.receiver_address = ""
                                self.daemon_connection = False


                # message from connected chat user daemon
                elif address == self.receiver_address:


                    response = self.receive_message(self.format_data(data))

                    if response:

                        self.daemon_sock.sendto(response.bytearray(), (self.receiver_address, self.DAEMON_PORT))


                    else:
                        continue

                else:

                    # block for handling incoming requests while occupied
                    self.handshake(self.format_data(data))


        # close socket if self.shutdown gets switched
        self.daemon_sock.close()


    def client_listen(self):

        data, host_from = self.client_sock.recvfrom(1024)
        address, _ = host_from

        if self.connection_request(data, address):
            user_request = b'Please enter your username'
            self.client_sock.sendto(user_request, (self.host_address, self.CLIENT_PORT))
            while not self.client_username:


                username = self.client_receive()
                if len(username) < 33:
                    self.client_username = username

                else:
                    error = b'Invalid username, please insert a username with a maximum of 32 characters'
                    self.client_sock.sendto(error, (self.host_address, self.CLIENT_PORT))
                    continue


            if self.chat_request:

                self.handle_chat_request()

            while True:

                options = b'Press 1 to start a new chat or 2 to wait for incoming chat requests'
                self.client_sock.sendto(options, (self.host_address, self.CLIENT_PORT))

                # capture user input
                user_choice = self.client_receive()

                if user_choice == "1":

                    ip_request = b'Please enter IP address to connect to'

                    self.client_sock.sendto(ip_request, (self.host_address, self.CLIENT_PORT))

                    daemon_address = self.client_receive()
                    self.receiver_address = daemon_address


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


                        if self.daemon_connection:

                            if self.receiver_address:

                                message = self.client_receive()

                                if message == "!shutdown":
                                    self.client_sock.sendto(message.encode("ascii"),(self.host_address, self.CLIENT_PORT))
                                    self.shutdown = True


                                self.client_sock.sendto(message.encode("ascii"), (self.ip_address, self.DAEMON_PORT))


                                # Send datagram class in form of bytes to other Daemon
                                # self.client_sock.sendto(datagram1.bytearray(), (self.ip_address, self.DAEMON_PORT))


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

                            if data == "!shutdown":
                                self.client_sock.sendto(data.encode("ascii"), (self.host_address, self.CLIENT_PORT))
                                self.shutdown = True

                            self.client_sock.sendto(data.encode("ascii"), (self.ip_address, self.DAEMON_PORT))


                else:

                    error = b'Wrong input'
                    self.client_sock.sendto(error, (self.host_address, self.CLIENT_PORT))





if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit(1)

    daemon = Daemon(sys.argv[1])
    daemon.start()



