import os
import secrets
from pathlib import Path
from datetime import datetime, timedelta, timezone
import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import User

secret_file = Path('.jwt-secret')
SECRET = os.getenv('JWT_SECRET')
if not SECRET:
    if not secret_file.exists():
        secret_file.write_text(secrets.token_urlsafe(48))
    SECRET = secret_file.read_text().strip()
hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
def token(user):
    return jwt.encode({'sub': str(user.id), 'exp': datetime.now(timezone.utc) + timedelta(hours=8)}, SECRET, algorithm='HS256')
def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    try:
        data = jwt.decode(credentials.credentials, SECRET, algorithms=['HS256'])
        user = db.get(User, int(data['sub']))
        if user is None:
            raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError, AttributeError, KeyError):
        raise HTTPException(401, 'Oturum geçersiz veya süresi dolmuş.')
def admin(user=Depends(current_user)):
    if user.role != 'ADMIN':
        raise HTTPException(403, 'Yönetici yetkisi gerekiyor.')
    return user
