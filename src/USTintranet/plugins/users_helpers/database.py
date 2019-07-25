from pprint import pprint

import pymongo
from bson import ObjectId

collection = pymongo.MongoClient().USTintranet.users


def get_users(coll: pymongo.collection.Collection):
    users = coll.find({'type': 'user'})
    return list(users)


def update_users(coll: pymongo.collection.Collection, dataset: dict):
    for key, data in dataset.items():
        coll.update_one({"_id": ObjectId(key)}, {"$set": data})


def add_users(coll: pymongo.collection.Collection, dataset: list):
    for d in dataset:
        d["_id"] = ObjectId(d["_id"])
    coll.insert_many(dataset)


def delete_users(coll: pymongo.collection.Collection, dataset: list):
    for _id in dataset:
        coll.delete_one({"_id": ObjectId(_id)})
