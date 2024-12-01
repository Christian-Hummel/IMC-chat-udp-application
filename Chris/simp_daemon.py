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
        self.daemon_sock.bind((self.ip_address,self.DAEMON_PORT))
        self.client_sock.bind((self.ip_address,self.CLIENT_PORT))
        self.connection = 0

    def start(self):
        print(f"Daemon running at {self.ip_address}")
        daemon_thread = threading.Thread(target=self.daemon_listen)
        client_thread = threading.Thread(target=self.client_listen)


        daemon_thread.start()
        client_thread.start()

        daemon_thread.join()
        client_thread.join()


    def daemon_listen(self):
        print(f"Listening for messages from daemons on port 7777 ")

        while True:
            data , host_from = self.daemon_sock.recvfrom(1024)
            print('Connected by', host_from)
            address, _ = host_from
            if not data:
                break
            print('Sending back data: ', data)
            self.handshake(data, address)
            print(f"connection status {self.connection}")



    def client_listen(self):

        print("Listening for messages from clients on port 7778")



        while True:
            data , host_from = self.client_sock.recvfrom(1024)
            print('Connected by', host_from)
            address, _ = host_from
            print(address)
            if not data:
                break
            print('Sending back data: ', data)
            self.handshake(data, address)
            print(f"connection status {self.connection}")

    def client_message(self):
        pass

    def daemon_message(self):
        pass

    def handshake(self, message, address):

        if message == b'0x02' and not self.connection:
            self.daemon_sock.sendto(b'0x06',(address, DAEMON_PORT))
            # time.sleep(5)
            reply, _ = self.daemon_sock.recvfrom(1024)
            if reply == b'0x04':
                self.connection = True
                print(f"connection established as a receiver with {address}")



        elif message != b'0x02' and not self.connection:
            print(f" message {message} address {address}")
            self.daemon_sock.sendto(b'0x02', (address, DAEMON_PORT))
            # time.sleep(5)
            reply, _ = self.daemon_sock.recvfrom(1024)
            if reply == b'0x06':
                # time.sleep(5)
                self.daemon_sock.sendto(b'0x04', (address, DAEMON_PORT))
                self.connection = True
                print(f"connection established as a sender with {address}")



        elif message == b'0x02' and self.connection:
            # send error message - client busy
            # send FIN
            # continue
            pass


        elif message == b'0x08' and self.connection:
            # send FIN
            # timeout
            # self.connection = False
            pass




if __name__ == "__main__":
    if len(sys.argv) != 2:
        exit(1)
    daemon = ExampleDaemon(sys.argv[1])
    daemon.start()


