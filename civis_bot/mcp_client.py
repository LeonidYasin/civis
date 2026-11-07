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
import threading
import concurrent.futures
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
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


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
            action TEXT DEFAULT 'create_listing',
            payload TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            retry_count INTEGER DEFAULT 0,
            guard_skip_count INTEGER DEFAULT 0,
            error_message TEXT,
            mcp_listing_id TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    cur.execute("PRAGMA table_info(pending_marketplace_sync)")
    pms_columns = [col[1] for col in cur.fetchall()]
    if 'action' not in pms_columns:
        cur.execute("ALTER TABLE pending_marketplace_sync ADD COLUMN action TEXT DEFAULT 'create_listing'")
        cur.execute("UPDATE pending_marketplace_sync SET action = 'create_listing' WHERE action IS NULL")
    if 'guard_skip_count' not in pms_columns:
        cur.execute("ALTER TABLE pending_marketplace_sync ADD COLUMN guard_skip_count INTEGER DEFAULT 0")
    if 'error_message' not in pms_columns:
        cur.execute("ALTER TABLE pending_marketplace_sync ADD COLUMN error_message TEXT")
    if 'mcp_listing_id' not in pms_columns:
        cur.execute("ALTER TABLE pending_marketplace_sync ADD COLUMN mcp_listing_id TEXT")

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


def enqueue_sync(tg_id: int, entity_type: str, entity_id: int, payload: Dict[str, Any], action: str = "create_listing") -> int:
    """
    Saves an outgoing item into the pending_marketplace_sync table for resilient dual-write.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()
    cur.execute("""
        INSERT INTO pending_marketplace_sync (
            tg_id, entity_type, entity_id, action, payload, status, retry_count, guard_skip_count, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'pending', 0, 0, ?, ?)
    """, (
        tg_id, entity_type, entity_id, action, json.dumps(payload),
        now_iso, now_iso
    ))
    sync_id = cur.lastrowid
    conn.commit()
    conn.close()
    return sync_id


def _handle_sync_error(conn: sqlite3.Connection, sid: int, retry_count: int, error_msg: str) -> bool:
    new_retry = retry_count + 1
    new_status = 'failed' if new_retry >= 5 else 'pending'
    now_iso = datetime.now().isoformat()
    cur = conn.cursor()
    cur.execute("""
        UPDATE pending_marketplace_sync 
        SET status = ?,
            retry_count = ?,
            error_message = ?,
            updated_at = ?
        WHERE id = ?
    """, (new_status, new_retry, error_msg, now_iso, sid))
    conn.commit()
    conn.close()
    return False


def process_single_sync(sync_id: int) -> bool:
    """Processes a single pending item from the sync queue with atomic claim and race guards."""
    conn = get_db_connection()
    cur = conn.cursor()
    now_iso = datetime.now().isoformat()

    # 1. Atomic claim: transition from pending to processing
    cur.execute("""
        UPDATE pending_marketplace_sync
        SET status = 'processing', updated_at = ?
        WHERE id = ? AND status = 'pending'
    """, (now_iso, sync_id))
    if cur.rowcount == 0:
        conn.close()
        return False
    conn.commit()

    cur.execute("""
        SELECT id, tg_id, entity_type, entity_id, action, payload, retry_count, guard_skip_count
        FROM pending_marketplace_sync WHERE id = ?
    """, (sync_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False

    sid, tg_id, entity_type, entity_id, action, payload_str, retry_count, guard_skip_count = row
    payload = json.loads(payload_str) if payload_str else {}
    table_name = "offers" if entity_type == "offer" else "requests"

    # --- REVOKE BRANCH ---
    if action == "revoke_listing":
        # Cancel any pending creates for this entity
        cur.execute("""
            UPDATE pending_marketplace_sync
            SET status = 'cancelled', updated_at = ?
            WHERE entity_type = ? AND entity_id = ? AND action = 'create_listing' AND status = 'pending'
        """, (now_iso, entity_type, entity_id))
        conn.commit()

        # Check if entity was ever published to MCP (has mcp_listing_id)
        cur.execute(f"SELECT mcp_listing_id FROM {table_name} WHERE id = ?", (entity_id,))
        ent_row = cur.fetchone()
        mcp_listing_id = ent_row[0] if ent_row else None

        if not mcp_listing_id:
            # Never published on MCP - finalize locally without MCP call
            cur.execute(f"UPDATE {table_name} SET status = 'deleted' WHERE id = ?", (entity_id,))
            cur.execute("""
                UPDATE pending_marketplace_sync
                SET status = 'synced', updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), sid))
            conn.commit()
            conn.close()
            return True

        # Call withdraw_listing on MCP
        key = ensure_mcr_key(tg_id)
        if not key:
            return _handle_sync_error(conn, sid, retry_count, "No MCP key")

        try:
            res = mcp_json_rpc_call(key, "withdraw_listing", {"listing_id": mcp_listing_id})
        except Exception as e:
            return _handle_sync_error(conn, sid, retry_count, str(e)[:250])

        # Validate response shape
        if not isinstance(res, dict):
            return _handle_sync_error(conn, sid, retry_count, f"unexpected_type: {type(res)}")
        tool_data = res.get("data")
        if not isinstance(tool_data, dict):
            return _handle_sync_error(conn, sid, retry_count, f"unexpected_data_shape: {res}")

        err = tool_data.get("error")
        if err:
            if err == "not_found":
                pass  # Idempotent success (already deleted or absent on MCP)
            else:
                return _handle_sync_error(conn, sid, retry_count, f"mcp_error: {err}")
        elif tool_data.get("success") is not True:
            return _handle_sync_error(conn, sid, retry_count, f"unexpected_response: {tool_data}")

        # Revoke success
        cur.execute(f"UPDATE {table_name} SET status = 'deleted' WHERE id = ?", (entity_id,))
        cur.execute("""
            UPDATE pending_marketplace_sync
            SET status = 'synced', updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), sid))
        conn.commit()
        conn.close()
        return True

    # --- CREATE BRANCH ---
    if action == "create_listing":
        # Check if revoke is pending for this entity
        cur.execute("""
            SELECT id FROM pending_marketplace_sync
            WHERE entity_type = ? AND entity_id = ? AND action = 'revoke_listing' AND status = 'pending'
        """, (entity_type, entity_id))
        pending_revoke = cur.fetchone()
        if pending_revoke:
            if guard_skip_count < 3:
                # Yield to revoke
                cur.execute("""
                    UPDATE pending_marketplace_sync
                    SET status = 'pending', guard_skip_count = guard_skip_count + 1, updated_at = ?
                    WHERE id = ?
                """, (now_iso, sid))
                conn.commit()
                conn.close()
                return False
            # guard_skip_count >= 3 -> break livelock and proceed

        key = ensure_mcr_key(tg_id)
        if not key:
            return _handle_sync_error(conn, sid, retry_count, "No MCP key")

        try:
            listing_id = publish_listing_pipeline(key, payload)
        except Exception as e:
            return _handle_sync_error(conn, sid, retry_count, str(e)[:250])

        cur.execute(f"UPDATE {table_name} SET mcp_listing_id = ? WHERE id = ?", (listing_id, entity_id))
        cur.execute("""
            UPDATE pending_marketplace_sync 
            SET status = 'synced', mcp_listing_id = ?, updated_at = ?
            WHERE id = ?
        """, (listing_id, datetime.now().isoformat(), sid))
        conn.commit()

        # Check for chained revoke queued while publication was executing
        cur.execute("""
            SELECT id FROM pending_marketplace_sync
            WHERE entity_type = ? AND entity_id = ? AND action = 'revoke_listing' AND status = 'pending'
            ORDER BY id ASC LIMIT 1
        """, (entity_type, entity_id))
        chained_revoke = cur.fetchone()
        conn.close()

        if chained_revoke:
            chained_sid = chained_revoke[0]
            _sync_pool.submit(lambda: process_single_sync(chained_sid))

        return True

    # Unknown action
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


_sync_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="mcp_sync")
_scanner_stop_event = threading.Event()
_scanner_thread = None


def trigger_background_sync(tg_id: int, entity_type: str, entity_id: int, payload: Dict[str, Any], action: str = "create_listing") -> int:
    """
    Persistently enqueues an item in pending_marketplace_sync and dispatches
    a worker thread to execute the publication or revocation immediately in the background.
    """
    sync_id = enqueue_sync(tg_id, entity_type, entity_id, payload, action=action)
    _sync_pool.submit(lambda: process_single_sync(sync_id))
    return sync_id


def process_all_pending_syncs(max_items: int = 10) -> int:
    """
    Batch processor for periodic retry scanner.
    Picks up pending tasks with retry_count < 5.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id FROM pending_marketplace_sync 
        WHERE status = 'pending' AND retry_count < 5 
        ORDER BY id ASC LIMIT ?
    """, (max_items,))
    ids = [r[0] for r in cur.fetchall()]
    conn.close()

    success_count = 0
    for sid in ids:
        if process_single_sync(sid):
            success_count += 1
    return success_count


def is_scanner_alive() -> bool:
    """Returns True if the background scanner thread is active and running."""
    global _scanner_thread
    return bool(_scanner_thread and _scanner_thread.is_alive())


def start_periodic_sync_scanner(interval_seconds: float = 30.0):
    """Starts background scanner thread checking pending retries."""
    global _scanner_thread, _scanner_stop_event
    if _scanner_thread and _scanner_thread.is_alive():
        return
    _scanner_stop_event.clear()

    def _scanner_loop():
        while not _scanner_stop_event.is_set():
            try:
                if _scanner_stop_event.wait(interval_seconds):
                    break
                process_all_pending_syncs()
            except Exception as e:
                logger.exception(f"Unexpected error in periodic sync scanner loop: {e}")

    _scanner_thread = threading.Thread(target=_scanner_loop, daemon=True, name="sync_scanner")
    _scanner_thread.start()


def stop_periodic_sync_scanner(timeout: float = 2.0):
    """Gracefully stops background scanner thread."""
    global _scanner_thread, _scanner_stop_event
    if _scanner_stop_event:
        _scanner_stop_event.set()
    if _scanner_thread and _scanner_thread.is_alive():
        _scanner_thread.join(timeout=timeout)


