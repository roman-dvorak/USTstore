from datetime import datetime, timedelta

from .doc_keys import NAME_DOC_KEYS


def name_to_str(name_document: dict):
    """
    Převede dokument name (jak je definovaný v db) na řetězec.
    Je-li name_document prázdný nebo None, vrací prázdný řetězec.
    """
    if not name_document:
        return ""

    name_bits = []
    for key in NAME_DOC_KEYS:
        if key in name_document and name_document[key]:
            name_bits.append(name_document[key])

    return " ".join(name_bits)


def date_to_str(date: datetime):
    """
    Převede datetime objekt na řetězec podle českého standardu zápisu data (den. měsíc. rok).
    Je-li date None, vrací prázdný řetězec.
    """
    if not date:
        return ""

    return f"{date.day}. {date.month}. {date.year}"


def date_to_iso_str(date: datetime):
    """
    Převede datetime objekt na řetězec podle českého standardu zápisu data (den. měsíc. rok).
    Je-li date None, vrací prázdný řetězec.
    """
    if not date:
        return ""

    return date.strftime("%Y-%m-%d")


def date_from_iso_str(date: str):
    """
    Převede řetězec data v iso formátu (YYYY-MM-DD) na datetime objekt.
    Je-li date prázdný řetězec, vrací None.
    """
    if not date:
        return None

    return datetime.strptime(date, "%Y-%m-%d")


def address_to_str(address_document: dict):
    """
    Převede dokument address na řetězec.
    """
    if not address_document:
        return ""

    address = ""
    if "street" in address_document:
        address += address_document["street"]
    if "city" in address_document:
        if address:
            address += " "
        address += address_document["city"]
    if "state" in address_document:
        if address:
            address += ", "
        address += address_document["state"]
    if "zip" in address_document:
        if address:
            address += ", "
        address += address_document["zip"]

    return address


def datetime_from_iso_string_and_time_string(date: str, time: str):
    if not date or not time:
        return None

    hours, minutes = time.split(":")
    delta = timedelta(hours=int(hours), minutes=int(minutes))

    return date_from_iso_str(date) + delta
