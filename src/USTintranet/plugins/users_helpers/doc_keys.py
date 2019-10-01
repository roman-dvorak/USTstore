USER_DOC_KEYS = [
    "user",
    "pass",
    "email",
    "email_validate",
    "role",
    "created",
    "type",
    "name",
    "birthdate",
    "addresses",
    "phone_number",
    "account_number",
    "assignment",
    "contracts",
    "skills",
    "notes",
    "work_spans",
    "vacations",
    "documents",
    "wages",
    "month_closed",
]
NAME_DOC_KEYS = [
    "pre_name_title",
    "first_name",
    "surname",
    "post_name_title",
]
ADDRESS_DOC_KEYS = [
    "street",
    "city",
    "state",
    "zip",
    "type",
]
CONTRACT_DOC_KEYS = [
    "_id",
    "type",
    "signing_date",
    "valid_from",
    "valid_until",
    "hour_rate",
    "is_signed",
]
DOCUMENT_DOC_KEYS = [
    "type",
    "valid_from",
    "valid_until",
    "path_to_file",
    "invalidated",  # datetime zrušení, key existuje jen pokud smlouva byla předčasně zrušena
]
VACATION_DOC_KEYS = [
    "from",
    "until",
    "do_not_disturb",
]
WAGE_DOC_KEYS = [
    "month",
    "hours_worked",
    "gross_wage",
    "is_taxed",
    "net_wage",
]
WORKSPAN_DOC_KEYS = [
    "from",
    "hours",
    "note",
    "assignment",
]