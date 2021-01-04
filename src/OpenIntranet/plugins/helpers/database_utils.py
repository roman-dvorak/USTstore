import pymongo
from bson import ObjectId


def add_embedded_mdoc_to_mdoc_array(coll: pymongo.collection.Collection,
                                    user_id: ObjectId,
                                    array_field: str,
                                    document: dict,
                                    document_id: ObjectId = None,
                                    filter_values=(None, "")):
    if filter_values:
        document = {key: value for key, value in document.items() if value not in filter_values}

    if document_id:
        document["_id"] = document_id

    coll.update_one({"_id": user_id},
                    {"$addToSet": {
                        array_field: document
                    }
                    })


def get_mdocument_set_unset_dicts(document, unset_values=(None, "")):
    to_set = dict(document)
    to_unset = {key: to_set.pop(key) for key, value in document.items() if value in unset_values}

    return to_set, to_unset


def get_user_embedded_mdoc_by_id(database, user_id: ObjectId, field: str, mdoc_id: ObjectId):
    mdoc = database.users.find_one({"_id": user_id, f"{field}._id": mdoc_id},
                                   {f"{field}.$": 1})
    if not mdoc:
        return None

    field_content = mdoc.get(field, None)

    return field_content[0] if field_content else None
