#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from .. import Intranet
from .. import BaseHandler
import json
import bson.json_util
import urllib
import datetime
import json
import code128

from fpdf import FPDF
from bson import ObjectId
from plugins import BaseHandler
from pystrich.datamatrix import DataMatrixEncoder

class print_label_default(BaseHandler):
    def get(self):
        print("Tisk home page   ...")
        self.render('print.home.hbs')


class print_packet_list(BaseHandler):

    def get(self):
        print("Tisk home page   ...")
        self.render('print.home.hbs')

class print_label(BaseHandler):

    def gen_pdf(self, data):

            pdf = FPDF('P', 'mm', format='A4')
            pdf.set_auto_page_break(False)

            pdf.add_font('pt_sans', '', 'static/pt_sans/PT_Sans-Web-Regular.ttf', uni=True)
            pdf.add_font('pt_sans-bold', '', 'static/pt_sans/PT_Sans-Web-Bold.ttf', uni=True)
            pdf.set_font('pt_sans', '', 11)
            pdf.add_page()
            page = 0
            skip = 0
            warehouse_name = self.get_warehouse().get('name', "Neni nastaven")

            for i, label in enumerate(data):
                print(".....")
                print(label)
                packet = label['packet']
                pdf.set_text_color(0)

                ir = i + skip
                ip = ir%(3*7)
                row  = ip//3
                cell  = ip%3
                print(i, ir, ip, row, cell)
                if page != (ir//(3*7)):
                    print("NOVA STRANKA", ir//(3*7))
                    pdf.add_page()
                    page = ir//(3*7)

                x0 = 70*cell
                y0 = (297/7)*row

                # Barevne pozadi stitku
                #pdf.set_draw_color(231, 221, 25)
                # pdf.set_fill_color(161, 255, 161)
                # pdf.rect(x0, y0, w=70, h=297/7, style = 'F')

                # nazev soucastky
                pdf.set_font('pt_sans-bold', '', 12)
                pdf.set_xy(x0+4, y0+6.5)
                pdf.cell(70-4, 0, label['component']['name'][:25], align = 'L')

                # # bile pozadi pod carovym kodem
                # pdf.set_fill_color(255,255,255)
                # pdf.rect(x0, y0+9, w=70, h=13.5, style = 'F')

                # #carovy kod
                # id = str(packet['_id'])
                # barcode = str(int(id, 16))
                # code128.image(barcode).save("static/tmp/barcode/%s.png"%(id))
                print(label.keys())
                id = str(label['_id'])

                barcode = "[)>\u001E06"     # format 06 header
                barcode += "\u001D1T{}".format(label['_id'])  ##
                barcode += "\u001D1P{}".format(label['component']['_id'])       # component identificator by supplier
                # barcode += "\u001D30P{}".format(label['component']['name'])    # Component identificator by supplier - 1st level
                barcode += "\u001D5D{}".format(datetime.datetime.now().strftime("%y%m%d"))
                barcode += "\u001E\u0004"   # end of barcode
                encoder = DataMatrixEncoder(barcode)
                encoder.save("static/tmp/barcode/%s.png"%(id))

                pdf.set_xy(x0+70-20-4, y0+8+7)
                pdf.image('static/tmp/barcode/%s.png'%(id), w = 20, h=20)
                # pdf.set_font('pt_sans', '', 6)
                # pdf.set_text_color(100)
                # pdf.set_xy(x0+0, y0+7)
                # pdf.cell(65, 0, id, align = 'R')


                # Popis stitku
                pdf.set_font('pt_sans', '', 8)
                pdf.set_xy(x0+4, y0+17)
                pdf.multi_cell(70-28, 2.8, label['component']['description'], align='L')

                # pozice ve skaldu

                pdf.set_text_color(100)
                pdf.set_xy(x0+4, y0+8.8)
                if "warehouse" in label:
                    pos = "/"
                    for p in label['path']:
                        pos += p['name'] + "/"

                    pdf.set_font('pt_sans-bold', '', 10)
                    pdf.write(5, label['warehouse']['code'].upper())
                    pdf.set_font('pt_sans', '', 8)
                    pdf.write(5, pos)
                    pdf.set_font('pt_sans-bold', '', 10)
                    pdf.write(5, label['position']['name'])
                else:
                    pdf.set_font('pt_sans', '', 10)
                    pdf.write(5, "Mimo skladu")

                if "category" in label:
                    pos = []
                    for c in label['category']:
                        pos += [c['name']]

                    pos = ','.join(pos)

                    pdf.set_xy(x0+4, y0+12)
                    pdf.set_font('pt_sans', '', 10)
                    pdf.write(5, pos)

                pdf.set_font('pt_sans', '', 7)
                pdf.set_xy(x0, y0+37)
                pdf.cell(70, 0, "UST.cz | {} | {}".format(datetime.datetime.now().strftime("%d. %m. %Y, %H:%M"), id), align="C")


            task = "tisk"

            pdf.output('static/tmp/{}.pdf'.format(task), 'F')
            gen_time = datetime.datetime(2018, 10, 1)
            lastOid = ObjectId.from_datetime(gen_time)


            self.redirect('/static/tmp/{}.pdf'.format(task))


    def get(self):

        print("Tisk stitky...")

        groups = self.get_arguments('group[]')
        for i, g in enumerate(groups):
            if g == "None": groups[i] = None
            else: groups[i] = ObjectId(g)

        print("Mam tisknout skupiny", groups)

        labels = list(self.mdb.label_list.aggregate([
            {"$match": {"group" : {"$in" : groups}}},
            {
               "$lookup": {
                   "from": 'stock',
                   "localField": 'id',
                   "foreignField": 'packets._id',
                   "as": 'component',
               }
            },
            {"$set": { "component": { "$first": "$component" }}   },

            {
              "$lookup":
                 {
                   "from": "stock",
                   "let": { "packet": "$id"},
                   "pipeline": [
                      { "$unwind": '$packets'},
                      { "$match": { "$expr": { "$eq": ["$packets._id", "$$packet"]} }},
                      { "$replaceRoot": {"newRoot": "$packets"}},
                   ],
                   "as": "packet"
                 }
            },
            {"$set": { "packet": { "$first": "$packet" }} },

            {
               "$lookup": {
                   "from": 'store_positions',
                   "localField": 'packet.position',
                   "foreignField": '_id',
                   "as": 'position',
               }
            },
            {"$set": { "position": { "$first": "$position" }} },

            {
               "$graphLookup": {
                  "from": 'store_positions',
                  "startWith": '$position.parent',
                  "connectFromField": "parent",
                  "connectToField": "_id",
                  "as": 'path'
               }
            },

            {
               "$lookup": {
                   "from": 'warehouse',
                   "localField": 'position.warehouse',
                   "foreignField": '_id',
                   "as": 'warehouse',
               }
            },
            {"$set": { "warehouse": { "$first": "$warehouse" }} },


            {
               "$lookup": {
                   "from": 'category',
                   "localField": 'component.category',
                   "foreignField": '_id',
                   "as": 'category',
               }
            },
            {
               "$graphLookup": {
                  "from": 'store_positions',
                  "startWith": '$category.parent',
                  "connectFromField": "parent",
                  "connectToField": "_id",
                  "as": 'path_cat'
               }
            },


        ]))

        #print(labels)
        self.gen_pdf(labels)
        #self.write(bson.json_util.dumps(labels))
        # self.render('print.label.hbs', print_task = dbobject)



class generate_label(BaseHandler):
    def get(self):

        task = self.get_argument('task', None)
        skip = int(self.get_argument('skip', 0))
        if task:
            print(task)
            task_data = self.mdb.label_generation.find_one({'_id': ObjectId(task)})
            print(task_data)
            group = task_data['type']
            items = task_data['items']
        else:
            data = self.get_argument('data', None)
            group = self.get_argument('group', None)

        if group == 'labels':

            length = len(items)

            items = list(self.mdb.store_labels.find({
              "_id" : {"$in" : items }
            }))


            pdf = FPDF('P', 'mm', format='A4')
            pdf.set_auto_page_break(False)

            pdf.add_font('pt_sans', '', 'static/pt_sans/PT_Sans-Web-Regular.ttf', uni=True)
            pdf.add_font('pt_sans-bold', '', 'static/pt_sans/PT_Sans-Web-Bold.ttf', uni=True)
            pdf.set_font('pt_sans', '', 12)
            pdf.add_page()
            page = 0

            warehouse_name = self.get_warehouse().get('name', "Neni nastaven")

            for i, label in enumerate(items):
                pdf.set_text_color(0)

                ir = i + skip
                ip = ir%(3*7)
                row  = ip//3
                cell  = ip%3
                print(i, ir, ip, row, cell)
                if page != (ir//(3*7)):
                    print("NOVA STRANKA", ir//(3*7))
                    pdf.add_page()
                    page = ir//(3*7)

                x0 = 70*cell
                y0 = (297/7)*row

                #pdf.set_draw_color(231, 221, 25)
                pdf.set_fill_color(231, 121, 25)
                pdf.set_xy(x0, y0+4)
                pdf.rect(x0, y0+12.5, w=70, h=8.4, style = 'F')

                pdf.set_font('pt_sans-bold', '', 14)
                pdf.set_xy(x0, y0+8.5)
                pdf.cell(70, 0, label['name'][:25], align = 'C')

                pdf.set_font('pt_sans', '', 11)
                pdf.set_xy(x0+3.5, y0+13.5)
                pdf.multi_cell(70-4, 3.4, label['text'], align='L')

                pdf.set_text_color(100)
                # pdf.set_font('pt_sans', '', 8)
                # pdf.set_xy(x0+2, y0+2.5)
                # pdf.cell(70, 0, "Pozice: {}".format(warehouse_name))

                id = str(position['_id'])

                barcode_content = "[)>\u001E06\u001DL{posID}\u001DT{packetId}\u001D1P{componentId}\u001D5D{Date}\u001E\u0004".format(posID = "", packetId = id, componentId = "", Date = "20200101")
                encoder = DataMatrixEncoder(a)
                encoder.save("static/tmp/barcode/%s.png"%(id))


                pdf.set_font('pt_sans', '', 7)
                pdf.set_xy(x0, y0+30)
                pdf.cell(70, 0, barcode, align = 'C')

                pdf.set_font('pt_sans', '', 7)
                pdf.set_xy(x0+3.5, y0+33)
                pdf.cell(70, 0, "{} | {}".format(warehouse_name, datetime.datetime.now().strftime("%d. %m. %Y, %H:%M")))


                print(label['category'])


            pdf.output('static/tmp/{}.pdf'.format(task), 'F')

            gen_time = datetime.datetime(2018, 10, 1)
            lastOid = ObjectId.from_datetime(gen_time)

            print(self.get_warehouse())

            self.write('/static/tmp/{}.pdf'.format(task))

        else:
            self.write("OK")
