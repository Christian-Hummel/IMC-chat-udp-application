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
        self.daemon_sock.bind((self.ip_address, self.DAEMON_PORT))
        self.client_sock.bind((self.ip_address, self.CLIENT_PORT))
        self.daemon_connection = False
        self.client_connection = False
        self.client_username = ""
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
        pass

    def client_receive(self):
        message, _ = self.client_sock.recvfrom(1024)
        return message.decode("ascii")

    def daemon_receive(self, message, address):

        if not self.daemon_connection:
            self.handshake(message, address)


        # check if message is coming from client or daemon and forward it
        elif self.daemon_connection:
            print(f"chat connection with {self.receiver_address}, address: {address}")

            # message coming from connected client - send to receiver
            if address == self.ip_address:
                self.daemon_sock.sendto(message, (self.receiver_address, self.DAEMON_PORT))

            # message coming from connected daemon - send to client
            elif address == self.receiver_address:
                self.daemon_sock.sendto(message, (self.host_address, self.CLIENT_PORT))

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

            if message.startswith(b'request_connection'):
                daemon_address = message.decode("ascii").split(" ")[1]
                self.daemon_sock.sendto(b'0x02', (daemon_address, self.DAEMON_PORT))

            elif message == b'0x02':
                self.daemon_sock.sendto(b'0x06', (address, self.DAEMON_PORT))
                print(f"Sending back ACK + SYN")


            elif message == b'0x06':
                print(f" message {message} address {address}")
                reply = b'0x04'
                self.daemon_sock.sendto(reply, (address, self.DAEMON_PORT))
                print(f"Sending back {reply}")
                self.daemon_connection = True
                self.receiver_address = address
                confirmation = f"Connected with {address}, please enter your message"
                self.daemon_sock.sendto(confirmation.encode("ascii"), (self.host_address, self.CLIENT_PORT))


            elif message == b'0x04':
                self.daemon_connection = True
                self.receiver_address = address
                confirmation = f"Connected with {address}"
                self.daemon_sock.sendto(confirmation.encode("ascii"), (self.host_address, self.CLIENT_PORT))


        elif self.daemon_connection:

            if message == b'0x02':
                error = b'User already in another chat'
                fin = b'0x08'
                self.daemon_sock.sendto(fin, (address, self.DAEMON_PORT))
                self.daemon_sock.sendto(error, (address, self.DAEMON_PORT))

            elif message == b'0x04':
                self.client_sock.settimeout(5.0)
                self.daemon_connection = False


            elif message == b'0x08':
                ack = b'0x04'
                self.daemon_sock.sendto(ack, (address, self.DAEMON_PORT))
                self.client_sock.settimeout(5.0)
                self.daemon_connection = False

    def daemon_listen(self):
        print(f"Listening for messages from daemons on port 7777 ")

        while True:

            data, host_from = self.daemon_sock.recvfrom(1024)
            address, _ = host_from
            print(f'Message from {address}: {data}')

            if data == b'quit':
                break

            self.daemon_receive(data, address)

        print(f"Closing")
        self.shutdown = True

    def client_listen(self):

        print("Listening for messages from clients on port 7778")

        data, host_from = self.client_sock.recvfrom(1024)
        address, _ = host_from
        print(f"host_address = {address}")

        if self.connection_request(data, address):

            user_request = b'Please enter your username'
            self.client_sock.sendto(user_request, (self.host_address, self.CLIENT_PORT))
            username = self.client_receive()
            print(username)
            self.client_username = username
            options = b'Press 1 to start a new chat or 2 to wait for incoming chat requests'
            self.client_sock.sendto(options, (self.host_address, self.CLIENT_PORT))

            while True:

                # capture user input
                user_choice = self.client_receive()

                if user_choice == "1":

                    ip_request = b'Please enter IP address to connect to'

                    self.client_sock.sendto(ip_request, (self.host_address, self.CLIENT_PORT))

                    daemon_address = self.client_receive()

                    print(f"User entered ip address: {daemon_address}")

                    request = f"request_connection {daemon_address}"

                    self.client_sock.sendto(request.encode("ascii"), (self.ip_address, self.DAEMON_PORT))

                    while True:

                        if self.daemon_connection:
                            message = self.client_receive()
                            #self.client_sock.sendto(message.encode("ascii"), (self.ip_address, self.DAEMON_PORT))

                            # Send datagram class in form of bytes to other Daemon
                            #self.client_sock.sendto(datagram1.bytearray(), (self.ip_address, self.DAEMON_PORT))




                elif user_choice == "2":

                    client_information = b'Waiting for incoming chat requests, please wait or press q to exit'

                    self.client_sock.sendto(client_information, (self.host_address, self.CLIENT_PORT))

                    self.client_sock.sendto(b'Wait', (self.ip_address, self.DAEMON_PORT))

                    while True:

                        if self.daemon_connection:

                            data = self.client_receive()
                            print(data)

                            if data == "exit":
                                self.shutdown = True
                                break

                            self.client_sock.sendto(data.encode("ascii"), (self.ip_address, self.DAEMON_PORT))

                    print("outside loop")
                    break


                else:

                    error = b'Wrong input, please enter 1 to start a new chat or 2 to wait for incoming chat requests'
                    self.client_sock.sendto(error, (self.host_address, self.CLIENT_PORT))

                self.shutdown = True

                print("outside all loops")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit(1)

    daemon = ExampleDaemon(sys.argv[1])
    daemon.start()



