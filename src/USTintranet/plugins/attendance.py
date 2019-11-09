from datetime import datetime, timedelta

import bson.json_util
from dateutil.relativedelta import relativedelta

from plugins import BaseHandler
from plugins.helpers import database_attendance as adb
from plugins.helpers import database_user as udb
from plugins.helpers import str_ops
from plugins.helpers.mdoc_ops import compile_user_month_info


def make_handlers(plugin_name, plugin_namespace):
    return [
        (r'/{}/u/(.*)/date/(.*)'.format(plugin_name), plugin_namespace.UserAttendanceHandler),
        (r'/{}/u/(.*)'.format(plugin_name), plugin_namespace.UserAttendanceHandler),
        (r'/{}/api/u/(.*)/workspans'.format(plugin_name), plugin_namespace.ApiAddWorkspanHandler),
        (r'/{}/api/u/(.*)/workspans/delete'.format(plugin_name), plugin_namespace.ApiDeleteWorkspanHandler),
        (r'/{}/api/u/(.*)/vacations'.format(plugin_name), plugin_namespace.ApiAddVacationHandler),
        (r'/{}/api/u/(.*)/vacations/delete'.format(plugin_name), plugin_namespace.ApiDeleteVacationHandler),
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

        day_workspans = adb.get_user_workspans(self.mdb.users, user_id, date, date + timedelta(days=1))
        for ws in day_workspans:
            ws["to"] = str_ops.date_to_time_str(ws["from"] + timedelta(minutes=round(ws["hours"] * 60)))
            ws["from"] = str_ops.date_to_time_str(ws["from"])

        current_and_future_vacations = adb.get_user_vacations(self.mdb.users, user_id, date)

        is_vacation_day = current_and_future_vacations and current_and_future_vacations[0]["from"] <= date

        for vacation in current_and_future_vacations:
            vacation["from"] = str_ops.date_to_str(vacation["from"])
            vacation["to"] = str_ops.date_to_str(vacation["to"])

        template_params = {
            "_id": user_id,
            "name": str_ops.name_to_str(user_document["name"]),
            "date": str_ops.date_to_iso_str(date),
            "date_pretty": str_ops.date_to_str(date),
            "workspans": day_workspans,
            "vacations": current_and_future_vacations,
            "is_vacation_day": is_vacation_day
        }
        template_params.update(compile_user_month_info(self.mdb.users, user_id, datetime.now()))

        self.render("attendance.home.hbs", **template_params)


class ApiAddWorkspanHandler(BaseHandler):

    def post(self, user_id):
        # TODO upravování poslaných dat (jsonovaného dictu) a ukládaní přímo jich do db je potenciálně problematické
        # lepší by asi bylo postavit nový dict a items které není potřeba upravovat prostě zkopírovat
        # možná trochu porušuje DRY ale je to čitelnější (je jasnější co se ukládá do db)

        req = self.request.body.decode("utf-8")
        workspan = bson.json_util.loads(req)

        workspan["from"] = str_ops.datetime_from_iso_string_and_time_string(workspan["date"], workspan["from"])
        del workspan["date"]
        workspan["hours"] = float(workspan["hours"])

        self.check_vacations_conflicts(user_id, workspan)
        self.check_workspans_conflicts(user_id, workspan)

        adb.add_user_workspan(self.mdb.users, user_id, workspan)

    def check_vacations_conflicts(self, user_id, workspan):
        # z databáze dostaneme dovolené končící dnes nebo později seřazené podle data konce.
        # první dovolená je nejblíž, stačí tedy zkontrolovat, jestli začíná dnes nebo dříve.
        today = workspan["from"].replace(hour=0, minute=0, second=0, microsecond=0)
        vacations = adb.get_user_vacations(self.mdb.users, user_id, today)
        if vacations and vacations[0]["from"] <= workspan["from"]:
            raise ValueError("Na dovolené se nepracuje.")

    def check_workspans_conflicts(self, user_id, workspan):
        today = workspan["from"].replace(hour=0, minute=0, second=0, microsecond=0)
        tomorow = today + relativedelta(days=1)

        todays_workspans = adb.get_user_workspans(self.mdb.users, user_id, today, tomorow)
        workspan_end = workspan["from"] + relativedelta(minutes=int(workspan["hours"] * 60))

        for other_ws in todays_workspans:
            latest_start = max(workspan["from"], other_ws["from"])
            earliest_end = min(workspan_end, other_ws["from"] + relativedelta(minutes=int(other_ws["hours"]) * 60))

            if latest_start < earliest_end:
                raise ValueError("Časový konflikt s jinou prací")  # TODO mělo by se ohlásit ve frontendu


class ApiAddVacationHandler(BaseHandler):

    def post(self, user_id):
        req = self.request.body.decode("utf-8")
        data = bson.json_util.loads(req)

        vacation = {
            "from": str_ops.date_from_iso_str(data["from"]),
            "to": str_ops.date_from_iso_str(data["to"])
        }

        if vacation["from"] > vacation["to"]:
            raise ValueError("Dovolená skončila dříve než začala.")  # TODO mělo by se ohlásit ve frontendu

        other_vacations = adb.get_user_vacations(self.mdb.users, user_id, vacation["from"])
        for other_vac in other_vacations:
            latest_start = max(vacation["from"], other_vac["from"])
            earliest_end = min(vacation["to"], other_vac["to"])

            if latest_start <= earliest_end:
                raise ValueError("Časový konflikt s jinou dovolenou")  # TODO mělo by se ohlásit ve frontendu

        adb.add_user_vacation(self.mdb.users, user_id, vacation)


class ApiDeleteVacationHandler(BaseHandler):

    def post(self, user_id):
        vacation_id = self.request.body.decode("utf-8")
        adb.delete_user_vacation(self.mdb.users, user_id, vacation_id)


class ApiDeleteWorkspanHandler(BaseHandler):

    def post(self, user_id):
        workspan_id = self.request.body.decode("utf-8")
        adb.delete_user_workspan(self.mdb.users, user_id, workspan_id)
