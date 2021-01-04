from pymongo.database import Database


class DbWithBulkOps(Database):
    """
    Tato třída přidává zjednodušený koncept bulk operací k pymongo.database.Database třídě. Objekty této třídy jsou
    zaměnitelné s běžnými databázovými objekty, ale tato třída je zamýšlena především pro využítí s objekty potomků
    abstraktních tříd pro obalení mdokumentů. Metoda add_operation() požaduje jako parametr wrapper_object,
    což je právě reference na takový obalovací objekt, jehož dat se daná operace týká. Toto umožňuje v případě např.
    chybného vstupu do fieldu wrapper_objectu stornovat všechny operace s tímto objektem pomocí
    clear_operations(wrapper_object).
    """
    def __init__(self, client, name, **kwargs):
        super().__init__(client, name, **kwargs)
        self._operations = {}

    def add_operation(self, wrapper_object, operation):
        if wrapper_object not in self._operations:
            self._operations[wrapper_object] = []

        self._operations[wrapper_object].append(operation)

    def write_operations(self):
        operations_by_collection = {}

        for wrapper_object, operations in self._operations.items():
            if wrapper_object.COLLECTION not in operations_by_collection:
                operations_by_collection[wrapper_object.COLLECTION] = []

            operations_by_collection[wrapper_object.COLLECTION] += operations

        for collection, operations in operations_by_collection.items():
            self[collection].bulk_write(operations)

    def clear_operations(self, wrapper_object=None):
        if wrapper_object:
            self._operations.pop(wrapper_object, None)
        else:
            self._operations = {}
