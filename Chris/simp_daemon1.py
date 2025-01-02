import socket
import sys
import threading
import time


class Datagram:
    def __init__(self, type, operation, sequence, payload):
        if type== 1:
            self.type = int.to_bytes(1, 1, byteorder="big")
            self.operation = int.to_bytes(operation, 1, byteorder="big")
        if type == 2:
            self.type = int.to_bytes(2, 1, byteorder="big")
            self.operation = int.to_bytes(1, 1, byteorder="big")
        if sequence == 0:
            self.sequence = int.to_bytes(0, 1, byteorder='big')
        elif sequence == 1:
            self.sequence = int.to_bytes(1, 1, byteorder='big')
        self.length = int.to_bytes(len(payload), 4, byteorder='big')
        if type == 1 and operation == 1:
            self.payload = payload.encode("ascii")
        else:
            self.payload = payload

    def __repr__(self):
        return b''.join([self.type, self.operation, self.sequence, self.length, self.payload])



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

    def client_receive(self):
        message, _ = self.client_sock.recvfrom(1024)
        return message.decode("ascii")


    def daemon_receive(self, message, address):

        if not self.daemon_connection:
            self.handshake(message, address)


        # check if message is coming from client or daemon and forward it
        elif self.daemon_connection:
            print(f"chat connection with {self.receiver_address}, address: {address}")
            if address == self.host_address:
                self.daemon_sock.sendto(message, (self.receiver_address, self.DAEMON_PORT))

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

            if message == b'0x02':
                self.daemon_sock.sendto(b'0x06', (address, self.DAEMON_PORT))
                print(f"Sending back ACK + SYN")


            elif message == b'0x06':
                print(f" message {message} address {address}")
                reply = b'0x04'
                self.daemon_sock.sendto(reply, (address, self.DAEMON_PORT))
                print(f"Sending back {reply}")
                self.daemon_connection = True
                self.receiver_address = address
                print(f"connection established as a sender with {address}")


            elif message == b'0x04':
                self.daemon_connection = True
                self.receiver_address = address
                print(f"connection established as a receiver with {address}")


        elif self.daemon_connection:

            if message == b'0x02':
                error = b'User already in another chat'
                fin = b'0x08'
                self.daemon_sock.sendto(fin, (address, self.DAEMON_PORT))

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

                    msg = b'0x02'
                    self.daemon_sock.sendto(msg, (daemon_address, self.DAEMON_PORT))
                    while True:

                        message = self.client_receive()

                        if self.daemon_connection:

                            self.client_sock.sendto(message.encode(), (self.ip_address, self.DAEMON_PORT))
                            print(self.client_receive())

                        elif not self.daemon_connection:
                            break


                elif user_choice == "2":

                    client_information = b'Waiting for incoming chat requests, please wait or press q to exit'

                    self.client_sock.sendto(client_information, (self.host_address, self.CLIENT_PORT))

                    while True:

                        if self.daemon_connection:
                            print(f"Connected to {self.receiver_address}")
                            print(self.client_receive())
                            response = input("Enter your message: ")
                            self.client_sock.sendto(response.encode(), (self.ip_address, self.DAEMON_PORT))

                        elif self.client_receive() == "Exit":
                            self.shutdown = True
                            break

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



