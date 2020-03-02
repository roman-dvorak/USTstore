import fpdf
import os

from datetime import datetime

from bson.objectid import ObjectId

import plugins.helpers.str_ops as str_ops
from plugins.helpers.exceptions import MissingInfoHTTPError
from plugins.helpers.mdoc_ops import find_type_in_addresses
from plugins.helpers.doc_keys import NAME_DOC_KEYS

SPACE_SIZE = 6
MULTICELL_SPACE_SIZE = 2
FONT = "DejaVu"
FONT_SIZE = 10
HEADING_SIZE = 16
WIDTH = 35
ONE_LINE_LIMIT = 60

FONT_DIR = os.path.join("static", "dejavu")

ACCOUNT_REPORT_COLUMN_SPACING = [80, 35, 35, 35, 35, 35]
ACCOUNT_REPORT_COLUMN_FORMATTERS = ["{}", "{}", "{} Kč/h", "{} Kč", "{} Kč", "{} Kč"]


class AccountantReport:
    COLUMN_SPACING = [80, 35, 35, 35, 35, 35]
    COLUMN_FORMATTERS = ["{}", "{}", "{} Kč/h", "{} Kč", "{} Kč", "{} Kč"]

    def __init__(self, company_name: str, month_date: datetime, version=0):
        self.sum_hours = 0
        self.sum_gross_wage = 0
        self.sum_net_wage = 0
        self.sum_tax = 0

        file_name = f"accountant_report_{month_date.month}-{month_date.year}_{str(ObjectId())}.pdf"
        self.output_path = os.path.join("static", "tmp", file_name)

        self.pdf = fpdf.FPDF("L", "mm", "A4")
        self.pdf.add_font(FONT, '', os.path.join(FONT_DIR, 'DejaVuSerif.ttf'), uni=True)
        self.pdf.add_font(FONT, 'B', os.path.join(FONT_DIR, 'DejaVuSerif-Bold.ttf'), uni=True)
        self.pdf.add_font(FONT, 'I', os.path.join(FONT_DIR, 'DejaVuSerif-Italic.ttf'), uni=True)

        self.pdf.set_margins(25, 25)

        self.pdf.add_page()

        self.pdf.set_font(FONT, "B", FONT_SIZE)

        self.pdf.cell(w=0, txt=f"{company_name} - období {month_date.month}/{month_date.year}, v{version}")
        self.pdf.ln(2 * SPACE_SIZE)

        self.pdf.set_font(FONT, "", FONT_SIZE)

        for spacing, data in zip(self.COLUMN_SPACING,
                                 ["Jméno", "Počet hodin", "Hodinová sazba", "Hrubá mzda", "Čistá mzda", "Daň"]):
            self.pdf.cell(w=spacing, txt=str(data))

        self.pdf.ln(SPACE_SIZE)

    def add_row(self, name, hours, hour_rate, gross_wage, net_wage, tax):
        self.sum_hours += hours
        self.sum_gross_wage += gross_wage
        self.sum_net_wage += net_wage
        self.sum_tax += tax

        for spacing, formatter, data in zip(self.COLUMN_SPACING, self.COLUMN_FORMATTERS,
                                            [name, hours, hour_rate, gross_wage, net_wage, tax]):
            self.pdf.cell(w=spacing, txt=formatter.format(data))

        self.pdf.ln(SPACE_SIZE)

    def add_sums(self):
        print(self.sum_hours, self.sum_gross_wage, self.sum_net_wage, self.sum_tax)
        self.pdf.ln(SPACE_SIZE)

        for spacing, formatter, data in zip(self.COLUMN_SPACING, self.COLUMN_FORMATTERS,
                                            ["Celkem",
                                             self.sum_hours,
                                             None,
                                             self.sum_gross_wage,
                                             self.sum_net_wage,
                                             self.sum_tax]):
            self.pdf.cell(w=spacing, txt=formatter.format(data) if data is not None else "")

    def save(self):
        self.pdf.output(self.output_path)

        return self.output_path


class HoursWorkedReport:

    def __init__(self, company_name, month_date, version=0):
        self.company_name = company_name
        self.month_date = month_date
        self.version = version

        self.sum_hours = 0

        self.output_name = os.path.join("static", "tmp",
                                        f"hours_report_{month_date.month}-{month_date.year}_{str(ObjectId())}.pdf")

        self.pdf = fpdf.FPDF("P", "mm", "A4")
        self.pdf.add_font(FONT, '', os.path.join(FONT_DIR, 'DejaVuSerif.ttf'), uni=True)
        self.pdf.add_font(FONT, 'B', os.path.join(FONT_DIR, 'DejaVuSerif-Bold.ttf'), uni=True)
        self.pdf.add_font(FONT, 'I', os.path.join(FONT_DIR, 'DejaVuSerif-Italic.ttf'), uni=True)

        self.pdf.set_margins(25, 25)

    def init_page(self, name):
        self.pdf.add_page()
        self.sum_hours = 0

        self.pdf.set_font(FONT, "B", FONT_SIZE)

        self.pdf.cell(w=0, txt=f"{self.company_name} - období {self.month_date.month}/{self.month_date.year}, "
                               f"v{self.version}")
        self.pdf.ln(SPACE_SIZE)
        self.pdf.cell(w=0, txt=name)
        self.pdf.ln(2 * SPACE_SIZE)

        self.pdf.set_font(FONT, "", FONT_SIZE)

        self.pdf.cell(w=10)
        self.pdf.cell(w=40, txt="Datum")
        self.pdf.cell(w=0, txt="Odpracované hodiny")
        self.pdf.ln(SPACE_SIZE)

    def add_row(self, date, hours):
        self.sum_hours += hours

        self.pdf.cell(w=10)
        self.pdf.cell(w=40, txt=f"{date.day}. {date.month}. {date.year}")
        self.pdf.cell(w=0, txt=str(hours))
        self.pdf.ln(SPACE_SIZE)

    def add_sums_and_end_page(self):
        self.pdf.cell(w=10)
        self.pdf.cell(w=40, txt="Celkem")
        self.pdf.cell(w=0, txt=str(self.sum_hours))
        self.pdf.ln(SPACE_SIZE * 2)

        self.pdf.cell(w=0, txt="Podpis zaměstnance:")
        self.pdf.ln(SPACE_SIZE * 3)

        self.pdf.cell(w=0, txt="____________________")

    def save(self):
        self.pdf.output(self.output_name)

        return self.output_name
