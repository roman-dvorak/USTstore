#!/usr/bin/python
# -*- coding: utf-8 -*-

# tento soubor ma link ve slozce ./plugins
# original je umisten ve slozce ./handlers

import tornado
import tornado.web
import pymongo
import hashlib, uuid


def make_handlers(module, plugin):
        return []
def plug_info():
    return {
        "module": "__init__",
        "name": "__init__"
    }

def database_init():
    return pymongo.MongoClient('localhost', 27017).USTintranet

class Intranet(tornado.web.RequestHandler):       #tento handler pouzivat jen pro veci, kde je potreba vnitrni autorizace - tzn. jen sprava systemu
    def prepare(self):
        self.xsrf_token
        try:
            self.access
            print( "autorizovany uzivatel", self.access)
            if not 'sudo' in self.access:
                self.access.append('sudo')
                pass
        except AttributeError:
            self.access = ['sudo']
            print( "Prava nejsou nastavena", self.access)

        login = self.get_secure_cookie("login")
        token = self.get_secure_cookie("token")
        print("login, token je:", login, token)
        
        if login:
            login = login.decode()
            token = eval(token)
            self.mdb = database_init()
            self.getCategories()
            print(self.mdb)
            #user_db =  self.mdb.users.find({'login': login})
            user_db =  self.mdb.users.find({"login": str("roman-dvorak")})[0]
            print("ACCESS", type(user_db), user_db, str(login))
            print(user_db['login'])
            self.actual_user = user_db
            self.permissions = user_db['access']

            if not 'remote_token' in self.actual_user:
                rt = haslib.md5(str(uuid.uuid4())).hexdigest()
                #self.mdb.users.update({ "_id": self.actual_user["_id"] }, { "set": { "remote_token": rt } })
                #self.actual_user['remote_token'] = rt
                print (rt)

            print( "prava uzivatele \t", self.permissions)
            print( "potrebna prava  \t", self.access)
            print( "spolecne klice  \t", set(self.access) & set(self.permissions))
            print(type(login), type(user_db['login']))
            print(login, user_db['login'])
            print( "Uzivatel je prihlasen", login)
            if bool(set(self.access) & set(self.permissions)) and str(user_db['login'])==str(login):
                print( "a ma dostatecna opravneni")
                return None
            print(bool(set(self.access) & set(self.permissions)), str(user_db['login'])==str(login))
            print( "Nema dostatecna opravneni")
            self.redirect("/eshop")
            return None
        else:
            print( "uzivatel neni korektne prihlasen")
            self.redirect("/login")
            return None

    def getCategories(self):
        print ("###########################")
        cats = self.mdb.categories.find({})
        counts = {}
        #for p in cat_list:
        for cat in cats:
            print(cat)
            p = cat['path']+cat['_id']
            print(p)
            parts = p.split('/')
            branch = counts
            for part in parts[1:-1]:
               branch = branch.setdefault(part+cat['_id'], {})
            #branch[parts[-1]] = 1 + branch.get(parts[-1], 0)
            branch[parts[-1]] = cat['name']
        return counts



    def get_current_user(self):
        login = self.get_secure_cookie("login")
        token = self.get_secure_cookie("token")
        if not login:
            return None
        else:
            return login


class BaseHandler(tornado.web.RequestHandler):
    def prepare(self):
        
        login = self.get_secure_cookie("login")

        self.mdb = database_init()
        user_db = self.mdb.users.find_one({'login': login})
        
        if login and user_db.get('login', False) == login:
            self.actual_user = user_db
            self.permissions = user_db['access']

            print( "prava uzivatele \t", self.permissions)

            print ("Uzivatel je prihlasen", login)
            self.logged = True
            return None
        else:
            print ("uzivatel neni korektne prihlasen")
            self.logged = False
            return None

    def get_current_user(self):
        login = self.get_secure_cookie("login")
        token = self.get_secure_cookie("token")
        if not login:
            return None
        else:
            return login

class home(BaseHandler):
    def get(self, param=None):
        self.write("Ahoj :) ")
        