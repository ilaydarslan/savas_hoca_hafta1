import hashlib
import json
from sqlalchemy import select, func
from fastapi import HTTPException
from app.models import *
from app.services.authority import authorized, scope_of, require_authority, can_manage

QUORUM = 3
DAILY_POINT_LIMIT = 10
TOPIC_POINT_LIMIT = 8
TARGETS = {'TOPIC': (Topic, 'topic_id'), 'SUBTOPIC': (SubTopic, 'subtopic_id'), 'DELETION': (DeletionProposal, 'deletion_proposal_id')}
def require(db, model, id):
    obj = db.get(model, id)
    if obj is None:
        raise HTTPException(404, 'Kayıt bulunamadı.')
    return obj
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
def award(db, user_id, topic_id, amount, reason, source):
    if db.scalar(select(PointEvent).where(PointEvent.source == source)):
        return
    daily = db.scalar(select(func.coalesce(func.sum(PointEvent.amount), 0)).where(PointEvent.user_id == user_id, PointEvent.created_at >= now()[:10]))
    topic_points = db.scalar(select(func.coalesce(func.sum(PointEvent.amount), 0)).where(PointEvent.user_id == user_id, PointEvent.topic_id == topic_id))
    amount = min(amount, DAILY_POINT_LIMIT-daily, TOPIC_POINT_LIMIT-topic_points)
    if amount <= 0:
        return
    db.add(PointEvent(user_id=user_id, topic_id=topic_id, amount=amount, reason=reason, source=source))
    user = require(db, User, user_id)
    user.points += amount
    user.reputation_coefficient = round(min(1.2, max(.8, 1 + user.points / 100)), 2)
    db.flush()
def eligible(user, topic):
    if scope_of(topic) != 'COMMUNITY':
        return authorized(user, topic)
    return bool((topic.affected_team_id is not None and user.team_id == topic.affected_team_id) or {t.id for t in user.interests} & {t.id for t in topic.tags})
def target(db, kind, id):
    model, field = TARGETS[kind]
    obj = require(db, model, id)
    topic = obj if kind == 'TOPIC' else require(db, Topic, obj.topic_id if kind == 'SUBTOPIC' else require(db, DiscussionMessage, obj.message_id).topic_id)
    return obj, topic, field
def summary(db, topic, kind='TOPIC', id=None):
    field = TARGETS[kind][1]
    votes = db.scalars(select(Vote).where(getattr(Vote, field) == (id or topic.id))).all()
    yes = sum(v.choice == 'YES' for v in votes)
    no = sum(v.choice == 'NO' for v in votes)
    group = [v for v in votes if topic.affected_team_id is not None and v.team_id == topic.affected_team_id]
    gy = sum(v.choice == 'YES' for v in group)
    gn = sum(v.choice == 'NO' for v in group)
    ratio = yes/(yes+no) if yes+no else 0
    gr = gy/(gy+gn) if gy+gn else None
    majority = ratio >= .6 if topic.impact_level == 'HIGH' else ratio > .5
    return {'yes': yes, 'no': no, 'abstain': len(votes)-yes-no, 'participants': len(votes), 'yes_ratio': ratio,
            'quorum': QUORUM, 'quorum_met': len(votes) >= QUORUM, 'majority_met': majority,
            'affected_support': gr, 'affected_participants': len(group),
            'minority_conflict': topic.affected_team_id is not None and (gr is None or gr < .4)}
def cast_vote(db, user, kind, id, choice):
    obj, topic, field = target(db, kind, id)
    require_authority(user, topic)
    if obj.status != 'VOTING':
        raise HTTPException(409, 'Bu oylama açık değil.')
    if not eligible(user, topic):
        raise HTTPException(403, 'İlgi alanınız veya takımınız bu konuyla ilişkili değil.')
    if db.scalar(select(Vote).where(Vote.user_id == user.id, getattr(Vote, field) == id)):
        raise HTTPException(409, 'Bu hedef için zaten oy kullandınız.')
    vote = Vote(user_id=user.id, choice=choice, team_id=user.team_id, **{field: id})
    db.add(vote)
    db.flush()
    append_ledger(db, 'VOTE_CAST', kind, id, {'user_id': user.id, 'choice': choice, 'team_id': user.team_id})
    return vote
def check_policy(db, topic):
    s = summary(db, topic)
    statuses = []
    for rule in db.scalars(select(Rule).order_by(Rule.id)):
        kind, value = rule.condition['kind'], rule.condition['value']
        failed = {
            'HIGH_SUPPORT': topic.impact_level == 'HIGH' and s['yes_ratio'] < value,
            'MINORITY_SUPPORT': topic.affected_team_id is not None and (s['affected_support'] is None or s['affected_support'] < value),
            'QUORUM': s['participants'] < value,
            'EXPERT_REVIEW': topic.impact_level == 'HIGH' and len(db.scalars(select(ExpertReview).where(ExpertReview.topic_id == topic.id)).all()) < value,
            'DESCRIPTION_LENGTH': len(topic.description) < value,
        }[kind]
        status = rule.severity if failed else 'COMPLIANT'
        statuses.append(status)
        db.add(RuleCheck(topic_id=topic.id, rule_id=rule.id, status=status, detail=f'{rule.code}: {rule.name} — {rule.description}'))
    topic.policy_status = 'BLOCKED' if 'BLOCKED' in statuses else 'WARNING' if 'WARNING' in statuses else 'COMPLIANT'
    # Invariant protections cannot be disabled by editing a policy rule.
    if not s['quorum_met'] or not s['majority_met'] or s['minority_conflict']:
        topic.policy_status = 'BLOCKED'
    append_ledger(db, 'RULE_CHECKED', 'TOPIC', topic.id, {'status': topic.policy_status})
    return topic.policy_status
def close_vote(db, user, kind, id):
    obj, topic, _ = target(db, kind, id)
    require_authority(user, topic)
    owner = topic.created_by if kind == 'TOPIC' else obj.created_by if kind == 'SUBTOPIC' else obj.proposed_by
    if not can_manage(user, topic, owner):
        raise HTTPException(403, 'Yalnızca teklif sahibi veya yönetici kapatabilir.')
    if obj.status != 'VOTING':
        raise HTTPException(409, 'Oylama açık değil.')
    s = summary(db, topic, kind, id)
    if not s['quorum_met']:
        raise HTTPException(409, f'En az {QUORUM} katılımcı gerekir. Oylama açık kaldı.')
    if s['majority_met'] and s['minority_conflict']:
        if kind == 'TOPIC':
            topic.decision_flag = 'MINORITY_CONFLICT'
            topic.policy_status = 'BLOCKED'
        append_ledger(db, 'MINORITY_CONFLICT', kind, id, s)
        return {'status': 'VOTING', 'decision_flag': 'MINORITY_CONFLICT', 'message': 'Etkilenen grubun desteği yetersiz olduğu için karar yeniden değerlendirmeye gönderildi.'}
    obj.status = 'ACCEPTED' if s['majority_met'] else 'REJECTED'
    if kind == 'TOPIC':
        topic.decision_flag = None
        if obj.status == 'ACCEPTED':
            check_policy(db, topic)
            award(db, topic.created_by, topic.id, 3, 'TOPIC_ACCEPTED', f'topic-accepted:{topic.id}')
    if kind == 'SUBTOPIC' and obj.status == 'ACCEPTED':
        award(db, obj.created_by, topic.id, 2, 'SUBTOPIC_ACCEPTED', f'subtopic:{obj.id}')
    if kind == 'DELETION' and obj.status == 'ACCEPTED':
        message = require(db, DiscussionMessage, obj.message_id)
        message.status = 'ARCHIVED'
        append_ledger(db, 'COMMENT_ARCHIVED', 'MESSAGE', message.id, {'proposal_id': id})
    append_ledger(db, f'{kind}_{obj.status}', kind, id, s)
    return {'status': obj.status, 'policy_status': topic.policy_status}
