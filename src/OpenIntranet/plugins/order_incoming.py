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

def get_plugin_handlers():
        module = 'invoice_import'
        return [
             (r'/{}/get_invoices/'.format(module), get_invoices),
             (r'/{}/get_invoice/'.format(module), get_invoice),

    # pro vytvoreni nove objednavky
             (r'/{}/invoice/edit/'.format(module), invoice_edit),
             (r'/{}/invoice/edit'.format(module), invoice_edit),
             (r'/{}/invoice/(.*)/edit'.format(module), invoice_edit),
             (r'/{}/invoice/(.*)/edit/'.format(module), invoice_edit),

             (r'/{}/invoice/(.*)/push_item/'.format(module), push_item),

             (r'/{}/save_invoice/'.format(module), save_invoice),
             (r'/{}/invoice/prepare_invoice_row/'.format(module), prepare_invoice_row),
             (r'/{}/next_state/'.format(module), invoice_next_state),
             (r'/{}/invoice/(.*)/'.format(module), invoice),
             (r'/{}'.format(module), home),
             (r'/{}/'.format(module), home),
             #(r'/%s' %module, home),
             #(r'/%s/' %module, home),
        ]

def get_plugin_info():
    return{
        "role": ['invoice', 'invoice-access'],
        "name": "invoice_import",
        "entrypoints": [
            {
                "title": "Importování faktur",
                "url": "/invoice_import",
                "icon": "assignment_returned",
            }
        ]
    }


class home(BaseHandler):
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


        state = list(self.mdb.invoice.find({ "_id": bson.ObjectId(invoice)}))[0].get('state', 0)
        print(state)
        if state > 3 or self.is_authorized(['invoice-sudo', 'invoice-validator']):
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
                    { "$push": { 'items': push_json }}, upsert=True)
            else:
                self.mdb.invoice.update(
                    { "_id": bson.ObjectId(invoice)},
                    { "$set": { 'items.{}'.format(element_id): push_json }}, upsert=True)
        else:
            raise tornado.web.HTTPError(status_code=401, log_message="Nemáte dostatečná oprávnění pro tuto operaci.")

        self.LogActivity('store', 'prepare_invoice_row')
        self.write('ACK-prepare_invoice_row');


class invoice_next_state(BaseHandler):
    def post(self):
        print("INVOICE NEXT STATE")
        cid = bson.ObjectId(self.get_argument('id'))
        state = int(list(self.mdb.invoice.find({'_id': cid}))[0].get('state', 0))

        if state == 4 and self.is_authorized(['invoice-access', 'invoice-sudo', 'invoice_import', 'invoice-validator'], sudo=False):
            print("4 -- 3")
            self.mdb.invoice.update({'_id': cid}, {'$inc': {'state': -1}})
            self.write('OK')
        # validace
        elif state == 3 and self.is_authorized(['invoice-sudo', 'invoice-validator'], sudo=False):
            print("3 --- 2")
            self.mdb.invoice.update({'_id': cid}, {'$inc': {'state': -1}})
            self.write('OK')

        #naskladneni
        elif state == 2 and self.is_authorized(['invoice-sudo', 'invoice-reciever'], sudo=False):
            print("2 --- 1")
            self.mdb.invoice.update({'_id': cid}, {'$inc': {'state': -1}})
            self.write('OK')
        # validace
        elif state == 1 and self.is_authorized(['invoice-sudo', 'invoice-validator'], sudo=False):
            print("1 --- 0")
            self.mdb.invoice.update({'_id': cid}, {'$inc': {'state': -1}})
            self.write('OK')
        else:
            print("AUTHORIZED PROBLEM ....", self.role)
            raise tornado.web.HTTPError(status_code=401, log_message="Nemáte dostatečná oprávnění pro tuto operaci.")

class invoice_edit(BaseHandler):
    def get(self, iid = None):

        self.render("invoice/invoice.items.edit.hbs", invoiceid = iid)

class push_item(BaseHandler):
    def post(self, iid):
        sid = bson.ObjectId(self.get_argument('sid'))   #id of stock item
        supplier = self.get_argument('supplier', -1)    #index of supplier in array
        count = self.get_argument('count', 0.0)

        print("iid:", iid)
        print("Pridavam polozku", iid, sid, supplier, count)
