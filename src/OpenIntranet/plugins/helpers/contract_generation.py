import fpdf
import os

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


def generate_contract(user_id, contract, company_name, company_address, company_crn):
    name = contract.get("name", None)
    if not name:
        raise MissingInfoHTTPError("Chybí jméno uživatele.")

    birthdate = str_ops.date_to_str(contract.get("birthdate", None))
    if not birthdate:
        raise MissingInfoHTTPError("Chybí datum narození.")

    address = contract.get("address", None)
    if not address:
        raise MissingInfoHTTPError("Chybí adresa trvalého bydliště.")

    assignment = contract.get("assignment", None)
    if not assignment:
        raise MissingInfoHTTPError("Chybí pracovní náplň.")

    account_number = contract.get("account_number", None)
    if not account_number:
        raise MissingInfoHTTPError("Chybí číslo účtu.")

    valid_from = str_ops.date_to_str(contract["valid_from"])
    valid_until = str_ops.date_to_str(contract["valid_until"])
    hour_rate = contract["hour_rate"]
    signing_date = contract["signing_date"]
    signing_place = contract["signing_place"]
    if not all((valid_from, valid_until, hour_rate, signing_date, signing_place)):
        raise MissingInfoHTTPError("Problém se smlouvou.")

    output_path = f"static/tmp/" \
                  f"{user_id}_{contract['type']}_{str_ops.date_to_iso_str(contract['signing_date'])}.pdf"

    pdf = fpdf.FPDF("P", "mm", "A4")
    pdf.add_font(FONT, '', os.path.join(FONT_DIR, 'DejaVuSerif.ttf'), uni=True)
    pdf.add_font(FONT, 'B', os.path.join(FONT_DIR, 'DejaVuSerif-Bold.ttf'), uni=True)
    pdf.add_font(FONT, 'I', os.path.join(FONT_DIR, 'DejaVuSerif-Italic.ttf'), uni=True)

    pdf.set_margins(25, 25)
    pdf.set_auto_page_break(False)
    pdf.add_page()

    pdf.set_font(FONT, "B", HEADING_SIZE)

    pdf.cell(w=0, txt="DOHODA O PROVEDENÍ PRÁCE", align="C")
    pdf.ln(SPACE_SIZE)

    pdf.set_font(FONT, "", FONT_SIZE)
    pdf.cell(w=0, txt="(do 300 hodin ročně)", align="C")
    pdf.ln(SPACE_SIZE * 2)

    pdf.cell(w=WIDTH, txt="Zaměstnavatel:")
    pdf.cell(w=0, txt=company_name)
    pdf.ln(SPACE_SIZE)

    pdf.cell(w=WIDTH, txt="se sídlem:")
    pdf.cell(w=0, txt=f"{company_address}, IČO: {company_crn}")
    pdf.ln(SPACE_SIZE)

    pdf.cell(w=0, txt="(dále jen zaměstnavatel)")
    pdf.ln(SPACE_SIZE)

    pdf.cell(w=0, txt="a")
    pdf.ln(SPACE_SIZE)

    pdf.cell(w=WIDTH, txt="zaměstnanec:")

    cell_text = f"{name}, nar.: {birthdate}"
    if len(cell_text) < ONE_LINE_LIMIT:
        pdf.cell(w=0, txt=cell_text)
    else:
        print("cell text length:", len(cell_text), cell_text)
        pdf.cell(w=0, txt=f"{name},")
        pdf.ln(SPACE_SIZE - 1)
        pdf.cell(w=WIDTH, txt="")
        pdf.cell(w=0, txt=f"nar.: {birthdate}")
    pdf.ln(SPACE_SIZE)

    pdf.cell(w=WIDTH, txt="bytem:")

    if len(address) < ONE_LINE_LIMIT:
        pdf.cell(w=0, txt=address)
    else:
        first_comma = address.find(", ") + 2
        before_comma = address[:first_comma]
        after_comma = address[first_comma:]
        pdf.cell(w=0, txt=before_comma)
        pdf.ln(SPACE_SIZE - 1)
        pdf.cell(w=WIDTH, txt="")
        pdf.cell(w=0, txt=after_comma)
    pdf.ln(SPACE_SIZE)

    pdf.cell(w=0, txt="uzavírají tuto")
    pdf.ln(SPACE_SIZE)

    pdf.set_font(FONT, "B", FONT_SIZE)

    pdf.cell(w=0, txt="dohodu o provedení práce", align="C")
    pdf.ln(SPACE_SIZE)

    pdf.set_font(FONT, "", FONT_SIZE)

    pdf.multi_cell(w=0, h=5, txt=f"1. Vymezení pracovního úkolu: {assignment}, pracovní úkol v rozsahu: max. 300 hodin "
                                 f"bude proveden od {valid_from} do {valid_until}")
    pdf.ln(MULTICELL_SPACE_SIZE)

    pdf.multi_cell(w=0, h=5, txt="2. Za splnění pracovního úkolu ve sjednané jakosti a lhůtě se sjednává odměna "
                                 f"ve výši Kč: {hour_rate},-/hodinu hrubé mzdy. Mzda je splatná k 15tému dni "
                                 f"následujícího měsíce na účet č. {account_number}.")
    pdf.ln(MULTICELL_SPACE_SIZE)

    pdf.multi_cell(w=0, h=5, txt="3. Zaměstnavatel se zavazuje vytvořit zaměstnanci přiměřené pracovní podmínky "
                                 "pro řádný a bezpečný výkon práce. Zaměstnavatel zaměstnance seznámil s předpisy "
                                 "vztahujícími se na výkon jeho práce, zejména s předpisy vydanými k zajištění "
                                 "bezpečnosti a ochrany při práci, jakož i s dalšími povinnostmi pracovníka "
                                 "a firmy, souvisejícími s uzavření této dohody v návaznosti na ustanovení "
                                 "§ 75 Zákoníku práce.")
    pdf.ln(MULTICELL_SPACE_SIZE)

    pdf.multi_cell(w=0, h=5, txt="4. Zaměstnavatel může odstoupit od dohody, jestliže pracovní úkol nebude proveden "
                                 "ve sjednané lhůtě. Zaměstnanec může od dohody odstoupit, nemůže-li pracovní úkol "
                                 "provést protože mu zaměstnavatel nevytvořil sjednané pracovní podmínky. "
                                 "V takovém případě je zaměstnavatel povinen nahradit zaměstnanci škodu, která mu tím "
                                 "vznikla. Sjednanou odměnu může zaměstnavatel po projednání se zaměstnancem přiměřeně "
                                 "snížit, neodpovídá-li provedená práce sjednaným podmínkám (nedodržení termínu, "
                                 "kvalita, a rozsah prací spod.).")
    pdf.ln(MULTICELL_SPACE_SIZE)

    pdf.multi_cell(w=0, h=5, txt="5. Zaměstnanec se zavazuje neposkytovat třetím osobám informace, které získal "
                                 "při výkonu práce pro firmu a které by mohly poškodit její obchodní zájmy. "
                                 "Tyto informace nebude rovněž zneužívat v neprospěch firmy. Porušení tohoto "
                                 "ustanovení je důvodem k okamžitému zrušení dohody, přičemž si firma vyhrazuje právo "
                                 "vymáhat náhradu vzniklé škody.")
    pdf.ln(MULTICELL_SPACE_SIZE)

    pdf.multi_cell(w=0, h=5, txt="6. Další ujednání: používání soukromého automobilu k výkonu činnosti – nárok "
                                 "na náhradu cestovních výdajů")
    pdf.ln(MULTICELL_SPACE_SIZE)

    pdf.multi_cell(w=0, h=5, txt="7. Tato dohoda byla vypracována ve dvou vyhotoveních, z nichž jedno obdrží "
                                 "zaměstnanec a jedno zaměstnavatel.")
    pdf.ln(SPACE_SIZE)

    pdf.cell(w=0, txt=f"{signing_place}, dne {str_ops.date_to_str(signing_date)}")
    pdf.ln(SPACE_SIZE * 3)

    pdf.cell(w=124, txt="." * 50)
    pdf.cell(w=WIDTH, txt="." * 50, align="R")
    pdf.ln(SPACE_SIZE)

    pdf.cell(w=124, txt="podpis zaměstnance")
    pdf.cell(w=WIDTH, txt="podpis opráv. zástupce firmy", align="R")

    pdf.output(output_path)

    return output_path
