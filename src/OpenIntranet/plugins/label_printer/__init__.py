from . import printer
from .. import BaseHandler


def get_plugin_handlers():
    base_name = "labels"

    handlers = [
        (r'/{}'.format(base_name), print_home),
        (r'/{}/packet'.format(base_name), printer.print_packet_list),
        (r'/{}/label'.format(base_name), printer.print_label),
        (r'/{}/generate_label'.format(base_name), printer.generate_label)
        ]
    return handlers

class print_home(BaseHandler):

    def get(self):
        print("Tisk home page   ...")
        self.render('print.home.hbs')


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
