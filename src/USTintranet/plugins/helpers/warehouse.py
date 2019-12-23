


def get_article_counts(article):
	if 'overview' in article:
		return article['overview']['count']	
	else:
		raise("Missing 'overview' parameter in article record")



def get_article_counts_in_warehouse(db, article_id, warehouse_id):
	if 'overview' in article:
		bilance = article["overview"]['stocks'].get(str(warehouse_id), None)
		if bilance:
			return bilance['count']
		else:
			return {'onstock':0, 'requested':0, 'ordered':0}
	else:
		raise("Missing 'overview' parameter in article record")


def get_article_price(article):
	warehouse_price = 0
	count = 0
	missing_count = article['overview']['count']['onstock']

	history_records = article.get('history', [])[::-1]
	for history in history_records:
		if history.get('operation', None) in ['buy', 'inventory']:
			record_price = history.get('price', 0)
			record_count = history['bilance']
			if record_count > missing_count:
				record_count = missing_count

			if record_price > 0 and missing_count > 0:
				count += record_count
				warehouse_price += record_price * record_count
				missing_count -= record_count

	if count:
		warehouse_price /= count
	else:
		warehouse_price = 0

	#print("Skladova cena polozky je:", warehouse_price, "pocet je", count)
	return warehouse_price


def update_article_price(db, article_id):
	article = db.find_one({"_id": article_id})
	price = get_article_price(article)
	db.update({"_id": article_id}, {"$set":{"warehouse_unit_price": price}})
	return price


def has_article_inventory(article, inventory_id, stocks = None):
	out = {}
	history_records = article.get('history', [])[::-1]
	for history in history_records:
		if history.get('operation', None) in ['inventory']:
			if history.get('inventory', None) == inventory_id:
				if 'stock' in history:
					out[history['stock']] = True
	return out

def get_current_inventory(db):
    current_id = db.intranet.find_one({'_id': 'stock_taking'})
    current = list(db.stock_taking.find({'_id': current_id['current']}))[0]
    return current




def get_warehouse_count(article, warehouse_id):
	count = article['overview'].get('stocks', {}).get(str(warehouse_id), {}).get('count', {'onstock': 0})['onstock']
	return count
