import pymongo
from bson.errors import InvalidId
from bson.objectid import ObjectId

DB_NAME = "USTintranet"


def add_id_to_addresses(database, user_mdoc):
    if "addresses" not in user_mdoc:
        return

    for address in user_mdoc["addresses"]:
        address["_id"] = ObjectId()

    database.users.update_one({"_id": user_mdoc["_id"]},
                              {"$set": {"addresses": user_mdoc["addresses"]}})


def convert_embedded_ids_to_objectid(database, field, user_mdoc):
    if field not in user_mdoc:
        return

    for embedded in user_mdoc[field]:
        try:
            embedded["_id"] = ObjectId(embedded["_id"])
        except InvalidId as e:
            print(f"Problém v {field}: {e}")

    database.users.update_one({"_id": user_mdoc["_id"]},
                              {"$set": {field: user_mdoc[field]}})


def main():
    database = pymongo.MongoClient()[DB_NAME]

    users_mdocs = database.users.find()

    for user in users_mdocs:
        add_id_to_addresses(database, user)

        for field in ["contracts", "documents", "workspans", "vacations"]:
            convert_embedded_ids_to_objectid(database, field, user)


if __name__ == '__main__':
    main()
