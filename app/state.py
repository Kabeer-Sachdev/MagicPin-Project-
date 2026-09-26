from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class StateStore:
    def __init__(self):
        self.start_time: float = time.time()
        # Key: (scope, context_id) -> {"version": int, "payload": dict, "previous_payload": Optional[dict], "delivered_at": str, "updated_at": str}
        self.contexts: Dict[Tuple[str, str], Dict[str, Any]] = {}
        # Key: suppression_key -> {"expires_at": Optional[str], "added_at": str, "reason": str}
        self.suppressions: Dict[str, Dict[str, Any]] = {}
        # Key: conversation_id -> dict with conv state
        self.conversations: Dict[str, Dict[str, Any]] = {}

    def get_uptime_seconds(self) -> int:
        return int(time.time() - self.start_time)

    def get_contexts_loaded(self) -> Dict[str, int]:
        counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
        for (scope, _), _ in self.contexts.items():
            if scope in counts:
                counts[scope] += 1
            else:
                counts[scope] = 1
        return counts

    def push_context(self, scope: str, context_id: str, version: int, payload: dict, delivered_at: str) -> Tuple[bool, Optional[str], Optional[int]]:
        key = (scope, context_id)
        existing = self.contexts.get(key)
        if existing and existing["version"] >= version:
            return False, "stale_version", existing["version"]

        prev_payload = existing["payload"] if existing else None

        self.contexts[key] = {
            "version": version,
            "payload": payload,
            "previous_payload": prev_payload,
            "delivered_at": delivered_at,
            "updated_at": datetime.utcnow().isoformat() + "Z"
        }
        return True, None, version

    def get_context_entry(self, scope: str, context_id: str) -> Optional[dict]:
        return self.contexts.get((scope, context_id))

    def get_context(self, scope: str, context_id: str) -> Optional[dict]:
        entry = self.get_context_entry(scope, context_id)
        return entry["payload"] if entry else None

    def get_all_contexts_by_scope(self, scope: str) -> Dict[str, dict]:
        res = {}
        for (s, cid), entry in self.contexts.items():
            if s == scope:
                res[cid] = entry["payload"]
        return res

    def is_suppressed(self, suppression_key: str) -> bool:
        if not suppression_key:
            return False
        return suppression_key in self.suppressions

    def add_suppression(self, suppression_key: str, reason: str = "handled", expires_at: Optional[str] = None):
        if suppression_key:
            self.suppressions[suppression_key] = {
                "reason": reason,
                "expires_at": expires_at,
                "added_at": datetime.utcnow().isoformat() + "Z"
            }

    def remove_suppression(self, suppression_key: str):
        if suppression_key in self.suppressions:
            del self.suppressions[suppression_key]

    def get_conversation(self, conversation_id: str) -> Optional[dict]:
        return self.conversations.get(conversation_id)

    def update_conversation(self, conversation_id: str, updates: dict) -> dict:
        conv = self.conversations.setdefault(conversation_id, {
            "conversation_id": conversation_id,
            "merchant_id": None,
            "customer_id": None,
            "status": "IDLE",
            "consecutive_auto_replies": 0,
            "turns": [],
            "last_action": None,
            "suppression_key": None
        })
        conv.update(updates)
        return conv

    def add_turn(self, conversation_id: str, role: str, message: str, ts: Optional[str] = None):
        conv = self.get_conversation(conversation_id) or self.update_conversation(conversation_id, {})
        conv["turns"].append({
            "from_role": role,
            "message": message,
            "ts": ts or datetime.utcnow().isoformat() + "Z"
        })
        # Keep conversation history bounded to last 20 turns
        if len(conv["turns"]) > 20:
            conv["turns"] = conv["turns"][-20:]


# Global singleton store
store = StateStore()
