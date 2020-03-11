from pymongo.database import Database


class DbWrapper(Database):

    def __init__(self, client, name, **kwargs):
        super().__init__(client, name, **kwargs)
        self._operations = {}

    def add_operation(self, collection, operation):
        if collection not in self._operations:
            print("-> adding collection", collection)
            self._operations[collection] = []

        self._operations[collection].append(operation)

    def write_operations(self):
        print("write_operations", self._operations)
        for collection, ops in self._operations.items():
            self[collection].bulk_write(ops)

    def clear_operations(self, collection=None):
        if collection:
            self._operations.pop(collection, None)
        else:
            self._operations = {}
