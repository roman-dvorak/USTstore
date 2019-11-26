# #!/usr/bin/python
# # -*- coding: utf-8 -*-
import glob
import os
from os.path import basename

import tornado
from git import Repo
from tornado import httpserver
from tornado import ioloop
from tornado import options
from tornado import web

from plugins import BaseHandler

tornado.options.define("port", default=10020, help="port", type=int)
tornado.options.define("config", default="/data/ust/intranet.conf", help="Intranet config file")
tornado.options.define("debug", default=True, help="debug mode", type=bool)
tornado.options.define("octopart_api", default=None, help="OCTOPART api key")

tornado.options.define("owncloud_url", default=None, help="URL address of owncloud server")
tornado.options.define("owncloud_user", default=None, help="URL address of owncloud server")
tornado.options.define("owncloud_pass", default=None, help="URL address of owncloud server")
tornado.options.define("owncloud_root", default='/OpenIntranet/', help="URL address of owncloud server")

tornado.options.define("mdb_database", default='OpenIntranet', help="MongoDB database name")
tornado.options.define("mdb_url", default='localhost', help="MongoDB URL")
tornado.options.define("mdb_port", default=27017, help="MongoDB port")
tornado.options.define("mdb_user", default=None, help="MongoDB user-name")
tornado.options.define("mdb_pass", default=None, help="MongoDB passworld")

tornado.options.define("intranet_name", default="OpenIntranet", help="Intranet name")
tornado.options.define("intranet_url", default="www.OpenIntranet.eu", help="Intranet name")

tornado.options.define("email_address", default="")
tornado.options.define("email_password", default="")
tornado.options.define("email_smtp_host", default="")
tornado.options.define("email_smtp_port", default=25)


class home(BaseHandler):
    def get(self, arg=None):
        print("GET home")
        err = []
        self.render("intranet.home.hbs", title=tornado.options.options.intranet_name, default=None, required=True,
                    parent=self, err=err, Repo=Repo)

    def post(self, arg=None):
        self.write("ACK")


class user(BaseHandler):
    def get(self, user=None):
        self.write("AAA")


class login(BaseHandler):
    def get(self):
        pass


class registration(BaseHandler):
    def get(self):
        pass


class WebApp(tornado.web.Application):
    def __init__(self, config={}):

        name = tornado.options.options.intranet_name
        server = tornado.options.options.intranet_url
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
            # staticke soubory je vhodne nahradit pristupem primo z proxy serveru. (pak to tolik nevytezuje tornado)
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

        print("plugins:")
        for plugin in plugins:
            print("", plugin)
        print("handlers:")
        for handler in handlers:
            pass
            # print("", server_url+handler[0], handler[1])
            # print(server_url+handler[0])

        settings = dict(
            plugins=plugins,
            cookie_secret="oeuhchcokicheokcihocoi",
            template_path="templates/",
            static_path="static/",
            plugin_path="plugins/",
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
        # tornado.locale.load_translations("locale/")
        print("Done")
        tornado.web.Application.__init__(self, handlers, **settings)


def main():
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    tornado.options.parse_command_line()
    try:
        print("Vyuzivam konfig: ", tornado.options.options.config)
        tornado.options.parse_config_file(tornado.options.options.config)
    except Exception as e:
        print("Konfiguraci nelze načíst:", e)
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(WebApp())
    http_server.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
