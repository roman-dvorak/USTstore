

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




def base(num, symbols="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", b=None):
    if not b:
        b = len(symbols)
    return ((num == 0) and symbols[0]) or (base(num // b, symbols, b).lstrip(symbols[0]) + symbols[num % b])

def barcode(hex):
    print(int(hex, 16))
    code = blake2s(bytes(hex, 'utf-8'), digest_size=6)
    code = int(code.hexdigest(), 16)
    print(code)
    code = base(code, b=62)
    code += code[1]
    code += code[0]
    return code

client = pymongo.MongoClient('localhost', 27017)
db = client.USTintranet

components = db.stock.find()

for i, comp in enumerate(components):
    try:
        print("====================================")

        #pprint(comp)
        oldid = comp['_id']
        dummy_id = ObjectId()
        main_code = barcode(str(dummy_id))
        comp['barcode'] = [main_code, comp['_id']]
        comp['primary_barcode'] = 0
        comp['_id'] = ObjectId(dummy_id)
        comp['sn_required'] = False

        print(main_code)
        db.stock.insert(comp)
        db.stock.remove({'_id': oldid})

    except Exception as e:
        print(e)

print(i, "celkem mame tolik polozek, to je tedy posledni Barcode ID")
