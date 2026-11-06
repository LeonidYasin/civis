#!/usr/bin/env python3
"""
Civis to Marketplace OS Initial Data Migration Script.
Imports existing offers and requests from civis_data.db into Marketplace OS.

Usage:
    python scripts/migrate_civis_to_marketplace.py [--publish]
"""

import sys
import os
import argparse
from pathlib import Path

# Add civis_bot to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent / "civis_bot"))

from mcp_client import (
    get_db_connection,
    ensure_mcp_tables,
    map_civis_to_mcp_listing,
    enqueue_sync,
    process_single_sync
)
from database import get_user, init_db


def migrate_data(auto_publish: bool = False):
    init_db()
    ensure_mcp_tables()
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("=" * 60)
    print("🚀 CIVIS -> MARKETPLACE OS MIGRATION TOOL")
    print("=" * 60)
    
    # 1. Offers
    cur.execute("SELECT id, tg_id, category, text, price, property_type, property_area, property_address, property_rooms FROM offers")
    offers = cur.fetchall()
    print(f"📦 Found {len(offers)} existing offers in Civis database.")
    
    # 2. Requests
    cur.execute("SELECT id, tg_id, category, text, price_min, price_max, property_type, property_area_min, property_area_max, property_address, property_rooms_min, property_rooms_max FROM requests")
    requests_list = cur.fetchall()
    print(f"📦 Found {len(requests_list)} existing requests in Civis database.\n")
    
    total_enqueued = 0
    total_published = 0
    
    for row in offers:
        oid, tg_id, cat, text, price, p_type, p_area, p_addr, p_rooms = row
        item = {
            "id": oid,
            "category": cat,
            "text": text,
            "price": price,
            "property_type": p_type,
            "property_area": p_area,
            "property_address": p_addr,
            "property_rooms": p_rooms
        }
        # Check if already enqueued
        cur.execute("SELECT id, status FROM pending_marketplace_sync WHERE entity_type = 'offer' AND entity_id = ?", (oid,))
        existing = cur.fetchone()
        if not existing:
            user = get_user(tg_id)
            payload = map_civis_to_mcp_listing("offer", item, user)
            enqueue_sync(tg_id, "offer", oid, payload)
            total_enqueued += 1
            print(f"  [+] Enqueued offer #{oid} ('{payload['title']}')")
            
    for row in requests_list:
        rid, tg_id, cat, text, p_min, p_max, p_type, a_min, a_max, p_addr, r_min, r_max = row
        item = {
            "id": rid,
            "category": cat,
            "text": text,
            "price_min": p_min,
            "price_max": p_max,
            "property_type": p_type,
            "property_area_min": a_min,
            "property_area_max": a_max,
            "property_address": p_addr,
            "property_rooms_min": r_min,
            "property_rooms_max": r_max
        }
        cur.execute("SELECT id, status FROM pending_marketplace_sync WHERE entity_type = 'request' AND entity_id = ?", (rid,))
        existing = cur.fetchone()
        if not existing:
            user = get_user(tg_id)
            payload = map_civis_to_mcp_listing("request", item, user)
            enqueue_sync(tg_id, "request", rid, payload)
            total_enqueued += 1
            print(f"  [+] Enqueued request #{rid} ('{payload['title']}')")

    conn.close()
    print(f"\n✅ Total enqueued items: {total_enqueued}")
    
    if auto_publish:
        print("\n⚡ Processing pending sync queue to Marketplace OS...")
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id FROM pending_marketplace_sync WHERE status = 'pending'")
        pending_ids = [r[0] for r in cur.fetchall()]
        conn.close()
        
        for sid in pending_ids:
            ok = process_single_sync(sid)
            if ok:
                total_published += 1
                print(f"  [✓] Synced queue item #{sid} to Marketplace OS")
            else:
                print(f"  [!] Failed queue item #{sid} (check logs / offline)")
                
        print(f"\n🎉 Successfully published {total_published}/{len(pending_ids)} items to Marketplace OS!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Civis items to Marketplace OS")
    parser.add_argument("--publish", action="store_true", help="Immediately attempt to publish to MCP server")
    args = parser.parse_args()
    
    migrate_data(auto_publish=args.publish)
