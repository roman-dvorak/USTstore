#!/usr/bin/python3
# -*- coding: utf-8 -*-
import bson.json_util

from . import BaseHandler
from . import BaseHandlerJson


def make_handlers(plugin_name, plugin_namespace):
    return [
        (r'/{}/api/user/(.*)/save'.format(plugin_name), plugin_namespace.save_user),
        (r'/{}/api/get_users/(.*)/'.format(plugin_name), plugin_namespace.ApiGetUsersHandler),
        (r'/{}/api/get_users'.format(plugin_name), plugin_namespace.ApiGetUsersHandler),
        (r'/{}/api/get_companies/'.format(plugin_name), plugin_namespace.get_compa),
        (r'/{}'.format(plugin_name), plugin_namespace.home),
        (r'/{}/'.format(plugin_name), plugin_namespace.home),
    ]


def plug_info():
    return {
        "module": "users",
        "name": "Uživatelé",
        "icon": 'icon_users.svg',
        "role": ['user-sudo', 'user-access', 'user-read', 'economy-read', 'economy-edit'],
    }


class home(BaseHandler):
    role_module = ['user-sudo', 'user-access', 'user-read', 'economy-read', 'economy-edit']

    def get(self, data=None):
        me = self.actual_user
        my_activity = list(self.mdb.operation_log.find({'user': me['user']}))

        if self.is_authorized(['users-editor', 'sudo-users']):
            users = self.mdb.users.find()
            self.render('users.home-sudo.hbs', title="TITLE", parent=self, users=users, me=me, my_activity=my_activity)
        else:
            self.render('users.home.hbs', title="Nastavení účtu", parent=self, users=me, me=me, my_activity=my_activity)


'''
    Tato trida vytvori senzam uzivatelu jako json dokument a posled na POST pozadavek
    Pokud obsahuje URL UID, poslou se pouze informace o uzivateli.
'''


class ApiGetUsersHandler(BaseHandlerJson):
    """
    Odpověď na GET požadavek. Vytvoří seznam uživatelů jako JSON dokument a pošle je zpět.
    Pokud je v url UID (_id), pošlou se pouze informace o konkrétním uživateli.
    """
    def get(self, uid=None):
        print("getting")
        if not uid:
            self.authorized(['users', 'users-sudo'])
            skip = int(self.get_argument('skip', 0))
            limit = int(self.get_argument('limit', 50))
            order = self.get_argument('order', 'user')
            order_polarity = int(self.get_argument('order_polarity', 1))

            project = {'user': 1, 'name': 1, 'email': 1}

            out = list(self.mdb.users.aggregate([
                {'$match': {'type': 'user'}},
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
            {'$match': {'type': 'company'}},
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
