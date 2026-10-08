import hashlib
import pytest
from sqlalchemy import select
from app.models import Topic
from app.services.scope_analysis import KeywordScopeStrategy, normalize
from app.services.evaluation import DATA_PATH, classification_metrics, evaluate
from conftest import auth


def test_turkish_normalization_and_suffixes():
    assert normalize('IŞIK İLETİŞİM') == 'ışık iletişim'
    strategy = KeywordScopeStrategy()
    assert strategy.predict('BÖLÜMÜMÜZDE yeni ders') == 'DEPARTMENT'
    assert strategy.predict('ÜNİVERSİTE GENELİNDE ULAŞIM') == 'UNIVERSITY'


@pytest.mark.parametrize('text', ['Yeni etkinlik öneriyorum', 'Bölüm ve fakülte ortak etkinliği', 'mikrokampüs kelimesi'])
def test_ambiguous_or_unknown_text_abstains(text):
    result = KeywordScopeStrategy().suggest(text)
    assert result['suggested_scope'] is None
    assert result['needs_review'] is True


def test_metrics_count_abstentions_as_misses():
    result = classification_metrics(
        ['COMMUNITY', 'DEPARTMENT', 'FACULTY', 'UNIVERSITY'],
        ['COMMUNITY', 'COMMUNITY', None, 'UNIVERSITY'])
    assert result['accuracy'] == .5
    assert result['coverage'] == .75
    assert result['macro_f1'] == pytest.approx((2/3 + 0 + 0 + 1)/4)
    assert result['confusion_matrix'][2][4] == 1
    assert len(result['per_class']) == 4
    assert sum(map(sum, result['confusion_matrix'])) == 4


def test_evaluation_is_reproducible_except_measured_latency():
    first, second = evaluate(), evaluate()
    assert first['dataset']['sha256'] == hashlib.sha256(DATA_PATH.read_bytes()).hexdigest()
    assert first['dataset']['size'] == 32
    assert first['labels'][-1] == 'REVIEW'
    assert first['methods'][0]['accuracy'] == .25
    assert first['methods'][0]['coverage'] == 1
    for left, right in zip(first['methods'], second['methods']):
        assert left.pop('latency_p95_ms') >= 0
        right.pop('latency_p95_ms')
        assert left == right
        assert left['errors']


def test_engineering_requires_login(client):
    assert client.get('/api/v1/engineering/evaluation').status_code == 401
    assert client.post('/api/v1/engineering/scope-suggestion', json={'text': 'Bölüm önerisi'}).status_code == 401


def test_suggestion_is_advisory_and_does_not_modify_topic(client, setup, db):
    users, topic, _, _ = setup
    before = {column.name: getattr(topic, column.name) for column in Topic.__table__.columns}
    response = client.post('/api/v1/engineering/scope-suggestion', headers=auth(users[1]), json={'text': 'ÜNİVERSİTE genelinde değişiklik'})
    assert response.status_code == 200
    assert response.json()['suggested_scope'] == 'UNIVERSITY'
    assert response.json()['needs_review'] is True
    db.expire_all()
    after = db.get(Topic, topic.id)
    assert {column.name: getattr(after, column.name) for column in Topic.__table__.columns} == before
    assert len(db.scalars(select(Topic)).all()) == 1
    assert client.post('/api/v1/engineering/scope-suggestion', headers=auth(users[1]), json={'text': 'ab'}).status_code == 422
    assert client.post('/api/v1/engineering/scope-suggestion', headers=auth(users[1]), json={'text': 'a' * 10001}).status_code == 422
    assert client.get('/api/v1/engineering/evaluation', headers=auth(users[1])).status_code == 200
