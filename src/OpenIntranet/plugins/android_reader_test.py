#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
from . import BaseHandler
# from pyoctopart.octopart import Octopart
import json
import bson.json_util
import urllib
import datetime

import collections, urllib, base64, hmac, hashlib, json


def get_plugin_handlers():
    plugin_name = get_plugin_info()["module"]

    return [
        (r'/%s' % plugin_name, hand_bi_home),
        (r'/%s/' % plugin_name, hand_bi_home),
    ]


def get_plugin_info():
    return {
        "module": "android_barcode",
        "name": "Android čtečka",
        "icon": 'icon_android.svg'
    }


class hand_bi_home(BaseHandler):
    def get(self, data=None):
        roles = self.authorized(['andorid'], sudo=False)
        print(">>>>>", roles)

        self.render("android_barcode.home.hbs", title="UST intranet", parent=self)
