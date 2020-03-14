import os
from datetime import datetime

from bson import ObjectId


def generate_actual_owncloud_path(file_id: ObjectId,
                                  oc_directory: str,
                                  oc_filename: str,
                                  oc_file_extension: str,
                                  version: int,
                                  oc_root=""):
    oc_filename_with_metadata = f"{file_id}_{oc_filename}_v{version}{oc_file_extension}"
    return os.path.join(oc_root, oc_directory, oc_filename_with_metadata)


def get_file_mdoc(database, file_id):
    if not file_id:
        return None

    return database.owncloud.find_one({"_id": file_id})


def get_file_url(database, file_id, version=-1):
    if not file_id:
        return None

    file_mdoc = get_file_mdoc(database, file_id)

    if not file_mdoc["versions"]:
        return ""

    return file_mdoc["versions"][version]["url"]


def get_file_last_version_number(file_mdoc: dict):
    """
    Vrací číslo poslední verze nebo -1 když soubor ještě nemá verzi.
    """
    if not file_mdoc:
        return -1

    return len(file_mdoc["versions"]) - 1


def generate_user_directory_path(user_id: ObjectId, user_name: str, year_date):
    if isinstance(year_date, datetime):
        year_date = str(year_date.year)

    user_dir_name = f"{user_id}_{user_name}"
    return os.path.join("accounting", year_date, "employees", user_dir_name)


def generate_contracts_directory_path(user_id: ObjectId, user_name: str, year_date):
    return os.path.join(generate_user_directory_path(user_id, user_name, year_date), "contracts")


def generate_documents_directory_path(user_id: ObjectId, user_name: str, year_date):
    return os.path.join(generate_user_directory_path(user_id, user_name, year_date), "documents")


def generate_reports_directory_path(month_date: datetime):
    year = str(month_date.year)
    month = str(month_date.month)
    return os.path.join("accounting", year, "reports", month)
