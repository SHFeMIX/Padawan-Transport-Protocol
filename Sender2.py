import random
from PTPSocket import *
import sys
from collections import deque, defaultdict
import queue
import threading


class SendSocket(PTPSocket):
    def __init__(self, target_addr, mws, mss, pdrop, timeout, seed):
        super(SendSocket, self).__init__()
        self.target_addr = target_addr
        # this buffer contain all the segment what will be sent to the receiver
        # before start sending
        # 右边入(append)，左边出(popleft)，需要重传直接左边进(appendleft)
        self.send_buffer = deque()
        self.unack_buffer = queue.Queue(int(mws / mss))
        self.seed = seed
        self.pdrop = pdrop
        self.mss = mss
        self.logfile = open('Sender_log.txt', 'w')
        self.kill = False
        self.amount = defaultdict(int)

    def readfile(self, file):
        with open(file, 'r') as f:
            while True:
                data = f.read(self.mss)
                if not data:
                    break
                header = Header(self.init_seq, self.init_ack, 0, 0, 0)
                segment = Segment(header, data.encode())
                self.send_buffer.append(segment)
                self.amount['DataTrans'] += len(segment.data)
                self.amount['SegSent'] += 1
                self.init_seq += len(segment.data)
            f.close()
        header = Header(self.init_seq, self.init_ack, 0, 0, 1)
        segment = Segment(header, b'')
        self.send_buffer.append(segment)

    def handshake(self):
        # make syn segment and send
        synheader = Header(self.init_seq, 0, 0, 1, 0)
        self._send(Segment(synheader, b''))
        print('sent syn')

        # receiver synack segment
        synack = self._receive()
        print('receive synack')
        synack.show()

        # make ack segment and send
        ackheader = Header(synack.getack(), synack.getseq() + 1, 1, 0, 0)
        self.init_seq = ackheader.seq
        self.init_ack = ackheader.ack
        self._send(Segment(ackheader, b''))
        print('send ack')

        # three_way handshake complete
        print('three-way handshake completed')
        # exit(0)

    def terminate(self):
        # receive ack
        print('收到ack')
        ack = self._receive()
        ack.show()

        # receive finack
        finack = self._receive()
        print('收到finack')
        finack.show()

        # send ack segment
        ackheader = Header(finack.getack(), finack.getseq() + 1, 1, 0, 0)
        self._send(Segment(ackheader, b''))

        # terminate completed
        print('four-segment connection termination completed')
        self.logfile.write('\n')
        self.logfile.write(f'Amount of (original) Data Transferred (in bytes): {self.amount["DataTrans"]}\n')
        self.logfile.write(f'Number of Data Segments Sent (excluding retransmissions): {self.amount["SegSent"]}\n')
        self.logfile.write(f'Number of (all) Packets Dropped (by the PL module): {self.amount["Drop"]}\n')
        self.logfile.write(f'Number of Retransmitted Segments: {self.amount["Retrans"]}\n')
        self.logfile.write(f'Number of Duplicate Acknowledgements received: {self.amount["DupAck"]}\n')
        self.logfile.close()
        '''
        Number of Data Segments Sent (excluding retransmissions) 
• Number of (all) Packets Dropped (by the PL module) 
• Number of Retransmitted Segments 
• Number of Duplicate Acknowledgements received 
        '''

    def main_threading(self):
        # start receive_threading
        receiving = threading.Thread(target=self.receive_threading)
        receiving.setDaemon(True)
        receiving.start()

        # send_threading
        random.seed(self.seed)
        while True:
            # if only fin remain
            if len(self.send_buffer) == 1:
                if not self.unack_buffer.empty():
                    print('aa')
                    continue

            # if unack is full and next is not resend segment
            # wait (resend doesn't care if unack is full or not)
            # first get next seg from send_buffer
            segment = self.send_buffer.popleft()
            if not self.unack_buffer.empty():
                print(f'长度{len(self.unack_buffer.queue)}')
                if self.unack_buffer.full() and segment != self.unack_buffer.queue[0]:
                    # 原路塞回去
                    self.send_buffer.appendleft(segment)
                    continue

            print('发送', end='')
            print(segment.data)

            # if segment is fin, finish the thread
            if not segment.data:
                self._send(segment)
                self.kill = True
                return

            # PL module
            n = random.random()
            if n > self.pdrop or not segment.data:
                # 写log snd
                self._send(segment)
            else:
                # 写log drop
                self.amount['Drop'] += 1
                self.logfile.write(segment.loginfor('drop', self.start_time))

            # resend segment doesn't need to put in unack buffer again
            if self.unack_buffer.empty() or segment != self.unack_buffer.queue[0]:
                self.unack_buffer.put(segment)
            '''
            else:
                if segment != self.unack_buffer.queue[0]:
                    self.unack_buffer.put(segment)
            '''

    def receive_threading(self):
        ackdict = defaultdict(int)
        while True:
            print(f'长度是{len(self.unack_buffer.queue)}')
            ackseg = self._receive()
            acknum = ackseg.getack()
            print(f'收的是{ackseg.getseq()} {acknum}')

            # if no unack segment, don't need to do anything
            if self.unack_buffer.empty():
                continue

            # remove all the acked segments in unack_buffer
            head = self.unack_buffer.queue[0]

            ifcontinue = 0
            while head.getseq() < acknum:
                print(f'放出一个')
                self.unack_buffer.get()
                if self.unack_buffer.empty():
                    ifcontinue = 1
                    break
                head = self.unack_buffer.queue[0]

            if ifcontinue:
                if len(self.send_buffer) == 1:
                    return
                continue
            # fast resend, if three identical ack number
            if ackdict[acknum] != 0:
                self.amount['DupACK'] += 1
            ackdict[acknum] += 1
            if ackdict[acknum] == 3:
                # head.setresend()
                self.amount['Retrans'] += 1
                self.send_buffer.appendleft(head)


# 每次发包，如果计时器开启了就不管他，计时器没开启就开启
# 到达timeout时限后，重传unack的第一个(unack_buffer.pop())
# sender 需要两个线程同时开始，并阻塞主线程，两个都结束后再继续主线程
# 把receiving 做成sending的守护线程
# 处理seq，ack， 实现超时重传
# 所有segment都被确认了再发fin，发完fin线程结束，receiver收到fin线程也结束，两边开始四次挥手剩下三次

# sender 发送的ack, receiver发送的seq全都保持不变，ack不占空间
# 三次握手，所有文件内容打包入buffer，开启线程不啦不啦不啦，结束线程四次分手
if __name__ == '__main__':
    recv_IP = sys.argv[1]
    recv_port = int(sys.argv[2])
    source_file = sys.argv[3]
    mws = int(sys.argv[4])
    mss = int(sys.argv[5])
    timeout = int(sys.argv[6])
    pdrop = float(sys.argv[7])
    seed = int(sys.argv[8])

    PTPSocket = SendSocket((recv_IP, recv_port), mws, mss, pdrop, timeout, seed)

    PTPSocket.handshake()

    PTPSocket.readfile(source_file)

    PTPSocket.startthreading()

    PTPSocket.terminate()
# 先发送的那一方会自动随机选个端口发送，但是发送需要知道对方的端口
# 先接受的一方需要先把自己绑定在一个端口上，接收到一次信息之后就能知道对方的端口号，用来给对方发送
# sender的target_addr直接作为参数传入，receiver的target_addr通过第一次接收得到

# sender第一次发送会随机选一个端口，之后会一直用那一
# 所以self.target_addr = addr其实只有receiver第一次接收的时候需要
