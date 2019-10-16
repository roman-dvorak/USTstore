

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
    try:
        #print("====================================")
        for j, h in enumerate(comp['history']):
            if h['stock'] in [ObjectId("5c67446b7e875154440cc299"), ObjectId("5c67444e7e875154440cc28f"), ObjectId("5c67445b7e875154440cc297")]:
                pass
            else:
                print("Spatne", h)
                db.stock.update(
                    {"_id": ObjectId(comp['_id'])},
                    {"$set": {"history.{}.stock".format(j): ObjectId("5c67444e7e875154440cc28f")}}
                )


    except Exception as e:
        print(e, comp['name'])

print(i, "celkem mame tolik polozek, to je tedy posledni Barcode ID")
