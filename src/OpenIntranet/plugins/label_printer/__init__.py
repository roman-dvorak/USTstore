from . import printer


def get_plugin_handlers():
    base_name = "labels"

    handlers = [
        (r'/{}'.format(base_name), printer.print_home),
        (r'/{}/packet'.format(base_name), printer.print_packet_list),
        (r'/{}/label'.format(base_name), printer.print_label),
        (r'/{}/generate_label'.format(base_name), printer.generate_label)
        ]
    return handlers

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
