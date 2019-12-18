#!/usr/bin/python
# -*- coding: utf-8 -*-

# tento soubor ma link ve slozce ./plugins
# original je umisten ve slozce ./handlers
import time

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

from bson import ObjectId
from tornado.options import define, options
from termcolor import colored
from tornado.web import HTTPError

from plugins.helpers.owncloud_utils import generate_actual_owncloud_path, get_file_last_version_index, \
    get_file_last_version_number


def make_handlers(module, plugin):
    handlers = [
        (r'/login', plugin.LoginHandler),
        (r'/logout', plugin.LogoutHandler),
        (r'/registration', plugin.RegistrationHandler),
        (r'/api/backup', plugin.doBackup), ]
    return handlers


def plug_info():
    return {
        "module": "init",
        "name": "init"
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
        db.owncloud.update({'_id': record['_id']}, {
            '$inc': {'revision': 1},
            '$set': {'update': datetime.datetime.now()}
        })
        return os.path.join(path, str(record['_id']) + "_" + file)
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
        return os.path.join(path, str(out) + "_" + file)


def upload_file(oc, local, remote, earse=True):
    oc.put_file(remote, local)
    os.remove(local)
    file = oc.share_file_with_link(remote)
    return file


@parametrized
def perm_validator(method, permissions=[], sudo=True):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        print(kwargs)
        return method

    return wrapper


def database_init():
    print(options.as_dict())
    return pymongo.MongoClient(tornado.options.options.mdb_url, tornado.options.options.mdb_port)[
        tornado.options.options.mdb_database]


def get_company_info(database):
    return database.intranet.find_one({"_id": "company_info"}) or {}


def get_dpp_params(database):
    return database.intranet.find_one({"_id": "dpp_params"}) or {}


class Intranet(tornado.web.RequestHandler):
    # tento handler pouzivat jen pro veci, kde je potreba vnitrni autorizace - tzn. jen sprava systemu
    def prepare(self):
        self.xsrf_token
        try:
            self.access
            print("autorizovany uzivatel", self.access)
            if not 'sudo' in self.access:
                self.access.append('sudo')
                pass
        except AttributeError:
            self.access = ['sudo']
            print("Prava nejsou nastavena", self.access)

        login = self.get_secure_cookie("user")
        token = self.get_secure_cookie("token")
        print("login, token je:", login, token)

        if login:
            login = login.decode()
            token = eval(token)
            self.mdb = database_init()
            self.getCategories()
            print(self.mdb)
            # user_db =  self.mdb.users.find({'login': login})
            user_db = self.mdb.users.find({"user": str("roman-dvorak")})[0]
            print("ACCESS", type(user_db), user_db, str(login))
            print(user_db['user'])
            self.actual_user = user_db
            self.role = user_db['role']

            if not 'remote_token' in self.actual_user:
                rt = haslib.md5(str(uuid.uuid4())).hexdigest()
                # self.mdb.users.update({ "_id": self.actual_user["_id"] }, { "set": { "remote_token": rt } })
                # self.actual_user['remote_token'] = rt
                print(rt)

            print("prava uzivatele \t", self.role)
            print("potrebna prava  \t", self.access)
            print("spolecne klice  \t", set(self.access) & set(self.role))
            print(type(login), type(user_db['user']))
            print(login, user_db['user'])
            print("Uzivatel je prihlasen", login)
            if bool(set(self.access) & set(self.role)) and str(user_db['user']) == str(login):
                print("a ma dostatecna opravneni")
                return None
            print(bool(set(self.access) & set(self.role)), str(user_db['user']) == str(login))
            print("Nema dostatecna opravneni")
            self.redirect("/eshop")
            return None
        else:
            print("uzivatel neni korektne prihlasen")
            self.redirect("/login")
            return None

    def getCategories(self):
        print("###########################")
        cats = self.mdb.categories.find({})
        counts = {}
        # for p in cat_list:
        for cat in cats:
            print(cat)
            p = cat['path'] + cat['_id']
            print(p)
            parts = p.split('/')
            branch = counts
            for part in parts[1:-1]:
                branch = branch.setdefault(part + cat['_id'], {})
            # branch[parts[-1]] = 1 + branch.get(parts[-1], 0)
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
    role_module = []

    def prepare(self):
        login = self.get_secure_cookie("user")
        if login:
            login = str(login, encoding="utf-8")

        self.mdb = database_init()
        user_db = self.mdb.users.find_one({'user': login})

        self.company_info = get_company_info(self.mdb)
        self.dpp_params = get_dpp_params(self.mdb)

        if login and user_db.get('user', False) == login:
            self.actual_user = user_db
            self.role = set(user_db['role'])
            if not self.is_authorized(self.role_module) and len(self.role_module) > 0:
                raise tornado.web.HTTPError(401)

            cart = self.get_cookie('cart', None)
            # print("Nakupni kosik", bson.ObjectId(cart))
            if cart:
                self.cart = list(self.mdb.carts.find({'_id': bson.ObjectId(cart)}))[0]
            else:
                self.cart = None

            self.logged = login
            return None
        else:
            print("uzivatel neni korektne prihlasen")
            self.logged = False
            return None

    def base(self, num, symbols="0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", b=None):
        if not b:
            b = len(symbols)
        return ((num == 0) and symbols[0]) or (self.base(num // b, symbols, b).lstrip(symbols[0]) + symbols[num % b])

    def get_warehouseses(self):
        return list(self.mdb.warehouse.find().sort([('code', 1)]))

    def get_current_warehouse_id(self):
        print(colored("[get_current_warehouse]", "green"))
        oid = bson.ObjectId(self.get_cookie('warehouse', None))
        return oid

    '''
    Ze zadaneho ObjectID pozice to vyhleda sklad
    '''

    def get_warehousese_by_position(self, position: bson.ObjectId):
        print(colored("[get_warehousese_by_position]", "green"))

        warehouse = self.mdb.store_positions.aggregate([
            {"$match": {'_id': position}}
        ])
        warehouse = list(warehouse)
        if len(warehouse) < 1:
            return None

        return warehouse[0]['warehouse']

    '''
    Ze zadaneho ObjectID skladu vrati informace o skladu
    '''

    def get_warehouse(self, warehouseid=None):
        if not warehouseid:
            warehouseid = self.get_current_warehouse_id()
        else:
            warehouseid = bson.ObjectId(warehouseid)
        print(warehouseid)
        warehouse = list(self.mdb.warehouse.aggregate([
            {"$match": {'_id': warehouseid}}
        ]))[0]
        return (warehouse)

    def warehouse_get_positions(self, warehouse):
        data = self.mdb.store_positions.aggregate([
            {"$match": {'warehouse': warehouse}},
            # {"$project": {''}}
        ])
        return (data)

    '''
    Ze zadaneho ObjectID skladu vrati informace o pozici
    '''

    def get_position(self, position: bson.ObjectId):
        position = self.mdb.store_positions.aggregate([
            {"$match": {'_id': position}}
        ])
        return (list(position)[0])

    def component_get_counts(self, id, warehouse=None):
        out = list(self.mdb.stock.aggregate([
            {"$match": {"_id": id}},
            {"$project": {"overview": 1}}
        ]))

        # dout = {}
        # dout['stocks'] = out[0]['overview']
        # dout['count'] = {
        #                'onstock': 0,
        #                'requested': 0,
        #                'ordered': 0
        #            }

        # for stock in out[0]['overview']:
        #    dout['count']['onstock'] += out[0]['overview'][stock]['count']['onstock']
        #    dout['count']['requested'] += out[0]['overview'][stock]['count']['requested']
        #    dout['count']['ordered'] += out[0]['overview'][stock]['count']['ordered']

        return out[0]['overview']

    '''
        Tato funkce vezme historii polozky a z ni to vytvori soucty do jednotlivych skladu a pozic
    '''

    def component_update_counts(self, id):
        print(colored("[component_update_counts]", "green", attrs=["bold"]))
        out = list(self.mdb.stock.aggregate([
            {"$match": {"_id": id}},
            {"$unwind": "$history"},

        ]))
        out = list(out)

        overview = {
            'count': {
                'onstock': 0,
                'requested': 0,
                'ordered': 0
            },
            'stocks': {}
        }
        for operation in out:
            operation = operation['history']
            warehouse = str(operation.get('stock', "5c67444e7e875154440cc28f"))
            print(warehouse)

            if warehouse not in overview['stocks']:
                overview['stocks'][warehouse] = {
                    'count': {
                        'onstock': 0,
                        'requested': 0,
                        'ordered': 0
                    }
                }

            if "operation" not in operation:
                overview['stocks'][warehouse]['count']['onstock'] += operation['bilance']
                overview['count']['onstock'] += operation['bilance']

            elif operation['operation'] in ['inventory', 'service', 'sell', 'buy', 'move_in', 'move_out']:
                overview['stocks'][warehouse]['count']['onstock'] += operation['bilance']
                overview['count']['onstock'] += operation['bilance']

            elif operation['operation'] in ['buy_request']:
                overview['stocks'][warehouse]['count']['requested'] += operation['bilance']
                overview['count']['requested'] += operation['bilance']

            else:
                print("[NEZNAMA OPERACE]", operation['operation'])
                print(operation)

        self.mdb.stock.update({"_id": id}, {"$set": {"overview": overview}})
        print(bson.json_util.dumps(overview, indent=2))
        print(colored("![component_update_counts]", "yellow", attrs=["bold"]))

    def component_get_buyrequests(self, id):
        out = list(self.mdb.stock.aggregate([  # {
            # "$facet":{
            #    "list":[
            {"$match": {"_id": id}},
            {"$unwind": "$history"},
            {"$match": {"history.operation": 'buy_request'}},
            {"$replaceRoot": {'newRoot': '$history'}},
            #    ],
            # }
        ]))
        return out

    def component_get_suppliers(self, id):
        out = self.mdb.stock.aggregate([
            {"$match": {"_id": id}},
            {"$unwind": '$supplier'},
            {"$project": {'supplier': 1, '_id': 0}}
        ])
        return list(out)

    def component_set_position(self, id, position, primary=False):
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

        current_positions = list(self.mdb.stock.aggregate([
            {"$match": {'_id': id}},
            {"$unwind": "$position"},
            {"$lookup": {"from": 'store_positions', 'localField': 'position.posid', 'foreignField': '_id',
                         'as': 'pos'}},
            {"$match": {'pos.warehouse': warehouseid['warehouse']}},
            {'$project': {'pos': 1, 'position': 1, 'name': 1}}
        ]))

        primary = None
        exist = False
        for pos in current_positions:
            print(pos)
            if target_position == pos['position']['posid']:
                exist = True
            if pos['position']['primary']:
                primary = pos['position']['posid']
        print(bson.json_util.dumps(current_positions, indent=4))
        print("nalezeno", exist)
        print("primarni", primary)

        if not primary:
            print("Primary position is not set yet.")
            target_primary = True

        if target_position == primary or (exist and target_position != primary and not target_primary):
            print("This position is exist.")
            return True

        # pokud tato skladova pozice uz u polozky existuje.
        if exist and target_primary:
            print("Nastavim pozici na primarni")
            self.mdb.stock.update(
                {'_id': id},
                {"$set": {"position.$[].primary": False}}
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
            {"$pull": {"position": {"posid": bson.ObjectId(stock)}}}
        )

    def component_get_positions(self, id, stock=None, primary=False):
        # stock = None
        '''
        'id': id polozky, ktera bude vyhledana
        'stock': id skladu, ve kterem se bude vyhledavat. Pokud je False, vyhledava se vsude
        'primary': Vyhledavaji se pouze primarni pozice
        '''
        q = [{"$match": {"_id": id}},
             {"$unwind": "$position"},
             {"$lookup": {"from": "store_positions", "localField": 'position.posid', "foreignField": '_id',
                          "as": "position.info"}},
             {"$project": {"pos": 1, "position": 1}},
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

    def component_update_suppliers_url(self, id):
        '''
        'id': id polozky, ktera bude vyhledana
        '''
        print("Component update component_update_suppliers_url")
        out = list(self.mdb.stock.find({"_id": id}))[0]

        try:
            for i, x in enumerate(out.get('supplier', [])):
                print("Supplier:")
                print(x)
                x['full_url'] = x.get('url', '')

                if x['supplier'].lower() == 'tme':
                    x['full_url'] = "https://www.tme.eu/cz/details/{}".format(x['symbol'])

                elif x['supplier'].lower() == 'mouser':
                    x['full_url'] = "https://cz.mouser.com/ProductDetail/{}".format(x['symbol'])

                elif x['supplier'].lower() == 'farnell':
                    x['full_url'] = "https://cz.farnell.com/{}".format(x['symbol'])

                elif x['supplier'].lower() == 'ecom':
                    x['full_url'] = "https://www.ecom.cz/?q={}&sAction=product_list&x=0&y=0".format(x['symbol'])

                elif x['supplier'].lower() == 'digikey':
                    x['full_url'] = "https://www.digikey.com/products/en?keywords={}".format(x['symbol'])

                elif x['supplier'].lower() == 'killich':
                    x['full_url'] = "https://eshop.killich.cz/?search=+{}".format(x['symbol'])

                self.mdb.stock.update({"_id": id}, {"$set": {"supplier.{}".format(i): x}})

        except Exception as e:
            print(e)

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
        wh = self.get_cookie('warehouse', None)
        user_db['param']['warehouse'] = wh
        user_db['param']['warehouse_info'] = self.mdb.warehouse.find_one({'_id': bson.ObjectId(wh)})
        return user_db

    def authorized(self, required=[], sudo=True):
        print("Authorized.....", required)
        if self.get_current_user():
            if sudo:
                required = required + ['sudo']
            req = set(required)
            intersection = list(self.role & req)
            if bool(intersection):
                print("DOstatecna prava")
                return intersection
            else:
                print("Uzivatel nema dostatecna opravneni k pristupu", required)
                raise tornado.web.HTTPError(403)
                self.finish()
        else:
            print("REDIRECT na LOGIN")
            self.redirect('/login')

    def is_authorized(self, required=[], sudo=True):
        print("AUTHORIZATION.....")
        if self.get_current_user():
            if sudo:
                required = required + ['sudo']
            req = set(required)
            intersection = list(self.role & req)
            if bool(intersection):
                return intersection
            else:
                return False
        else:
            self.redirect('/login')

    def getComponentById(self, id):
        return (self.mdb.stock.find_one({'_id': id}))

    def LogActivity(self, module=None, operation=None, data={}, user=None):
        if not user: user = self.logged
        if not module: module = self.__class__.__name__
        print("Activity logger:")
        print(">> activity from {} in {} module".format(user, module))
        print(">> operation: {}".format(operation))

        self.mdb.operation_log.insert({'user': user, 'module': module, 'operation': operation, 'data': data})


#
#    def update_component(self, component):
#

class BaseHandlerJson(BaseHandler):
    def prepare(self):
        self.set_header('Content-Type', 'application/json')
        super(BaseHandlerJson, self).prepare()


class BaseHandlerOwnCloud(BaseHandler):

    def prepare(self):
        self.oc = owncloud.Client(tornado.options.options.owncloud_url)
        self.oc.login(tornado.options.options.owncloud_user, tornado.options.options.owncloud_pass)

        super(BaseHandlerOwnCloud, self).prepare()

    def upload_to_owncloud(self,
                           oc_directory,
                           oc_filename,
                           local_path,
                           uploaded_by_id,
                           delete_local=True):
        file_id = ObjectId()

        oc_path = generate_actual_owncloud_path(str(file_id),
                                                oc_directory,
                                                oc_filename,
                                                0,
                                                tornado.options.options.owncloud_root)

        self.put_file(oc_path, local_path)
        shared_url = self.oc.share_file_with_link(oc_path).get_link()

        coll: pymongo.collection.Collection = self.mdb.owncloud
        coll.insert_one({
            "_id": file_id,
            "directory": oc_directory,
            "filename": oc_filename,
            "versions": {
                "0": {
                    "by": uploaded_by_id,
                    "when": datetime.datetime.now(),
                    "path": oc_path,
                    "url": shared_url,
                }
            }
        })

        if delete_local:
            os.remove(local_path)

        return file_id

    def put_file(self, oc_path, local_path):
        start_time = time.time()
        print("-> nahrávám soubor na owncloud")
        self.oc.put_file(oc_path, local_path)
        print(f"-> soubor nahrán za {(time.time() - start_time):.2f} sekund")

    def update_owncloud_file(self,
                             file_id: ObjectId,
                             local_path: str,
                             uploaded_by_id: str,
                             delete_local=True):
        coll: pymongo.collection.Collection = self.mdb.owncloud
        file_mdoc = coll.find_one({"_id": file_id})

        version_number = get_file_last_version_number(file_mdoc) + 1
        oc_path = generate_actual_owncloud_path(str(file_id),
                                                file_mdoc['directory'],
                                                file_mdoc['filename'],
                                                version_number,
                                                tornado.options.options.owncloud_root)

        self.put_file(oc_path, local_path)
        shared_url = self.oc.share_file_with_link(oc_path).get_link()

        coll.update_one({"_id": file_id},
                        {"$set": {
                            f"versions.{version_number}": {
                                "by": uploaded_by_id,
                                "when": datetime.datetime.now(),
                                "path": oc_path,
                                "url": shared_url,
                            }
                        }})

        if delete_local:
            os.remove(local_path)

    def save_uploaded_files(self, input_name, directory="static/tmp"):
        if not self.request.files or not self.request.files[input_name]:
            return None

        processed_paths = []

        for file in self.request.files[input_name]:
            file_path = os.path.join(directory, file["filename"])

            with open(file_path, "wb") as f:
                f.write(file["body"])

            processed_paths.append(file_path)

        return processed_paths


def password_hash(user_name, password):
    return hashlib.sha384((password + user_name).encode('utf-8')).hexdigest()


class LoginHandler(BaseHandler):
    def get(self):
        self.render('_login.hbs', msg='')

    def post(self):
        email = self.get_argument('email').lower()
        password = self.get_argument('password')
        print("Prihlasovani", email)

        user_mdoc = self.mdb.users.find_one({"type": "user", "email": email})

        if not user_mdoc:
            self.render("_login.hbs", msg="No such user")
            return

        user_name = user_mdoc["user"]
        real_password_hash = user_mdoc["pass"]
        this_password_hash = password_hash(user_name, password)

        if real_password_hash == this_password_hash:
            self.set_secure_cookie('user', user_name)
            self.redirect('/')
            return

        self.render("_login.hbs", msg="Wrong password")


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie('user')
        self.redirect('/')

    def post(self):
        self.clear_cookie('user')


class RegistrationHandler(BaseHandler):
    def get(self):
        self.render('_registration.hbs', msg=None)

    def post(self):
        email = self.get_argument('email')
        password = self.get_argument('password')
        password_check = self.get_argument('password_check')
        agree = self.get_argument('agree')

        if agree != 'agree':
            self.render('_registration.hbs', msg='Musíte souhlasit s ...')
            return

        if password != password_check:
            self.render('_registration.hbs', msg='Hesla se neshodují')
            return

        user_name = email
        matching_users_in_db = list(self.mdb.users.find({'$or': [{'user': user_name}, {'email': email}]}))
        if matching_users_in_db:
            self.render('_registration.hbs',
                        msg='Toto <b>uživatelské jméno</b> nebo <b>email</b> již v je zaregistrované.')
            return

        new_password_hash = password_hash(user_name, password)

        self.mdb.users.insert({
            'user': user_name,
            'pass': new_password_hash,
            'email': email,
            'email_validated': "no",
            'created': datetime.datetime.now(),
            'type': 'user',
            'role': [],
        })

        print("Registrován email", email)
        self.redirect('/')


class doBackup(BaseHandlerOwnCloud):
    def get(self):
        remote = os.path.join(tornado.options.options.owncloud_root, 'backup', '2018', 'mdb')
        remote = os.path.join(tornado.options.options.owncloud_root, 'accounting')
        import subprocess
        subprocess.run(["mongodump", "--out=static/tmp/mdb/"])
        self.oc.put_directory(remote, 'static/tmp/mdb')
        # os.remove('static/tmp/mdb')
        self.write("OK")
