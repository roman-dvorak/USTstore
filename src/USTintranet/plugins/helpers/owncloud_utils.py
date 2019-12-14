import os

from bson import ObjectId


def generate_actual_owncloud_path(file_id, oc_directory, oc_filename, version):
    oc_filename_with_metadata = f"{file_id}_{oc_filename}_v{version}"
    return os.path.join(oc_directory, oc_filename_with_metadata)


def get_(database, file_id, version=-1):
    database.owncloud.find_one({"_id": ObjectId(file_id)},)