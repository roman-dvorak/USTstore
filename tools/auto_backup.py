import subprocess
import owncloud
import configparser
import os
import datetime
import shutil

location_config = '/data/ust/intranet.conf'


with open(location_config, 'r') as f:
    config_string = '[root]\n' + f.read()
config = configparser.ConfigParser()
config.read_string(config_string)

url = (str(config['root']['owncloud_url']).replace("'", ""))
user = (str(config['root']['owncloud_user']).replace("'", ""))
pasw = (str(config['root']['owncloud_pass']).replace("'", ""))
root = (str(config['root']['owncloud_root']).replace("'", ""))
print(url, user, pasw, root)

local = "tmp/mdb/"
remote = os.path.join(root, 'backup', datetime.datetime.now().strftime('%Y/%Y%m%d_%H%M'))

subprocess.run(["mongodump", "--out="+local])

oc = owncloud.Client(url)
oc.login(user, pasw) 

tpath = ""
for x in remote.split('/'):
	try:
		tpath += x + '/'
		print(tpath)
		oc.mkdir(tpath)
	except Exception as e:
		print(e)

oc.put_directory(remote, local)
shutil.rmtree(local, ignore_errors=True)
print("Done")