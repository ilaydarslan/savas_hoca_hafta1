from sqlalchemy import select

from app.models import LedgerEntry, ProjectCanvas
from app.routers.canvas import DEFAULT_FIELDS
from app.services.ledger import verify_ledger
from conftest import auth


def test_canvas_requires_login_and_defaults_are_not_saved(client, db, setup):
    users, *_ = setup
    assert client.get('/api/v1/engineering/canvas').status_code == 401
    response = client.get('/api/v1/engineering/canvas', headers=auth(users[1]))
    assert response.status_code == 200
    assert response.json()['fields'] == DEFAULT_FIELDS
    assert response.json()['updated_at'] is None
    assert db.get(ProjectCanvas, 1) is None


def test_canvas_admin_save_persists_and_audits(client, db, setup):
    users, *_ = setup
    fields = {**DEFAULT_FIELDS, 'business_goal': 'A reviewed measurable project goal.'}
    for user in (users[1], users[6]):
        assert client.put('/api/v1/engineering/canvas', headers=auth(user), json={'fields': fields}).status_code == 403
    response = client.put('/api/v1/engineering/canvas', headers=auth(users[0]), json={'fields': fields})
    assert response.status_code == 200
    db.expire_all()
    assert client.get('/api/v1/engineering/canvas', headers=auth(users[1])).json()['fields'] == fields
    assert db.get(ProjectCanvas, 1).updated_by == users[0].id
    event = db.scalar(select(LedgerEntry).where(LedgerEntry.event_type == 'PROJECT_CANVAS_UPDATED'))
    assert event.payload['fields'] == fields
    assert verify_ledger(db)['verified']


def test_canvas_rejects_incomplete_or_extra_fields(client, setup):
    users, *_ = setup
    for fields in ({'business_goal': 'x'}, {**DEFAULT_FIELDS, 'extra': 'unexpected'}):
        assert client.put('/api/v1/engineering/canvas', headers=auth(users[0]), json={'fields': fields}).status_code == 422
