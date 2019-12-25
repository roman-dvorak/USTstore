from datetime import datetime

import pymongo
from pymongo.errors import OperationFailure

DB_NAME = "USTintranet"


def convert_users():
    database = pymongo.MongoClient()[DB_NAME]

    users_old: pymongo.collection.Collection = database.users
    try:
        users_old.rename("users_old")
    except OperationFailure:
        print("! Pozor, kolekce users_old již existuje, končím.")
    users_old = database.users_old

    users_new = database.users

    users_old_mdocs = users_old.find()

    for mdoc in users_old_mdocs:
        new_mdoc = {}

        new_mdoc["_id"] = mdoc["_id"]

        if "created" in mdoc:
            new_mdoc["created"] = mdoc["created"]
        else:
            new_mdoc["created"] = datetime.now()

        if "type" in mdoc:
            new_mdoc["type"] = mdoc["type"]
        else:
            print(f"! záznam s _id {mdoc['_id']} nemá typ, přeskakuji")
            continue

        if "user" in mdoc:
            new_mdoc["user"] = mdoc["user"]
        else:
            print(f"! záznam s _id {mdoc['_id']} nemá položku user, přeskakuji")
            continue

        if "email" in mdoc:
            new_mdoc["email"] = mdoc["email"]

        if "role" in mdoc:
            new_mdoc["role"] = mdoc["role"]
        else:
            new_mdoc["role"] = []

        if "pass" in mdoc:
            new_mdoc["pass"] = mdoc["pass"]

        if "name" in mdoc:
            if not isinstance(mdoc["name"], str):
                print(f"! jméno uživatele s _id {mdoc['_id']} není string, přeskakuji")

            name_parts = mdoc["name"].split()
            if len(name_parts) == 2:
                new_mdoc["name"] = {
                    "first_name": name_parts[0],
                    "surname": name_parts[1]
                }
            else:
                new_mdoc["name"] = {
                    "first_name": mdoc["name"]
                }

        new_mdoc["email_validated"] = "no"

        users_new.insert_one(new_mdoc)

        print(f"Uživatel {mdoc['user']} zkonvertován")


def reset():
    database = pymongo.MongoClient()[DB_NAME]

    users_new: pymongo.collection.Collection = database.users
    users_new.drop()

    users_old = database.users_old
    users_old.rename("users")


if __name__ == '__main__':
    convert_users()
