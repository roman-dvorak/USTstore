from collections import namedtuple
from time import sleep

from pymongo.operations import InsertOne, UpdateOne, DeleteOne

from plugins.helpers.db_experiments_utils import cachedproperty, get_embedded_mdoc_by_id, filter_nones_from_dict


class MdocWrapper:
    COLLECTION = ""

    def __init__(self, database, mdoc=None):
        self._database = database
        self._mdoc = mdoc
        self._is_mdoc_up_to_date = True

        if not self.COLLECTION:
            raise ValueError("The COLLECTION constant must be defined in this class.")

        self._collection = self._database[self.COLLECTION]
        self.__operations = []

    def _get_from_mdoc(self, field):
        if not self._is_mdoc_up_to_date:
            self.reload_from_database()

        return self._mdoc.get(field, None)

    def _add_operation(self, operation):
        self.__operations.append({
            "collection": self.COLLECTION,
            "operation": operation,
        })

    def reload_from_database(self):
        raise NotImplementedError()

    def get_operations(self):
        return self.__operations

    def clear_operations(self):
        self.__operations = []

    def clear_cache(self):
        try:
            del self.__cachedproperty_cache
        except AttributeError:
            pass

    def write_operations(self):
        if not self.__operations:
            return

        self._collection.bulk_write([oper_dict["operation"] for oper_dict in self.__operations])
        self.clear_operations()
        self._is_mdoc_up_to_date = False


class TopLevelMdocWrapper(MdocWrapper):

    @classmethod
    def new(cls, database, _id=None):
        if not _id:
            _id = ObjectId()

        mdoc = {"_id": _id}

        obj = cls(database, mdoc)
        obj._add_operation(InsertOne(mdoc))

    @classmethod
    def from_id(cls, database, _id):
        obj = cls(database=database, mdoc={"_id": _id})
        obj._is_mdoc_up_to_date = False

        return obj

    @classmethod
    def get_all(cls, database, **query_by):
        mdocs = database[cls.COLLECTION].find(query_by)

        return tuple(cls(database, mdoc) for mdoc in mdocs)

    def _get_tuple_of_embedded_mdocs(self, embedded_wrapper_class):
        if not self._is_mdoc_up_to_date:
            self.reload_from_database()

        return tuple(embedded_wrapper_class(self._database, self.id, mdoc)
                     for mdoc in self._mdoc.get(embedded_wrapper_class.FIELD, []))

    def _process_updates(self, updates: dict):
        updates = filter_nones_from_dict(updates)

        self._add_operation(UpdateOne({"_id": self.id}, {"$set": updates}))

    @property
    def id(self):
        return self._mdoc["_id"]

    def set(self, **kwargs):
        pass

    def reload_from_database(self):
        self._mdoc = self._collection.find_one({"_id": self.id})
        self.clear_cache()

    def delete(self):
        self._add_operation(DeleteOne({"_id": self.id}))


class EmbeddedMdocWrapper(MdocWrapper):
    FIELD = ""

    def __init__(self, database, parent_id, mdoc=None):
        super().__init__(database=database, mdoc=mdoc)

        self._parent_id = parent_id

        if not self.FIELD:
            raise ValueError("The FIELD constant must be defined in this class.")


class EmbeddedMdocWithIdWrapper(EmbeddedMdocWrapper):

    @classmethod
    def new(cls, database, parent_id, embedded_id=None):
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

    @classmethod
    def from_id(cls, database, parent_id, embedded_id):
        obj = cls(database=database, parent_id=parent_id, mdoc={"_id": embedded_id})
        obj._is_mdoc_up_to_date = False

        return obj

    def _process_updates(self, updates):
        updates = filter_nones_from_dict(updates)

        set_dict = {f"{self.FIELD}.$.{key}": value for key, value in updates.items()}

        self._add_operation(UpdateOne({"_id": self._parent_id, f"{self.FIELD}._id": self.id},
                                      {"$set": set_dict}))

    @property
    def id(self):
        return self._mdoc["_id"]

    def reload_from_database(self):
        self._mdoc = get_embedded_mdoc_by_id(self._collection, self._parent_id, self.FIELD, self.id)
        self.clear_cache()

    def delete(self):
        update = {"$pull": {
            self.FIELD: {
                "_id": self.id
            }
        }}
        self._add_operation(UpdateOne({"_id": self._parent_id}, update))


class SingleEmbeddedMdocWrapper(EmbeddedMdocWrapper):

    def _process_updates(self, updates):
        updates = filter_nones_from_dict(updates)

        set_dict = {f"{self.FIELD}.{key}": value for key, value in updates.items()}

        self._add_operation(UpdateOne({"_id": self._parent_id},
                                      {"$set": set_dict}))

    def reload_from_database(self):
        res = self._collection.find_one({"_id": self._parent_id}, {self.FIELD: 1})

        self._mdoc = res.get(self.FIELD, {}) if res else {}


class Name(SingleEmbeddedMdocWrapper):
    COLLECTION = "users"
    FIELD = "name"

    @property
    def pre_name_title(self):
        return self._get_from_mdoc("pre_name_title")

    @property
    def first_name(self):
        return self._get_from_mdoc("first_name")

    @property
    def surname(self):
        return self._get_from_mdoc("surname")

    @property
    def post_name_title(self):
        return self._get_from_mdoc("post_name_title")

    def set(self,
            pre_name_title=None,
            first_name=None,
            surname=None,
            post_name_title=None):
        self._process_updates({
            "pre_name_title": pre_name_title,
            "first_name": first_name,
            "surname": surname,
            "post_name_title": post_name_title
        })


# TODO dát adresám _id a chovat se k nim jako k normálním embedded
class Address(EmbeddedMdocWrapper):
    COLLECTION = "users"
    FIELD = "addresses"

    @property
    def street(self):
        return self._get_from_mdoc("street")

    @property
    def city(self):
        return self._get_from_mdoc("city")

    @property
    def state(self):
        return self._get_from_mdoc("state")

    @property
    def zip(self):
        return self._get_from_mdoc("zip")

    @property
    def type(self):
        return self._get_from_mdoc("type")

    def set(self,
            street=None,
            city=None,
            state=None,
            zip=None):
        pass


class Contract(EmbeddedMdocWithIdWrapper):
    COLLECTION = "users"
    FIELD = "contracts"

    @property
    def type(self):
        return self._get_from_mdoc("type")

    @property
    def signing_date(self):
        return self._get_from_mdoc("signing_date")

    @property
    def signing_place(self):
        return self._get_from_mdoc("signing_place")

    @property
    def valid_from(self):
        return self._get_from_mdoc("valid_from")

    @property
    def valid_until(self):
        return self._get_from_mdoc("valid_until")

    @property
    def hour_rate(self):
        return self._get_from_mdoc("hour_rate")

    @property
    def file(self):
        return self._get_from_mdoc("file")

    @property
    def invalidation_date(self):
        return self._get_from_mdoc("invalidation_date")


class Document(EmbeddedMdocWithIdWrapper):
    COLLECTION = "users"
    FIELD = "documents"

    @property
    def type(self):
        return self._get_from_mdoc("type")

    @property
    def valid_from(self):
        return self._get_from_mdoc("valid_from")

    @property
    def valid_until(self):
        return self._get_from_mdoc("valid_until")

    @property
    def file(self):
        return self._get_from_mdoc("file")

    @property
    def invalidation_date(self):
        return self._get_from_mdoc("invalidation_date")


class Vacation(EmbeddedMdocWithIdWrapper):
    COLLECTION = "users"
    FIELD = "vacations"

    @property
    def from_(self):
        return self._get_from_mdoc("from")

    @property
    def to(self):
        return self._get_from_mdoc("to")

    def set(self,
            from_=None,
            to=None):
        self._process_updates({
            "from": from_,
            "to": to,
        })


class Workspan(EmbeddedMdocWithIdWrapper):
    COLLECTION = "users"
    FIELD = "workspans"

    @property
    def from_(self):
        return self._get_from_mdoc("from")

    @property
    def hours(self):
        return self._get_from_mdoc("hours")

    @property
    def notes(self):
        return self._get_from_mdoc("notes")

    @property
    def contract(self):
        return self._get_from_mdoc("contract")


class User(TopLevelMdocWrapper):
    COLLECTION = "users"

    @property
    def user_name(self):
        return self._get_from_mdoc("user")

    @property
    def role(self):
        return self._get_from_mdoc("role")

    @property
    def created(self):
        return self._get_from_mdoc("created")

    @property
    def type(self):
        return self._get_from_mdoc("type")

    @property
    def email_validated(self):
        return self._get_from_mdoc("email_validated")

    @property
    def months_closed(self):
        return self._get_from_mdoc("months_closed")

    @property
    def account_number(self):
        return self._get_from_mdoc("account_number")

    @property
    def assignment(self):
        return self._get_from_mdoc("assignment")

    @property
    def birthdate(self):
        return self._get_from_mdoc("birthdate")

    @property
    def email(self):
        return self._get_from_mdoc("email")

    @property
    def notes(self):
        return self._get_from_mdoc("notes")

    @property
    def phone_number(self):
        return self._get_from_mdoc("phone_number")

    @property
    def skills(self):
        return self._get_from_mdoc("skills")

    @cachedproperty
    def addresses(self):
        return self._get_tuple_of_embedded_mdocs(Address)

    @cachedproperty
    def name(self):
        return Name(self._database, self.id, self._mdoc.get("name", {}))

    @cachedproperty
    def contracts(self):
        return self._get_tuple_of_embedded_mdocs(Contract)

    @cachedproperty
    def documents(self):
        return self._get_tuple_of_embedded_mdocs(Document)

    @cachedproperty
    def vacations(self):
        return self._get_tuple_of_embedded_mdocs(Vacation)

    @cachedproperty
    def workspans(self):
        return self._get_tuple_of_embedded_mdocs(Workspan)

    def set(self,
            role=None,
            account_number=None,
            assignment=None,
            birthdate=None,
            email=None,
            notes=None,
            phone_number=None,
            skills=None):
        self._process_updates({
            "role": role,
            "account_number": account_number,
            "assignment": assignment,
            "birthdate": birthdate,
            "email": email,
            "notes": notes,
            "phone_number": phone_number,
            "skills": skills,
        })


if __name__ == '__main__':
    import pymongo
    from bson import ObjectId
    from db_experiments_utils import write_operations

    db = pymongo.MongoClient().USTintranet

    u = User.from_id(db, ObjectId("5e2c47a158872d1d9b210a49"))
