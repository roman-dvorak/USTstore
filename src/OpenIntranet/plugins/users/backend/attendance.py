import calendar
import json
from datetime import datetime, timedelta

import bson.json_util
from bson import ObjectId
from dateutil.relativedelta import relativedelta

from plugins import BaseHandler, get_dpp_params, BaseHandlerOwnCloud
from plugins.helpers import database_attendance as adb, report_generation, database_reports as rdb, owncloud_utils
from plugins.helpers import database_user as udb
from plugins.helpers import str_ops
from plugins.helpers.exceptions import BadInputHTTPError, MissingInfoHTTPError, ForbiddenHTTPError
from plugins.helpers.finance import calculate_tax
from plugins.helpers.math_utils import floor_to_half
from plugins.helpers.mdoc_ops import get_user_days_of_vacation_in_year
from plugins.helpers.owncloud_utils import generate_reports_directory_path, get_file_url
from plugins.users.backend.helpers.api import ApiJSONEncoder

ROLE_SUDO = "users-sudo"
ROLE_ACCOUNTANT = "users-accountant"


class HomeHandler(BaseHandler):

    def get(self):
        current_user_id = self.actual_user["_id"]

        if self.is_authorized([ROLE_SUDO, ROLE_ACCOUNTANT]):
            self.render('attendance.home-sudo.hbs')
        else:
            self.redirect(f"/attendance/u/{current_user_id}")


class AttendanceCalculator:

    def __init__(self, database, user_id, date: datetime):
        self.database = database
        self.user_id = user_id
        self.month = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self.year = self.month.replace(month=1)

        self.dpp_params = get_dpp_params(self.database)
        self.year_max_hours = self.dpp_params["year_max_hours"]
        self.month_max_gross_wage = self.dpp_params["month_max_gross_wage"]
        self.tax_rate = self.dpp_params["tax_rate"]
        self.tax_deduction = self.dpp_params["tax_deduction"]
        self.tax_deduction_student = self.dpp_params["tax_deduction_student"]

        self._month_hours_worked = None
        self._month_gross_wage = None
        self._month_tax_amount = None

        self._month_hour_rate = None

        self._year_hours_worked = None
        self._year_gross_wage = None
        self._year_tax_amount = None

    def _calculate_this_month(self):
        hours_worked, gross_wage, tax_amount = self._calculate_given_month(self.month)

        self._month_hours_worked = hours_worked
        self._month_gross_wage = gross_wage
        self._month_tax_amount = tax_amount

    def _calculate_given_month(self, month: datetime):
        print("_calculate_given_month", month)
        if month == self.month and self._month_hours_worked is not None:
            print("tento měsíc je už spočítaný")
            return self._month_hours_worked, self._month_gross_wage, self.month_tax_amount

        next_month = month + relativedelta(months=1)

        workspans = adb.get_user_workspans(self.database, self.user_id, month, next_month)

        has_study_certificate = self._month_has_study_certificate(month)
        has_tax_declaration = self._month_has_tax_declaration(month)

        contract = None

        hours_worked = 0
        for workspan in workspans:
            if workspan["contract"]:
                if not contract:
                    contract = udb.get_user_contract_by_id(self.database, self.user_id, workspan["contract"])

            else:
                print(f"Pro tuto práci neexistuje platná smlouva: {workspan}")
                continue  # TODO vyřešit hlášení do frontendu

            hours_worked += workspan["hours"]

        if not hours_worked or not contract:
            return 0, 0, 0

        gross_wage = contract["hour_rate"] * hours_worked

        tax_amount = calculate_tax(gross_wage, self.tax_rate,
                                   self.tax_deduction if has_tax_declaration else 0,
                                   self.tax_deduction_student if has_study_certificate else 0)

        return hours_worked, gross_wage, tax_amount

    def _calculate_this_year(self):
        hours_worked = 0
        gross_wage = 0
        tax_amount = 0
        for month in range(12):
            start_of_month = datetime(self.year.year, month + 1, 1)
            month_hours_worked, month_gross_wage, month_tax_amount = self._calculate_given_month(start_of_month)

            hours_worked += month_hours_worked
            gross_wage += month_gross_wage
            tax_amount += month_tax_amount

        self._year_hours_worked = hours_worked
        self._year_gross_wage = gross_wage
        self._year_tax_amount = tax_amount

    def _month_has_study_certificate(self, month):
        return bool(udb.get_user_active_documents(self.database, self.user_id, "study_certificate",
                                                  month, month + relativedelta(months=1)))

    def _month_has_tax_declaration(self, month):
        return bool(udb.get_user_active_documents(self.database, self.user_id, "tax_declaration",
                                                  month, month + relativedelta(months=1)))

    @property
    def month_hours_worked(self):
        if self._month_hours_worked is None:
            self._calculate_this_month()

        return self._month_hours_worked

    @property
    def month_gross_wage(self):
        if self._month_gross_wage is None:
            self._calculate_this_month()

        return self._month_gross_wage

    @property
    def month_tax_amount(self):
        if self._month_tax_amount is None:
            self._calculate_this_month()

        return self._month_tax_amount

    @property
    def year_hours_worked(self):
        if self._year_hours_worked is None:
            self._calculate_this_year()

        return self._year_hours_worked

    @property
    def year_gross_wage(self):
        if self._year_gross_wage is None:
            self._calculate_this_year()

        return self._year_gross_wage

    @property
    def year_tax_amount(self):
        if self._year_tax_amount is None:
            self._calculate_this_year()

        return self._year_tax_amount

    @property
    def month_hour_rate(self):
        if self._month_hour_rate is None:
            self._calculate_this_month()

        month_contracts = udb.get_user_active_contracts(self.database, self.user_id, self.month,
                                                        self.month + relativedelta(months=1))
        if month_contracts:
            return month_contracts[0]["hour_rate"]
        else:
            return None

    @property
    def month_net_wage(self):
        return self.month_gross_wage - self.month_tax_amount

    @property
    def year_net_wage(self):
        return self.year_gross_wage - self.year_tax_amount

    @property
    def month_max_hours(self):
        if self.month_hour_rate is None:
            return None
        return floor_to_half(self.month_max_gross_wage / self.month_hour_rate)

    @property
    def month_available_hours(self):
        if self.month_max_hours is None:
            return None
        return self.month_max_hours - self.month_hours_worked

    @property
    def year_available_hours(self):
        return self.year_max_hours - self.year_hours_worked


class ApiAdminMonthTableHandler(BaseHandler):
    role_module = [ROLE_SUDO, ROLE_ACCOUNTANT]

    def get(self, date):
        date = str_ops.datetime_from_iso_str(date)
        rows = []

        users = udb.get_users(self.mdb.users)
        for user in users:
            user_id = user["_id"]
            calculator = AttendanceCalculator(self.mdb, user_id, date)

            row = {
                "id": str(user_id),
                "name": user.get("name", {}),
                "hours_worked": calculator.month_hours_worked,
                "hour_rate": calculator.month_hour_rate,
                "month_closed": adb.is_month_closed(self.mdb, user_id, date),
                "gross_wage": calculator.month_gross_wage,
                "tax_amount": calculator.month_tax_amount,
                "net_wage": calculator.month_net_wage,
            }
            rows.append(row)

        self.write(json.dumps(rows, cls=ApiJSONEncoder))


class ApiAdminYearTableHandler(BaseHandler):
    role_module = [ROLE_SUDO, ROLE_ACCOUNTANT]

    def get(self, date):
        date = str_ops.datetime_from_iso_str(date)

        rows = []

        users = udb.get_users(self.mdb.users)
        for user in users:
            calculator = AttendanceCalculator(self.mdb, user["_id"], date)

            row = {
                "id": str(user["_id"]),
                "name": user.get("name", {}),
                "hours_worked": calculator.year_hours_worked,
                "gross_wage": calculator.year_gross_wage,
                "tax_amount": calculator.year_tax_amount,
                "net_wage": calculator.year_net_wage,
            }
            rows.append(row)

        self.write(json.dumps(rows, cls=ApiJSONEncoder))


class ApiAdminReportsTableHandler(BaseHandler):
    role_module = [ROLE_SUDO, ROLE_ACCOUNTANT]

    def get(self, date):
        print("DATE", date)
        date = str_ops.datetime_from_iso_str(date).replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        print(date)
        
        rows = []

        for month in range(1, 13):
            month_date = date.replace(month=month)

            accountant_report_owncloud_id = rdb.get_report_file_id(self.mdb, month_date, rdb.ACCOUNTANT_REPORT)
            hours_worked_report_owncloud_id = rdb.get_report_file_id(self.mdb, month_date, rdb.HOURS_WORKED_REPORT)

            row = {
                "month": str_ops.date_to_iso_str(month_date),
                "accountant_report": owncloud_utils.get_file_url(self.mdb, accountant_report_owncloud_id),
                "accountant_report_up_to_date": rdb.is_report_up_to_date(self.mdb, month_date, rdb.ACCOUNTANT_REPORT),
                "hours_worked_report": owncloud_utils.get_file_url(self.mdb, hours_worked_report_owncloud_id),
                "hours_worked_report_up_to_date": rdb.is_report_up_to_date(self.mdb, month_date,
                                                                           rdb.HOURS_WORKED_REPORT)
            }

            rows.append(row)

        self.write(json.dumps(rows, cls=ApiJSONEncoder))


class UserAttendancePageHandler(BaseHandler):

    def get(self, user_id, date_str=None):
        user_id = ObjectId(user_id)

        if not self.is_authorized([ROLE_SUDO, ROLE_ACCOUNTANT], specific_users=[user_id]):
            raise ForbiddenHTTPError(operation="zobrazení docházky jiného uživatele")

        date = str_ops.datetime_from_iso_str(date_str)
        if not date:
            date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        user_document = udb.get_user(self.mdb.users, user_id)

        day_workspans = adb.get_user_workspans(self.mdb, user_id, date, date + timedelta(days=1))
        print("day_workspans", day_workspans)
        print("date", date)
        for ws in day_workspans:
            ws["to"] = str_ops.date_to_time_str(ws["from"] + timedelta(minutes=round(ws["hours"] * 60)))
            ws["from"] = str_ops.date_to_time_str(ws["from"])

        current_and_future_vacations = adb.get_user_vacations(self.mdb, user_id, date)
        is_vacation_day = current_and_future_vacations and current_and_future_vacations[0]["from"] <= date

        for vacation in current_and_future_vacations:
            vacation["from"] = str_ops.date_to_str(vacation["from"])
            vacation["to"] = str_ops.date_to_str(vacation["to"])

        # toto je rychlý hack jak rozumně zprovoznit uzavírání měsíců
        # TODO popřemýšlet o tom víc (je potřeba být schopen odkázat v adrese na měsíc, aby se zobrazil v kalendáři)
        this_month_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_date = this_month_date + relativedelta(months=-1)

        last_month_closed = adb.is_month_closed(self.mdb, user_id, last_month_date)
        last_month_has_contract = udb.get_user_active_contracts(self.mdb, user_id, last_month_date, this_month_date)

        template_params = {
            "_id": str(user_id),
            "name": str_ops.name_to_str(user_document.get("name", {})),
            "date": str_ops.date_to_iso_str(date),
            "date_pretty": str_ops.date_to_str(date),
            "workspans": day_workspans,
            "vacations": current_and_future_vacations,
            "is_vacation_day": is_vacation_day,
            # aby to neupozorňovalo na neuzavřenost měsíce kdy uživatel neměl smlouvu
            "last_month_closed": last_month_closed or not last_month_has_contract,
            "last_month_date": str_ops.date_to_iso_str(last_month_date),
        }

        self.render("attendance.home.hbs", **template_params)


class ApiCalendarHandler(BaseHandler):

    def get(self, user_id, date):
        user_id = ObjectId(user_id)

        if not self.is_authorized([ROLE_SUDO, ROLE_ACCOUNTANT], specific_users=[user_id]):
            raise ForbiddenHTTPError(operation="zobrazení kalendáře jiného uživatele")

        # TODO je potřeba v kalendáři mít přístup i k assignmentům
        month = str_ops.datetime_from_iso_str(date).replace(day=1)
        num_days_in_month = calendar.monthrange(month.year, month.month)[1]

        vacations = adb.get_user_vacations(self.mdb,
                                           user_id,
                                           month - relativedelta(months=1),
                                           month + relativedelta(months=2))
        print(vacations)
        vacation_days = []
        for vacation in vacations:
            vacation_length = (vacation["to"] - vacation["from"]).days + 1
            vacation_days += [str_ops.date_to_iso_str(vacation["from"] + timedelta(days=i))
                              for i in range(vacation_length)]

        workspans = adb.get_user_workspans(self.mdb,
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

        self.write(json.dumps(data, cls=ApiJSONEncoder))


class ApiMonthInfoHandler(BaseHandler):

    def get(self, user_id, date):
        user_id = ObjectId(user_id)

        if not self.is_authorized([ROLE_SUDO, ROLE_ACCOUNTANT], specific_users=[user_id]):
            raise ForbiddenHTTPError(operation="zobrazení informací o měsíci jiného uživatele")

        month = str_ops.datetime_from_iso_str(date).replace(day=1)

        calculator = AttendanceCalculator(self.mdb, user_id, month)

        data = {
            "month_hours_worked": calculator.month_hours_worked,
            "year_hours_worked": calculator.year_hours_worked,
            "hour_rate": calculator.month_hour_rate,
            "year_max_hours": calculator.year_max_hours,
            "month_max_hours": calculator.month_max_hours,
            "month_available_hours": calculator.month_available_hours,
            "year_available_hours": calculator.year_available_hours,
            "month_gross_wage": calculator.month_gross_wage,
            "month_tax_amount": calculator.month_tax_amount,
            "month_net_wage": calculator.month_net_wage,
            "year_days_of_vacation": get_user_days_of_vacation_in_year(self.mdb, user_id, month),
            "month_closed": adb.is_month_closed(self.mdb, user_id, month)
        }

        self.write(json.dumps(data, cls=ApiJSONEncoder))


class WorkspanBaseHandler(BaseHandler):

    def prepare(self):
        super().prepare()
        self.reset_cache()

    def set_target_user_id(self, user_id):
        print("-> nastavuji user_id", user_id)
        self.user_id = user_id

    def reset_cache(self):
        print("-> resetuji cache")
        self.added_workspans = []
        self.deleted_workspans = []

    def add_workspan(self, workspan):
        print("-> přidávám workspan", workspan)
        self.ensure_no_vacations_conflicts(workspan)
        self.ensure_no_workspans_conflicts(workspan)

        self.added_workspans.append(workspan)

    def delete_workspan(self, workspan):
        print("-> mažu workspan", workspan)
        self.deleted_workspans.append(workspan)

    def commit_changes(self):
        """
        Pro fungování předpokládá, že všechny workspany přidány v jedné instanci této třídy jsou v jednou měsíci.
        """
        print("-> komituju změny")

        if self.added_workspans:
            self.attendance_calculator = AttendanceCalculator(self.mdb, self.user_id, self.added_workspans[0]["from"])
            sum_hours_added = sum(ws["hours"] for ws in self.added_workspans)
            sum_hours_deleted = sum(ws["hours"] for ws in self.deleted_workspans)
            self.total_hours_added = sum_hours_added - sum_hours_deleted

            self.ensure_month_max_hours_not_reached()
            self.ensure_year_max_hours_not_reached()

        for added_workspan in self.added_workspans:
            adb.add_user_workspan(self.mdb, self.user_id, added_workspan)

        for deleted_workspan in self.deleted_workspans:
            adb.delete_user_workspan(self.mdb, self.user_id, ObjectId(deleted_workspan["_id"]))

        self.reset_cache()

    def ensure_no_vacations_conflicts(self, workspan):
        # z databáze dostaneme dovolené končící dnes nebo později seřazené podle data konce.
        # první dovolená je nejblíž, stačí tedy zkontrolovat, jestli začíná dnes nebo dříve.
        print("-> vacation conflicts")

        today = workspan["from"].replace(hour=0, minute=0, second=0, microsecond=0)
        vacations = adb.get_user_vacations(self.mdb, self.user_id, today)
        if vacations and vacations[0]["from"] <= workspan["from"]:
            raise BadInputHTTPError("Zadaná práce zasahuje do dovolené.")

    def ensure_no_workspans_conflicts(self, workspan):
        """
        K fungování předpokládá, že v jedné instanci této třídy je přidán jen jeden workspan za den.
        Předpoklad je splněn při přidávání po jednom (v ApiAddWorkspanHandler) a přidávání celého měsíce
        (v ApiEditMonthWorkspansHandler).
        """
        print("-> workspans conflicts")

        today = workspan["from"].replace(hour=0, minute=0, second=0, microsecond=0)
        tomorow = today + relativedelta(days=1)

        todays_workspans = adb.get_user_workspans(self.mdb, self.user_id, today, tomorow)
        workspan_end = workspan["from"] + relativedelta(minutes=int(workspan["hours"] * 60))

        hours_in_day = workspan["hours"]

        for other_ws in todays_workspans:
            if other_ws["_id"] in (ws["_id"] for ws in self.deleted_workspans):
                continue

            latest_start = max(workspan["from"], other_ws["from"])
            earliest_end = min(workspan_end, other_ws["from"] + relativedelta(minutes=int(other_ws["hours"]) * 60))

            if latest_start < earliest_end:
                raise BadInputHTTPError("V zadané době je již jiná práce.")

            hours_in_day += other_ws["hours"]

        if hours_in_day > 12:
            raise BadInputHTTPError("V jednom dni lze pracovat nejvýše 12 hodin.")

    def ensure_month_max_hours_not_reached(self):
        print("-> month max hours")

        month_hours = self.attendance_calculator.month_hours_worked + self.total_hours_added
        if month_hours > self.attendance_calculator.month_max_hours:
            raise BadInputHTTPError("Zadané odpracované hodiny převyšují měsíční limit povolených hodin.")

    def ensure_year_max_hours_not_reached(self):
        print("-> year max hours")
        year_hours = self.attendance_calculator.year_hours_worked + self.total_hours_added

        if year_hours > self.attendance_calculator.year_max_hours:
            raise BadInputHTTPError("Zadané odpracované hodiny převyšují roční limit povolených hodin.")


# TODO validovat vstup
class ApiAddWorkspanHandler(WorkspanBaseHandler):

    def post(self, user_id):
        user_id = ObjectId(user_id)

        if not self.is_authorized([ROLE_SUDO, ROLE_ACCOUNTANT], specific_users=[user_id]):
            raise ForbiddenHTTPError(operation="přidání docházky jiného uživatele")

        req = self.request.body.decode("utf-8")
        form_data = bson.json_util.loads(req)

        if not form_data["hours"]:
            raise BadInputHTTPError("Zadejte počet hodin.")

        today = str_ops.datetime_from_iso_str(form_data["date"])

        workspan = {}
        workspan["from"] = str_ops.datetime_from_iso_string_and_time_string(form_data["date"], form_data["from"])
        workspan["hours"] = float(form_data["hours"])
        workspan["notes"] = form_data["notes"]

        contract_mdoc = udb.get_user_active_contract(self.mdb.users, user_id, today)
        workspan["contract"] = contract_mdoc["_id"] if contract_mdoc else None

        self.set_target_user_id(user_id)
        self.add_workspan(workspan)
        self.commit_changes()


# TODO validovat vstup
class ApiEditMonthWorkspansHandler(WorkspanBaseHandler):

    def post(self, user_id):
        user_id = ObjectId(user_id)

        if not self.is_authorized([ROLE_SUDO, ROLE_ACCOUNTANT], specific_users=[user_id]):
            raise ForbiddenHTTPError(operation="editace docházky jiného uživatele")

        self.set_target_user_id(user_id)

        req = self.request.body.decode("utf-8")
        form_data = bson.json_util.loads(req)

        for day_dict in form_data:
            today = str_ops.datetime_from_iso_str(day_dict["date"])
            tomorow = today + relativedelta(days=1)

            workspan = {}
            workspan["from"] = today
            workspan["hours"] = float(day_dict["hours"])
            workspan["notes"] = day_dict["notes"]

            contract_mdoc = udb.get_user_active_contract(self.mdb.users, user_id, today)
            workspan["contract"] = contract_mdoc["_id"] if contract_mdoc else None

            todays_workspans = adb.get_user_workspans(self.mdb, user_id, today, tomorow)

            for today_workspan in todays_workspans:
                self.delete_workspan(today_workspan)

            if workspan["hours"] > 0:
                self.add_workspan(workspan)

        self.commit_changes()


# TODO validovat vstup
class ApiAddVacationHandler(BaseHandler):

    def post(self, user_id):
        user_id = ObjectId(user_id)

        if not self.is_authorized([ROLE_SUDO], specific_users=[user_id]):
            raise ForbiddenHTTPError(operation="přidání dovolené jinému uživateli")

        # TODO hlídat aby nové dovolené byly v budoucnosti, nelze přidat dovolenou zpětně
        req = self.request.body.decode("utf-8")
        data = bson.json_util.loads(req)

        vacation = {
            "from": str_ops.datetime_from_iso_str(data["from"]),
            "to": str_ops.datetime_from_iso_str(data["to"])
        }

        if vacation["from"] > vacation["to"]:
            raise BadInputHTTPError("Dovolená skončila dříve než začala.")

        other_vacations = adb.get_user_vacations(self.mdb, user_id, vacation["from"])
        for other_vac in other_vacations:
            latest_start = max(vacation["from"], other_vac["from"])
            earliest_end = min(vacation["to"], other_vac["to"])

            if latest_start <= earliest_end:
                raise BadInputHTTPError("Časový konflikt s jinou dovolenou.")

        adb.add_user_vacation(self.mdb, user_id, vacation)


# TODO validovat vstup
class ApiInterruptVacationHandler(BaseHandler):

    def post(self, user_id):
        user_id = ObjectId(user_id)

        if not self.is_authorized([ROLE_SUDO], specific_users=[user_id]):
            raise ForbiddenHTTPError(operation="přerušení dovolené jiného uživatele")

        req = self.request.body.decode("utf-8")
        data = json.loads(req)
        vacation_id = ObjectId(data["_id"])

        interruption_date = str_ops.datetime_from_iso_str(data["date"])
        vacation_mdoc = adb.get_user_vacation_by_id(self.mdb, user_id, vacation_id)

        if not (vacation_mdoc["from"] <= interruption_date <= vacation_mdoc["to"]):
            raise BadInputHTTPError("Datum přerušení musí být mezi začátkem a koncem dovolené!")

        adb.interrupt_user_vacation(self.mdb, user_id, vacation_id, interruption_date)


class ApiDeleteWorkspanHandler(BaseHandler):

    def post(self, user_id):
        user_id = ObjectId(user_id)

        if not self.is_authorized([ROLE_SUDO, ROLE_ACCOUNTANT], specific_users=[user_id]):
            raise ForbiddenHTTPError(operation="odstranění docházky jiného uživatele")

        workspan_id = ObjectId(self.request.body.decode("utf-8"))
        adb.delete_user_workspan(self.mdb, user_id, workspan_id)


# TODO validovat vstup
class ApiCloseMonthHandler(BaseHandler):

    def post(self, user_id):
        user_id = ObjectId(user_id)

        if not self.is_authorized([ROLE_SUDO, ROLE_ACCOUNTANT], specific_users=[user_id]):
            raise ForbiddenHTTPError(operation="uzavření měsíce jiného uživatele")

        month_date_iso = self.request.body.decode("utf-8")
        month_date = str_ops.datetime_from_iso_str(month_date_iso)

        workspans = adb.get_user_workspans(self.mdb, user_id, month_date, month_date + relativedelta(months=1))
        for workspan in workspans:
            if not workspan["contract"]:
                raise MissingInfoHTTPError(f"Práce ve dni {str_ops.date_to_str(workspan['from'])} nemá "
                                           f"odpovídající smlouvu.")

        adb.close_month(self.mdb, user_id, month_date)


# TODO validovat vstup
class ApiReopenMonthHandler(BaseHandler):
    role_module = [ROLE_SUDO, ROLE_ACCOUNTANT]

    def post(self, user_id):
        user_id = ObjectId(user_id)

        month_date_iso = self.request.body.decode("utf-8")
        month_date = str_ops.datetime_from_iso_str(month_date_iso)

        adb.reopen_month(self.mdb, user_id, month_date)
        rdb.set_report_out_of_date(self.mdb, month_date, rdb.ACCOUNTANT_REPORT)
        rdb.set_report_out_of_date(self.mdb, month_date, rdb.HOURS_WORKED_REPORT)


# TODO validovat vstup
class ApiGenerateAccountantReportHandler(BaseHandlerOwnCloud):
    role_module = [ROLE_SUDO, ROLE_ACCOUNTANT]

    async def post(self):
        month_date_iso = self.request.body.decode("utf-8")
        month_date = str_ops.datetime_from_iso_str(month_date_iso)

        existing_report_file_id = rdb.get_report_file_id(self.mdb, month_date, rdb.ACCOUNTANT_REPORT)
        existing_report_mdoc = owncloud_utils.get_file_mdoc(self.mdb, existing_report_file_id)
        existing_report_version = owncloud_utils.get_file_last_version_number(existing_report_mdoc)

        report = report_generation.AccountantReport(self.company_info["name"], month_date, existing_report_version + 1)

        users = udb.get_users(self.mdb.users)

        for user_mdoc in users:
            user_id = user_mdoc["_id"]
            ac = AttendanceCalculator(self.mdb, user_id, month_date)

            if not ac.month_hours_worked:
                continue

            if not adb.is_month_closed(self.mdb, user_id, month_date):
                raise MissingInfoHTTPError(f"{str_ops.name_to_str(user_mdoc.get('name', ''))} ({user_mdoc['user']})"
                                           f"nemá uzavřený měsíc.")

            report.add_row(str_ops.name_to_str(user_mdoc["name"]),
                           ac.month_hours_worked,
                           ac.month_hour_rate,
                           ac.month_gross_wage,
                           ac.month_net_wage,
                           ac.month_tax_amount)

        report.add_sums()
        file_path = report.save()

        if existing_report_file_id:
            await self.update_owncloud_file(existing_report_file_id, file_path)
            rdb.set_report_up_to_date(self.mdb, month_date, rdb.ACCOUNTANT_REPORT)
        else:
            owncloud_directory = generate_reports_directory_path(month_date)

            company_name_no_spaces = self.company_info["name"].replace(" ", "_")
            owncloud_name = f"accountant_report_{company_name_no_spaces}_{month_date.month}-{month_date.year}"
            owncloud_id = await self.upload_to_owncloud(owncloud_directory, owncloud_name, file_path)

            rdb.save_report_file_id(self.mdb, month_date, owncloud_id, rdb.ACCOUNTANT_REPORT)


# TODO validovat vstup
class ApiGenerateHoursWorkedReportHandler(BaseHandlerOwnCloud):
    role_module = [ROLE_SUDO, ROLE_ACCOUNTANT]

    async def post(self):
        month_date_iso = self.request.body.decode("utf-8")
        month_date = str_ops.datetime_from_iso_str(month_date_iso)

        users = udb.get_users(self.mdb.users)

        existing_report_file_id = rdb.get_report_file_id(self.mdb, month_date, rdb.HOURS_WORKED_REPORT)
        existing_report_mdoc = owncloud_utils.get_file_mdoc(self.mdb, existing_report_file_id)
        existing_report_version = owncloud_utils.get_file_last_version_number(existing_report_mdoc)

        report = report_generation.HoursWorkedReport(self.company_info["name"], month_date, existing_report_version + 1)

        for user_mdoc in users:
            self.make_user_page(report, user_mdoc, month_date)

        file_path = report.save()

        if existing_report_file_id:
            await self.update_owncloud_file(existing_report_file_id, file_path)
            rdb.set_report_up_to_date(self.mdb, month_date, rdb.HOURS_WORKED_REPORT)
        else:
            owncloud_directory = generate_reports_directory_path(month_date)

            company_name_no_spaces = self.company_info["name"].replace(" ", "_")
            owncloud_name = f"hours_worked_report_{company_name_no_spaces}_{month_date.month}-{month_date.year}"
            owncloud_id = await self.upload_to_owncloud(owncloud_directory, owncloud_name, file_path)

            rdb.save_report_file_id(self.mdb, month_date, owncloud_id, rdb.HOURS_WORKED_REPORT)

    def make_user_page(self, report, user_mdoc, month_date):

        user_id = user_mdoc["_id"]

        workspans = adb.get_user_workspans(self.mdb, user_id, month_date, month_date + relativedelta(months=1))

        if not workspans:
            return

        if not adb.is_month_closed(self.mdb, user_id, month_date):
            raise MissingInfoHTTPError(f"{str_ops.name_to_str(user_mdoc.get('name'))} ({user_mdoc['user']}) "
                                       f"nemá uzavřený měsíc.")

        report.init_page(str_ops.name_to_str(user_mdoc["name"]))

        hours_in_day = {}
        for workspan in workspans:
            date = workspan["from"].replace(hour=0, minute=0)

            if date in hours_in_day:
                hours_in_day[date] += workspan["hours"]
            else:
                hours_in_day[date] = workspan["hours"]

        for date, hours in hours_in_day.items():
            report.add_row(date, hours)

        report.add_sums_and_end_page()
