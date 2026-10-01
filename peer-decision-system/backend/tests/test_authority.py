from sqlalchemy import select
from app.models import AuthorityMembership, Topic, LedgerEntry
from conftest import auth

def institutional(client, users, tags):
    response=client.post('/api/v1/topics', headers=auth(users[1]), json={
        'title':'Üniversite genelinde ders saatleri', 'description':'Üniversite genelindeki ders saatleri için değerlendirme önerisi.',
        'category':'Education','tag_ids':[tags[0].id], 'decision_scope':'UNIVERSITY'})
    assert response.status_code==201
    return response.json()['id']

def test_owner_and_admin_cannot_start_without_membership(client,setup):
    users,_,_,tags=setup
    id=institutional(client,users,tags)
    for user in [users[1],users[0],users[6]]:
        r=client.post(f'/api/v1/topics/{id}/start-voting',headers=auth(user))
        assert r.status_code==403 and 'Bu kararı siz alamazsınız' in r.json()['detail']
    assert client.get(f'/api/v1/topics/{id}',headers=auth(users[1])).json()['status']=='PROPOSED'

def test_only_admin_assigns_membership_and_board_can_decide(client,db,setup):
    users,_,_,tags=setup
    id=institutional(client,users,tags)
    path=f'/api/v1/admin/users/{users[1].id}/authorities'
    assert client.put(path,headers=auth(users[1]),json={'scopes':['UNIVERSITY']}).status_code==403
    for u in users[2:5]:
        assert client.put(f'/api/v1/admin/users/{u.id}/authorities',headers=auth(users[0]),json={'scopes':['UNIVERSITY']}).status_code==200
    assert client.post(f'/api/v1/topics/{id}/start-voting',headers=auth(users[2])).status_code==200
    for u in [users[1],users[0],users[6]]:
        assert client.post('/api/v1/votes',headers=auth(u),json={'target_type':'TOPIC','target_id':id,'choice':'YES'}).status_code==403
        assert client.post(f'/api/v1/topics/{id}/close-voting',headers=auth(u)).status_code==403
    for u in users[2:5]:
        assert client.post('/api/v1/votes',headers=auth(u),json={'target_type':'TOPIC','target_id':id,'choice':'YES'}).status_code==201
    assert client.post(f'/api/v1/topics/{id}/close-voting',headers=auth(users[2])).json()['status']=='ACCEPTED'
    assert db.get(Topic,id).status=='ACCEPTED'

def test_referral_idempotent_and_discussion_open(client,db,setup):
    users,_,_,tags=setup
    id=institutional(client,users,tags)
    for _ in range(2):
        assert client.post(f'/api/v1/topics/{id}/refer-to-authority',headers=auth(users[1])).status_code==200
    assert len(db.scalars(select(LedgerEntry).where(LedgerEntry.event_type=='AUTHORITY_REVIEW_REQUESTED')).all())==1
    assert client.get(f'/api/v1/topics/{id}',headers=auth(users[1])).json()['authority']['requested']
    assert client.post(f'/api/v1/topics/{id}/messages',headers=auth(users[7]),json={'message':'Öneriye ilişkin görüşüm.'}).status_code==201

def test_wrong_board_and_revocation(client,db,setup):
    users,_,_,tags=setup
    id=institutional(client,users,tags)
    path=f'/api/v1/admin/users/{users[2].id}/authorities'
    client.put(path,headers=auth(users[0]),json={'scopes':['FACULTY']})
    assert client.post(f'/api/v1/topics/{id}/start-voting',headers=auth(users[2])).status_code==403
    client.put(path,headers=auth(users[0]),json={'scopes':['UNIVERSITY']})
    assert client.post(f'/api/v1/topics/{id}/start-voting',headers=auth(users[2])).status_code==200
    client.put(path,headers=auth(users[0]),json={'scopes':[]})
    assert client.post('/api/v1/votes',headers=auth(users[2]),json={'target_type':'TOPIC','target_id':id,'choice':'YES'}).status_code==403

def test_scope_validation_and_no_self_grant(client,setup):
    users,_,_,tags=setup
    r=client.post('/api/v1/topics',headers=auth(users[1]),json={'title':'New topic','description':'Detailed description','category':'Education','tag_ids':[tags[0].id],'decision_scope':'ROOT'})
    assert r.status_code==422
    r=client.post('/api/v1/auth/register',json={'first_name':'New','last_name':'User','username':'newuser','email':'new@example.com','password':'Password123','authority_scopes':['UNIVERSITY']})
    assert r.status_code==422
