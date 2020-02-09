

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

def getInventoryRecord(component, inventory, stock):
    count = 0
    price = 0    
    for x in reversed(component.get('history', [])):
        if x.get('operation', None) == 'inventory' and x.get('inventory', None) == inventory and x.get('stock', None) == stock['_id']:
            price = x.get('price', None)
            count = x.get('bilance', None)
            return(x)
    return None

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