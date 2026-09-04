"""Parser für ISO 20022 CAMT.053 Kontoauszüge (camt.053.001.02/04/08).

Bewusst tolerant gegenüber Namespace-Varianten: es wird nur auf lokale
Tag-Namen (ohne Namespace-Präfix) gematcht, damit unterschiedliche Bank-
Exportversionen ohne Anpassung funktionieren.
"""
import hashlib
from datetime import datetime
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET


def _local(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def _direct_children(elem, name):
    return [c for c in elem if _local(c.tag) == name]


def _first_direct(elem, name):
    found = _direct_children(elem, name)
    return found[0] if found else None


def _text(elem):
    return elem.text.strip() if elem is not None and elem.text else ""


def _find_anywhere(elem, name):
    for child in elem.iter():
        if _local(child.tag) == name:
            return child
    return None


def _findall_anywhere(elem, name):
    return [c for c in elem.iter() if _local(c.tag) == name]


def _find_party(ntry, primary, ultimate):
    """Sucht zuerst die direkte Partei (z.B. Cdtr), dann ersatzweise die
    "Ultimate"-Variante (z.B. UltmtCdtr), die manche Banken stattdessen liefern."""
    return _find_anywhere(ntry, primary) or _find_anywhere(ntry, ultimate)


def _party_display(party_elem):
    """Name + Postadresse einer Partei als ein String (z.B. für Cdtr/Dbtr),
    z.B. 'EKZ Elektrizitaetswerke des Kantons Zuerich, Dreikoenigstrasse, 18, 8022, Zuerich, CH'."""
    if party_elem is None:
        return ""
    name = _text(_first_direct(party_elem, "Nm"))
    address_parts = []
    pstl_adr = _first_direct(party_elem, "PstlAdr")
    if pstl_adr is not None:
        for tag in ("StrtNm", "BldgNb", "PstCd", "TwnNm", "Ctry"):
            value = _text(_first_direct(pstl_adr, tag))
            if value:
                address_parts.append(value)
    parts = ([name] if name else []) + address_parts
    return ", ".join(parts)


class Camt053ParseError(Exception):
    pass


def parse_camt053(file_obj):
    """Parst eine CAMT.053-XML-Datei und gibt eine Liste von Buchungen zurück.

    Jede Buchung ist ein dict:
        date, amount (Decimal, negativ=Ausgabe), currency, description,
        counterparty, entry_ref, account_iban
    """
    try:
        tree = ET.parse(file_obj)
    except ET.ParseError as exc:
        raise Camt053ParseError(f"Ungültiges XML: {exc}") from exc

    root = tree.getroot()
    stmts = _findall_anywhere(root, "Stmt")
    if not stmts:
        raise Camt053ParseError(
            "Kein <Stmt>-Element gefunden. Ist das wirklich eine CAMT.053-Datei?"
        )

    results = []
    for stmt in stmts:
        acct = _first_direct(stmt, "Acct")
        account_iban = ""
        if acct is not None:
            iban_el = _find_anywhere(acct, "IBAN")
            account_iban = _text(iban_el)

        for ntry in _direct_children(stmt, "Ntry"):
            amt_el = _first_direct(ntry, "Amt")
            amount = Decimal("0")
            currency = "CHF"
            if amt_el is not None:
                try:
                    amount = Decimal(_text(amt_el))
                except (InvalidOperation, AttributeError):
                    amount = Decimal("0")
                currency = amt_el.attrib.get("Ccy", "CHF")

            cdt_dbt_el = _first_direct(ntry, "CdtDbtInd")
            sign = Decimal("-1") if _text(cdt_dbt_el) == "DBIT" else Decimal("1")
            amount = amount * sign

            booking_date = None
            bookg_dt = _first_direct(ntry, "BookgDt")
            if bookg_dt is not None:
                date_el = _first_direct(bookg_dt, "Dt")
                if date_el is None:
                    date_el = _first_direct(bookg_dt, "DtTm")
                raw = _text(date_el)
                if raw:
                    try:
                        booking_date = datetime.fromisoformat(raw[:19]).date()
                    except ValueError:
                        booking_date = None

            descr_parts = [
                _text(u) for u in _findall_anywhere(ntry, "Ustrd") if _text(u)
            ]
            if not descr_parts:
                # Manche Banken liefern AddtlNtryInf direkt unter Ntry, andere
                # verschachtelt unter NtryDtls/TxDtls — daher anywhere statt direct.
                addtl = _find_anywhere(ntry, "AddtlNtryInf")
                if addtl is not None and _text(addtl):
                    descr_parts.append(_text(addtl))
            description = " / ".join(dict.fromkeys(descr_parts)) or "(keine Beschreibung)"

            # Bei einer Ausgabe (DBIT) ist die relevante Gegenpartei der Empfänger
            # (Cdtr), bei einer Einnahme (CRDT) der Absender (Dbtr) — nicht der
            # jeweils andere, der bei einer Ausgabe z.B. der Kontoinhaber selbst wäre.
            if _text(cdt_dbt_el) == "DBIT":
                party = _find_party(ntry, "Cdtr", "UltmtCdtr")
            else:
                party = _find_party(ntry, "Dbtr", "UltmtDbtr")
            counterparty = _party_display(party)

            ref_el = _find_anywhere(ntry, "AcctSvcrRef")
            acct_svcr_ref = _text(ref_el)

            if acct_svcr_ref:
                entry_ref = acct_svcr_ref
            else:
                raw_key = f"{account_iban}|{booking_date}|{amount}|{description}"
                entry_ref = "auto-" + hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:24]

            results.append(
                {
                    "date": booking_date,
                    "amount": amount,
                    "currency": currency,
                    "description": description,
                    "counterparty": counterparty,
                    "entry_ref": entry_ref,
                    "account_iban": account_iban,
                }
            )

    return results


def suggest_category(description, counterparty, categories):
    """Sehr einfache stichwortbasierte Auto-Zuordnung anhand Category.keywords."""
    text = f"{description} {counterparty}".lower()
    for cat in categories:
        for kw in cat.keyword_list():
            if kw in text:
                return cat
    return None
