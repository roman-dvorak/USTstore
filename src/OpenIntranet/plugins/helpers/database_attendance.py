from datetime import datetime

import pymongo
from bson import ObjectId

from plugins.helpers import str_ops
from plugins.helpers.database_utils import add_embedded_mdoc_to_mdoc_array, get_user_embedded_mdoc_by_id


# done
def add_user_workspan(database, user_id: ObjectId, workspan):
    assert isinstance(user_id, ObjectId)

    workspan_id = str(ObjectId())

    add_embedded_mdoc_to_mdoc_array(database.users, user_id, "workspans", workspan, workspan_id, filter_values=())

    return workspan_id


# done
def add_user_vacation(database, user_id: ObjectId, vacation):
    assert isinstance(user_id, ObjectId)

    vacation_id = str(ObjectId())

    add_embedded_mdoc_to_mdoc_array(database.users, user_id, "vacations", vacation, vacation_id)

    return vacation_id


# prepared
def get_user_workspans(database, user_id: ObjectId, from_date: datetime, to_date: datetime):
    assert isinstance(user_id, ObjectId)

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


# prepared
def get_user_vacations(database,
                       user_id: ObjectId,
                       earliest_end: datetime,
                       latest_end: datetime = None):
    assert isinstance(user_id, ObjectId)

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


# done
def get_user_vacation_by_id(database, user_id: ObjectId, vacation_id: str):
    assert isinstance(user_id, ObjectId)

    return get_user_embedded_mdoc_by_id(database, user_id, "vacations", vacation_id)


# done
def interrupt_user_vacation(database, user_id: ObjectId, vacation_id, new_end_date):
    assert isinstance(user_id, ObjectId)

    database.users.update_one({"_id": user_id, "vacations._id": vacation_id},
                              {"$set": {
                                  "vacations.$.to": new_end_date,
                              }})


# done
def delete_user_workspan(database, user_id: ObjectId, workspan_id):
    assert isinstance(user_id, ObjectId)

    database.users.update_one({"_id": user_id},
                              {"$pull": {
                                  "workspans": {
                                      "_id": workspan_id
                                  }
                              }})


# TODO možná mít speciální třídu i pro pole? Aby všechny operace nebyly v User?
# prepared
def is_month_closed(database, user_id: ObjectId, month_date: datetime):
    month_date = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    mdoc = database.users.find_one({"_id": user_id, "months_closed": month_date})

    return bool(mdoc)


# prepared
def close_month(database, user_id: ObjectId, month_date: datetime):
    month_date = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    database.users.update_one({"_id": user_id},
                              {
                                  "$addToSet": {"months_closed": month_date}
                              })


# prepared
def reopen_month(database, user_id, month_date: datetime):
    month_date = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    database.users.update_one({"_id": user_id},
                              {"$pull": {
                                  "months_closed": month_date,
                              }})
