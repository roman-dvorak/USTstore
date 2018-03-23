#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
from . import BaseHandler
from . import perm_validator
import json
import bson.json_util
import urllib
import datetime


def make_handlers(module, plugin):
        return [
             (r'/{}'.format(module), plugin.home),
             (r'/{}/'.format(module), plugin.home),
             #(r'/%s/print/' %module, plugin.print_layout),
             #(r'/%s/api/(.*)/' %module, plugin.api)
        ]

def plug_info():
    return{
        "module": "users",
        "name": "Adresář"
    }

#@perm_validator(permissions=['sudo'])
class home(BaseHandler):
    def get(self, data=None):
        self.roles = self.authorized(['users', 'sudo-users'])

        users = self.mdb.users.find()

        self.render('users.home.hbs', title = "TITLE", parent = self, users = users)
