#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from .. import Intranet
from .. import BaseHandler
from bson.json_util import dumps
from bson import ObjectId

from plugins.helpers.warehouse import *
from .packet_helper import *


def get_plugin_handlers():
        #plugin_name = get_plugin_info()["name"]
        plugin_name = 'store'

        return [
             (r'/{}/popover/packet/(.*)/'.format(plugin_name), popover_packet)
        ]



class popover_packet(BaseHandler):
    def get(self, packet):
        print(packet)
        packet_id = bson.ObjectId(packet)

        packet = get_packet(self.mdb, packet_id)
        print(packet)
        self.render('store/popover/packet.hbs', out = packet)