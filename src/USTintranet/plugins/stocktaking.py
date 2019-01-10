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

import sys
sys.path.append("..")
from plugins.store_data.stock_counting import getLastInventory, getPrice, getInventory


def make_handlers(module, plugin):
        return [
             (r'/{}/get_item/'.format(module), plugin.load_item),
             (r'/{}/save_item/'.format(module), plugin.save_stocktaking),
             (r'/{}/event/(.*)/save'.format(module), plugin.stocktaking_eventsave),
             (r'/{}/event/lock'.format(module), plugin.stocktaking_eventlock),
             (r'/{}/event/(.*)'.format(module), plugin.stocktaking_event),
             (r'/{}/events'.format(module), plugin.stocktaking_events),
             (r'/{}/view/categories'.format(module), plugin.view_categories),
             (r'/{}'.format(module), plugin.home),
             (r'/{}/'.format(module), plugin.home),
        ]

def plug_info():
    #class base_info(object):
    return {
        "module": "stocktaking",
        "name": "Stack taking"
    }


class home(BaseHandler):
    def get(self):
        current = self.mdb.intranet.find_one({'_id': 'stock_taking'})['current']
        if current: stocktaking_info = self.mdb.stock_taking.find_one({'_id': current})
        else: stocktaking_info = None

        self.render('stocktaking.home.hbs', stocktaking = stocktaking_info)


##
##  Trida, pro prehled skladu rozrazeny do kategorii
##
class view_categories(BaseHandler):
    def get(self):

        categories = list(self.mdb.category.aggregate([]))

        # seradit kategorie tak, aby to odpovidalo adresarove strukture
        paths = set()
        for x in categories:
            paths.add(x['path']+x['name'])
        paths = sorted(list(paths))

        data = []
        data = list(data)
        
        for i, path in enumerate(paths):
            data += [{}]
            data[i]['path'] = path
            print(path.split('/')[-1])
            data[i]['level'] = len(path.split('/'))-2
            data[i]['category'] = path

            cat_modules = self.mdb.stock.aggregate([
                {'$match': {'category.0': path.split('/')[-1]}},
                {'$addFields': {'count': {'$sum': '$history.bilance'}}},
                {'$sort': {'name': 1}}
            ])
            data[i]['modules'] = list(cat_modules)
            cat_elements = 0
            cat_sum = 0
            cat_sum_bilance = 0
            inventura = True

            for module in data[i]['modules']:
                #module['inventory'] = getInventory(module, datetime.datetime(2018, 10, 1), None, False)
                module['inventory'] = getLastInventory(module, datetime.datetime(2018, 10, 1), False)
                if module['inventory']:
                    module['count'] = module['inventory']
                module['inventory'] = bool(module['inventory'])
                module['price_sum'] = getPrice(module)
                if module['count'] > 0:
                    module['price'] = module['price_sum']/module['count']
                else:
                    module['price'] = 0

                module['inventory_2018'] = {'bilance_count': None, 'bilance_price': None}
                (module['inventory_2018']['count'], module['inventory_2018']['price']) = getInventory(module, datetime.datetime(2018, 1, 1), datetime.datetime(2018, 10, 1), False)
                module['inventory_2018']['bilance_count'] = module['count'] - module['inventory_2018']['count']
                module['inventory_2018']['bilance_price'] = module['price_sum'] - module['inventory_2018']['price']*module['inventory_2018']['count']

                cat_sum += module['price_sum']
                cat_elements += module['count']
                cat_sum_bilance += module['inventory_2018']['bilance_price']
                inventura &= (module['inventory'] or (module['count']==0))


            data[i]['cat_sum'] = cat_sum
            data[i]['cat_sum_bilance'] = cat_sum_bilance
            data[i]['cat_elements'] = cat_elements
            data[i]['cat_inventura'] = inventura
        self.render("stocktaking.view.categories.hbs", data=data, category = data)


class load_item(BaseHandler):
    def post(self):
        self.set_header('Content-Type', 'application/json')
        item = self.get_argument('_id', None)
        print("ARGUMENT JE....", item)
        #self.write(item)
        out = {}
        out['item'] = self.mdb.stock.find_one({'_id': item})
        out['history'] = list(self.mdb.stock.aggregate([
                {
                    '$match':{'_id': item}
                },{
                    '$unwind': '$history'
                },{
                    '$group' : {
                        '_id' : '$history.stock',
                        'bilance': { '$sum': '$history.bilance' },
                    }
                }]))
        out = bson.json_util.dumps(out)
        self.write(out)

class save_stocktaking(BaseHandler):
    def post(self):
        
        self.set_header('Content-Type', 'application/json')
        stock = self.get_argument('stock', 'pha01')
        description = self.get_argument('description', None)
        bilance = self.get_argument('bilance')
        absolute = self.get_argument('absolute')
        item = self.get_argument('_id', None)

        current = self.mdb.intranet.find_one({'_id': 'stock_taking'})['current']
        if not current:
            raise tornado.web.HTTPError(500)
        else:
            print("service_push >>", item, stock, description, bilance, absolute)
            data = {
                    '_id': bson.ObjectId(),
                    'stock': stock,
                    'operation': 'inventory',
                    'bilance': float(bilance),
                    'absolute': float(absolute),
                    'inventory': current,
                    'description': description,
                    'user':self.logged,
                    }
            
            out = self.mdb.stock.update(
                    {'_id': item},
                    {
                        '$push': {'history':data}
                    }
                )
            
            #TODO: remove TAG creation
            out = self.mdb.stock.update(
                    {'_id': item},
                    {
                        '$push': {"tags": {'id': 'inventura2019', 'date': datetime.datetime.utcnow()}}
                    }
                )
            
            self.write(bson.json_util.dumps(data))


class stocktaking_events(BaseHandler):
    '''
        Slouzi k ziskani prehledu o vsech Vytvorenych kampanich. 

    '''
    def get(self):
        self.render('stocktaking.events.hbs')

    def post(self):
        self.set_header('Content-Type', 'application/json')
        events = list(self.mdb.stock_taking.find())
        stocktaking = self.mdb.intranet.find_one({'_id': 'stock_taking'})

        for event in events:
            print(event['_id'])
            event['id'] = str(event['_id'])
            event['opened_from'] = str(event['opened'].date())
            event['opened_to'] = str(event['closed'].date())
            event['status'] = int(stocktaking['current'] == event['_id'])

        out = bson.json_util.dumps(events)
        self.write(out)



class stocktaking_event(BaseHandler):
    '''
        Slouzi k ziskani informaci o jedne inventurovaci kampani.
    '''
    def post(self, id):
        print(id)
        self.set_header('Content-Type', 'application/json')
        stocktaking = self.mdb.intranet.find_one({'_id': 'stock_taking'})
        event = self.mdb.stock_taking.find_one({"_id": bson.ObjectId(id)})

        event['id'] = str(event['_id'])
        event['opened_from'] = str(event['opened'].date())
        event['opened_to'] = str(event['closed'].date())
        event['status'] = int(stocktaking['current'] == event['_id'])

        out = bson.json_util.dumps(event)
        self.write(out)


class stocktaking_eventlock(BaseHandler):
    '''
        Uzamkne otevrenou kampan. Nepujde provadet inventura.
    '''
    def post(self):
        self.mdb.intranet.update({'_id': 'stock_taking'}, {'$set':{'current': None}})
        self.write("OK")

class stocktaking_eventsave(BaseHandler):
    '''
        Slouzi k ulozeni dat o inventure. Zaloven zapise globalni parametr s id aktualni invetury.
    '''
    def post(self, id):
        data = {'name': self.get_argument('name'),
                'opened': datetime.datetime.strptime(self.get_argument('from'), '%Y-%m-%d'),
                'closed': datetime.datetime.strptime(self.get_argument('to'), '%Y-%m-%d'),
                'status': self.get_argument('status'),
                'author': self.get_argument('author'),
                }

        if id == 'new':
            data['history'] = []
            data['documents'] = []
            id = str(self.mdb.stock_taking.insert(data))
        else: #TODO: dodelat overeni, ze se jedna o legitimni ObjectID
            self.mdb.stock_taking.update({'_id': bson.ObjectId(id)}, {'$set':data}, False, True)
        
        # ulozit aktualni inventuru
        if data['status']: self.mdb.intranet.update({'_id': 'stock_taking'}, {'$set':{'current': bson.ObjectId(id)}})
        self.write(id)
