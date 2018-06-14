#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
from . import BaseHandler
#from pyoctopart.octopart import Octopart
import json
import bson.json_util
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
             (r'/%s/api/(.*)/' %module, plugin.api),
             (r'/{}/operation/(.*)/'.format(module), plugin.operation)
        ]

def plug_info():
    return{
        "module": "store",
        "name": "Správce skladu",
        "icon": 'icon_sklad.svg'
    }


class print_layout(BaseHandler):
    def get(self, data = None):
        out_type = self.get_argument('type', 'html')
        components = self.get_arguments('action[]', [])
        multiply = int(self.get_argument('multiply', 5))
        layout = self.get_argument('template', '70x40_simple')
        skip = int(self.get_argument('skip', 0))
        print(components)
        if len(components) > 0:
            comp = self.mdb.stock.find({'_id' : {'$in' : components}})
        else:
            comp = self.mdb.stock.find().sort([("category", 1), ("_id",1)])
        page = 0

        if layout == 'souhrn_01':
            autori = self.get_arguments('autor', None)
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


            data = self.mdb.stock.find({})
            for i, component in enumerate(data):


                try:
                    if pdf.get_y() > pdf.h-20:
                        pdf.line(10, pdf.get_y(), pdf.w-10, pdf.get_y())
                        pdf.add_page()

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

                    pdf.set_font('pt_sans', '', 10)

                    count = 0
                    price = 0
                    for x in component['stock']:
                        count += float(component['stock'][x]['count'])
                    price = float(component['price'])
                    money_sum += (price*count)
                    if price == 0.0 and count > 0:
                        Err.append('Polozka >%s< nulová cena, nenulový počet' %(component['_id']))

                    print(i, component)
                    pdf.set_x(10)
                    pdf.cell(100, 5, component['_id'])

                    pdf.set_x(95)
                    pdf.cell(10, 5, "%5.d" %(count), align='R')

                    pdf.set_x(120)
                    pdf.cell(10, 5, "%6.2f Kč" %(price), align='R')

                    pdf.set_font('pt_sans-bold', '', 10)
                    pdf.set_x(180)
                    pdf.cell(10, 5, "%6.2f Kč" %(price*count), align='R', ln=2)


                except Exception as e:
                    Err.append('Err' + repr(e) + component['_id'])
                    print(e)

            pdf.line(10, pdf.get_y(), pdf.w-10, pdf.get_y())
            pdf.set_font('pt_sans', '', 8)
            pdf.set_x(180)
            pdf.cell(10, 5, "Konec souhrnu", align='R')

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



class api(BaseHandler):
    def post(self, data=None):
        self.set_header('Content-Type', 'application/json')
        #print(">>", data)
        #print(self.request.arguments)

        ascii_list_to_str = lambda input: [x.decode('ascii') for x in input]
        ascii_list_to_str = lambda input: [str(x, 'utf-8') for x in input]

        if data == 'product':
            print(self.request.arguments.get('selected[]', None))
            dout = list(self.mdb.stock.find({self.get_argument('key', '_id'):self.get_argument('value','')}).sort([("_id",1)]))
            dout += [list(self.mdb.stock_movements.aggregate([{
                '$match':{'product': self.get_argument('value', '')}
                },{
                    '$group' : {
                        '_id' : '$stock',
                        'bilance': { '$sum': '$bilance' },
                    }
                }]))]

        elif data == 'products':
            polarity = '$nin' if (self.request.arguments.get('polarity', ['true'])[0] == b'true') else '$in'
            tag_polarity = True if (self.request.arguments.get('tag_polarity', ['true'])[0] == b'true') else False
            selected = (self.request.arguments.get('selected[]', []))
            page = self.get_argument('page', 0)
            page_len = 100
            search = self.get_argument('search')#.decode('ascii')
            tag_search = self.get_argument('tag_search')#.decode('ascii')
            print("SEARCH", search)
            dout = []

            dbcursor = self.mdb.stock.aggregate([
                {"$unwind": "$_id"},
                {"$sort" : {"category": 1,"_id": 1} },
                {"$match": {'$or':[
                                    {'_id': { '$regex': search, '$options': 'ix'}},
                                    {'name': { '$regex': search, '$options': 'ix'}},
                                    {'description': { '$regex': search, '$options': 'ix'}} ]}
                },{
                    "$match": {'category': {polarity: ascii_list_to_str(selected)}}
                },{
                    "$match": {'tags.'+tag_search : {"$exists" : tag_polarity}}
                },{
                    "$lookup":{
                        "from": "category",
                        "localField": "category",
                        "foreignField": "name",
                        "as": "category"
                    }
                },{
                    '$skip' : int(page_len)*int(page)
                },{
                    '$limit' : int(page_len)
                }], useCursor=True)

            dout = list(dbcursor)
            #print(dout)
            print("POCET polozek je", len(dout))

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
            print(self.get_argument('json', [None]))
            false = False
            true = True
            new_json = eval(self.request.arguments.get('json', [None])[0])
            print("Update product with parameters:")
            print(new_json)

            ## Pokud neni zarazen do zadne kategorie dat ho do Nezarazeno
            if len(new_json['category']) == 0:
                new_json['category'] += ['Nezařazeno']

            dout = (self.mdb.stock.update({"_id": new_json['_id']},new_json, upsert=True))

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
            dbcursor = self.mdb.stock_movements.aggregate([
                    {
                        "$match": {"product": self.get_argument('key')}
                    },{
                        "$sort" : {"_id": -1} 
                    },{
                        "$limit": 500
                    }
                ], useCursor = True)
            dout = list(dbcursor)

            print("Output type", output_type)
            if output_type == "html_tab":
                self.set_header('Content-Type', 'text/html; charset=UTF-8')
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

        output = bson.json_util.dumps(dout)
#        print(output)
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
            operations = self.mdb.stock_movements.find({'product': comp})
            counts = list(self.mdb.stock_movements.aggregate([
                    {'$match':{
                        "product": comp
                        }
                    },
                    {'$group':{
                        '_id': '$stock',
                        'count': {"$sum": '$bilance'}
                        }
                    }]))
            self.render("store.comp_operation.{}.hbs".format(data), last = operations, counts = counts)
        elif data == 'service_push': # vlozeni 'service do skladu'
            comp = self.get_argument('component')
            stock = self.get_argument('stock')
            description = self.get_argument('description', '')
            bilance = self.get_argument('offset')

            print("service_push >>", comp, stock, description, bilance)
            self.mdb.stock_movements.insert({'stock': stock, 'product': comp, 'bilance': float(bilance), 'description':description, 'user':self.logged})
            self.LogActivity('store', 'operation_service')
            self.write("ACK");


        #nakup jedne polozky do skladu. Musi obsahovat: cena za ks, pocet ks, obchod, faktura, ...
        elif data == 'buy':
            comp = self.get_argument('component')
            operations = self.mdb.stock_movements.find({'product': comp})
            counts = list(self.mdb.stock_movements.aggregate([
                    {'$match':{
                        "product": comp
                        }
                    },
                    {'$group':{
                        '_id': '$stock',
                        'count': {"$sum": '$bilance'}
                        }
                    }]))
            
            self.render("store.comp_operation.{}.hbs".format(data), last = operations, counts = counts)

        elif data == 'buy_push': # vlozeni 'service do skladu'
            comp = self.get_argument('component');
            stock = self.get_argument('stock');
            description = self.get_argument('description', '');
            bilance = self.get_argument('count');
            invoice = self.get_argument('invoice', '');
            price = self.get_argument('price');

            print("buy_push >>", comp, stock, description, bilance, invoice, price)
            self.mdb.stock_movements.insert({'stock': stock, 'operation':'buy', 'product': comp, 'bilance': float(bilance), 'price': float(price), 'invoice': invoice,  'description':description, 'user':self.logged})
            self.LogActivity('store', 'operation_service')
            self.write("ACK");
        else: 
            self.write('''

                <h2>AAA {} {}</h2>


            '''.format(data, self.get_argument('component')))
