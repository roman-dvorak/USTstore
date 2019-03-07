#!/usr/bin/python
# -*- coding: utf-8 -*-

# tento soubor ma link ve slozce ./plugins
# original je umisten ve slozce ./handlers

import tornado
import tornado.web
import pymongo
import owncloud
import hashlib, uuid
import functools
import bson
import datetime
import os
import bson
from hashlib import blake2s

def make_handlers(module, plugin):
        handlers = [
            (r'/login', plugin.loginHandler),
            (r'/logout', plugin.logoutHandler),
            (r'/registration', plugin.regHandler),
            (r'/api/backup', plugin.doBackup),
            (r'/system', plugin.system_handler),
            (r'/system/', plugin.system_handler)]
        return handlers

def plug_info():
    return {
        "module": "system",
        "name": "system"
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

def save_file(db, original_filename):
    path = os.path.dirname(original_filename)
    file = os.path.basename(original_filename)

    record = db.owncloud.find_one({'original_filename': file, 'path': path})
    if record:
        db.owncloud.update({'_id': record['_id']},{
                '$inc': {'revision': 1},
                '$set': {'update': datetime.datetime.now()}
            })
        return os.path.join(path, str(record['_id'])+"_"+file)
    else:
        out = db.owncloud.insert({
                'path': path,
                'original_filename': file,
                'revision': 1,
                'author': 'autor',
                'type': 'file',
                'update': datetime.datetime.now()
            })
        print("....", out)
        return os.path.join(path, str(out)+"_"+file)

def upload_file(oc, local, remote, earse = True):
    oc.put_file(remote, local)
    os.remove(local)
    file = oc.share_file_with_link(remote)
    return file


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

    def base(self, num, symbols="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", b=None):
        if not b:
            b = len(symbols)
        return ((num == 0) and symbols[0]) or (self.base(num // b, symbols, b).lstrip(symbols[0]) + symbols[num % b])


    def get_warehouseses(self):
        return list(self.mdb.warehouse.find().sort([('code',1)]))

    def warehouse_get_positions(self, warehouse):
        data = self.mdb.store_positions.aggregate([
            {"$match": {'warehouse': warehouse}},
            #{"$project": {''}}
        ])
        return (data)


    def component_get_counts(self, id, warehouse = False):
        if not warehouse:
            out = list(self.mdb.stock.aggregate([{
                "$facet":{
                    "suma":[
                        {"$match": {"_id": id}},
                        {"$unwind": "$history"},
                        {"$group": {"_id": None, "count":{"$sum": "$history.bilance"}}},
                        {"$project": {"count": 1, "_id":0}}
                    ],
                     "by_warehouse":[
                         {"$match": {"_id": id}},
                         {"$unwind": "$history"},
                         {"$group": {"_id": "$history.stock", "count":{"$sum": "$history.bilance"}}},
                         {"$sort": {"warehouse": 1}},
                         {"$lookup": {"from": "store_positions", "localField": '_id', "foreignField" : '_id', "as": "position"}},
                         {"$lookup": {"from": "warehouse", "localField": 'position.warehouse', "foreignField" : '_id', "as": "warehouse"}},
                         {"$project": {
                            "_id":0,
                            "warehouse":1,
                            "count": 1,
                            "position": { "$arrayElemAt": [ "$position", 0 ] },
                            "warehouse": { "$arrayElemAt": [ "$warehouse", 0 ] },
                            }},
                     ]
                }
            }]))
        else:
            print(warehouse, type(warehouse))
            out = list(self.mdb.stock.aggregate([{
                "$facet":{
                    "suma":[
                        {"$match": {"_id": id}},
                        {"$unwind": "$history"},
                        {"$group": {"_id": None, "count":{"$sum": "$history.bilance"}}},
                        {"$project": {"count": 1, "_id":0}}
                    ],
                     "by_warehouse":[
                         {"$match": {"_id": id}},
                         {"$unwind": "$history"},
                         {"$group": {"_id": "$history.stock", "count":{"$sum": "$history.bilance"}}},
                         {"$sort": {"warehouse": 1}},
                         {"$lookup": {"from": "store_positions", "localField": '_id', "foreignField" : '_id', "as": "position"}},
                         {"$match": {"position.warehouse": warehouse}},
                         {"$lookup": {"from": "warehouse", "localField": 'position.warehouse', "foreignField" : '_id', "as": "warehouse"}},
                         {"$project": {
                            "_id":0,
                            "warehouse":1,
                            "count": 1,
                            "position": { "$arrayElemAt": [ "$position", 0 ] },
                            "warehouse": { "$arrayElemAt": [ "$warehouse", 0 ] },
                            }},
                     ]
                }
            }]))

        #print("GET Component COUNTS....")
        #print(out[0]['by_warehouse'])

        return out[0]

    def component_get_suppliers(self, id):
        out = self.mdb.stock.aggregate([
                {"$match": {"_id": id}},
                {"$unwind": '$supplier'},
                {"$project": {'supplier':1, '_id':0}}
            ])
        return list(out)

    def component_set_position(self, id, position, primary = False):
        '''
        id: Id polozky, ktera se vyhledavam
        position: Pozice, ktera se nastavuje pro polozkou
        primary: ma byt polozka primarni?
        '''
        target_position = position
        target_primary = primary

        # zjisti warehouse id podle toho, jakou pridavam pozici
        warehouseid = self.mdb.store_positions.find_one({'_id': target_position})

        print(".>>>> pos", warehouseid)

        out2 = list(self.mdb.stock.aggregate([
            {"$match": {'_id': id}},
            {"$unwind": "$position"},
            {"$lookup": {"from": 'store_positions', 'localField': 'position.posid', 'foreignField': '_id', 'as': 'pos'}},
            {"$match": {'pos.warehouse':  warehouseid['warehouse']}},
            {'$project': {'pos':1, 'position': 1, 'name':1}}
        ]))

        primary = None
        exist = False
        for pos in out2:
            print(pos)
            if target_position == pos['position']['posid']:
                exist = True
            if pos['position']['primary']:
                primary = pos['position']['posid']
        print(bson.json_util.dumps(out2, indent=4))
        print("nalezeno", exist)
        print("primarni", primary)

        if not primary:
            print("Primary position is not set yet.")
            target_primary = True

        if target_position == primary or (exist and target_position != primary and not target_primary):
            print("This position is exist.")
            return True

        if exist:
            print("Nastavim pozici na primarni")
            if primary and not target_primary:
                self.mdb.stock.update(
                    {'_id': id, 'position.posid': primary},
                    {"$set": {"position.$.primary": False}}
                )
            self.mdb.stock.update(
                {'_id': id, 'position.posid': target_position},
                {"$set": {"position.$.primary": target_primary}}
            )
            return True
        else:
            print("Nastavim novou pozici")
            if primary and target_primary:
                print("Earsing primary positions", primary, target_primary)
                self.mdb.stock.update(
                    {'_id': id, 'position.posid': primary},
                    {"$set": {"position.$.primary": False}}
                )
            self.mdb.stock.update(
                {'_id': id},
                {"$addToSet": {"position": {"posid": target_position, "primary": target_primary}}}
            )
            return True

    def component_remove_position(self, id, stock):
        self.mdb.stock.update(
            {'_id': bson.ObjectId(id)},
            {"$pull": {"position":{"posid": bson.ObjectId(stock)}}}
        )

    def component_get_positions(self, id, stock = None, primary = False):
        #stock = None
        '''
        'id': id polozky, ktera bude vyhledana
        'stock': id skladu, ve kterem se bude vyhledavat. Pokud je False, vyhledava se vsude
        'primary': Vyhledavaji se pouze primarni pozice
        '''
        q =[{"$match": {"_id": id}},
            {"$unwind": "$position"},
            {"$lookup": {"from": "store_positions", "localField": 'position.posid', "foreignField" : '_id', "as": "position.info"}},
            {"$project" : {"pos":1, "position":1}},
            {"$replaceRoot": {"newRoot": "$position"}
        }]
        if stock:
            print("VYBRANY STOCK...")
            print(stock, type(stock))
            q += [{"$match": {"info.warehouse": stock}}]
        if primary:
            q += [{"$match": {"primary": primary}}]
        data = list(self.mdb.stock.aggregate(q))
        print(bson.json_util.dumps(data, indent=4))
        return data

    def barcode(self, hex):
        print(int(hex, 16))
        code = blake2s(bytes(hex, 'utf-8'), digest_size=6)
        code = int(code.hexdigest(), 16)
        print(code)
        code = self.base(code, b=62)
        code += code[1]
        code += code[0]
        return code

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
        user_db['param'] = {}
        user_db['param']['warehouse'] = self.get_cookie('warehouse', None)
        return user_db

    def authorized(self, required = [], sudo = True):
        print("Authorized.....", required)
        if self.get_current_user():
            if sudo:
                required = required + ['sudo']
            req = set(required)
            intersection = list(self.role&req)
            if  bool(intersection):
                print("DOstatecna prava")
                return intersection
            else:
                print("Uzivatel nema dostatecna opravneni k pristupu", required)
                raise tornado.web.HTTPError(403)
                self.finish()
        else:
            print("REDIRECT na LOGIN")
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


class BaseHandlerOwnCloud(BaseHandler):
    def prepare(self):
        self.oc = owncloud.Client(tornado.options.options.owncloud_url)
        self.oc.login(tornado.options.options.owncloud_user, tornado.options.options.owncloud_pass)
        super(BaseHandlerOwnCloud, self).prepare()

class loginHandler(BaseHandler):
    def get(self):
        self.render('_login.hbs', msg='')

    def post(self):
        user = self.get_argument('user')
        passw= self.get_argument('pass')

        username = self.mdb.users.find_one({"$or": [{"user": user},{'email': user}]})
        print("USERNAME:", username)
        if username:
            username = username.get('user', None)
            hash = hashlib.sha384((passw+username).encode('utf-8')).hexdigest()
            print("login", username, hash)
            userdb = self.mdb.users.find_one({"$or": [{"user": user},{'email': user}], 'pass': hash})
            if userdb:
                self.set_secure_cookie('user', userdb['user'])
                self.redirect('/')
                self.finish()

        self.redirect('/login?msg=badlogin')

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

class doBackup(BaseHandlerOwnCloud):
    def get(self):
        remote =  os.path.join(tornado.options.options.owncloud_root, 'backup', '2018', 'mdb')
        remote = os.path.join(tornado.options.options.owncloud_root, 'accounting')
        import subprocess
        subprocess.run(["mongodump", "--out=static/tmp/mdb/"])
        self.oc.put_directory(remote, 'static/tmp/mdb')
        #os.remove('static/tmp/mdb')
        self.write("OK")



class system_handler(BaseHandler):
    def get(self):
        self.render('system.homepage.hbs', warehouses = self.get_warehouseses())

    def post(self):
        operation = self.get_argument('operation')
        if operation == 'set_warehouse':
            self.set_cookie("warehouse", self.get_argument('warehouse'))
            print("Nastaveno cookie pro vybrany warehouse")
