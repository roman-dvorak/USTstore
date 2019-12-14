import calendar
import functools
from datetime import datetime, timedelta

import bson.json_util
from dateutil.relativedelta import relativedelta
from tornado.web import HTTPError

from plugins import BaseHandler, get_dpp_params
from plugins.helpers import database_attendance as adb
from plugins.helpers import database_user as udb
from plugins.helpers import str_ops
from plugins.helpers.exceptions import BadInputError
from plugins.helpers.finance import calculate_tax
from plugins.helpers.mdoc_ops import compile_user_month_info, get_user_days_of_vacation_in_year


def make_handlers(plugin_name, plugin_namespace):
    return [
        (r'/{}/u/(.*)/date/(.*)'.format(plugin_name), plugin_namespace.UserAttendanceHandler),
        (r'/{}/u/(.*)'.format(plugin_name), plugin_namespace.UserAttendanceHandler),
        (r'/{}/api/u/(.*)/workspans'.format(plugin_name), plugin_namespace.ApiAddWorkspanHandler),
        (r'/{}/api/u/(.*)/calendar/date/(.*)'.format(plugin_name), plugin_namespace.ApiCalendarHandler),
        (r'/{}/api/u/(.*)/monthinfo/date/(.*)'.format(plugin_name), plugin_namespace.ApiMonthInfoHandler),
        (r'/{}/api/u/(.*)/workspans/delete'.format(plugin_name), plugin_namespace.ApiDeleteWorkspanHandler),
        (r'/{}/api/u/(.*)/vacations'.format(plugin_name), plugin_namespace.ApiAddVacationHandler),
        (r'/{}/api/u/(.*)/vacations/delete'.format(plugin_name), plugin_namespace.ApiDeleteVacationHandler),
        (r'/{}/api/month_table/(.*)'.format(plugin_name), plugin_namespace.ApiAdminMonthTableHandler),
        (r'/{}/api/year_table/(.*)'.format(plugin_name), plugin_namespace.ApiAdminYearTableHandler),
        (r'/{}'.format(plugin_name), plugin_namespace.HomeHandler),
        (r'/{}/'.format(plugin_name), plugin_namespace.HomeHandler),
    ]


def plug_info():
    return {
        "module": "attendance",
        "name": "Docházka",
        "icon": 'icon_users.svg',
        # "role": ['user-sudo', 'user-access', 'user-read', 'economy-read', 'economy-edit'],
    }


class HomeHandler(BaseHandler):

    def get(self):
        me = self.actual_user

        if self.is_authorized(['users-editor', 'sudo-users']):
            self.render('attendance.home-sudo.hbs')
        else:
            self.redirect(f"/attendance/u/{me['_id']}")


def cachedproperty(func):
    func_name = func.__name__

    @property
    @functools.wraps(func)
    def inner(self):
        if not hasattr(self, "_cache"):
            self._cache = {}

        if func_name not in self._cache:
            self._cache[func_name] = func(self)

        return self._cache[func_name]

    return inner


class AttendanceCalculator:

    def __init__(self, user_id, from_date, to_date, database):
        self.user_id = user_id
        self.from_date = from_date
        self.to_date = to_date
        self.database = database

        self.dpp_params = get_dpp_params(self.database)
        self.year_max_hours = self.dpp_params["year_max_hours"]
        self.month_max_gross_wage = self.dpp_params["month_max_gross_wage"]
        self.tax_rate = self.dpp_params["tax_rate"]
        self.tax_deduction = self.dpp_params["tax_deduction"]
        self.tax_deduction_student = self.dpp_params["tax_deduction_student"]

        self._cache = {}

    @cachedproperty
    def workspans(self):
        return adb.get_user_workspans(self.database, self.user_id, self.from_date, self.to_date)

    @cachedproperty
    def contracts(self):
        return udb.get_user_active_contracts(self.database, self.user_id, self.from_date, self.to_date)

    @cachedproperty
    def study_certificates(self):
        return self._get_documents("study_certificate")

    @cachedproperty
    def tax_declarations(self):
        return self._get_documents("tax_declarations")

    @cachedproperty
    def hours_worked(self):
        return sum(ws["hours"] for ws in self.workspans)

    @cachedproperty
    def hour_rate(self):
        hour_rates = [contract["hour_rate"] for contract in self.contracts]

        if hour_rates and all(hour_rates[0] == hr for hr in hour_rates):
            return hour_rates[0]

        return 0

    @cachedproperty
    def gross_wage(self):
        return

    @cachedproperty
    def tax_amount(self):
        return

    @cachedproperty
    def net_wage(self):
        return

    @cachedproperty
    def available_hours(self):
        return

    def _get_documents(self, document_type):
        return udb.get_user_active_documents(self.database,
                                             self.user_id,
                                             document_type,
                                             self.from_date,
                                             self.to_date)


class ApiAdminMonthTableHandler(BaseHandler):

    def get(self, date):
        month = str_ops.datetime_from_iso_str(date).replace(day=1)
        next_month = month + relativedelta(months=1)

        rows = []

        users = udb.get_users(self.mdb.users)
        for user in users:
            # TODO tady je edge case: smlouva a dokumenty s kontrolují k prvnímu dnu v měsíci
            # a je předpoklad, že platí celý měsíc!
            active_contract = udb.get_user_active_contract(self.mdb.users, user["_id"], month)
            apply_deduction = bool(udb.get_user_active_tax_declaration(self.mdb.users, user["_id"], month))
            apply_deduction_student = bool(udb.get_user_active_study_certificate(self.mdb.users, user["_id"], month))

            hour_rate = active_contract["hour_rate"] if active_contract else 0
            month_workspans = adb.get_user_workspans(self.mdb.users, user["_id"], month, next_month)
            hours_worked = sum(ws["hours"] for ws in month_workspans)
            gross_wage = hours_worked * hour_rate
            tax_amount = calculate_tax(gross_wage,
                                       self.dpp_params["tax_rate"],
                                       self.dpp_params["tax_deduction"] if apply_deduction else 0,
                                       self.dpp_params["tax_deduction_student"] if apply_deduction_student else 0)
            net_wage = gross_wage - tax_amount

            row = {
                "id": user["_id"],
                "name": user.get("name", {}),
                "hours_worked": hours_worked,
                "hour_rate": hour_rate,
                "month_closed": user.get("month_closed", False),  # TODO tak jak nyní month_closed funguje nedává smysl,
                # v db je reprezentován bool hodnotou, ale to znamená že ta bude skákat každý měsíc. Větší smysl dává
                # mít pole months_closed or closed_months a do něj přidávat uzavřené měsíce (třeba data prvních dnů
                # v měsíci v iso tvaru.
                "gross_wage": gross_wage,
                "tax_amount": tax_amount,
                "net_wage": net_wage,
            }
            rows.append(row)

        self.write(bson.json_util.dumps(rows))


class ApiAdminYearTableHandler(BaseHandler):

    def get(self, date):
        year = str_ops.datetime_from_iso_str(date).replace(day=1, month=1)
        next_year = year + relativedelta(years=1)

        rows = []

        users = udb.get_users(self.mdb.users)
        for user in users:
            active_contract = udb.get_user_active_contract(self.mdb.users, user["_id"])
            hour_rate = active_contract["hour_rate"] if active_contract else 0
            year_workspans = adb.get_user_workspans(self.mdb.users, user["_id"], year, next_year)
            hours_worked = sum(ws["hours"] for ws in year_workspans)
            gross_wage = hours_worked * hour_rate
            tax_amount = 0
            net_wage = gross_wage - tax_amount

            row = {
                "id": user["_id"],
                "name": user.get("name", {}),
                "hours_worked": hours_worked,
                "hour_rate": hour_rate,
                "gross_wage": gross_wage,
                "tax_amount": tax_amount,
                "net_wage": net_wage,
            }
            rows.append(row)

        self.write(bson.json_util.dumps(rows))


class UserAttendanceHandler(BaseHandler):

    def get(self, user_id, date_str=None):
        date = str_ops.datetime_from_iso_str(date_str)
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
            "name": str_ops.name_to_str(user_document.get("name", {})),
            "date": str_ops.date_to_iso_str(date),
            "date_pretty": str_ops.date_to_str(date),
            "workspans": day_workspans,
            "vacations": current_and_future_vacations,
            "is_vacation_day": is_vacation_day,
            # "year_days_of_vacation": get_user_year_days_of_vacation(self.mdb.users, user_id, date)
        }
        # template_params.update(compile_user_month_info(self.mdb.users, user_id, datetime.now()))

        self.render("attendance.home.hbs", **template_params)


class ApiCalendarHandler(BaseHandler):

    def post(self, user_id, date):
        month = str_ops.datetime_from_iso_str(date).replace(day=1)
        num_days_in_month = calendar.monthrange(month.year, month.month)[1]

        vacations = adb.get_user_vacations(self.mdb.users,
                                           user_id,
                                           month - relativedelta(months=1),
                                           month + relativedelta(months=2))
        print(vacations)
        vacation_days = []
        for vacation in vacations:
            vacation_length = (vacation["to"] - vacation["from"]).days + 1
            vacation_days += [str_ops.date_to_iso_str(vacation["from"] + timedelta(days=i))
                              for i in range(vacation_length)]

        workspans = adb.get_user_workspans(self.mdb.users,
                                           user_id,
                                           month - relativedelta(months=1),
                                           month + relativedelta(months=2))
        workspan_days_hours = {}
        for workspan in workspans:
            iso_date = str_ops.date_to_iso_str(workspan["from"])

            if iso_date in workspan_days_hours:
                workspan_days_hours[iso_date] += workspan["hours"]
            else:
                workspan_days_hours[iso_date] = workspan["hours"]

        data = {
            "vacations": vacation_days,
            "workdays": workspan_days_hours,
        }

        self.write(bson.json_util.dumps(data))


class ApiMonthInfoHandler(BaseHandler):

    def post(self, user_id, date):
        month = str_ops.datetime_from_iso_str(date).replace(day=1)

        data = compile_user_month_info(self.mdb.users, user_id, month,
                                       self.dpp_params["year_max_hours"],
                                       self.dpp_params["month_max_gross_wage"])
        data["year_days_of_vacation"] = get_user_days_of_vacation_in_year(self.mdb.users, user_id, month)

        self.write(bson.json_util.dumps(data))


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
            raise BadInputError("Na dovolené se nepracuje.")

    def check_workspans_conflicts(self, user_id, workspan):
        today = workspan["from"].replace(hour=0, minute=0, second=0, microsecond=0)
        tomorow = today + relativedelta(days=1)

        todays_workspans = adb.get_user_workspans(self.mdb.users, user_id, today, tomorow)
        workspan_end = workspan["from"] + relativedelta(minutes=int(workspan["hours"] * 60))

        for other_ws in todays_workspans:
            latest_start = max(workspan["from"], other_ws["from"])
            earliest_end = min(workspan_end, other_ws["from"] + relativedelta(minutes=int(other_ws["hours"]) * 60))

            if latest_start < earliest_end:
                raise BadInputError("Časový konflikt s jinou prací.")


class ApiAddVacationHandler(BaseHandler):

    def post(self, user_id):
        # TODO hlídat aby nové dovolené byly v budoucnosti, nelze přidat dovolenou zpětně
        # TODO dovolené by měly jít v půlce přerušit aniž by musely být smazané
        req = self.request.body.decode("utf-8")
        data = bson.json_util.loads(req)

        vacation = {
            "from": str_ops.datetime_from_iso_str(data["from"]),
            "to": str_ops.datetime_from_iso_str(data["to"])
        }

        if vacation["from"] > vacation["to"]:
            raise BadInputError("Dovolená skončila dříve než začala.")

        other_vacations = adb.get_user_vacations(self.mdb.users, user_id, vacation["from"])
        for other_vac in other_vacations:
            latest_start = max(vacation["from"], other_vac["from"])
            earliest_end = min(vacation["to"], other_vac["to"])

            if latest_start <= earliest_end:
                raise BadInputError("Časový konflikt s jinou dovolenou.")

        adb.add_user_vacation(self.mdb.users, user_id, vacation)


class ApiDeleteVacationHandler(BaseHandler):

    def post(self, user_id):
        vacation_id = self.request.body.decode("utf-8")
        adb.delete_user_vacation(self.mdb.users, user_id, vacation_id)


class ApiDeleteWorkspanHandler(BaseHandler):

    def post(self, user_id):
        workspan_id = self.request.body.decode("utf-8")
        adb.delete_user_workspan(self.mdb.users, user_id, workspan_id)
