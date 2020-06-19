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



class print_home(BaseHandler):

    def get(self):
        print("Tisk home page   ...")
        self.render('print.home.hbs')


class print_label_default(BaseHandler):
    def get(self):
        print("Tisk home page   ...")
        self.render('print.home.hbs')



class print_packet_list(BaseHandler):

    def get(self):
        print("Tisk home page   ...")
        self.render('print.home.hbs')




class print_label(BaseHandler):
    def get(self):
        print("Tisk stitku...")
        items = self.get_argument('items', '')
        data_type = self.get_argument('type')
        end = self.get_argument('end', False)

        oids = []
        for iid in items.split(','):
            oids.append(ObjectId(iid))

        dbobject = self.mdb.label_generation.insert({
                'type': data_type,
                'items': oids
            })
        self.render('print.label.hbs', print_task = dbobject)

class generate_label(BaseHandler):
    def post(self):
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

        if group == 'positions':

            length = len(items)

            items = list(self.mdb.store_positions.find({
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

            for i, position in enumerate(items):
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
                pdf.cell(70, 0, position['name'][:25], align = 'C')

                pdf.set_font('pt_sans', '', 11)
                pdf.set_xy(x0+3.5, y0+13.5)
                pdf.multi_cell(70-4, 3.4, position['text'], align='L')

                pdf.set_text_color(100)
                # pdf.set_font('pt_sans', '', 8)
                # pdf.set_xy(x0+2, y0+2.5)
                # pdf.cell(70, 0, "Pozice: {}".format(warehouse_name))

                id = str(position['_id'])
                barcode = "pos"+str(int(id, 16))
                code128.image(barcode).save("static/tmp/barcode/%s.png"%(id))
                pdf.set_xy(x0+2.5, y0+21)
                pdf.image('static/tmp/barcode/%s.png'%(id), w = 70-5, h=7)

                pdf.set_font('pt_sans', '', 7)
                pdf.set_xy(x0, y0+30)
                pdf.cell(70, 0, barcode, align = 'C')

                pdf.set_font('pt_sans', '', 7)
                pdf.set_xy(x0+3.5, y0+33)
                pdf.cell(70, 0, "{} | {}".format(warehouse_name, datetime.datetime.now().strftime("%d. %m. %Y, %H:%M")))


            pdf.output('static/tmp/{}.pdf'.format(task), 'F')

            gen_time = datetime.datetime(2018, 10, 1)
            lastOid = ObjectId.from_datetime(gen_time)

            print(self.get_warehouse())

            self.write('/static/tmp/{}.pdf'.format(task))

        else:
            self.write("OK")
