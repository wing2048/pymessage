import socketserver
import threading
import time
from datetime import datetime

pwd = "kek"

messages = []
users = {}
channels = {}


def get_server_time():
    return ''.join(datetime.now().isoformat().split('T')[1].split('.')[0])


class Message:
    def __init__(self, ip, chan, message, time, datetime, u):
        self.chan = chan
        self.time = time
        self.u = u
        self.datetime = datetime
        self.message = message
        self.ip = ip
        self.is_message = message is not None
        if ip in users:
            self.name = users[self.ip]
        else:
            self.name = 'anon'

    def __str__(self):
        if self.u:
            return ' ' + self.time + ' ' + self.name + ': ' + self.message
        else:
            return " * " + self.message + " *"

    def update(self):
        if self.ip in users:
            self.name = users[self.ip]
        else:
            self.name = 'anon'


def get_ip_by_user(user):
    for u in users:
        if users[u] == user:
            return u


def get_last_message_by(ip):
    for m in reversed(messages):
        if m.ip == ip:
            return m
    return None


def add_message(ip, chan, msg=None, u=True):
    messages.append(Message(ip, chan, msg, get_server_time(), datetime.now(), u))


def count_online():
    return len(users)


def update_users():
    c = 0
    to_pop = []
    popped = []
    for user in users:
        if not get_last_message_by(user) is None:
            if (datetime.now() - get_last_message_by(user).datetime).total_seconds() < 5:
                c += 1
            else:
                to_pop.append(user)
    for u in to_pop:
        popped.append([u, users[u]])
        users.pop(u)
    return popped


def add_user_to_chan(ip, chan):
    if chan not in channels:
        channels[chan] = []
    channels[chan].append(ip)


def remove_user_from_channels(ip):
    for channel in channels:
        if ip in channel:
            channel.pop(ip)


class TCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        add = True
        out = ''
        send = True
        ip = self.client_address[0]
        recv = self.request.recv(4096 * 32).decode().rstrip()
        # if len(recv.split(chr(0))) >= 4:
        #     chan, id, name, = recv.split(chr(0))[:3]
        #     data = bytes(chr(0).join(recv.split(chr(0))[3:]), "utf-8")
        #     if not os.path.isdir(chan):
        #         os.mkdir(chan)
        #     with open(chan + os.path.sep + name, 'xb') as file:
        #         file.write(data)
        #     add = False
        if len(recv.split(chr(0))) == 3:
            chan, data, name = recv.split(chr(0))
        else:
            chan, data = recv.split(chr(0))
            name = 'anon'
        if data.split()[0] == ':nick':
            if ip in users:
                last_nick = users[ip]
            else:
                last_nick = 'anon'
            users[ip] = ' '.join(data.split()[1:])
            add_message(ip, chan, last_nick + " is now known as " + data.split()[1], False)
        elif data.split()[0] == ':ping':
            if not get_last_message_by(get_ip_by_user(data.split()[1])) is None:
                if (datetime.now() - get_last_message_by(get_ip_by_user(data.split()[1])).datetime).total_seconds() < 5:
                    add_message(ip, chan, users[ip] + " pinged " + data.split()[1] + ": user online", False)
                else:
                    add_message(ip, chan, users[ip] + " pinged " + data.split()[1] + ": user not online", False)
            else:
                add_message(ip, chan, users[ip] + " pinged " + data.split()[1] + ": not a user", False)

        elif data.split()[0] == ':sudo':
            if data.split()[1] == pwd:
                if data.split()[2] == 'cls':
                    for message in messages:
                        if message.chan == chan:
                            messages.remove(message)
                    add_message(ip, chan, users[ip] + " cleared history", False)
            else:
                add_message(ip, chan, users[ip] + " tried to type in the admin password.", False)
        elif data.split()[0] == ':join':
            add_message(ip, chan, users[ip] + " left #" + chan, False)
            add_message(ip, data.split()[1], users[ip] + " joined #" + data.split()[1], False)
        elif len(data) == 1 and ord(data) < 30:
            if ord(data) == 1:
                add_message(ip, chan)
            elif ord(data) == 2:
                send = False
                o = count_online()
                u = '|'.join([users[x] + ' [' + x + ']' for x in users])
                self.request.sendall(bytes(str(o) + '||' + u, "utf-8"))
            elif ord(data) == 3:
                users[ip] = name
                add_message(ip, chan, "%s [%s] has connected" % (users[ip], ip), False)
                remove_user_from_channels(ip)
                add_user_to_chan(ip, chan)
                add_message(ip, chan, users[ip] + " joined #" + chan, False)
                print(get_server_time() + ": %s joined" % ip)
        else:
            if add:
                add_message(ip, chan, data)
                print(get_server_time() + ": message from [%s] in channel %s" % (ip, chan))
            else:
                add_message(ip, chan, '%s sent a file: %s' % (users[ip], name), False)
                print(get_server_time() + ": file from " + ip)
        for message in messages:
            message.update()
            if message.is_message and message.chan == chan:
                out += str(message) + '\n'
        if send:
            self.request.sendall(bytes(out, "utf-8"))


def get_current_channel(u):
    for channel in channels:
        if u in channel:
            return channel


def update_thread():
    while True:
        dcd = update_users()
        for u, ip in dcd:
            add_message(ip, get_current_channel(ip), "%s [%s] disconnected" % (ip, u), False)
            print(get_server_time() + ': ' + u, 'disconnected.')


uthread = threading.Thread(target=update_thread)
uthread.start()
HOST, PORT = "", 80
print("Starting server...")
server = socketserver.TCPServer((HOST, PORT), TCPHandler)

# Activate the server; this will keep running until you
# interrupt the program with Ctrl-C
try:
    print("Server up.")
    server.serve_forever()
except KeyboardInterrupt:
    print("Stopping server...")
    server.shutdown()
    print("Stopped.")
