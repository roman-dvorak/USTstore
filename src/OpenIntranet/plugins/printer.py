#!/usr/bin/python3
# -*- coding: utf-8 -*-

import tornado.escape
import tornado.web
import tornado.websocket
from . import Intranet
from . import BaseHandler
import json
import bson.json_util
import urllib
import datetime
import json
import code128

from fpdf import FPDF
from bson import ObjectId
from plugins import BaseHandler


def make_handlers(module, plugin):
    handlers = [
        (r'/{}/label'.format(module), plugin.print_label),
        (r'/{}/generate_label'.format(module), plugin.generate_label)
        ]
    return handlers


def plug_info():
    return {
        "module": "printer",
        "name": "tisk"
    }



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
                ip = ir%(3*8)
                row  = ip//3
                cell  = ip%3
                print(i, ir, ip, row, cell)
                if page != (ir//(3*8)):
                    print("NOVA STRANKA", ir//(3*8))
                    pdf.add_page()
                    page = ir//(3*8)

                x0 = 70*cell
                y0 = 37.125*row

                #pdf.set_draw_color(231, 221, 25)
                pdf.set_fill_color(231, 121, 25)
                pdf.set_xy(x0, y0+2)
                pdf.rect(x0, y0+9.5, w=70, h=8.5, style = 'F')

                pdf.set_font('pt_sans-bold', '', 14)
                pdf.set_xy(x0, y0+6.5)
                pdf.cell(70, 0, position['name'][:25], align = 'C')

                pdf.set_font('pt_sans', '', 11)
                pdf.set_xy(x0+2, y0+10.5)
                pdf.multi_cell(70-4, 3, position['text'], align='L')

                pdf.set_text_color(100)
                pdf.set_font('pt_sans', '', 8)
                pdf.set_xy(x0+2, y0+2.5)
                pdf.cell(70, 0, "Pozice: {}".format(warehouse_name))

                id = str(position['_id'])
                barcode = "pos"+str(int(id, 16))
                code128.image(barcode).save("static/tmp/barcode/%s.png"%(id))
                pdf.set_xy(x0+1, y0+18)
                pdf.image('static/tmp/barcode/%s.png'%(id), w = 70-2, h=9)

                pdf.set_font('pt_sans', '', 8)
                pdf.set_xy(x0, y0+29)
                pdf.cell(70, 0, barcode, align = 'C')

                pdf.set_font('pt_sans', '', 6)
                pdf.set_xy(x0+2, y0+31.5)
                pdf.cell(70, 0, "Generovano {}".format(datetime.datetime.now().strftime("%d. %m. %Y, %H:%M")))
            

            pdf.output('static/tmp/{}.pdf'.format(task), 'F')

            gen_time = datetime.datetime(2018, 10, 1)
            lastOid = ObjectId.from_datetime(gen_time)

            print(self.get_warehouse())

            self.write('/static/tmp/{}.pdf'.format(task))

        else:
            self.write("OK")
