import evdev
from evdev import InputDevice, categorize, ecodes
import time, json
from multiprocessing import Process
from multiprocessing import Queue

import tornado.httpserver
import tornado.websocket
import tornado.ioloop
import tornado.web
import socket

print("Start")
print(evdev.list_devices())

dev = None
devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
for device in devices:
    print(device.info, device.name, '#', device.phys)
    print(device.leds(verbose=True))
    if '1400g' in device.name:
        dev = InputDevice(device)
        print("selected>>>>>")

if not dev:
    print("Device must by set manually...")
    dev = InputDevice('/dev/input/event0')

print("Selected device is", dev)

dev.grab()

keys = []
global connections
connections = []
con = []

qcon = Queue()

# With shift
sh = {
    '0':')',
    '1':'!',
    '2':'@',
    '3':'#',
    '4':'$',
    '5':'%',
    '6':'^',
    '7':'&',
    '8':'*',
    '9':'(',
    'MINUS':'_',
    'EQUAL':'+'
}


# Without shift
sl = {
    'SPACE':' ',
    'MINUS':'-',
    'SLASH':'/',
    'DOT':  '.',
    'COMMA':',',
    'EQUAL':'='
}

def build_string(pole):
    string = ""
    for shift, code in pole:
        if shift:
            string += sh.get(code[4:], code[4]).upper()
        else:
            string += sl.get(code[4:], code[4]).lower()
    return string

def get_con():
    global connections
    return connections

def read_barcode():
    global connections
    keys = []
    shift = 0
    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY:
            cate = categorize(event)
            if cate.keycode == 'KEY_LEFTSHIFT':
                shift = cate.keystate
                print("shift", cate.keystate)
            elif cate.keycode == 'KEY_ENTER' and cate.keystate == 0:
                print("Ener begin")
                keys = []
            elif cate.keycode == 'KEY_ENTER' and cate.keystate == 1:
                print("Ener end")
                print(keys)
                code = build_string(keys)
                print(">>>", connections, con, get_con())
                for x in get_con():
                    print(x)
                    x.write_message(code)
            elif event.value:
                print(shift, cate.keycode, cate.keystate)
                keys += [(shift, cate.keycode)]
#read_barcode()

#p1 = Process(target=read_barcode)
#p1.start()

    keys = []
    shift = 0

def blocking_func():
    global connections
    global keys
    global shift
    try:
        for event in dev.read():
            if event.type == ecodes.EV_KEY:
                cate = categorize(event)
                if cate.keycode == 'KEY_LEFTSHIFT':
                    shift = cate.keystate
                    print("shift", cate.keystate)
                elif cate.keycode == 'KEY_ENTER' and cate.keystate == 0:
                    print("Ener begin")
                    keys = []
                elif cate.keycode == 'KEY_ENTER' and cate.keystate == 1:
                    print("Ener end")
                    code = build_string(keys)
                    #print("Mozna pripojeni", connections)
                    for x in connections:
                        print("Posilam na", x)
                        try:
                            data = {'code': code, 'codetype': None, 'date': None, 'source': 'barcode_reader'}
                            print(data)
                            x.write_message(json.dumps(data))
                        except Exception as e:
                            print(e)
                            print("Odeslani dat se nepovedlo..., Odstranuji..")
                            connections.remove(x)

                elif event.value:
                    print(shift, cate.keycode, cate.keystate)
                    keys += [(shift, cate.keycode)]
    except Exception as e:
        #print(connections)
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

    tornado.ioloop.PeriodicCallback(blocking_func, 20).start()
    tornado.ioloop.IOLoop.instance().start()
