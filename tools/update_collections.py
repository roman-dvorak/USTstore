

from pprint import pprint
import pymongo
from bson import ObjectId

client = pymongo.MongoClient('localhost', 27017)
db = client.USTintranet

coll = "carts"
if coll not in db.collection_names():
    db.create_collection(coll)
else:
    print("existuje...", coll)


coll = "category"
if coll not in db.collection_names():
    db.create_collection(coll)
else:
    print("existuje...", coll)


coll = "intranet"
if coll not in db.collection_names():
    db.create_collection(coll)
else:
    print("existuje...", coll)


coll = "invoice"
if coll not in db.collection_names():
    db.create_collection(coll)
else:
    print("existuje...", coll)


coll = "operation_log"
if coll not in db.collection_names():
    db.create_collection(coll)
else:
    print("existuje...", coll)


coll = "product"
if coll not in db.collection_names():
    db.create_collection(coll)
else:
    print("existuje...", coll)


coll = "production"
if coll not in db.collection_names():
    db.create_collection(coll)
else:
    print("existuje...", coll)


coll = "stock"
if coll not in db.collection_names():
    db.create_collection(coll)
else:
    print("existuje...", coll)

coll = "stock_movements"
if coll not in db.collection_names():
    db.create_collection(coll)
else:
    print("existuje...", coll)

coll = "stock_taking"
if coll not in db.collection_names():
    db.create_collection(coll)
else:
    print("existuje...", coll)

coll = "stock_positions"
if coll not in db.collection_names():
    db.create_collection(coll)
else:
    print("existuje...", coll)

coll = "store_positions"
if coll not in db.collection_names():
    db.create_collection(coll)
else:
    print("existuje...", coll)

coll = "users"
if coll not in db.collection_names():
    db.create_collection(coll)
else:
    print("existuje...", coll)

coll = "warehouse"
if coll not in db.collection_names():
    db.create_collection(coll)
else:
    print("existuje...", coll)
