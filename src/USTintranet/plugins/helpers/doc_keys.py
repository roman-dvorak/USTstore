USER_DOC_KEYS = [
    "user",
    "pass",
    "email",
    # "email_validate",  # <- deprecated key
    "email_validated",  # values "no", "pending", "yes"
    "email_validation_token",
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
    "workspans",
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
    "signing_place",
    "valid_from",
    "valid_until",
    "hour_rate",
    "file",
    "scan_file",
    "invalidated",  # datetime zrušení, key existuje jen pokud smlouva byla předčasně zrušena
]
DOCUMENT_DOC_KEYS = [
    "type",
    "valid_from",
    "valid_until",
    "file",
    "invalidated",  # datetime zrušení, key existuje jen pokud dokument byl předčasně zrušen
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
    "assignment",
]

OWNCLOUD_DOC_KEYS = [
    "_id",
    "versions",
    "directory",
    "filename",  # jméno souboru tak jak ho uživatel dá do ukládací fce
]

OWNCLOUD_VERSION_DOC_KEYS = [
    "url",
    "by",
    "when",
    "path",  # skutečná cesta k souboru na owncloudu (s id a verzí)
]
