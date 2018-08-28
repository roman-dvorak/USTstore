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


def make_handlers(module, plugin):
        return [
             (r'/{}/(.*)/upload/bom/ust/'.format(module), plugin.ust_bom_upload),
             (r'/{}/(.*)/print/'.format(module), plugin.print_bom),
             (r'/{}'.format(module), plugin.hand_bi_home),
             (r'/{}/'.format(module), plugin.hand_bi_home),
             (r'/{}/(.*)/'.format(module), plugin.edit),
             (r'/{}/(.*)'.format(module), plugin.edit),
        ]

def plug_info():
    #class base_info(object):
    return {
        "module": "production",
        "name": "production"
    }


#
#   {'Ref': 'U9', 'Value': 'NCP1117ST50', 'Tstamp': '5AA08E3A', 'Datasheet': 'http://www.diodes.com/datasheets/AP1117.pdf', 'Footprint': 'TO_SOT_Packages_SMD:SOT-223-3_TabPin2'}
#
'''

for (j in components){
    if (selected.indexOf(j) == -1){
        var com2 = components[j];
        if (c_package == com2['Package'] && c_value == com2['Value'] && c_ustid == (com2['UST_ID'] || null) && c_note == (com2['Note'] || null)) {
            c_ref.push(com2['Ref']);
            selected.push(j);
        }
    }
}





    for (i in components){
        if (selected.indexOf(i) == -1){
            var com = components[i];
            selected.push(i);
            var c_ref = [com['Ref']];
            var c_package = com['Package']  || null;
            var c_note = com['Note'] || null;
            var c_value = com['Value']  || null;
            var c_ustid = com['UST_ID'] || null;

            // Tato cast provede 'grouping' polozek se stejnymi parametry
            for (j in components){
                if (selected.indexOf(j) == -1){
                    var com2 = components[j];
                    if (c_package == com2['Package'] && c_value == com2['Value'] && c_ustid == (com2['UST_ID'] || null) && c_note == (com2['Note'] || null)) {
                        c_ref.push(com2['Ref']);
                        selected.push(j);
                    }
                }
            }


'''

def mask_array(data, mask, default = None):
    new = {}
    for x in mask:
        new[x] = data.get(x, default)
    return new

def group_data(data, groupby = ['Footprint', 'UST_ID', 'Value']):
    selected = []
    for component in data:
        use = 0
        c_ref = [component['Ref']]
        c_footprint = component.get('Footprint', None)
        c_ustid = component.get('UST_ID', None)
        c_value = component.get('Value', 0)

        s = 0
        for i, sel in enumerate(selected):
            if mask_array(component, groupby) == mask_array(sel, groupby):
                s += 1
        if s != 0:
            selected[i]['Ref'] += c_ref
        else:
            component['Ref'] = c_ref
            selected.append(component)

    return selected

class hand_bi_home(BaseHandler):
    def get(self):
        production_list = self.mdb.production.aggregate([])
        self.render('production.home.hbs', production_list = production_list)

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
            dout = group_data(dout[0].get('components', []))
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

class print_bom(BaseHandler):
    def get_component(self, components, name, field='Ref'):
        print("get", components, name)
        for c in components:
            print('>>', c)
            if c.get(field, {}) == name:
                return c
        return {}


    def get(self, name):
        dout = list(self.mdb.production.aggregate([
            {'$match': {'_id': bson.ObjectId(name)}},
            {'$sort': {'components.Ref': 1}}
        ]))[0]
        print(dout)


        pdf = FPDF('P', 'mm', format='A4')
        pdf.add_font('pt_sans', '', 'static/pt_sans/PT_Sans-Web-Regular.ttf', uni=True)
        pdf.add_font('pt_sans-bold', '', 'static/pt_sans/PT_Sans-Web-Bold.ttf', uni=True)
        pdf.add_page()

        pdf.set_font('pt_sans', '', 12)

        pdf.set_xy(10, 10)
        pdf.cell(0,5, dout.get('name', name))

        pdf.set_font('pt_sans', '', 8)

        row = []
        used = []

        df = pd.DataFrame(dout['components'])
        df = df.sort('Ref')
        print(df)
        grouped = df.groupby(by=['Value', 'Footprint'])

        rowh = 8

        pdf.set_xy(10, 28)
        for i, c in enumerate(grouped.groups):
            
            indexes = list(grouped.groups[c])
            ref = []
            for j, index in enumerate(indexes):
                component = df.loc[[index]]
                ref.append(component['Ref'].values[0])
            pdf.set_xy(10, 28+i*rowh+3)
            pdf.cell(0, 5, str(len(ref))+'x', border=0)

            
            pdf.set_xy(15, 28+i*rowh+3)
            #pdf.cell(0, 5, component, border=0)
            pdf.cell(0, 5, repr(self.get_component(dout['components'], component['Ref'].values[0])))

            pdf.set_xy(3, 28+i*rowh)
            pdf.cell(0, 5, ', '.join(ref), border=0)

            pdf.set_xy(55, 28+i*rowh)
            pdf.cell(0, 5, component['Value'].values[0])
            pdf.set_xy(95, 28+i*rowh)
            pdf.cell(0, 5, component['Footprint'].values[0])


            print("=============================================================")
            #pdf.cell(100, 5, repr(cg[0]))
            #pdf.set_x(95)
            #pdf.cell(100, 5, repr(cv[0]))


        pdf.output("static/production.pdf")
        with open('static/production.pdf', 'rb') as f:
            self.set_header("Content-Type", 'application/pdf; charset="utf-8"')
            self.set_header("Content-Disposition", "inline; filename=UST_osazovaci_list.pdf")
            self.write(f.read())
        f.close()



'''
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








    def get(self, name):
        

        dout = list(self.mdb.production.aggregate([
            {'$match': {'_id': bson.ObjectId(name)}},
            {'$sort': {'components.Ref': 1}}
        ]))[0]
        print(dout)


        pdf = FPDF('P', 'mm', format='A4')
        pdf.add_font('pt_sans', '', 'static/pt_sans/PT_Sans-Web-Regular.ttf', uni=True)
        pdf.add_font('pt_sans-bold', '', 'static/pt_sans/PT_Sans-Web-Bold.ttf', uni=True)
        pdf.add_page()

        pdf.set_font('pt_sans', '', 12)

        pdf.set_xy(10, 10)
        pdf.cell(0,5, dout.get('name', name))

        pdf.set_font('pt_sans', '', 8)

        row = []
        used = []

        df = pd.DataFrame(dout['components'])
        df = df.sort('Ref')
        print(df)
        grouped = df.groupby(by=['Value', 'Footprint'])

        rowh = 8

        pdf.set_xy(10, 28)
        ref = []
        for j, index in enumerate(indexes):
            component = df.loc[[index]]
            ref.append(component['Ref'].values[0])
        pdf.set_xy(10, 28+i*rowh+3)
        pdf.cell(0, 5, str(len(ref))+'x', border=0)

        
        pdf.set_xy(15, 28+i*rowh+3)
        pdf.cell(0, 5, self.get_component(dout['components'], ref).get('MFPN'), border=0)

        pdf.set_xy(3, 28+i*rowh)
        pdf.cell(0, 5, ', '.join(ref), border=0)

        pdf.set_xy(55, 28+i*rowh)
        pdf.cell(0, 5, component['Value'].values[0])
        pdf.set_xy(95, 28+i*rowh)
        pdf.cell(0, 5, component['Footprint'].values[0])


        print("=============================================================")
        #pdf.cell(100, 5, repr(cg[0]))
        #pdf.set_x(95)
        #pdf.cell(100, 5, repr(cv[0]))


        pdf.output("static/production.pdf")
        with open('static/production.pdf', 'rb') as f:
            self.set_header("Content-Type", 'application/pdf; charset="utf-8"')
            self.set_header("Content-Disposition", "inline; filename=UST_osazovaci_list.pdf")
            self.write(f.read())
        f.close()










'''