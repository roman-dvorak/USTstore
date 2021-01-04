#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
from . import BaseHandler, BaseHandlerOwnCloud
from . import save_file, upload_file
#from pyoctopart.octopart import Octopart
import json
import urllib
import bson
from bson import ObjectId
import datetime
import pandas as pd
from fpdf import FPDF
import os
import sys

from plugins.helpers.warehouse import *

sys.path.append("..")
from plugins.store_data.stock_counting import getLastInventory, getPrice, getInventory, getInventoryRecord


def get_plugin_handlers():
        plugin_name = get_plugin_info()["name"]

        return [
             (r'/{}/get_packet/'.format(plugin_name), load_item),
             (r'/{}/save_item/'.format(plugin_name), save_stocktaking),
             (r'/{}/event/(.*)/save'.format(plugin_name), stocktaking_eventsave),
             (r'/{}/event/lock'.format(plugin_name), stocktaking_eventlock),
             (r'/{}/event/generate/basic/(.*)'.format(plugin_name), stocktaking_event_generate_basic),
             (r'/{}/event/(.*)'.format(plugin_name), stocktaking_event),
             (r'/{}/events'.format(plugin_name), stocktaking_events),
             (r'/{}/view/categories'.format(plugin_name), view_categories),
             (r'/{}'.format(plugin_name), home),
             (r'/{}/'.format(plugin_name), home),
        ]

def get_plugin_info():
    #class base_info(object):
    return {
        "name": "stocktaking",
        "entrypoints": [
            {
                "title": "Inventura",
                "url": "/stocktaking",
                "icon": "insert_chart",
            }
        ]
    }


class home(BaseHandler):
    def get(self):
        wrehouse = bson.ObjectId(self.get_cookie('warehouse', False))
        positions = self.warehouse_get_positions(wrehouse)
        current = self.mdb.intranet.find_one({'_id': 'stock_taking'})['current']
        if current: stocktaking_info = self.mdb.stock_taking.find_one({'_id': current})
        else: stocktaking_info = None

        self.render('stocktaking.home.hbs', stocktaking = stocktaking_info, places = positions)


##
##  Trida, pro prehled skladu rozrazeny do kategorii
##
class view_categories(BaseHandler):
    def get(self):
        self.authorized(['inventory'])

        # Ziskat kategorie
        categories = list(self.mdb.category.aggregate([]))

        # Ziskat vsechny sklady
        warehouse = self.get_warehouse()
        warehouses = self.get_warehouseses()

        # seradit kategorie tak, aby to odpovidalo adresarove strukture
        # paths = set()
        # for x in categories:
        #     paths.add(x)
        # paths = sorted(list(paths))
        paths = categories

        data = []
        data = list(data)


        for i, path in enumerate(paths):
            data += [{}]
            data[i]['path'] = path
            print(path)
            data[i]['level'] = 0
            data[i]['category'] = path
            #data[i]['category_name'] = path['_id']

        # ID aktualni inventury
            current = self.mdb.intranet.find_one({'_id': 'stock_taking'})['current']

        # Vyhledat artikly ve vybrane katerogii
            cat_modules = self.mdb.stock.aggregate([
                {'$match': {'category.0': path['_id']}},
                {'$addFields': {'count': {'$sum': '$history.bilance'}}},
                {'$sort': {'name': 1}}
            ])
            data[i]['modules'] = list(cat_modules)
            cat_elements = 0
            cat_sum = 0
            cat_sum_bilance = 0
            inventura = True

            for module in data[i]['modules']:
                #module['inventory'] = getInventory(module, datetime.datetime(2018, 10, 1), None, False)

                module['count_all'] = module['overview']['count']['onstock']
                if str(warehouse['_id']) in module['overview']['stocks']:
                    module['count'] = module['overview']['stocks'][str(warehouse['_id'])]['count']['onstock']
                else:
                    module['count'] = 0

                module['price_sum'] = module['count_all']*module['warehouse_unit_price']
                module['price_warehouse'] = module['count']*module['warehouse_unit_price']


                #module['inventory'] = getLastInventory(module, datetime.datetime(2018, 10, 1), False)
                module['inventory'] = getInventoryRecord(module, current, self.get_warehouse())
                #if module['inventory']:
                #    module['count'] = module['inventory']
                #module['inventory'] = bool(module['inventory'])

                #module['price_sum'] = getPrice(module)
                #if module['count'] > 0:
                #   module['price'] = module['price_sum']/module['count']
                #else:
                #    module['price'] = 0


                module['inventory_2018'] = {'bilance_count': None, 'bilance_price': None}
                (module['inventory_2018']['count'], module['inventory_2018']['price']) = getInventory(module, datetime.datetime(2018, 1, 1), datetime.datetime(2018, 10, 1), False)
                module['inventory_2018']['bilance_count'] = module['count'] - module['inventory_2018']['count']
                module['inventory_2018']['bilance_price'] = module['price_sum'] - module['inventory_2018']['price']*module['inventory_2018']['count']

                cat_sum += module['price_sum']
                cat_elements += module['count']
                cat_sum_bilance += module['inventory_2018']['bilance_price']
                inventura &= (bool(module['inventory']) or (module['count']==0))


            data[i]['cat_sum'] = cat_sum
            data[i]['cat_sum_bilance'] = cat_sum_bilance
            data[i]['cat_elements'] = cat_elements
            data[i]['cat_inventura'] = inventura


        self.render("stocktaking.view.categories.hbs", data=data, category = data, warehouses = warehouses )


class load_item(BaseHandler):
    def post(self):
        self.authorized(['inventory'], True)
        self.set_header('Content-Type', 'application/json')
        packet_id = self.get_argument('_id', None)
        stocktaking_position = self.get_argument('stocktaking_position', None)
        add_stocktaking_position = self.get_argument('add_position', None)

        print("Nacitani dat artiklu {} na pozici {}. Pozice se prida {}".format(packet_id, stocktaking_position, add_stocktaking_position))
        out = {}

        packet_id = bson.ObjectId(packet_id)

        # TODO: umoznit automaticke pridani (premisteni) sacku pri inventurovane
        # Měla by existovat možnost, jak inventuru odmítnout, protože to tu nemá co dělat.
        #if add_stocktaking_position:
        #    self.component_set_position(packet_id, bson.ObjectId(stocktaking_position))

        print("ObjectID pro nacteni", packet_id)
        # self.component_update_counts(packet_id)

        out['item'] = self.mdb.stock.find_one({'packets._id': packet_id})
        # out['article_unit_price'] = get_article_price(out['item'])
        # out['position'] = self.component_get_positions(id = packet_id)
        out['article_unit_price'] = 0
        out['position'] = self.component_get_positions(id = packet_id)
        out['inventory'] = self.get_inventory()

        out = bson.json_util.dumps(out)
        self.write(out)

    def get_inventory(self):
        current_id = self.mdb.intranet.find_one({'_id': 'stock_taking'})
        current = list(self.mdb.stock_taking.find({'_id': current_id['current']}))[0]
        return current

class save_stocktaking(BaseHandler):
    def post(self):
        self.authorized(['inventory'], True)
        self.set_header('Content-Type', 'application/json')
        #stock = self.get_argument('stock', self.get_warehouse()['_id'])
        description = self.get_argument('description', None)
        bilance = self.get_argument('bilance')
        absolute = self.get_argument('absolute')
        item = self.get_argument('_id', None)

        current = self.mdb.intranet.find_one({'_id': 'stock_taking'})['current']
        if not current:
            raise tornado.web.HTTPError(403)
        else:

            current_st = self.mdb.stock_taking.find_one({'_id': current})
            print("service_push >>", item, description, bilance, absolute)
            data = {
                    '_id': bson.ObjectId(),
                    'stock': self.get_warehouse()['_id'],
                    'operation': 'inventory',
                    'bilance': float(bilance),
                    'absolute': float(absolute),
                    'inventory': current,
                    'description': "{} | {}".format(current_st['name'], description),
                    'user':self.logged,
                    }

            out = self.mdb.stock.update(
                    {'_id': bson.ObjectId(item)},
                    {
                        '$push': {'history':data}
                    }
                )

            self.write(bson.json_util.dumps(data))


class stocktaking_events(BaseHandler):
    '''
        Slouzi k ziskani prehledu o vsech Vytvorenych kampanich.

    '''
    def get(self):
        self.authorized(['inventory-sudo'], True)
        warehouse = self.get_warehouse()
        print("Vybrany sklad je", warehouse)
        self.render('stocktaking.events.hbs', warehouse = warehouse)

    def post(self):
        self.authorized(['inventory-sudo'], True)
        self.set_header('Content-Type', 'application/json')
        events = list(self.mdb.stock_taking.find())
        stocktaking = self.mdb.intranet.find_one({'_id': 'stock_taking'})

        for event in events:
            print(event['_id'])
            event['id'] = str(event['_id'])
            event['opened_from'] = str(event['opened'].date())
            event['opened_to'] = str(event['closed'].date())
            event['status'] = int(stocktaking['current'] == event['_id'])

        out = bson.json_util.dumps(events)
        self.write(out)



class stocktaking_event(BaseHandler):
    '''
        Slouzi k ziskani informaci o jedne inventurovaci kampani.
    '''
    def post(self, id):
        self.authorized(['inventory'], True)
        self.set_header('Content-Type', 'application/json')
        stocktaking = self.mdb.intranet.find_one({'_id': 'stock_taking'})
        event = self.mdb.stock_taking.find_one({"_id": bson.ObjectId(id)})

        event['id'] = str(event['_id'])
        event['opened_from'] = str(event['opened'].date())
        event['opened_to'] = str(event['closed'].date())
        event['status'] = int(stocktaking['current'] == event['_id'])

        out = bson.json_util.dumps(event)
        self.write(out)


class stocktaking_eventlock(BaseHandler):
    '''
        Uzamkne otevrenou kampan. Nepujde provadet inventura.
    '''
    def post(self):

        self.authorized(['inventory-sudo'], True)
        self.mdb.intranet.update({'_id': 'stock_taking'}, {'$set':{'current': None}})
        self.write("OK")

class stocktaking_eventsave(BaseHandler):
    '''
        Slouzi k ulozeni dat o inventure. Zaloven zapise globalni parametr s id aktualni invetury.
    '''
    def post(self, id):
        self.authorized(['inventory-sudo'], True)
        data = {'name': self.get_argument('name'),
                'opened': datetime.datetime.strptime(self.get_argument('from'), '%Y-%m-%d'),
                'closed': datetime.datetime.strptime(self.get_argument('to'), '%Y-%m-%d'),
                'status': self.get_argument('status'),
                'author': self.get_argument('author'),
                }

        data['warehouse'] = self.get_warehouse()['_id']

        if id == 'new':
            data['history'] = []
            data['documents'] = []
            id = str(self.mdb.stock_taking.insert(data))
        else: #TODO: dodelat overeni, ze se jedna o legitimni ObjectID
            self.mdb.stock_taking.update({'_id': bson.ObjectId(id)}, {'$set':data}, False, True)

        # ulozit aktualni inventuru
        if data['status']: self.mdb.intranet.update({'_id': 'stock_taking'}, {'$set':{'current': bson.ObjectId(id)}})
        self.write(id)



class edit(BaseHandler):
    def get(self, name):
        print("Vyhledavam polozku", name)
        if name == 'new':
            product = self.mdb.production.insert({
                    'name': 'Without name',
                    'created': datetime.datetime.now(),
                    'state': 0,
                    'info':{},
                    'author': [],
                    'tags': [],
                    'priority': 0,
                    'type': 'module',
                    'components': []
                })
            print(product)
            self.redirect('/production/{}/'.format(product))

class stocktaking_event_generate_basic(BaseHandlerOwnCloud):
    def post(self, id):
        bid = ObjectId(id)
        stocktaking = self.mdb.stock_taking.find_one({'_id': bid})
        print(bid, id, stocktaking)
        file = setava_01(self, stocktaking)
        print(file)
        self.write(file.get_link())
    #
    # def post(self, name):
    #     self.set_header('Content-Type', 'application/json')
    #     op = self.get_argument('operation', 'get_production')
    #     print("POST....", op)
    #     print(name)
    #
    #     if op == 'get_production':
    #         #print("get_production")
    #         dout = list(self.mdb.production.aggregate([
    #                 {'$match': {'_id': bson.ObjectId(name)}},
    #                 {'$sort': {'components.Ref': 1}}
    #             ]))
    #         print(dout)
    #         output = bson.json_util.dumps(dout[0])
    #         self.write(output)

def setava_01(self, stock_taking):
    comp = list(self.mdb.stock.find().sort([("category", 1), ("_id",1)]))
    autori = stock_taking['author'].strip().split(',')
    datum = str(stock_taking['closed'].date())
    filename = "{}_{}.pdf".format(stock_taking['_id'], ''.join(stock_taking['name'].split()))

    print("Generovani prehledu inventury")
    print("Od:", autori)
    print("Kdy:", datum)
    print("Soubor,", filename)

    page = 1
    money_sum = 0
    Err = []

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
    pdf.cell(10, 0, "Vytvořeno %s, strana %s z %s" %(datetime.datetime.now().strftime("%d. %m. %Y, %H:%M:%S"), page, pdf.alias_nb_pages()) )

    pdf.add_page()


    data = self.mdb.stock.aggregate([
            {'$addFields': {'count': {'$sum': '$history.bilance'}}}
        ])

    gen_time = datetime.datetime(2018, 10, 1)
    lastOid = ObjectId.from_datetime(gen_time)

    print(data)


    for i, component in enumerate(data):
        print(component['_id'], component['name'])
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
                pdf.cell(10, 0, "Vytvořeno %s, strana %s z %s" %(datetime.datetime.now().strftime("%d. %m. %Y, %H:%M:%S"), page, pdf.alias_nb_pages()) )

                pdf.set_font('pt_sans', '', 11)
                pdf.set_xy(10, 10)
                pdf.cell(100, 5, 'Skladová položka')
                pdf.set_x(105)
                pdf.cell(10, 5, "Počet kusů", align='R')
                #pdf.set_x(120)
                #pdf.cell(10, 5, "Cena za 1ks", align='R')
                pdf.set_x(180)
                pdf.cell(10, 5, "Cena položky (bez DPH)", align='R', ln=2)
                pdf.line(10, 15, pdf.w-10, 15)
                pdf.set_y(18)
                page_sum = 0

            pdf.set_font('pt_sans', '', 10)

            count = component['count']
            price = 0
            price_ks = 0
            first_price = 0

            inventura = False
            for x in reversed(component.get('history', [])):
                if x.get('operation', None) == 'inventory':
                    #TODO: tady porovnávat, jesti to patri do stejne kampane. Ne na zaklade casu ale ID
                    if x['_id'].generation_time > lastOid.generation_time:
                        inventura = True
                        count = x['absolute']
                        pdf.set_x(120)
                        pdf.cell(1, 5, "i")
                        break;

            if count > 0:
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

                pdf.set_font('pt_sans', '', 10)
                pdf.set_x(105)
                pdf.cell(10, 5, "{} j".format(count), align='R')

                pdf.set_x(10)
                pdf.cell(100, 5, "{:5.0f}  {}".format(i, component['name']))

                pdf.set_font('pt_sans-bold', '', 10)
                pdf.set_x(180)
                pdf.cell(10, 5, "%6.2f Kč" %(price), align='R')


        except Exception as e:
            Err.append('Err' + repr(e) + repr(component['_id']))
            print(e)

        if count > 0:
            pdf.set_y(pdf.get_y()+4)

    pdf.line(10, pdf.get_y(), pdf.w-10, pdf.get_y())
    pdf.set_font('pt_sans', '', 8)
    pdf.set_x(180)
    pdf.cell(10, 5, "Konec souhrnu", align='R')

    #pdf.set_font('pt_sans', '', 10)
    #pdf.set_xy(150, pdf.get_y()+3)
    #pdf.cell(100, 5, 'Součet strany: {:6.2f} Kč'.format(page_sum))

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

    pdf.output("static/tmp/sestava.pdf")
    year = datum[:4]

    filename = "{}.pdf".format(''.join(stock_taking['name'].split(' ')))
    foldername = os.path.join(tornado.options.options.owncloud_root, 'accounting', year, 'stocktaking', filename)
    foldername = save_file(self.mdb, foldername)
    return upload_file(self.oc, 'static/tmp/sestava.pdf', foldername)
