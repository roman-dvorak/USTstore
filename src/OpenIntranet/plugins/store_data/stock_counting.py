

def getLastInventory(component, until, use_count = False):
    count = None
    if use_count: count = component['count']
    for x in reversed(component.get('history', [])):
        if x.get('operation', None) == 'inventory':
            print(x['_id'].generation_time.date(), until.date())
            print(x['_id'].generation_time.date() > until.date())
            if x['_id'].generation_time.date() > until.date():
                count = x['absolute']
                break;

    return count


def getInventory(component, fro = None, to = None, use_count = False):
    count = 0
    price = 0
    if use_count: count = component['count']
    for x in reversed(component.get('history', [])):
        if x.get('operation', None) == 'inventory':
            print(x['_id'].generation_time.date())
            if (fro and x['_id'].generation_time.date() > fro.date()) and (to and x['_id'].generation_time.date() < to.date()):
                print("selected!!!! ", fro.date(), x["_id"].generation_time.date(), to.date())
                price = x.get('price', None)
                count = x.get('bilance', None)
                break;

    return (count, price)

def getInventoryRecord(mdb, pid):
    query = [
        {'$match': {"pid": pid, "type": "inventory"}},
    ]
    out = list(mdb.stock_operation.aggregate(query))
    
    return out

def isInventoryDone(mdb, pid, inventory = None):
    if not inventory:
        inventory = getInventoryId(mdb)
    inventories = getInventoryRecord(mdb, pid)
    count = 0
    for i in inventories:
        if i.get('inventory_id', None) == inventory:
            count += 1
    return count

## 
##   Vrati ID aktualni inventury
##
def getInventoryId(mdb):
    current_id = mdb.intranet.find_one({'_id': 'stock_taking'})
    return current_id.get('current', None)

##
##  Vrati informace o aktualni inventure
##
def getInventoryData(mdb):
    current_id = getInventoryId(mdb)
    current = list(self.mdb.stock_taking.find({'_id': current_id}))[0]
    return current

def getPrice(component):
    count = component['count']
    rest = count 
    price = 0
    first_price = 0
    for x in reversed(component.get('history', [])):
        if x.get('price', 0) > 0:
            if first_price == 0: 
                first_price = x['price']
            if x['bilance'] > 0:
                if x['bilance'] <= rest:
                    price += x['price']*x['bilance']
                    rest -= x['bilance']
                else:
                    price += x['price']*rest
                    rest = 0

    print("Zbývá", rest, "ks, secteno", count-rest, "za cenu", price)
    if(count-rest): price += rest*first_price

    component['price_sum'] = price
    return price