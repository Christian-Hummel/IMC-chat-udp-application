#!/usr/bin/env python3

import socket
import sys
import threading
import time

DAEMON_PORT = 7777
CLIENT_PORT = 7778

# Daemon listens on Port 7777 and 7778 at the same time
    # if from other Daemon then get SYN
        # D1 sends SYN, D2 sends SYN+ACK, D3 sends ACK

    # if from client, send SYN

class ExampleDaemon:
    def __init__(self,ip_address):
        self.ip_address = ip_address
        self.DAEMON_PORT = 7777
        self.CLIENT_PORT = 7778
        self.daemon_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.host_address = ""
        self.receiver_address = ""
        self.daemon_sock.bind((self.ip_address,self.DAEMON_PORT))
        self.client_sock.bind((self.ip_address,self.CLIENT_PORT))
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


    def connection_request(self, msg, ip_address):

        if msg.decode() == "connectionrequest" and not self.client_connection:
            message = b'connected'
            self.host_address = ip_address
            self.client_sock.sendto(message, (ip_address, CLIENT_PORT))
            self.client_connection = True
            return True

        elif msg.decode() == "connectionrequest" and self.client_connection:
            error = b'This daemon is already connected to a client'
            self.client_sock.sendto(error, (ip_address, CLIENT_PORT))
            return False

        else:
            error = b'Connection request failed'
            self.client_sock.sendto(error, (ip_address, CLIENT_PORT))
            return False


    def handshake(self, message, address):

        if message == b'0x02' and not self.daemon_connection:
            self.daemon_sock.sendto(b'0x06',(address, DAEMON_PORT))
            # time.sleep(5)
            reply, _ = self.daemon_sock.recvfrom(1024)
            if reply == b'0x04':
                self.daemon_connection = True
                print(f"connection established as a receiver with {address}")



        elif message != b'0x02' and not self.daemon_connection:
            print(f" message {message} address {address}")
            self.daemon_sock.sendto(b'0x02', (address, DAEMON_PORT))
            # time.sleep(5)
            reply, _ = self.daemon_sock.recvfrom(1024)
            if reply == b'0x06':
                # time.sleep(5)
                self.daemon_sock.sendto(b'0x04', (address, DAEMON_PORT))
                self.daemon_connection = True
                print(f"connection established as a sender with {address}")



        elif message == b'0x02' and self.daemon_connection:
            # send error message - client busy
            # send FIN
            # continue
            pass


        elif message == b'0x08' and self.daemon_connection:
            # send FIN
            # timeout
            # self.connection = False
            pass

    def client_receive(self):

        message, _ = self.client_sock.recvfrom(1024)
        return message.decode()


    def client_message(self):
        pass

    def daemon_receive(self):

        message, _ = self.daemon_sock.recvfrom(1024)
        return message

    def daemon_message(self):
        pass




    def daemon_listen(self):
        print(f"Listening for messages from daemons on port 7777 ")


        if self.client_connection:

            while True:

                data , host_from = self.daemon_sock.recvfrom(1024)
                address, _ = host_from
                print('Connected by', host_from)
                print(address)
                if not data:
                    break
                print('Sending back data: ', data)
                self.handshake(data, address)
                print(f"connection status {self.daemon_connection}")

        elif self.shutdown:
            sys.exit()



    def client_listen(self):

        print("Listening for messages from clients on port 7778")



        data, host_from = self.client_sock.recvfrom(1024)
        address, _ = host_from

        if self.connection_request(data, address):

            self.client_username = self.client_receive()
            print(f"Username {self.client_username}")
            intro = b'Press 1 to start a new chat or 2 to wait for incoming chat requests'
            self.client_sock.sendto(intro, (self.host_address, CLIENT_PORT))

            user_choice = self.client_receive()
            if user_choice == "1":

                self.client_sock.sendto(user_choice.encode(), (self.host_address, CLIENT_PORT))
                ip_address = self.client_receive()
                print(f"User entered ip address: {ip_address}")
                sys.exit()

            elif user_choice == "2":

                self.client_sock.sendto(user_choice.encode(), (self.host_address, CLIENT_PORT))

                while True:
                    print("Waiting for now")
                    self.client_receive()

            else:

                error = b'Wrong input, please enter 1 to start a new chat or 2 to wait for incoming chat requests'
                self.client_sock.sendto(error, (self.host_address, CLIENT_PORT))





            # chat functionality
            # while True:
            #
            #     data, host_from = self.client_sock.recvfrom(1024)
            #
            #     if data.decode() == "!q":
            #         self.shutdown = True
            #         break
            #
            #     reply = data
            #
            #     print(f"sending reply {reply}")
            #     self.client_sock.sendto(reply, (self.host_address, CLIENT_PORT))
            #
            #     if not data:
            #         self.client_connection = False
            #         break







if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit(1)

    daemon = ExampleDaemon(sys.argv[1])
    daemon.start()



