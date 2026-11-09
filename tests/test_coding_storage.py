"""Focused persistence tests for the coding workspaces."""
import tempfile
import unittest
from pathlib import Path

import pv_coding
import pv_storage


class CodingStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        pv_storage.DATA_DIR = root
        pv_storage.DB_PATH = root / "test.sqlite3"
        pv_storage.DOCUMENT_DIR = root / "documents"
        pv_storage.init_db()
        pv_coding.initialize()
        self.case_id = pv_storage.create_case({"Country": "Training"}, "Test user")

    def tearDown(self):
        self.temp.cleanup()

    def test_import_and_search_meddra_csv(self):
        csv_data = b"llt,llT_code,pt,pt_code,hlt,hlgt,soc,primary_soc,version\nTraining event,99999999,Training PT,99999999,HLT,HLGT,SOC,Yes,Training fixture\n"
        count = pv_coding.import_dictionary_csv(pv_coding.MEDDRA, csv_data, "Test user", True)
        self.assertEqual(count, 1)
        found = pv_coding.search_dictionary(pv_coding.MEDDRA, "Training event")
        self.assertEqual(found[0]["record"]["term"], "Training event")
        self.assertEqual(found[0]["record"]["code"], "99999999")

    def test_import_requires_authorization(self):
        data = b"preferred_name,drug_code\nExample,TRAINING-1\n"
        with self.assertRaises(ValueError):
            pv_coding.import_dictionary_csv(pv_coding.WHODRUG, data, "Test user", False)

    def test_coding_save_and_history(self):
        pv_coding.save_coding(self.case_id, pv_coding.MEDDRA, "event-1", "Training event", {"LLT": "Training event", "LLT code": ""}, "Training entry - not dictionary verified", "Test user")
        record = pv_coding.get_coding(self.case_id, pv_coding.MEDDRA, "event-1")
        self.assertEqual(record["reported_term"], "Training event")
        self.assertEqual(record["coding_status"], "Training entry - not dictionary verified")
        self.assertEqual(len(pv_coding.get_history(self.case_id, pv_coding.MEDDRA, "event-1")), 1)

    def test_review_requires_reviewer(self):
        with self.assertRaises(ValueError):
            pv_coding.save_coding(self.case_id, pv_coding.WHODRUG, "product-1", "Example", {}, "Reviewed", "Coder")

    def test_csv_rows_require_term_and_code(self):
        data = b"llt,llt_code\nTraining event,\n"
        with self.assertRaises(ValueError):
            pv_coding.import_dictionary_csv(pv_coding.MEDDRA, data, "Test user", True)


if __name__ == "__main__":
    unittest.main()
