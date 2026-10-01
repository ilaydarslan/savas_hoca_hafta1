from fastapi import HTTPException

# Illustrative governance configuration, not Ankara University's real regulations.
SCOPES = {
    'COMMUNITY': {'label': 'Öğrenci topluluğu · gönüllü etkinlik / akran öğrenme', 'body': 'İlgili katılımcılar'},
    'DEPARTMENT': {'label': 'Bölüm · bölüm içi düzenleme', 'body': 'Demo Bölüm Kurulu'},
    'FACULTY': {'label': 'Fakülte · fakülte genelinde düzenleme', 'body': 'Demo Fakülte Kurulu'},
    'UNIVERSITY': {'label': 'Ankara Üniversitesi · üniversite genelinde düzenleme', 'body': 'Ankara Üniversitesi Yönetim Kurulu (demo yetki eşlemesi)'},
}

def scope_of(topic):
    return topic.decision_scope or 'COMMUNITY'

def authorized(user, topic):
    scope = scope_of(topic)
    return scope == 'COMMUNITY' or any(m.scope == scope for m in user.authorities)

def require_authority(user, topic):
    if not authorized(user, topic):
        raise HTTPException(403, f'Bu kararı siz alamazsınız. Yetkili organ: {SCOPES[scope_of(topic)]["body"]}. Önerinizi bu kurula değerlendirme için iletebilirsiniz. ADMIN veya EXPERT rolü tek başına karar yetkisi vermez.')

def can_manage(user, topic, owner_id=None):
    if scope_of(topic) != 'COMMUNITY':
        return authorized(user, topic)
    return user.role == 'ADMIN' or user.id == (owner_id or topic.created_by)

def authority_info(user, topic):
    scope = scope_of(topic)
    return {'scope': scope, 'label': SCOPES[scope]['label'], 'body': SCOPES[scope]['body'],
            'authorized': authorized(user, topic), 'restricted': scope != 'COMMUNITY',
            'requested': bool(topic.authority_requested), 'demo': True}
