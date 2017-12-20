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

def make_handlers(module, plugin):
        return [
             (r'/%s' %module, plugin.hand_bi_home),
             (r'/%s/' %module, plugin.hand_bi_home),
             (r'/%s/print/' %module, plugin.print_layout),
             (r'/%s/api/(.*)/' %module, plugin.api)
        ]

def plug_info():
    return{
        "module": "plug_info",
        "name": "plug_info"
    }


class print_layout(BaseHandler):
    def get(self, data = None):

        components = self.get_arguments('action[]')
        multiply = int(self.get_argument('multiply', 5))
        layout = self.get_argument('template', '70x40_simple')
        print(components)
        comp = self.mdb.stock.find({'_id' : {'$in' : components}})
        print(comp.count())
        self.render("store.print.%s.hbs" %layout, components = comp, multiply = multiply)


class api(BaseHandler):
    def post(self, data=None):
        self.set_header('Content-Type', 'application/json')
        print(data)
        print(self.request.arguments)

        ascii_list_to_str = lambda input: [x.decode('ascii') for x in input]

        if data == 'product':
            print(self.request.arguments.get('selected[]', None))
            dout = list(self.mdb.stock.find({self.get_argument('key', '_id'):self.get_argument('value','')}).sort([("_id",1)]))
            dout += [list(self.mdb.stock_movements.aggregate([{
                '$match':{'product': self.get_argument('value', '')}
                },{
                    '$group' : {
                        '_id' : '$stock',
                        'bilance': { '$sum': '$bilance' },
                    }
                }]))]

        elif data == 'products':
            selected = (self.request.arguments.get('selected[]', []))
            page = self.get_argument('page', 0)
            page_len = 100
            search = self.get_argument('search')#.decode('ascii')
            print("SEARCH", search)
            dout = []
            dbout = self.mdb.stock.aggregate([{
                    '$skip' : int(page_len)*int(page)
                },{
                    '$limit' : int(page_len)
                },{
                    '$match': {'_id': { '$regex': search, '$options': 'ix'}} 
                },{
                    "$unwind": "$category"
                },{
                    "$lookup":{
                        "from": "category",
                        "localField": "category",
                        "foreignField": "name",
                        "as": "category"
                    }
                },{
                    "$match": {"_id": {'$ne': []}}
                }], useCursor=True)

            dbout = list(dbout)

            for x in dbout:
                print("=================")
                rm = True
                #if not len(x['category']) and 'uncat' in  ascii_list_to_str(selected):
                #if 1 > len(x['category']):
                #        rm = False
                for i, y in enumerate(x['category']):
                    #print(y)
                    
                    #print(y['name'])
                    if y['name'] in ascii_list_to_str(selected):
                        #print("nalezeno")
                        rm = False
                if not rm:
                    #print("+")
                    #print(y)
                    dout.append(x)

        output = bson.json_util.dumps(dout)
        #print(output)
        self.write(output)


class hand_bi_home(BaseHandler):
    def get(self, data=None):
        print("Store")
        #cat = {}
        cat = list(self.mdb.category.find({}))
        #cat = []
        self.render("store.home.hbs", title="UST intranet", parent=self, category = cat)
