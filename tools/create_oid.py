

from pprint import pprint
import csv
import pymongo
import json
import urllib.request
import re
import sys
import datetime
from bson import ObjectId


client = pymongo.MongoClient('localhost', 27017)
db = client.USTintranet


components = db.stock.find()

for comp in components:
    try:
        print("====================================")

        pprint(comp)
        
        oldid = comp['_id']
        dummy_id = ObjectId()
        
        comp['barcode'] = [comp['_id']]
        comp['_id'] = ObjectId(dummy_id)

        print("----------")
        pprint(comp)

        db.stock.insert(comp)
        db.stock.remove({'_id': oldid})

    except Exception as e:
        print(e)
    