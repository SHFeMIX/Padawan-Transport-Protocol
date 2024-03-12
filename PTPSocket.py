import struct
import socket
import threading
import time


class Header:
    def __init__(self, seq, ack, ACK, SYN, FIN):
        self.seq = seq
        self.ack = ack
        self.ACK = ACK
        self.SYN = SYN
        self.FIN = FIN

    def toBytes(self):
        return struct.pack('>QQ???', self.seq, self.ack, self.ACK, self.SYN, self.FIN)

    def show(self):
        print('\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\')
        print(f'seq: {self.seq}')
        print(f'ack: {self.ack}')
        print(f'ACK: {self.ACK}')
        print(f'SYN: {self.SYN}')
        print(f'FIN: {self.FIN}')
        print('/////////////////////')

    @staticmethod
    def parse(stream):
        string = struct.unpack('>QQ???', stream)
        return Header(*string)


class Segment:
    def __init__(self, header, data):
        self.header = header
        self.data = data

    def toBytes(self):
        return self.header.toBytes() + self.data

    def show(self):
        self.header.show()
        print(self.data)
        print('/////////////////////')

    def getseq(self):
        return self.header.seq

    def getack(self):
        return self.header.ack

    def ifFIN(self):
        return self.header.FIN

    @staticmethod
    def parse(stream):
        header = Header.parse(stream[:19])
        return Segment(header, stream[19:])

    def loginfor(self, act, start_time):
        n_bytes = len(self.data)
        sec = round((time.time() - start_time)*1000, 3)
        if n_bytes:
            type = 'D'
        else:
            if self.header.ACK:
                if self.header.FIN:
                    type = 'FA'
                elif self.header.SYN:
                    type = 'SA'
                else:
                    type = 'A'
            else:
                if self.header.FIN:
                    type = 'F'
                else:
                    type = 'S'

        seq = self.header.seq
        ack = self.header.ack
        line = "{:<6}{:<11}{:<5}{:<6}{:<5}{}\n".format(act, sec, type, seq, n_bytes, ack)
        return line


class PTPSocket:
    def __init__(self):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.target_addr = ()
        self.init_seq = 0
        self.init_ack = 0
        self.start_time = time.time()
        self.logfile = None

    # real send, as a separate function
    # because hand shake and wave don't use buffer
    def _send(self, segment):
        self.udp_socket.sendto(segment.toBytes(), self.target_addr)
        self.logfile.write(segment.loginfor('snd', self.start_time))

    # real receive, as a separate function
    # because hand shake and wave don't use buffer
    def _receive(self):
        bytes, addr = self.udp_socket.recvfrom(1024)
        self.target_addr = addr
        segment = Segment.parse(bytes)
        self.logfile.write(segment.loginfor('rcv', self.start_time))
        return segment

    def main_threading(self):
        pass

    def startthreading(self):
        main = threading.Thread(target=self.main_threading)
        main.start()
        main.join()
