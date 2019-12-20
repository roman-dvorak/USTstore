from datetime import datetime

import pymongo
from dateutil.relativedelta import relativedelta
from plugins.helpers import database_attendance as adb
from plugins.helpers import database_user as udb


def find_type_in_addresses(addresses: list, addr_type: str):
    """
    Najde první adresu s daným typem v listu adres.
    Adresy bez explicitního typu jsou chápány jako typ "residence"

    """
    return next((a for a in addresses if a.get("type", "residence") == addr_type), None)


def compile_user_month_info(database,
                            user_id: str,
                            date: datetime,
                            year_max_hours,  # TODO tohle je hack, vyřešit přeuspořádáním BaseHandleru
                            month_max_gross_wage):
    result = {}

    start_of_month = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_month = start_of_month + relativedelta(months=1)
    start_of_year = start_of_month.replace(month=1)
    end_of_year = start_of_year + relativedelta(years=1)

    month_workspans = adb.get_user_workspans(database, user_id, start_of_month, end_of_month)
    year_workspans = adb.get_user_workspans(database, user_id, start_of_year, end_of_year)
    active_contract = udb.get_user_active_contract(database.users, user_id)

    result["month_hours_worked"] = sum(ws["hours"] for ws in month_workspans)
    result["year_hours_worked"] = sum(ws["hours"] for ws in year_workspans)

    # TODO doplnit DPČ a pracovní smlouvu
    if active_contract and active_contract["type"] == "dpp":
        result["hour_rate"] = active_contract["hour_rate"]
        result["year_max_hours"] = year_max_hours
        result["month_max_hours"] = int(2 * month_max_gross_wage / active_contract["hour_rate"]) / 2
        result["month_available_hours"] = result["month_max_hours"] - result["month_hours_worked"]
        result["year_available_hours"] = result["year_max_hours"] - result["year_hours_worked"]
        result["month_money_made"] = result["hour_rate"] * result["month_hours_worked"]

        result["month_money_made"] = f"{result['month_money_made']:0.2f}"
        result["hour_rate"] = f"{result['hour_rate']:0.2f}"
    else:
        for key in ["hour_rate", "year_max_hours", "month_max_hours", "month_available_hours",
                    "year_available_hours", "month_money_made"]:
            result[key] = None

    return result


def get_user_days_of_vacation_in_year(database, user_id: str, date: datetime):
    start_of_year = date.replace(day=1, month=1)
    end_of_year = start_of_year + relativedelta(years=1) - relativedelta(days=1)
    vacations = adb.get_user_vacations(database, user_id, start_of_year)

    days = 0
    for vacation in vacations:
        vac_from = max(vacation["from"], start_of_year)
        vac_to = min(vacation["to"], end_of_year) + relativedelta(days=1)  # protože se počítá i poslední den

        days += (vac_to - vac_from).days

    return days
