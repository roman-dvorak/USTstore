

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
db = client.USTintranet

components = db.stock.find()

for i, comp in enumerate(components):
    try:
        print("====================================")
        for j, h in enumerate(comp['history']):
            #print(h)
            if h['stock'] == 'pha01':
                print(j,"PRAHA")
                db.stock.update(
                    {"_id": ObjectId(comp['_id'])},
                    {"$set": {"history.{}.stock".format(j): ObjectId("5c68ad767e875154440d4dd8")}}
                )

            elif h['stock'] == 'sob01':
                print(j,'SOBESLAV')
                db.stock.update(
                    {"_id": ObjectId(comp['_id'])},
                    {"$set": {"history.{}.stock".format(j): ObjectId("5c68ad8e7e875154440d4de0")}}
                )


    except Exception as e:
        print(e)

print(i, "celkem mame tolik polozek, to je tedy posledni Barcode ID")
