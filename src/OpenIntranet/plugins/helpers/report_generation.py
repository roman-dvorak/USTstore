import fpdf
import os

from datetime import datetime

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


def accountant_report_init(company_name: str, month_date: datetime):
    pdf = fpdf.FPDF("L", "mm", "A4")
    pdf.add_font(FONT, '', os.path.join(FONT_DIR, 'DejaVuSerif.ttf'), uni=True)
    pdf.add_font(FONT, 'B', os.path.join(FONT_DIR, 'DejaVuSerif-Bold.ttf'), uni=True)
    pdf.add_font(FONT, 'I', os.path.join(FONT_DIR, 'DejaVuSerif-Italic.ttf'), uni=True)

    pdf.set_margins(25, 25)
    pdf.set_font(FONT, "", FONT_SIZE)

    pdf.add_page()

    pdf.cell(w=0, txt=f"{company_name} - období {month_date.month}/{month_date.year}")
    pdf.ln(2 * SPACE_SIZE)

    for spacing, data in zip(ACCOUNT_REPORT_COLUMN_SPACING,
                             ["Jméno", "Počet hodin", "Hodinová sazba", "Hrubá mzda", "Čistá mzda", "Daň"]):
        pdf.cell(w=spacing, txt=str(data))

    pdf.ln(SPACE_SIZE)

    return pdf


def accountant_report_add_row(pdf_file, name, hours, hour_rate, gross_wage, net_wage, tax):
    for spacing, formatter, data in zip(ACCOUNT_REPORT_COLUMN_SPACING, ACCOUNT_REPORT_COLUMN_FORMATTERS,
                                        [name, hours, hour_rate, gross_wage, net_wage, tax]):
        pdf_file.cell(w=spacing, txt=formatter.format(data))

    pdf_file.ln(SPACE_SIZE)


def hours_worked_report_init(company_name, name, month_date):
    pdf = fpdf.FPDF("P", "mm", "A4")
    pdf.add_font(FONT, '', os.path.join(FONT_DIR, 'DejaVuSerif.ttf'), uni=True)
    pdf.add_font(FONT, 'B', os.path.join(FONT_DIR, 'DejaVuSerif-Bold.ttf'), uni=True)
    pdf.add_font(FONT, 'I', os.path.join(FONT_DIR, 'DejaVuSerif-Italic.ttf'), uni=True)

    pdf.set_margins(25, 25)
    pdf.set_font(FONT, "", FONT_SIZE)

    pdf.add_page()

    pdf.cell(w=0, txt=f"{company_name} - období {month_date.month}/{month_date.year}")
    pdf.ln(SPACE_SIZE)
    pdf.cell(w=0, txt=name)
    pdf.ln(2 * SPACE_SIZE)

    pdf.cell(w=10)
    pdf.cell(w=40, txt="Datum")
    pdf.cell(w=0, txt="Odpracované hodiny")
    pdf.ln(SPACE_SIZE)

    return pdf


def hours_worked_report_add_row(pdf_file, date, hours):
    pdf_file.cell(w=10)
    pdf_file.cell(w=40, txt=f"{date.day}. {date.month}. {date.year}")
    pdf_file.cell(w=0, txt=str(hours))
    pdf_file.ln(SPACE_SIZE)


def hours_worked_report_finish(pdf_file, total_hours):
    pdf_file.cell(w=10)
    pdf_file.cell(w=40, txt="Celkem")
    pdf_file.cell(w=0, txt=str(total_hours))
    pdf_file.ln(SPACE_SIZE*2)

    pdf_file.cell(w=0, txt="Podpis zaměstnance:")
    pdf_file.ln(SPACE_SIZE * 3)

    pdf_file.cell(w=0, txt="____________________")
