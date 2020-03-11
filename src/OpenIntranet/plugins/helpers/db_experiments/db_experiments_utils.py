import functools


def cachedproperty(func):
    func_name = func.__name__

    @property
    @functools.wraps(func)
    def wrapper(self):
        if not hasattr(self, "__cachedproperty_cache"):
            print("no cache, initializing")
            self.__cachedproperty_cache = {}

        if func_name not in self.__cachedproperty_cache:
            print(f"no {func_name} in cache, setting")
            self.__cachedproperty_cache[func_name] = func(self)

        print("content of cache:", self.__cachedproperty_cache.keys())

        return self.__cachedproperty_cache[func_name]

    return wrapper


def get_embedded_mdoc_by_id(coll, parent_id, embedded_field, embedded_id):
    mdoc = coll.find_one({"_id": parent_id, f"{embedded_field}._id": embedded_id},
                         {f"{embedded_field}.$": 1})
    if not mdoc:
        return None

    field_content = mdoc.get(embedded_field, None)

    return field_content[0] if field_content else None


def filter_nones_from_dict(dictionary, inplace=True):
    if not inplace:
        dictionary = dict(dictionary)

    for key in list(dictionary.keys()):
        if dictionary[key] is None:
            del dictionary[key]

    return dictionary


def write_operations(database, operations):
    ops_by_collection = {}

    for op in operations:
        collection = op["collection"]

        if collection not in ops_by_collection:
            ops_by_collection[collection] = []

        ops_by_collection[collection].append(op["operation"])

    for collection, ops in ops_by_collection.items():
        database[collection].bulk_write(ops)

