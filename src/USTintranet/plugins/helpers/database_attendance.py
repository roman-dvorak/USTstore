import pymongo
from bson.json_util import ObjectId


def add_user_workspan(coll: pymongo.collection.Collection, user_id, workspan):
    workspan_id = ObjectId()
    workspan["_id"] = workspan_id
    workspan["user"] = ObjectId(user_id)

    coll.insert_one(workspan)

    return str(workspan_id)
