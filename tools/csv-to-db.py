import csv
import pymongo
import json
import urllib.request
import re
import sys


client = pymongo.MongoClient('localhost', 27017)
db = client.USTintranet

apikey = 'f158279b'

def match(name):
    url = 'http://octopart.com/api/v3/parts/match?'
    url += '&queries=[{"mpn":"%s"}]' %(name)
    url += '&apikey='+apikey
    url += '&pretty_print=true'

    #data = urllib.urlopen(url).read()
    #response = json.loads(data)

    print(url)
    with urllib.request.urlopen(url) as url:
        print(url)
        response = url.read()

    return response

file = sys.argv[1]
with open(file, 'rt', encoding='utf-8') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',')
    for row in spamreader:
        

        print(row)
        part = {}
        operation = {}

        if row[4] == '': row[4] = '0'
        if row[5] == '': row[5] = '0'

        part['_id'] = row[1].strip()
        part['name'] = row[0].strip()
        part['description'] = row[2].strip()
        part['category'] = [row[7].strip()]
        part['price'] = float(row[4].replace(',', '.'))
        part['parameters'] = {}
        part['supplier'] = []
        part['stock'] = {'pha01':{}, 'sob01':{'count':0}}
        part['stock']['pha01']['count'] = float(row[5].replace(',', '.'))
        part['tags'] = {'imported':{}}

        operation['product'] = row[1].strip()
        operation['operation'] = 'buy'
        operation['bilance'] = float(row[5].replace(',', '.'))
        operation['price'] = float(row[4].replace(',', '.'))
        operation['stock'] = 'pha01'

        print (part)
        #print (operation)

        db.stock.update_one(
            {"_id": row[1].strip()},
            {'$set': part},
            upsert = True
        )
        '''
        db.stock_movements.insert_one(
           operation
        )
        '''