from datetime import datetime
from pprint import pprint

import pymongo
from bson import ObjectId
import warnings

from pymongo.collection import ReturnDocument

coll = pymongo.MongoClient().USTintranet.users


def get_users(coll: pymongo.collection.Collection):
    users = list(coll.find({'type': 'user'}))
    for user in users:
        user["_id"] = str(user["_id"])
    return users


def get_user(coll: pymongo.collection.Collection, _id: str):
    user = coll.find_one({'_id': ObjectId(_id)})
    user["_id"] = str(user["_id"])
    return user


def update_user(coll: pymongo.collection.Collection, _id: str, data: dict, embedded_1to1_docs=("name",)):
    """
    Updatuje data existujícího uživatele v databázi. Data by měla být first level fieldy a fieldy jednotlivě embedded
    dokumentů v dot notation. Pro updatování polí embedded dokumentů jsou speciální funkce.
    Je-li hodnota určitého fieldu "" (prázdný řetězec), field je z dokumentu odstraněn (je-li poslední v embedded
    dokumentu, embedded dokument je odstraněn).
    """
    to_unset = {key: "" for key, value in data.items() if value == ""}
    for key in to_unset:
        del data[key]

    operation_dict = {}
    if data:
        operation_dict["$set"] = data
    if to_unset:
        operation_dict["$unset"] = to_unset

    updated = coll.find_one_and_update({"_id": ObjectId(_id)}, operation_dict, return_document=ReturnDocument.AFTER)

    for key in embedded_1to1_docs:
        if not updated[key]:
            coll.update_one({"_id": ObjectId(_id)}, {"$unset": {"name": ""}})


def update_user_address(coll: pymongo.collection.Collection, _id: str, address: dict):
    """
    Nastaví pro daného uživatele adresu. Dict address musí obsahovat field "type". Uživatel může mít jen jednu adresu
    daného typu.
    Je-li hodnota určitého fieldu "" (prázdný řetězec), field je z adresy odstraněn (je-li poslední v adrese kromě
    "type", je adresa odstraněna).

    """
    address_type = address["type"]

    to_unset = {key: "" for key, value in address.items() if value == ""}
    for key in to_unset:
        del address[key]

    # pokud už je tento typ adresy v databázi
    if coll.find_one({"_id": ObjectId(_id), "addresses.type": address_type}):

        operation_dict = {}
        if len(address) > 1:  # je tam něco kromě "type"
            operation_dict["$set"] = {f"addresses.$.{key}": value for key, value in address.items()}
        if to_unset:
            operation_dict["$unset"] = {f"addresses.$.{key}": value for key, value in to_unset.items()}

        updated = coll.find_one_and_update({"_id": ObjectId(_id), "addresses.type": address_type}, operation_dict,
                                           return_document=ReturnDocument.AFTER)

        # smaž adresu z "addresses", pokud po updatu obsahuje pouze "type"
        for address in updated["addresses"]:
            if address["type"] == address_type and len(address) <= 1:
                delete_user_address(coll, _id, address_type)

    # jinak přidej adresu do databáze, pokud obsahuje víc než jen "type"
    elif len(address) > 1:
        coll.update_one({"_id": ObjectId(_id)},
                        {"$addToSet": {
                            "addresses": address
                        }
                        })


def delete_user_address(coll: pymongo.collection.Collection, _id: str, address_type: str):
    """
    Smaže daný typ adresy z databáze.
    """
    # TODO implementovat odstranění fieldu když je hodnota fieldu prázdná
    coll.update_one({"_id": ObjectId(_id)},
                    {"$pull": {
                        "addresses": {
                            "type": address_type
                        }
                    }})


def add_users(coll: pymongo.collection.Collection, ids: list = None, n: int = None):
    """
    Přidá nové uživatele do databáze. Do databáze se zapíše jen id a čas vytvoření, ostatní data uživatele je nutno
    přidat pomocí update_user.
    Je možné buď zadat přesná id, která budou přidána do databáze, nebo specifikovat kolik uživatelů přidat, id budou
    vygenerovány automaticky.
    Vrací id přidaných uživatelů.
    """
    if ids:
        oids = [ObjectId(_id) for _id in ids]
    elif n:
        oids = [ObjectId() for _ in range(n)]
        ids = [str(_id) for _id in oids]
    else:
        warnings.warn("Nebyla specifikována žádná id ani počet nových uživatelů. Nic se nestalo.")
        return

    users = [{"_id": _id, "created": datetime.now().replace(microsecond=0)} for _id in oids]
    coll.insert_many(users)

    return ids


def delete_user(coll: pymongo.collection.Collection, _id: str):
    coll.delete_one({"_id": ObjectId(_id)})
