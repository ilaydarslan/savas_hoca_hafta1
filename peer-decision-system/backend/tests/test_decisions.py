import pytest
from fastapi import HTTPException
from sqlalchemy import select,func
from sqlalchemy.exc import IntegrityError
from app.models import *
from app.services.decisions import *
from conftest import auth

def cast_many(db,users,topic,choices):
    for user,choice in zip(users,choices):
        cast_vote(db,user,'TOPIC',topic.id,choice)

def test_duplicate_vote_api(client,setup):
    users,t,*_=setup
    data={'target_type':'TOPIC','target_id':t.id,'choice':'YES'}
    assert client.post('/api/v1/votes',json=data,headers=auth(users[1])).status_code==201
    assert client.post('/api/v1/votes',json=data,headers=auth(users[1])).status_code==409

def test_duplicate_vote_database(db,setup):
    users,t,*_=setup
    db.add(Vote(user_id=users[1].id,topic_id=t.id,choice='YES'));db.commit()
    db.add(Vote(user_id=users[1].id,topic_id=t.id,choice='NO'))
    with pytest.raises(IntegrityError):db.commit()
    db.rollback()

def test_unrelated_cannot_vote(client,setup):
    users,t,*_=setup
    r=client.post('/api/v1/votes',json={'target_type':'TOPIC','target_id':t.id,'choice':'YES'},headers=auth(users[7]))
    assert r.status_code==403

@pytest.mark.parametrize('choices,accepted', [(['YES','NO','ABSTAIN'],False),(['YES','YES','ABSTAIN'],True),(['YES','NO','NO'],False)])
def test_normal_majority_and_abstention(db,setup,choices,accepted):
    users,t,*_=setup
    cast_many(db,users,t,choices)
    result=close_vote(db,users[0],'TOPIC',t.id)
    assert (result['status']=='ACCEPTED')==accepted
    assert summary(db,t)['participants']==3

@pytest.mark.parametrize('choices,accepted',[(['YES','YES','YES','NO','NO'],True),(['YES','YES','NO','NO','ABSTAIN'],False)])
def test_high_sixty_percent(db,setup,choices,accepted):
    users,t,*_=setup;t.impact_level='HIGH'
    cast_many(db,users,t,choices)
    assert (close_vote(db,users[0],'TOPIC',t.id)['status']=='ACCEPTED')==accepted

def test_minority_conflict(db,setup):
    users,t,teams,_=setup;t.affected_team_id=teams[0].id
    cast_many(db,users,t,['NO','NO','YES','YES','YES','YES','YES'])
    s=summary(db,t)
    assert s['yes_ratio']>.6 and s['affected_support']<.4
    close_vote(db,users[0],'TOPIC',t.id)
    assert t.status=='VOTING' and t.decision_flag=='MINORITY_CONFLICT' and t.policy_status=='BLOCKED'

def test_unrepresented_affected_team_blocks(db,setup):
    users,t,teams,_=setup;t.affected_team_id=teams[0].id
    cast_many(db,users[3:6],t,['YES']*3)
    assert close_vote(db,users[0],'TOPIC',t.id)['decision_flag']=='MINORITY_CONFLICT'

def test_no_quorum_remains_open(db,setup):
    users,t,*_=setup
    cast_many(db,users,t,['YES','YES'])
    with pytest.raises(HTTPException) as error:close_vote(db,users[0],'TOPIC',t.id)
    assert error.value.status_code==409 and t.status=='VOTING'

def test_policy_blocks_accepted_high_without_expert(db,setup):
    users,t,*_=setup;t.impact_level='HIGH'
    cast_many(db,users,t,['YES']*3)
    close_vote(db,users[0],'TOPIC',t.id)
    assert t.status=='ACCEPTED' and t.policy_status=='BLOCKED'
    assert any(c.status=='BLOCKED' and 'EXPERT_REVIEW' in c.detail for c in db.scalars(select(RuleCheck)))

def test_policy_review_unblocks_without_changing_vote(db,setup):
    users,t,*_=setup;t.impact_level='HIGH'
    cast_many(db,users,t,['YES']*3);close_vote(db,users[0],'TOPIC',t.id)
    db.add(ExpertReview(topic_id=t.id,expert_id=users[6].id,opinion='Expert approves the approach.',recommendation='APPROVE'));db.flush()
    assert check_policy(db,t)=='COMPLIANT'
    assert summary(db,t)['participants']==3

def test_ledger_detects_payload_and_metadata_tamper(db,setup):
    users,t,*_=setup
    e=append_ledger(db,'TOPIC_CREATED','TOPIC',t.id,{'title':t.title})
    append_ledger(db,'OTHER_EVENT','TOPIC',t.id,{'value':2})
    assert verify_ledger(db)['verified']
    e.payload={'title':'tampered'};db.flush()
    assert not verify_ledger(db)['verified']
    e.payload={'title':t.title};db.flush()
    assert verify_ledger(db)['verified']
    e.event_type='FORGED';db.flush()
    assert not verify_ledger(db)['verified']

def test_archive_preserves_message(db,setup):
    users,t,*_=setup
    m=DiscussionMessage(topic_id=t.id,user_id=users[1].id,message='Original content')
    db.add(m);db.flush()
    p=DeletionProposal(message_id=m.id,proposed_by=users[1].id,reason='Duplicate content')
    db.add(p);db.flush()
    for u in users[:3]:cast_vote(db,u,'DELETION',p.id,'YES')
    close_vote(db,users[0],'DELETION',p.id)
    db.commit()
    assert db.get(DiscussionMessage,m.id).status=='ARCHIVED'
    assert db.get(DiscussionMessage,m.id).message=='Original content'
    assert db.scalar(select(func.count()).select_from(DiscussionMessage))==1
    assert verify_ledger(db)['verified']

def test_reputation_does_not_weight_vote(db,setup):
    users,t,*_=setup
    users[0].reputation_coefficient=1.2;users[1].reputation_coefficient=.8
    cast_many(db,users,t,['YES','NO','ABSTAIN'])
    assert summary(db,t)['yes_ratio']==.5

def test_point_limits_and_idempotence(db,setup):
    users,t,*_=setup
    for i in range(20):award(db,users[1].id,t.id,2,'QUALITY',f'point-{i}')
    assert users[1].points==8
    other=Topic(title='Other',description='Other topic',category='Education',created_by=users[1].id)
    db.add(other);db.flush()
    award(db,users[1].id,other.id,3,'QUALITY','other')
    award(db,users[1].id,other.id,3,'QUALITY','other')
    assert users[1].points==10
    assert .8<=users[1].reputation_coefficient<=1.2

def test_subtopic_vote_and_unique_constraint(db,setup):
    users,t,*_=setup;t.status='ACCEPTED'
    sub=SubTopic(topic_id=t.id,created_by=users[1].id,title='Subtopic',description='Description')
    db.add(sub);db.flush()
    for u in users[:3]:cast_vote(db,u,'SUBTOPIC',sub.id,'YES')
    assert close_vote(db,users[0],'SUBTOPIC',sub.id)['status']=='ACCEPTED'
    db.commit()
    db.add(Vote(user_id=users[0].id,subtopic_id=sub.id,choice='NO'))
    with pytest.raises(IntegrityError):db.commit()
    db.rollback()

def test_vote_requires_exactly_one_target(db,setup):
    users,t,*_=setup
    db.add(Vote(user_id=users[0].id,choice='YES'))
    with pytest.raises(IntegrityError):db.commit()
    db.rollback()

def test_team_snapshot_stays_stable(db,setup):
    users,t,teams,_=setup;t.affected_team_id=teams[0].id
    cast_vote(db,users[1],'TOPIC',t.id,'NO')
    users[1].team_id=teams[1].id;db.flush()
    assert summary(db,t)['affected_support']==0

def test_auth_roles_and_input_validation(client,setup):
    users,t,*_=setup
    assert client.get('/api/v1/topics').status_code==401
    assert client.get('/api/v1/admin/users',headers=auth(users[1])).status_code==403
    assert client.get('/api/v1/admin/users',headers=auth(users[0])).status_code==200
    assert client.post('/api/v1/votes',headers=auth(users[1]),json={'target_type':'TOPIC','target_id':t.id,'choice':'MAYBE'}).status_code==422
    assert client.post(f'/api/v1/topics/{t.id}/close-voting',headers=auth(users[2])).status_code==403

def test_expert_scope_and_no_unilateral_decision(client,db,setup):
    users,t,_,tags=setup
    body={'opinion':'This proposal should be revised.','recommendation':'REVISION_REQUIRED'}
    assert client.post(f'/api/v1/topics/{t.id}/expert-reviews',json=body,headers=auth(users[1])).status_code==403
    assert client.post(f'/api/v1/topics/{t.id}/expert-reviews',json=body,headers=auth(users[6])).status_code==201
    assert t.status=='VOTING'
    users[6].interests=[tags[1]];db.commit()
    assert client.post(f'/api/v1/topics/{t.id}/expert-reviews',json=body,headers=auth(users[6])).status_code==403

def test_readonly_ledger_and_no_message_delete(client,db,setup):
    users,t,*_=setup
    e=append_ledger(db,'TEST','TOPIC',t.id,{})
    assert client.delete(f'/api/v1/ledger/{e.id}',headers=auth(users[0])).status_code in (404,405)
    assert client.put(f'/api/v1/ledger/{e.id}',json={},headers=auth(users[0])).status_code in (404,405)
    assert client.delete('/api/v1/messages/1',headers=auth(users[0])).status_code in (404,405)

def test_registration_cannot_escalate_role(client,setup):
    body={'first_name':'New','last_name':'User','username':'newuser','email':'new@example.com','password':'LongPassword123!','role':'ADMIN'}
    assert client.post('/api/v1/auth/register',json=body).status_code==422
    del body['role']
    r=client.post('/api/v1/auth/register',json=body)
    assert r.status_code==201 and r.json()['user']['role']=='USER'
    assert 'password_hash' not in r.json()['user']
    assert client.post('/api/v1/auth/login',json={'email':body['email'],'password':body['password']}).status_code==200
    assert client.post('/api/v1/auth/login',json={'email':body['email'],'password':'wrong'}).status_code==401

def test_comment_spam_gives_no_points(client,db,setup):
    users,t,*_=setup
    for _ in range(4):
        assert client.post(f'/api/v1/topics/{t.id}/messages',headers=auth(users[1]),json={'message':'My repeated contribution'}).status_code==201
    assert users[1].points==0

def test_proposed_topic_lifecycle(client,setup):
    users,_,_,tags=setup
    r=client.post('/api/v1/topics',headers=auth(users[1]),json={'title':'A new proposal','description':'A detailed proposal with enough information to vote on.','category':'Education','tag_ids':[tags[0].id]})
    assert r.status_code==201 and r.json()['status']=='PROPOSED'
    id=r.json()['id']
    assert client.post(f'/api/v1/topics/{id}/subtopics',headers=auth(users[1]),json={'title':'New subtopic','description':'A detailed subtopic.'}).status_code==409
    assert client.post(f'/api/v1/topics/{id}/start-voting',headers=auth(users[2])).status_code==403
    assert client.post(f'/api/v1/topics/{id}/start-voting',headers=auth(users[1])).status_code==200

def test_rule_edit_rechecks_accepted_topics(client,db,setup):
    users,t,*_=setup
    cast_many(db,users,t,['YES']*3);close_vote(db,users[0],'TOPIC',t.id);db.commit()
    r=client.put('/api/v1/admin/rules/3',headers=auth(users[0]),json={'code':'RULE-003','name':'Higher quorum','description':'Five participants required','category':'Test','condition':{'kind':'QUORUM','value':5},'severity':'BLOCKED'})
    assert r.status_code==200 and t.policy_status=='BLOCKED'
