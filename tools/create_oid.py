

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

for i, comp in enumerate(components):
    try:
        print("====================================")

        pprint(comp)

        oldid = comp['_id']
        dummy_id = ObjectId()
        main_code = "USTa{:x}".format(i)
        comp['barcode'] = [main_code, comp['_id']]
        comp['primary_barcode'] = 0
        comp['_id'] = ObjectId(dummy_id)
        comp['sn_required'] = False

        print("----------")
        pprint(comp)

        db.stock.insert(comp)
        db.stock.remove({'_id': oldid})

    except Exception as e:
        print(e)

    print(i, "celkem mame tolik polozek, to je tedy posledni Barcode ID")
