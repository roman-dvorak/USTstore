from datetime import datetime

from bson import ObjectId


class BaseField:
    field = ""
    serialize = "a"

    def __get__(self, instance, owner):
        raise NotImplementedError()


class IdField(BaseField):

    def __init__(self, serialize=True):
        self.field = "_id"
        self.serialize = serialize

    def __get__(self, instance, owner):
        return instance._mdoc[self.field]


class ValueField(BaseField):

    def __init__(self, field, *, settable=True, deletable=True, serialize=True):
        self.field = field
        self.settable = settable
        self.deletable = deletable
        self.serialize = serialize
        if not serialize:
            print(self.field, "is not serialized")

    def __get__(self, instance, owner):
        if self.field in instance._updates:
            return instance._updates[self.field]

        return instance._get_from_mdoc(self.field)

    def __set__(self, instance, value):
        if not self.settable and not instance._i_know_what_im_doing:
            raise PermissionError(f"Field {self.field} není zapisovatelný.")

        self.validate(value)

        instance._process_updates({self.field: value})

    def validate(self, value):
        pass


class StringField(ValueField):

    def validate(self, value):
        if not isinstance(value, str):
            raise TypeError("StringField může obsahovat jen str objekty.")


class IntegerField(ValueField):

    def validate(self, value):
        if not isinstance(value, int):
            raise TypeError("IntegerField může obsahovat jen int objekty.")


class FloatField(ValueField):

    def validate(self, value):
        if not isinstance(value, float):
            raise TypeError("FloatField může obsahovat jen float objekty.")


class BooleanField(ValueField):

    def validate(self, value):
        if not isinstance(value, bool):
            raise TypeError("BooleanField může obsahovat jen bool objekty.")


class DateField(ValueField):

    def validate(self, value):
        if not isinstance(value, datetime):
            raise TypeError("DateField může obsahovat jen datetime objekty.")


class ObjectIdField(ValueField):

    def validate(self, value):
        if not isinstance(value, ObjectId):
            raise TypeError("ObjectIdField může obsahovat jen ObjectId objekty.")


class EnumerationField(ValueField):

    def __init__(self, field, enumeration, *, settable=True, deletable=True):
        super().__init__(field, settable=settable, deletable=deletable)

        self.enumeration = enumeration

    def validate(self, value):
        if value not in self.enumeration:
            raise TypeError("Tento EnumerationField může obsahovat jen tyto objekty:", self.enumeration)


class ArrayField(ValueField):

    # TODO try other iterables
    def validate(self, value):
        if not isinstance(value, list):
            raise TypeError("ArrayField může obsahovat jen list objekty.")


class SingleEmbeddedField(BaseField):

    def __init__(self, type_, serialize=True):
        self.type = type_
        self.field = self.type.FIELD
        self.serialize = serialize

    def __get__(self, instance, owner):
        if not instance._cache.get(self.field, None):
            instance._cache[self.field] = self.type(instance._database,
                                                    instance.id,
                                                    instance._get_from_mdoc(self.field))

        return instance._cache[self.field]


class ArrayOfEmbeddedField(BaseField):

    def __init__(self, type_, serialize=True):
        self.type = type_
        self.field = self.type.FIELD
        self.serialize = serialize

    def __get__(self, instance, owner):
        if not instance._cache.get(self.field, None):
            instance._cache[self.field] = tuple(self.type(instance._database, instance.id, mdoc)
                                                for mdoc in instance._get_from_mdoc(self.field))

        return instance._cache[self.field]
