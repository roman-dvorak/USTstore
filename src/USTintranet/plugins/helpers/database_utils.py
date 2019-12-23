import pymongo


def add_embedded_mdoc_to_mdoc_array(coll: pymongo.collection.Collection,
                                    user: str,
                                    array_field: str,
                                    document: dict,
                                    document_id: str = "",
                                    filter_values=(None, "")):
    """
    Přidá embedded mdokument do daného pole uživatele. Nepřidají se fieldy, které mají hodnotu z filter_values.
    Dokumentu se přiřadí _id z parametru document_id. Je li document_id prázdné, _id se nepřiřadí.
    """
    if filter_values:
        document = {key: value for key, value in document.items() if value not in filter_values}

    if document_id:
        document["_id"] = str(document_id)

    coll.update_one({"user": user},
                    {"$addToSet": {
                        array_field: document
                    }
                    })


def get_mdocument_set_unset_dicts(document, unset_values=(None, "")):
    """
    Rozdělí mdokument na dva dicts pro operaci $set a $unset. Do to_unset jdou fieldy s hodnotami z unset_values.
    """
    to_set = dict(document)
    to_unset = {key: to_set.pop(key) for key, value in document.items() if value in unset_values}

    return to_set, to_unset


def get_user_embedded_mdoc_by_id(database, user: str, field: str, mdoc_id: str):
    mdoc = database.users.find_one({"user": user, f"{field}._id": mdoc_id},
                                   {f"{field}.$": 1})
    if not mdoc:
        return None

    field_content = mdoc.get(field, None)

    return field_content[0] if field_content else None
