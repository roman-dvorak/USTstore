import cProfile
import json
import pstats
import sys

from mongomock import ObjectId
from socks import HTTP
from tornado.web import StaticFileHandler, HTTPError

from plugins import BaseHandler
from plugins.helpers.db_experiments.user_db import User
from .helpers.api import ApiJSONEncoder
from ...helpers.exceptions import BadInputHTTPError


class VueStaticFileHandler(StaticFileHandler):

    def validate_absolute_path(self, root: str, absolute_path: str):
        try:
            return super().validate_absolute_path(root, absolute_path)
        except HTTPError as e:
            if e.status_code == 404:
                return self.get_absolute_path(root, "index.html")
            else:
                raise e


class ApiCurrentUserHandler(BaseHandler):

    def get(self, *args):
        print(args)
        print(self.current_user)

        data = {
            "_id": str(self.current_user["_id"]),
            "user": self.current_user["user"],
            "param": self.current_user["param"]
        }

        self.write(ApiJSONEncoder().encode(data))


class ApiContractsHandler(BaseHandler):

    def get(self, user_id, contract_id=None):
        self.write("hi")


class ApiUsersHandler(BaseHandler):
    """
    api:

    GET /users - vrací všechny uživatele (potenciálně filtrované)
    POST /users - nový uživatel (odpověď by ho měla vrátit)
    ...

    GET /users/<_id> - vrací konkrétního uživatele
        ?include-fields=field1,field2... - vrať pouze tyto fieldy
         exclude-fields=field1,field2... - vrať vše kromě těchto fieldů - vzájemně výlučné
    """

    # def prepare(self):
    #     super().prepare()
    #
    #     self.pr = cProfile.Profile()
    #     self.pr.enable()
    #
    # def on_finish(self):
    #     self.pr.disable()
    #     ps = pstats.Stats(self.pr, stream=sys.stdout)
    #     ps.sort_stats("tottime")
    #     ps.print_stats()

    def get(self, user_id):
        print("hello")
        if not user_id:
            self.handle_get_users()
        else:
            self.handle_get_specific_user(ObjectId(user_id))

    def handle_get_users(self):
        pass

    def handle_get_specific_user(self, user_id):
        include_fields = self.get_query_argument("include", None)
        if include_fields:
            include_fields = include_fields.split(",")

        exclude_fields = self.get_query_argument("exclude", None)
        if exclude_fields:
            exclude_fields = exclude_fields.split(",")

        print(include_fields)
        print(exclude_fields)

        if include_fields and exclude_fields:
            raise BadInputHTTPError("Nelze zároveň předat argument include-fields a exclude-fields.")

        user = User.from_id(self.mdb, user_id)

        self.write(json.dumps(user.get_json_serializable(included=include_fields, excluded=exclude_fields),
                              cls=ApiJSONEncoder,
                              sort_keys=True,
                              indent=2))
        # self.write("hi<br>new")


class ApiDocumentsHandler(BaseHandler):
    pass