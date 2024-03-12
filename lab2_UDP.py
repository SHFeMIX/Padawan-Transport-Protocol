import socket
import datetime
import sys
import time

import queue
# write(self.log_format.format(segment.loginfor()))
print('{}'.format('aa'))

print("{:<5}{:<10}{:<5}{:<5}{:<5}{}".format('snd', 34.555, 'SA', '123', '100', 0))
old = time.time()
time.sleep(0.03)
print(round((time.time() - old)*1000,3))
exit(0)
q = queue.Queue()
for n in [2, 3, 4, 6, 7, 9]:
    q.put(n)
print(q.queue[0])
list = []
for n in [1, 5, 8]:
    list.append(n)
    last = n
    while not q.empty():
        head = q.queue[0]
        if head == last + 1:
            list.append(head)
            q.get()
            last += 1
        else:
            break
    print(list)
print(list)



exit(0)
'''
create UDP socket
send message
receive message
print
timeout
printformat
'''

IP = sys.argv[1]
port = int(sys.argv[2])
clientSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
serveraddr = (IP, port)
list_rtt = []
lost = 0
seq = 0
for i in range(3331, 3346):
    sendtime = datetime.datetime.now()
    message = str(i) + ' ' + str(sendtime) + ' ' + '\r\n'
    clientSocket.sendto(message.encode(), serveraddr)

    try:
        clientSocket.settimeout(0.6)
        response, address = clientSocket.recvfrom(1024)
        rtt = round((datetime.datetime.now() - sendtime).total_seconds() * 1000)

        list_rtt.append(rtt)
        print(f'{i} PING to {IP}, seq = {seq}, rtt = {rtt} ms')
    except:
        lost += 1
        print(f'{i} PING to {IP}, seq = {seq}, rtt = time out')

    seq += 1

print('\n')
print(f'Minimum RTT = {min(list_rtt)} ms')
print(f'Maximum RTT = {max(list_rtt)} ms')
print(f'Average RTT = {round(float(sum(list_rtt) / len(list_rtt)))} ms')
print(f'{float(lost / 15 * 100)}% of packets have been lost through the network')
clientSocket.close()
