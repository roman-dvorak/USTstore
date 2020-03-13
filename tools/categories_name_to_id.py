

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

        for i, c in enumerate(comp['category']):
            cat = db.category.find({'name': c})
            print(c, cat[0]['_id'])
            comp['category'][i] = cat[0]['_id']


        db.stock.update({"_id": comp['_id']}, {"$set": {"category": comp['category']}})
        #print(bson.json_util.dumps(overview, indent=2))
        #print(colored("![component_update_counts]", "yellow", attrs=["bold"]))
        

    except Exception as e:
        print(e)
