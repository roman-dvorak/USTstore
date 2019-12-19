from datetime import datetime

import pymongo
from bson import ObjectId
from pymongo.collection import ReturnDocument

from plugins.helpers.database_utils import add_embedded_mdoc_to_mdoc_array, get_mdocument_set_unset_dicts, \
    get_user_embedded_mdoc_by_id


# TODO brát jako parametr databázi, ne kolekci


def get_users(coll: pymongo.collection.Collection, **by):
    """
    Vrátí list uživatelů z databáze. Každý uživatel má field "_id" s textovou verzí ObjectID jeho mdokumentu.
    # TODO upravit docstring
    """
    by_copy = dict(by)
    by_copy["type"] = "user"
    users = list(coll.find(by_copy))
    for user in users:
        user["_id"] = str(user["_id"])
    return users


def get_user(coll: pymongo.collection.Collection, user_id: str):
    """
    Vrátí mdokument daného uživatele. Uživatel má field "_id" s textovou verzí ObjectID jeho mdokumentu.
    """
    user = coll.find_one({'_id': user_id})
    if not user:
        return None
    return user


def get_user_contracts(coll: pymongo.collection.Collection, user_id: str, sort_by="signing_date"):
    """
    Vrátí list smluv uživatele seřazených sestupně podle fieldu daného parametrem sort_by.
    """
    cursor = coll.aggregate([
        {"$match": {"_id": user_id}},
        {"$unwind": "$contracts"},
        {"$match": {"contracts.type": "dpp"}},  # TODO udělat to obecně ne jen pro dpp
        {"$sort": {f"contracts.{sort_by}": -1}},
        {"$group": {"_id": "$_id", "contracts": {"$push": "$contracts"}}}
    ])
    return next(cursor, {}).get("contracts", [])


def update_user(coll: pymongo.collection.Collection, user_id: str, data: dict, embedded_1to1_docs=("name",)):
    """
    Updatuje data existujícího uživatele v databázi. Data by měla být first level fieldy a fieldy jednotlivě embedded
    mdokumentů v dot notation. Pro updatování polí embedded mdokumentů jsou speciální funkce.
    Je-li hodnota určitého fieldu "" (prázdný řetězec), field je z mdokumentu odstraněn (je-li poslední v embedded
    mdokumentu, embedded mdokument je odstraněn).
    """
    to_unset = {key: "" for key, value in data.items() if value == ""}
    for key in to_unset:
        del data[key]

    operation_dict = {}
    if data:
        operation_dict["$set"] = data
    if to_unset:
        operation_dict["$unset"] = to_unset

    updated = coll.find_one_and_update({"_id": user_id}, operation_dict, return_document=ReturnDocument.AFTER)

    for key in embedded_1to1_docs:
        if key in updated and not updated[key]:
            coll.update_one({"_id": user_id}, {"$unset": {"name": ""}})


def update_user_address(coll: pymongo.collection.Collection, user_id: str, address: dict):
    """
    Nastaví pro daného uživatele adresu. Dict address musí obsahovat field "type". Uživatel může mít jen jednu adresu
    daného typu.
    Je-li hodnota určitého fieldu "" (prázdný řetězec) nebo None, field je z adresy odstraněn (je-li poslední v adrese
    kromě "type", je adresa odstraněna).

    """
    address_type = address["type"]

    to_set, to_unset = get_mdocument_set_unset_dicts(address)

    # pokud už je tento typ adresy v databázi
    if coll.find_one({"_id": user_id, "addresses.type": address_type}):

        operation_dict = {}
        if len(to_set) > 1:  # je tam něco kromě "type"
            operation_dict["$set"] = {f"addresses.$.{key}": value for key, value in to_set.items()}
        if to_unset:
            operation_dict["$unset"] = {f"addresses.$.{key}": value for key, value in to_unset.items()}

        updated = coll.find_one_and_update({"_id": user_id, "addresses.type": address_type}, operation_dict,
                                           return_document=ReturnDocument.AFTER)

        # smaž adresu z "addresses", pokud po updatu obsahuje pouze "type"
        for address in updated["addresses"]:
            if address["type"] == address_type and len(address) <= 1:
                delete_user_address(coll, user_id, address_type)

    # jinak přidej adresu do databáze, pokud obsahuje víc než jen "type"
    elif len(address) > 1:
        add_embedded_mdoc_to_mdoc_array(coll, user_id, "addresses", address, filter_values=None)


def delete_user_address(coll: pymongo.collection.Collection, user_id: str, address_type: str):
    """
    Smaže daný typ adresy z databáze.
    """
    coll.update_one({"_id": user_id},
                    {"$pull": {
                        "addresses": {
                            "type": address_type
                        }
                    }})


def add_users(coll: pymongo.collection.Collection, ids: list):
    """
    Přidá nové uživatele do databáze. Do databáze se zapíše jen id a čas vytvoření, ostatní data uživatele je nutno
    přidat pomocí update_user.
    Je možné buď zadat přesná id, která budou přidána do databáze, nebo specifikovat kolik uživatelů přidat, id budou
    vygenerovány automaticky.
    Vrací id přidaných uživatelů. TODO najít a opravit kde se toto používá
    """
    users = [{"_id": _id,
              "created": datetime.now().replace(microsecond=0),
              "type": "user",
              } for _id in ids]
    coll.insert_many(users)

    return ids


def delete_user(coll: pymongo.collection.Collection, _id: str):
    """
    Smaže uživatele z databáze.
    """
    coll.delete_one({"_id": _id})


def add_user_contract(coll: pymongo.collection.Collection, user_id: str, contract: dict):
    """
    Přidá novou smlouvu daného uživatele. Smlouva dostane vlastní "_id".
    """
    add_embedded_mdoc_to_mdoc_array(coll, user_id, "contracts", contract, str(ObjectId()))


def add_user_contract_preview(coll: pymongo.collection.Collection, user_id: str, contract: dict):
    contract_id = str(ObjectId())

    contract = dict(contract)
    contract["type"] = f"{contract['type']}_preview"
    add_embedded_mdoc_to_mdoc_array(coll, user_id, "contracts", contract, contract_id)

    return contract_id


def unmark_user_contract_as_preview(database, user_id: str, contract_id: str):
    contract_mdoc = get_user_contract_by_id(database, user_id, contract_id)

    new_type = contract_mdoc["type"].replace("_preview", "")

    database.users.update_one({"_id": user_id, "contracts._id": contract_id},
                              {"$set": {
                                  "contracts.$.type": new_type,
                              }})


def invalidate_user_contract(coll: pymongo.collection.Collection,
                             user_id: str,
                             contract_id: str,
                             invalidation_date: datetime):
    """
    Přidá do mdocumentu smlouvy key "invalidated" obsahující aktuální datum. Toto značí zneplatnění smlouvy,
    nelze vzít zpět.
    """
    coll.update_one({"_id": user_id, "contracts._id": contract_id},
                    {"$set": {
                        "contracts.$.invalidated": invalidation_date,
                    }})


def add_user_contract_scan(coll: pymongo.collection.Collection, user_id: str, contract_id: str, file_id):
    coll.update_one({"_id": user_id, "contracts._id": contract_id},
                    {"$set": {
                        "contracts.$.scan_file": file_id,
                    }})


def add_user_document(coll: pymongo.collection.Collection, user_id: str, document: dict):
    """
    Přidá nový dokument daného uživatele. Dokument dostane vlastní "_id".
    """
    _id = str(ObjectId())
    add_embedded_mdoc_to_mdoc_array(coll, user_id, "documents", document, _id)
    return _id


def delete_user_document(coll: pymongo.collection.Collection, user_id: str, document_id: str):
    """
    Smaže daný dokument uživatele z databáze.
    """
    coll.update_one({"_id": user_id},
                    {"$pull": {
                        "documents": {
                            "_id": document_id
                        }
                    }})


def invalidate_user_document(coll: pymongo.collection.Collection,
                             user_id: str,
                             document_id: str,
                             invalidation_date: datetime):
    coll.update_one({"_id": user_id, "documents._id": document_id},
                    {"$set": {
                        "documents.$.invalidated": invalidation_date
                    }})


def get_user_document_owncloud_id(coll: pymongo.collection.Collection, user_id: str, document_id: str):
    document_mdoc = coll.find_one({"_id": user_id, "documents._id": document_id}, {"documents.$": 1})
    return document_mdoc["documents"][0]["file"]


def update_user_document(coll: pymongo.collection.Collection, user_id: str, document_id: str, document: dict):
    """
    Upraví dokument s daným document_id daného uživatele. Má-li field hodnotu "" (prázdný řetězec) nebo None,
    je z mdokumentu odstraněn.
    """
    to_set, to_unset = get_mdocument_set_unset_dicts(document)

    operation_dict = {}
    if to_set:  # některý z fieldů je neprázdný
        operation_dict["$set"] = {f"documents.$.{key}": value for key, value in to_set.items()}
    if to_unset:
        operation_dict["$unset"] = {f"documents.$.{key}": value for key, value in to_unset.items()}

    assert not (set(to_set.keys()).intersection(set(to_unset.keys())))
    print("to_set", to_set)
    print("to_unset", to_unset)

    updated = coll.find_one_and_update({"_id": user_id, "documents._id": document_id}, operation_dict,
                                       return_document=ReturnDocument.AFTER)
    if not list(updated):
        raise ValueError("Uživatel nemá dokument s tímto _id")


def get_user_active_contract(coll: pymongo.collection.Collection, user_id: str, date: datetime = None):
    if not date:
        date = datetime.now()

    mdoc = coll.find_one({
        "_id": user_id,
        "contracts": {
            "$elemMatch": {
                "valid_from": {"$lte": date},
                "valid_until": {"$gte": date},
                "invalidated": {"$exists": False},
                "type": "dpp"  # TODO udělat obecně
            }
        }
    }, {"contracts.$": 1})

    if not mdoc:
        return None

    contracts = mdoc.get("contracts", None)

    return contracts[0] if contracts else None


def get_user_active_contracts(database, user_id: str, from_date: datetime, to_date: datetime, sort_by="valid_from"):
    cursor = database.users.aggregate([
        {"$match": {"_id": user_id}},
        {"$unwind": "$contracts"},
        {"$match": {
            "$nor": [
                {"contracts.valid_from": {"$gt": to_date}},
                {"contracts.valid_until": {"$lt": from_date}},
                {"contracts.invalidated": {"$exists": True}},
            ],
            "contracts.type": "dpp",  # TODO udělat obecně
        }},
        {"$sort": {f"contracts.{sort_by}": -1}},
        {"$group": {"_id": "$_id", "contracts": {"$push": "$contracts"}}}
    ])
    return next(cursor, {}).get("contracts", [])


def get_user_active_document(coll: pymongo.collection.Collection, user_id, document_type, date: datetime = None):
    if not date:
        date = datetime.now()

    mdoc = coll.find_one({
        "_id": user_id,
        "documents": {
            "$elemMatch": {
                "valid_from": {"$lte": date},
                "valid_until": {"$gte": date},
                "type": document_type,
                "invalidated": {"$exists": False},
            }
        }
    }, {"documents.$": 1})

    if not mdoc:
        return None

    documents = mdoc.get("documents", None)

    return documents[0] if documents else None


def get_user_active_documents(db,
                              user_id: str,
                              document_type: str,
                              from_date: datetime,
                              to_date: datetime,
                              sort_by="valid_from"):
    cursor = db.users.aggregate([
        {"$match": {"_id": user_id}},
        {"$unwind": "$documents"},
        {"$match": {"documents.type": document_type}},
        {"$match": {
            "$nor": [
                {"documents.valid_from": {"$gte": to_date}},
                {"documents.valid_until": {"$lt": from_date}},
            ]
        }},
        {"$sort": {f"documents.{sort_by}": -1}},
        {"$group": {"_id": "$_id", "documents": {"$push": "documents"}}}
    ])
    return next(cursor, {}).get("documents", [])


def get_user_active_tax_declaration(coll: pymongo.collection.Collection, user_id: str, date: datetime = None):
    return get_user_active_document(coll, user_id, "tax_declaration", date)


def get_user_active_study_certificate(coll: pymongo.collection.Collection, user_id: str, date: datetime = None):
    return get_user_active_document(coll, user_id, "study_certificate", date)


def update_email_is_validated_status(coll: pymongo.collection.Collection,
                                     user_id: str,
                                     yes=False,
                                     no=False,
                                     token=""):
    if token:
        res = coll.update_one({"_id": user_id},
                              {"$set": {
                                  "email_validated": "pending",
                                  "email_validation_token": token,
                              }})
    elif yes:
        coll.update_one({"_id": user_id},
                        {
                            "$set": {
                                "email_validated": "yes",
                            },
                            "$unset": {
                                "email_validation_token": "",
                            },
                        })
    elif no:
        coll.update_one({"_id": user_id},
                        {
                            "$set": {
                                "email_validated": "no",
                            },
                            "$unset": {
                                "email_validation_token": "",
                            },
                        })


def get_user_contract_by_id(database, user_id: str, contract_id: str):
    return get_user_embedded_mdoc_by_id(database, user_id, "contracts", contract_id)


def get_user_document_by_id(database, user_id: str, document_id: str):
    return get_user_embedded_mdoc_by_id(database, user_id, "documents", document_id)
