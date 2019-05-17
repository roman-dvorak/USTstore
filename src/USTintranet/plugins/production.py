#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
from . import BaseHandler, BaseHandlerJson
#from pyoctopart.octopart import Octopart
import json
import urllib
import bson
import datetime
import pandas as pd
from fpdf import FPDF


def make_handlers(module, plugin):
        return [
             (r'/{}/(.*)/upload/bom/ust/'.format(module), plugin.ust_bom_upload),
             (r'/{}/(.*)/print/'.format(module), plugin.print_bom),
             (r'/{}/(.*)/edit/'.format(module), plugin.edit),
             (r'/{}/api/getProductionList'.format(module), plugin.get_production_list),
             (r'/{}'.format(module), plugin.home),
             (r'/{}/'.format(module), plugin.home),
        ]

def plug_info():
    #class base_info(object):
    return {
        "module": "production",
        "name": "production"
    }



def mask_array(data, mask, default = None):
    new = {}
    for x in mask:
        new[x] = data.get(x, default)
    return new

def num_to_float(data):
    try:
        return float(data)
    except Exception as e:
        return 0

def group_data(data, groupby = ['Footprint', 'UST_ID', 'Value'], db = None):
    selected = []
    for component in data:
        use = 0
        c_ref = [component['Ref']]
        c_footprint = component.get('Footprint', None)
        c_ustid = component.get('UST_ID', None)
        c_value = component.get('Value', 0)
        c_price = num_to_float(component.get('price', 0.0))
        c_component = component.get('store', [])
        print("########")
        print(c_ref)


        s = 0
        for i, sel in enumerate(selected):
            if mask_array(component, groupby) == mask_array(sel, groupby):
                print("Shod..", mask_array(component, groupby), mask_array(sel, groupby))
                selected[i]['Ref'] += c_ref
                selected[i]['count'] += 1
                selected[i]['price_group'] += c_price
                s = 1
                break
        if not s:
            #else: # polozka je zde poprvj
            component['Ref'] = c_ref
            component['count'] = 1
            component['price_group'] = c_price
            price = 0
            print("stav:...", db, c_ustid)
            if db and c_ustid:
                try:
                    o = list(db.stock_movements.find({'product': c_ustid}))
                    print(">...", o)
                    price = o[0].get('price', 0.0)
                except Exception as e:
                    print("ERr", c_ustid)

            component['price_store'] = price
            selected.append(component)


    return selected

# prida do pole pocet skladovych zasob na zaklade nazvu soucastky v dictionary jako 'UST_ID', pokud to neobsahuje, tak je pole preskoceno...
def get_component_stock(data, db):
    for component_i, component in enumerate(data):
        print("____")
        print(component_i, component)
        if component.get('UST_ID', False):
            stock = 0
            movements = db.stock.aggregate([
                {
                    "$match":{'_id': component.get('UST_ID')}
                },{
                    "$unwind": "$history"
                },
            ])
            for movement in movements:
                print(movement)
                stock += movement['history'].get('bilance', 0)
            data[component_i]['stock'] = stock
    return data

class home(BaseHandler):
    def get(self):
        production_list = self.mdb.production.aggregate([])
        self.render('production.home.hbs', production_list = production_list)

'''
    Nacte vsechny polozky z DB pro vytvoreni prehledove tobulky.
'''
class get_production_list(BaseHandlerJson):
    def post(self):
        data = list(self.mdb.production.find())
        for d in data:
            d['id'] = str(d['_id'])
            d['components'] = len(d['components'])
            d['created'] = str(d['created'].date())
            d['author_text'] = ', '.join(d['author'])
            d['placement'] = None
        print(data)
        out = bson.json_util.dumps(data)
        self.write(out)

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
            self.redirect('/production/{}/edit/'.format(product))

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
        #     dout = list(self.mdb.production.aggregate([
        #         {'$match': {'_id': bson.ObjectId(name)}},
        #         {'$sort': {'components.Ref': 1}}
        #     ]))
        #     dout = group_data(dout[0].get('components', []), db = self.mdb)
        #     dout = get_component_stock(dout, db = self.mdb)
        #     for i,d in enumerate(dout):
        #         if not d.get('price', False):
        #             dout[i]['price'] = d.get('price_store', 0)
        #     out = bson.json_util.dumps(dout)

            dout = list(self.mdb.production.aggregate([
                    {'$match': {'_id': bson.ObjectId(name)}},
                    {'$unwind': '$components'},
                    {'$project': {'components': 1}},
                    {'$sort': {'components.Ref': 1}},
                    {'$group':{
                        '_id': {'UST_ID': '$components.UST_ID',
                                'Value': '$components.Value',
                                'Footprint': '$components.Footprint',
                                'Distributor': '$components.Distributor',
                                'Datasheet': '$components.Datasheet',
                                'MFPN': '$components.MFPN',
                                'stock_count': '$components.stock_count',
                                'note': '$components.note',},
                        'Ref': {'$push': '$components.Ref'},
                        'count': {'$sum': 1},
                    }},
                    {"$addFields":{"cUST_ID": {"$convert":{
                             "input": '$_id.UST_ID',
                             "to": 'objectId',
                             "onError": "Err",
                             "onNull": "null"
                    }}}},
                    {"$lookup":{
                        "from": 'stock',
                        "localField": 'cUST_ID',
                        "foreignField": '_id',
                        "as": 'stock'
                    }}
                ]))
            out = bson.json_util.dumps(dout)
            print("Get component grouped")
            print(json.dumps(out, indent=4, sort_keys=True))
            #print(".................")
            #print(out)
            #print("................")
            self.write(out)

        elif op == 'reload_prices':
            print('Reload prices from stock')


        elif op == 'update_component_parameters':
            print("####.... update_component_parameter")
            component = self.get_arguments('component[]')
            parameter = self.get_argument('parameter').strip().replace('_id.', '')
            value = self.get_argument('value').strip()

            if value == 'undefined': value = ''

            for c in component:
                if parameter == 'UST_ID':
                    value = bson.ObjectId(value)
                    print("JE TO UST ID... budu potrebovat ID")
                self.mdb.production.update(
                    {
                       '_id': bson.ObjectId(name.strip()),
                       "components.Ref": c.strip()
                    },
                    {
                        "$set":{"components.$.{}".format(parameter): value}
                    }
                )
                print("Uravil jsem", c)

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
                {'$unwind': "$components"},
                {'$group':
                    {"_id": "$components.UST_ID", "count": { "$sum": 1 }}
                }
            ]))

            #print(production)
            #
            # print(production)
            for c in production:
                try:
                    id = c['_id']
                    oid = bson.ObjectId(id)
                    count = self.component_get_counts(oid, bson.ObjectId(self.get_cookie('warehouse')))
                    print(id, "..", count)
                    if len(count['by_warehouse']) > 0:
                        print("Nastavuji", name, id, count['suma'][0]['count'])
                        self.mdb.production.update_many(
                            {'_id': bson.ObjectId(name), 'components.UST_ID': id},
                            {'$set': {"components.$[id].stock_count": count['suma'][0]['count']}},

                            array_filters = [{ "id.UST_ID": id}],
                            upsert = False
                        )
                    else:
                        print("POLOZKA NENALEZENA....")
                except Exception as e:
                    print("CHYBA ....")
            self.write({'status': 'ok'})




        ##
        #### Update production
        ##
        elif op == 'update_parameters':
            print("update_parameters")
            p_name = self.get_argument('name')
            p_description = self.get_argument('description')
            print(p_name, p_description)

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

class print_bom(BaseHandler):
    def get_component(self, components, name, field='Ref'):
        print("get", components, name)
        for c in components:
            print('>>', c)
            if c.get(field, {}) == name:
                return c
        return {}


    def get(self, name):
        info = list(self.mdb.production.aggregate([
            {'$match': {'_id': bson.ObjectId(name)}},
        #     {'$sort': {'components.Ref': 1}},
        #     # {"$lookup":{
        #     #     "from": 'stock',
        #     #     "localField": 'UST_ID',
        #     #     "foreignField": '_id',
        #     #     "as": 'stock'
        #     # }}
        ]))[0]

        print(info)


        out = list(self.mdb.production.aggregate([
                {'$match': {'_id': bson.ObjectId(name)}},
                {'$unwind': '$components'},
                {'$project': {'components': 1}},
                {'$sort': {'components.Ref': 1}},
                {'$group':{
                    '_id': {'UST_ID': '$components.UST_ID',
                            'Value': '$components.Value',
                            'Footprint': '$components.Footprint',
                            'Distributor': '$components.Distributor',
                            'Datasheet': '$components.Datasheet',
                            'stock_count': '$components.stock_count',
                            'note': '$components.note'},
                    'Ref': {'$push': '$components.Ref'},
                    'category': {'$push': '$components.category'},
                    'count': {'$sum': 1},
                }},
                {"$addFields":{"cUST_ID": {"$convert":{
                         "input": '$_id.UST_ID',
                         "to": 'objectId',
                         "onError": "Err",
                         "onNull": "null"
                }}}},
                {"$lookup":{
                    "from": 'stock',
                    "localField": 'cUST_ID',
                    "foreignField": '_id',
                    "as": 'stock'
                }}
            ]))

        pdf = FPDF('P', 'mm', format='A4')
        pdf.set_auto_page_break(False)
        pdf.add_font('pt_sans', '', 'static/pt_sans/PT_Sans-Web-Regular.ttf', uni=True)
        pdf.add_font('pt_sans-bold', '', 'static/pt_sans/PT_Sans-Web-Bold.ttf', uni=True)
        pdf.add_page()

        pdf.set_font('pt_sans', '', 12)
        pdf.set_xy(10, 10)
        pdf.cell(0,5, info.get('name', name))

        pdf.set_font('pt_sans', '', 8)
        pdf.set_y(15)
        pdf.cell(0,5, info.get('description', name))

        pdf.set_font('pt_sans', '', 8)
        pdf.set_xy(170, 3)
        pdf.cell(0, 5, "Strana "+str(pdf.page_no())+"/{nb}", border=0)
        pdf.set_xy(170, 6)
        pdf.cell(0, 5, str(datetime.datetime.now())[:16], border=0)
        if pdf.page_no() == 1:
            pdf.set_xy(170, 9)
            pdf.cell(0, 5, str("Sklad: {}".format('nazev')), border=0)

        row = []
        used = []

        rowh = 9+4
        first_row = 28
        pdf.set_xy(10, 28)

        out = [{
                '_id': {
                    'UST_ID': 'UST_ID',
                    'Value': 'Value',
                    'Footprint': 'FootPrint',
                    'Distributor': 'Distributor',
                    'Datasheet': 'Datasheet',
                    'note': "Poznámka"
                },
                'Ref': ['Ref'],
                'count': '',
                'cUST_ID': "UST_ID",
                'stock': [{'name': 'Název', 'category': ['Kategorie']}]}
            ]+out

        j = 0

        last = 10
        for i, component in enumerate(out):
            print("Component", i, component)
            item_places = self.component_get_positions(component['cUST_ID'], stock = bson.ObjectId(self.get_cookie('warehouse', False)))
            #print("Places:", item_places)

            try:
                name = component.get('stock')[0]['name']
                category = component.get('stock')[0]['category']
            except Exception as e:
                name = ''
                category = []

            j += 1
            if j > 28-9:
                j = 0
                first_row = 10
                print("New page...")
                pdf.add_page()
                pdf.set_font('pt_sans', '', 8)
                pdf.set_xy(170, 3)
                pdf.cell(0, 5, "Strana "+str(pdf.page_no())+"/{nb}", border=0)
                pdf.set_xy(170, 6)
                pdf.cell(0, 5, str(datetime.datetime.now())[:16], border=0)
                pdf.line(10,first_row, 200, first_row )

                pdf.set_xy(10, 3)
                pdf.cell(0, 5, info.get('name', name), border=0)

            if type(component['count']) == 'String' and ['count'] > 5.0:
                last += 15
            else:
                last += 10

            pdf.set_font('pt_sans', '', 8)

            pdf.set_xy(10, first_row+j*rowh)
            pdf.cell(0, 5, str(i)+'.', border=0)

            pdf.set_xy(10, first_row+j*rowh + 3.5)
            pdf.cell(0, 5, str(component['count'])+'x', border=0)

            pdf.set_xy(15, first_row+j*rowh + 3.5)
            pdf.cell(0, 5, str(', '.join(component['Ref'])), border=0)

            pdf.set_xy(163, first_row+j*rowh + 3.5)
            pdf.cell(0, 5, str(component['_id'].get('UST_ID', '--')))

            pdf.set_xy(130, first_row+j*rowh)
            pdf.cell(0, 5, component['_id'].get('Footprint', '--')[:45])

            pdf.set_font('pt_sans-bold', '', 7.5)

            pdf.set_xy(15, first_row+j*rowh)
            pdf.cell(0, 5, component['_id'].get('Value', '--')[:30])


            pdf.set_font('pt_sans-bold', '', 9)

            pdf.set_xy(60, first_row+j*rowh)
            pdf.cell(0, 5, name)

            pdf.set_xy(130, first_row+j*rowh + 7)
            pdf.cell(0, 5, str(component['_id'].get('note', '--')))

            pdf.set_font('pt_sans', '', 8)


            pdf.set_xy(15, first_row+j*rowh + 7)
            pdf.cell(0, 5, str(', '.join(category)), border=0)

            #for k, place in enumerate(item_places):
            #    pdf.set_xy(15, first_row+j*rowh + 7)
            #    pdf.cell(0, 5, place['info'][0]['name'])


            pdf.line(10,first_row+j*rowh + 8+5, 200, first_row+j*rowh + 8 + 5)
            print("===================Value==========================================")

        pdf.alias_nb_pages()
        pdf.output("static/production.pdf")
        with open('static/production.pdf', 'rb') as f:
            self.set_header("Content-Type", 'application/pdf; charset="utf-8"')
            self.set_header("Content-Disposition", "inline; filename=UST_osazovaci_list.pdf")
            self.write(f.read())
        f.close()
