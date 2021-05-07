#!/usr/bin/python3
# -*- coding: utf-8 -*-

import json
import bson
import bson.json_util
from bson.json_util import dumps
from bson import *
from bson import ObjectId
import datetime

def get_packet(db, packet):

    packet_query = [{ '$match': {"packets._id": packet}},
                { "$project": {"packets": 1}},
                { "$unwind": '$packets'},
                { "$replaceRoot": {"newRoot": "$packets"}},
                { "$match": {"_id": packet}},
                { "$lookup": { "from": 'store_positions', "localField":'position', "foreignField": '_id', "as": 'position'}},
                { "$lookup": { "from": 'stock_operation', "localField":'_id', "foreignField": 'pid', "as": 'operations'}},
                { "$lookup": { "from": 'store_positions_complete', "localField":'position._id', "foreignField": '_id', "as": 'position'}},
                { "$lookup": { "from": 'stock', "let": { "packet_id": "$_id" }, "pipeline": [ {"$match": { "$expr": { "$in": ["$$packet_id", "$packets._id"]}}}, ], "as": "component" }  },
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
                ]
    print(packet_query)
    return list(db.stock.aggregate(packet_query))[0]


