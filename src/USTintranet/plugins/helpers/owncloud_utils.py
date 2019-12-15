import os


def generate_actual_owncloud_path(file_id: str,
                                  oc_directory: str,
                                  oc_filename: str,
                                  version: int,
                                  oc_root=""):
    filename_without_ext, ext = os.path.splitext(oc_filename)
    oc_filename_with_metadata = f"{file_id}_{filename_without_ext}_v{version}{ext}"
    return os.path.join(oc_root, oc_directory, oc_filename_with_metadata)


def get_file_url(database, file_id, version=-1):
    file_mdoc = database.owncloud.find_one({"_id": file_id})

    index = list(file_mdoc["versions"].keys())[version]
    return file_mdoc["versions"][index]["url"]


def get_file_last_version_index(file_mdoc: dict):
    return list(file_mdoc["versions"].keys())[-1]


def get_file_last_version_number(file_mdoc: dict):
    return int(get_file_last_version_index(file_mdoc))
