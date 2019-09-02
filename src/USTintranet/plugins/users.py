#!/usr/bin/python3
# -*- coding: utf-8 -*-
from datetime import datetime

import bson.json_util

from .users_helpers.doc_keys import CONTRACT_DOC_KEYS
from . import BaseHandler
from .users_helpers import database as db
from .users_helpers import str_ops


def make_handlers(plugin_name, plugin_namespace):
    return [
        (r'/{}/api/admintable'.format(plugin_name), plugin_namespace.ApiAdminTableHandler),
        (r'/{}/api/u/(.*)/edit'.format(plugin_name), plugin_namespace.ApiEditUserHandler),
        (r'/{}/api/u/(.*)/contracts'.format(plugin_name), plugin_namespace.ApiUserContractsHandler),
        (r'/{}/api/u/(.*)/documents'.format(plugin_name), plugin_namespace.ApiUserDocumentsHandler),
        (r'/{}/u/(.*)'.format(plugin_name), plugin_namespace.UserPageHandler),
        (r'/{}'.format(plugin_name), plugin_namespace.HomeHandler),
        (r'/{}/'.format(plugin_name), plugin_namespace.HomeHandler),
    ]


def plug_info():
    return {
        "module": "users",
        "name": "Uživatelé",
        "icon": 'icon_users.svg',
        "role": ['user-sudo', 'user-access', 'user-read', 'economy-read', 'economy-edit'],
    }


class HomeHandler(BaseHandler):
    role_module = ['user-sudo', 'user-access', 'user-read', 'economy-read', 'economy-edit']

    def get(self, data=None):
        me = self.actual_user
        my_activity = list(self.mdb.operation_log.find({'user': me['user']}))

        if self.is_authorized(['users-editor', 'sudo-users']):
            users = self.mdb.users.find()
            self.render('users.home-sudo.hbs', title="TITLE", parent=self, users=users, me=me, my_activity=my_activity)
        else:
            self.render('users.home.hbs', title="Nastavení účtu", parent=self, users=me, me=me, my_activity=my_activity)


class ApiAdminTableHandler(BaseHandler):

    def get(self, uid=None):
        data = db.get_users(self.mdb.users)

        for item in data:
            if "created" in item:
                item["created"] = item["created"].replace(microsecond=0).isoformat()
            if "birthdate" in item:
                item["birthdate"] = item["birthdate"].replace(microsecond=0).isoformat()

            item.pop("pass", None)

            if "addresses" in item:
                item["residence_address"] = next((a for a in item["addresses"] if a["type"] == "residence"), None)
                item["contact_address"] = next((a for a in item["addresses"] if a["type"] == "contact"), None)

                del item["addresses"]

        out = bson.json_util.dumps(data)
        self.write(out)

    def post(self):
        """
        formát objektu data:
        {
            "edited": {
                <id 1>: {<editované fieldy uživatele s id 1>},
                <id 2>: {<nové fieldy uživatele s id 2>},
            },
            "new": [<id 2>, <další id nově přidaných uživatelů>],
            "deleted": [<id 3>, <další id smazaných uživatelů>],
        }
        """
        req = self.request.body.decode("utf-8")
        data = bson.json_util.loads(req)

        edited_data = data["edited"]
        new_ids = data["new"]
        deleted_ids = data["deleted"]

        for _id in deleted_ids:
            db.delete_user(self.mdb.users, _id)

        if new_ids:
            db.add_users(self.mdb.users, new_ids)

        for _id, fields in edited_data.items():
            self.process_and_update(_id, fields)

    def process_and_update(self, _id, data):
        """
        Zajistí, že data uživatele jsou v odpovídajícím tvaru pro uložení do databáze a uloží je.
        """
        keys = list(data.keys())
        residence_address = {key.split(".")[1]: data.pop(key) for key in keys if "residence_address" in key}
        contact_address = {key.split(".")[1]: data.pop(key) for key in keys if "contact_address" in key}

        if "birthdate" in data and data["birthdate"] != "":
            data["birthdate"] = datetime.strptime(data["birthdate"], "%Y-%m-%d")

        if data:
            db.update_user(self.mdb.users, _id, data)

        if residence_address:
            residence_address["type"] = "residence"
            db.update_user_address(self.mdb.users, _id, residence_address)

        if contact_address:
            contact_address["type"] = "contact"
            db.update_user_address(self.mdb.users, _id, contact_address)


class ApiEditUserHandler(BaseHandler):

    def post(self, _id):
        req = self.request.body.decode("utf-8")
        changes = bson.json_util.loads(req)

        residence_address = changes.pop("residence_address", {})
        contact_address = changes.pop("contact_address", {})

        if "birthdate" in changes and changes["birthdate"] != "":
            changes["birthdate"] = datetime.strptime(changes["birthdate"], "%Y-%m-%d")

        if changes:
            db.update_user(self.mdb.users, _id, changes)

        if residence_address:
            residence_address["type"] = "residence"
            db.update_user_address(self.mdb.users, _id, residence_address)
        if contact_address:
            contact_address["type"] = "contact"
            db.update_user_address(self.mdb.users, _id, contact_address)


class UserPageHandler(BaseHandler):

    def get(self, _id):
        user_document = db.get_user(self.mdb.users, _id)

        name_doc = user_document.get("name", {})
        res_address_doc = next((a for a in user_document.get("addresses", {}) if a["type"] == "residence"), {})
        cont_address_doc = next((a for a in user_document.get("addresses", {}) if a["type"] == "contact"), {})

        birthdate = user_document.get("birthdate", None)

        template_params = {
            "user": user_document.get("user", ""),
            "_id": user_document.get("_id"),

            "name": str_ops.name_to_str(name_doc),
            "pre_name_title": name_doc.get("pre_name_title", ""),
            "first_name": name_doc.get("first_name", ""),
            "surname": name_doc.get("surname", ""),
            "post_name_title": name_doc.get("post_name_title", ""),

            "birthdate": str_ops.date_to_str(birthdate),
            "birthdate_iso": str_ops.date_to_iso_str(birthdate),

            "residence_address": str_ops.address_to_str(res_address_doc),
            "residence_street": res_address_doc.get("street", ""),
            "residence_city": res_address_doc.get("city", ""),
            "residence_state": res_address_doc.get("state", ""),
            "residence_zip": res_address_doc.get("zip", ""),

            "contact_address": str_ops.address_to_str(cont_address_doc),
            "contact_street": cont_address_doc.get("street", ""),
            "contact_city": cont_address_doc.get("city", ""),
            "contact_state": cont_address_doc.get("state", ""),
            "contact_zip": cont_address_doc.get("zip", ""),

            "email": user_document.get("email", ""),
            "phone_number": user_document.get("phone_number", ""),
            "account_number": user_document.get("account_number", ""),
            "role": ", ".join(user_document.get("role", [])),
            "assignment": user_document.get("assignment", ""),
            "skills": user_document.get("skills", ""),
            "notes": user_document.get("notes", ""),
        }

        contracts = db.get_user_contracts(self.mdb.users, _id)
        template_params["contracts"] = self.prepare_contracts(contracts)
        documents = user_document.get("documents", [])
        template_params["documents"] = self.prepare_documents(documents)

        self.render("users.user-page.hbs", **template_params)

    def prepare_contracts(self, contracts):
        # TODO rozmyslet si líp fieldy smluv ("is_valid" vs "is_signed") a obarvit neplatné smlouvy šedě

        possible_type = {
            "dpp": "Dohoda o provedení práce",
            "dpc": "Dohoda o pracovní činnosti",
            "ps": "Pracovní smlouva",
        }

        result = []

        for contract in contracts:
            new = {}
            contract_type = possible_type[contract["type"]]
            valid_from = contract["valid_from"]
            valid_until = contract["valid_until"]

            new["_id"] = contract["_id"]
            new["type"] = possible_type[contract["type"]]
            new["signing_date"] = str_ops.date_to_str(contract["signing_date"])
            new["valid_from"] = str_ops.date_to_str(valid_from)
            new["valid_until"] = str_ops.date_to_str(valid_until)
            new["notes"] = contract.get("notes", "")
            new["is_valid"] = "Ano" if contract["is_valid"] else "Ne"
            new["button_text"] = "Zneplatnit" if contract["is_valid"] else "Nastavit jako platnou"
            new["title"] = f"{new['type']} {new['valid_from']} - {new['valid_until']}"

            result.append(new)

        return result

    def prepare_documents(self, documents):
        possible_type = {
            "study_certificate": "Potvrzení o studiu",
            "tax_declaration": "Prohlášení k dani",
            "contract_scan": "Sken podepsané smlouvy"
        }

        for document in documents:
            valid_from_text = str_ops.date_to_str(document.get("valid_from", None))
            valid_until_text = str_ops.date_to_str(document.get("valid_until", None))

            document["type_text"] = possible_type[document["type"]]
            document["valid_from_text"] = valid_from_text
            document["valid_until_text"] = valid_until_text
            document["valid_from"] = str_ops.date_to_iso_str(document.get("valid_from", None))
            document["valid_until"] = str_ops.date_to_iso_str(document.get("valid_until", None))

            date_texts = [date for date in [valid_from_text, valid_until_text] if date]
            document["title"] = f"{document['type_text']} {' - '.join(date_texts)}"

        return documents


class ApiUserContractsHandler(BaseHandler):

    def post(self, _id):
        req = self.request.body.decode("utf-8")
        contract = bson.json_util.loads(req)

        contract["signing_date"] = datetime.strptime(contract["signing_date"], "%Y-%m-%d")
        contract["valid_from"] = datetime.strptime(contract["valid_from"], "%Y-%m-%d")
        contract["valid_until"] = datetime.strptime(contract["valid_until"], "%Y-%m-%d")

        db.add_user_contract(self.mdb.users, _id, contract)


class ApiUserDocumentsHandler(BaseHandler):

    def post(self, _id):
        req = self.request.body.decode("utf-8")
        document = bson.json_util.loads(req)

        if "delete" in document:
            db.delete_user_document(self.mdb.users, _id, document.pop("_id"))
            return

        document["valid_from"] = str_ops.date_from_iso_str(document.get("valid_from", None))
        document["valid_until"] = str_ops.date_from_iso_str(document.get("valid_until", None))

        if document.get("_id", None):
            db.update_user_document(self.mdb.users, _id, document.pop("_id"), document)
        else:
            db.add_user_document(self.mdb.users, _id, document)
