#!/usr/bin/env python3

import socket
import threading
import sys
import time



CLIENT_PORT = 7778
client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# client also need to be bound to an ip and port
client_sock.bind(("127.0.0.1",CLIENT_PORT))






def connect(ip_address):


    conn_test = b'connectionrequest'

    try:

        with client_sock as s:
            s.sendto(conn_test, (ip_address,CLIENT_PORT))
            data, _ = client_sock.recvfrom(1024)
            if data.decode() == "connected":
                return True

    except Exception:
        return False




def send(host, message: bytes):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:

        s.sendto(message, (host,CLIENT_PORT))



def receive():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:

            data, host_from = s.recvfrom(1024)
            print(f"Response from {host_from}: {data.decode()}")
    except:
        pass




def show_usage():
    print('Usage: simple_socket_client.py')


if __name__ == "__main__":
    if len(sys.argv) != 3:
        show_usage()

    # t = threading.Thread(target=receive)
    # t.start()


    daemon_ip_request = sys.argv[1]
    daemon_ip = "" + daemon_ip_request
    print(f"daemon_ip_request {daemon_ip_request}")

    if connect(daemon_ip_request):
        print(f"Successfully connected to daemon with ip {daemon_ip_request}")


        while True:
            receive()
            message = input("Enter your message")


            if message == "!q":
                sys.exit()

            else:
                send(daemon_ip, message.encode())

                # socket error here for simp_daemon

                pass




    else:
        print(f"failed to connect to {daemon_ip}")
        sys.exit()











    # while True:
    #     client_input = input("1 for start conversation and 0 for wait")
    #     if int(client_input) == 1:
    #         data = send(sys.argv[1], str.encode(sys.argv[2]))
    #         print('Received', data)
    #
    #     elif int(client_input) == 0:
    #         receive(daemon_ip)


