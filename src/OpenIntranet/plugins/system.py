import json

from bson import ObjectId

from plugins import BaseHandler, get_company_info, get_dpp_params


def get_plugin_handlers():
    plugin_name = get_plugin_info()["name"]

    handlers = [
        (r'/{}/parameters'.format(plugin_name), ParametersHandler),
        (r'/{}/api/objectid'.format(plugin_name), ApiObjectIdHandler),
        (r'/{}'.format(plugin_name), SystemHandler),
        (r'/{}/'.format(plugin_name), SystemHandler), ]
    return handlers


def get_plugin_info():
    return {
        "name": "system",
        "entrypoints": [
            {
                "title": "Systém",
                "url": "/system",
                "icon": "settings",
            }
        ],
        #"role": ['sudo', 'sudo-system', 'system-user']
    }


class SystemHandler(BaseHandler):
    def get(self):
        self.render('system.homepage.hbs', warehouses=self.get_warehouseses(), is_authorized=self.is_authorized)

    def post(self):
        operation = self.get_argument('operation')
        if operation == 'set_warehouse':
            self.set_cookie("warehouse", self.get_argument('warehouse'))
            print("Nastaveno cookie pro vybrany warehouse")


# TODO validovat vstup
class ParametersHandler(BaseHandler):
    role_module = ["sudo"]

    def get(self):
        self.render("system.parameters.hbs",
                    company_info=get_company_info(self.mdb),
                    dpp_params=get_dpp_params(self.mdb))

    def post(self):
        company_name = self.get_argument("company_name")
        company_address = self.get_argument("company_address")
        company_crn = self.get_argument("company_crn")
        dpp_year_max_hours = self.get_argument("dpp_year_max_hours")
        dpp_month_max_gross_wage = self.get_argument("dpp_month_max_gross_wage")
        dpp_tax_rate = self.get_argument("dpp_tax_rate")
        dpp_tax_deduction = self.get_argument("dpp_tax_deduction")
        dpp_tax_deduction_student = self.get_argument("dpp_tax_deduction_student")

        company_info = {}
        dpp_params = {}

        if company_name:
            company_info["name"] = company_name

        if company_address:
            company_info["address"] = company_address

        if company_crn:
            company_info["crn"] = company_crn

        if dpp_year_max_hours:
            dpp_params["year_max_hours"] = int(dpp_year_max_hours)

        if dpp_month_max_gross_wage:
            dpp_params["month_max_gross_wage"] = int(dpp_month_max_gross_wage)

        if dpp_tax_rate:
            dpp_params["tax_rate"] = int(dpp_tax_rate)

        if dpp_tax_deduction:
            dpp_params["tax_deduction"] = int(dpp_tax_deduction)

        if dpp_tax_deduction_student:
            dpp_params["tax_deduction_student"] = int(dpp_tax_deduction_student)

        if company_info:
            self.mdb.intranet.update_one({"_id": "company_info"},
                                         {"$set": company_info})
        if dpp_params:
            self.mdb.intranet.update_one({"_id": "dpp_params"},
                                         {"$set": dpp_params})

        self.redirect("/system/parameters")




class ApiObjectIdHandler(BaseHandler):

    def get(self):
        self.write(str(ObjectId()))
