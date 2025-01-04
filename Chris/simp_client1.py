import socket
import sys
import keyboard


CLIENT_PORT = 7778



def connect(ip_address, client_sock):
    conn_test = b'connectionrequest'

    try:

        client_sock.sendto(conn_test, (ip_address, CLIENT_PORT))
        data, _ = client_sock.recvfrom(1024)
        if data.decode() == "connected":
            return True

    except Exception:
        return False


def send(message: bytes, host, client_sock):
    client_sock.sendto(message, (host, CLIENT_PORT))


def receive(client_sock):
    try:
        data, host_from = client_sock.recvfrom(1024)
        return data.decode()

    except:
        pass


def quit(host, client_sock):
    close = b'Exit'
    client_sock.sendto(close, (host, CLIENT_PORT))




def show_usage():
    print('Usage: simple_socket_client.py')


if __name__ == "__main__":
    if len(sys.argv) != 3:
        show_usage()

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_sock:
        # client also need to be bound to an ip and port
        client_sock.bind(("127.0.0.3", CLIENT_PORT))


        daemon_ip_request = sys.argv[1]
        daemon_ip = "" + daemon_ip_request
        print(f"daemon_ip_request {daemon_ip_request}")

        # Connect client with daemon
        if connect(daemon_ip_request, client_sock):
            print(f"Successfully connected to daemon with ip {daemon_ip_request}")

            # General wait for messages
            while True:

                data = receive(client_sock)

                # second possibility - User chose to stay idle
                if data == "Waiting for incoming chat requests, please wait or press q to exit":
                    print(data)


                    while True:

                        data = receive(client_sock)
                        print(data)
                        print("waiting 1")

                        if data.startswith("Connected with"):
                            message = receive(client_sock)
                            print(message)


                        response = input()
                        send(response.encode("ascii"), daemon_ip, client_sock)

                        if keyboard.is_pressed("q"):
                            break


                    quit(daemon_ip, client_sock)
                    break



                print(data)

                response = input()

                send(response.encode("ascii"), daemon_ip, client_sock)



