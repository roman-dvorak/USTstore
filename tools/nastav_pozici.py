

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
        print(comp['name'])
        db.stock.update(
            {"_id": ObjectId(comp['_id'])},
            {"$set": {"position": [{'posid': ObjectId("5c709fa012875079fd76e238"), 'primary': True}]}}
        )


    except Exception as e:
        print(e)

print(i, "celkem mame tolik polozek, to je tedy posledni Barcode ID")
