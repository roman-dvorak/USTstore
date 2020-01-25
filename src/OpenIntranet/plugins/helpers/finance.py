import math


def calculate_tax(gross_wage, tax_rate, tax_deduction, tax_deduction_student):
    tax = gross_wage * tax_rate / 100
    tax -= tax_deduction
    tax -= tax_deduction_student

    tax = math.ceil(tax)
    tax = max(tax, 0)

    return tax
