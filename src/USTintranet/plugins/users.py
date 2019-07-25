#!/usr/bin/python3
# -*- coding: utf-8 -*-

import bson.json_util

from . import BaseHandler
from .users_helpers import database as db


def make_handlers(plugin_name, plugin_namespace):
    return [
        (r'/{}/api/user/admintable'.format(plugin_name), plugin_namespace.ApiAdminTableHandler),
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
            item["id"] = str(item["_id"])
            if "created" in item:
                item["created"] = item["created"].replace(microsecond=0).isoformat()
            del item["_id"]
            if "pass" in item:
                del item["pass"]

        out = bson.json_util.dumps(data)
        self.write(out)

    def post(self):
        data = bson.json_util.loads(self.request.body.decode("utf-8"))

        edited = data["edited"]
        new = data["new"]
        deleted = data["deleted"]

        db.update_users(self.mdb.users, edited)

        if new:
            new_formated = []
            for _id, data in new.items():
                data["_id"] = _id
                data["type"] = "user"
                new_formated.append(data)

            db.add_users(self.mdb.users, new_formated)

        db.delete_users(self.mdb.users, deleted)
