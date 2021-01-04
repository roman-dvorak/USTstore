#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
from . import BaseHandler
import json
import bson.json_util
import urllib
import datetime


def get_plugin_handlers():
        plugin_name = get_plugin_info()["name"]

        return [
             (r'/{}'.format(plugin_name), home),
             (r'/{}/'.format(plugin_name), home),
             #(r'/{}/test'.format(plugin_name), test),
             #(r'/{}/print/(.*)/'.format(plugin_name), api_print),
             #(r'/{}/api/add_to_cart'.format(plugin_name), api_addToCart),
             #(r'/{}/api/new_cart'.format(plugin_name), api_new_cart),
        ]

def get_plugin_info():
    return{
        "name": "development",
        "entrypoints": []
    }


class home(BaseHandler):
    def get(self, data=None):
        self.render('development/development.home.hbs', title = "TITLE")
