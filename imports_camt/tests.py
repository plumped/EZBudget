import io
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from core.models import Account, Category, Transaction
from .camt053 import Camt053ParseError, parse_camt053, suggest_category
from .models import ImportBatch

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

    def test_history_view_lists_batches(self):
        ImportBatch.objects.create(account=self.account, filename="a.xml", transactions_created=2, transactions_skipped=1)
        response = self.client.get("/api/import/history/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["account_name"], "Girokonto")
