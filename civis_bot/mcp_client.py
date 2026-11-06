#!/usr/bin/env python3
"""
MCP Gateway Client for Civis Telegram Bot.
Connects Civis citizens with the Marketplace OS (MCP Rooms) coordinator.

Handles:
1. Dynamic bot registration and key provisioning via POST /api/bot/register-user
2. Dual-write mapping: Civis offers/requests -> MCP create_listing -> preview_listing -> publish_listing
3. Asymmetric semantic matching via match_listings
4. Safe background retry queue for resilient offline fallback
"""

import os
import logging
import sqlite3
import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "civis_data.db"

MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:3000/mcp")
MCP_REGISTER_URL = os.getenv("MCP_REGISTER_URL", "http://127.0.0.1:3000/api/bot/register-user")
BOT_SHARED_SECRET = os.getenv("BOT_SHARED_SECRET", "")

VALID_MCP_CATEGORIES = {
    'business', 'jobs', 'services', 'real_estate', 'communities', 
    'things', 'dating', 'rides', 'delivery', 'other'
}


def _http_post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int = 30) -> Tuple[int, Dict[str, Any]]:
    """Safe standard library HTTP POST returning (status_code, response_json)."""
    req_data = json.dumps(payload).encode("utf-8")
    all_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        **headers
    }
    req = urllib.request.Request(url, data=req_data, headers=all_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status_code = resp.getcode()
            raw_body = resp.read().decode("utf-8")
            return status_code, json.loads(raw_body) if raw_body else {}
    except urllib.error.HTTPError as e:
        raw_body = e.read().decode("utf-8")
        try:
            parsed = json.loads(raw_body)
        except Exception:
            parsed = {"error": raw_body}
        return e.code, parsed


def get_db_connection():
    """Returns SQLite connection to civis_data.db"""
    return sqlite3.connect(DB_PATH)


def ensure_mcp_tables():
    """Initializes queue and user key columns for MCP sync"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check users table for mcr_key if table exists
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if cur.fetchone():
        cur.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cur.fetchall()]
        if 'mcr_key' not in columns:
            cur.execute("ALTER TABLE users ADD COLUMN mcr_key TEXT")
            logger.info("Added 'mcr_key' column to users table")
        
    # Queue table for dual-write resilience
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pending_marketplace_sync (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tg_id INTEGER NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER NOT NULL,
            payload TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0,
            error_message TEXT,
            mcp_listing_id TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def ensure_mcr_key(tg_id: int, user_name: Optional[str] = None) -> Optional[str]:
    """
    Retrieves or provisions an MCP API key for a Civis citizen.
    Uses the protected POST /api/bot/register-user endpoint.
    """
    ensure_mcp_tables()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT mcr_key, name FROM users WHERE tg_id = ?", (tg_id,))
    row = cur.fetchone()
    
    if row and row[0]:
        conn.close()
        return row[0]
        
    name = user_name or (row[1] if row and row[1] else f"Citizen {tg_id}")
    conn.close()
    
    if not BOT_SHARED_SECRET:
        logger.warning("BOT_SHARED_SECRET is not configured. MCP key auto-issue disabled.")
        return None

    try:
        headers = {
            "X-Bot-Secret": BOT_SHARED_SECRET
        }
        payload = {
            "tg_id": tg_id,
            "name": name
        }
        status_code, data = _http_post_json(MCP_REGISTER_URL, payload, headers=headers, timeout=10)
        if status_code == 201:
            key = data.get("key")
            if key:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("UPDATE users SET mcr_key = ? WHERE tg_id = ?", (key, tg_id))
                conn.commit()
                conn.close()
                logger.info(f"Successfully provisioned MCP key for citizen tg_id={tg_id}")
                return key
        else:
            logger.error(f"Failed to provision MCP key for tg_id={tg_id}: HTTP {status_code} {data}")
    except Exception as e:
        logger.error(f"Network error provisioning MCP key for tg_id={tg_id}: {e}")
        
    return None


def mcp_json_rpc_call(key: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes an MCP tool call over JSON-RPC 2.0 to Marketplace OS.
    """
    headers = {
        "Authorization": f"Bearer {key}"
    }
    body = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000),
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    status_code, data = _http_post_json(MCP_URL, body, headers=headers, timeout=30)
    if status_code >= 400:
        raise RuntimeError(f"MCP HTTP Error {status_code}: {data}")
    if "error" in data:
        raise RuntimeError(f"MCP RPC Error ({data['error'].get('code')}): {data['error'].get('message')}")
    return data.get("result", {})


def map_civis_to_mcp_listing(entity_type: str, item: Dict[str, Any], user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Translates a Civis offer or request into the Marketplace OS create_listing contract.
    """
    raw_text = (item.get("text") or "").strip()
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    first_line = lines[0] if lines else "Объявление от гражданина Civis"
    
    # Title extraction (max 80 chars)
    title = first_line[:75] + "..." if len(first_line) > 75 else first_line
    
    # Kind
    kind = "offer" if entity_type == "offer" else "request"
    
    # Category mapping
    raw_cat = (item.get("category") or "").lower()
    if raw_cat in VALID_MCP_CATEGORIES:
        category = raw_cat
    else:
        # Derive from user role or property fields
        role = (user_profile.get("role") or "").lower() if user_profile else ""
        if "инвестор" in role or "координатор" in role:
            category = "business"
        elif "исполнитель" in role:
            category = "services"
        elif "заказчик" in role:
            category = "jobs"
        elif item.get("property_type"):
            category = "real_estate"
        else:
            category = "other"
            
    # Locality
    locality = item.get("property_address") or "Казань"
    
    # Price
    price_val = 0
    if kind == "offer":
        price_val = item.get("price") or 0
    else:
        price_val = item.get("price_max") or item.get("price_min") or 0
        
    try:
        price_rubles = int(price_val)
    except (ValueError, TypeError):
        price_rubles = 0

    return {
        "title": title,
        "description": raw_text,
        "category": category,
        "kind": kind,
        "locality": locality,
        "price_rubles": price_rubles,
        "modes": ["pickup", "online"]
    }


def publish_listing_pipeline(key: str, listing_args: Dict[str, Any]) -> str:
    """
    Performs 2-phase CAS publication on Marketplace OS:
    create_listing -> preview_listing (consent_token) -> publish_listing
    Returns published listing_id.
    """
    # 1. Create draft
    created = mcp_json_rpc_call(key, "create_listing", listing_args)
    listing_record = created.get("created_listing")
    if not listing_record:
        raise RuntimeError(f"create_listing returned no record: {created}")
        
    listing_id = listing_record["id"]
    revision = listing_record["revision"]

    # 2. Preview and get consent token
    preview = mcp_json_rpc_call(key, "preview_listing", {"listing_id": listing_id})
    consent_token = preview.get("consent_token")
    if not consent_token:
        raise RuntimeError(f"preview_listing returned no consent_token: {preview}")

    # 3. Publish to catalog
    published = mcp_json_rpc_call(key, "publish_listing", {
        "listing_id": listing_id,
        "consent_token": consent_token,
        "revision": revision
    })
    
    logger.info(f"Successfully published listing {listing_id} to Marketplace OS")
    return listing_id


def enqueue_sync(tg_id: int, entity_type: str, entity_id: int, payload: Dict[str, Any]):
    """
    Saves an outgoing item into the pending_marketplace_sync table for resilient dual-write.
    """
    ensure_mcp_tables()
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pending_marketplace_sync (
            tg_id, entity_type, entity_id, payload, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'pending', ?, ?)
    """, (
        tg_id, entity_type, entity_id, json.dumps(payload),
        datetime.now().isoformat(), datetime.now().isoformat()
    ))
    conn.commit()
    conn.close()


def process_single_sync(sync_id: int) -> bool:
    """Processes a single pending item from the sync queue"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, tg_id, entity_type, entity_id, payload, retry_count FROM pending_marketplace_sync WHERE id = ?", (sync_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False
        
    sid, tg_id, entity_type, entity_id, payload_str, retry_count = row
    payload = json.loads(payload_str)
    
    # 1. Ensure user has MCP key
    key = ensure_mcr_key(tg_id)
    if not key:
        cur.execute("""
            UPDATE pending_marketplace_sync 
            SET retry_count = retry_count + 1, error_message = 'No MCP key', updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), sid))
        conn.commit()
        conn.close()
        return False

    try:
        listing_id = publish_listing_pipeline(key, payload)
        cur.execute("""
            UPDATE pending_marketplace_sync 
            SET status = 'synced', mcp_listing_id = ?, updated_at = ?
            WHERE id = ?
        """, (listing_id, datetime.now().isoformat(), sid))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        error_msg = str(e)[:250]
        logger.warning(f"Sync item #{sid} failed (attempt {retry_count + 1}): {error_msg}")
        cur.execute("""
            UPDATE pending_marketplace_sync 
            SET status = CASE WHEN retry_count >= 5 THEN 'failed' ELSE 'pending' END,
                retry_count = retry_count + 1,
                error_message = ?,
                updated_at = ?
            WHERE id = ?
        """, (error_msg, datetime.now().isoformat(), sid))
        conn.commit()
        conn.close()
        return False


def find_marketplace_matches(key: str, text_query: str, kind: str, locality: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Searches complementary matches via Google Embeddings on Marketplace OS.
    """
    target_kind = "offer" if kind == "request" else "request"
    args = {
        "query": text_query,
        "query_kind": target_kind,
        "limit": 5
    }
    if locality:
        args["locality"] = locality
        
    res = mcp_json_rpc_call(key, "match_listings", args)
    return res.get("matches", [])


def create_private_room(key: str, listing_id: str, initial_message: str) -> Dict[str, Any]:
    """
    Opens a private negotiation room with the listing author.
    """
    return mcp_json_rpc_call(key, "join_room", {
        "listing_id": listing_id,
        "visibility": "private",
        "initial_message": initial_message
    })


import concurrent.futures

_sync_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="mcp_sync")


def trigger_background_sync(tg_id: int, entity_type: str, entity_id: int, payload: Dict[str, Any]):
    """
    Persistently enqueues an item in pending_marketplace_sync and dispatches
    a worker thread to execute the publication immediately in the background.
    """
    enqueue_sync(tg_id, entity_type, entity_id, payload)

    def _worker():
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT id FROM pending_marketplace_sync 
                WHERE status = 'pending' AND entity_type = ? AND entity_id = ? 
                ORDER BY id DESC LIMIT 1
            """, (entity_type, entity_id))
            row = cur.fetchone()
            conn.close()
            if row:
                process_single_sync(row[0])
        except Exception as err:
            logger.warning(f"Background worker error syncing {entity_type} #{entity_id}: {err}")

    _sync_pool.submit(_worker)


def process_all_pending_syncs(max_items: int = 10) -> int:
    """
    Batch processor for cron or periodic retry task.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM pending_marketplace_sync WHERE status = 'pending' ORDER BY id ASC LIMIT ?", (max_items,))
    ids = [r[0] for r in cur.fetchall()]
    conn.close()

    success_count = 0
    for sid in ids:
        if process_single_sync(sid):
            success_count += 1
    return success_count
