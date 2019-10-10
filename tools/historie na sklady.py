

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
        #print("====================================")
        for j, h in enumerate(comp['history']):
            if h['stock'] in [ObjectId("5c709fa012875079fd76e238"), ObjectId("5c709fb412875079fd76e249")]:
                pass
                #print("..", h)
            else:
                print("Spatne", h)
                db.stock.update(
                    {"_id": ObjectId(comp['_id'])},
                    {"$set": {"history.{}.stock".format(j): ObjectId("5c709fb412875079fd76e249")}}
                )


    except Exception as e:
        print(e, comp['name'])

print(i, "celkem mame tolik polozek, to je tedy posledni Barcode ID")
