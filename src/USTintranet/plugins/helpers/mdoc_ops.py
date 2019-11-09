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


def compile_user_month_info(coll: pymongo.collection.Collection, user_id: str, date: datetime):
    result = {}

    start_of_month = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_month = start_of_month + relativedelta(months=1)
    start_of_year = start_of_month.replace(month=1)
    end_of_year = start_of_year + relativedelta(years=1)

    month_workspans = adb.get_user_workspans(coll, user_id, start_of_month, end_of_month)
    year_workspans = adb.get_user_workspans(coll, user_id, start_of_year, end_of_year)
    active_contract = udb.get_user_active_contract(coll, user_id)

    result["month_hours_worked"] = sum([ws["hours"] for ws in month_workspans])
    result["year_hours_worked"] = sum([ws["hours"] for ws in year_workspans])

    # TODO doplnit DPČ a pracovní smlouvu, tahat z databáze
    if active_contract and active_contract["type"] == "dpp":
        result["hour_rate"] = active_contract["hour_rate"]
        result["year_max_hours"] = 300
        result["month_max_hours"] = int(2 * 10000 / active_contract["hour_rate"]) / 2
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