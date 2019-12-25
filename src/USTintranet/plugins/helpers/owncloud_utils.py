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


def get_file_url(database, file_id, version=-1):
    file_mdoc = database.owncloud.find_one({"_id": file_id})

    index = list(file_mdoc["versions"].keys())[version]
    return file_mdoc["versions"][index]["url"]


def get_file_last_version_index(file_mdoc: dict):
    return list(file_mdoc["versions"].keys())[-1]


def get_file_last_version_number(file_mdoc: dict):
    return int(get_file_last_version_index(file_mdoc))


def generate_user_directory_path(user_id: ObjectId, user_name: str, year_date):
    if isinstance(year_date, datetime):
        year_date = str(year_date.year)

    user_dir_name = f"{user_id}_{user_name}"
    return os.path.join("accounting", year_date, "employees", user_dir_name)


def generate_contracts_directory_path(user_id: ObjectId, user_name: str, year_date):
    return os.path.join(generate_user_directory_path(user_id, user_name, year_date), "contracts")


def generate_documents_directory_path(user_id: ObjectId, user_name: str, year_date):
    return os.path.join(generate_user_directory_path(user_id, user_name, year_date), "documents")
