import pymongo
import json
import sys
import datetime
from bson import ObjectId


client = pymongo.MongoClient('localhost', 27017)
db = client.USTdev

poss = db.store_positions.find()
cats = db.category.find()


for i, cat in enumerate(cats):
    print("cat", i, cat['_id'])
    try:
        parent = cat['parent']

        if parent != '#':
            count = db.category.find({'_id': parent}).count()
            if count == 0:
                db.category.update({'_id': cat['_id']}, {'$set': {'parent': '#'}})
                print("REPAIRED")


    except Exception as e:
        print(cat)
        #db.category.update({'_id': cat['_id']}, {'$set': {'parent', '#'}})
        print(e)

for i, pos in enumerate(poss):
    print("pos", i, pos['_id'])
    try:
        parent = pos['parent']

        if parent != '#':
            count = db.store_positions.find({'_id': parent}).count()
            print("count", count)
            if count == 0:
                db.store_positions.update({'_id': pos['_id']}, {'$set': {'parent': '#'}})
                print("REPAIRED")
        
        db.store_positions.update({'_id': pos['_id']}, {'$set': {'parent': '#'}})


    except Exception as e:
        print(pos)
        #db.store_positions.update({'_id': pos['_id']}, {'$set': {'parent', '#'}})
        print(e)
