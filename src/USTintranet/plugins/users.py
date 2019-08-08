#!/usr/bin/python3
# -*- coding: utf-8 -*-
from datetime import datetime

import bson.json_util

from . import BaseHandler
from .users_helpers import database as db
from .users_helpers import tostr


def make_handlers(plugin_name, plugin_namespace):
    return [
        (r'/{}/api/admintable'.format(plugin_name), plugin_namespace.ApiAdminTableHandler),
        (r'/{}/api/u/(.*)/edit'.format(plugin_name), plugin_namespace.ApiEditUserHandler),
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

            "name": tostr.name_to_str(name_doc),
            "pre_name_title": name_doc.get("pre_name_title", ""),
            "first_name": name_doc.get("first_name", ""),
            "surname": name_doc.get("surname", ""),
            "post_name_title": name_doc.get("post_name_title", ""),

            "birthdate": tostr.date_to_str(birthdate),
            "birthdate_iso": tostr.date_to_iso_string(birthdate),

            "residence_address": tostr.address_to_str(res_address_doc),
            "residence_street": res_address_doc.get("street", ""),
            "residence_city": res_address_doc.get("city", ""),
            "residence_state": res_address_doc.get("state", ""),
            "residence_zip": res_address_doc.get("zip", ""),

            "contact_address": tostr.address_to_str(cont_address_doc),
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

        self.render("users.user-page.hbs", **template_params)
