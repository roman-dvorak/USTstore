#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
from . import BaseHandler
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

def make_handlers(module, plugin):
        return [
             (r'/%s' %module, plugin.hand_bi_home),
             (r'/%s/' %module, plugin.hand_bi_home),
             (r'/%s/print/' %module, plugin.print_layout),
             (r'/{}/api/products/'.format(module), plugin.api_products_json),
             (r'/{}/api/get_parameters/list/'.format(module), plugin.api_parameters_list),
             (r'/{}/api/get_positions/list/'.format(module), plugin.api_positions_list),
             (r'/{}/api/set_positions/update/'.format(module), plugin.api_update_position),
             (r'/%s/newprint' %module, plugin.newprint),
             (r'/%s/api/(.*)/' %module, plugin.api),
             (r'/{}/operation/(.*)/'.format(module), plugin.operation)
        ]

def plug_info():
    return{
        "module": "store",
        "name": "Správce skladu",
        "icon": 'icon_sklad.svg'
    }

ascii_list_to_str = lambda input: [x.decode('ascii') for x in input]
ascii_list_to_str = lambda input: [str(x, 'utf-8') for x in input]




class api_products_json(BaseHandler):
    def post(self):
        self.set_header('Content-Type', 'application/json')
        dout = {}

        polarity = '$nin' if (self.request.arguments.get('polarity', ['true'])[0] == b'true') else '$in'
        tag_polarity = not self.request.arguments.get('tag_polarity', b'true')[0] == b'true'
        selected = (self.request.arguments.get('selected[]', []))
        in_stock = self.get_argument('in_stock', 'All')
        page = self.get_argument('page', 0)
        page_len = self.get_argument('page_len', 100)
        search = self.get_argument('search')#.decode('ascii')
        tag_search = self.get_argument('tag_search')#.decode('ascii')
        print("SEARCH", search)
        print("tag polarity", tag_polarity, in_stock)
        dout = {}

        agq = [
            {"$unwind": "$_id"},
            {"$sort" : {"category": 1,"_id": 1} },
            {"$match": {'$or':[
                                {'_id': { '$regex': search, '$options': 'ix'}},
                                {'name': { '$regex': search, '$options': 'ix'}},
                                {'description': { '$regex': search, '$options': 'ix'}} ]}
            },{
                "$match": {'category': {polarity: ascii_list_to_str(selected)}}
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
                    "foreignField": "name",
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

        dbcursor = self.mdb.stock.aggregate(agq)
        dout['data'] = list(dbcursor)
        print(dout['data'])
        dout['count'] = (count)

        dout = bson.json_util.dumps(dout)
        self.write(dout)



class api_parameters_list(BaseHandler):
    def post(self):
        self.set_header('Content-Type', 'application/json')

        search = self.get_argument('term', '')
        print("vyhledavam dle", search)

        agq = [{"$match": {'$or':[
                        {'name': { '$regex': search, '$options': 'ix'}},
                        {'lang.en': { '$regex': search, '$options': 'ix'}},
                        {'lang.cs': { '$regex': search, '$options': 'ix'}}
                    ]}
                }]

        dout = list(self.mdb.parameters.aggregate(agq))

        data = {
            'total_count': len(dout),
            'incomplete_results': False,
            'items': dout,
        }
        self.write(bson.json_util.dumps(data))

# list of positions in current stock
class api_positions_list(BaseHandler):
    def post(self):
        oid = bson.ObjectId(self.get_cookie("warehouse", None))
        self.set_header('Content-Type', 'application/json')
        print(oid)

        dbcursor = self.warehouse_get_positions(oid)
        dout = list(dbcursor)
        output = bson.json_util.dumps(dout)
        self.write(output)

class api_update_position(BaseHandler):
    def post(self):
        data = {'_id': bson.ObjectId(self.get_argument("id", None)),
                'name': self.get_argument('name', 'not_set'),
                'text': self.get_argument('text', 'not_set'),
                'warehouse': bson.ObjectId(self.get_cookie('warehouse'))}

        self.mdb.store_positions.update({'_id': data['_id']}, data, upsert=True)
        self.write("OK")

class api(BaseHandler):
    def post(self, data=None):
        self.set_header('Content-Type', 'application/json')

        if data == 'product':
            print(self.request.arguments.get('selected[]', None))
            #ZDE POSILAT JEN ID jako je to nize....
            id = bson.ObjectId(self.get_argument('value', ''))
            dout = list(self.mdb.stock.aggregate([
                    {'$match': {self.get_argument('key', '_id'): ObjectId(self.get_argument('value', ''))}},
                    {'$addFields': {'price_buy_last': {'$avg':{'$slice' : ['$history.price', -1]}}}
                        # tady 'avg' je jen z duvodu, aby to nevracelo pole ale rovnou cislo ($slice vraci pole o jednom elementu)
                    },
                    {'$addFields': {'price_buy_avg': {'$avg': '$history.price'}}},
                    {'$addFields': {'count': {'$sum': '$history.bilance'}}}
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
            if len(new_json['category']) == 0:
                new_json['category'] += ['Nezařazeno']

            if new_json.get('barcode', [False])[0] == "":
                print("BARCODE id", id, str(int(str(id), 16)))
                #new_json['barcode'] = [self.barcode(str(id))]
                new_json['barcode'] = [str(int(str(id), 16))]
            else:
                new_json.pop('barcode')


            print("Update product with parameters:", ObjectId(id))
            print(json.dumps(new_json, indent=4))
            dout = self.mdb.stock.update(
                    {
                        "_id": ObjectId(id)
                    },{
                        '$set': new_json
                    },upsert=True)
            #else:
            #    dout = self.mdb.stock.insert(new_json)


        elif data == 'update_tag':
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
            dout = list(self.mdb.category.find({}))

        elif data == 'get_history':
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
                print(dout)
                self.render('store/store.api.history_tab_view.hbs', dout = dout)
                return None

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

        output = bson.json_util.dumps(dout)
        self.write(output)


class hand_bi_home(BaseHandler):
    def get(self, data=None):
        cat = list(self.mdb.category.find({}))
        cat = sorted(cat, key = lambda x: x['path']+x['name'])
        permis = self.is_authorized(['sudo-stock', 'sudo', 'stock', 'stock-admin'])
        if permis:
            self.render("store/store.home.hbs", title="UST intranet", parent=self, category = cat, cart = self.cart)
        else:
            self.render("store/store.home.hbs", title="UST intranet", parent=self, category = cat, cart = self.cart)


class operation(BaseHandler):
    def post(self, data=None):

        id_wh = bson.ObjectId(self.get_cookie('warehouse', False))
        id = bson.ObjectId(self.get_argument('component', False))

        # emtoda service slouží k uprave poctu polozek ve skladu. Je jedno, jsetli to tam je, nebo neni...
        if data == 'service':
            id = bson.ObjectId(self.get_argument('component'))

            article = list(self.mdb.stock.find_one({'_id': id}))
            counts= self.component_get_counts(id)
            places = self.get_warehouseses()
            self.render("store/store.comp_operation.service.hbs", last = article, counts = counts, all_places=places)

        elif data == 'service_push': # vlozeni 'service do skladu'
            id = bson.ObjectId(self.get_argument('component'))
            stock = bson.ObjectId(self.get_argument('stock'))
            description = self.get_argument('description', '')
            bilance = self.get_argument('offset')

            print("service_push >>", id, stock, description, bilance)
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

            places = self.component_get_positions(id, stock = id_wh)
            request = self.component_get_buyrequests(id)
            print("Pozadavky na nakup", request)
            self.render("store/store.comp_operation.buy.hbs", article = article, places = places, request = request)

        elif data == 'buy_push': # vlozeni 'service do skladu'
            comp = self.get_argument('component')
            ctype = self.get_argument('type', None)
            supplier = self.get_argument('supplier', None)
            stock = ObjectId(self.get_argument('stock'))
            description = self.get_argument('description', '')
            bilance = self.get_argument('count', 0)
            bilance_plan = self.get_argument('count_planned', None)
            invoice = self.get_argument('invoice', None)
            price = self.get_argument('price')
            request = self.get_argument('request')

            # Pokud se jedna o nakup a ma se naskladnit
            if request == 'false':
                invoice = bson.ObjectId(invoice)
                id = bson.ObjectId()
                out = self.mdb.stock.update(
                        {'_id': bson.ObjectId(comp)},
                        {'$push': {'history':
                            {'_id': id, 'stock': stock, 'operation':'buy', 'supplier': supplier, 'type': ctype, 'bilance': float(bilance), 'bilance_plan': bilance_plan, 'price': float(price), 'invoice': invoice,  'description':description, 'user':self.logged}
                        }}
                    )
                print("buy_push >>", comp, stock, description, bilance, invoice, price)

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

            current_places = self.component_get_counts(id)
            print("CURRENT...")
            print(bson.json_util.dumps(current_places))
            places = self.get_warehouseses()

            current_places = self.component_get_positions(id, stock = id_wh)
            print("PLACES...", current_places)
            self.render('store/store.comp_operation.move.hbs', current_places = current_places, all_places=places)

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
                    {'_id': ida, 'stock': bson.ObjectId(source), 'operation':'move', 'bilance': -float(count), 'price': 0, 'description':description, 'user':self.logged},
                }}
            )
            out = self.mdb.stock.update(
                {'_id': bson.ObjectId(comp)},
                {'$push': {'history':
                    {'_id': idb, 'stock': bson.ObjectId(target), 'operation':'move', 'bilance': float(count), 'price': 0, 'description':description, 'user':self.logged},
                }}
            )

        ##
        ## Funkce pro nastaveni vychozich pozic ve skladech.
        ##
        elif data == 'setposition':
            id = bson.ObjectId(self.get_argument('component'))
            current_places = self.component_get_positions(id, stock = bson.ObjectId(self.get_cookie('warehouse', False)))
            print(bson.json_util.dumps(current_places))
            places = list(self.mdb.store_positions.find({'warehouse': bson.ObjectId(self.get_cookie('warehouse', False))}).sort([('name', 1)]))
            self.render("store/store.comp_operation.setposition.hbs", current_places = current_places, all_places = places, stock_positions = [])

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
            url = self.get_argument('symbol')

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
        pdf.cell(cell_w-10, 10, str(datetime.date.today()) + " | " + ','.join(component['category']))

        pdf.set_xy(cell_x+3, cell_y+15)
        pdf.cell(cell_w-10, 10, str(stock_identificator['code']) + " | " + str(pos))

        print("Generovani pozice...")
    return pdf


class print_layout(BaseHandler):
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
