#!/usr/bin/python3
# -*- coding: utf-8 -*-
from datetime import datetime

import bson.json_util

from . import BaseHandler
from .users_helpers import database as db

EXPECTED_FIELDS = [
    "user",
    "pass",
    "email",
    "email_validate",
    "role",
    "created",
    "type",
    "name",
    "pre_name_title",
    "first_name",
    "surname",
    "post_name_title",
    "birthdate",
    "addresses",
    "phone_number",
    "account_number",
    "assignment",
    "contracts",
    "skills",
    "notes",
    "work_spans",
    "vacations",
    "documents",
    "wages",
    "month_closed",
]

EMPTY_USER_DOC = {
    "user": None,
    "pass": None,
    "email": None,
    "email_validate": None,
    "role": [],
    "created": None,
    "type": None,
    "name": None,
    "birthdate": None,
    "addresses": [],
    "phone_number": None,
    "account_number": None,
    "assignment": None,
    "contracts": [],
    "skills": None,
    "notes": None,
    "work_spans": [],
    "vacations": [],
    "documents": [],
    "wages": [],
    "month_closed": None,
}
EMPTY_NAME_DOC = {
    "pre_name_title": None,
    "first_name": None,
    "surname": None,
    "post_name_title": None,
}
EMPTY_ADDRESS_DOC = {
    "street": None,
    "city": None,
    "state": None,
    "zip": None,
    "type": None,
}
EMPTY_CONTRACT_DOC = {
    "type": None,
    "signing_date": None,
    "valid_from": None,
    "valid_until": None,
    "hour_rate": None,
    "is_valid": None,
}
EMPTY_DOCUMENT_DOC = {
    "type": None,
    "valid_from": None,
    "valid_until": None,
    "path_to_file": None,
}
EMPTY_VACATION_DOC = {
    "from": None,
    "until": None,
    "do_not_disturb": None,
}
EMPTY_WAGE_DOC = {
    "month": None,
    "hours_worked": None,
    "gross_wage": None,
    "is_taxed": None,
    "net_wage": None,
}
EMPTY_WORKSPAN_DOC = {
    "from": None,
    "hours": None,
    "note": None,
    "assignment": None,
}


def make_handlers(plugin_name, plugin_namespace):
    return [
        (r'/{}/api/user/admintable'.format(plugin_name), plugin_namespace.ApiAdminTableHandler),
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
            item["_id"] = str(item["_id"])

            if "created" in item:
                item["created"] = item["created"].replace(microsecond=0).isoformat()

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
        data = bson.json_util.loads(self.request.body.decode("utf-8"))

        edited_data = data["edited"]
        new_ids = data["new"]
        deleted_ids = data["deleted"]

        for _id in deleted_ids:
            db.delete_user(self.mdb.users, _id)

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

        if "birthdate" in data:
            data["birthdate"] = datetime.strptime(data["birthdate"], "%Y-%m-%d")

        if data:
            db.update_user(self.mdb.users, _id, data)

        if residence_address:
            residence_address["type"] = "residence"
            db.update_user_address(self.mdb.users, _id, residence_address)

        if contact_address:
            contact_address["type"] = "contact"
            db.update_user_address(self.mdb.users, _id, contact_address)


class UserPageHandler(BaseHandler):

    def get(self, _id):
        print(_id)
        user_document = db.get_user(self.mdb.users, _id)
        print(user_document)

        for key in EXPECTED_FIELDS:
            if key not in user_document:
                user_document[key] = None

        self.render("users.user-page.hbs", user_doc=user_document)
