#!/usr/bin/python
# -*- coding: utf-8 -*-
import tornado
#from tornado import web
from tornado import ioloop
from tornado import auth
from tornado import escape
from tornado import httpserver
from tornado import options
from tornado import web
#import functools
import json
import time
import datetime
import calendar
import os
import glob
from os.path import dirname, basename
import git
from git import Repo, Actor

#from handlers import admin, auth
from handlers import BaseHandler

tornado.options.define("port", default=10020, help="port", type=int)
tornado.options.define("debug", default=True, help="debug mode", type=bool)
tornado.options.define("octopart_api", default=None, help="OCTOPART api key")

tornado.options.define("owncloud_url", default=None, help="URL address of owncloud server")
tornado.options.define("owncloud_user", default=None, help="URL address of owncloud server")
tornado.options.define("owncloud_pass", default=None, help="URL address of owncloud server")
tornado.options.define("owncloud_root", default='/OpenIntranet/', help="URL address of owncloud server")


class home(BaseHandler):
    def get(self, arg=None):
        print("GET home")
        err = []
        self.render("intranet.home.hbs", title="UST intranet", parent=self, err = err, Repo = Repo)

    def post(self, arg=None):
        self.write("ACK")

class user(BaseHandler):
    def get(self, user = None):
        self.write("AAA")

class login(BaseHandler):
    def get(self):
        pass

class registration(BaseHandler):
    def get(self):
        pass

class WebApp(tornado.web.Application):
    def __init__(self, config={}):

        name = 'UST intranet'
        server = 'sklad.ust.cz'
        server_url = '{}:{}'.format(server, tornado.options.options.port)
        server_url = '{}:{}'.format(server, 88)

        handlers = []
        plugins = {}

        #
        # tohle najde vsechny python kody ve slozce 'plugins', ktere obsahuji fci make_handlers
        #
        for filepath in glob.glob("./plugins/*.py"):
            try:
                mod_name = basename(filepath)[:-3]
                mod = __import__('plugins.%s' % mod_name, fromlist=[''])

                globals()[mod_name] = mod
                handlers += mod.make_handlers(mod_name, mod)
                plugins[mod_name] = mod.plug_info()
            except Exception as e:
                print("Exception in plugin %s: %s" % (mod_name, e))

        handlers += [
            #staticke soubory je vhodne nahradit pristupem primo z proxy serveru. (pak to tolik nevytezuje tornado)
            (r'/favicon.ico', tornado.web.StaticFileHandler, {'path': "/static/"}),
            (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static/'}),
            (r'/user', user),
            (r'/user/(.*)/', user),
            (r'/user/(.*)', user),
            (r'/login/', login),
            (r'/registration/', registration),
            (r'(.*)', home),
            (r'/(.*)', home)
        ]

        print ("plugins:")
        for plugin in plugins:
            print("", plugin)
        print ("handlers:")
        for handler in handlers:
            pass
            #print("", server_url+handler[0], handler[1])
            #print(server_url+handler[0])

        settings = dict(
            plugins = plugins,
            cookie_secret="ROT13IrehaxnWrArwyrcfvQvixnAnFirgr",
            template_path= "templates/",
            static_path= "static/",
            plugin_path= "plugins/",
            xsrf_cookies=False,
            name=name,
            server_url=server_url,
            site_title=name,
            login_url="/login",
            port=tornado.options.options.port,
            compress_response=True,
            debug=tornado.options.options.debug,
            autoreload=True
        )
        #tornado.locale.load_translations("locale/")
        print("Done")
        tornado.web.Application.__init__(self, handlers, **settings)

def main():
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

    tornado.options.parse_config_file("/data/ust/intranet.conf")
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(WebApp())
    http_server.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
