import json

from bson import ObjectId
from datetime import datetime

from plugins.helpers.db_experiments.db_wrappers import MdocWrapper


class ApiJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, MdocWrapper):
            print("mdocwrapper", type(o))
            return o.get_json_serializable()
        return json.JSONEncoder.default(self, o)
