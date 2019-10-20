from datetime import datetime

import bson.json_util

from .users_helpers import str_ops
from plugins import BaseHandler
from .users_helpers import database as db


def make_handlers(plugin_name, plugin_namespace):
    return [
        (r'/{}/u/(.*)/date/(.*)'.format(plugin_name), plugin_namespace.UserAttendanceHandler),
        (r'/{}/u/(.*)'.format(plugin_name), plugin_namespace.UserAttendanceHandler),
        (r'/{}/api/u/(.*)/workspans'.format(plugin_name), plugin_namespace.ApiAddWorkSpanHandler),
        (r'/{}'.format(plugin_name), plugin_namespace.HomeHandler),
        (r'/{}/'.format(plugin_name), plugin_namespace.HomeHandler),
    ]


def plug_info():
    return {
        "module": "attendance",
        "name": "Docházka",
        "icon": 'icon_users.svg',
        "role": ['user-sudo', 'user-access', 'user-read', 'economy-read', 'economy-edit'],
    }


class HomeHandler(BaseHandler):

    def get(self):
        self.write("attendance home")


class UserAttendanceHandler(BaseHandler):

    def get(self, user_id, date_str=None):
        date = str_ops.date_from_iso_str(date_str)
        user_document = db.get_user(self.mdb.users, user_id)

        template_params = {
            "_id": user_id,
            "name": str_ops.name_to_str(user_document["name"]),
            "date": str_ops.date_to_iso_str(date),
            "date_pretty": str_ops.date_to_str(date)
        }

        self.render("attendance.home.hbs", **template_params)


class ApiAddWorkSpanHandler(BaseHandler):

    def post(self, user_id):
        req = self.request.body.decode("utf-8")
        data = bson.json_util.loads(req)

        print(data)
