#!/usr/bin/env python3

import socket
import threading
import sys
import time



CLIENT_PORT = 7778







def connect(ip_address, client_sock):


    conn_test = b'connectionrequest'

    try:

        client_sock.sendto(conn_test, (ip_address,CLIENT_PORT))
        data, _ = client_sock.recvfrom(1024)
        if data.decode() == "connected":
            return True

    except Exception:
        return False




def send(host, message: bytes, client_sock):

    client_sock.sendto(message, (host,CLIENT_PORT))



def receive(client_sock):
    try:
        data, host_from = client_sock.recvfrom(1024)
        print(f"Response from {host_from}: {data.decode()}")
    except:
        pass

def quit(host, message, client_sock):

    client_sock.sendto(message, (host, CLIENT_PORT))
    sys.exit()




def show_usage():
    print('Usage: simple_socket_client.py')


if __name__ == "__main__":
    if len(sys.argv) != 3:
        show_usage()


    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_sock:
        # client also need to be bound to an ip and port
        client_sock.bind(("127.0.0.1", CLIENT_PORT))


        daemon_ip_request = sys.argv[1]
        daemon_ip = "" + daemon_ip_request
        print(f"daemon_ip_request {daemon_ip_request}")

        if connect(daemon_ip_request, client_sock):
            print(f"Successfully connected to daemon with ip {daemon_ip_request}")

            while True:


                message = input("Enter your message")

                # shut down client - daemon connection
                if message == "!q":
                    quit(daemon_ip ,message.encode(), client_sock)

                else:
                    send(daemon_ip, message.encode(), client_sock)
                    receive(client_sock)

























    # while True:
    #     client_input = input("1 for start conversation and 0 for wait")
    #     if int(client_input) == 1:
    #         data = send(sys.argv[1], str.encode(sys.argv[2]))
    #         print('Received', data)
    #
    #     elif int(client_input) == 0:
    #         receive(daemon_ip)


