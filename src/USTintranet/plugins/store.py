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
        dout = []

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


        dbcursor = self.mdb.stock.aggregate(agq, useCursor=True)
        dout = {}
        dout['count'] = count
        dout['data'] = list(dbcursor)

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

class api(BaseHandler):
    def post(self, data=None):
        self.set_header('Content-Type', 'application/json')
        #print(">>", data)
        #print(self.request.arguments)

        if data == 'product':
            print(self.request.arguments.get('selected[]', None))

            dout = list(self.mdb.stock.aggregate([
                    {
                        '$match': {self.get_argument('key', '_id'): ObjectId(self.get_argument('value', ''))}
                    },{
                        '$addFields': {'price_buy_last': {'$avg':{'$slice' : ['$history.price', -1]}}}
                        # tady avg je jen z duvodu, aby to nevracelo pole ale rovnou cislo ($slice vraci pole o jednom elementu)
                    },{
                        '$addFields': {'price_buy_avg': {'$avg': '$history.price'}}

                    },{
                        '$addFields': {'count': {'$sum': '$history.bilance'}}

                    }
                ]))

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
            id = self.get_argument('id')

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

            print("Update product with parameters:")
            print(new_json)

            id =new_json.pop("_id")
            new_item = not bson.ObjectId.is_valid(id)
            if new_item:
                id = ObjectId()
                print("NOVA POLOZKA", id)
            else:
                id = ObjectId(id)
                print("EXISTUJICI POLOZKA", id)


            ## Pokud neni zarazen do zadne kategorie dat ho do Nezarazeno
            if len(new_json['category']) == 0:
                new_json['category'] += ['Nezařazeno']

            if not 'barcode' in new_json:
                new_json['Barcode'] = [self.barcode(str(id))]


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
                self.render('store.api.history_tab_view.hbs', dout = dout)
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
            self.render("store.home.hbs", title="UST intranet", parent=self, category = cat, cart = self.cart)
        else:
            self.render("store.home.hbs", title="UST intranet", parent=self, category = cat, cart = self.cart)


class operation(BaseHandler):
    def post(self, data=None):

        # emtoda service slouží k uprave poctu polozek ve skladu. Je jedno, jsetli to tam je, nebo neni...
        if data == 'service':
            comp = self.get_argument('component')

            article = list(self.mdb.stock.find({'_id': bson.ObjectId(comp)}))[0]
            counts = list(self.mdb.stock.aggregate([
                    {
                        '$match':{ "_id": bson.ObjectId(comp)}
                    },{
                        '$unwind': '$history'
                    },{
                        '$group':{
                            '_id': '$history.stock',
                            'count': {"$sum": '$history.bilance'}
                        }
                    }]))
            self.render("store.comp_operation.{}.hbs".format(data), last = article, counts = counts)

        elif data == 'service_push': # vlozeni 'service do skladu'
            comp = self.get_argument('component')
            stock = self.get_argument('stock')
            description = self.get_argument('description', '')
            bilance = self.get_argument('offset')

            print("service_push >>", comp, stock, description, bilance)
            out = self.mdb.stock.update(
                    {'_id': bson.ObjectId(comp)},
                    {'$push': {'history':
                        {'_id': bson.ObjectId(), 'stock': stock, 'operation': 'service', 'bilance': float(bilance),  'description':description, 'user':self.logged}
                    }}
                )
            self.LogActivity('store', 'operation_service')
            self.write("ACK");


        #nakup jedne polozky do skladu. Musi obsahovat: cena za ks, pocet ks, obchod, faktura, ...
        elif data == 'buy':
            comp = self.get_argument('component')
            article = list(self.mdb.stock.find({'_id': bson.ObjectId(comp)}))[0]
            places = list(self.mdb.store_positions.find().sort([('name', 1)]))
            print("Skladovj pozice", places)
            counts = list(self.mdb.stock.aggregate([
                    {
                        '$match':{ "_id": bson.ObjectId(comp)}
                    },{
                        '$unwind': '$history'
                    },{
                        '$group':{
                            '_id': '$history.stock',
                            'count': {"$sum": '$history.bilance'}
                        }
                    }]))

            self.render("store.comp_operation.{}.hbs".format(data), article = article, counts = counts, places = places)

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

            invoice = bson.ObjectId(invoice)
            id = bson.ObjectId()

            print("buy_push >>", comp, stock, description, bilance, invoice, price)
            out = self.mdb.stock.update(
                    {'_id': bson.ObjectId(comp)},
                    {'$push': {'history':
                        {'_id': id, 'stock': stock, 'operation':'buy', 'supplier': supplier, 'type': ctype, 'bilance': float(bilance), 'bilance_plan': bilance_plan, 'price': float(price), 'invoice': invoice,  'description':description, 'user':self.logged}
                    }}
                )
            self.LogActivity('store', 'operation_service')
            self.write(out)

        ## Move components from place to place...
        elif data == 'move':
            id = bson.ObjectId(self.get_argument('component'))
            current = self.mdb.stock.aggregate([
                {"$match": {"_id": id}},
                {"$unwind": "$history"},
                {"$group": { "_id": "$history.stock", "count": { "$sum": "$history.bilance" }}},
                {"$lookup":
                    {
                        "from": "store_positions",
                        "localField": '_id',
                        "foreignField" : '_id',
                        "as": "position"
            }}])
            places = list(self.mdb.store_positions.find().sort([('name', 1)]))
            self.render('store.comp_operation.move.hbs', current_places = list(current), all_places=places)

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

        print("Zahajuji generovani PDF")
        print("Soucastky", comp)

        comp = self.mdb.stock.find({'_id' : {'$in' : comp}})
        print("......................")
        pdf = stickers_simple(comp = comp)
        pdf.output("static/sestava.pdf")

        with open('static/sestava.pdf', 'rb') as f:
            self.set_header("Content-Type", 'application/pdf; charset="utf-8"')
            self.set_header("Content-Disposition", "inline; filename=UST_tiskova_sestava.pdf")
            self.write(f.read())
        f.close()



def stickers_simple(col = 3, rows = 7, skip = 0, comp = []):
    page = 0
    page_cols = col
    page_rows = rows
    page_cells = page_cols * page_rows
    cell_w = 210/page_cols
    cell_h = 297/page_rows


    print ("pozadovany format je 70x42")
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



        pdf.output("static/sestava.pdf")
        with open('static/sestava.pdf', 'rb') as f:
            self.set_header("Content-Type", 'application/pdf; charset="utf-8"')
            self.set_header("Content-Disposition", "inline; filename=UST_tiskova_sestava.pdf")
            self.write(f.read())
        f.close()
