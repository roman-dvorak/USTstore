from .backend import orders


def get_plugin_handlers():
    order_base_name = "order"

    return [
        #(r'/{}/u/(.*)'.format(order_base_name), users.UserPageHandler),
        (r'/{}'.format(order_base_name), orders.HomeHandler),
        (r'/{}/'.format(order_base_name), orders.HomeHandler),
    ]


def get_plugin_info():
    return {
        "name": "order",
        "entrypoints": [
            {
                "url": "/order",
                "title": "Zakázky",
                "icon": 'queue',
            },
        ]
    }
