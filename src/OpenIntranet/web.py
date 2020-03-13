# #!/usr/bin/python
# # -*- coding: utf-8 -*-
import glob
import importlib
import os
import traceback
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
tornado.options.define("intranet_storage", default='/data/intranet', help="Folder for local files as logo, ...")

tornado.options.define("company_name", default="Company name", help="Company name")
tornado.options.define("company_graphic", default=None, help="Folder with company graphic.")

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

    def post(self, *args, **kwargs):
        self.write("ACK")


class WebApp(tornado.web.Application):

    def __init__(self):
        print("Hledám pluginy...")
        print()

        plugins, handlers, ignored = self.find_plugins("plugins")

        # staticke soubory je vhodne nahradit pristupem primo z proxy serveru. (pak to tolik nevytezuje tornado)
        handlers += [
            (r'/favicon.png', tornado.web.StaticFileHandler, {'path': tornado.options.options.intranet_storage}),
            (r'/storage/(.*)', tornado.web.StaticFileHandler, {'path': tornado.options.options.intranet_storage}),
            (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static/'}),
            (r'(.*)', home),
            (r'/(.*)', home)
        ]

        print("plugins:")
        for plugin in plugins:
            print(f"\t{plugin}")
        print()

        if ignored:
            print("ignored:")
            for file in ignored:
                print(f"\t{file}")
            print()

        name = tornado.options.options.intranet_name
        server = tornado.options.options.intranet_url
        # server_url = '{}:{}'.format(server, tornado.options.options.port)
        server_url = '{}:{}'.format(server, 88)

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

        print("Done")
        super().__init__(handlers, **settings)

    def find_plugins(self, plugins_dir_name, *, tracebacks=True, ignored_names=("__pycache__",)):
        plugin_infos = {}
        handlers = []
        ignored_files = []

        for file_name in os.listdir(plugins_dir_name):
            if file_name in ignored_names:
                continue

            module_name = self.get_module_name(file_name, plugins_dir_name)

            try:
                module = importlib.import_module(f"{plugins_dir_name}.{module_name}")

                plugin_handlers = module.get_plugin_handlers()
                plugin_info = module.get_plugin_info()
                plugin_name = plugin_info.get("module", module_name)

                if plugin_name in plugin_infos:
                    raise RuntimeError(f"Plugin {plugin_name} (v souboru {file_name}) je duplicitní.")

                handlers += plugin_handlers
                plugin_infos[plugin_name] = plugin_info

            except ModuleNotFoundError:
                ignored_files.append(file_name)

            except Exception as e:
                if tracebacks:
                    self.print_traceback(e)

                ignored_files.append(file_name)

        return plugin_infos, handlers, ignored_files

    @staticmethod
    def print_traceback(e):
        for line in traceback.format_exception(type(e), e, e.__traceback__):
            print(line, end="")
        print()

    @staticmethod
    def get_module_name(file_name, plugins_dir_name):
        file_path = os.path.join(plugins_dir_name, file_name)

        if not os.path.isdir(file_path):
            module_name, _ = os.path.splitext(file_name)
        else:
            module_name = file_name

        return module_name


def main():
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    tornado.options.parse_command_line()

    try:
        print("Využívám konfiguraci: ", tornado.options.options.config)
        print()

        tornado.options.parse_config_file(tornado.options.options.config)
    except Exception as e:
        print("Konfiguraci nelze načíst:", e)

    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(WebApp())
    http_server.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
