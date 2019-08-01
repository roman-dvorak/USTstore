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
            if "pass" in item:
                del item["pass"]

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

        edited_raw = data["edited"]
        new_ids = data["new"]
        deleted_ids = data["deleted"]

        if deleted_ids:
            db.delete_users(self.mdb.users, deleted_ids)

        edited_formatted = self.prepare_edited(edited_raw)

        edited = {_id: fields for _id, fields in edited_formatted.items() if _id not in new_ids}
        db.update_users(self.mdb.users, edited)

        if new_ids:
            new = self.prepare_new(edited_formatted, new_ids)
            db.add_users(self.mdb.users, new)

    def prepare_edited(self, raw):
        formatted = {}

        for _id, fields in raw.items():
            if any([key in fields for key in EMPTY_NAME_DOC.keys()]):
                fields["name"] = {}

            for key in EMPTY_NAME_DOC.keys():
                if key in fields:
                    fields["name"][key] = fields[key]

            formatted[_id] = fields

        return formatted

    def prepare_new(self, data, ids):
        prepared = []
        for _id, fields in data.items():
            if _id in ids:
                fields["_id"] = _id
                fields["type"] = "user"
                fields["created"] = datetime.now().replace(microsecond=0)
                prepared.append(fields)

        return prepared


class UserPageHandler(BaseHandler):

    def get(self, _id):
        print(_id)
        user_document = db.get_user(self.mdb.users, _id)
        print(user_document)

        for key in EXPECTED_FIELDS:
            if key not in user_document:
                user_document[key] = None

        self.render("users.user-page.hbs", user_doc=user_document)
