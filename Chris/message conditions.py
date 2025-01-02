import socket
import sys
import threading
import time
from enum import Enum

MAX_HEADER_SIZE = 35 # constant size (in bytes) of header
MESSAGE_TYPE_SIZE = 1
MESSAGE_OPERATION_SIZE = 1
MESSAGE_SEQUENCE_SIZE = 1
MESSAGE_USER_SIZE = 32





# ljust(32, b'0x00') - function to pad username field with zero bytes until 32 is reached
class Datagram:
    def __init__(self, type, sequence, username, payload=None, operation=None):
        if type== 1:
            self.type = int.to_bytes(1, 1, byteorder="big")
        elif type == 2:
            self.type = int.to_bytes(2, 1, byteorder="big")
        if sequence == 0:
            self.sequence = int.to_bytes(0, 1, byteorder='big')
        elif sequence == 1:
            self.sequence = int.to_bytes(1, 1, byteorder='big')

        self.length = int(0).to_bytes(1, byteorder='big')
        self.username = username.encode("ascii").ljust(32, int(0).to_bytes(1, byteorder='big'))
        if payload != None:
            self.payload = payload.encode("ascii")
            self.length = int.to_bytes(len(payload), 4, byteorder='big')
        else:
            self.payload = b""

        if operation != None:
            self.operation = operation.to_bytes(1, byteorder='big')
        else:
            self.operation = int(1).to_bytes(1, byteorder='big')


    def __repr__(self):
        return "".join([str(self.type), str(self.operation), str(self.sequence), str(self.username), str(self.payload)])




class HeaderType(Enum):
    CONTROL = 1
    CHAT = 2

    def to_bytes(self):
        if self == HeaderType.CONTROL:
            return int(1).to_bytes(1, byteorder='big')
        elif self == HeaderType.CHAT:
            return int(2).to_bytes(1, byteorder='big')



class HeaderOperation(Enum):
    ERR = 1
    SYN = 2
    ACK = 4
    SYN_ACK = 6
    FIN = 8


    def to_bytes(self):
        if self == HeaderOperation.ERR:
            return int(1).to_bytes(1, byteorder='big')
        elif self == HeaderOperation.SYN:
            return int(2).to_bytes(1, byteorder='big')
        elif self == HeaderOperation.ACK:
            return int(4).to_bytes(1, byteorder='big')
        elif self == HeaderOperation.SYN_ACK:
            return int(6).to_bytes(1, byteorder='big')
        elif self == HeaderOperation.FIN:
            return int(8).to_bytes(1, byteorder='big')



# class HeaderSequence(Enum):
#     NULL = 0
#     ONE = 1
#
#     def to_bytes(self):
#         if self == HeaderSequence.NULL:
#             return int(0).to_bytes(1, byteorder='big')
#         elif self == HeaderSequence.ONE:
#             return int(1).to_bytes(1, byteorder='big')


class HeaderInfo:
    is_ok = False
    type: HeaderType
    operation: HeaderOperation
    # sequence: HeaderSequence

    def __init__(self):
        self.is_ok = False
        self.type = HeaderType.CONTROL
        self.operation = HeaderOperation.ERR
        # self.sequence = HeaderSequence.NULL

def handshake(operation: HeaderOperation):
    connection = True
    if not connection:

        if operation == HeaderOperation.SYN:
            return HeaderOperation.SYN_ACK
        elif operation == HeaderOperation.SYN_ACK:
            return HeaderOperation.ACK
        elif operation == HeaderOperation.ACK:
            connection = True
            return connection

    elif connection:

        if operation == HeaderOperation.SYN:
            return HeaderOperation.ERR, HeaderOperation.FIN




def get_message_type(type: bytes):
    if int.from_bytes(type) == 1:
        return HeaderType.CONTROL
    elif int.from_bytes(type) == 2:
        return HeaderType.CHAT

def get_message_operation(operation: bytes):
    if int.from_bytes(operation) == 1:
        return HeaderOperation.ERR
    elif int.from_bytes(operation) == 2:
        return HeaderOperation.SYN
    elif int.from_bytes(operation) == 4:
        return HeaderOperation.ACK
    elif int.from_bytes(operation) == 6:
        return HeaderOperation.SYN_ACK
    elif int.from_bytes(operation) == 8:
        return HeaderOperation.FIN

def check_header(datagram: Datagram) -> HeaderInfo:

    header_info = HeaderInfo()

    header_info.type = get_message_type(datagram.type)

    if header_info.type == HeaderType.CONTROL:
        header_info.operation = get_message_operation(datagram.operation)

    header_info.is_ok = True
    return header_info



def build_response(header_info: HeaderInfo, datagram) -> Datagram:

    # handshake

    if header_info.type == HeaderType.CONTROL and header_info.operation != HeaderOperation.ERR:

        operation = handshake(header_info.operation)


        if len(operation) > 1:
            print(operation)

            return [Datagram(), Datagram()]


    return Datagram()

# -- Sender
# receive syn
# send err
# send FIN


# -- Receiver
# 1 - send chat request
# send syn
# receive err
    # if operation == ERR
    # recvfrom()
    # FIN
    # reset chat request


    response = build_response()






data1 = Datagram(type=1, operation=2, sequence=0, username="Chris")


print(data1)
#print(get_message_type(data1.type))
header_info = check_header(data1)

print(build_response(header_info, data1))




# class Datagram1:
#
#     def __init__(self, type, operation, length, payload):
#         self.type = type
#         self.operation = operation
#         self.length = length
#         self.payload = payload

# def handshake(self, message, address):
#
#     if not self.daemon_connection:
#
#         if message == b'0x02':
#             self.daemon_sock.sendto(b'0x06', (address, self.DAEMON_PORT))
#             print(f"Sending back ACK + SYN")
#
#
#         elif message == b'0x06':
#             print(f" message {message} address {address}")
#             reply = b'0x04'
#             self.daemon_sock.sendto(reply, (address, self.DAEMON_PORT))
#             print(f"Sending back {reply}")
#             self.daemon_connection = True
#             self.receiver_address = address
#             print(f"connection established as a sender with {address}")
#
#
#         elif message == b'0x04':
#             self.daemon_connection = True
#             self.receiver_address = address
#             print(f"connection established as a receiver with {address}")
#
#
#     elif self.daemon_connection:
#
#         if message == b'0x02':
#             error = b'User already in another chat'
#             fin = b'0x08'
#             self.daemon_sock.sendto(fin, (address, self.DAEMON_PORT))
#
#         elif message == b'0x04':
#             self.client_sock.settimeout(5.0)
#             self.daemon_connection = False
#
#
#         elif message == b'0x08':
#             ack = b'0x04'
#             self.daemon_sock.sendto(ack, (address, self.DAEMON_PORT))
#             self.client_sock.settimeout(5.0)
#             self.daemon_connection = False



