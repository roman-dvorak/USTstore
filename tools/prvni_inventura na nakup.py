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
        if comp['type'] == 'inventory' and "Inventura 2018" in comp['description']:
            n += 1
            print(i, n, comp)
            db.stock_operation.update(
                {"_id": comp['_id']},
                {"$set": {"type": "buy", "description": "prevedeno na nakup | "+comp['description']}}
            )


    except Exception as e:
        print(e)

print(i, "celkem mame tolik polozek, to je tedy posledni Barcode ID")
print(n, "upraveno polozek")
