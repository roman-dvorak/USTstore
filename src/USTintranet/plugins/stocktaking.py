#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
from . import BaseHandler
#from pyoctopart.octopart import Octopart
import json
import urllib
import bson
import datetime
import pandas as pd
from fpdf import FPDF

import sys
sys.path.append("..")
from plugins.store_data.stock_counting import getLastInventory, getPrice


def make_handlers(module, plugin):
        return [
             #(r'/{}/(.*)/upload/bom/ust/'.format(module), plugin.ust_bom_upload),
             #(r'/{}/(.*)/print/'.format(module), plugin.print_bom),

             (r'/{}/get_item/'.format(module), plugin.load_item),
             (r'/{}/save_item/'.format(module), plugin.save_stocktaking),
             (r'/{}/view/categories'.format(module), plugin.view_categories),
             (r'/{}'.format(module), plugin.home),
             (r'/{}/'.format(module), plugin.home),

             #(r'/{}/(.*)/'.format(module), plugin.edit),
             #(r'/{}/(.*)'.format(module), plugin.edit),
        ]

def plug_info():
    #class base_info(object):
    return {
        "module": "stocktaking",
        "name": "Stack taking"
    }


class home(BaseHandler):
    def get(self):
        cat = list(self.mdb.category.find({}))
        cat = sorted(cat, key = lambda x: x['path']+x['name'])
        self.render('stocktaking.home.hbs', category = cat)


##
##  Trida, pro prehled skladu rozrazeny do kategorii
##
class view_categories(BaseHandler):
    def get(self):

        categories = list(self.mdb.category.aggregate([]))

        # seradit kategorie tak, aby to odpovidalo adresarove strukture
        paths = set()
        for x in categories:
            paths.add(x['path']+x['name'])
        paths = sorted(list(paths))

        data = []
        data = list(data)

        for i, path in enumerate(paths):
            data += [{}]
            data[i]['path'] = path
            print(path.split('/')[-1])
            data[i]['level'] = len(path.split('/'))-2
            data[i]['category'] = path

            cat_modules = self.mdb.stock.aggregate([
                {'$match': {'category.0': path.split('/')[-1]}},
                {'$addFields': {'count': {'$sum': '$history.bilance'}}},
                {'$sort': {'name': 1}}
            ])
            data[i]['modules'] = list(cat_modules)

            cat_sum = 0
            for module in data[i]['modules']:
                module['inventory'] = getLastInventory(module, datetime.datetime(2018, 10, 1), False)
                if module['inventory']:
                    module['count'] = module['inventory']
                module['inventory'] = bool(module['inventory'])
                module['price_sum'] = getPrice(module)
                if module['count'] > 0:
                    module['price'] = module['price_sum']/module['count']
                else:
                    module['price'] = 0
                cat_sum += module['price_sum']
            data[i]['cat_sum'] = cat_sum
        self.render("stocktaking.view.categories.hbs", data=data, category = data)


class load_item(BaseHandler):
    def post(self):
        self.set_header('Content-Type', 'application/json')
        item = self.get_argument('_id', None)
        print("ARGUMENT JE....", item)
        #self.write(item)
        out = {}
        out['item'] = self.mdb.stock.find_one({'_id': item})
        out['history'] = list(self.mdb.stock.aggregate([
                {
                    '$match':{'_id': item}
                },{
                    '$unwind': '$history'
                },{
                    '$group' : {
                        '_id' : '$history.stock',
                        'bilance': { '$sum': '$history.bilance' },
                    }
                }]))
        out = bson.json_util.dumps(out)
        self.write(out)

class save_stocktaking(BaseHandler):
    def post(self):
        
        self.set_header('Content-Type', 'application/json')
        stock = self.get_argument('stock', 'pha01')
        description = self.get_argument('description', None)
        bilance = self.get_argument('bilance')
        absolute = self.get_argument('absolute')
        item = self.get_argument('_id', None)

        print("service_push >>", item, stock, description, bilance, absolute)
        data = {
                '_id': bson.ObjectId(),
                'stock': stock,
                'operation': 'inventory',
                'bilance': float(bilance),
                'absolute': float(absolute),
                'description': description,
                'user':self.logged,
                }
        print(data)
        out = self.mdb.stock.update(
                {'_id': item},
                {
                    '$push': {'history':data}
                }
            )
        out = self.mdb.stock.update(
                {'_id': item},
                {
                    '$push': {"tags": {'id': 'inventura2019', 'date': datetime.datetime.utcnow()}}
                }
            )
        print(out)
        #self.mdb.stock.update(
        #    {"_id": item},
        #    {'$set':{"tags.inventura2019":
        #        {'date': datetime.datetime.utcnow() }
        #    }}
        #)
        
        self.write(bson.json_util.dumps(data))



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

        product = self.mdb.production.aggregate([
                {'$match': {'_id': bson.ObjectId(name)}}
            ])
        self.render('production.flow.hbs', id = name, product = list(product))

    def post(self, name):
        self.set_header('Content-Type', 'application/json')
        op = self.get_argument('operation', 'get_production')
        print("POST....", op)
        print(name)

        if op == 'get_production':
            #print("get_production")
            dout = list(self.mdb.production.aggregate([
                    {'$match': {'_id': bson.ObjectId(name)}},
                    {'$sort': {'components.Ref': 1}}
                ]))
            print(dout[0])
            output = bson.json_util.dumps(dout[0])
            self.write(output)

        elif op == 'get_components_grouped':
            dout = list(self.mdb.production.aggregate([
                {'$match': {'_id': bson.ObjectId(name)}},
                {'$sort': {'components.Ref': 1}}
            ]))
            dout = group_data(dout[0].get('components', []), db = self.mdb)
            dout = get_component_stock(dout, db = self.mdb)
            for i,d in enumerate(dout):
                if not d.get('price', False):
                    dout[i]['price'] = d.get('price_store', 0)
            out = bson.json_util.dumps(dout)
            self.write(out)

        elif op == 'reload_prices':
            print('Reload prices from stock')


        elif op == 'update_component_parameters':
            component = self.get_arguments('component[]')
            parameter = self.get_argument('parameter')
            value = self.get_argument('value')

            for c in component:
                self.mdb.production.update(
                    {
                       '_id': bson.ObjectId(name),
                       "components.Ref": c
                    },
                    {
                        "$set":{"components.$.{}".format(parameter): value}
                    }#,
                    #'upsert': False,
                    #'multiple': True
                )

            print(component, parameter, value)
            out = bson.json_util.dumps({})
            self.write(out)

        elif op == 'update_component':
            print("update_component")

            '''
            tstmp: tstamp,
            ref: ref,
            name: name,
            value: value,
            package: package,
            ust_id: ust_id,
            description: description,
            price_predicted: price_predicted,
            price_store: price_store, 
            price_final: price_final
            '''

            ref = self.get_argument('ref')
            value = self.get_argument('value')
            c_name = self.get_argument('name')
            package = self.get_argument('package')
            ust_id = self.get_argument('ust_id')
            price_predicted = self.get_argument('price_predicted', 0.0)
            price_store = self.get_argument('price_store', 0.0)
            price_final = self.get_argument('price_final', 0.0)
            description = self.get_argument('description', '')
            print(ref.split(','))

            for c in ref.split(','):
                exist = self.mdb.production.find({'_id': bson.ObjectId(name), 'components.Ref': c})
                print(exist.count())
                print(bson.ObjectId(name))

                if exist.count() > 0:
                    update = self.mdb.production.update(
                            {
                                '_id': bson.ObjectId(name),
                                "components.Ref": c
                            },{
                               "$set": {
                                    "components.$.Ref": c,
                                    "components.$.Value": value,
                                    "components.$.Package": package,
                                    "components.$.UST_ID": ust_id,
                                    "components.$.price_predicted": price_predicted,
                                    "components.$.price_store": price_store,
                                    "components.$.price_final": price_final,
                                    "components.$.Note": description,
                               }
                            }, upsert = True)
                else:
                    print("NOVA POLOZKA")
                    update = self.mdb.production.update(
                            {
                                '_id': bson.ObjectId(name)
                            },{
                                "$push": {'components': {
                                    "Ref": c,
                                    "Package": package,
                                    "Value": value,
                                    "UST_ID": ust_id,
                                    "price_predicted": price_predicted,
                                    "price_store": price_store,
                                    "price_final": price_final,
                                    "Note": description
                                    }
                                }
                            })

            dout = [{'state': 'ok'}]
            output = bson.json_util.dumps(dout)
            self.write(output)
        ##
        #### END: Update component
        ##



        elif op == 'update_prices':
            print("UPDATE PRICES ....")
            print(name)
            production = list(self.mdb.production.aggregate([
                {'$match': {'_id': bson.ObjectId(name)}},
            ]))[0]
            components = production.get('components', [])
            for c in components:
                print(c.get('UST_ID', None))




        ##
        #### Update production
        ##
        elif op == 'update_parameters':
            print("update_parameters")
            p_name = self.get_argument('name')
            p_description = self.get_argument('description')
        
            self.mdb.production.update(
                {'_id': bson.ObjectId(name)},
                {'$set':{
                    'name': p_name,
                    'description': p_description
                }})
            dout = [{'state': 'ok'}]
            output = bson.json_util.dumps(dout)
            self.write(output)

        ##
        #### Update placement
        ##
        ## Ref,Val,Package,PosX,PosY,Rot,Side
        ##
        elif op == 'update_placement':
            print("update_placement")

            ref = self.get_argument('Ref')
            val = self.get_argument('Val')
            package = self.get_argument('Package')
            posx = self.get_argument('PosX')
            posy = self.get_argument('PosY')
            rot = self.get_argument('Rot')
            side = self.get_argument('Side')
            tstep = self.get_argument('Tstep')

            exist = self.mdb.production.find({'placement.Tstep': tstep})
            print(exist.count())
            print(bson.ObjectId(name))

            if exist.count() > 0:
                update = self.mdb.production.update(
                        {
                            '_id': bson.ObjectId(name),
                            "placement.Tstep": tstep
                        },{
                           "$set": {
                                "placement.$.Ref": ref,
                                "placement.$.Tstep": tstep,
                                "placement.$.Val": val,
                                "placement.$.Package": package,
                                "placement.$.PosX": posx,
                                "placement.$.PosY": posy,
                                "placement.$.Rot": rot,
                                "placement.$.Side": side
                           }
                        }, upsert = True)
            else:
                print("NOVA POLOZKA")
                update = self.mdb.production.update(
                        {
                            '_id': bson.ObjectId(name)
                        },{
                            "$push": {'placement': {
                                "Tstep": tstep,
                                "Ref": ref,
                                "Val": val,
                                "Package": package,
                                "PosX": posx,
                                "PosY": posy,
                                "Rot": rot,
                                "Side": side
                                }
                            }
                        })

            dout = [{'state': 'ok'}]
            output = bson.json_util.dumps(dout)
            self.write(output)


class ust_bom_upload(BaseHandler):
    def post(self, name):
        data = json.loads(self.request.body.decode('utf-8'))
        #self.mdb.production.update(
        #    {
        #        '_id': bson.ObjectId(name)
        #    },{
        #        '$set':{'components': data}
        #    })

        for component in data:
            print(component)
            exist = self.mdb.production.find({'_id': bson.ObjectId(name), 'components.Tstamp': component['Tstamp']})
            print(exist.count())
            v_update = {}
            v_push = {}

            for x in component:
                v_update["components.$.{}".format(x)] = component[x]
                v_push["{}".format(x)] = component[x]

            print(v_update)
            print(v_push)

            if exist.count() > 0:
                update = self.mdb.production.update(
                        {
                            '_id': bson.ObjectId(name),
                            "components.Tstamp": component['Tstamp']
                        },{
                           "$set": v_update
                        }, upsert = True)
            else:
                print("NOVA POLOZKA")
                update = self.mdb.production.update(
                        {
                            '_id': bson.ObjectId(name)
                        },{
                            "$push": {'components': v_push
                            }
                        })
