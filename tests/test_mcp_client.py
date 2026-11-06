#!/usr/bin/env python3
"""
Unit tests for Civis MCP Client & Marketplace OS Integration.
"""

import sys
import unittest
from pathlib import Path

# Add civis_bot to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "civis_bot"))

from mcp_client import (
    map_civis_to_mcp_listing,
    ensure_mcp_tables,
    enqueue_sync,
    get_db_connection,
    VALID_MCP_CATEGORIES
)


class TestMcpClient(unittest.TestCase):

    def test_map_offer_business(self):
        item = {
            "id": 1,
            "text": "Ищу кофаундера в финтех-стартап.\nОпыт в B2B, знание Python и ML приветствуются.",
            "price": 0,
            "category": "general"
        }
        user = {
            "name": "Алексей",
            "role": "Инвестор / Фаундер"
        }
        listing = map_civis_to_mcp_listing("offer", item, user)
        self.assertEqual(listing["kind"], "offer")
        self.assertEqual(listing["category"], "business")
        self.assertTrue(listing["title"].startswith("Ищу кофаундера в финтех-стартап"))
        self.assertEqual(listing["price_rubles"], 0)
        self.assertIn("pickup", listing["modes"])
        self.assertIn(listing["category"], VALID_MCP_CATEGORIES)

    def test_map_request_services(self):
        item = {
            "id": 2,
            "text": "Нужен React фронтендер для доработки админки\nСрок 2 недели, бюджет до 60 000 руб.",
            "price_max": 60000,
            "category": "general"
        }
        user = {
            "name": "Михаил",
            "role": "Заказчик"
        }
        listing = map_civis_to_mcp_listing("request", item, user)
        self.assertEqual(listing["kind"], "request")
        self.assertEqual(listing["category"], "jobs")
        self.assertEqual(listing["price_rubles"], 60000)
        self.assertIn(listing["category"], VALID_MCP_CATEGORIES)

    def test_map_real_estate(self):
        item = {
            "id": 3,
            "text": "Сдам рабочее место в коворкинге на Бауманской",
            "property_type": "coworking",
            "property_address": "Москва, Бауманская 15",
            "price": 15000,
            "category": "general"
        }
        listing = map_civis_to_mcp_listing("offer", item, None)
        self.assertEqual(listing["category"], "real_estate")
        self.assertEqual(listing["locality"], "Москва, Бауманская 15")
        self.assertEqual(listing["price_rubles"], 15000)

    def test_enqueue_sync(self):
        ensure_mcp_tables()
        test_payload = {
            "title": "Тестовое объявление",
            "description": "Тестовое описание",
            "category": "business",
            "kind": "offer",
            "locality": "Казань",
            "price_rubles": 0
        }
        enqueue_sync(9999999, "offer", 101, test_payload)
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT tg_id, entity_type, entity_id, status FROM pending_marketplace_sync WHERE tg_id = 9999999 AND entity_id = 101")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 9999999)
        self.assertEqual(row[1], "offer")
        self.assertEqual(row[2], 101)
        self.assertEqual(row[3], "pending")
        
        # Cleanup test row
        cur.execute("DELETE FROM pending_marketplace_sync WHERE tg_id = 9999999 AND entity_id = 101")
        conn.commit()
        conn.close()


if __name__ == "__main__":
    unittest.main()
