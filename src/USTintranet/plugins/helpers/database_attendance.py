from datetime import datetime

import pymongo
from bson import ObjectId

from plugins.helpers.database_utils import add_embedded_mdoc_to_mdoc_array

# TODO brát jako parametr databázi, ne kolekci

def add_user_workspan(coll: pymongo.collection.Collection, user_id, workspan):
    workspan_id = str(ObjectId())

    add_embedded_mdoc_to_mdoc_array(coll, user_id, "workspans", workspan, workspan_id)

    return workspan_id


def add_user_vacation(coll: pymongo.collection.Collection, user_id, vacation):
    vacation_id = str(ObjectId())

    add_embedded_mdoc_to_mdoc_array(coll, user_id, "vacations", vacation, vacation_id)

    return vacation_id


def get_user_workspans(db, user_id, from_date: datetime, to_date: datetime):
    cursor = db.users.aggregate([
        {"$match": {"_id": ObjectId(user_id)}},
        {"$unwind": "$workspans"},
        {"$match": {
            "workspans.from": {
                "$gte": from_date,
                "$lt": to_date,
            }
        }},
        {"$sort": {"workspans.from": 1}},
        {"$group": {"_id": "$_id", "workspans": {"$push": "$workspans"}}}
    ])

    return next(cursor, {}).get("workspans", [])


def get_user_vacations(coll: pymongo.collection.Collection,
                       user_id: str,
                       earliest_end: datetime,
                       latest_end: datetime = None):
    earliest_latest_dict = {
        "$gte": earliest_end
    }
    if latest_end:
        earliest_latest_dict["$lt"] = latest_end

    cursor = coll.aggregate([
        {"$match": {"_id": ObjectId(user_id)}},
        {"$unwind": "$vacations"},
        {"$match": {
            "vacations.to": earliest_latest_dict
        }},
        {"$sort": {"vacations.to": 1}},
        {"$group": {"_id": "$_id", "vacations": {"$push": "$vacations"}}}
    ])

    return next(cursor, {}).get("vacations", [])


def delete_user_vacation(coll: pymongo.collection.Collection, user_id, vacation_id):
    coll.update_one({"_id": ObjectId(user_id)},
                    {"$pull": {
                        "vacations": {
                            "_id": vacation_id
                        }
                    }})


def delete_user_workspan(coll: pymongo.collection.Collection, user_id, workspan_id):
    coll.update_one({"_id": ObjectId(user_id)},
                    {"$pull": {
                        "workspans": {
                            "_id": workspan_id
                        }
                    }})
