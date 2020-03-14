#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
from . import BaseHandler
#from pyoctopart.octopart import Octopart
import json
import bson.json_util
import urllib
from fpdf import FPDF
import barcode
import code128
import codecs
import datetime

import json
import urllib
import urllib.request
import urllib.parse

import collections, urllib, base64, hmac, hashlib, json


def get_plugin_handlers():
        plugin_name = get_plugin_info()["module"]

        return [
             #(r'/%s' %plugin_name, hand_bi_home),
             (r'/%s/tme/' %plugin_name, tme),
             (r'/%s/octopart/' %plugin_name, octopart),
             #(r'/%s/print/' %plugin_name, print_layout),
             #(r'/%s/api/(.*)/' %plugin_name, api)
        ]

def get_plugin_info():
    return{
        "module": "external_database",
        "name": "external_database"
    }


def api_call(action, params, token, app_secret, show_header=False):
    api_url = 'https://api.tme.eu/' + action + '.json';
    params['Token'] = token;

    params = collections.OrderedDict(sorted(params.items()));

    encoded_params = urllib.parse.urlencode(params, '').encode("utf-8")
    signature_base = 'POST' + '&' + urllib.parse.quote(api_url, '') + '&' + urllib.parse.quote(encoded_params, '')
    signature_base = signature_base.encode('utf-8')

    api_signature = base64.encodestring( hmac.new(app_secret, signature_base, hashlib.sha1).digest() ).rstrip();
    params['ApiSignature'] = api_signature;

    opts = {
        'http': {
            'method' : 'POST',
            'header' : 'Content-type: application/x-www-form-urlencoded',
            'content' : urllib.parse.urlencode(params)
        }
    };

    http_header = {
        "Content-type": "application/x-www-form-urlencoded",
    };
    
    req = urllib.request.Request(api_url, urllib.parse.urlencode(params).encode('utf-8'), http_header);

    # submit your request
    try:
        res = urllib.request.urlopen(req)
        html = res.read()
    except urllib.error.URLError as e:
        print(e.code)
        print("Error")
        html = e.read()

    return html;





class tme(BaseHandler):
    def get(self, data=None):
        print("TME")

        token = b'963ac3230b4d77de3df46444a154c0d1052eb5b17a74159503'
        app_secret = b'5fcc038203350d8e60ef'

        params = {
            #'SearchPlain' : self.get_argument('component', 'NE555'),
            #'Phrase' : self.get_argument('component', 'NE555'),
            #'SymbolList' : [self.get_argument('sku', '74HC1G14GW')],
            'SymbolList[]' : '74HC1G14GW',
            'Country': 'CZ',
            'Language': 'CZ',
        }

        response = api_call('Products/GetParameters', params, token, app_secret, True).decode()
        #response = api_call('Utils/Ping', {}, token, app_secret, True)
        #response = api_call('Auth/GetNonce', {}, token, app_secret, True)
        #response = api_call(self.get_argument('operation', 'Products/SearchParameters'), params, token, app_secret, True).decode('utf-8')
        #response = json.loads(response);
        print(response);

        self.write(json.loads(response))


        #self.render("tme.home.hbs", title="UST intranet", parent=self)

    def post(self):
        operation = self.get_argument('operation', None)

        token = b'963ac3230b4d77de3df46444a154c0d1052eb5b17a74159503'
        app_secret = b'5fcc038203350d8e60ef'

        params = {
            'SearchPlain' : self.get_argument('coponent'),
            'Country': 'CZ',
            'Currency': 'CZK',
            'Language': 'CZ',
        }

        response = api_call(operation, params, token, app_secret, True).decode('utf-8')
        print(response);


        self.write(json.loads(response))


'''
nonce: D0CCA76A25
odpoved: 6820A40C41
token: 963ac3230b4d77de3df46444a154c0d1052eb5b17a74159503
'''



class octopart(BaseHandler):
    def get(self):


        url = "http://octopart.com/api/v3/parts/search"
        url += "?apikey=a400f668" 

        args = [
           ('q', self.get_argument('sku', '74HC1G14GW')),
           ('start', 0),
           ('limit', 10),
           ('include[]','descriptions'),
           ('include[]', 'specs')
           ]

        url += '&' + urllib.parse.urlencode(args)

        print(url)
        f = urllib.request.urlopen(url)
        search_response = f.read()
        print(search_response)

        self.write(json.loads(search_response))