#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
#from pyoctopart.octopart import Octopart
import json
import urllib

def make_handlers(module, plugin):
		return [
			 (r'/%s' %module, plugin.hand_bi_home),
			 (r'/%s/' %module, plugin.hand_bi_home),
		]
def plug_info():
	#class base_info(object):
	return {
		"module": "base_info",
		"name": "base_info"
	}


class hand_bi_home(tornado.web.RequestHandler):
	def get(self, data=None):
		self.write("BASE ....")