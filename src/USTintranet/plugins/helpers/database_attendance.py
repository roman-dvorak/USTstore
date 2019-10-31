from datetime import datetime

import pymongo
from bson import ObjectId

from database_utils import add_embedded_mdoc_to_mdoc_array


def add_user_workspan(coll: pymongo.collection.Collection, user_id, workspan):
    workspan_id = str(ObjectId())

    add_embedded_mdoc_to_mdoc_array(coll, user_id, "workspans", workspan, workspan_id)

    return workspan_id


def get_user_workspans(coll: pymongo.collection.Collection, user_id, since: datetime, to: datetime):
    cursor = coll.aggregate([
        {"$match": {"_id": ObjectId(user_id)}},
        {"$unwind": "$workspans"},
        {"$match": {
            "workspans.from": {
                "$gte": since,
                "$lt": to,
            }
        }},
        {"$sort": {"workspans.from": 1}},
        {"$group": {"_id": "$_id", "workspans": {"$push": "$workspans"}}}
    ])

    return next(cursor, {}).get("workspans", [])