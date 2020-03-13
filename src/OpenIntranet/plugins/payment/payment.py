#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from .. import Intranet
from .. import BaseHandler
from . import PaymentHelper
import json
import bson.json_util
import urllib
import datetime



def make_handlers(module, plugin):
        return [
             (r'/{}'.format(module), plugin.home),
             (r'/{}/'.format(module), plugin.home),
        ]

def plug_info():
    return{
        "module": "payment",
        "name": "Platby",
    }

class home(BaseHandler, PaymentHelper):
    def get(self):
        overview = bson.json_util.dumps(self.get_payment_overview())
        self.render('../plugins/payment/payment.home.hbs', title = "Platby", payments = overview)

    def post(self):
        overview = bson.json_util.dumps(self.get_payment_overview())
        self.write(overview)


