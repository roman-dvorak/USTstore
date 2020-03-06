from collections import namedtuple
from time import sleep

from datetime import datetime
from pymongo.operations import InsertOne, UpdateOne, DeleteOne

from plugins.helpers.db_experiments_utils import cachedproperty, get_embedded_mdoc_by_id, filter_nones_from_dict, \
    chainable

"""
Design practices:

Wrappery jsou abstraktní, na ty nemá "uživatel", tj. běžný kód v systému, co sahat. Jsou určeny pro dědění.
Každá třída dědící TopLevelMdocWrapper a EmbeddedMdocWithIdWrapper by měla definovat classmethod new nebo new_*
s inicializačními parametry, v těchto metodách lze volat cls._new_empty() pro obecnou inicializaci.
Třídy reprezentující mutable objekty v databázi by měly pro přímé nastavování fieldů implementovat self.set() 
s parametry odpovídajícími jménům fieldů, v těchto metodách lze volat self._process_updates(updates) pro uložení změn.

Všechny public metody, jejichž účelem není vracet data, by měly být @chainable.
"""


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

    @chainable
    def clear_operations(self):
        self.__operations = []

    @chainable
    def clear_cache(self):
        try:
            del self.__cachedproperty_cache
        except AttributeError:
            pass

    @chainable
    def write_operations(self):
        if not self.__operations:
            return

        self._collection.bulk_write([oper_dict["operation"] for oper_dict in self.__operations])
        self.clear_operations()
        self._is_mdoc_up_to_date = False


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

    @chainable
    def reload_from_database(self):
        self._mdoc = self._collection.find_one({"_id": self.id})
        self.clear_cache()

    @chainable
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

    @chainable
    def _process_updates(self, updates):
        updates = filter_nones_from_dict(updates)

        set_dict = {f"{self.FIELD}.$.{key}": value for key, value in updates.items()}

        self._add_operation(UpdateOne({"_id": self._parent_id, f"{self.FIELD}._id": self.id},
                                      {"$set": set_dict}))

    @property
    def id(self):
        return self._mdoc["_id"]

    @chainable
    def reload_from_database(self):
        self._mdoc = get_embedded_mdoc_by_id(self._collection, self._parent_id, self.FIELD, self.id)
        self.clear_cache()

    @chainable
    def delete(self):
        update = {"$pull": {
            self.FIELD: {
                "_id": self.id
            }
        }}
        self._add_operation(UpdateOne({"_id": self._parent_id}, update))


class SingleEmbeddedMdocWrapper(EmbeddedMdocWrapper):

    @chainable
    def _process_updates(self, updates):
        updates = filter_nones_from_dict(updates)

        set_dict = {f"{self.FIELD}.{key}": value for key, value in updates.items()}

        self._add_operation(UpdateOne({"_id": self._parent_id},
                                      {"$set": set_dict}))

    @chainable
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

    @classmethod
    def new_preview(cls, database, user_id, type_, file_id):
        if not cls.is_valid_type(type_):
            raise ValueError("Zadaný typ smlouvy není validní.")

        contract = cls._new_empty(database, user_id)
        contract._process_updates({
            "type": f"{type_}_preview",
            "file": file_id,
        })

    @staticmethod
    def is_valid_type(contract_type):
        return contract_type in ("dpp", "dpc", "ps")

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
    def scan_file(self):
        return self._get_from_mdoc("scan_file")

    @property
    def invalidation_date(self):
        return self._get_from_mdoc("invalidation_date")

    @chainable
    def unmark_as_preview(self):
        self._process_updates({"type": self.type.replace("_preview", "")})

    @chainable
    def invalidate(self, invalidation_date: datetime):
        self._process_updates({"invalidation_date": invalidation_date})

    @chainable
    def add_scan_file(self, scan_file_id):
        self._process_updates({"scan_file": scan_file_id})


class Document(EmbeddedMdocWithIdWrapper):
    COLLECTION = "users"
    FIELD = "documents"

    @classmethod
    def new(cls, database, user_id, type_, file):
        return cls._new_empty(database, user_id)._process_updates({
            "type": type_,
            "file": file,
        })

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

    @classmethod
    def new(cls, database, user_id, from_, to):
        return cls._new_empty(database, user_id)._process_updates({
            "from": from_,
            "to": to
        })

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

    @classmethod
    def new(cls, database, user_id, from_, hours, contract_id, notes=None):
        obj = cls._new_empty(database, user_id)
        obj._process_updates({
            "from": from_,
            "hours": hours,
            "contract": contract_id,
            "notes": notes,
        })
        return obj

    @property
    def from_(self):
        return self._get_from_mdoc("from")

    @property
    def hours(self):
        return self._get_from_mdoc("hours")

    @property
    def contract(self):
        return Contract.from_id(self._database, self._parent_id, self._get_from_mdoc("contract"))

    @property
    def notes(self):
        return self._get_from_mdoc("notes")


class User(TopLevelMdocWrapper):
    COLLECTION = "users"

    @classmethod
    def new(cls, database, user_name, user_id=None):
        return User._new_empty(database, user_id)._process_updates({
            "user": user_name,
            "type": "user",
            "email_validated": "no",
            "role": []
        })

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

    def get_active_contract(self, date):
        return

    def get_active_contracts(self, from_date, to_date):
        return

    def get_active_document(self, document_type, date):
        return

    def get_active_documents(self, document_type, from_date, to_date):
        return

    def update_email_validation_status(self, yes=False, no=False, token=None):
        return

    def set_password_change_token(self, token):
        return

    def unset_password_change_token(self):
        return

    def get_workspans(self, from_date, to_date):
        return

    def get_vacations(self, earliest_end, latest_end):
        return

    def is_month_closed(self, month_date):
        return

    def close_month(self, month_date):
        return

    def reopen_month(self, month_date):
        return


class OwnCloudFile(TopLevelMdocWrapper):
    COLLECTION = "owncloud"

    @classmethod
    def new(cls, database, url):
        return cls._new_empty(database)

    @property
    def directory(self):
        return self._get_from_mdoc("directory")

    @property
    def filename(self):
        return self._get_from_mdoc("filename")

    def get_url(self, version=-1):
        return


if __name__ == '__main__':
    import pymongo
    from bson import ObjectId
    from db_experiments_utils import write_operations

    db = pymongo.MongoClient().USTintranet

    u = User.from_id(db, ObjectId("5e2c47a158872d1d9b210a49"))
