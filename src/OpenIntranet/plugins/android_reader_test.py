#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
from . import BaseHandler
#from pyoctopart.octopart import Octopart
import json
import bson.json_util
import urllib
import datetime

import collections, urllib, base64, hmac, hashlib, json


def make_handlers(module, plugin):
        return [
             (r'/%s' %module, plugin.hand_bi_home),
             (r'/%s/' %module, plugin.hand_bi_home),
        ]

def plug_info():
    return{
        "module": "android_barcode",
        "name": "Android čtečka",
        "icon": 'icon_android.svg'
    }




class hand_bi_home(BaseHandler):
    def get(self, data=None):
        roles = self.authorized(['andorid'], sudo=False)
        print(">>>>>", roles)
        
        self.render("android_barcode.home.hbs", title="UST intranet", parent=self)