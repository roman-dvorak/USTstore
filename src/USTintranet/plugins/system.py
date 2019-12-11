import json

from plugins import BaseHandler, get_company_info, get_dpp_params


def make_handlers(module, plugin):
    handlers = [
        (r'/{}/parameters'.format(module), plugin.ParametersHandler),
        (r'/{}'.format(module), plugin.SystemHandler),
        (r'/{}/'.format(module), plugin.SystemHandler), ]
    return handlers


def plug_info():
    return {
        "module": "system",
        "name": "system"
    }


class SystemHandler(BaseHandler):
    def get(self):
        self.render('system.homepage.hbs', warehouses=self.get_warehouseses())

    def post(self):
        operation = self.get_argument('operation')
        if operation == 'set_warehouse':
            self.set_cookie("warehouse", self.get_argument('warehouse'))
            print("Nastaveno cookie pro vybrany warehouse")


class ParametersHandler(BaseHandler):

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

        self.redirect("/system/parameters")
