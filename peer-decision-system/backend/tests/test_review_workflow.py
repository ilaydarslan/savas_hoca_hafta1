import pytest

from app.models import AuthorityMembership
from app.services.decisions import cast_vote, close_vote
from conftest import auth


REVIEW = {
    'opinion': 'The proposal has been independently assessed in detail.',
    'recommendation': 'APPROVE',
}


def accept(db, users, topic):
    for user in users[:3]:
        cast_vote(db, user, 'TOPIC', topic.id, 'YES')
    close_vote(db, users[0], 'TOPIC', topic.id)
    db.commit()


def detail(client, topic, user):
    response = client.get(f'/api/v1/topics/{topic.id}', headers=auth(user))
    assert response.status_code == 200
    return response.json()


def test_accepted_review_request_resolves_and_restores_applicability(client, db, setup):
    users, topic, *_ = setup
    accept(db, users, topic)
    assert detail(client, topic, users[1])['can_apply']

    response = client.post(f'/api/v1/topics/{topic.id}/request-expert-review', headers=auth(users[1]))
    assert response.status_code == 200
    assert not detail(client, topic, users[1])['can_apply']

    response = client.post(f'/api/v1/topics/{topic.id}/expert-reviews', headers=auth(users[6]), json=REVIEW)
    assert response.status_code == 201
    result = detail(client, topic, users[1])
    assert result['status'] == 'ACCEPTED'
    assert result['decision_flag'] is None
    assert result['can_apply']
    assert result['votes']['participants'] == 3


def test_expert_review_rechecks_policy_for_accepted_high_impact_topic(client, db, setup):
    users, topic, *_ = setup
    topic.impact_level = 'HIGH'
    accept(db, users, topic)
    assert detail(client, topic, users[1])['policy_status'] == 'BLOCKED'

    response = client.post(f'/api/v1/topics/{topic.id}/expert-reviews', headers=auth(users[6]), json=REVIEW)
    assert response.status_code == 201
    result = detail(client, topic, users[1])
    assert result['policy_status'] == 'COMPLIANT'
    assert result['can_apply']


def test_closing_vote_preserves_pending_expert_request(client, db, setup):
    users, topic, *_ = setup
    assert client.post(f'/api/v1/topics/{topic.id}/request-expert-review', headers=auth(users[1])).status_code == 200
    accept(db, users, topic)
    result = detail(client, topic, users[1])
    assert result['status'] == 'ACCEPTED'
    assert result['decision_flag'] == 'EXPERT_REVIEW_REQUESTED'
    assert not result['can_apply']

    assert client.post(f'/api/v1/topics/{topic.id}/expert-reviews', headers=auth(users[6]), json=REVIEW).status_code == 201
    assert detail(client, topic, users[1])['can_apply']


def test_expert_review_does_not_override_minority_conflict(client, db, setup):
    users, topic, teams, _ = setup
    topic.affected_team_id = teams[0].id
    for user, choice in zip(users, ['NO', 'NO', 'YES', 'YES', 'YES', 'YES', 'YES']):
        cast_vote(db, user, 'TOPIC', topic.id, choice)
    close_vote(db, users[0], 'TOPIC', topic.id)
    db.commit()

    assert client.post(f'/api/v1/topics/{topic.id}/request-expert-review', headers=auth(users[1])).status_code == 200
    assert client.post(f'/api/v1/topics/{topic.id}/expert-reviews', headers=auth(users[6]), json=REVIEW).status_code == 201
    result = detail(client, topic, users[1])
    assert result['status'] == 'VOTING'
    assert result['decision_flag'] == 'MINORITY_CONFLICT'
    assert result['policy_status'] == 'BLOCKED'
    assert not result['can_apply']
    assert result['votes']['participants'] == 7


@pytest.mark.parametrize('action', ['request-expert-review', 'check-policy'])
def test_institutional_management_matches_board_authority(client, db, setup, action):
    users, topic, *_ = setup
    topic.decision_scope = 'UNIVERSITY'
    for user in users[:3]:
        user.authorities.append(AuthorityMembership(scope='UNIVERSITY'))
    db.flush()
    accept(db, users, topic)
    users[0].authorities.clear()
    users[1].authorities.clear()
    users[3].authorities.append(AuthorityMembership(scope='FACULTY'))
    db.commit()

    path = f'/api/v1/topics/{topic.id}/{action}'
    for user in (users[0], users[1], users[3]):
        assert not detail(client, topic, user)['can_manage']
        assert client.post(path, headers=auth(user)).status_code == 403
    assert detail(client, topic, users[2])['can_manage']
    assert client.post(path, headers=auth(users[2])).status_code == 200
