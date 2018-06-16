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
             (r'/{}/get_invoices/'.format(module), plugin.get_invoices),
             (r'/{}/get_invoice/'.format(module), plugin.get_invoice),
             (r'/{}/invoice/(.*)/'.format(module), plugin.invoice),
             (r'/{}'.format(module), plugin.hand_bi_home),
             (r'/{}/'.format(module), plugin.hand_bi_home),
             #(r'/%s' %module, plugin.hand_bi_home),
             #(r'/%s/' %module, plugin.hand_bi_home),
        ]

def plug_info():
    return{
        "module": "invoice_import",
        "name": "Importování faktur",
        "icon": 'icon_sklad.svg'
    }


class hand_bi_home(BaseHandler):
    def get(self, data=None):
        
        self.render("invoice_import.home.hbs", parent = self)




class get_invoices(BaseHandler):
    def post(self):
        out = self.get_argument('out', 'html')
        data = self.mdb.invoice.find({})
            
        if 'json' in out:
            self.set_header('Content-Type', 'application/json')
            output = bson.json_util.dumps(list(data))
            self.write(output)
        
        elif 'html' in out:
            self.render("invoice_import.api.invoice_list.basic.hbs", invoices = list(data))

class get_invoice(BaseHandler):
    def post(self):
        id = self.get_argument('id', None)
        out= self.get_argument('out', 'json')
        oid = bson.ObjectId(id)

        data = self.mdb.invoice.aggregate([
                {'$match':{'_id': oid}},
                {'$lookup':{
                        'from': 'stock_movements',
                        'localField': 'elements._id',
                        'foreignField': '_id',
                        'as':'element_list'
                    }
                }
            ])

        output = bson.json_util.dumps(list(data)[0])
        self.write(output)


class invoice(BaseHandler):
    def get(self, i_id):
        self.write("INVOICE" + str(i_id))
