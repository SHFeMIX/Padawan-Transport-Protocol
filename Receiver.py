import sys
from PTPSocket import *
import queue


class RecvSocket(PTPSocket):
    def __init__(self, port):
        super(RecvSocket, self).__init__()
        self.udp_socket.bind(('127.0.0.1', port))
        # list contain all the segment received from sender
        # after the whole progress finished
        self.init_seq = 100
        self.recv_store = []
        self.disorderbuffer = queue.Queue()
        self.logfile = open('Receiver_log.txt', 'w')

    def writefile(self, file):
        counter = 0
        with open(file, 'w') as f:
            for segment in self.recv_store:
                if segment.ifFIN():
                    break
                data = segment.data.decode()
                f.write(data)
                counter += 1
            f.close()
        print(f'写入{counter}次')

    def handshake(self):
        # receive syn segment
        syn = self._receive()
        print('receive syn')
        syn.show()
        print(self.target_addr)

        # make and send synack segment
        synackheader = Header(self.init_seq, syn.getseq() + 1, 1, 1, 0)
        self.init_ack = syn.getseq() + 1
        self._send(Segment(synackheader, b''))
        print('sent synack')

        # receive ack segment
        ack = self._receive()
        ack.show()
        print('receive ack')
        self.init_seq = ack.getack()

        # three-way handshake completed
        print('three-way handshake completed')
        print(self.target_addr)
        #exit(0)

    def terminate(self):
        print('发一次')
        # send ack
        ackheader = Header(self.init_seq, self.init_ack, 1, 0, 0)
        print(f'发的是{self.init_seq} {self.init_ack}')
        self._send(Segment(ackheader, b''))

        print('发两次')
        # send finack
        finackheader = Header(self.init_seq, self.init_ack + 1, 1, 0, 1)
        self._send(Segment(finackheader, b''))

        print('收一次')
        # receive ack
        ack = self._receive()
        ack.show()

        # terminate completed
        print('four-segment connection termination completed')
        self.logfile.close()

    # only threading for receiver, receive and return ack
    def main_threading(self):
        nextwantseq = self.init_ack
        while True:
            segment = self._receive()
            recvseq = segment.getseq()
            print('收到', end='')
            print(segment.getseq())

            if segment.ifFIN():
                self.init_seq = segment.getack()
                self.init_ack = segment.getseq() + 1
                print('退出')
                return
            # 丢弃重复分组
            if recvseq < nextwantseq:
                print('丢弃重复')
                print(f'recvseq: {recvseq}, nextwantseq: {nextwantseq}')
                header = Header(self.init_seq, nextwantseq, 1, 0, 0)
                print(f'想要{nextwantseq}')
                self._send(Segment(header, b''))
                continue

            # if disorder received, put segment in buffer
            if recvseq != nextwantseq:
                print('乱序到达')
                self.disorderbuffer.put(segment)

            # if order receive
            else:
                print('顺序到达')
                self.recv_store.append(segment)

                # 对当前queue头来说的上一个
                lastseq = recvseq
                while not self.disorderbuffer.empty():
                    head = self.disorderbuffer.queue[0]
                    if head.getseq() == lastseq + len(segment.data):
                        self.recv_store.append(head)
                        self.disorderbuffer.get()
                        lastseq = head.getseq()
                    else:
                        break
                nextwantseq = lastseq + len(segment.data)

            # send ackseg, acknum = nextwantseq
            header = Header(self.init_seq, nextwantseq, 1, 0, 0)
            print(f'想要{nextwantseq}')
            self._send(Segment(header, b''))


# 三次握手，开启线程不啦不啦不啦，结束线程四次分手，从buffer得到data写入文件
if __name__ == '__main__':
    port = int(sys.argv[1])
    target_file = sys.argv[2]

    PTPSocket = RecvSocket(port)

    PTPSocket.handshake()

    PTPSocket.startthreading()

    PTPSocket.terminate()

    PTPSocket.writefile(target_file)

# sender 读取所有文件内容进buffer之后加一个finseg，
# receiver的接受线程收到fin就结束，开始四次分手
# 核心部分缓冲区的概念还要理解一下，是否两边都需要queue，list可不可以
# 三次握手第三次就发内容，四次挥手与最后一次内容绑在一起，是否可行
