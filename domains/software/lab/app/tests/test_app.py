"""Tests for the inventory service (stdlib unittest, zero deps)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app as svc  # module import; sys.path set above (E402 not enabled in this repo's ruff config)


class TestCatalog(unittest.TestCase):
    def test_found_item(self):
        self.assertEqual(svc.find_item("SKU-0001")["name"], "widget-1")

    def test_missing_item(self):
        self.assertIsNone(svc.find_item("SKU-9999"))

    def test_restock_applies_and_returns_new_qty(self):
        before = svc.CATALOG["SKU-0002"]["qty"]
        out = svc.apply_restock({"SKU-0002": 5})
        self.assertEqual(out["SKU-0002"], before + 5)

    def test_restock_ignores_unknown_sku(self):
        out = svc.apply_restock({"NOPE-0001": 3})
        self.assertNotIn("NOPE-0001", out)


if __name__ == "__main__":
    unittest.main()
