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
