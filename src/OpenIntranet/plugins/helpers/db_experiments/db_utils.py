from datetime import datetime

from bson import ObjectId
from contextlib import contextmanager
from pymongo.operations import InsertOne, UpdateOne, DeleteOne

from plugins import DbWrapper
from plugins.helpers.db_experiments.db_experiments_utils import get_embedded_mdoc_by_id

"""
Design practices:

Wrappery jsou abstraktní, na ty nemá "uživatel", tj. běžný kód v systému, co sahat. Jsou určeny pro dědění.
Každá třída dědící TopLevelMdocWrapper a EmbeddedMdocWithIdWrapper by měla definovat classmethod new nebo new_*
s inicializačními parametry, v těchto metodách lze volat cls._new_empty() pro obecnou inicializaci.
Třídy reprezentující mutable objekty v databázi by měly pro přímé nastavování fieldů implementovat self.set() 
s parametry odpovídajícími jménům fieldů, v těchto metodách lze volat self._process_updates(updates) pro uložení změn.

Všechny public metody, jejichž účelem není vracet data, by měly vracet self.
"""


class MdocWrapper:
    COLLECTION = ""

    def __init__(self, database: DbWrapper, mdoc=None):
        self._cache = {}

        self._database = database
        self._mdoc = mdoc
        self._is_mdoc_up_to_date = True

        if not self.COLLECTION:
            raise ValueError("The COLLECTION constant must be defined in this class.")

        self._collection = self._database[self.COLLECTION]
        self._i_know_what_im_doing = False

    @contextmanager
    def i_know_what_im_doing(self):
        try:
            self._i_know_what_im_doing = True
            yield
        finally:
            self._i_know_what_im_doing = False

    def _get_from_mdoc(self, field):
        if not self._is_mdoc_up_to_date:
            self.reload_from_database()

        return self._mdoc.get(field, None)

    def _add_operation(self, operation):
        self._database.add_operation(self.COLLECTION, operation)

    def _process_updates(self, updates):
        raise NotImplementedError()

    def reload_from_database(self):
        raise NotImplementedError()

    def clear_cache(self):
        self._cache = {}

        return self


class TopLevelMdocWrapper(MdocWrapper):

    @classmethod
    def _new_empty(cls, database, _id=None):
        if not _id:
            _id = ObjectId()

        mdoc = {"_id": _id}

        obj = cls(database, mdoc)
        obj._add_operation(InsertOne(mdoc))

        return obj

    @classmethod
    def from_id(cls, database, _id):
        obj = cls(database=database, mdoc={"_id": _id})
        obj._is_mdoc_up_to_date = False

        return obj

    @classmethod
    def get_all(cls, database, **query_by):
        mdocs = database[cls.COLLECTION].find(query_by)

        return tuple(cls(database, mdoc) for mdoc in mdocs)

    def _process_updates(self, updates: dict):
        if updates:
            self._add_operation(UpdateOne({"_id": self.id}, {"$set": updates}))

        return self

    @property
    def id(self):
        return self._mdoc["_id"]

    def reload_from_database(self):
        self._mdoc = self._collection.find_one({"_id": self.id})
        self.clear_cache()

        return self

    def delete(self):
        self._add_operation(DeleteOne({"_id": self.id}))

        return self


class EmbeddedMdocWrapper(MdocWrapper):
    FIELD = ""

    def __init__(self, database, parent_id, mdoc=None):
        super().__init__(database=database, mdoc=mdoc)

        self._parent_id = parent_id

        if not self.FIELD:
            raise ValueError("The FIELD constant must be defined in this class.")

    def reload_from_database(self):
        raise NotImplementedError()


class EmbeddedMdocWithIdWrapper(EmbeddedMdocWrapper):

    @classmethod
    def _new_empty(cls, database, parent_id, embedded_id=None):
        """
        This class method is lazy, obj.write_operations() must be called afterwards!

        Adds new embedded document represented by the class to an array of specified parent mdoc in database.
        Every mdoc of this type must have an id, if none is provided, a new id is generated (text version of ObjectID).

        :param database: MongoDB database object
        :param parent_id: _id of parent mdoc
        :param embedded_id: _id of the new embedded document
        :return: object representing new embedded document
        """
        if not embedded_id:
            embedded_id = str(ObjectId())

        mdoc = {"_id": embedded_id}
        obj = cls(database, parent_id, mdoc)
        update = UpdateOne({"_id": parent_id}, {
            "$push": {
                cls.FIELD: mdoc
            }
        })

        obj._add_operation(update)

        return obj

    @classmethod
    def from_id(cls, database, parent_id, embedded_id):
        obj = cls(database=database, parent_id=parent_id, mdoc={"_id": embedded_id})
        obj._is_mdoc_up_to_date = False

        return obj

    def _process_updates(self, updates):
        if updates:
            set_dict = {f"{self.FIELD}.$.{key}": value for key, value in updates.items()}

            self._add_operation(UpdateOne({"_id": self._parent_id, f"{self.FIELD}._id": self.id},
                                          {"$set": set_dict}))

        return self

    @property
    def id(self):
        return self._mdoc["_id"]

    def reload_from_database(self):
        self._mdoc = get_embedded_mdoc_by_id(self._collection, self._parent_id, self.FIELD, self.id)
        self.clear_cache()

        return self

    def delete(self):
        update = {"$pull": {
            self.FIELD: {
                "_id": self.id
            }
        }}
        self._add_operation(UpdateOne({"_id": self._parent_id}, update))

        return self


class SingleEmbeddedMdocWrapper(EmbeddedMdocWrapper):

    def _process_updates(self, updates):
        if updates:
            set_dict = {f"{self.FIELD}.{key}": value for key, value in updates.items()}

            self._add_operation(UpdateOne({"_id": self._parent_id},
                                          {"$set": set_dict}))

        return self

    def reload_from_database(self):
        res = self._collection.find_one({"_id": self._parent_id}, {self.FIELD: 1})

        self._mdoc = res.get(self.FIELD, {}) if res else {}

        return self


class ValueField:

    def __init__(self, field, *, settable=True, deletable=True):
        self.field = field
        self.settable = settable
        self.deletable = deletable

    def __get__(self, instance, owner):
        return instance._get_from_mdoc(self.field)

    def __set__(self, instance, value):
        if not self.settable and not instance._i_know_what_im_doing:
            raise PermissionError(f"Field {self.field} is not settable.")

        self._validate(value)

        instance._process_updates({self.field: value})

    def _validate(self, value):
        return True


class StringField(ValueField):

    def _validate(self, value):
        if not isinstance(value, str):
            raise TypeError("StringField can only contain str objects.")


class IntegerField(ValueField):

    def _validate(self, value):
        if not isinstance(value, int):
            raise TypeError("IntegerField can only contain str objects.")


class FloatField(ValueField):

    def _validate(self, value):
        if not isinstance(value, float):
            raise TypeError("FloatField can only contain str objects.")


class BooleanField(ValueField):

    def _validate(self, value):
        if not isinstance(value, bool):
            raise TypeError("BooleanField can only contain bool objects.")


class DateField(ValueField):

    def _validate(self, value):
        if not isinstance(value, datetime):
            raise TypeError("DateField can only contain datetime objects.")


class ObjectIdField(ValueField):

    def _validate(self, value):
        if not isinstance(value, ObjectId):
            raise TypeError("ObjectIdField can only contain ObjectId objects.")


class EnumerationField(ValueField):

    def __init__(self, field, enumeration, *, settable=True, deletable=True):
        super().__init__(field, settable=settable, deletable=deletable)

        self.enumeration = enumeration

    def _validate(self, value):
        if value not in self.enumeration:
            raise TypeError("This EnumerationField can only contain these values:", self.enumeration)


class ArrayField(ValueField):

    # TODO try other iterables
    def _validate(self, value):
        if not isinstance(value, list):
            raise TypeError("ArrayField can only contain list objects.")


class SingleEmbeddedField:

    def __init__(self, type_):
        self.type = type_

    def __get__(self, instance, owner):
        field = self.type.FIELD

        if not instance._cache.get(field, None):
            instance._cache[field] = self.type(instance._database,
                                               instance.id,
                                               instance._get_from_mdoc(field))

        return instance._cache[field]


class ArrayOfEmbeddedField:

    def __init__(self, type_):
        self.type = type_

    def __get__(self, instance, owner):
        field = self.type.FIELD

        if not instance._cache.get(field, None):
            instance._cache[field] = tuple(self.type(instance._database, instance.id, mdoc)
                                           for mdoc in instance._get_from_mdoc(field))

        return instance._cache[field]
