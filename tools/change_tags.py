import csv
import pymongo
import json
import urllib.request
import re
import sys


client = pymongo.MongoClient('localhost', 27017)
db = client.USTintranet
# Tohle vezme vsechny polozky a jejich pocty to presune do movements tabulky....



import csv
import pymongo
import json
import urllib.request
import re
import sys

client = pymongo.MongoClient('localhost', 27017)
db = client.USTintranet


components = db.stock.find()

for comp in components:
    try:
        print(comp['_id'])
        tags = comp['tags']
        tlist = list(tags.keys())
        tnew = []
        for tag in tlist:
            tnew.append({'id': tag})
        print(tnew)

        db.stock.update({'_id': comp['_id']}, {'$set': {'tags': tnew}})


        #print(">>> ", cena)
        #for stock in comp['stock']:
        #    pocet = float(comp['stock'][stock]['count'])
        #    if pocet > 0:
        #        print(">>", stock, pocet)
        #        db.stock_movements.insert({'product': comp['_id'], 'operation': 'inventory', 'price': cena, 'bilance': pocet, 'stock': stock, 'user': 'admin', 'description': 'Inventura 2018 (2018/05)'})

    except Exception as e:
        print(e)
    