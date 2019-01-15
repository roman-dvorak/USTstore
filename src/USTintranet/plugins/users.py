#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
from . import BaseHandler
from . import BaseHandlerJson
from . import perm_validator
import json
import bson.json_util
import urllib
import datetime


def make_handlers(module, plugin):
        return [ # users
             (r'/{}/api/user/(.*)/save'.format(module), plugin.save_user),
             (r'/{}/api/get_users/(.*)/'.format(module), plugin.get_users),
             (r'/{}/api/get_users'.format(module), plugin.get_users),
             (r'/{}/api/get_comps/'.format(module), plugin.get_compa),
             (r'/{}'.format(module), plugin.home),
             (r'/{}/'.format(module), plugin.home),
             #(r'/%s/print/' %module, plugin.print_layout),
             #(r'/%s/api/(.*)/' %module, plugin.api)
        ]

def plug_info():
    return{
        "module": "users",
        "name": "Adresář",
        "icon": 'icon_users.svg'
    }

#@perm_validator(permissions=['sudo'])
class home(BaseHandler):
    def get(self, data=None):
        self.authorized(['users', 'users-sudo'])
        me = self.actual_user
        my_activity = list(self.mdb.operation_log.find({'user': me['user']}))
        if self.is_authorized(['users-editor', 'sudo-users']):
            users = self.mdb.users.find()
            self.render('users.home-sudo.hbs', title = "TITLE", parent = self, users = users, me=me, my_activity=my_activity)
        else:
            self.render('users.home.hbs', title = "Nastavení účtu", parent = self, users = me, me = me, my_activity = my_activity)


'''
    Tato trida vytvori senzam uzivatelu jako json dokument a posled na POST pozadavek
    Pokud obsahuje URL UID, poslou se pouze informace o uzivateli.
'''
class get_users(BaseHandlerJson):
    def post(self, uid = None):
        if not uid:
            self.authorized(['users', 'users-sudo'])
            skip = int(self.get_argument('skip', 0))
            limit = int(self.get_argument('limit', 50))
            order = self.get_argument('order', 'user')
            order_polarity = int(self.get_argument('order_polarity', 1))

            project = {'user': 1, 'name': 1, 'email': 1}

            out = list(self.mdb.users.aggregate([
                    {'$match': {'type':'user'}},
                    {'$sort': {order: order_polarity}},
                    {'$skip': skip},
                    {'$limit': limit},
                    {'$project': project}
                ]))
            for u in out:
                u['id'] = str(u['_id'])
                u['pass'] = None

        else:
            self.authorized(['users', 'users-sudo'])
            out = self.mdb.users.find_one({'_id': bson.ObjectId(uid)})
            out['id'] = str(out['_id'])
            out['pass'] = None
            out['role_text'] = ','.join(out['role'])

        out = bson.json_util.dumps(out)
        self.write(out)

'''
    Tato trida navrati ve formatu json, ktere seznamu firem...
'''
class get_compa(BaseHandlerJson):
    def post(self):
        skip = int(self.get_argument('skip', 0))
        limit = int(self.get_argument('limit', 50))

        out = list(self.mdb.users.aggregate([
                {'$match': {'type':'company'}},
                {'$skip': skip},
                {'$limit': limit}
            ]))
        out = bson.json_util.dumps(out)
        self.write(out)


class save_user(BaseHandler):
    def post(self, uid):
        self.authorized(['users-sudo'])
        print(uid)
        data = {
            'user': self.get_argument('user'),
            'name': self.get_argument('name'),
            'email': self.get_argument('email'),
            'role': self.get_argument('role_text').strip().split(','),
        }
        self.mdb.users.update({'_id': bson.ObjectId(uid)}, {"$set": data})
        self.write(uid)