import io
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from core.models import Account, Category, Transaction
from .camt053 import Camt053ParseError, parse_camt053, suggest_category
from .models import ImportBatch, Rule

SAMPLE_DIR = settings.BASE_DIR / "sample_data"


def _parse_file(name):
    with open(SAMPLE_DIR / name, "rb") as f:
        return parse_camt053(f)


class ParseCamt053Tests(TestCase):
    def test_parses_camt_053_001_02_reference_file(self):
        rows = _parse_file("beispiel_camt053.xml")
        self.assertEqual(len(rows), 3)
        by_ref = {r["entry_ref"]: r for r in rows}
        self.assertEqual(by_ref["REF-1001"]["amount"], Decimal("-84.30"))
        self.assertEqual(by_ref["REF-1002"]["amount"], Decimal("4200.00"))
        self.assertEqual(by_ref["REF-1003"]["description"], "Mietzins September")
        self.assertEqual(by_ref["REF-1003"]["counterparty"], "Hausverwaltung Muster AG")

    def test_parses_camt_053_001_08_variant_with_dttm_and_multiple_stmts(self):
        rows = _parse_file("camt053_001_08_ubs_variante.xml")
        self.assertEqual(len(rows), 3)
        by_ref = {r["entry_ref"]: r for r in rows}
        # DtTm statt Dt korrekt in ein date-Objekt umgewandelt
        self.assertEqual(by_ref["UBS-REF-88001"]["date"].isoformat(), "2026-10-02")
        # zweiter Stmt-Block wird ebenfalls erfasst
        self.assertEqual(by_ref["UBS-REF-88002"]["amount"], Decimal("3950.00"))
        # mehrfach identische <Ustrd> werden dedupliziert
        self.assertEqual(by_ref["UBS-REF-88002"]["description"], "Lohn Oktober 2026")

    def test_missing_acct_svcr_ref_gets_stable_auto_generated_ref(self):
        rows = _parse_file("camt053_001_08_ubs_variante.xml")
        auto_rows = [r for r in rows if r["entry_ref"].startswith("auto-")]
        self.assertEqual(len(auto_rows), 1)
        # AddtlNtryInf verschachtelt unter NtryDtls/TxDtls wird trotzdem gefunden
        self.assertEqual(auto_rows[0]["description"], "Streaming-Abo monatlich")

        # Erneutes Parsen derselben Datei liefert denselben Fallback-Ref (deterministisch)
        rows_again = _parse_file("camt053_001_08_ubs_variante.xml")
        auto_rows_again = [r for r in rows_again if r["entry_ref"].startswith("auto-")]
        self.assertEqual(auto_rows[0]["entry_ref"], auto_rows_again[0]["entry_ref"])

    def test_parses_camt_053_001_02_postfinance_variant_with_foreign_currency(self):
        rows = _parse_file("camt053_001_02_postfinance_variante.xml")
        self.assertEqual(len(rows), 3)
        by_ref = {r["entry_ref"]: r for r in rows}
        self.assertEqual(by_ref["POFI-REF-0002"]["currency"], "EUR")
        self.assertEqual(by_ref["POFI-REF-0002"]["amount"], Decimal("-39.00"))
        # AddtlNtryInf direkt unter Ntry (ohne NtryDtls) wird als Beschreibung übernommen
        self.assertEqual(by_ref["POFI-REF-0001"]["description"], "Mietzins Oktober, Dauerauftrag")
        # CRDT-Buchung ist positiv
        self.assertEqual(by_ref["POFI-REF-0003"]["amount"], Decimal("250.00"))

    def test_invalid_xml_raises_parse_error(self):
        bad_file = io.BytesIO(b"not valid xml <<<")
        with self.assertRaises(Camt053ParseError):
            parse_camt053(bad_file)

    def test_xml_without_stmt_element_raises_parse_error(self):
        no_stmt = io.BytesIO(
            b"<?xml version='1.0'?><Document xmlns='urn:iso:std:iso:20022:tech:xsd:camt.053.001.02'>"
            b"<BkToCstmrStmt><GrpHdr><MsgId>X</MsgId></GrpHdr></BkToCstmrStmt></Document>"
        )
        with self.assertRaises(Camt053ParseError):
            parse_camt053(no_stmt)


class SuggestCategoryTests(TestCase):
    def setUp(self):
        self.groceries = Category.objects.create(
            name="Lebensmittel", kind=Category.Kind.VARIABLE, keywords="migros, coop, denner"
        )
        self.rent = Category.objects.create(
            name="Miete", kind=Category.Kind.FIXED, keywords="hausverwaltung, miete"
        )

    def test_matches_keyword_case_insensitively(self):
        cats = [self.groceries, self.rent]
        result = suggest_category("Einkauf Migros Zuerich", "Migros Genossenschaft", cats)
        self.assertEqual(result, self.groceries)

    def test_matches_on_counterparty_text_too(self):
        cats = [self.groceries, self.rent]
        result = suggest_category("Mietzins September", "Hausverwaltung Muster AG", cats)
        self.assertEqual(result, self.rent)

    def test_no_match_returns_none(self):
        cats = [self.groceries, self.rent]
        result = suggest_category("Kino Tickets", "Pathe AG", cats)
        self.assertIsNone(result)


class ImportApiTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")
        self.account = Account.objects.create(name="Girokonto")
        self.category = Category.objects.create(
            name="Lebensmittel", kind=Category.Kind.VARIABLE, keywords="migros"
        )

    def _upload(self, name):
        with open(SAMPLE_DIR / name, "rb") as f:
            content = f.read()
        return SimpleUploadedFile(name, content, content_type="application/xml")

    def test_parse_view_returns_preview_rows_with_suggestion_and_no_side_effects(self):
        response = self.client.post(
            "/api/import/parse/",
            {"account": self.account.id, "camt_file": self._upload("beispiel_camt053.xml")},
        )
        self.assertEqual(response.status_code, 200)
        rows = response.json()["rows"]
        self.assertEqual(len(rows), 3)
        migros_row = next(r for r in rows if "Migros" in r["description"])
        self.assertEqual(migros_row["suggested_category_id"], self.category.id)
        self.assertFalse(migros_row["is_duplicate"])
        self.assertEqual(Transaction.objects.count(), 0)

    def test_parse_view_flags_duplicates_against_existing_transactions(self):
        Transaction.objects.create(
            account=self.account, date="2026-09-02", amount=Decimal("-84.30"), import_ref="REF-1001"
        )
        response = self.client.post(
            "/api/import/parse/",
            {"account": self.account.id, "camt_file": self._upload("beispiel_camt053.xml")},
        )
        rows = response.json()["rows"]
        dup_row = next(r for r in rows if r["entry_ref"] == "REF-1001")
        self.assertTrue(dup_row["is_duplicate"])
        self.assertFalse(dup_row["is_possible_duplicate"])

    def test_parse_view_flags_manual_transaction_without_import_ref_as_possible_duplicate(self):
        """Eine manuell erfasste Zahlung (z.B. aus dem Schulden-Sweep-Vorschlag) hat
        keine Bank-Referenz — die harte Duplikat-Prüfung via import_ref greift dafür
        nicht. Datum+Betrag sollen sie trotzdem als möglichen Treffer markieren,
        aber NICHT hart blockieren (kein import_ref = keine echte Gewissheit)."""
        Transaction.objects.create(account=self.account, date="2026-09-02", amount=Decimal("-84.30"))
        response = self.client.post(
            "/api/import/parse/",
            {"account": self.account.id, "camt_file": self._upload("beispiel_camt053.xml")},
        )
        rows = response.json()["rows"]
        row = next(r for r in rows if r["entry_ref"] == "REF-1001")
        self.assertFalse(row["is_duplicate"])
        self.assertTrue(row["is_possible_duplicate"])

    def test_parse_view_only_flags_as_many_possible_duplicates_as_existing_matches(self):
        """Zwei unabhängige echte Buchungen am selben Tag mit demselben Betrag
        dürfen nicht beide verloren gehen, nur weil zufällig EINE bereits manuell
        erfasste Buchung mit gleichem Datum/Betrag existiert — die Heuristik muss
        als Multiset zählen, nicht pauschal jeden Treffer markieren."""
        # DBIT (Ausgabe) wird vom Parser als negativer Betrag geführt — der manuell
        # erfasste Vergleichswert muss also ebenfalls negativ sein, damit er matcht.
        Transaction.objects.create(account=self.account, date="2026-09-05", amount=Decimal("-50.00"))
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">
  <BkToCstmrStmt>
    <GrpHdr><MsgId>MSG-1</MsgId><CreDtTm>2026-09-01T08:00:00</CreDtTm></GrpHdr>
    <Stmt>
      <Id>STMT-1</Id>
      <Acct><Id><IBAN>CH9300762011623852957</IBAN></Id><Ccy>CHF</Ccy></Acct>
      <Ntry>
        <Amt Ccy="CHF">50.00</Amt>
        <CdtDbtInd>DBIT</CdtDbtInd>
        <BookgDt><Dt>2026-09-05</Dt></BookgDt>
        <AcctSvcrRef>REF-A</AcctSvcrRef>
        <NtryDtls><TxDtls><RmtInf><Ustrd>Zahlung A</Ustrd></RmtInf></TxDtls></NtryDtls>
      </Ntry>
      <Ntry>
        <Amt Ccy="CHF">50.00</Amt>
        <CdtDbtInd>DBIT</CdtDbtInd>
        <BookgDt><Dt>2026-09-05</Dt></BookgDt>
        <AcctSvcrRef>REF-B</AcctSvcrRef>
        <NtryDtls><TxDtls><RmtInf><Ustrd>Zahlung B</Ustrd></RmtInf></TxDtls></NtryDtls>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>"""
        upload = SimpleUploadedFile("two_same.xml", xml.encode("utf-8"), content_type="application/xml")
        response = self.client.post("/api/import/parse/", {"account": self.account.id, "camt_file": upload})
        rows = response.json()["rows"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(sum(1 for r in rows if r["is_possible_duplicate"]), 1)

    def test_confirm_view_does_not_force_skip_possible_duplicate_row(self):
        """Anders als ein hartes Duplikat (is_duplicate) darf ein möglicher Treffer
        (is_possible_duplicate) den Import nicht blockieren, wenn der Nutzer die
        Checkbox bewusst angehakt lässt — der Nutzer könnte ja Recht haben, dass es
        doch zwei verschiedene Buchungen sind."""
        rows = [
            {
                "date": "2026-09-02", "amount": "-84.30", "description": "Einkauf Migros",
                "counterparty": "Migros", "entry_ref": "REF-1001", "category_id": self.category.id,
                "include": True, "is_duplicate": False, "is_possible_duplicate": True,
            },
        ]
        response = self.client.post(
            "/api/import/confirm/",
            {"account": self.account.id, "filename": "beispiel_camt053.xml", "rows": rows},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["created"], 1)

    def test_confirm_view_creates_transactions_and_import_batch(self):
        rows = [
            {
                "date": "2026-09-02", "amount": "-84.30", "description": "Einkauf Migros",
                "counterparty": "Migros", "entry_ref": "REF-1001", "category_id": self.category.id,
                "include": True, "is_duplicate": False,
            },
            {
                "date": "2026-09-01", "amount": "4200.00", "description": "Lohn",
                "counterparty": "AG", "entry_ref": "REF-1002", "category_id": None,
                "include": False, "is_duplicate": False,
            },
        ]
        response = self.client.post(
            "/api/import/confirm/",
            {"account": self.account.id, "filename": "beispiel_camt053.xml", "rows": rows},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["created"], 1)
        self.assertEqual(Transaction.objects.count(), 1)
        self.assertEqual(ImportBatch.objects.count(), 1)
        self.assertEqual(Transaction.objects.get().category_id, self.category.id)

    def test_confirm_view_counts_duplicate_rows_as_skipped(self):
        # Das Frontend deaktiviert die Checkbox für Duplikat-Zeilen und schickt
        # daher include=False für sie — trotzdem müssen sie als "skipped" zählen,
        # nicht einfach stillschweigend ignoriert werden.
        rows = [
            {
                "date": "2026-09-02", "amount": "-84.30", "description": "Einkauf Migros",
                "counterparty": "Migros", "entry_ref": "REF-1001", "category_id": None,
                "include": False, "is_duplicate": True,
            },
        ]
        response = self.client.post(
            "/api/import/confirm/",
            {"account": self.account.id, "filename": "beispiel_camt053.xml", "rows": rows},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["created"], 0)
        self.assertEqual(data["skipped"], 1)
        self.assertEqual(ImportBatch.objects.get().transactions_skipped, 1)

    def test_history_view_lists_batches(self):
        ImportBatch.objects.create(account=self.account, filename="a.xml", transactions_created=2, transactions_skipped=1)
        response = self.client.get("/api/import/history/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["account_name"], "Girokonto")

    def test_rule_takes_priority_over_keyword_matching(self):
        precise_category = Category.objects.create(name="Miete direkt", kind=Category.Kind.FIXED)
        Rule.objects.create(
            counterparty_match_type=Rule.MatchType.EXACT, counterparty_value="Hausverwaltung Muster AG",
            category=precise_category, priority=10,
        )
        response = self.client.post(
            "/api/import/parse/",
            {"account": self.account.id, "camt_file": self._upload("beispiel_camt053.xml")},
        )
        rows = response.json()["rows"]
        rent_row = next(r for r in rows if "Mietzins" in r["description"])
        self.assertEqual(rent_row["suggested_category_id"], precise_category.id)

    def test_rule_can_combine_counterparty_and_amount(self):
        precise_category = Category.objects.create(name="Miete direkt", kind=Category.Kind.FIXED)
        Rule.objects.create(
            counterparty_match_type=Rule.MatchType.CONTAINS, counterparty_value="Hausverwaltung",
            amount_max=Decimal("-1000"), category=precise_category, priority=10,
        )
        response = self.client.post(
            "/api/import/parse/",
            {"account": self.account.id, "camt_file": self._upload("beispiel_camt053.xml")},
        )
        rows = response.json()["rows"]
        migros_row = next(r for r in rows if "Migros" in r["description"])
        rent_row = next(r for r in rows if "Mietzins" in r["description"])
        # Migros (-84.30) unterschreitet -1000 nicht -> Regel greift nicht, nur Miete (-1450) tut es
        self.assertNotEqual(migros_row["suggested_category_id"], precise_category.id)
        self.assertEqual(rent_row["suggested_category_id"], precise_category.id)


class RuleModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Lebensmittel", kind=Category.Kind.VARIABLE)

    def test_contains_match_is_case_insensitive(self):
        rule = Rule(counterparty_match_type=Rule.MatchType.CONTAINS, counterparty_value="migros", category=self.category)
        self.assertTrue(rule.matches("Einkauf", "MIGROS Zürich AG", Decimal("-10")))

    def test_startswith_requires_prefix(self):
        rule = Rule(description_match_type=Rule.MatchType.STARTSWITH, description_value="Mietzins", category=self.category)
        self.assertTrue(rule.matches("Mietzins September", "", Decimal("-1450")))
        self.assertFalse(rule.matches("Nachzahlung Mietzins", "", Decimal("-1450")))

    def test_exact_requires_full_match(self):
        rule = Rule(counterparty_match_type=Rule.MatchType.EXACT, counterparty_value="Migros AG", category=self.category)
        self.assertTrue(rule.matches("", "Migros AG", Decimal("-10")))
        self.assertFalse(rule.matches("", "Migros AG Filiale 12", Decimal("-10")))

    def test_no_condition_never_matches(self):
        rule = Rule(category=self.category)
        self.assertFalse(rule.matches("irgendwas", "irgendwas", Decimal("-10")))

    def test_amount_range_condition(self):
        rule = Rule(amount_min=Decimal("-50"), amount_max=Decimal("-10"), category=self.category)
        self.assertTrue(rule.matches("", "", Decimal("-25")))
        self.assertFalse(rule.matches("", "", Decimal("-5")))
        self.assertFalse(rule.matches("", "", Decimal("-100")))

    def test_all_set_conditions_must_match(self):
        rule = Rule(
            counterparty_match_type=Rule.MatchType.CONTAINS, counterparty_value="Migros",
            amount_max=Decimal("-50"), category=self.category,
        )
        self.assertFalse(rule.matches("", "Migros AG", Decimal("-10")))  # Gegenpartei ok, Betrag nicht
        self.assertTrue(rule.matches("", "Migros AG", Decimal("-60")))


class RuleApiTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="tester", password="testpass12345")
        self.client.login(username="tester", password="testpass12345")
        self.account = Account.objects.create(name="Girokonto")
        self.category = Category.objects.create(name="Lebensmittel", kind=Category.Kind.VARIABLE)

    def test_create_list_and_delete_rule(self):
        response = self.client.post(
            "/api/import/rules/",
            {"name": "Migros", "counterparty_match_type": "contains", "counterparty_value": "Migros", "category": self.category.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        rule_id = response.json()["id"]

        response = self.client.get("/api/import/rules/")
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["category_name"], "Lebensmittel")

        response = self.client.delete(f"/api/import/rules/{rule_id}/")
        self.assertEqual(response.status_code, 204)

    def test_create_rule_without_any_condition_is_rejected(self):
        response = self.client.post(
            "/api/import/rules/",
            {"name": "Leer", "category": self.category.id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_edit_rule_via_put_updates_all_condition_fields(self):
        rule = Rule.objects.create(
            name="Migros", counterparty_match_type=Rule.MatchType.CONTAINS, counterparty_value="Migros",
            category=self.category,
        )
        other_category = Category.objects.create(name="Transport", kind=Category.Kind.VARIABLE)
        response = self.client.put(
            f"/api/import/rules/{rule.id}/",
            {
                "name": "Migros gross",
                "description_match_type": "contains", "description_value": "Einkauf",
                "counterparty_match_type": "exact", "counterparty_value": "Migros AG",
                "amount_min": "-100", "amount_max": "-10",
                "category": other_category.id, "priority": 5, "is_active": False,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        rule.refresh_from_db()
        self.assertEqual(rule.description_value, "Einkauf")
        self.assertEqual(rule.counterparty_match_type, "exact")
        self.assertEqual(rule.amount_min, Decimal("-100"))
        self.assertEqual(rule.category_id, other_category.id)
        self.assertFalse(rule.is_active)

    def test_preview_returns_matching_existing_transactions(self):
        Transaction.objects.create(account=self.account, date="2026-09-05", amount=Decimal("-20"), counterparty="Migros AG")
        Transaction.objects.create(account=self.account, date="2026-09-06", amount=Decimal("-30"), counterparty="Coop")

        response = self.client.post(
            "/api/import/rules/preview/",
            {"counterparty_match_type": "contains", "counterparty_value": "Migros"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["transactions"][0]["counterparty"], "Migros AG")

    def test_preview_without_any_condition_is_rejected(self):
        response = self.client.post("/api/import/rules/preview/", {}, content_type="application/json")
        self.assertEqual(response.status_code, 400)

    def test_apply_recategorizes_matching_transactions_and_syncs_debt(self):
        from debts.models import Debt

        debt = Debt.objects.create(
            name="Kreditkarte", principal=Decimal("1000"), current_balance=Decimal("1000"),
            interest_rate=Decimal("0"), minimum_payment=Decimal("50"),
        )
        t1 = Transaction.objects.create(account=self.account, date="2026-09-05", amount=Decimal("-20"), counterparty="Migros AG")
        Transaction.objects.create(account=self.account, date="2026-09-06", amount=Decimal("-30"), counterparty="Coop")

        response = self.client.post(
            "/api/import/rules/apply/",
            {"counterparty_match_type": "contains", "counterparty_value": "Migros", "category": debt.category_id},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updated"], 1)

        t1.refresh_from_db()
        self.assertEqual(t1.category_id, debt.category_id)
        debt.refresh_from_db()
        self.assertEqual(debt.current_balance, Decimal("980"))
        self.assertEqual(Rule.objects.count(), 0)
