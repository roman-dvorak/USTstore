import time, json
from multiprocessing import Process
from multiprocessing import Queue

import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
import socket
import sys
import bson

keys = []
global connections
connections = []
con = []
shift = 0

i = 0
def blocking_func():
    global connections
    global keys
    global shift
    try:

        c = sys.stdin.read(1)
        keys += [c]

        if str(keys[-1]) == '\n':
            print("Nalezen konec")
            code = "".join(keys[:-1])
            oid = None
            group = None
            codetype = None
            try:
                oid = bson.ObjectId("{:x}".format(int(code, 10)))
                code = str(oid)
                codetype = 'ObjectId'
            except Exception as e:
                print("NOT")
            keys = []
            for x in connections:
                print("Posilam na", x)
                try:
                    data = {'code': code, 'codetype': codetype, 'group': group, 'date': None, 'source': 'barcodereader_dummy'}
                    print(data)
                    x.write_message(json.dumps(data))
                except Exception as e:
                    print(e)
                    print("Odeslani dat se nepovedlo..., Odstranuji..")
                    connections.remove(x)

    except Exception as e:
        print(e)
        pass

class WSHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        global connections
        print('new connection')
        connections += [self]
        print(connections)
        global qcon
        #qcon.put(self)

    def on_message(self, message):
        global connections
        print(connections)
        print('message received:  %s' % message)
        for x in connections:
            x.write_message(message[::-1])

    def on_close(self):
        print('connection closed')

    def check_origin(self, origin):
        return True

application = tornado.web.Application([
    (r'/ws', WSHandler),
])


if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8765)
    myIP = socket.gethostbyname(socket.gethostname())
    print('*** Websocket Server Started at %s***' % myIP)

    tornado.ioloop.PeriodicCallback(blocking_func, 10).start()
    tornado.ioloop.IOLoop.instance().start()
