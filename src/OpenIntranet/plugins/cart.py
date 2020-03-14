#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
from . import BaseHandler
import json
import bson.json_util
import urllib
import datetime


def get_plugin_handlers():
        plugin_name = get_plugin_info()["module"]

        return [
             (r'/{}'.format(plugin_name), home),
             (r'/{}/'.format(plugin_name), home),
             (r'/{}/test'.format(plugin_name), test),
             (r'/{}/print/(.*)/'.format(plugin_name), api_print),
             (r'/{}/api/add_to_cart'.format(plugin_name), api_addToCart),
             (r'/{}/api/new_cart'.format(plugin_name), api_new_cart),
             #(r'/%s/print/' %plugin_name, print_layout),
             #(r'/%s/api/add_to_cart/' %plugin_name, api_addToCart)
             #(r'/%s/api/get_cart/' %plugin_name, api_getCart)
             #(r'/%s/api/(.*)/' %plugin_name, api)
        ]

def get_plugin_info():
    return{
        "module": "cart",
        "name": "Nákupí košíky",
        "icon": 'icon_cart.svg'
    }


class home(BaseHandler):
    def get(self, data=None):
        carts = self.mdb.carts.find({}).sort([("_id", -1)] )
        self.render('carts.home.hbs', title = "TITLE", carts = carts, handler_cart = self.cart)


class test(BaseHandler):
    def get(self):
        self.write("Hi")



class api_getCart(BaseHandler):
    def post(self):
        pass

class api_addToCart(BaseHandler):
    def post(self):
        component = self.get_argument('id')
        count = self.get_argument('count')
        method = self.get_argument('method', 'absolute')
        cart = self.cart
        exist = False
        if component:
            component_param = self.getComponentById(component)
            print(component_param)
            ctype = cart.get('type', 'list')
            if not ctype in ['list', 'sell', 'buy', 'bom']:
                ctype = 'list'

            for x in cart.get('cart', []):
                if x['id'] == component:
                    exist = x
                    break

            if method == 'absolute':
                print("Do kosiku pridavam polozku '{}' v počtu '{}' metodou {}".format(component, count, method))

                if exist:
                    self.mdb.carts.update({'_id': bson.ObjectId(cart['_id']),
                                           'cart.id': component},
                                            { '$set': { 'cart.$.count': count } })
                else:
                    row = {'id': component, 'count': count}
                    self.mdb.carts.update({'_id': bson.ObjectId(cart['_id'])},
                            { '$push': {'cart' :row} })

            if ctype == 'sell':
                    self.mdb.carts.update({'_id': bson.ObjectId(cart['_id']), 'cart.id': component},
                                          { '$set': {
                                                'cart.$.price': component_param.get('price_sell', component_param.get('price', 0)),
                                                'cart.$.offset': 0,
                                                'cart.$.offset_type': 'abs'
                                                }
                                          })




            self.write("ok")

class api_new_cart(BaseHandler):
    def post(self):
        name = self.get_argument('name')
        ctype = self.get_argument('type')
        cart = {
            'name': name,
            'autor': self.actual_user['user'],
            'cart': [],
            'status': self.get_argument('status', 0),
            'type': ctype,
            'public': self.get_argument('public', True),
            'created': datetime.datetime.now()
        }
        self.mdb.carts.insert(cart)


class api(object):
    def get(self, data=None):
        self.write("unsupported")

    def post(self, data=None):
        self.finish()

class api_print(BaseHandler):
    def get(self, pid):
        plist = list(self.mdb.carts.find({'_id': bson.ObjectId(pid)}))[0]
        components = []
        for element in plist['cart']:
            components += [element['id']];
        print(plist)
        print(components)

        url = '/store/print/?type=pdf&template=70x42-3_simple'
        url += '&action[]='+'&action[]='.join(components)

        print(url)
        self.redirect(url)
