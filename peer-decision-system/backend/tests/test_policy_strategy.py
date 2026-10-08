from dataclasses import replace

import pytest

from app.services.ai import get_analysis_provider
from app.main import app
from app.services.policy import PolicyContext, PolicyEngine, policy_engine
from conftest import auth


BASE = PolicyContext(True, True, .6, .4, 3, 1, 80)


@pytest.mark.parametrize('kind,threshold,field,bad_value', [
    ('HIGH_SUPPORT', .6, 'yes_ratio', .59),
    ('MINORITY_SUPPORT', .4, 'affected_support', None),
    ('QUORUM', 3, 'participants', 2),
    ('EXPERT_REVIEW', 1, 'expert_reviews', 0),
    ('DESCRIPTION_LENGTH', 80, 'description_length', 79),
])
def test_policy_boundaries_and_severity(kind, threshold, field, bad_value):
    assert policy_engine.evaluate(kind, threshold, 'BLOCKED', BASE) == 'COMPLIANT'
    failed = replace(BASE, **{field: bad_value})
    assert policy_engine.evaluate(kind, threshold, 'BLOCKED', failed) == 'BLOCKED'
    assert policy_engine.evaluate(kind, threshold, 'WARNING', failed) == 'WARNING'


def test_irrelevant_rules_do_not_block():
    context = replace(BASE, high_impact=False, affected_team=False,
                      yes_ratio=0, affected_support=None, expert_reviews=0)
    for kind, threshold in [('HIGH_SUPPORT', .6), ('MINORITY_SUPPORT', .4), ('EXPERT_REVIEW', 1)]:
        assert policy_engine.evaluate(kind, threshold, 'BLOCKED', context) == 'COMPLIANT'


def test_unknown_persisted_condition_blocks():
    assert policy_engine.evaluate('UNKNOWN', 1, 'WARNING', BASE) == 'BLOCKED'


def test_engine_accepts_new_strategy_without_changing_evaluation():
    class MinimumParticipation:
        def fails(self, context, threshold):
            return context.participants < threshold

    engine = PolicyEngine({'NEW_RULE': MinimumParticipation()})
    assert engine.evaluate('NEW_RULE', 4, 'BLOCKED', BASE) == 'BLOCKED'
    assert engine.evaluate('NEW_RULE', 3, 'BLOCKED', BASE) == 'COMPLIANT'


def test_analysis_provider_can_be_replaced_at_api_boundary(client, setup):
    users, topic, *_ = setup

    class TestProvider:
        def analyze(self, topic, similar, rules):
            return {'provider': 'test-provider', 'topic_id': topic.id}

    app.dependency_overrides[get_analysis_provider] = lambda: TestProvider()
    response = client.get(f'/api/v1/topics/{topic.id}/ai-analysis', headers=auth(users[1]))
    assert response.status_code == 200
    assert response.json() == {'provider': 'test-provider', 'topic_id': topic.id}
