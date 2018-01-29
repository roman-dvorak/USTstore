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
i= 0
suma = 0
file = sys.argv[1]
with open(file, 'rt', encoding='utf-8') as csvfile:
    spamreader = csv.reader(csvfile, delimiter=',')
    for row in spamreader:
        i += 1
        #print(row)
        part = {}
        operation = {}

        if row[4] == '': row[4] = '0'
        if row[5] == '': row[5] = '0'

        part['_id'] = row[1].strip()
        part['aid'] = []
        part['type'] = 0
        part['name'] = row[0].strip()
        part['description'] = row[2].strip()
        part['category'] = [row[7].strip()]
        part['price'] = float(row[4].replace(',', '.'))
        part['parameters'] = {}
        part['supplier'] = []
        if len(row[3].strip())>0:
            part['supplier'] = [{'supplier':row[3], 'id':''}]
        part['stock'] = {'pha01':{}, 'sob01':{'count':0}}
        part['stock']['pha01']['count'] = float(row[5].replace(',', '.'))
        part['tags'] = {'imported':{}, 'standard_item':{}}

        suma += part['price']*part['stock']['pha01']['count']

        operation['product'] = row[1].strip()
        operation['operation'] = 'buy'
        operation['bilance'] = float(row[5].replace(',', '.'))
        operation['price'] = float(row[4].replace(',', '.'))
        operation['stock'] = 'pha01'

        #print (part)
        #print (operation)

        out= db.stock.update_one(
            {"_id": row[1].strip()},
            {'$set': part},
            upsert = True
        )
        print(out)
        '''
        db.stock_movements.insert_one(
           operation
        )
        '''

print('za ', suma)
print('celkem bylo:', i)