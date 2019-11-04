import pymongo
from bson import ObjectId


def add_embedded_mdoc_to_mdoc_array(coll: pymongo.collection.Collection,
                                    mdoc_id: str,
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

    coll.update_one({"_id": ObjectId(mdoc_id)},
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