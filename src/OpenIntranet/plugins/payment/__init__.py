from .payment import home
from .. import BaseHandler


def get_plugin_handlers():
    plugin_name = get_plugin_info()["module"]

    return [
        (r'/{}'.format(plugin_name), home),
        (r'/{}/'.format(plugin_name), home),
    ]


def get_plugin_info():
    return {
        "module": "payment",
        "name": "Platby",
    }
