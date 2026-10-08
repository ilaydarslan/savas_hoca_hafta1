"""Transactional hash-chain audit recording and verification."""
import hashlib
import json
from sqlalchemy import select
from app.models import LedgerEntry, now

def digest(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
def append_ledger(db, event, entity, id, payload):
    previous = db.scalar(select(LedgerEntry).order_by(LedgerEntry.id.desc()).limit(1))
    entry = LedgerEntry(event_type=event, entity_type=entity, entity_id=id, payload=payload,
                        data_hash=digest(payload), previous_hash=previous.current_hash if previous else '0'*64, created_at=now())
    entry.current_hash = digest([entry.event_type, entry.entity_type, entry.entity_id, entry.data_hash, entry.previous_hash, entry.created_at])
    db.add(entry)
    db.flush()
    return entry
def verify_ledger(db):
    previous = '0'*64
    entries = db.scalars(select(LedgerEntry).order_by(LedgerEntry.id)).all()
    for entry in entries:
        expected = digest([entry.event_type, entry.entity_type, entry.entity_id, digest(entry.payload), previous, entry.created_at])
        if entry.previous_hash != previous or entry.data_hash != digest(entry.payload) or expected != entry.current_hash:
            return {'verified': False, 'count': len(entries), 'error_at': entry.id}
        previous = entry.current_hash
    return {'verified': True, 'count': len(entries), 'head_hash': previous}
