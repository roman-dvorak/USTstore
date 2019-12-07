import pymongo

DB_NAME = "USTintranet"
COMPANY_INFO_MDOC = {
    "_id": "company_info",
    "name": "Universal Scientific Technologies s.r.o.",
    "address": "U Jatek 19, 392 01 Soběslav",
    "crn": "28155319"
}
DPP_PARAMETERS_MDOC = {
    "_id": "dpp_params",
    "year_max_hours": 300,
    "month_max_gross_wage": 10_000,
    "tax_rate": 15,
    "tax_deduction": 2070,
    "tax_deduction_student": 335,
}


def add_mdoc(coll: pymongo.collection.Collection, mdoc: dict):
    mdoc_filter = {"_id": mdoc["_id"]}

    current_mdoc_in_db = coll.find_one(mdoc_filter)

    if current_mdoc_in_db is not None:
        print(f"Stávanící mdokument '{mdoc['_id']}': {current_mdoc_in_db}")
        rewrite = input(f"'{mdoc['_id']}' mdokument už v kolekci existuje, mám ho přepsat (a/N)? ")
        if rewrite.lower() not in ["a", "ano", "y", "yes"]:
            print("Zachovávám původní mdokument.")
            return

        coll.delete_one(mdoc_filter)

    coll.insert_one(mdoc)
    print(f"Přidán mdokument {mdoc['_id']}")


if __name__ == '__main__':
    intranet = pymongo.MongoClient()[DB_NAME].intranet

    add_mdoc(intranet, COMPANY_INFO_MDOC)
    add_mdoc(intranet, DPP_PARAMETERS_MDOC)
