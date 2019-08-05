from datetime import datetime
from pprint import pprint

import pymongo
from bson import ObjectId
import warnings

coll = pymongo.MongoClient().USTintranet.users


def get_users(coll: pymongo.collection.Collection):
    users = coll.find({'type': 'user'})
    return list(users)


def get_user(coll: pymongo.collection.Collection, _id: str):
    user = coll.find_one({'_id': ObjectId(_id)})
    return user


def update_user(coll: pymongo.collection.Collection, _id: str, data: dict):
    """
    Updatuje data existujícího uživatele v databázi. Data by měla být first level fieldy a fieldy jednotlivě embedded
    dokumentů v dot notation. Pro updatování polí embedded dokumentů jsou speciální funkce.
    """
    coll.update_one({"_id": ObjectId(_id)}, {"$set": data})


def update_user_address(coll: pymongo.collection.Collection, _id: str, address: dict):
    """
    Nastaví pro daného uživatele adresu. Dict address musí obsahovat field "type". Uživatel může mít jen jednu adresu
    daného typu.
    """
    address_type = address["type"]
    print("address_type", address_type)

    if coll.find_one({"_id": ObjectId(_id), "addresses.type": address_type}):
        print("updating")
        update_dict = {f"addresses.$.{key}": value for key, value in address.items()}

        coll.update_one({"_id": ObjectId(_id), "addresses.type": address_type},
                        {"$set": update_dict})

    else:
        print("new")
        coll.update_one({"_id": ObjectId(_id)},
                        {"$addToSet": {
                            "addresses": address
                        }
                        })


def delete_user_address(coll: pymongo.collection.Collection, _id: str, address_type: str):
    """
    Smaže daný typ adresy z databáze.
    """
    # TODO
    pass


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
