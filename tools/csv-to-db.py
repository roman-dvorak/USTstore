import csv
import pymongo
import json
import urllib.request
import re


client = pymongo.MongoClient('localhost', 27017)
db = client.USTintranet

apikey = '*****'

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


with open('/home/roman/ownCloud/ust/c_0402.csv', 'rt', encoding='utf-8') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=';')
    for row in spamreader:
        
        #print(match(row[0]))
        prefix = 'C0402-'

        print(row)
        part = {}
        operation = {}
        part['_id'] = prefix+row[0]
        part['name'] = prefix+row[0]
        part['description'] = row[1]
        part['category'] = ['C_0402']
        part['price'] = float(row[3].replace(',', '.'))
        part['parameters'] = {}
        part['supplier'] = []

        operation['product'] = prefix+row[0]
        operation['operation'] = 'buy'
        operation['bilance'] = float(row[4].replace(',', '.'))
        operation['price'] = float(row[3].replace(',', '.'))
        operation['stock'] = 'PHA01'

        print (part)
        #print (operation)


        db.stock.update_one(
            {"_id": prefix+row[0]},
            {'$set': part},
            upsert = True
        )

        db.stock_movements.insert_one(
           operation
        )