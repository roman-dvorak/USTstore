#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
from . import BaseHandler, BaseHandlerOwnCloud
from . import save_file, upload_file
#from pyoctopart.octopart import Octopart
import json
import urllib
import bson
from bson import ObjectId
import datetime
import pandas as pd
from fpdf import FPDF
import os
import sys
sys.path.append("..")
from plugins.store_data.stock_counting import getLastInventory, getPrice, getInventory


def make_handlers(module, plugin):
        return [
             (r'/stocktaking/view/positions', plugin.view_positions),
        ]

def plug_info():
    #class base_info(object):
    return {
        "display": False,
        "module": "stocktaking",
        "name": "Stock taking - Positions overiew"
    }


##
##  Trida, pro prehled skladu rozrazeny do kategorii
##
class view_positions(BaseHandler):
    def get(self):
        print("TEST...")
        self.authorized(['inventory'])

        # categories = list(self.mdb.category.aggregate([]))

        # # seradit kategorie tak, aby to odpovidalo adresarove strukture
        # paths = set()
        # for x in categories:
        #     paths.add(x['path']+x['name'])
        # paths = sorted(list(paths))

        # data = []
        # data = list(data)
        
        # for i, path in enumerate(paths):
        #     data += [{}]
        #     data[i]['path'] = path
        #     print(path.split('/')[-1])
        #     data[i]['level'] = len(path.split('/'))-2
        #     data[i]['category'] = path

        #     cat_modules = self.mdb.stock.aggregate([
        #         {'$match': {'category.0': path.split('/')[-1]}},
        #         {'$addFields': {'count': {'$sum': '$history.bilance'}}},
        #         {'$sort': {'name': 1}}
        #     ])
        #     data[i]['modules'] = list(cat_modules)
        #     cat_elements = 0
        #     cat_sum = 0
        #     cat_sum_bilance = 0
        #     inventura = True

        #     for module in data[i]['modules']:
        #         #module['inventory'] = getInventory(module, datetime.datetime(2018, 10, 1), None, False)
        #         module['inventory'] = getLastInventory(module, datetime.datetime(2018, 10, 1), False)
        #         if module['inventory']:
        #             module['count'] = module['inventory']
        #         module['inventory'] = bool(module['inventory'])
        #         module['price_sum'] = getPrice(module)
        #         if module['count'] > 0:
        #             module['price'] = module['price_sum']/module['count']
        #         else:
        #             module['price'] = 0

        #         module['inventory_2018'] = {'bilance_count': None, 'bilance_price': None}
        #         (module['inventory_2018']['count'], module['inventory_2018']['price']) = getInventory(module, datetime.datetime(2018, 1, 1), datetime.datetime(2018, 10, 1), False)
        #         module['inventory_2018']['bilance_count'] = module['count'] - module['inventory_2018']['count']
        #         module['inventory_2018']['bilance_price'] = module['price_sum'] - module['inventory_2018']['price']*module['inventory_2018']['count']

        #         cat_sum += module['price_sum']
        #         cat_elements += module['count']
        #         cat_sum_bilance += module['inventory_2018']['bilance_price']
        #         inventura &= (module['inventory'] or (module['count']==0))


        #     data[i]['cat_sum'] = cat_sum
        #     data[i]['cat_sum_bilance'] = cat_sum_bilance
        #     data[i]['cat_elements'] = cat_elements
        #     data[i]['cat_inventura'] = inventura

    # ziskej aktualni sklad
        warehouse = self.get_warehouse()

    # Ziskej pozice tohoto skladu
        positions = self.warehouse_get_positions(warehouse['_id'])
        positions_id = set([ pos['_id'] for pos in positions ])
        print(positions_id)
    # 
        data = {None:{'name': "Bez pozice", "list": []}}

        for position in positions:
            data[ position['_id'] ] = {"name": position['name'], "list": [], "position_info": position}

        #print(data)

        articles = self.mdb.stock.aggregate([])

        for article in articles:
            position = False
            for article_position in article.get('position', []):
                if article_position['posid'] in positions_id:
                    #print("article_position", article_position)
                    if article_position['primary']:
                        data[article_position['posid']]['list'].append(article)
                        position = True

            if position == False:
                data[None]['list'].append(article)

            #print(data)
            #position in positions()

        for position_id in data:
            data[position_id]['info'] = {}
            data[position_id]['info']['count'] = len(data[position_id]['list'])




        self.render("stocktaking.view.positions.hbs", data=data, positions = positions)
        #self.write("TEST")