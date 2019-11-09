def find_type_in_addresses(addresses: list, addr_type: str):
    """
    Najde první adresu s daným typem v listu adres.
    Adresy bez explicitního typu jsou chápány jako typ "residence"

    """
    return next((a for a in addresses if a.get("type", "residence") == addr_type), None)