#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from .. import Intranet
from .. import BaseHandler
#from pyoctopart.octopart import Octopart
import json
import bson
import bson.json_util
from bson import *
from bson import ObjectId
import urllib
from fpdf import FPDF
import barcode
import code128
import codecs
import datetime

from plugins.helpers.warehouse import *

def get_plugin_handlers():
        plugin_name = get_plugin_info()["name"]

        return [
             (r'/%s' %plugin_name, hand_bi_home),
             (r'/%s/' %plugin_name, hand_bi_home),
             (r'/%s/print/' %plugin_name, print_layout),
             (r'/{}/api/items/by_position/'.format(plugin_name), api_get_items_by_position),
             (r'/{}/api/packets/by_position/'.format(plugin_name), api_get_packets_by_position),
             (r'/{}/api/item/(.*)/'.format(plugin_name), api_item_json),
             (r'/{}/api/item/(.*)/buy_request'.format(plugin_name), api_buyrequest_json),
             (r'/{}/api/item/(.*)/suppliers'.format(plugin_name), api_suppliers),
             (r'/{}/api/products/'.format(plugin_name), api_products_json),
             #(r'/{}/api/get_parameters/list/'.format(plugin_name), api_parameters_list),
             (r'/{}/api/get_positions/list/'.format(plugin_name), api_positions_list),
             (r'/{}/api/get_positions/list/(.*)'.format(plugin_name), api_positions_list),
             (r'/{}/api/set_positions/update/'.format(plugin_name), api_update_position),
             (r'/{}/api/set_positions/move/'.format(plugin_name), api_move_position),

             (r'/{}/api/get_categories/list/'.format(plugin_name), api_categories_list),
             (r'/{}/api/get_categories/list/(.*)'.format(plugin_name), api_categories_list),
             (r'/{}/api/set_categories/move/'.format(plugin_name), api_move_category),
             (r'/{}/api/set_categories/update/'.format(plugin_name), api_update_category),
             (r'/{}/api/get_parameters/list/'.format(plugin_name), api_parameters_list),

             (r'/%s/newprint' %plugin_name, newprint),
             (r'/%s/api/(.*)/' %plugin_name, api),
             (r'/{}/operation/(.*)/'.format(plugin_name), operation)
        ]

def get_plugin_info():
    return{
        "role": ['store-access', 'store-sudo', 'sudo', 'store-manager'],
        "name": "store",
        "entrypoints": [
            {
                "title": "Sklad",
                "url": "/store",
                "icon": "business",
            }
        ]
    }

ascii_list_to_str = lambda input: [x.decode('ascii') for x in input]
ascii_list_to_str = lambda input: [str(x, 'utf-8') for x in input]


class api_item_json(BaseHandler):
#    Tato funkce vrati zakladni informace o polozce
#
# bez upravy dokumentace neupravovat.

    role_module = ['store-sudo', 'store-manager', 'store-access', 'store-read']
    def post(self, id):
        iid = bson.ObjectId(id)
        self.set_header('Content-Type', 'application/json')
        print("Vyhledavam soucastku s ID:", iid)
        item = list(self.mdb.stock.aggregate([
            {"$match": {"_id": iid}},
        ]))
        print(item)
        self.write(bson.json_util.dumps(item))

class api_buyrequest_json(BaseHandler):
#    Tato funkce sezam pozadavku na nakup soucastky
#
# bez upravy dokumentace neupravovat.

    role_module = ['store-sudo', 'store-manager', 'store-access', 'store-read']
    def post(self, id):
        iid = bson.ObjectId(id)
        self.set_header('Content-Type', 'application/json')
        print("Vyhledavam soucastku s ID:", iid)
        item = list(self.mdb.stock.aggregate([
            {"$match": {"_id": iid}},
            {"$unwind": "$history"},
            {"$match": {"history.operation": 'buy_request'}},
            #{"$project": {'history': 1}}
        ]))
        self.write(bson.json_util.dumps(item))

class api_suppliers(BaseHandler):
    def get(self, iid):
        iid = bson.ObjectId(iid)
        print("soucastka", iid)
        item = list(self.mdb.stock.aggregate([
            {"$match": {"_id": iid}},
            {"$unwind": "$supplier"},
            {"$project": {'supplier': 1, 'name': 1}}
        ]))

        for i in item:
            if i['supplier'].get('url', False):
                i['url'] = i['supplier']['url']
            elif i['supplier'].get('supplier', "none") == 'TME':
                i['url'] =  "https://www.tme.eu/details/{}".format(i.get('symbol', ''))

        self.render('store/store.item.suppliers_view.hbs', suppliers = item)


class api_products_json(BaseHandler):
    role_module = ['store-sudo', 'store-access', 'store-manager', 'store_read']

    def post(self):
        self.set_header('Content-Type', 'application/json')
        dout = {}

        polarity = '$nin' if (self.request.arguments.get('polarity', [b'true'])[0] == b'true') else '$in'
        tag_polarity = not self.request.arguments.get('tag_polarity', b'true')[0] == b'true'
        selected = (self.request.arguments.get('categories[]', []))
        for i, cat in enumerate(selected):
            print(cat.decode('UTF-8'))
            selected[i] = bson.ObjectId(cat.decode('UTF-8'))
        print("SEZNAM kategorie", selected)
        in_stock = self.get_argument('in_stock', 'All')
        page = self.get_argument('page', 0)
        page_len = self.get_argument('page_len', 100)
        search = self.get_argument('search')#.decode('ascii')
        tag_search = self.get_argument('tag_search', '')#.decode('ascii')
        print("SEARCH", search)
        print("search polarity", polarity, selected)
        print("tag polarity", tag_polarity, in_stock)
        dout = {}

        if bson.ObjectId.is_valid(search):
            print("Vybiram rozpoznani dle ObjectID")
            agq = [{"$match": {'_id': bson.ObjectId(search)}
                },{
                    '$addFields': {'count': { '$sum': '$history.bilance'}}
                }]
            count = len(list(self.mdb.stock.aggregate(agq)))

        elif search.isdigit():
            search_string = "{:x}".format(int(search))
            agq = [{"$match": {'_id': bson.ObjectId(search_string)}
                },{
                    '$addFields': {'count': { '$sum': '$history.bilance'}}
                }]
            count = len(list(self.mdb.stock.aggregate(agq)))


        else:

            print("Hledam podle parametru")
            agq = [
                {"$unwind": "$_id"},
                {"$sort" : {"category": 1,"_id": 1} },
                {"$match": {'$or':[
                                    {'_id': { '$regex': search, '$options': 'ix'}},
                                    {'name': { '$regex': search, '$options': 'i'}},
                                    {'description': { '$regex': search, '$options': 'i'}} ]}
                },{
                    "$match": {'category': {polarity: selected}}
                },{
                    '$addFields': {'count': { '$sum': '$history.bilance'}}
                }]

            if in_stock == 'Yes':
                agq += [{'$match': {'count': {'$gt': 0}}}]
            elif in_stock == 'No':
                agq += [{'$match': {'count': {'$eq': 0}}}]

            if len(tag_search) > 1 and not tag_polarity:
                agq += [{
                    "$match": {'tags': { '$not': {'$elemMatch': {'id': tag_search}}}}
                }]

            elif len(tag_search) > 1 and tag_polarity:
                agq += [{
                    "$match": {'tags': {'$elemMatch': {'id': tag_search}}}
                }]

            if in_stock == 'Yes':
                agq += [{"$match": {'count': {"$gt": 0}}}]
            elif in_stock == 'No':
                agq += [{"$match": {'count': {"$eq": 0}}}]

            count = len(list(self.mdb.stock.aggregate(agq)))

            agq += [{
                    '$skip' : int(page_len)*int(page)
                },{
                    '$limit' : int(page_len)
                },{
                    "$lookup":{
                        "from": "category",
                        "localField": "category",
                        "foreignField": "_id",
                        "as": "category"
                    }
                },{
                    '$addFields': {'price_buy_avg': {'$avg': '$history.price'}}
                }]

            # agq += [{
            #     "$lookup":{
            #         "from": "",
            #         "localField": "category",
            #         "foreignField": "name",
            #         "as": "category"
            #     }
            # }]
        print(agq)

        dbcursor = self.mdb.stock.aggregate(agq)
        dout['data'] = list(dbcursor)
        print(dout['data'])
        dout['count'] = (count)

        dout = bson.json_util.dumps(dout)
        self.write(dout)


class api_get_items_by_position(BaseHandler):
    role_module = ['store-sudo', 'store-access', 'store-manager', 'store_read']

    def get(self):
        position = bson.ObjectId(self.get_argument('position'))

        data = self.mdb.stock.aggregate([
            {'$match': {'position.posid': position}},
            {'$project' : { 'name' : 1 , 'description' : 1, 'history':1} }
        ])

        data = list(data)

        self.write(bson.json_util.dumps(data))

class api_get_packets_by_position(BaseHandler):
    role_module = ['store-sudo', 'store-access', 'store-manager', 'store_read']

    def get(self):
        position = bson.ObjectId(self.get_argument('position'))
        #stock = self.get_argument('this_stock')

        data = self.mdb.stock.aggregate([
            {'$match': {'packets.position': position}},
            {'$unwind': "$packets"},
            {'$project' : { 'name' : 1 , 'description' : 1, 'packets':1} },
            {'$lookup':{
                'from': 'stock_operation',
                'localField': "packets._id",
                'foreignField': "pid",
                'as': 'history'
                }
            }
        ])

        data = list(data)

        self.write(bson.json_util.dumps(data))


class api_positions_list(BaseHandler):
    role_module = ['store-sudo', 'store-access', 'store-manager', 'store_read']
    def post(self):
        print("api_positions_list")
        self.set_header('Content-Type', 'application/json')
        wid = bson.ObjectId(self.get_cookie("warehouse", None))
        jstree = bool(self.get_argument('jstree', False))
        type = self.get_argument('type', 'jstree')
        print("type", type)

        if type == 'jstree':
            dout = list(self.warehouse_get_positions(wid))
            output = bson.json_util.dumps(dout)
            print("Chceme jstree")
            print('warehouse', wid)

            new = []
            for i, out in enumerate(dout):
                pos = {}
                pos['_id'] = str(out['_id'])
                pos['id'] = str(out['_id'])
                #pos['id'] = out['name']
                pos['text'] = out['name'] + " <small>({})</small>".format(out['text'])
                pos['parent'] = "#"
                pos['li_attr'] = {"name": out['name'], 'text': out['text']}
                if len(out['name'].split('/')) > 1:
                    pos['parent'] = '/'.join(out['name'].split('/')[:1])
                pos['parent'] = str(out.get('parent', '#'))
                new.append(pos)
            output = bson.json_util.dumps(new)
            print(output)

        elif type == 'select':
            print('Chceme select2')

            question = self.get_argument('q', None)
            print(question)
            new = []

            dout = list(self.warehouse_get_positions(wid, q = question))
            output = bson.json_util.dumps(dout)

            for i, out in enumerate(dout):
                pos = {}
                pos['_id'] = str(out['_id'])
                pos['id'] = str(out['_id'])
                #pos['id'] = out['name']
                pos['text'] = out['name'] + " <small>({})</small>".format(out['text'])
                pos['parent'] = "#"
                pos['li_attr'] = {"name": out['name'], 'text': out['text']}
                if len(out['name'].split('/')) > 1:
                    pos['parent'] = '/'.join(out['name'].split('/')[:1])
                pos['parent'] = str(out.get('parent', '#'))
                new.append(pos)
            output = bson.json_util.dumps(new)
            #print(output)

        self.write(output)


# list of all categories
class api_categories_list(BaseHandler):
    role_module = ['store-sudo', 'store-access', 'store-manager', 'store_read']
    def post(self):
        self.set_header('Content-Type', 'application/json')
        jstree = bool(self.get_argument('jstree', False))
        type = self.get_argument('type', 'jstree')
        print("api_categories_list .. ", type)

        if type == 'jstree':
            dout = list(self.mdb.category.find({}))
            new = []
            for i, out in enumerate(dout):
                pos = {}
                pos['_id'] = str(out['_id'])
                pos['id'] = str(out['_id'])
                pos['text'] = "{} <small>({})</small>".format(out['name'], out['description'])
                pos['li_attr'] = {"name": out['name'], 'text': out['description']}
                pos['parent'] = str(out.get('parent', '#'))
                new.append(pos)
            output = bson.json_util.dumps(new)

        elif type == 'select':
            q = self.get_argument('q', None)
            query = []

            if q:
                print("Dotaz,", q)
                query += [{"$match": {'$or':[
                    {'name': { '$regex': q, '$options': 'i'}},
                    {'name_cs': { '$regex': q, '$options': 'i'}},
                    {'description': { '$regex': q, '$options': 'i'}} ]}
                }]

            dout = list(self.mdb.category.aggregate(query))
            # new = []
            # for i, out in enumerate(dout):
            #     pos = {}
            #     pos['_id'] = str(out['_id'])
            #     pos['id'] = str(out['_id'])
            #     pos['text'] = "{} <small>({})</small>".format(out['name'], out['description'])
            #     pos['li_attr'] = {"name": out['name'], 'text': out['description']}
            #     pos['parent'] = str(out.get('parent', '#'))
            #     new.append(pos)
            output = bson.json_util.dumps(dout)

        else:
            dout = list(self.mdb.category.find({}))
            output = bson.json_util.dumps(list(self.mdb.category.find({})))

        self.write(output)

class api_move_category(BaseHandler):
    role_module = ['store-sudo', 'store-access', 'store-manager', 'store_read']
    def post(self):
        parent = self.get_argument('parent', '#')
        cid = bson.ObjectId(self.get_argument("id", None))

        if parent == '':
            print("CHYBA neni nastaven rodic")
            parent = '#'
        if parent is not '#': parent = bson.ObjectId(parent.split('_')[0])
        print("new parent", parent)
        print("Object", self.get_argument("id", None))


        data = {'$set': {'parent': parent} }
        if parent != cid:
            self.mdb.category.update({'_id': cid}, data, upsert=False)
        else:
            print("CHYBA")
        self.write("OK")

class api_move_position(BaseHandler):
    role_module = ['store-sudo', 'store-access', 'store-manager', 'store_read']
    def post(self):
        parent = self.get_argument('parent', '#')
        cid = bson.ObjectId(self.get_argument("id", None))

        if parent == '':
            print("CHYBA neni nastaven rodic")
            parent = '#'
        if parent is not '#': parent = bson.ObjectId(parent.split('_')[0])
        print("new parent", parent)
        print("Object", self.get_argument("id", None))

        data = {'$set': {'parent': parent} }
        if parent != cid:
            self.mdb.store_positions.update({'_id': cid}, data, upsert=False)
        else:
            print("CHYBA")
        self.write("OK")

class api_update_position(BaseHandler):
    role_module = ['store-sudo', 'store-access', 'store-manager', 'store_read']
    def post(self):
        cid = self.get_argument("id", None)
        if cid == 'new':
            cid = bson.ObjectId()
        else:
            cid = bson.ObjectId(cid)

        parent = self.get_argument('parent', None)
        if parent and parent != '#':
            parent = bson.ObjectId(parent)

        print(parent, cid)

        if cid != parent:
            data = {'name': self.get_argument('name'),
                    'text': self.get_argument('text', 'not_set'),
                    'warehouse': bson.ObjectId(self.get_cookie('warehouse'))}

            if parent:
                data['parent'] = parent

            self.mdb.store_positions.update({'_id': cid}, {"$set": data}, upsert=True)
        self.write("OK")

class api_update_category(BaseHandler):
    role_module = ['store-sudo', 'store-access', 'store-manager', 'store_read']
    def post(self):
        cid = self.get_argument("id", None)
        if cid == 'new':
            cid = bson.ObjectId()
        else:
            cid = bson.ObjectId(cid)

        parent = self.get_argument('parent', None)
        if parent and parent != '#':
            parent = bson.ObjectId(parent)
        print(parent, cid)

        if cid != parent:
            data = {'name': self.get_argument('name'),
                    'description': self.get_argument('description', ''),}

            if parent:
                data['parent'] = parent

            self.mdb.category.update({'_id': cid}, {"$set": data}, upsert=True)
        self.write("{'state': 'OK'}")

class api_parameters_list(BaseHandler):
    def get(self):
        self.set_header('Content-Type', 'application/json')
        dout = list(self.mdb.parameters.aggregate([]))

        output = bson.json_util.dumps(dout)
        self.write(output)


class api(BaseHandler):
    role_module = ['store-sudo', 'store-access', 'store-manager', 'store_read']
    def post(self, data=None):
        self.set_header('Content-Type', 'application/json')

        if data == 'product':
            print(self.request.arguments.get('selected[]', None))
            #ZDE POSILAT JEN ID jako je to nize....
            id = bson.ObjectId(self.get_argument('value', ''))
            self.component_update_suppliers_url(id)
            self.component_update_counts(id)
            update_article_price(self.mdb.stock, id)
            dout = list(self.mdb.stock.aggregate([
                    {
                        '$match': {
                            self.get_argument('key', '_id'): ObjectId(self.get_argument('value', ''))
                        }
                    },
                    {"$lookup":
                         {
                           "from": 'store_positions',
                           "localField":'position.posid',
                           "foreignField": '_id',
                           "as": 'positions'
                         }
                    },

                    {"$lookup":
                         {
                           "from": 'category',
                           "localField":'category',
                           "foreignField": '_id',
                           "as": 'categories'
                         }
                    },

                    {
                        '$addFields': {
                            'price_buy_last': {
                                '$avg': {
                                    '$slice' : ['$history.price', -1]
                                }
                            }
                        }
                        # tady 'avg' je jen z duvodu, aby to nevracelo pole ale rovnou cislo ($slice vraci pole o jednom elementu)
                    },
                    {
                        '$addFields': {
                                'price_buy_avg':  {
                                    '$avg': '$history.price'
                                }
                            }
                    },
                    {
                        '$addFields': {
                            'count':  {
                                '$sum': '$history.bilance'
                            }
                        }
                    }
                ]))

            # counta = self.mdb.stock.aggregate([
            #     {"$match": {self.get_argument('key', '_id'): ObjectId(self.get_argument('value', ''))}},
            #     {"$unwind": "$history"},
            #     {"$group": { "_id": "$history.stock", "count": { "$sum": "$history.bilance" }}},
            #     {"$lookup": {"from": "store_positions", "localField": '_id', "foreignField" : '_id', "as": "position"}}
            # ])

            print("COUNT.....ID", id, type(id))
            dout[0]['count_part'] = self.component_get_counts(id)
            dout[0]['positions_local'] = self.component_get_positions(id, stock = bson.ObjectId(self.get_cookie('warehouse', False)))
            #dout[0]['positions_local'] = self.component_get_positions(id, stock = bson.ObjectId("5c67445b7e875154440cc297"))
            print(dout[0]['count_part'])
            print("===================")

        elif data == "get_tags":
            dout = list(self.mdb.stock.distinct('tags.id'))

        elif data == 'get_suppliers':
            cid = self.get_argument('id', None)
            sup = self.get_argument('supplier', None)
            if not cid:
                q = self.get_argument('q', '')
                dbcursor = self.mdb.stock.distinct('supplier.supplier',{'supplier.supplier': {'$regex': q, '$options': 'ix'}})
            else:
                dbcursor = self.mdb.stock.aggregate([
                    {'$match': {'_id': cid, 'supplier.supplier': sup}},
                    {'$unwind': '$supplier'},
                ])
            dout = list(dbcursor)

            for x in dout:
                print(x)

        elif data == 'add_supplier':
            id = self.get_argument('id', None)

            out = self.mdb.update({'_id': id},{
                '$push':{'supplier':{
                        'supplier': self.get_argument('supplier'),
                        'id': self.get_argument('symbol'),
                        'barcode': self.get_argument('barcode', None),
                        'bartype': self.get_argument('bartype', None),
                        'url': self.get_argument('url', None)
                    }}
                })
            print(">>>>>>>>>>>", out)

        elif data == 'update_parameter':
            parameter = self.get_argument('parameter', None)
            if parameter == 'stock_count':
                pass
            else: # casem zakomentovat
                component = self.get_argument('component', [None])
                stock = self.get_argument('stock', [None])
                count = self.get_argument('count', [None])

                if component:
                    print("Pozadavek na upravu", component, "Ze skladu:", stock, "Na pocet", count)
                    self.mdb.stock.update(
                        { "_id": component },
                        {"$set": {"stock."+stock+".count": count}  },
                        upsert = False
                    )
                    dout = {'done': True}

        elif data == 'update_product':
            #TODO: udelat zde nejake overeni spravnosti dat. Alespon, jestli odpovida struktura.
            print(self.get_argument('json', [None]))
            false = False
            true = True
            new_json = json.loads(self.request.arguments.get('json', [None])[0].decode())
            new_json.pop('history', None)
            new_json.pop('count', None)
            new_json.pop('count_part', None)
            new_json.pop('position', None)
            new_json.pop('positions_local', None)
            #new_json.pop('barcode', None)


            print("Update product with parameters:")
            print(json.dumps(new_json, indent=4))

            id = new_json.pop("_id")
            new_item = not bson.ObjectId.is_valid(id)
            if new_item:
                id = ObjectId()
                print("New component", id)
            else:
                id = ObjectId(id)
                print("Older component", id)


            ## Pokud neni zarazen do zadne kategorie dat ho do Nezarazeno

            print("KATEGORIE:", new_json['category'])
            for i, cat in enumerate(new_json['category']):
                print(cat, type(cat))
                new_json['category'][i] = bson.ObjectId(cat)

            if len(new_json['category']) == 0:
                new_json['category'] += bson.ObjectId('5a68f0522208c4a21e2aa99c')


            if new_json.get('barcode', [False])[0] == "":
                print("BARCODE id", id, str(int(str(id), 16)))
                #new_json['barcode'] = [self.barcode(str(id))]
                new_json['barcode'] = [str(int(str(id), 16))]
            else:
                new_json.pop('barcode')


            print("Update product with parameters:", ObjectId(id))
            #print(json.dumps(new_json, indent=4))
            dout = self.mdb.stock.update(
                    {
                        "_id": ObjectId(id)
                    },{
                        '$set': new_json
                    },upsert=True)
            #else:
            #    dout = self.mdb.stock.insert(new_json)


        elif data == 'update_tag':
            print(">[update_tag]")
            component = self.get_argument('component')
            tag  = self.get_argument('tag')
            state = self.get_argument('state', 'true')  # True nebo False, nastavit nebo odstranit tag
            state = True if state == 'true' else False
            self.LogActivity()
            self.mdb.stock.update({
                    "_id": component
                },{
                    ('$set' if state else '$unset'):{
                        "tags."+tag: {'date': "2018-02-01" }
                    }
                }
            )
            self.LogActivity(module = 'store', operation = 'update_tag', data={'tag': tag, 'state': state, 'component': component})
            dout = {'done': True}

        elif data == 'get_categories':

            jstree = bool(self.get_argument('jstree', False))
            print("jstree", jstree, bool(jstree))

            if jstree:
                dbcursor = self.warehouse_get_positions(oid)
                dout = list(dbcursor)
                output = bson.json_util.dumps(dout)

                new = []
                for i, out in enumerate(dout):
                    pos = {}
                    pos['_id'] = str(out['_id'])
                    pos['id'] = str(out['_id'])
                    pos['text'] = out['name'] + " <small>({})</small>".format(out['description'])
                    pos['li_attr'] = {"name": out['name'], 'description': out['description']}
                    pos['parent'] = str(out.get('parent', '#'))
                    new.append(pos)
                dout = bson.json_util.dumps(new)

            else:
                dout = list(self.mdb.category.find({}))

        elif data == 'get_warehouses':
            dout = self.get_warehouseses()

        elif data == 'get_history':
            print("> [get_history]")
            output_type = self.get_argument('output', 'json')
            dbcursor = self.mdb.stock.aggregate([
                    {"$match": {"_id": bson.ObjectId(self.get_argument('key'))}},
                    {"$unwind": '$history'},
                    {"$sort" : {"history._id": -1}},
                    {"$limit": 500}
                ], useCursor = True)
            dout = list(dbcursor)

            print("Output type", output_type)
            if output_type == "html_tab":
                self.set_header('Content-Type', 'text/html; charset=UTF-8')
                self.render('store/store.api.history_tab_view.hbs', dout = dout, parent = self)
                return None

        elif data == 'get_packets':
            print("> [get_packets]")
            output_type = self.get_argument('output', 'json')

            dbcursor = self.mdb.stock.aggregate([
                    {"$match": {"_id": bson.ObjectId(self.get_argument('key'))}},

                    {"$unwind": '$packets'},
                    {"$lookup": {"from": 'stock_operation', "localField":'packets._id', "foreignField": 'pid', "as": 'packets.operations'}},
                    {"$unwind": '$packets.operations'},
                    {"$replaceRoot": { "newRoot": "$packets" }},
                    {"$lookup": {"from": 'store_positions', "localField":'position', "foreignField": '_id', "as": 'position'}},
                    { "$set": { "position": { "$first": "$position" }} },{
                      "$graphLookup": {
                         "from": "store_positions",
                         "startWith": "$position.parent",
                         "connectFromField": "parent",
                         "connectToField": "_id",
                         "as": "position.path"
                      }
                    },
                    {"$set": {"position.path": { "$concatArrays": ["$position.path.name", ["$position.name"]]}} },
                    {"$lookup":
                         {
                           "from": 'warehouse',
                           "localField":'position.warehouse',
                           "foreignField": '_id',
                           "as": 'warehouse'
                         }
                     },
                     { "$set": { "warehouse": { "$first": "$warehouse" }} },
                     { "$group":
                         {
                            "_id": '$_id',
                            "root": { "$first": "$$ROOT" },
                            "operations": { "$push": "$operations" }
                         }
                     },
                    { "$set": { "root.operations": "$operations" } },
                    { "$replaceWith": "$root" },


                     { "$addFields": {
                          "count":  {"$sum": "$operations.count"},
                          "price":
                             { "$function":
                                {
                                   "body": '''function(prices, counts) {
                                     let total_counts = Array.sum(counts);
                                     var tmp_count = total_counts;
                                     var total_price = 0;

                                     var c = counts.reverse();
                                     var p = prices.reverse();

                                     for(i in c){
                                         if(c[i] > 0){
                                             if(c[i] < tmp_count){
                                                 total_price += (c[i]*p[i]);
                                                 tmp_count -= c[i]
                                              }
                                              else{
                                                 total_price += (tmp_count*p[i]);
                                                 tmp_count = 0;
                                              }
                                          }

                                      }
                                      return total_price;

                                   }''',
                                   "args": ["$operations.unit_price", "$operations.count"],
                                   "lang": "js"
                                }
                             }
                        }
                     },
                     { "$sort" : {'_id' : -1} },
                     { "$facet":
                       {
                          "current_warehouse": [{"$match": {"count": {"$ne": 0}}}, {"$match": {'warehouse._id': {"$exists": 1}}}, {"$match": {'warehouse._id': self.get_warehouse().get('_id') }} ],
                          "other_warehouse": [{"$match": {"count": {"$ne": 0}}}, {"$match": {'warehouse._id': {"$exists": 1}}}, {"$match": {'warehouse._id': {"$ne": self.get_warehouse().get('_id') }}} ],
                          "uncategorised": [{"$match": {"count": {"$ne": 0}}}, {"$match": {'warehouse._id': {"$exists": 0}}}],
                          "external_warehouse": [{"$match": {"count": {"$ne": 0}}}, {"$match": {'warehouse.external': {"$exists": 1}}}, {"$match": {'warehouse.external': True}} ],
                          "null": [{"$match": {"count": {"$eq": 0}}}]
                       }
                    }

                ], useCursor = True)
            dout = list(dbcursor)

            if output_type == "html_tab":
                self.set_header('Content-Type', 'text/html; charset=UTF-8')
                # print(dout)
                self.render('store/store.api.packets_tab_view.hbs', dout = dout, parent = self)
                return None

        elif data == 'get_component_docs':
            print("> [get_component_docs]")
            output_type = self.get_argument('output', 'json')

            if output_type == "html_tab":


                dbcursor = self.mdb.stock.aggregate([
                    {"$match": {"_id": bson.ObjectId(self.get_argument('key'))}},

                ], useCursor = True)

                dout = list(dbcursor)
                self.render('store/store.api.component_docs_view.hbs', dout = dout, parent = self)



        elif data == 'update_category':
            self.LogActivity(module = 'store', operation = 'update_category', data={'category': self.get_argument('name')})
            self.mdb.category.update({"name": self.get_argument('name')},
            {
                "name_cs": self.get_argument('name_cs'),
                "description": self.get_argument('description'),
                "path": self.get_argument('path'),
                "name": self.get_argument('name')
            },
            upsert = True)
            dout = {}
            pass

        elif data == 'get_components_requested':
            #status = self.get_argument('status': 5)
            print("Get component requested")
            out = self.mdb.stock.aggregate([
                {"$match": {'history.operation': 'buy_request'}},
                {"$unwind": '$history'},
                {"$match": {'history.operation': 'buy_request'}},
                {"$project": {'history':1, 'supplier':1, 'description': 1, 'name': 1}},
                ])
            dout = list(out)

        elif data == 'search':
            search = self.get_argument('q', '')
            page = self.get_argument('page', '0')
            key = self.get_arguments('key[]')
            if key == []: key = ['_id', 'name', 'description']
            match = list(map(lambda x: {x: { '$regex': search, '$options': 'ix'}}, key ))
            print(key)
            print(match)
            '''
                                    [
                                    {'_id': { '$regex': search, '$options': 'ix'}},
                                    {'name': { '$regex': search, '$options': 'ix'}},
                                    {'description': { '$regex': search, '$options': 'ix'}} ]
            '''


            dbcursor = self.mdb.stock.aggregate([
                {"$unwind": "$_id"},
                {"$sort" : {"category": 1,"_id": 1} },
                {"$match": {'$or':match}
                },{
                    "$lookup":{
                        "from": "category",
                        "localField": "category",
                        "foreignField": "name",
                        "as": "category"
                    }
                },{
                    '$skip' : int(50)*int(page)
                },{
                    '$limit' : int(50)
                }], useCursor=True)
            dout = list(dbcursor)

        print("operace:", data)
        output = bson.json_util.dumps(dout)
        self.write(output)


class hand_bi_home(BaseHandler):
    role_module = ['store-access', 'store-sudo', 'store-manager']
    def get(self, data=None):
        cat = list(self.mdb.category.find({}))
        cat = sorted(cat, key = lambda x: x.get('path', '/')+x['name'])

        if self.is_authorized(['sudo-stock', 'sudo', 'stock', 'stock-admin']):
            self.render("store/store.home.hbs", title="UST intranet", parent=self, category = cat, cart = self.cart)
        else:
            self.render("store/store.home.hbs", title="UST intranet", parent=self, category = cat, cart = self.cart)
        print("..................")
        print(self.get_warehouseses())

class operation(BaseHandler):
    role_module = ['store-sudo', 'store-manager']
    def post(self, data=None):

        id_wh = bson.ObjectId(self.get_cookie('warehouse', False))
        id = bson.ObjectId(self.get_argument('component', False))

        # mtoda service slouží k uprave poctu polozek ve skladu. Je jedno, jsetli to tam je, nebo neni...
        if data == 'service':
            id = bson.ObjectId(self.get_argument('component'))
            article = list(self.mdb.stock.find_one({'_id': id}))
            counts = self.component_get_counts(id)
            stock = self.get_warehouse()
            print(counts)
            self.render("store/store.comp_operation.service.hbs", last = article, counts = counts, stock = stock)

        elif data == 'service_push': # vlozeni 'service do skladu'
            id = bson.ObjectId(self.get_argument('component'))
            #stock_list = self.get_warehouseses()
            stock = (self.get_warehouse()['_id'])
            description = self.get_argument('description', '')
            bilance = self.get_argument('offset')
            bilance = bilance.replace(",", ".").strip()


            if '=' == bilance[0]:
                counts = self.component_get_counts(id)['stocks'][str(stock)]['count']['onstock']
                bilance = float(bilance[1:]) - counts
                description += "oprava z %d na %d ks".format(counts, bilance)

            print("service_push >>", id, stock, description, float(bilance))
            out = self.mdb.stock.update(
                    {'_id': id},
                    {'$push': {'history':
                        {'_id': bson.ObjectId(), 'stock': stock, 'operation': 'service', 'bilance': float(bilance),  'description':description, 'user':self.logged}
                    }}
                )
            self.LogActivity('store', 'operation_service')
            self.write("ACK");


        #nakup jedne polozky do skladu. Musi obsahovat: cena za ks, pocet ks, obchod, faktura, ...
        elif data == 'buy':

            id = bson.ObjectId(self.get_argument('component'))
            article = self.mdb.stock.find_one({'_id': id})
            # places = list(self.mdb.store_positions.find().sort([('name', 1)]))
            # print("Skladovj pozice", places)
            # counts = self.mdb.stock.aggregate([
            #     {"$match": {"_id": id}},
            #     {"$unwind": "$history"},
            #     {"$group": { "_id": "$history.stock", "count": { "$sum": "$history.bilance" }}},
            #     {"$lookup": {"from": "store_positions", "localField": '_id', "foreignField" : '_id', "as": "position"}}
            # ])

            stocks = self.get_warehouseses()
            request = self.component_get_buyrequests(id)
            print("Pozadavky na nakup", request)
            self.render("store/store.comp_operation.buy.hbs", article = article, stocks = stocks, request = request)

        elif data == 'buy_push': # vlozeni 'service do skladu'
            comp = self.get_argument('component')
            ctype = self.get_argument('type', None)
            supplier = self.get_argument('supplier', None)
            position = self.get_argument('position')
            packet = self.get_argument('packet')
            description = self.get_argument('description', '')
            description_operation = self.get_argument('description_operation', '')
            bilance = self.get_argument('count', 0)
            bilance_plan = self.get_argument('count_planned', None)
            invoice = self.get_argument('invoice', None)
            price = self.get_argument('price')
            request = self.get_argument('request')

            new_packet = False
            if packet == 'new':
                new_packet = True
                packet_id = ObjectId()
            else:
                packet_id = ObjectId(packet)

            if position == "None":
                position = None
            else:
                position = ObjectId(position)

            query_data = {'_id': bson.ObjectId(comp)}
            packet_data = {}

            # Pokud zakladam novy packet
            if new_packet:
                packet_data = {'$push':
                        {
                        'packets':
                        {
                            '_id': packet_id,
                            'type': 'zip_bag',
                            'supplier': supplier,
                            # 'count': float(bilance),
                            #'reserved': 0,
                            'position': position,
                            'description': description,
                            'operations': [
                                {
                                    'count': float(bilance),
                                    'unit_price': float(price),
                                    'type': 'buy',
                                    'date': datetime.datetime.now(),
                                    'user': self.logged,
                                    'invoice': invoice,
                                    'supplier': supplier,
                                    'description': description_operation,
                                }
                            ]
                        }
                      }
                    }
                out = self.mdb.stock.update(query_data, packet_data)
                print("Pridavam sacek", out)

            # Pridavam do existujiciho packetu
            #else:
            #    packet_data = {}

            # Pokud se jedna o nakup a ma se naskladnit
            if request == 'false':
                invoice = bson.ObjectId(invoice)
                id = bson.ObjectId()

                out = self.mdb.stock.update(query_data,
                    {
                    '$push':
                        {
                        'history':
                            {
                            '_id': id,
                            'packet': packet_id,
                            'operation': 'buy',
                            'supplier': supplier,
                            'type': ctype,
                            'bilance': float(bilance),
                            'bilance_plan': bilance_plan,
                            'price': float(price),
                            'invoice': invoice,
                            'description': description,
                            'user': self.logged
                            }
                        }
                    }
                    )
                print("buy_push >>", comp, position, packet, description, bilance, invoice, price)

                self.LogActivity('store', 'operation_service')

            # Pokud vytvarime pozadavek na koupi polozky
            else:
                out = self.mdb.stock.update(
                    {'_id': bson.ObjectId(comp)},
                    {'$push': {'history':
                        {'_id': id, 'operation':'buy_request', 'bilance': float(bilance), 'description':description, 'user':self.logged, 'status': 0}
                    }}
                )
                self.LogActivity('store', 'Created request')
            self.write(out)

        ## Move components from place to place...
        elif data == 'move':
            id = bson.ObjectId(self.get_argument('component'))
            self.component_update_counts(id)
            stock = self.get_warehouse()
            print("")

            current_places = self.component_get_counts(id)
            print("CURRENT...")
            print(bson.json_util.dumps(current_places))
            places = self.get_warehouseses()

            current_places = self.component_get_positions(id, stock = id_wh)
            print("PLACES...", current_places)
            self.render('store/store.comp_operation.move.hbs', stock = stock, all_places=places)

        elif data == 'move_push':
            comp = self.get_argument("component")
            source = self.get_argument("source")
            target = self.get_argument("target")
            count = self.get_argument("count")
            description = self.get_argument("description")

            ida = bson.ObjectId()
            idb = bson.ObjectId()

            print("move_push >>", comp, source, target, count, description)
            out = self.mdb.stock.update(
                {'_id': bson.ObjectId(comp)},
                {'$push': {'history':
                    {'_id': ida, 'stock': bson.ObjectId(source), 'operation':'move_out', 'bilance': -float(count), 'price': 0, 'description':description, 'user':self.logged},
                }}
            )
            out = self.mdb.stock.update(
                {'_id': bson.ObjectId(comp)},
                {'$push': {'history':
                    {'_id': idb, 'stock': bson.ObjectId(target), 'operation':'move_in', 'bilance': float(count), 'price': 0, 'description':description, 'user':self.logged},
                }}
            )

        ##
        ## Funkce pro nastaveni vychozich pozic ve skladech.
        ##
        elif data == 'setposition':
            id = bson.ObjectId(self.get_argument('component'))
            current_places = self.component_get_positions(id, stock = bson.ObjectId(self.get_cookie('warehouse', False)))
            all_places = self.component_get_positions(id, stock = False)
            print(bson.json_util.dumps(current_places))
            print(bson.json_util.dumps(all_places))
            places = list(self.mdb.store_positions.find({'warehouse': bson.ObjectId(self.get_cookie('warehouse', False))}).sort([('name', 1)]))
            print(bson.json_util.dumps(places))
            self.render("store/store.comp_operation.setposition.hbs", current_places = current_places, all_places = places, all_positions = all_places, stock_positions = [])

        elif data == 'setposition_push':
            id = bson.ObjectId(self.get_argument('component'))
            type = self.get_argument('type')
            position = bson.ObjectId(self.get_argument('position'))

            if type == 'add':
                print("Add position")
                self.component_set_position(id, position, False)
            elif type == 'change':
                print("change position")
                self.component_set_position(id, position, True)
            elif type == 'remove':
                self.component_remove_position(id, position)
            else:
                self.write("Err")

            self.LogActivity('store', 'operation_setposition')
            self.write("ACK");

        ## Nastaveni dodavatelu pro polozku
        elif data == 'supplier':
            suppliers = self.component_get_suppliers(id)
            self.render('store/store.comp_operation.supplier.hbs', suppliers = suppliers)

        elif data == 'supplier_push':
            id = bson.ObjectId(self.get_argument('component'))
            order = int(self.get_argument('supplier_id'))
            supplier = self.get_argument('supplier')
            symbol = self.get_argument('symbol')
            code = self.get_argument('code')
            url = self.get_argument('url')

            if order < 0:
                # nova polozka
                out = self.mdb.stock.update({'_id': id}, {
                    "$push": {"supplier": {'supplier':supplier, 'symbol':symbol, 'barcode':code, 'url':url}}
                })
            else:
                out = self.mdb.stock.update({'_id': id}, {
                    "$set": {"supplier.{}".format(order): {'supplier':supplier, 'symbol':symbol, 'barcode':code, 'url':url}}
                })
            self.write(out)

        else:
            self.write('''
                <h2>Zatim nepodporovana operace {} s polozkou {}</h2>
            '''.format(data, self.get_argument('component')))

class newprint(BaseHandler):
    role_module = ['store-access', 'store-sudo', 'store-manager']
    def post(self, data=None):
        comp = self.get_arguments('component')
        if self.get_argument('cart', False):
            l = list(self.mdb.carts.find({'_id': bson.ObjectId(self.get_argument('cart'))}))[0]['cart']
            comp = [d['id'] for d in l if 'id' in d]
            print(comp)

        print("Zahajuji generovani PDF")
        print("Soucastky", comp)
        comp = [ObjectId(x) for x in comp]
        comp = list(self.mdb.stock.find({'_id' : {'$in' : comp}}))
        print("......................")
        print(comp)
        pdf = stickers_simple(comp = comp, store = self.get_current_user()['param']['warehouse_info'], pozice = self.component_get_positions)
        pdf.output("static/tmp/sestava.pdf")

        with open('static/tmp/sestava.pdf', 'rb') as f:
            self.set_header("Content-Type", 'application/pdf; charset="utf-8"')
            self.set_header("Content-Disposition", "inline; filename=UST_tiskova_sestava.pdf")
            self.write(f.read())
        f.close()



def stickers_simple(col = 3, rows = 7, skip = 0, comp = [], store = None, pozice = None):
    page = 0
    page_cols = col
    page_rows = rows
    page_cells = page_cols * page_rows
    cell_w = 210/page_cols
    cell_h = 297/page_rows

    stock_identificator = store

    print ("pozadovany format je 70x42")
    pdf = FPDF('P', 'mm', format='A4')

    pdf.add_font('pt_sans', '', 'static/pt_sans/PT_Sans-Web-Regular.ttf', uni=True)
    pdf.add_font('pt_sans-bold', '', 'static/pt_sans/PT_Sans-Web-Bold.ttf', uni=True)
    pdf.set_font('pt_sans-bold', '', 12)

    pdf.set_auto_page_break(False)
    pdf.add_page()

    for i, component in enumerate(comp):
        i += skip
        #   id = component['name'].strip().replace('/', '_')
        id = str(component['_id'])
        barcode = str(int(id, 16))
        code128.image(barcode).save("static/tmp/barcode/%s.png"%(id))

        if i != 0 and i%(page_cells) == 0:
            page += 1
            pdf.add_page()
            print("New PAGE --- ", i, i%page_cells)

        row = int(i/page_cols)-page*page_rows
        column = i%page_cols
        cell_x = column*cell_w
        cell_y = row*cell_h

        pdf.set_xy(cell_x+3, cell_y+6.75)
        if len(component['name'])<23:
            pdf.set_font('pt_sans-bold', '', 14)
        else:
            pdf.set_font('pt_sans-bold', '', 10)
        pdf.cell(cell_w-10, 0, component['name'][:35])
        pdf.set_xy(cell_x+1, cell_y+9)
        pdf.image('static/tmp/barcode/%s.png'%(id), w = cell_w-2, h=6)

        pdf.set_font('pt_sans', '', 9.5)
        pdf.set_xy(cell_x+3, cell_y+22)
        try:
            pdf.multi_cell(cell_w-6, 3.4, component['description'][:190])
        except Exception as e:
            pdf.multi_cell(cell_w-10, 5, "ERR" + repr(e))

        #pdf.set_xy(cell_x+3, cell_y+12)
        #pdf.set_font('pt_sans', '', 7.5)
        #pdf.cell(cell_w-10, 10, id + " | " + str(datetime.date.today()) )

        pos = pozice(bson.ObjectId(id), stock = stock_identificator['_id'], primary = True)
        if len(pos) > 0:
            pos = pos[0]['info'][0]['name']
            print("POZ", pos)
        else:
            pos = ""
        pdf.set_font('pt_sans', '', 7.5)
        #pdf.set_xy(cell_x+3, cell_y+15)
        #pdf.cell(cell_w-10, 10, str(stock_identificator['code']) + " | " + str(pos) + " | " + ','.join(component['category']))

        pdf.set_xy(cell_x+3, cell_y+12)
        #pdf.cell(cell_w-10, 10, str(datetime.date.today()) + " | " + ','.join(component['category']))
        pdf.cell(cell_w-10, 10, str(datetime.date.today()))

        pdf.set_xy(cell_x+3, cell_y+15)
        pdf.cell(cell_w-10, 10, str(stock_identificator['code']) + " | " + str(pos))

        print("Generovani pozice...")
    return pdf


class print_layout(BaseHandler):
    role_module = ['store-access', 'store-sudo', 'store-manager']
    def get(self, data = None):
        out_type = self.get_argument('type', 'html')
        components = []
        components = self.get_query_arguments('action[]', [])
        multiply = int(self.get_argument('multiply', 5))
        layout = self.get_argument('template', '70x40_simple')
        skip = int(self.get_argument('skip', 0))
        #print("Soucastky..",components)
        if len(components) > 0:
            comp = list(self.mdb.stock.find({'_id' : {'$in' : components}}))
        else:
            comp = list(self.mdb.stock.find().sort([("category", 1), ("_id",1)]))
        page = 0
        #print("Budeme tisknout:", comp)

        if layout == 'souhrn_01':
            autori = self.get_query_argument('autor', None)
            if not autori: autori = ['autory vlozite pridanim autoru do adresy s parametrem "autor"', 'autoru muze byt vice, pouzijte vice parametru', 'Například pridanim tohoto na konec adresy: &autor=Tester První']
            datum = self.get_argument('datum', ">>pro specifikovani pridejte parametr 'datum' do GET parametru<<")
            page = 1
            money_sum = 0
            Err = []

            print ("pozadovany format je:", layout)
            pdf = FPDF('P', 'mm', format='A4')
            pdf.set_auto_page_break(False)

            pdf.add_font('pt_sans', '', 'static/pt_sans/PT_Sans-Web-Regular.ttf', uni=True)
            pdf.add_font('pt_sans-bold', '', 'static/pt_sans/PT_Sans-Web-Bold.ttf', uni=True)
            pdf.set_font('pt_sans', '', 12)
            pdf.add_page()

            pdf.set_xy(0, 40)
            pdf.cell(pdf.w, 0, 'Celkový přehled skladu', align='C', ln=2)
            pdf.set_xy(0, 46)
            pdf.cell(pdf.w, 0, 'Universal Scientific Technologies s.r.o.', align='C', ln=2)

            pdf.set_xy(20, 200)
            pdf.cell(1,0, 'Inventuru provedli:', ln=2)
            for x in autori:
                pdf.cell(1,20, x, ln=2)

            pdf.set_font('pt_sans', '', 8)
            pdf.set_xy(120, 288)
            pdf.cell(10, 0, "Generováno %s, strana %s z %s" %(datetime.datetime.now(), page, pdf.alias_nb_pages()) )

            pdf.add_page()


            data = self.mdb.stock.aggregate([
                    {'$addFields': {'count': {'$sum': '$history.bilance'}}}
                ])


            gen_time = datetime.datetime(2018, 10, 1)
            lastOid = ObjectId.from_datetime(gen_time)


            for i, component in enumerate(data):
            #for i, component in enumerate(list(data)[:30]):
                print(i, "=============================")
                print(component['_id'])
                try:
                    ## Pokud je konec stránky
                    if pdf.get_y() > pdf.h-20:
                        pdf.line(10, pdf.get_y()+0.5, pdf.w-10, pdf.get_y()+0.5)

                        pdf.set_font('pt_sans', '', 10)
                        pdf.set_xy(150, pdf.get_y()+1)
                        pdf.cell(100, 5, 'Součet strany: {:6.2f} Kč'.format(page_sum))

                        pdf.add_page()

                    ## Pokud je nová strana
                    if page != pdf.page_no():
                        pdf.set_font('pt_sans', '', 8)
                        page = pdf.page_no()
                        pdf.set_xy(120, 288)
                        pdf.cell(10, 0, "Generováno %s, strana %s z %s" %(datetime.datetime.now(), page, pdf.alias_nb_pages()) )

                        pdf.set_font('pt_sans', '', 11)
                        pdf.set_xy(10, 10)
                        pdf.cell(100, 5, 'Skladová položka')
                        pdf.set_x(95)
                        pdf.cell(10, 5, "Počet kusů", align='R')
                        pdf.set_x(120)
                        pdf.cell(10, 5, "Cena za 1ks", align='R')
                        pdf.set_x(180)
                        pdf.cell(10, 5, "Cena položky (bez DPH)", align='R', ln=2)
                        pdf.line(10, 15, pdf.w-10, 15)
                        pdf.set_y(18)
                        page_sum = 0

                    pdf.set_font('pt_sans', '', 10)

                    count = component['count']

                    if count >0:
                        price = 0
                        price_ks = 0
                        first_price = 0


                        pdf.set_x(10)
                        pdf.cell(100, 5, component['_id'])

                        pdf.set_x(95)
                        pdf.cell(10, 5, "%5.d" %(count), align='R')

                    pdf.set_x(10)
                    pdf.cell(100, 5, "{:5.0f}  {}".format(i, component['_id']))


                    inventura = False
                    for x in reversed(component.get('history', [])):
                        if x.get('operation', None) == 'inventory':
                            print("inventura", x)
                            if x['_id'].generation_time > lastOid.generation_time:
                                print("#############")
                                inventura = True
                                count = x['absolute']

                                pdf.set_x(110)
                                pdf.cell(1, 5, "i")
                                break;

                    pdf.set_font('pt_sans', '', 10)
                    pdf.set_x(95)
                    pdf.cell(10, 5, "{} j".format(count), align='R')

                    rest = count

                    for x in reversed(component.get('history', [])):

                        if x.get('price', 0) > 0:
                            if first_price == 0:
                                first_price = x['price']
                            if x['bilance'] > 0:
                                if x['bilance'] <= rest:
                                    price += x['price']*x['bilance']
                                    rest -= x['bilance']
                                else:
                                    price += x['price']*rest
                                    rest = 0

                    print("Zbývá", rest, "ks, secteno", count-rest, "za cenu", price)
                    if(count-rest): price += rest*first_price
                    money_sum += price
                    page_sum +=price

                    if price == 0.0 and x.get('count', 0) > 0:
                        Err.append('Polozka >%s< nulová cena, nenulový počet' %(component['_id']))

                    pdf.set_x(120)
                    if count > 0: pdf.cell(10, 5, "%6.2f Kč" %(price/count), align='R')
                    else: pdf.cell(10, 5, "%6.2f Kč" %(0), align='R')

                    pdf.set_font('pt_sans-bold', '', 10)
                    pdf.set_x(180)
                    pdf.cell(10, 5, "%6.2f Kč" %(price), align='R')


                except Exception as e:
                    Err.append('Err' + repr(e) + component['_id'])
                    print(e)

                pdf.set_y(pdf.get_y()+4)

            pdf.line(10, pdf.get_y(), pdf.w-10, pdf.get_y())
            pdf.set_font('pt_sans', '', 8)
            pdf.set_x(180)
            pdf.cell(10, 5, "Konec souhrnu", align='R')

            pdf.set_font('pt_sans', '', 10)
            pdf.set_xy(150, pdf.get_y()+3)
            pdf.cell(100, 5, 'Součet strany: {:6.2f} Kč'.format(page_sum))

            pdf.page = 1
            pdf.set_xy(20,175)
            pdf.set_font('pt_sans', '', 12)
            pdf.cell(20,20, "Cena skladových zásob k %s je %0.2f Kč (bez DPH)" %(datum, money_sum))
            if len(Err) > 0:
                pdf.set_xy(30,80)
                pdf.cell(1,6,"Pozor, chyby ve skladu:", ln=2)
                pdf.set_x(32)
                for ch in Err:
                    pdf.cell(1,5,ch,ln=2)
            pdf.page = page

            print(autori)



        if layout == '105x74_simple':
            page = 0
            page_cols = 2
            page_rows = 4
            page_cells = page_cols * page_rows
            cell_w = 105
            cell_h = 75

            print ("pozadovany format je:", layout)
            pdf = FPDF('P', 'mm', format='A4')

            pdf.add_font('pt_sans', '', 'static/pt_sans/PT_Sans-Web-Regular.ttf', uni=True)
            pdf.add_font('pt_sans-bold', '', 'static/pt_sans/PT_Sans-Web-Bold.ttf', uni=True)
            pdf.set_font('pt_sans-bold', '', 12)

            pdf.set_auto_page_break(False)
            pdf.add_page()

            for i, component in enumerate(comp):
                i += skip
                id = component['_id'].strip().replace('/', '')
                code128.image(component['_id']).save("static/barcode/%s.png"%(id))

                if i != 0 and i%(page_cells) == 0:
                    page += 1
                    pdf.add_page()
                    print("New PAGE --- ", i, i%page_cells)

                row = int(i/page_cols)-page*page_rows
                column = i%page_cols
                cell_x = column*cell_w
                cell_y = row*cell_h

                print(component)
                pdf.set_font('pt_sans-bold', '', 14)
                pdf.set_xy(cell_x+5, cell_y+5)
                pdf.cell(cell_w-10, 0, component['_id'])
                pdf.set_xy(cell_x, cell_y+10)
                pdf.image('static/barcode/%s.png'%(id), w = cell_w, h=10)

                pdf.set_font('pt_sans', '', 11)
                pdf.set_xy(cell_x+5, cell_y+23)
                try:
                    pdf.multi_cell(cell_w-10, 5, component['description'])
                except Exception as e:
                    pdf.multi_cell(cell_w-10, 5, "ERR" + repr(e))


                pdf.set_xy(cell_x+5, cell_y+cell_h-15)
                pdf.set_font('pt_sans', '', 8)
                pdf.cell(cell_w-10, 10, ', '.join(component['category']) + "  |  " + str(datetime.datetime.now()) + "  |  " + "UST")


        if layout == '70x42-3_simple':
            page = 0
            page_cols = 3
            page_rows = 7
            page_cells = page_cols * page_rows
            cell_w = 210/page_cols
            cell_h = 297/page_rows


            print ("pozadovany format je:", layout)
            pdf = FPDF('P', 'mm', format='A4')

            pdf.add_font('pt_sans', '', 'static/pt_sans/PT_Sans-Web-Regular.ttf', uni=True)
            pdf.add_font('pt_sans-bold', '', 'static/pt_sans/PT_Sans-Web-Bold.ttf', uni=True)
            pdf.set_font('pt_sans-bold', '', 12)

            pdf.set_auto_page_break(False)
            pdf.add_page()

            for i, component in enumerate(comp):
                i += skip
                id = component['name'].strip().replace('/', '_')
                code128.image(component['_id']).save("static/barcode/%s.png"%(id))

                if i != 0 and i%(page_cells) == 0:
                    page += 1
                    pdf.add_page()
                    print("New PAGE --- ", i, i%page_cells)

                row = int(i/page_cols)-page*page_rows
                column = i%page_cols
                cell_x = column*cell_w
                cell_y = row*cell_h

                pdf.set_xy(cell_x+5, cell_y+6.75)
                if len(component['name'])<23:
                    pdf.set_font('pt_sans-bold', '', 14)
                else:
                    pdf.set_font('pt_sans-bold', '', 10)
                pdf.cell(cell_w-10, 0, component['name'][:35])
                pdf.set_xy(cell_x+2.5, cell_y+9)
                pdf.image('static/barcode/%s.png'%(id), w = cell_w-5, h=7)

                pdf.set_font('pt_sans', '', 11)
                pdf.set_xy(cell_x+4, cell_y+20)
                try:
                    pdf.multi_cell(cell_w-8, 4, component['description'][:185])
                except Exception as e:
                    pdf.multi_cell(cell_w-10, 5, "ERR" + repr(e))


                pdf.set_xy(cell_x+5, cell_y+cell_h-7)
                pdf.set_xy(cell_x+5, cell_y+13)
                pdf.set_font('pt_sans', '', 7.5)
                pdf.cell(cell_w-10, 10, ', '.join(component['category']) + " |" + str(datetime.date.today()) + "| " + component['_id'])



        if layout == '105x48_simple':
            page = 0
            page_cols = 2
            page_rows = 6
            page_cells = page_cols * page_rows
            #cell_w = 105
            #cell_h = 48
            cell_w = 210/page_cols
            cell_h = 297/page_rows

            print ("pozadovany format je:", layout)
            pdf = FPDF('P', 'mm', format='A4')

            pdf.add_font('pt_sans', '', 'static/pt_sans/PT_Sans-Web-Regular.ttf', uni=True)
            pdf.add_font('pt_sans-bold', '', 'static/pt_sans/PT_Sans-Web-Bold.ttf', uni=True)
            pdf.set_font('pt_sans-bold', '', 12)

            pdf.set_auto_page_break(False)
            pdf.add_page()

            for i, component in enumerate(comp):
                i += skip
                id = component['_id'].strip().replace('/', '')
                code128.image(component['_id']).save("static/barcode/%s.png"%(id))

                if i != 0 and i%(page_cells) == 0:
                    page += 1
                    pdf.add_page()
                    print("New PAGE --- ", i, i%page_cells)

                row = int(i/page_cols)-page*page_rows
                column = i%page_cols
                cell_x = column*cell_w
                cell_y = row*cell_h

                print(component)
                pdf.set_font('pt_sans-bold', '', 14)
                pdf.set_xy(cell_x+5, cell_y+5)
                pdf.cell(cell_w-10, 0, component['_id'])
                pdf.set_xy(cell_x, cell_y+10)
                pdf.image('static/barcode/%s.png'%(id), w = cell_w, h=10)

                pdf.set_font('pt_sans', '', 10)
                pdf.set_xy(cell_x+5, cell_y+20)
                try:
                    pdf.multi_cell(cell_w-10, 4, component['description'][:275])
                except Exception as e:
                    pdf.multi_cell(cell_w-10, 4, "ERR" + repr(e))


                pdf.set_xy(cell_x+5, cell_y+cell_h-10)
                pdf.set_font('pt_sans', '', 8)
                pdf.cell(cell_w-10, 10, ', '.join(component['category']) + "  |  " + str(datetime.datetime.now()) + "  |  " + "UST")


        elif layout == '105x48_panorama':
            page = 0
            page_cols = 6
            page_rows = 2
            page_cells = page_cols * page_rows
            cell_w = 48
            cell_h = 105

            print ("pozadovany format je:", layout)
            pdf = FPDF('L', 'mm', format='A4')

            pdf.add_font('pt_sans', '', 'static/pt_sans/PT_Sans-Web-Regular.ttf', uni=True)
            pdf.add_font('pt_sans-bold', '', 'static/pt_sans/PT_Sans-Web-Bold.ttf', uni=True)
            pdf.set_font('pt_sans-bold', '', 12)

            pdf.set_auto_page_break(False)
            pdf.add_page()

            for i, component in enumerate(comp):
                i += skip
                id = component['_id'].strip().replace('/', '')
                code128.image(component['_id']).save("static/barcode/%s.png"%(id))

                if i != 0 and i%(page_cells) == 0:
                    page += 1
                    pdf.add_page()
                    print("New PAGE --- ", i, i%page_cells)

                row = int(i/page_cols)-page*page_rows
                column = i%page_cols
                cell_x = column*cell_w
                cell_y = row*cell_h

                print(component)
                pdf.set_font('pt_sans-bold', '', 14)
                pdf.set_xy(cell_x+5, cell_y+5)
                pdf.cell(cell_w-10, 0, component['_id'])
                pdf.set_xy(cell_x, cell_y+cell_h)
                pdf.rotate(90)
                pdf.image('static/barcode/%s.png'%(id), w = cell_h-5, h=10)
                pdf.rotate(0)

                pdf.set_font('pt_sans', '', 11)
                pdf.set_xy(cell_x+8, cell_y+20)
                try:
                    pdf.multi_cell(cell_w-10, 5, component['description'])
                except Exception as e:
                    pdf.multi_cell(cell_w-10, 5, "ERR" + repr(e))


                pdf.set_xy(cell_x+5, cell_y+cell_h-15)
                pdf.set_font('pt_sans', '', 8)
                pdf.cell(cell_w-10, 10, ', '.join(component['category']) + "  |  " + str(datetime.datetime.now()) + "  |  " + "UST")



        pdf.output("static/tmp/sestava.pdf")
        with open('static/tmp/sestava.pdf', 'rb') as f:
            self.set_header("Content-Type", 'application/pdf; charset="utf-8"')
            self.set_header("Content-Disposition", "inline; filename=UST_tiskova_sestava.pdf")
            self.write(f.read())
        f.close()
