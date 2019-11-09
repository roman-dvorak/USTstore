

from pprint import pprint
import csv
import pymongo
import json
import urllib.request
import re
import sys
import datetime
from bson import ObjectId
import hashids
from hashlib import blake2b, blake2s
import time


client = pymongo.MongoClient('localhost', 27017)
db = client.USTdev

components = db.stock.find()

for i, comp in enumerate(components):
    print("comp", i, comp['_id'])
    try:

        out = list(db.stock.aggregate([
            {"$match": {"_id": comp['_id']}},
            {"$unwind": "$history"},

        ]))
        out = list(out)

        overview = {
            'count':{
                'onstock': 0,
                'requested': 0,
                'ordered': 0
            },
            'stocks': {}
        }
        for operation in out:
            operation = operation['history']
            warehouse = str(operation.get('stock', "5c67444e7e875154440cc28f"))
            print(warehouse)
            
            if warehouse not in overview['stocks']:
                overview['stocks'][warehouse] = {
                    'count':{
                        'onstock': 0,
                        'requested': 0,
                        'ordered': 0
                    }
                    #'name': self.get_warehouse(warehouse)['name']
                }

            if "operation" not in operation:
                overview['stocks'][warehouse]['count']['onstock'] += operation['bilance']
                overview['count']['onstock'] += operation['bilance']

            elif operation['operation'] in ['inventory', 'service', 'sell', 'buy', 'move_in', 'move_out']:
                overview['stocks'][warehouse]['count']['onstock'] += operation['bilance']
                overview['count']['onstock'] += operation['bilance']

            elif operation['operation'] in ['buy_request']:
                overview['stocks'][warehouse]['count']['requested'] += operation['bilance']
                overview['count']['requested'] += operation['bilance']

            else:
                print("[NEZNAMA OPERACE]", operation['operation'])
                print(operation)

        print("Dokoncuji")
        db.stock.update({"_id": comp['_id']}, {"$set": {"overview": overview}})
        #print(bson.json_util.dumps(overview, indent=2))
        #print(colored("![component_update_counts]", "yellow", attrs=["bold"]))
        

    except Exception as e:
        print(e)
