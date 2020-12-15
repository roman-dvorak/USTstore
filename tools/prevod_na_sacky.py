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

components = db.stock.aggregate([
    # {"$match": {"_id": ObjectId('5c70984612875079b91f89e9')}},
    {"$lookup": {"from": 'store_positions', "localField":'position.posid', "foreignField": '_id', "as": 'position_info'}},
])

errs = set()

for i, comp in enumerate(components):
    try:
        print("====================================")
        # print(comp)
        position = None
        cid = comp['_id']
        stocks = set()


        # prevodni tabulka ze skladu na nezarazenou pozici
        stock = {
            ObjectId("5c67444e7e875154440cc28f"): None,# Praha
            ObjectId("5c67445b7e875154440cc297"): None,# sob provozovna
            ObjectId("5c67446b7e875154440cc299"): None,# Hvezdarna
        }
        stock_usage = {
            ObjectId("5c67444e7e875154440cc28f"): False,# Praha
            ObjectId("5c67445b7e875154440cc297"): False,# sob provozovna
            ObjectId("5c67446b7e875154440cc299"): False,# Hvezdarna
        }


        ## Ziskat pozice ve skladu (uprednostnit primarni a pak posledni)
        for j, p in enumerate(comp.get('position', [])):
            info = comp['position_info'][j]
            if p['primary']:
                stock[info['warehouse']] = p['posid']

        for j, p in enumerate(comp.get('position', [])):
            info = comp['position_info'][j]
            if not stock[info['warehouse']] or stock[info['warehouse']] in [ObjectId('5c709fa012875079fd76e238')]:
                stock[info['warehouse']] = p['posid']

        if not stock[ObjectId("5c67444e7e875154440cc28f")]: stock[ObjectId("5c67444e7e875154440cc28f")] = ObjectId('5c709fa012875079fd76e238')


        db.stock.update(
            {
                "_id": cid
            },
            {
                "$set": {"packets": []},
                #"$set": {"parameters": {}}
            }
        )

        for j, h in enumerate(comp.get('history', [])):
            if not 'stock' in h: h['stock'] = ObjectId("5c67444e7e875154440cc28f")
            if not stock_usage[h['stock']]:
                pid = ObjectId()
                stock_usage[h['stock']] = pid
                print("Vytvorim novy sacek {}".format(pid))
                query = {
                    "$push": {
                        "packets": {
                            '_id': pid,
                            'type': 'zip_bag',
                            'supplier': 'null',
                            'position': stock[h['stock']],
                            'description': 'Vytvoreno pri aktualizaci databaze'
                        }
                    }
                }
                db.stock.update(
                    {
                        "_id": cid
                    },
                    query
                )


        for j, h in enumerate(comp.get('history', [])):
            print("* ",j, h)
            pos = stock[h['stock']]

            query = {
                    "pid": stock_usage[h['stock']],
                    "count" : h.get('bilance', 0),
                    "unit_price": h.get('price', 0),
                    "type" : h.get('operation', 'service'),
                    "date" : h['_id'].generation_time,
                    "user" : h.get('user', 'null'),
                    "invoice" : h.get('invoice'),
                    "supplier" : h.get('supplier'),
                    "description" : "upgrade, " + h.get('description', '')
                }
            print(query)
            db.stock_operation.insert(query)

            # db.stock.update({
            #     "_id": cid
            # }, {
            #     "$push": {
            #         "packets": {
            #             '_id': pid,
            #             'type': 'zip_bag',
            #             'supplier': 'null',
            #             'position': 'null',
            #             'description': 'Vytvoreno oddelenim z {}'.format(src)
            #         }
            #     }
            # })
        # print(positions)



    except Exception as e:
        print("chyba", e)
        errs.add((comp['_id'], comp['name'], e))

print(i, "celkem mame tolik polozek")
for e in errs:
    print(e)
