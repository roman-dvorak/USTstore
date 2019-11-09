#!/usr/bin/python3
# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

import bson.json_util
import tornado
import tornado.options
import os

from plugins.helpers.mdoc_ops import find_type_in_addresses, compile_user_month_info
from plugins.helpers.contract_generation import generate_contract
from plugins import BaseHandlerOwnCloud
from plugins import BaseHandler, save_file, upload_file
from plugins.helpers import database_user as udb
from plugins.helpers import str_ops


def make_handlers(plugin_name, plugin_namespace):
    return [
        (r'/{}/api/admintable'.format(plugin_name), plugin_namespace.ApiAdminTableHandler),
        (r'/{}/api/u/(.*)/edit'.format(plugin_name), plugin_namespace.ApiEditUserHandler),
        (r'/{}/api/u/(.*)/contracts'.format(plugin_name), plugin_namespace.ApiUserContractsHandler),
        (r'/{}/api/u/(.*)/documents'.format(plugin_name), plugin_namespace.ApiUserDocumentsHandler),
        (r'/{}/api/u/(.*)/documents/delete'.format(plugin_name), plugin_namespace.ApiUserDeleteDocumentHandler),
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
        data = udb.get_users(self.mdb.users)

        for item in data:
            if "name" in item and not isinstance(item["name"], dict):
                item["full_name"] = item.pop("name")

            if "created" in item:
                item["created"] = item["created"].replace(microsecond=0).isoformat()
            if "birthdate" in item:
                item["birthdate"] = item["birthdate"].replace(microsecond=0).isoformat()

            item.pop("pass", None)

            if "addresses" in item:
                item["residence_address"] = find_type_in_addresses(item["addresses"], "residence")
                item["contact_address"] = find_type_in_addresses(item["addresses"], "contact")

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
        print(data)

        edited_data = data["edited"]
        new_ids = data["new"]
        deleted_ids = data["deleted"]

        for _id in deleted_ids:
            udb.delete_user(self.mdb.users, _id)

        if new_ids:
            udb.add_users(self.mdb.users, new_ids)

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
            udb.update_user(self.mdb.users, _id, data)

        if residence_address:
            residence_address["type"] = "residence"
            udb.update_user_address(self.mdb.users, _id, residence_address)

        if contact_address:
            contact_address["type"] = "contact"
            udb.update_user_address(self.mdb.users, _id, contact_address)


class ApiEditUserHandler(BaseHandler):

    def post(self, _id):
        req = self.request.body.decode("utf-8")
        changes = bson.json_util.loads(req)

        residence_address = changes.pop("residence_address", {})
        contact_address = changes.pop("contact_address", {})

        if "birthdate" in changes and changes["birthdate"] != "":
            changes["birthdate"] = datetime.strptime(changes["birthdate"], "%Y-%m-%d")

        if changes:
            udb.update_user(self.mdb.users, _id, changes)

        if residence_address:
            residence_address["type"] = "residence"
            udb.update_user_address(self.mdb.users, _id, residence_address)
        if contact_address:
            contact_address["type"] = "contact"
            udb.update_user_address(self.mdb.users, _id, contact_address)


class UserPageHandler(BaseHandler):

    def get(self, _id):
        user_document = udb.get_user(self.mdb.users, _id)

        name_doc = user_document.get("name", {})
        if not isinstance(name_doc, dict):
            name_doc = {}

        res_address_doc = find_type_in_addresses(user_document.get("addresses", {}), "residence") or {}
        cont_address_doc = find_type_in_addresses(user_document.get("addresses", {}), "contact") or {}

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
        template_params.update(compile_user_month_info(self.mdb.users, _id, datetime.now()))

        contracts = udb.get_user_contracts(self.mdb.users, _id)
        template_params["contracts"] = self.prepare_contracts(contracts)
        documents = user_document.get("documents", [])
        template_params["documents"] = self.prepare_documents(documents, contracts)

        self.render("users.user-page.hbs", **template_params)

    def prepare_contracts(self, contracts):
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
            new["is_signed"] = "Ano" if contract["is_signed"] else "Ne"
            new["is_signed_raw"] = contract["is_signed"]
            # new["button_text"] = "Zneplatnit" if contract["is_signed"] else "Nastavit jako platnou"
            new["title"] = f"{new['type']} {new['valid_from']} - {new['valid_until']}"
            new["url"] = contract["url"]

            new["is_valid"] = False
            if contract["is_signed"] and not contract.get("invalidated", False):
                if contract["valid_from"] <= datetime.now() <= contract["valid_until"] + timedelta(days=1):
                    new["is_valid"] = True

            if contract.get("invalidated", False):
                new["invalidated"] = str_ops.date_to_str(contract["invalidated"])

            result.append(new)

        return result

    def prepare_documents(self, documents, contracts):
        possible_type = {
            "study_certificate": "Potvrzení o studiu",
            "tax_declaration": "Prohlášení k dani",
            "contract_scan": "Sken podepsané smlouvy"
        }

        for document in documents:
            if document["type"] == "contract_scan":
                contract = next(item for item in contracts if item["_id"] == document["contract_id"])
                document["valid_from"] = contract["valid_from"]
                document["valid_until"] = contract["valid_until"]

            valid_from_text = str_ops.date_to_str(document.get("valid_from", None))
            valid_until_text = str_ops.date_to_str(document.get("valid_until", None))

            if document["valid_from"] <= datetime.now() <= document["valid_until"] + timedelta(days=1):
                document["is_valid"] = True
            else:
                document["is_valid"] = False

            document["type_text"] = possible_type[document["type"]]
            document["valid_from_text"] = valid_from_text
            document["valid_until_text"] = valid_until_text
            document["valid_from"] = str_ops.date_to_iso_str(document.get("valid_from", None))
            document["valid_until"] = str_ops.date_to_iso_str(document.get("valid_until", None))

            date_texts = [date for date in [valid_from_text, valid_until_text] if date]
            document["title"] = f"{document['type_text']} {' - '.join(date_texts)}"

        return documents


class ApiUserContractsHandler(BaseHandlerOwnCloud):

    def post(self, _id):
        req = self.request.body.decode("utf-8")
        contract = bson.json_util.loads(req)

        if "contract_id" in contract:
            if contract.get("invalidated", False):
                udb.invalidate_user_contract(self.mdb.users, _id, contract["contract_id"])

            if contract.get("is_signed", False):
                udb.sign_user_contract(self.mdb.users, _id, contract["contract_id"])
        else:
            contract["signing_date"] = str_ops.datetime_from_iso_str(contract["signing_date"])
            contract["valid_from"] = str_ops.datetime_from_iso_str(contract["valid_from"])
            contract["valid_until"] = str_ops.datetime_from_iso_str(contract["valid_until"])
            contract["hour_rate"] = int(contract["hour_rate"])

            local_path = generate_contract(udb.get_user(self.mdb.users, _id), contract,
                                          "Universal Scientific Technologies s.r.o.",  # TODO tahat z databáze
                                          "U Jatek 19, 392 01 Soběslav",
                                          "28155319")

            owncloud_path = os.path.join(tornado.options.options.owncloud_root,
                                         "contracts",
                                         os.path.basename(local_path))
            remote = save_file(self.mdb, owncloud_path)
            res = upload_file(self.oc, local_path, remote)

            contract["url"] = res.get_link()

            udb.add_user_contract(self.mdb.users, _id, contract)


class ApiUserDocumentsHandler(BaseHandlerOwnCloud):

    def post(self, _id):
        document = {
            "_id": self.get_argument("_id"),
            "type": self.get_argument("type"),
            "valid_from": self.get_argument("valid_from"),
            "valid_until": self.get_argument("valid_until"),
            "notes": self.get_argument("notes")
        }
        print("document", document)

        if document["type"] == "contract_scan":
            document["contract_id"] = self.get_argument("document_contract")
            document.pop("valid_from", None)
            document.pop("valid_until", None)

        document["valid_from"] = str_ops.datetime_from_iso_str(document.get("valid_from", None))
        document["valid_until"] = str_ops.datetime_from_iso_str(document.get("valid_until", None))

        if document.get("_id", None):
            udb.update_user_document(self.mdb.users, _id, document.pop("_id"), document)
        else:
            document_id = udb.add_user_document(self.mdb.users, _id, document)

            file = None
            if self.request.files:
                file = self.request.files["file"][0]

            if file:
                user_mdoc = udb.get_user(self.mdb.users, _id)
                file_name = self.make_document_name(user_mdoc, document, document_id)
                owncloud_url = self.process_file(file, file_name)
                udb.update_user_document(self.mdb.users, _id, document_id, {"url": owncloud_url})

        self.redirect(f"/users/u/{_id}", permanent=True)

    def process_file(self, file, document_name):
        extension = os.path.splitext(file["filename"])[1]

        new_filename = f"{document_name}{extension}"
        local_path = os.path.join("static", "tmp", new_filename)

        with open(local_path, "wb") as f:
            f.write(file["body"])

        owncloud_path = os.path.join(tornado.options.options.owncloud_root, "documents", new_filename)
        remote = save_file(self.mdb, owncloud_path)
        res = upload_file(self.oc, local_path, remote)
        print("res", res)

        return res.get_link()

    def make_document_name(self, user_mdoc, document, document_id):
        surname = user_mdoc.get("name", {}).get("surname", "unknown")
        return f"{document_id}_{surname}_{document['type']}"


class ApiUserDeleteDocumentHandler(BaseHandler):

    def post(self, _id):
        document_id = self.request.body.decode("utf-8")
        udb.delete_user_document(self.mdb.users, _id, document_id)

