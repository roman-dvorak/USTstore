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


def make_handlers(module, plugin):
        return [
             (r'/{}'.format(module), plugin.home),
             (r'/{}/'.format(module), plugin.home),
             #(r'/{}/test'.format(module), plugin.test),
             #(r'/{}/print/(.*)/'.format(module), plugin.api_print),
             #(r'/{}/api/add_to_cart'.format(module), plugin.api_addToCart),
             #(r'/{}/api/new_cart'.format(module), plugin.api_new_cart),
        ]

def plug_info():
    return{
        "module": "development",
        "name": "Vývvoj",
    }


class home(BaseHandler):
    def get(self, data=None):
        self.render('development/development.home.hbs', title = "TITLE")
