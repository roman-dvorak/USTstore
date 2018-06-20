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
             (r'/{}/save_invoice/'.format(module), plugin.save_invoice),
             (r'/{}/invoice/prepare_invoice_row/'.format(module), plugin.prepare_invoice_row),
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
        self.set_header('Content-Type', 'application/json')
        id = self.get_argument('id', None)
        if not id: id = None
        out = self.get_argument('out', 'json')
        oid = bson.ObjectId(id)

        if not id:
            self.write(bson.json_util.dumps({
                    'new': True,
                    '_id': str(oid)
                }))
            return None

        invoice = self.mdb.invoice.aggregate([
            {'$match':{'_id': oid}}
        ])

        data = self.mdb.invoice.aggregate([
                {'$match':{'_id': oid}},
                {'$unwind': '$elements'},
                {'$project': {'elements': 1, '_id': 0}},
                {'$lookup':{
                        'from': 'stock_movements',
                        'localField': 'elements._id',
                        'foreignField': '_id',
                        'as':'elements'
                    }
                }
            ])
        jout = list(invoice)[0]
        print(oid)
        print(">>>", jout)
        #jout['elements'] = list(data)
        #output = bson.json_util.dumps(jout, indent=4, sort_keys=True)
        output = bson.json_util.dumps(jout)
        self.write(output)


class invoice(BaseHandler):
    def get(self, i_id):
        self.write("INVOICE" + str(i_id))


class save_invoice(BaseHandler):
    def post(self):
        self.mdb.invoice.update({'_id': bson.ObjectId(self.get_argument('id'))},{
            '$set':{
                'invoice': self.get_argument('invoice_number'),
                'due_date': self.get_argument('duedate'),
                'partner': self.get_argument('partner'),
                'type': self.get_argument('type', 1),
                'state': self.get_argument('state', 4)
            }
        }, upsert = True)

class prepare_invoice_row(BaseHandler):
    def post(self):
        element_id = self.get_argument('component_id', -1)
        comp = self.get_argument('component')
        symbol = self.get_argument('symbol', None)
        description = self.get_argument('description', '')
        bilance = 0
        bilance_plan = self.get_argument('count_planned', None)
        invoice = self.get_argument('invoice')
        price = self.get_argument('price')


        out = self.mdb.invoice.find({ "_id": bson.ObjectId(invoice), 'history.article': comp, 'history.symbol': symbol}).count()
        print(">>>>>>>", element_id)

        push_json = {
            'bilance_planned': bilance_plan,
            'bilance': bilance,
            'article': comp,
            'price': price,
            'symbol': symbol,
            'type': self.get_argument('type', None)
        }

        if int(element_id) == -1:
            self.mdb.invoice.update(
                { "_id": bson.ObjectId(invoice)},
                { "$push": { 'history': push_json }}, upsert=True)
        else:
            self.mdb.invoice.update(
                { "_id": bson.ObjectId(invoice)},
                { "$set": { 'history.{}'.format(element_id): push_json }}, upsert=True)
    
        print("......")
        print(out)
    
        '''
        out = self.mdb.invoice.find({'_id': bson.ObjectId(invoice), 'history.article': comp}).count()
        if out < 1:
            oper = '$push'
        else:
            oper = '$push'

        out = self.mdb.invoice.update({'_id': bson.ObjectId(invoice)},{
                oper:{'history': {
                        'bilance_planned': bilance_plan,
                        'bilance': bilance,
                        'article': comp,
                        'price': price,
                        'symbol': symbol,
                        'type': self.get_argument('type', None)
                }}
            })
        '''



        #out = self.mdb.stock_movements.insert({'stock': stock, 'operation':'buy', 'product': comp, 'supplier': supplier, 'type': ctype, 'bilance': float(bilance), 'bilance_plan': bilance_plan, 'price': float(price), 'invoice': invoice,  'description':description, 'user':self.logged})
        #self.mdb.invoice.update({'_id': bson.ObjectId(invoice)}, {'$push':{ 'elements':{'_id': bson.ObjectId(out)}} })
        
        print('invoice', invoice)
        print(out)
        self.LogActivity('store', 'prepare_invoice_row')
        self.write('ACK-prepare_invoice_row');