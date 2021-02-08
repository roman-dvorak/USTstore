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
from bson.json_util import dumps
from bson import *
from bson import ObjectId
import urllib
from fpdf import FPDF
import barcode
import code128
import codecs
import datetime
from si_prefix import *

from plugins.helpers.warehouse import *

#from .store import get_plugin_info


def get_packet(db, id, packet):

    packet_query = [{ '$match': {"_id": id}},
                { "$project": {"packets": 1}},
                { "$unwind": '$packets'},
                { "$replaceRoot": {"newRoot": "$packets"}},
                { "$match": {"_id": packet}},
                { "$lookup": { "from": 'store_positions', "localField":'position', "foreignField": '_id', "as": 'position'}},
                { "$lookup": { "from": 'stock_operation', "localField":'_id', "foreignField": 'pid', "as": 'operations'}},
                { "$addFields": {
                        "packet_count":  {"$sum": "$operations.count"},
                        "packet_reserv":  {"$sum": "$operations.reserv"},
                        "packet_ordered":  {"$sum": "$operations.ordered"},
                        "packet_price": {
                        "$function":
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
                                "args": ["$operations.unit_price", "$operations.count"], "lang": "js"
                            }
                        }
                    }
                },
                ]
    print(packet_query)
    return list(db.stock.aggregate(packet_query))



def get_component(db, id, current_warehouse=ObjectId("5c67444e7e875154440cc28f")):

    output = {}
    basicdata_query = [
            { "$match": { "_id": id }},
            { "$lookup": { "from": 'category_complete', "localField": 'category', "foreignField": '_id', "as": 'categories' }},
            { "$unset": ["history", "packets", 'position', 'overview', 'stock', 'warehouse_unit_price']}
        ]

    output['basic'] = list(db.stock.aggregate(basicdata_query))
    #print("BASIC")
    #print(output['basic'])


    packet_query = [{ '$match': {"_id": id}},
                { "$project": {"packets": 1}},
                { "$unwind": '$packets'},
                { "$replaceRoot": {"newRoot": "$packets"}},
                { "$lookup": { "from": 'store_positions', "localField":'position', "foreignField": '_id', "as": 'position'}},
                { "$lookup": { "from": 'stock_operation', "localField":'_id', "foreignField": 'pid', "as": 'operations'}}]

    output['packets'] = list(db.stock.aggregate(packet_query))
    #print("packets")
    #print(dumps(output['packets'], indent=4, sort_keys=True))

    current_warehouse_query = [{ '$match': {"_id": id}},
                { "$project": {"packets": 1}},
                { "$unwind": '$packets'},
                { "$replaceRoot": {"newRoot": "$packets"}},
                { "$lookup": { "from": 'store_positions', "localField":'position', "foreignField": '_id', "as": 'position'}},
                { "$lookup": { "from": 'stock_operation', "localField":'_id', "foreignField": 'pid', "as": 'operations'}},
                { "$match": { "position": {"$not":{"$size":0}, "$elemMatch":{"warehouse": current_warehouse}}}},
                #{ "$match": { "position": {"$not":{"$size":0}, "$elemMatch":{"warehouse": ObjectId("5c67444e7e875154440cc28f")}}}},
                { "$addFields": {
                        "packet_count":  {"$sum": "$operations.count"},
                        "packet_reserv":  {"$sum": "$operations.reserv"},
                        "packet_ordered":  {"$sum": "$operations.ordered"},
                        "packet_price": {
                        "$function":
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
                                "args": ["$operations.unit_price", "$operations.count"], "lang": "js"
                            }
                        }
                    }
                },
                { "$group": {
                        '_id': 'null',
                        'count': {"$sum": '$packet_count'},
                        'price': {"$sum": '$packet_price'},
                        'reserv': {"$sum": '$packet_reserv'},
                        'ordered': {"$sum": '$packet_ordered'},
                    }
                 }
                 ]

    output['current_warehouse'] = list(db.stock.aggregate(current_warehouse_query))
    #print("current_warehouse")
    #print(dumps(output['current_warehouse'], indent=4, sort_keys=True))
    if(output['current_warehouse'] == []): output['current_warehouse'] = [{}]



    other_warehouse_query = [{ '$match': {"_id": id}},
                { "$project": {"packets": 1}},
                { "$unwind": '$packets'},
                { "$replaceRoot": {"newRoot": "$packets"}},
                { "$lookup": { "from": 'store_positions', "localField":'position', "foreignField": '_id', "as": 'position'}},
                { "$lookup": { "from": 'stock_operation', "localField":'_id', "foreignField": 'pid', "as": 'operations'}},

                #{ "$match": { "position": {"$not":{"$size":0}, "$elemMatch":{"warehouse": ObjectId("5c67444e7e875154440cc28f")}}}},
                #{ "$match": { "position": {"$not":{"$size":0}, "$elemMatch":{"warehouse": ObjectId("5c67444e7e875154440cc28f")}}}},
                { "$addFields": {
                        "packet_count":  {"$sum": "$operations.count"},
                        "packet_reserv":  {"$sum": "$operations.reserv"},
                        "packet_ordered":  {"$sum": "$operations.ordered"},
                        "packet_price": {
                        "$function":
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
                                "args": ["$operations.unit_price", "$operations.count"], "lang": "js"
                            }
                        }
                    }
                },
                { "$group": {
                        '_id': 'null',
                        'count': {"$sum": '$packet_count'},
                        'price': {"$sum": '$packet_price'},
                        'reserv': {"$sum": '$packet_reserv'},
                        'ordered': {"$sum": '$packet_ordered'},
                    }
                 }]

    output['other_warehouse'] = list(db.stock.aggregate(other_warehouse_query))
    if(output['other_warehouse'] == []): output['other_warehouse'] = [{}]


    prices_query = [{ '$match': { "_id": id}},
                { "$project": {"packets": 1}},
                { "$unwind": '$packets'}, { "$replaceRoot": {"newRoot": "$packets"}},
                { "$lookup": { "from": 'stock_operation', "localField":'_id', "foreignField": 'pid', "as": 'operations'}},
                { "$unwind": '$operations'}, { "$replaceRoot": {"newRoot": "$operations"}},
                { "$sort": {'date': 1}},
                { "$match": {'type': 'buy'}},
                { "$group": {
                        '_id': 'null',
                        'min_price': {"$min": "$unit_price"},
                        'max_price': {"$max": "$unit_price"},
                        'avg_price': {"$avg": "$unit_price"},
                        'last_price': {"$last": "$unit_price"}
                }}]
    output['prices'] = list(db.stock.aggregate(prices_query))
    if(output['prices'] == []): output['prices'] = [{}]


    parameters_query = [{ '$match': {"_id": id}},
        { "$project": {"parameters": {"$objectToArray": "$parameters"}}},
        { "$unwind": '$parameters'},
        { "$replaceRoot": {"newRoot": "$parameters"}},
        { "$lookup": { "from": 'parameters', "localField":'k', "foreignField": 'key', "as": 'm'}},
        { "$project": {"m": {"$first": "$m"}, "v":1, "k": 1}},
    ]

    #output['parameters'] = list(db.stock.aggregate(parameters_query))
    output['parameters'] = []
    #print("parameters")
    #print(dumps(output['parameters'], indent=4, sort_keys=True))

    #print(".............................................")

    return output




def get_plugin_handlers():
        #plugin_name = get_plugin_info()["name"]
        plugin_name = 'store'

        return [
             (r'/{}/component/(.*)/set_name/'.format(plugin_name), component_set_name),
             (r'/{}/component/(.*)/set_description/'.format(plugin_name), component_set_description),
             (r'/{}/component/(.*)/set_categories/'.format(plugin_name), component_set_categories),
             # (r'/{}/component/(.*)/get_categories/'.format(plugin_name), component_set_description),
             (r'/{}/component/(.*)/set_param/'.format(plugin_name), component_set_param),
             (r'/{}/component/(.*)/set_supplier/'.format(plugin_name), component_set_supplier),
             (r'/{}/component/(.*)/do_buy/'.format(plugin_name), component_do_buy),
             (r'/{}/component/(.*)/do_move/'.format(plugin_name), component_do_move),
             (r'/{}/component/(.*)/do_relocate/'.format(plugin_name), component_do_relocate),
             (r'/{}/component/(.*)/do_service/'.format(plugin_name), component_do_service),
             (r'/{}/component/(.*)/do_parameters/'.format(plugin_name), component_do_parameters),
             (r'/{}/component/(.*)/do_duplicate/'.format(plugin_name), component_do_duplicate),
             (r'/{}/component/(.*)/'.format(plugin_name), component_home_page)
        ]


class component_home_page(BaseHandler):
    def get(self, component):
        cid = bson.ObjectId(component)

        component = get_component(self.mdb, cid, bson.ObjectId(self.get_cookie('warehouse')))

        self.render('store/store.component.card.hbs', id=component['basic'][0]['_id'], component = component['basic'][0], current_warehouse = component['current_warehouse'][0], other_warehouse = component['other_warehouse'][0], prices = component['prices'][0], packets = component['packets'], parameters = component['parameters'], dumps=dumps, warehouse = self.get_warehouse())


class component_set_name(BaseHandler):
    def post(self, component):
        cid = bson.ObjectId(component)
        new_name = self.get_argument('new_name')

        self.mdb.stock.update({'_id': cid}, {"$set": {'name': new_name}})
        self.write({'status': 'ok'})


class component_set_description(BaseHandler):
    def post(self, component):
        cid = bson.ObjectId(component)
        new_description = self.get_argument('new_description')

        self.mdb.stock.update({'_id': cid}, {"$set": {'description': new_description}})
        self.write({'status': 'ok'})

class component_set_param(BaseHandler):
    def post(self, component):
        cid = bson.ObjectId(component)
        parameter = self.get_argument('parameter')
        value = self.get_argument('value')
        unit = self.get_argument('unit', None)

        #TODO: Kontrola, že tento klíč (parametr) existuje

        #TODO: kontrola typu a správného zápisu hodnoty
        print({'_id': cid}, {"$set": {'parameters.$.{}'.format(parameter): {'value': value}}})
        self.mdb.stock.update({'_id': cid}, {"$set": {'parameters.{}'.format(parameter): {'value': value}}} )
        self.write({'status': 'ok'})

class component_set_supplier(BaseHandler):
    def post(self, component):
        cid = bson.ObjectId(component)
        id = int(self.get_argument('id'))
        supplier = self.get_argument('supplier')
        symbol = self.get_argument('symbol')
        url = self.get_argument('url', None)

        data = {
            "supplier": supplier,
            "symbol": symbol,
            "url": url
        }

        if id == -1: # Novy dodavatel
            self.mdb.stock.update({'_id': cid}, {"$push": {'supplier': data}} )
        else:
            self.mdb.stock.update({'_id': cid}, {"$set": {'supplier.{}'.format(id): data}} )

        self.write({'status': 'ok'})

class component_set_categories(BaseHandler):
    def post(self, component):
        cid = bson.ObjectId(component)
        categories = self.get_arguments('categories')

        for i, c in enumerate(categories):
            categories[i] = ObjectId(c)

        out = self.mdb.stock.update({'_id': cid}, {"$set": {'category': categories}} )
        self.write({'status': 'ok', 'data': str(out)})
        #self.write({'status': 'ok'})



class component_do_buy(BaseHandler):
    def post(self, component):
        cid = bson.ObjectId(component)

        ctype = self.get_argument('type', None)
        supplier = self.get_argument('supplier', None)
        position = self.get_argument('position', None)
        packet = self.get_argument('packet', None)
        description = self.get_argument('description', '')
        description_operation = self.get_argument('description_operation', '')
        bilance = float(self.get_argument('count', 0))
        bilance_plan = self.get_argument('count_planned', None)
        invoice = self.get_argument('invoice', None)
        price = float(self.get_argument('price'))

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

        query_data = {'_id': cid}
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
                    }
                  }
                }
            out = self.mdb.stock.update(query_data, packet_data)
            print("Pridavam sacek", out)

        out = self.mdb.stock_operation.insert({
            'pid': packet_id,
            'count': float(bilance),
            'reserved': 0,
            'cart': 0,
            'unit_price': float(price),
            'type': 'buy',
            'date': datetime.datetime.now(),
            'user': self.logged,
            'invoice': invoice,
            'supplier': supplier,
            'description': description_operation,
        })
        print("Pridavam operaci", out)

        print("buy_push >>", cid, position, packet, description, bilance, invoice, price)

        self.LogActivity('store', 'operation_service')
        self.write('Byl proveden nákup položky {} v počtu {} jednotek. Cena operace je {} Czk.'.format(cid, bilance, price*bilance))



class component_do_move(BaseHandler):
    def post(self, component):
        cid = bson.ObjectId(component)

        src = bson.ObjectId(self.get_argument('source'))
        dst = self.get_argument('destination')
        if dst != 'none': dst = bson.ObjectId(dst)

        print("Move")
        print(cid)
        print(src)
        print(dst)
        operation_description = self.get_argument('operation_description', None)
        count = float(self.get_argument('count', 0))

        packet = get_packet(self.mdb, cid, src)[0]

        ready = True
        msg = ""

        if count <= 0:
            ready = False
            msg += "Počet součástek musí být větší než 0"

        if ready and packet['packet_count'] < count:
            ready = False
            msg += "Ve zdrojovém sáčku není dostatečný počet kusů. Pouze {} ks."

# Vypocitat cenu odebraneho zbozi
        operation_price = 0
        tmp_count = count

        for operation in packet['operations']:
            print("oper", operation)
            if operation['type'] in ['buy', 'import', 'invoice']:
                if tmp_count > operation['count']:
                    operation_price += operation['count']*operation['unit_price']
                    tmp_count -= operation['count']
                    print("A", tmp_count, operation['count'], operation['count']*operation['unit_price'], (operation['count']*operation['unit_price'])/operation['count'])
                else:
                    operation_price += tmp_count*operation['unit_price']
                    tmp_count = 0
                    print("END", tmp_count, operation['count'], operation['count']*operation['unit_price'], (operation['count']*operation['unit_price'])/operation['count'])
            if tmp_count == 0:
                break

        operation_price /= count

        if ready:
            print("ready", ready)
        print(packet)

        if ready:

            if dst == 'none':
                dst = bson.ObjectId()
                print("Vytvorim novy sacek {}".format(dst))
                self.mdb.stock.update({
                    "_id": cid
                }, {
                    "$push": {
                        "packets": {
                            '_id': dst,
                            'type': 'zip_bag',
                            'supplier': 'null',
                            'position': 'null',
                            'description': 'Vytvoreno oddelenim z {}'.format(src)
                        }
                    }
                })

            self.mdb.stock_operation.insert({
                    "pid": dst,
                    "count" : count,
                    "unit_price" : operation_price,
                    "type" : "import",
                    "date" : datetime.datetime.now(),
                    "user" : "roman-dvorak",
                    "invoice" : 'null',
                    "supplier" : "0",
                    "description" : "Presun do jineho sacku"
                })
            self.mdb.stock_operation.insert({
                    "pid": src,
                    "count" : -count,
                    "unit_price" : -operation_price,
                    "type" : "export",
                    "date" : datetime.datetime.now(),
                    "user" : "roman-dvorak",
                    "invoice" : 'null',
                    "supplier" : "0",
                    "description" : "Presun do jineho sacku"
                })
            self.write("Presun byl proveden ze sacku <b>{}</b> do <b>{}</b> v počtu {} ks. Cena převedeného materiálu byla {}Czk ({}Czk/ks)".format(src, dst, count, count*operation_price, operation_price))
        else:
            self.write(msg)



class component_do_relocate(BaseHandler):
    def post(self, component):
        cid = bson.ObjectId(component)

        packet = bson.ObjectId(self.get_argument('packet_to_move'))
        pos = self.get_argument('position')
        if pos != 'none': pos = bson.ObjectId(pos)

        print("Move")
        print(cid)
        print(packet)
        print(pos)

        self.mdb.stock.update({
                "_id": cid,
                'packets._id': packet
            }, {
                "$set": { "packets.$.position": pos }
            })
        self.write('Byl proveden přesun sáčku {} se součástkou {}. Do pozice {}.'.format(packet, cid, pos))


class component_do_service(BaseHandler):
    def post(self, component):
        cid = bson.ObjectId(component)
        pid = bson.ObjectId(self.get_argument('packet_to_service'))
        count = self.get_argument('count')

        if count[0] in ['=']:
            packet = get_packet(self.mdb, cid, pid)
            actual = packet[0]['packet_count']
            new = float(count[1:])
            relative_count = (new - actual)
        elif count[0] in ['+', '-']:
            relative_count = float(count)
        else:
            relative_count = float(count)

        description = self.get_argument('description', "")
        out = self.mdb.stock_operation.insert({
            'pid': pid,
            'count': float(relative_count),
            'reserved': 0,
            'cart': 0,
            'unit_price': float(0),
            'type': 'buy',
            'date': datetime.datetime.now(),
            'user': self.logged,
            'invoice': None,
            'supplier': None,
            'description': description,
        })

        msg = "Byl proveden servisní odběr součástky {}.".format(cid)
        if count[0] in ['=']:
            msg += ' Počet byl aktualizován na {} jednotek.'.format(new)

        if relative_count > 0:
            msg += ' Ze sáčku bylo odebráno {} jednotek. '.format(relative_count)
        else:
            msg += ' Ze sáčku bylo odebráno {} jednotek. '.format(relative_count)

        self.write(msg)



        # packet = bson.ObjectId(self.get_argument('packet_to_move'))
        # pos = self.get_argument('position')
        # if pos != 'none': pos = bson.ObjectId(pos)
        #
        # print("Move")
        # print(cid)
        # print(packet)
        # print(pos)
        #
        # self.mdb.stock.update({
        #         "_id": cid,
        #         'packets._id': packet
        #     }, {
        #         "$set": { "packets.$.position": pos }
        #     })

class component_do_parameters(BaseHandler):
    def get(self, component):
        self.render('store/store.component.view.parameters.hbs')

class component_do_duplicate(BaseHandler):
    def post(self, component):

        cid = bson.ObjectId(component)
        component = self.mdb.stock.find({'_id': cid})
        component = list(component)[0]

        component['_id'] = ObjectId()
        component['name'] += ' [copy]'
        component.pop('aid', None)
        component.pop('position', None)
        component['history'] = []
        component['packets'] = []
        component['overview'] = {}
        component['stock'] = {}

        self.mdb.stock.insert(component)
        self.write({'status': 'ok', 'new_component': str(component['_id'])})
