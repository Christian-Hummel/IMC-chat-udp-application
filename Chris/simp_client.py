#!/usr/bin/env python3

import socket
import sys
import string
import time

CLIENT_PORT = 7778

connection = False



def send(host, message: bytes) -> string:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:

        s.sendto(message, (host,CLIENT_PORT))
        reply = s.recv(1024)
        return repr(reply)


def receive(host) -> string:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:

        data, host_from = s.recvfrom(1024)
        print(f"Received chat request from {host_from}")


def show_usage():
    print('Usage: simple_socket_client.py <host> <port> <message>')


if __name__ == "__main__":
    if len(sys.argv) != 3:
        show_usage()

    daemon_ip = int(input("Please insert the ip_address from your chat daemon "))

    send(sys.argv[1], str.encode(sys.argv[2]))



    # while True:
    #     client_input = input("1 for start conversation and 0 for wait")
    #     if int(client_input) == 1:
    #         data = send(sys.argv[1], str.encode(sys.argv[2]))
    #         print('Received', data)
    #
    #     elif int(client_input) == 0:
    #         receive(daemon_ip)


