#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta

import bson.json_util
import tornado
import tornado.options
from bson import ObjectId
from dateutil.relativedelta import relativedelta
from tornado.web import HTTPError

from plugins import BaseHandler, password_hash
from plugins import BaseHandlerOwnCloud
from plugins.helpers import database_user as udb
from plugins.helpers import str_ops
from plugins.helpers.contract_generation import generate_contract
from plugins.helpers.doc_keys import CONTRACT_DOC_KEYS
from plugins.helpers.emails import generate_validation_token, generate_validation_message, send_email
from plugins.helpers.exceptions import BadInputHTTPError, MissingInfoHTTPError, ForbiddenHTTPError
from plugins.helpers.mdoc_ops import find_type_in_addresses, update_workspans_contract_id
from plugins.helpers.owncloud_utils import get_file_url, generate_contracts_directory_path, \
    generate_documents_directory_path
from plugins.users.backend.helpers.api import ApiJSONEncoder

"""
Role:
základní uživatel nemá speciální roli jelikož všichni jsou základními uživateli
users-accountant - Účetní
users-sudo - Admin
"""

ROLE_SUDO = "users-sudo"
ROLE_ACCOUNTANT = "order-view, order-manager"


class HomeHandler(BaseHandler):
    def get(self):

        self.render("../plugins/order/frontend/orders.overview.hbs")
        self.write("OK :) ... tak ted jeste tu sablonu")
