import pymongo
from bson.errors import InvalidId
from bson.objectid import ObjectId

DB_NAME = "USTdev"


def main():
    database = pymongo.MongoClient()[DB_NAME]

    owncloud_mdocs = database.owncloud.find()

    for mdoc in owncloud_mdocs:
        if "versions" not in mdoc:
            continue

        versions = []

        for index, version_mdoc in mdoc["versions"].items():
            print(index, end=" ")
            version_mdoc["_id"] = ObjectId()
            versions.append(version_mdoc)
        print()

        database.owncloud.update_one({"_id": mdoc["_id"]},
                                     {"$set": {"versions": versions}})


if __name__ == '__main__':
    main()
