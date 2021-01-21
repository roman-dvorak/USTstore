import csv
import pymongo
import json
import urllib.request
import re
import sys

client = pymongo.MongoClient('localhost', 27017)
db = client.USTdev

db.stock.update({}, {"$unset": {"stock":1, "aid":1, "position": 1, "overview": 1}}, multi=True);