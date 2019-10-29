from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import bson.json_util

from .helpers import str_ops
from plugins import BaseHandler
from .helpers import database_user as udb


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
        if not date:
            date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        user_document = udb.get_user(self.mdb.users, user_id)

        day_workspans = udb.get_user_workspans(self.mdb.users, user_id, date, date + timedelta(days=1))
        for ws in day_workspans:
            ws["to"] = str_ops.date_to_time_str(ws["from"] + timedelta(minutes=round(ws["hours"] * 60)))
            ws["from"] = str_ops.date_to_time_str(ws["from"])

        start_of_month = date.replace(day=1)
        end_of_month = start_of_month + relativedelta(months=1)
        month_workspans = udb.get_user_workspans(self.mdb.users, user_id, start_of_month, end_of_month)

        month_hours_worked = sum([ws["hours"] for ws in month_workspans])

        template_params = {
            "_id": user_id,
            "name": str_ops.name_to_str(user_document["name"]),
            "date": str_ops.date_to_iso_str(date),
            "date_pretty": str_ops.date_to_str(date),
            "workspans": day_workspans,
            "month_hours_worked": month_hours_worked,
        }

        print("month workspans", month_workspans)
        self.render("attendance.home.hbs", **template_params)


class ApiAddWorkSpanHandler(BaseHandler):

    def post(self, user_id):
        req = self.request.body.decode("utf-8")
        data = bson.json_util.loads(req)

        data["from"] = str_ops.datetime_from_iso_string_and_time_string(data["date"], data["from"])
        del data["date"]

        data["hours"] = float(data["hours"])

        udb.add_user_workspan(self.mdb.users, user_id, data)
