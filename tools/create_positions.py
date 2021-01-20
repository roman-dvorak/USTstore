

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
#db = client.USTdev
db = client.USTintranet

for i in range(5, 71):
    print(i)
    data = {
            "name" : "PCB{:03d}".format(i),
            "text" : "PCB kapsa {:03d}".format(i),
            "parent" : ObjectId("5c84f5b41287500b4e027fe1"),
            "warehouse" : ObjectId("5c67444e7e875154440cc28f")
        }
    print(data)
    db.store_positions.insert_one(data)