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

from plugins.helpers.warehouse import *

def get_plugin_handlers():
        return [
             (r'/stocktaking/view/positions', view_positions),
        ]

def get_plugin_info():
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

    # Zobrazit pouze primarni pozice
        only_primary = False

    # Ziskej ID aktualni inventury
        current_inventory = get_current_inventory(self.mdb)

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
            #print('article:', article['name'])
            article['warehouse_unit_price'] = update_article_price(self.mdb.stock, article['_id'])
            article['has_inventory'] = has_article_inventory(article, current_inventory['_id']).get(warehouse['_id'], False)
            position = False
            article['in_stock'] = False
            for article_position in article.get('position', []):
                if article_position['posid'] in positions_id:
                    #print("article_position", article_position)
                    if article_position['primary'] or not only_primary:
                        data[article_position['posid']]['list'].append(article)
                        position = True

            if position == False:
                data[None]['list'].append(article)

            #print(data)
            #position in positions()
            for history in article.get('history', []):
                if history.get('stock', 'None') == warehouse['_id']:
                    article['in_stock'] = True
                    continue

        for position_id in data:
            data[position_id]['info'] = {}
            data[position_id]['info']['count'] = len(data[position_id]['list'])


        self.render("stocktaking.view.positions.hbs", data=data, positions = positions, warehouse = warehouse, get_warehouse_count = get_warehouse_count, inventory =current_inventory)
        #self.write("TEST")
