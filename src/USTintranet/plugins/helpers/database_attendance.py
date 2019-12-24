from datetime import datetime

import pymongo
from bson import ObjectId

from plugins.helpers.assertions import assert_isinstance
from plugins.helpers.database_utils import add_embedded_mdoc_to_mdoc_array, get_user_embedded_mdoc_by_id


def add_user_workspan(database, user_id: ObjectId, workspan):
    assert_isinstance(user_id, ObjectId)

    workspan_id = str(ObjectId())

    add_embedded_mdoc_to_mdoc_array(database.users, user_id, "workspans", workspan, workspan_id, filter_values=())

    return workspan_id


def add_user_vacation(database, user_id: ObjectId, vacation):
    assert_isinstance(user_id, ObjectId)

    vacation_id = str(ObjectId())

    add_embedded_mdoc_to_mdoc_array(database.users, user_id, "vacations", vacation, vacation_id)

    return vacation_id


def get_user_workspans(database, user_id: ObjectId, from_date: datetime, to_date: datetime):
    assert_isinstance(user_id, ObjectId)

    cursor = database.users.aggregate([
        {"$match": {"_id": user_id}},
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


def get_user_vacations(database,
                       user_id: ObjectId,
                       earliest_end: datetime,
                       latest_end: datetime = None):
    assert_isinstance(user_id, ObjectId)

    earliest_latest_dict = {
        "$gte": earliest_end
    }
    if latest_end:
        earliest_latest_dict["$lt"] = latest_end

    cursor = database.users.aggregate([
        {"$match": {"_id": user_id}},
        {"$unwind": "$vacations"},
        {"$match": {
            "vacations.to": earliest_latest_dict
        }},
        {"$sort": {"vacations.to": 1}},
        {"$group": {"_id": "$_id", "vacations": {"$push": "$vacations"}}}
    ])

    return next(cursor, {}).get("vacations", [])


def get_user_vacation_by_id(database, user_id: ObjectId, vacation_id: str):
    assert_isinstance(user_id, ObjectId)

    return get_user_embedded_mdoc_by_id(database, user_id, "vacations", vacation_id)


def interrupt_user_vacation(database, user_id: ObjectId, vacation_id, new_end_date):
    assert_isinstance(user_id, ObjectId)

    database.users.update_one({"_id": user_id, "vacations._id": vacation_id},
                              {"$set": {
                                  "vacations.$.to": new_end_date,
                              }})


def delete_user_workspan(database, user_id: ObjectId, workspan_id):
    assert_isinstance(user_id, ObjectId)

    database.users.update_one({"_id": user_id},
                              {"$pull": {
                                  "workspans": {
                                      "_id": workspan_id
                                  }
                              }})
