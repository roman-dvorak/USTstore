from . import printer
from .. import BaseHandler
import datetime
import bson


def get_plugin_handlers():
    base_name = "labels"

    handlers = [
        (r'/{}'.format(base_name), print_home),
        (r'/{}/packet'.format(base_name), printer.print_packet_list),
        (r'/{}/label'.format(base_name), printer.print_label),
        (r'/{}/print'.format(base_name), printer.print_label),
        (r'/{}/generate_label'.format(base_name), printer.generate_label),
        (r'/{}/remove_label'.format(base_name), remove_label),
        (r'/{}/hide_group'.format(base_name), hide_group),
        (r'/{}/add_packet_to_group'.format(base_name), add_packet_to_group),
        (r'/{}/get_grouped_labels'.format(base_name), get_grouped_labels),
        (r'/{}/set_label_group'.format(base_name), set_label_group),
        (r'/{}/print_position_labels'.format(base_name), print_position_labels),
        ]
    return handlers

class print_home(BaseHandler):
    def get(self):
        print("Tisk home page   ...")
        self.render('print.home.hbs')

class add_packet_to_group(BaseHandler):
    def post(self):
        pid = self.get_argument('packet')
        count = self.get_argument('count', 1)
        group = self.get_argument('group', None)
        author = None
        date = datetime.datetime.utcnow()

        self.mdb.label_list.insert({
            'type': 'packet',
            'id': bson.ObjectId(pid),
            'count': count,
            'group': group,
            'author': self.actual_user['_id'],
            'date': date
        })
        self.write('done')


class create_group(BaseHandler):
    def post(self):
        author = None
        name = self.get_argument('name')
        date = datetime.datetime.utcnow()

        self.mdb.label_group.insert({
            'name': name,
            'author': self.actual_user['_id'],
            'show': 1,
            'date': date,
            'printed': None
        })

        self.write('done')

class remove_label(BaseHandler):
    def post(self):
        label_id = bson.ObjectId(self.get_argument('label'))

        self.mdb.label_list.delete_one({'_id': label_id})
        self.write('done')

class hide_group(BaseHandler):
    def post(self):
        group = self.get_argument('group')
        if group is not "none":
            group_id = bson.ObjectId(group)

            self.mdb.label_groups.update_one({"_id": group_id},
                {"$set": {"show": 0}})

        self.write('done')


class get_grouped_labels(BaseHandler):
    def get(self):
        method = self.get_argument('method', 'render')

        packet_query = [
            {
                "$match": {"$or": [
                    {"show": {"$exists": 0}},
                    {"show": {"$gte": 1}}
                ]}
            },
            {
               "$lookup": {
                   "from": 'label_list',
                   "localField": '_id',
                   "foreignField": 'group',
                   "as": 'labels',
               }
            },
            {
                "$unwind": {
                    "path":"$labels",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
               "$lookup": {
                    "from": 'stock',
                    "let": { "packet_id": "$labels.id" },
                    "pipeline": [
                        {"$match": { "$expr": { "$in": ["$$packet_id", "$packets._id"]}}},
                    ],
                    "as": "labels.item"
               }
            },
            {
                "$group": {
                    "_id": '$_id',
                    "root": { "$mergeObjects": '$$ROOT' },
                    "name": {"$last": '$name' },
                    "labels": {"$push": '$labels' },
                }
            },
            {
                "$replaceRoot": {
                    "newRoot": {
                        "$mergeObjects": ['$root', '$$ROOT']
                    }
                }
            },
            {
                "$project": {
                    "root": 0
                }
            },
            {
                "$sort": {"name":1}
            }
        ]

        data = list(self.mdb.label_groups.aggregate(packet_query))

        if method == 'json':
            self.set_header('Content-Type', 'application/json')
            self.write(bson.json_util.dumps(data))

        elif method == 'render':
            self.render('print.list.hbs', groups = data)

class set_label_group(BaseHandler):
    def post(self):
        label = bson.ObjectId(self.get_argument('label'))
        group = self.get_argument('group')
        if group == "None":
            group = None
        else:
            group = bson.ObjectId(group)

        self.mdb.label_list.update({'_id': label}, {"$set":{"group":group}})

        self.write("ok")


def get_plugin_info():
    return {
        "name": "label_printer",
        "entrypoints": [
            {
                "url": "/labels",
                "title": "Tisk štítků",
                "icon": 'print',
            }
        ]
    }



class print_position_labels(BaseHandler):
    def post(self):

        posid = self.get_arguments('pid[]')
        type = self.get_argument('type')
        print("Chci stitky do", posid)

        posid = [bson.ObjectId(x) for x in posid]
        group_id = bson.ObjectId()

        print(posid)

        pos_data = list(self.mdb.store_positions.find({'_id': posid[0]}))[0]
        print(pos_data)

        # Vytvoreni skupiny
        self.mdb.label_groups.insert({
            '_id': group_id,
            'name': 'Print group: ' + pos_data['name']
        })

        for pos in posid:
            if type in ['all', 'position']:
                # Vlozit vsechny sacky do tiskoveho seznamu
                self.mdb.label_list.insert({
                        'type': 'position',
                        'id': pos,
                        'count': 1,
                        'group': group_id,
                        'author': self.actual_user['_id'],
                        'date': datetime.datetime.now()
                })


            if type in ['all', 'packets', 'packet']:
                # Zikat sacky v pozici
                packets = list(self.mdb.stock.aggregate([
                    {"$unwind": '$packets'},
                    {"$match": {"packets.position": pos }}
                ]))

                for packet in packets:
                    self.mdb.label_list.insert({
                        'type': 'packet',
                        'id': packet['packets']['_id'],
                        'count': 1,
                        'group': group_id,
                        'author': self.actual_user['_id'],
                        'date': datetime.datetime.now()
                    })

        self.write("ok")
