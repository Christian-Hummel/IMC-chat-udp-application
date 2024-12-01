#!/usr/bin/env python3

import socket
import sys
import string
import os

CLIENT_PORT = 7778

#
#
# while True:
#     if client_input == "q":
#         break


def send(host, message: bytes) -> string:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(message, (host,CLIENT_PORT))
        reply = s.recv(1024)
        return repr(reply)

def check_connection(ip_address):
    try:

        send(ip_address, b"TestConnection")

    except ConnectionResetError:
        return False

    return True


def show_usage():
    print('Usage: simple_socket_client.py <host> <port> <message>')


if __name__ == "__main__":

    daemon_address = input("Give me the IP-Address of the Daemon:")

    if not check_connection(daemon_address):
        print("This Daemon is not running, try another IP-Address")

    username = input("Give me your username:")

    if len(sys.argv) != 3:
        show_usage()
        exit(1)

    data = send(sys.argv[1], str.encode(sys.argv[2]))
    print('Received', data)
