import csv
import pymongo
import json
import urllib.request
import re
import sys

client = pymongo.MongoClient('localhost', 27017)
db = client.USTintranet

old_name = 'Faenell'
new_name = 'Farnell'

components = db.stock.find({'supplier.supplier': old_name})

for comp in components:
    try:
        print(comp['_id'])
        db.stock.update({'_id': comp['_id'], 'supplier.supplier': old_name}, {'$set': {'supplier.$.supplier': new_name}})


        #print(">>> ", cena)
        #for stock in comp['stock']:
        #    pocet = float(comp['stock'][stock]['count'])
        #    if pocet > 0:
        #        print(">>", stock, pocet)
        #        db.stock_movements.insert({'product': comp['_id'], 'operation': 'inventory', 'price': cena, 'bilance': pocet, 'stock': stock, 'user': 'admin', 'description': 'Inventura 2018 (2018/05)'})

    except Exception as e:
        print(e)
    