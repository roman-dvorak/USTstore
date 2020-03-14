#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
# from pyoctopart.octopart import Octopart
import json
import urllib


def get_plugin_handlers():
    plugin_name = get_plugin_info()["module"]

    return [
        (r'/%s' % plugin_name, hand_bi_home),
        (r'/%s/' % plugin_name, hand_bi_home),
    ]


def get_plugin_info():
    # class base_info(object):
    return {
        "module": "base_info",
        "name": "base_info"
    }


class hand_bi_home(tornado.web.RequestHandler):
    def get(self, data=None):
        self.write("BASE ....")
