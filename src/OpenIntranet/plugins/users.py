#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta

import bson.json_util
import tornado
import tornado.options
from bson import ObjectId
from dateutil.relativedelta import relativedelta
from tornado.web import HTTPError

from plugins import BaseHandler, password_hash
from plugins import BaseHandlerOwnCloud
from plugins.helpers import database_user as udb
from plugins.helpers import str_ops
from plugins.helpers.assertions import assert_isinstance
from plugins.helpers.contract_generation import generate_contract
from plugins.helpers.doc_keys import CONTRACT_DOC_KEYS
from plugins.helpers.emails import generate_validation_token, generate_validation_message, send_email
from plugins.helpers.exceptions import BadInputHTTPError, MissingInfoHTTPError
from plugins.helpers.mdoc_ops import find_type_in_addresses, update_workspans_contract_id
from plugins.helpers.owncloud_utils import get_file_url, generate_contracts_directory_path, \
    generate_documents_directory_path


def make_handlers(plugin_name, plugin_namespace):
    return [
        (r'/{}/api/admintable'.format(plugin_name), plugin_namespace.ApiAdminTableHandler),
        (r'/{}/api/u/(.*)/edit'.format(plugin_name), plugin_namespace.ApiEditUserHandler),
        (r'/{}/api/u/(.*)/contracts/add'.format(plugin_name), plugin_namespace.ApiUserAddContractHandler),
        (r'/{}/api/u/(.*)/contracts/invalidate'.format(plugin_name), plugin_namespace.ApiUserInvalidateContractHandler),
        (r'/{}/api/u/(.*)/contracts/scan'.format(plugin_name), plugin_namespace.ApiUserUploadContractScanHandler),
        (r'/{}/api/u/(.*)/contracts/finalize'.format(plugin_name), plugin_namespace.ApiUserFinalizeContractHandler),
        (r'/{}/api/u/(.*)/documents/add'.format(plugin_name), plugin_namespace.ApiUserAddDocumentHandler),
        (r'/{}/api/u/(.*)/documents/invalidate'.format(plugin_name), plugin_namespace.ApiUserInvalidateDocumentHandler),
        (r'/{}/api/u/(.*)/documents/reupload'.format(plugin_name), plugin_namespace.ApiUserReuploadDocumentHandler),
        (r'/{}/api/u/(.*)/email/validate/(.*)'.format(plugin_name), plugin_namespace.ApiUserValidateEmail),
        (r'/{}/api/u/(.*)/email/validate'.format(plugin_name), plugin_namespace.ApiUserValidateEmail),
        (r'/{}/api/u/(.*)/password/change'.format(plugin_name), plugin_namespace.ApiUserChangePasswordHandler),
        (r'/{}/api/u/(.*)/password/change/token/(.*)'.format(plugin_name),
         plugin_namespace.ApiUserChangePasswordHandler),
        (r'/{}/u/(.*)'.format(plugin_name), plugin_namespace.UserPageHandler),
        (r'/{}'.format(plugin_name), plugin_namespace.HomeHandler),
        (r'/{}/'.format(plugin_name), plugin_namespace.HomeHandler),
    ]


def plug_info():
    return {
        "module": "users",
        "name": "Uživatelé",
        "icon": 'icon_users.svg',
        # "role": ['user-sudo', 'user-access', 'user-read', 'economy-read', 'economy-edit'],
    }


# TODO zkontrolovat práva
class HomeHandler(BaseHandler):
    # role_module = ['user-sudo', 'user-access', 'user-read', 'economy-read', 'economy-edit']

    def get(self, data=None):
        me = self.actual_user
        my_activity = list(self.mdb.operation_log.find({'user': me['user']}))

        if self.is_authorized(['users-editor', 'sudo-users']):
            users = self.mdb.users.find()
            self.render('users.home-sudo.hbs', title="TITLE", parent=self, users=users, me=me, my_activity=my_activity)
        else:
            self.redirect(f"/users/u/{me['_id']}")


# TODO doplnit práva
# TODO validovat vstup
class ApiAdminTableHandler(BaseHandler):

    def get(self, uid=None):
        data = udb.get_users(self.mdb.users)

        for item in data:
            item["_id"] = str(item["_id"])

            if "name" in item and not isinstance(item["name"], dict):
                item["full_name"] = item.pop("name")

            if "created" in item:
                item["created"] = item["created"].replace(microsecond=0).isoformat()
            if "birthdate" in item:
                item["birthdate"] = item["birthdate"].replace(microsecond=0).isoformat()

            item.pop("pass", None)

            if "role" in item:
                item["role"] = ",".join(item["role"])

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

        for fields in edited_data.values():
            self.validate_fields(fields)

        for _id in deleted_ids:
            udb.delete_user(self.mdb.users, ObjectId(_id))

        if new_ids:
            udb.add_users(self.mdb.users, [ObjectId(_id) for _id in new_ids])

        for _id, fields in edited_data.items():
            self.process_and_update(ObjectId(_id), fields)

    def process_and_update(self, user_id, data):
        """
        Zajistí, že data uživatele jsou v odpovídajícím tvaru pro uložení do databáze a uloží je.
        """
        keys = list(data.keys())
        residence_address = {key.split(".")[1]: data.pop(key) for key in keys if "residence_address" in key}
        contact_address = {key.split(".")[1]: data.pop(key) for key in keys if "contact_address" in key}

        if "birthdate" in data and data["birthdate"] != "":
            data["birthdate"] = datetime.strptime(data["birthdate"], "%Y-%m-%d")

        if "role" in data:
            data["role"] = data["role"].replace(" ", "").split(",")

        if "email" in data:
            data["email_validated"] = "no"

        if data:
            udb.update_user(self.mdb.users, user_id, data)

        if residence_address:
            residence_address["type"] = "residence"
            udb.update_user_address(self.mdb.users, user_id, residence_address)

        if contact_address:
            contact_address["type"] = "contact"
            udb.update_user_address(self.mdb.users, user_id, contact_address)

    def validate_fields(self, fields):
        if "email" in fields:
            matching_users_in_db = udb.get_users(self.mdb.users, email=fields["email"])
            if matching_users_in_db:
                raise BadInputHTTPError("Uživatel s touto emailovou adresou již existuje.")

        if "user" in fields:
            matching_users_in_db = udb.get_users(self.mdb.users, user=fields["user"])
            if matching_users_in_db:
                raise BadInputHTTPError("Uživatel s tímto přihlašovacím jménem již existuje.")


# TODO doplnit práva
# TODO validovat vstup
class ApiEditUserHandler(BaseHandler):

    def post(self, user_id):
        user_id = ObjectId(user_id)

        req = self.request.body.decode("utf-8")
        changes = bson.json_util.loads(req)

        residence_address = changes.pop("residence_address", {})
        contact_address = changes.pop("contact_address", {})

        if "birthdate" in changes and changes["birthdate"] != "":
            changes["birthdate"] = datetime.strptime(changes["birthdate"], "%Y-%m-%d")

        if "role" in changes:
            changes["role"] = changes["role"].replace(" ", "").split(",")

        if "email" in changes:
            matching_users_in_db = udb.get_users(self.mdb.users, email=changes["email"])
            if matching_users_in_db:
                raise BadInputHTTPError("Uživatel s touto emailovou adresou již existuje.")
            changes["email_validated"] = "no"  # TODO je potřeba tuto kontrolu dát na jedno místo

        if changes:
            udb.update_user(self.mdb.users, user_id, changes)

        if residence_address:
            residence_address["type"] = "residence"
            udb.update_user_address(self.mdb.users, user_id, residence_address)
        if contact_address:
            contact_address["type"] = "contact"
            udb.update_user_address(self.mdb.users, user_id, contact_address)


# TODO doplnit práva
class UserPageHandler(BaseHandler):

    def get(self, user_id):
        user_id = ObjectId(user_id)

        user_document = udb.get_user(self.mdb.users, user_id)

        name_doc = user_document.get("name", {})
        if not isinstance(name_doc, dict):
            name_doc = {}

        res_address_doc = find_type_in_addresses(user_document.get("addresses", {}), "residence") or {}
        cont_address_doc = find_type_in_addresses(user_document.get("addresses", {}), "contact") or {}

        birthdate = user_document.get("birthdate", None)

        template_params = {
            "user": user_document.get("user", ""),
            "_id": str(user_document.get("_id")),

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
            "role": ",".join(user_document.get("role", [])),
            "assignment": user_document.get("assignment", ""),
            "skills": user_document.get("skills", ""),
            "notes": user_document.get("notes", ""),

            "today": str_ops.date_to_iso_str(datetime.now())
        }

        contracts = udb.get_user_contracts(self.mdb.users, user_id)
        template_params["contracts"] = self.prepare_contracts(contracts)
        documents = user_document.get("documents", [])
        template_params["documents_json"] = self.prepare_documents(documents)

        print("template_params", template_params)
        self.render("users.home.hbs", **template_params)

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
            new["valid_from_iso"] = str_ops.date_to_iso_str(valid_from)
            new["valid_until_iso"] = str_ops.date_to_iso_str(valid_until)
            new["valid_from"] = str_ops.date_to_str(valid_from)
            new["valid_until"] = str_ops.date_to_str(valid_until)
            new["notes"] = contract.get("notes", "")
            new["title"] = f"{new['type']} {new['valid_from']} - {new['valid_until']}"
            new["url"] = get_file_url(self.mdb, contract["file"])

            if "scan_file" in contract:
                new["scan_signed_url"] = get_file_url(self.mdb, contract["scan_file"])
            else:
                new["scan_signed_url"] = None

            new["is_valid"] = False

            effective_valid_until = valid_until
            if "invalidation_date" in contract:
                effective_valid_until = min(valid_until, contract["invalidation_date"] - timedelta(days=1))

            if contract["valid_from"] <= datetime.now() <= effective_valid_until + timedelta(days=1):
                new["is_valid"] = True

            if contract.get("invalidation_date", False):
                new["invalidation_date_iso"] = str_ops.date_to_iso_str(contract["invalidation_date"])
                new["invalidation_date"] = str_ops.date_to_str(contract["invalidation_date"])

            if new["is_valid"]:
                result.insert(0, new)
            else:
                result.append(new)

        return result

    def prepare_documents(self, documents):
        possible_type = {
            "study_certificate": "Potvrzení o studiu",
            "tax_declaration": "Prohlášení k dani"
        }

        study_certificates = []
        tax_declarations = []

        for document in documents:

            valid_from_text = str_ops.date_to_str(document.get("valid_from", None))
            valid_until_text = str_ops.date_to_str(document.get("valid_until", None))

            effective_valid_until = document["valid_until"]
            if "invalidation_date" in document:
                effective_valid_until = min(document["valid_until"], document["invalidation_date"] - timedelta(days=1))

            if document["valid_from"] <= datetime.now() <= effective_valid_until + timedelta(days=1):
                document["is_valid"] = True
            else:
                document["is_valid"] = False

            if "invalidation_date" in document:
                document["invalidation_date_text"] = str_ops.date_to_str(document["invalidation_date"])
                document["invalidation_date"] = str_ops.date_to_iso_str(document["invalidation_date"])

            document["type_text"] = possible_type[document["type"]]
            document["valid_from_text"] = valid_from_text
            document["valid_until_text"] = valid_until_text
            document["valid_from"] = str_ops.date_to_iso_str(document.get("valid_from", None))
            document["valid_until"] = str_ops.date_to_iso_str(document.get("valid_until", None))

            document["url"] = get_file_url(self.mdb, document["file"])
            del document["file"]

            date_texts = [date for date in [valid_from_text, valid_until_text] if date]
            document["title"] = f"{document['type_text']} {' - '.join(date_texts)}"

            if document["type"] == "study_certificate":
                if document["is_valid"]:
                    study_certificates.insert(0, document)
                else:
                    study_certificates.append(document)
            elif document["type"] == "tax_declaration":
                if document["is_valid"]:
                    tax_declarations.insert(0, document)
                else:
                    tax_declarations.append(document)

        final_structure = {
            "study_certificate": study_certificates,
            "tax_declaration": tax_declarations,
        }

        return json.dumps(final_structure)


# TODO doplnit práva
# TODO validovat vstup
class ApiUserAddContractHandler(BaseHandlerOwnCloud):

    async def post(self, user_id):
        user_id = ObjectId(user_id)

        req = self.request.body.decode("utf-8")
        contract = bson.json_util.loads(req)

        if "_id" in contract:
            raise ValueError("Nedefinovaný stav")  # pozůstatek po předchozí funkcionalitě

        contract["signing_date"] = str_ops.datetime_from_iso_str(contract["signing_date"])
        contract["valid_from"] = str_ops.datetime_from_iso_str(contract["valid_from"])
        contract["valid_until"] = str_ops.datetime_from_iso_str(contract["valid_until"])
        contract["hour_rate"] = int(contract["hour_rate"])
        contract["birthdate"] = str_ops.datetime_from_iso_str(contract["birthdate"])

        if not self.check_for_conflict_with_other_contracts(user_id, contract):
            raise BadInputHTTPError("Uživatel může mít v danou chvíli jen jednu platnou smlouvu.")

        if not self.check_for_inconsistent_hour_rate(user_id, contract):
            raise BadInputHTTPError("Uživatel musí mít po celý měsíc stejnou hodinovou mzdu.")

        local_path = generate_contract(user_id, contract,
                                       self.company_info["name"],
                                       self.company_info["address"],
                                       self.company_info["crn"])

        user_mdoc = udb.get_user(self.mdb.users, user_id)

        owncloud_directory = generate_contracts_directory_path(user_id, user_mdoc["user"], contract["valid_from"])
        owncloud_filename = f"contract_{contract['type']}"

        file_id = await self.upload_to_owncloud(owncloud_directory, owncloud_filename, local_path)

        contract["file"] = file_id

        for key in list(contract.keys()):
            if key not in CONTRACT_DOC_KEYS:
                del contract[key]

        contract_id = udb.add_user_contract_preview(self.mdb.users, user_id, contract)

        response = {
            "_id": contract_id,
            "url": get_file_url(self.mdb, file_id)
        }
        self.write(json.dumps(response))

    def check_for_conflict_with_other_contracts(self, user_id, contract):
        other_contracts = udb.get_user_active_contracts(self.mdb,
                                                        user_id,
                                                        contract["valid_from"],
                                                        contract["valid_until"])
        print("-> checking conflicts, other contracts:", other_contracts)
        return not other_contracts

    def check_for_inconsistent_hour_rate(self, user_id, contract):
        month_of_start = contract["valid_from"].replace(day=1)
        month_of_end = contract["valid_until"].replace(day=1)

        for month in [month_of_start, month_of_end]:
            other_contracts = udb.get_user_active_contracts(self.mdb,
                                                            user_id,
                                                            month,
                                                            month + relativedelta(months=1))
            print("-> checking hour rates, other contracts:", other_contracts)
            for other_contract in other_contracts:
                print("-> other contract:", other_contract)
                if contract["hour_rate"] != other_contract["hour_rate"]:
                    return False

        return True


# TODO doplnit práva
class ApiUserFinalizeContractHandler(BaseHandler):

    def post(self, user_id):
        user_id = ObjectId(user_id)

        contract_id = self.request.body.decode("utf-8")
        contract = udb.get_user_contract_by_id(self.mdb, user_id, contract_id)

        update_workspans_contract_id(self.mdb, user_id,
                                     contract["valid_from"],
                                     contract["valid_until"] + relativedelta(days=1),
                                     contract_id)

        udb.unmark_user_contract_as_preview(self.mdb, user_id, contract_id)


# TODO doplnit práva
# TODO validovat vstup
class ApiUserInvalidateContractHandler(BaseHandler):

    def post(self, user_id):
        user_id = ObjectId(user_id)

        req = self.request.body.decode("utf-8")
        data = json.loads(req)

        invalidation_date = str_ops.datetime_from_iso_str(data["date"])
        contract_mdoc = udb.get_user_contract_by_id(self.mdb, user_id, data["_id"])

        if not (contract_mdoc["valid_from"] <= invalidation_date <= contract_mdoc["valid_until"]):
            raise BadInputHTTPError("Datum zneplatnění smlouvy musí spadat do období platnosti smlouvy.")

        update_workspans_contract_id(self.mdb, user_id,
                                     invalidation_date,
                                     contract_mdoc["valid_until"] + relativedelta(days=1),
                                     None)

        udb.invalidate_user_contract(self.mdb.users, user_id, data["_id"], invalidation_date)


# TODO doplnit práva
class ApiUserUploadContractScanHandler(BaseHandlerOwnCloud):

    async def post(self, user_id):
        user_id = ObjectId(user_id)

        contract_id = self.get_argument("_id")

        local_path, = self.save_uploaded_files("file")
        if not local_path:
            self.redirect(f"/users/u/{user_id}", permanent=True)
            return

        contract_mdoc = udb.get_user_contract_by_id(self.mdb, user_id, contract_id)
        if "scan_file" in contract_mdoc:
            await self.update_owncloud_file(contract_mdoc["scan_file"], local_path)
        else:
            user_mdoc = udb.get_user(self.mdb.users, user_id)
            owncloud_directory = generate_contracts_directory_path(user_id,
                                                                   user_mdoc["user"],
                                                                   contract_mdoc["valid_from"])
            owncloud_filename = f"contract_scan_{contract_mdoc['type']}"

            file_id = await self.upload_to_owncloud(owncloud_directory, owncloud_filename, local_path)
            udb.add_user_contract_scan(self.mdb.users, user_id, contract_id, file_id)

        self.redirect(f"/users/u/{user_id}", permanent=True)


# TODO doplnit práva
# TODO validovat vstup
# TODO potvrzení o studiu nelze přidat bez existujícího prohlášení o dani
class ApiUserAddDocumentHandler(BaseHandlerOwnCloud):

    async def post(self, user_id):
        user_id = ObjectId(user_id)

        document = {
            "_id": self.get_argument("_id"),
            "type": self.get_argument("type"),
            "valid_from": self.get_argument("valid_from"),
            "valid_until": self.get_argument("valid_until"),
            "notes": self.get_argument("notes")
        }
        print("document", document)
        if document.get("_id", None):
            raise ValueError("nedefinovaný stav")

        document["valid_from"] = str_ops.datetime_from_iso_str(document.get("valid_from", None))
        document["valid_until"] = str_ops.datetime_from_iso_str(document.get("valid_until", None))

        user_mdoc = udb.get_user(self.mdb.users, user_id)

        owncloud_directory = generate_documents_directory_path(user_id, user_mdoc["user"], document["valid_from"])
        owncloud_filename = f"document_{document['type']}"

        local_paths = self.save_uploaded_files("file")
        if local_paths:
            document["file"] = await self.upload_to_owncloud(owncloud_directory, owncloud_filename, local_paths[0])
        else:
            document["file"] = self.create_empty_owncloud_record(owncloud_directory, owncloud_filename)

        udb.add_user_document(self.mdb.users, user_id, document)

        self.redirect(f"/users/u/{user_id}", permanent=True)


# TODO doplnit práva
class ApiUserReuploadDocumentHandler(BaseHandlerOwnCloud):

    async def post(self, user_id):
        user_id = ObjectId(user_id)

        document_id = self.get_argument("_id")
        print(document_id)
        local_path, = self.save_uploaded_files("file")

        owncloud_id = udb.get_user_document_owncloud_id(self.mdb.users, user_id, document_id)
        await self.update_owncloud_file(owncloud_id, local_path)

        self.redirect(f"/users/u/{user_id}", permanent=True)


# TODO doplnit práva
class ApiUserInvalidateDocumentHandler(BaseHandler):

    def post(self, user_id):
        user_id = ObjectId(user_id)

        req = self.request.body.decode("utf-8")
        data = json.loads(req)

        invalidation_date = str_ops.datetime_from_iso_str(data["date"])
        document_mdoc = udb.get_user_document_by_id(self.mdb, user_id, data["_id"])

        if not (document_mdoc["valid_from"] <= invalidation_date <= document_mdoc["valid_until"]):
            raise BadInputHTTPError("Datum zneplatnění dokumentu musí spadat do období platnosti dokumentu.")

        udb.invalidate_user_document(self.mdb.users, user_id, data["_id"], invalidation_date)


# TODO doplnit práva
class ApiUserValidateEmail(BaseHandler):

    def get(self, user_id, token):
        user_id = ObjectId(user_id)

        print(f"validate_email, user_id = {user_id}, token = {token}")

        user_mdoc = udb.get_user(self.mdb.users, user_id)

        if user_mdoc["email_validated"] == "yes":
            if "pass" in user_mdoc:
                self.render("users.email_validation.hbs", success=True, message="Email již byl ověřen.")
                return
            else:
                self.redirect(f"/users/api/u/{user_id}/password/change/token/{token}")

        token_in_db = user_mdoc.get("email_validation_token", None)
        if user_mdoc["email_validated"] == "pending" and token == token_in_db:
            udb.update_user_email_is_validated_status(self.mdb.users, user_id, yes=True)
            if "pass" in user_mdoc:
                self.render("users.email_validation.hbs", success=True)
            else:
                udb.user_set_password_change_token(self.mdb.users, user_id, token)
                self.redirect(f"/users/api/u/{user_id}/password/change/token/{token}")

        self.render("users.email_validation.hbs", success=False, message="Ověření se nezdařilo.")

    def post(self, user_id):
        user_id = ObjectId(user_id)

        print(f"validate_email pro {user_id}")

        user_mdoc = udb.get_user(self.mdb.users, user_id)

        if "email" not in user_mdoc:
            raise BadInputHTTPError("Uživatel nemá emailovou adresu.")

        token = generate_validation_token()
        message = generate_validation_message(user_mdoc["email"], user_id, token, tornado.options.options)
        send_email(message, tornado.options.options)

        udb.update_user_email_is_validated_status(self.mdb.users, user_id, token=token)


class ApiUserChangePasswordHandler(BaseHandler):

    def get(self, user_id, token=None):
        self.render("users.change_password.hbs", _id=user_id, token=token)

    def post(self, user_id):
        user_id = ObjectId(user_id)

        req = self.request.body.decode("utf-8")
        fields = json.loads(req)

        if "new_password" not in fields or not fields["new_password"]:
            raise MissingInfoHTTPError("Je nutné vyplnit nové heslo.")

        if "new_password_check" not in fields or not fields["new_password_check"]:
            raise MissingInfoHTTPError("Je nutné vyplnit kontrolu hesla.")

        if fields["new_password"] != fields["new_password_check"]:
            raise BadInputHTTPError("Nová hesla se musejí shodovat.")

        user_mdoc = udb.get_user(self.mdb.users, user_id)

        if "token" in fields:
            token_in_db = user_mdoc.get("password_change_token", None)
            if token_in_db != fields["token"]:
                raise BadInputHTTPError("Ověření pomocí tokenu se nezdařilo.")

            udb.user_unset_password_change_token(self.mdb.users, user_id)

        else:
            if user_id != self.actual_user["_id"]:
                raise HTTPError(status_code=403, log_message="Heslo můžete změnit jen sobě.")

            if "old_password" not in fields or not fields["old_password"]:
                raise MissingInfoHTTPError("Je nutné vyplnit stávající heslo.")

            password_hash_in_db = user_mdoc["pass"]
            given_old_password_hash = password_hash(user_mdoc["user"], fields["old_password"])

            if password_hash_in_db != given_old_password_hash:
                raise BadInputHTTPError("Bylo zadáno špatné stávající heslo.")

        new_password_hash = password_hash(user_mdoc["user"], fields["new_password"])

        self.mdb.users.update_one({"_id": user_id},
                                  {
                                      "$set": {"pass": new_password_hash},
                                  })






