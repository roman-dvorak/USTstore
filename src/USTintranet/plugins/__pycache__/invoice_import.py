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
from fpdf import FPDF
import barcode
import code128
import codecs
import datetime

def make_handlers(module, plugin):
        return [
             (r'/%s' %module, plugin.hand_bi_home),
             (r'/%s/' %module, plugin.hand_bi_home),
        ]

def plug_info():
    return{
        "module": "Invoire import",
        "name": "Importování faktur",
        "icon": 'icon_sklad.svg'
    }


class hand_bi_module(BaseHandler):
    def get():
        self.write("ACK")