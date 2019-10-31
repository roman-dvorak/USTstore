import fpdf
import os

import plugins.helpers.str_ops as str_ops
from mdoc_ops import find_type_in_addresses
from plugins.helpers.doc_keys import NAME_DOC_KEYS

SPACE_SIZE = 6
MULTICELL_SPACE_SIZE = 2
FONT = "DejaVu"
FONT_SIZE = 11
HEADING_SIZE = 16

FONT_DIR = os.path.join("static", "dejavu")


def generate_contract(user, contract, company_name, company_address, company_id):
    name_doc = user["name"]
    full_name = " ".join([name_doc[key] for key in NAME_DOC_KEYS if name_doc.get(key, None)])
    birthdate = str_ops.date_to_str(user["birthdate"])

    address = str_ops.address_to_str(find_type_in_addresses(user["addresses"], "residence"))

    assignment = user["assignment"]

    valid_from = str_ops.date_to_str(contract["valid_from"])
    valid_until = str_ops.date_to_str(contract["valid_until"])

    hour_rate = contract["hour_rate"]
    account_number = user["account_number"]
    signing_date = contract["signing_date"]

    output_path = f"static/contracts/" \
                  f"{user['_id']}_{contract['type']}_{str_ops.date_to_iso_str(contract['signing_date'])}.pdf"

    pdf = fpdf.FPDF("P", "mm", "A4")
    pdf.add_font(FONT, '', os.path.join(FONT_DIR, 'DejaVuSerif.ttf'), uni=True)
    pdf.add_font(FONT, 'B', os.path.join(FONT_DIR, 'DejaVuSerif-Bold.ttf'), uni=True)
    pdf.add_font(FONT, 'I', os.path.join(FONT_DIR, 'DejaVuSerif-Italic.ttf'), uni=True)

    pdf.set_margins(25, 25)
    pdf.add_page()

    pdf.set_font(FONT, "B", HEADING_SIZE)

    pdf.cell(w=0, txt="DOHODA O PROVEDENÍ PRÁCE", align="C")
    pdf.ln(SPACE_SIZE)

    pdf.set_font(FONT, "", FONT_SIZE)
    pdf.cell(w=0, txt="(do 300 hodin ročně)", align="C")
    pdf.ln(SPACE_SIZE * 2)

    pdf.cell(w=50, txt="Zaměstnavatel:")
    pdf.cell(w=0, txt=company_name)
    pdf.ln(SPACE_SIZE)

    pdf.cell(w=50, txt="se sídlem:")
    pdf.cell(w=0, txt=f"{company_address}, IČO: {company_id}")
    pdf.ln(SPACE_SIZE)

    pdf.cell(w=0, txt="(dále jen zaměstnavatel)")
    pdf.ln(SPACE_SIZE)

    pdf.cell(w=0, txt="a")
    pdf.ln(SPACE_SIZE)

    pdf.cell(w=50, txt="zaměstnanec:")
    pdf.cell(w=0, txt=f"{full_name}, nar.: {birthdate}")
    pdf.ln(SPACE_SIZE)

    pdf.cell(w=50, txt="bytem:")
    pdf.cell(w=0, txt=address)
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
                                 "vztahujícími se na výkon jeho práce, zejména s přepisy vydanými k zajištění "
                                 "bezpečnosti a ochrany při práci, jakož i s dalšími povinnostmi pracovníka "
                                 "a firmy, souvisejícími s uzavření této dohody v návaznosti na ustanovení "
                                 "§ 75 Zákoníku práce.")
    pdf.ln(MULTICELL_SPACE_SIZE)

    pdf.multi_cell(w=0, h=5, txt="4. Zaměstnavatel může odstoupit od dohody, jestliže pracovní úkol nebude proveden "
                                 "ve sjednané lhůtě. Zaměstnanec může od dohody odstoupil, nemůže-li pracovní úkol "
                                 "provést proto, že mu zaměstnavatel nevytvořil sjednané pracovní podmínky. "
                                 "V takovém případě je zaměstnavatel povinen nahradit zaměstnanci škodu, která mu tím "
                                 "vznikla. Sjednanou odměnu může zaměstnavatel po projednání se zaměstnancem přiměřeně "
                                 "snížit, neodpovídá-li provedená práce sjednaným podmínkám (nedodržení termínu, "
                                 "kvalita, a rozsah prací spod.).")
    pdf.ln(MULTICELL_SPACE_SIZE)

    pdf.multi_cell(w=0, h=5, txt="5. Zaměstnanec se zavazuje neposkytovat třetím osobám informace, které získal "
                                 "při výkonu práce pro firmu a které by mohly poškodit její obchodní zájmy. "
                                 "Tyto informace nebude rovněž zneužívat v  neprospěch firmy. Porušení tohoto "
                                 "ustanovení je důvodem k okamžitému zrušení dohody, přičemž si firma vyhrazuje právo "
                                 "vymáhat náhradu vzniklé škody.")
    pdf.ln(MULTICELL_SPACE_SIZE)

    pdf.multi_cell(w=0, h=5, txt="6. Další ujednání: používání soukromého automobilu k výkonu činnosti – nárok "
                                 "na náhradu cestovních výdajů")
    pdf.ln(MULTICELL_SPACE_SIZE)

    pdf.multi_cell(w=0, h=5, txt="7. Tato dohoda byla vypracována ve dvou vyhotoveních, z nichž jedno obdrží "
                                 "zaměstnanec a jedno zaměstnavatel.")
    pdf.ln(SPACE_SIZE)

    pdf.cell(w=0, txt=f"V Praze, dne {str_ops.date_to_str(signing_date)}")
    pdf.ln(SPACE_SIZE * 3)

    pdf.cell(w=100, txt="." * 50)
    pdf.cell(w=50, txt="." * 50, align="R")
    pdf.ln(SPACE_SIZE)

    pdf.cell(w=100, txt="podpis zaměstnance")
    pdf.cell(w=50, txt="podpis opráv. zástupce firmy", align="R")

    pdf.output(output_path)

    return output_path
