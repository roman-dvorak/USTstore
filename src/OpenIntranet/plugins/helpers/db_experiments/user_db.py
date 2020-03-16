from datetime import datetime

from plugins.helpers.db_experiments.db_wrappers import SingleEmbeddedMdocWrapper, EmbeddedMdocWithIdWrapper, \
    TopLevelMdocWrapper
from plugins.helpers.db_experiments.db_fields import StringField, IntegerField, FloatField, BooleanField, DateField, \
    ObjectIdField, EnumerationField, ArrayField, SingleEmbeddedField, ArrayOfEmbeddedField


class Name(SingleEmbeddedMdocWrapper):
    COLLECTION = "users"
    FIELD = "name"

    pre_name_title = StringField("pre_name_title")
    first_name = StringField("first_name")
    surname = StringField("surname")
    post_name_title = StringField("post_name_title")


# TODO dát adresám _id a chovat se k nim jako k normálním embedded
class Address(EmbeddedMdocWithIdWrapper):
    COLLECTION = "users"
    FIELD = "addresses"

    street = StringField("street")
    city = StringField("city")
    state = StringField("state")
    zip = StringField("zip")

    type = EnumerationField("type", ["residence", "contact"], settable=False, deletable=False)


class Contract(EmbeddedMdocWithIdWrapper):
    COLLECTION = "users"
    FIELD = "contracts"

    type = EnumerationField("type", ["dpp", "dpp_preview"], settable=False, deletable=False)
    signing_date = DateField("signing_date", settable=False, deletable=False)
    signing_place = DateField("signing_place", settable=False, deletable=False)
    valid_from = DateField("valid_from", settable=False, deletable=False)
    valid_until = DateField("valid_until", settable=False, deletable=False)
    hour_rate = IntegerField("hour_rate", settable=False, deletable=False)
    file = ObjectIdField("file", settable=False, deletable=False)
    scan_file = ObjectIdField("scan_file", settable=False, deletable=False)

    invalidation_date = DateField("invalidation_date")

    @classmethod
    def new_preview(cls, database,
                    user_id,
                    type_,
                    signing_date,
                    signing_place,
                    valid_from,
                    valid_until,
                    hour_rate,
                    file_id):
        contract = cls._new_empty(database, user_id)
        with contract.i_know_what_im_doing():
            contract.type = type_
            contract.signing_date = signing_date
            contract.signing_place = signing_place
            contract.valid_from = valid_from
            contract.valid_until = valid_until
            contract.hour_rate = hour_rate
            contract.file = file_id

    def unmark_as_preview(self):
        with self.i_know_what_im_doing():
            self.type = self.type.replace("_preview", "")

        return self

    def add_scan_file(self, scan_file_id):
        with self.i_know_what_im_doing():
            self.scan_file = scan_file_id

        return self

    def _invalidation_date_validator(self, value):
        if not (self.valid_from <= value <= self.valid_until):
            raise ValueError("Datum zneplatnění musí být mezi daty začátku a konce platnosti smlouvy.")


class Document(EmbeddedMdocWithIdWrapper):
    COLLECTION = "users"
    FIELD = "documents"

    type = EnumerationField("type", ["study_certificate", "tax_declaration"], settable=False, deletable=False)
    valid_from = DateField("valid_from", settable=False, deletable=False)
    valid_until = DateField("valid_until", settable=False, deletable=False)
    invalidation_date = DateField("invalidation_date", settable=False, deletable=False)
    file = ObjectIdField("file", settable=False, deletable=False)

    @classmethod
    def new(cls, database, user_id, type_, file):
        return cls._new_empty(database, user_id)._process_updates({
            "type": type_,
            "file": file,
        })


class Vacation(EmbeddedMdocWithIdWrapper):
    COLLECTION = "users"
    FIELD = "vacations"

    from_ = DateField("from")
    to = DateField("to")

    @classmethod
    def new(cls, database, user_id, from_, to):
        return cls._new_empty(database, user_id)._process_updates({
            "from": from_,
            "to": to
        })


class Workspan(EmbeddedMdocWithIdWrapper):
    COLLECTION = "users"
    FIELD = "workspans"

    from_ = DateField("from", settable=False, deletable=False)
    hours = FloatField("hours", settable=False, deletable=False)
    contract = ObjectIdField("contract", settable=False, deletable=False)
    notes = StringField("notes")

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


class User(TopLevelMdocWrapper):
    COLLECTION = "users"

    user = StringField("user", settable=False, deletable=False)
    role = ArrayField("role")
    created = DateField("created", settable=False, deletable=False)
    type = EnumerationField("type", ["user"], settable=False, deletable=False)
    email_validated = EnumerationField("email_validated", ["no", "pending", "yes"])
    months_closed = ArrayField("months_closed")
    account_number = StringField("account_number")
    assignment = StringField("assignment")
    birthdate = DateField("birthdate")
    email = StringField("email")
    notes = StringField("notes")
    phone_number = StringField("phone_number")
    skills = StringField("skills")

    name = SingleEmbeddedField(Name)
    addresses = ArrayOfEmbeddedField(Address)
    contracts = ArrayOfEmbeddedField(Contract)
    documents = ArrayOfEmbeddedField(Document)
    vacations = ArrayOfEmbeddedField(Vacation)
    workspans = ArrayOfEmbeddedField(Workspan)

    @classmethod
    def new(cls, database, user_name, user_id=None):
        return User._new_empty(database, user_id)._process_updates({
            "user": user_name,
            "type": "user",
            "email_validated": "no",
            "role": []
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

    directory = StringField("directory", settable=False, deletable=False)
    filename = StringField("filename", settable=False, deletable=False)

    @classmethod
    def new(cls, database, directory, filename):
        return cls._new_empty(database)

    def get_url(self, version=-1):
        return

    def add_version(self, url):
        return self


class Report(TopLevelMdocWrapper):
    COLLECTION = "users_reports"

    type = EnumerationField("type", ["accountant_report", "hours_worked_report"], settable=False, deletable=False)
    month = DateField("month", settable=False, deletable=False)
    file = ObjectIdField("file", settable=False, deletable=False)
    up_to_date = BooleanField("up_to_date")
