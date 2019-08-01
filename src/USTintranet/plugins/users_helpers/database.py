from pprint import pprint

import pymongo
from bson import ObjectId

collection = pymongo.MongoClient().USTintranet.users


def get_users(coll: pymongo.collection.Collection):
    users = coll.find({'type': 'user'})
    return list(users)


def get_user(coll: pymongo.collection.Collection, _id):
    user = coll.find_one({'_id': ObjectId(_id)})
    return user


def update_users(coll: pymongo.collection.Collection, dataset: dict):
    """
    Dataset je dict {<_id>: <JSON-like dokument, reprezentující strukturu databáze>}
    """
    print("updating users", dataset)
    for _id, fields in dataset.items():
        coll.update_one({"_id": ObjectId(_id)}, {"$set": fields})


def add_users(coll: pymongo.collection.Collection, dataset: list):
    print("adding users", dataset)
    for d in dataset:
        d["_id"] = ObjectId(d["_id"])
    coll.insert_many(dataset)


def delete_users(coll: pymongo.collection.Collection, dataset: list):
    print("deleting users", dataset)
    for _id in dataset:
        coll.delete_one({"_id": ObjectId(_id)})
