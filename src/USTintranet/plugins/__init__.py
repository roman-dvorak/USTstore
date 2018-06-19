#!/usr/bin/python
# -*- coding: utf-8 -*-

# tento soubor ma link ve slozce ./plugins
# original je umisten ve slozce ./handlers

import tornado
import tornado.web
import pymongo
import hashlib, uuid
import functools
import bson
import datetime


def make_handlers(module, plugin):
        return [
            (r'/login', plugin.loginHandler),
            (r'/logout', plugin.logoutHandler),
            (r'/registration', plugin.regHandler)]
            
def plug_info():
    return {
        "module": "__init__",
        "name": "__init__"
    }

def parametrized(dec):
    def layer(*args, **kwargs):
        def repl(f):
            return dec(f, *args, **kwargs)
        return repl
    return layer

'''
@parametrized
def perm_validator(fn, permissions = [], sudo=True):
    print("Validace opravneni.....")
    print(permissions, sudo, fn.__dict__)
    print(fn)

    return fn
'''

@parametrized
def perm_validator(method, permissions = [], sudo = True):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        print(kwargs)
        return method

    return wrapper


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

        login = self.get_secure_cookie("user")
        token = self.get_secure_cookie("token")
        print("login, token je:", login, token)

        if login:
            login = login.decode()
            token = eval(token)
            self.mdb = database_init()
            self.getCategories()
            print(self.mdb)
            #user_db =  self.mdb.users.find({'login': login})
            user_db =  self.mdb.users.find({"user": str("roman-dvorak")})[0]
            print("ACCESS", type(user_db), user_db, str(login))
            print(user_db['user'])
            self.actual_user = user_db
            self.role = user_db['role']

            if not 'remote_token' in self.actual_user:
                rt = haslib.md5(str(uuid.uuid4())).hexdigest()
                #self.mdb.users.update({ "_id": self.actual_user["_id"] }, { "set": { "remote_token": rt } })
                #self.actual_user['remote_token'] = rt
                print (rt)

            print( "prava uzivatele \t", self.role)
            print( "potrebna prava  \t", self.access)
            print( "spolecne klice  \t", set(self.access) & set(self.role))
            print(type(login), type(user_db['user']))
            print(login, user_db['user'])
            print( "Uzivatel je prihlasen", login)
            if bool(set(self.access) & set(self.role)) and str(user_db['user'])==str(login):
                print( "a ma dostatecna opravneni")
                return None
            print(bool(set(self.access) & set(self.role)), str(user_db['user'])==str(login))
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
        login = self.get_secure_cookie("user")
        if login:
            login = str(login, encoding="utf-8")

        self.mdb = database_init()
        user_db = self.mdb.users.find_one({'user': login})

        if login and user_db.get('user', False) == login:
            self.actual_user = user_db
            self.role = set(user_db['role'])
            cart = self.get_cookie('cart', None)
            print("Nakupni kosik", bson.ObjectId(cart))
            if cart:
                self.cart = list(self.mdb.carts.find({'_id': bson.ObjectId(cart)}))[0]
            else:
                self.cart = None
            print(self.cart)

            print("prava uzivatele \t", self.role)
            print ("Uzivatel je prihlasen", login)

            self.logged = login
            return None
        else:
            print ("uzivatel neni korektne prihlasen")
            self.logged = False
            return None


    def get_current_user(self):
        login = self.get_secure_cookie("user", None)
        if not login:
            return None
        login = str(login, encoding="utf-8")
        print(login)
        user_db = self.mdb.users.find_one({'user': login})

        if not user_db:
            print("NIC", user_db)
            return None
        return user_db

    def authorized(self, required = [], sudo = True):
        print("AUTHORIZED.....")
        if self.get_current_user():
            if sudo:
                required = required + ['sudo']
            req = set(required)
            intersection = list(self.role&req)
            if  bool(intersection):
                return intersection
            else:
                print("Go To ERRRRRR")
                self.redirect('/?err=authorized')
        else:
            self.redirect('/login')

    def is_authorized(self, required = [], sudo = True):
        print("AUTHORIZATION.....")
        if self.get_current_user():
            if sudo:
                required = required + ['sudo']
            req = set(required)
            intersection = list(self.role&req)
            if  bool(intersection):
                return intersection
            else:
                return False
        else:
            self.redirect('/login')

    def getComponentById(self, id):
        return (self.mdb.stock.find_one({'_id': id}))

    def LogActivity(self, module = None, operation = None, data = {}, user = None):
        if not user: user = self.logged
        if not module: module = self.__class__.__name__
        print("Activity logger:")
        print(">> activity from {} in {} module".format(user, module))
        print(">> operation: {}".format(operation))

        self.mdb.operation_log.insert({'user': user, 'module': module, 'operation': operation, 'data': data})

class BaseHandlerJson(BaseHandler):
    def prepare(self):
        self.set_header('Content-Type', 'application/json')
        super(BaseHandlerJson, self).prepare()


class home(BaseHandler):
    def get(self, param=None):
        self.write("Ahoj :) ")


class loginHandler(BaseHandler):
    def get(self):
        self.render('_login.hbs', msg='')

    def post(self):
        user = self.get_argument('user')
        passw= self.get_argument('pass')
        
        username = self.mdb.users.find_one({"$or": [{"user": user},{'email': user}]})['user']
        hash = hashlib.sha384((passw+username).encode('utf-8')).hexdigest()
        print("login", username, hash)
        userdb = self.mdb.users.find_one({"$or": [{"user": user},{'email': user}], 'pass': hash})
        if userdb:
            self.set_secure_cookie('user', userdb['user'])
            self.redirect('/')
        else:
            self.redirect('/login')

class logoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie('user')
        self.redirect('/')

    def post(self):
        self.clear_cookie('user')

class regHandler(BaseHandler):
    def get(self):
        self.render('_registration.hbs', msg = None)

    def post(self):
        user = self.get_argument('user')
        email = self.get_argument('email')
        psw = self.get_argument('pass')
        pswc = self.get_argument('pass_check')
        agree = self.get_argument('agree')

        if agree != 'agree':
            self.render('_registration.hbs', msg = 'Musíte souhlasit s ...')

        if psw != pswc:
            self.render('_registration.hbs', msg = 'Hesla se neshodují')
        hash = hashlib.sha384((psw+user).encode('utf-8')).hexdigest()

        data = list(self.mdb.users.find({'$or': [{'user':user}, {'email':email}] }))
        print(data)
        print(len(data))

        if len(data) == 0:
            self.mdb.users.insert({
                    'user': user,
                    'pass': hash,
                    'name': user,
                    'email': email,
                    'email_validate': False,
                    'created': datetime.datetime.now(),
                    'type': 'user',
                    'role': [],
                })
        else:
            self.render('_registration.hbs', msg = 'Toto <b>uživatelské jméno</b> nebo <b>email</b> již v je zaregistrované.')

        print(user, email, psw, pswc, agree)
        self.redirect('/')
