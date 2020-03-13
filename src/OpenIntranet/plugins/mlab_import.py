#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
from . import BaseHandler
#from pyoctopart.octopart import Octopart
import json
import urllib
import bson
import datetime
import pandas as pd
from fpdf import FPDF
import requests


def get_plugin_handlers():
        plugin_name = get_plugin_info()["module"]

        return [
             (r'/{}/data/module_list'.format(plugin_name), module_list),
             (r'/{}/update'.format(plugin_name), stock_update),
             #(r'/{}/(.*)/print/'.format(plugin_name), print_bom),
             (r'/{}'.format(plugin_name), home),
             (r'/{}/'.format(plugin_name), home),
        ]

def get_plugin_info():
    #class base_info(object):
    return {
        "module": "mlab_import",
        "name": "Importování z MLABu"
    }



class home(BaseHandler):
    def get(self):
        self.render('mlab_import.home.hbs')

class module_list(BaseHandler):
    def get(self):

        r = requests.get('http://mlab.ust.cz/api/modules/').json()
        for x in r:
            stock = self.mdb.invoice.aggregate([
                {'$match':{'_id': x['_id']}}
            ])
            stock = list(stock)
            x['stock_exist'] = False             
            if len(stock) == 1:
                x['stock_exist'] = True
                x['stock_data'] = stock

        self.render('mlab_import.home.list.hbs', data = r)

class stock_update(BaseHandler):
    def post(self):
        module = self.get_argument('module')

        r = requests.get('http://mlab.ust.cz/api/module/{}/'.format(module)).json()
        print(r)

        module_data = r
        output = json.dumps(module_data)
        self.write(output)
        self.finish()

        