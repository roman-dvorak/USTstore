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
        "name": "stocktaking_view_positions",
        "entrypoints": [],
        # "name": "Stock taking - Positions overiew"
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
        #print(positions_id)
    #
        data = {None:{'name': "Bez pozice", "list": []}}

        for position in positions:
            data[ position['_id'] ] = {"name": position['name'], "list": [], "position_info": position}

        #print(data)

        query = [
            { "$group": {
                '_id': '$pid',
                'operations': { "$push": "$$ROOT" }
                }
            },
            { "$addFields": {
                    "packet_count":  {"$sum": "$operations.count"},
                    "packet_reserv":  {"$sum": "$operations.reserv"},
                    "packet_ordered":  {"$sum": "$operations.ordered"},
                    "packet_price": {
                    "$function":
                        {
                            "body": '''function(prices, counts) {
                             let total_counts = Array.sum(counts);
                             var tmp_count = total_counts;
                             var total_price = 0;

                             var c = counts.reverse();
                             var p = prices.reverse();

                             for(i in c){
                                 if(c[i] > 0){
                                     if(c[i] < tmp_count){
                                         total_price += (c[i]*p[i]);
                                         tmp_count -= c[i]
                                      }
                                      else{
                                         total_price += (tmp_count*p[i]);
                                         tmp_count = 0;
                                      }
                                }

                             }
                             return total_price;
                            }''',
                            "args": ["$operations.unit_price", "$operations.count"], "lang": "js"
                        }
                    }
                }
            },
            #{"$addFields": {"comp": "$pid"}},
            {
            "$lookup":
                {
                    "from": "stock",
                    "let": {"pid": "$_id"},
                    "pipeline": [
                        { "$match": { "$expr": { "$in": ["$$pid", "$packets._id"]}}},
                        { "$unwind": "$packets" },
                        { "$match": { "$expr": { "$eq": ["$packets._id", "$$pid"]}}},
                    ],
                    "as": "component"
                }
            },
            { "$set": { "component": {"$first": "$component"}}},

            {
            "$lookup":
                {
                    "from": "store_positions_complete",
                    "localField": "component.packets.position",
                    "foreignField": "_id",
                    "as": "position_info",
                }
            },
            { "$set": { "position_info": {"$first": "$position_info"}}},

            { "$sort": {"position_info.warehouse.code": 1, "position_info.path_string": 1, "position_info.name": 1, "component.name":1}},

            #{ "$project": { "packet_count": 1, "packet_reserv": 1, "packet_price": 1, "packet_ordered": 1, "_id": 0} },
            # { "$group": {
            #     '_id': 'null',
            #     'count': {"$sum": '$packet_count'},
            #     'price': {"$sum": '$packet_price'},
            #     'reserv': {"$sum": '$packet_reserv'},
            #     'ordered': {"$sum": '$packet_ordered'},
            #     }
            # }
        ]
        packets = list(self.mdb.stock_operation.aggregate(query))
        # print(packets)
        
        self.render("stocktaking.view.positions.hbs", packets = packets, positions = data, warehouse = warehouse, get_warehouse_count = get_warehouse_count, inventory =current_inventory)
        #self.write("TEST")
