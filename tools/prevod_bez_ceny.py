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

components = list(db.stock_operation.find())
n = 0

for i, comp in enumerate(components):
    try:
        print("====================================")
        #print(comp)
        if comp['type'] == 'import' and "Presun do jineho sacku" in comp['description']:
            
            print(i, n, comp)

            l = list(db.stock.aggregate([
                    {"$match": {"packets._id": comp['pid']}},
                    {"$unwind": "$packets"},
                    {"$match": {"packets._id": comp['pid']}}
                ]))[0]

            #print(l)

            if "Vytvoreno oddelenim" in l['packets']['description']:
                n += 1
                src_pid = l['packets']['description'].split(" ")[3]
                src_pid = ObjectId(src_pid)
                print(l)
                print("To je ono ... :) ", src_pid)


            m = list(db.stock_operation.aggregate([
                    {"$match": {"pid": src_pid, "type": "buy", "unit_price": {"$gt": 0}}},
                    {"$sort": {"date": 1}},
                ]))
            print(">>>", m)
            print("cena", m[0]['unit_price'])
            up = m[0]['unit_price']

            db.stock_operation.update(
                {"_id": comp['_id']},
                {"$set": {"unit_price": float(up), "description": "Oprava ceny pri importu | "+comp['description']}}
            )


    except Exception as e:
        print(e)

print(i, "celkem mame polozek")
print(n, "upraveno polozek")
