from .store import hand_bi_home as home
from .store import get_plugin_handlers as handlers
from .component import get_plugin_handlers as handlers_2

from .. import BaseHandler


def get_plugin_handlers():
    return handlers() + handlers_2()


def get_plugin_info():
    return {
        "name": "store",
        "entrypoints": [
            {
                "title": "Sklad",
                "url": "/store",
                "icon": "store",
            }
        ]
    }
