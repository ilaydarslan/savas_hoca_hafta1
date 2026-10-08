"""Single-worker write serialization shared by application endpoints."""
from threading import RLock

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

write_lock = RLock()


def commit(db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Kayıt zaten mevcut veya ilişki kısıtı ihlal edildi.')
