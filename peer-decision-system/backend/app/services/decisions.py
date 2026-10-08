from sqlalchemy import select, func
from fastapi import HTTPException
from app.models import Topic, SubTopic, DeletionProposal, DiscussionMessage, Vote, Rule, RuleCheck, ExpertReview
from app.services.authority import authorized, scope_of, require_authority, can_manage
from app.services.records import require
from app.services.ledger import append_ledger, verify_ledger
from app.services.points import award, DAILY_POINT_LIMIT, TOPIC_POINT_LIMIT
from app.services.policy import PolicyContext, policy_engine

QUORUM = 3
TARGETS = {'TOPIC': (Topic, 'topic_id'), 'SUBTOPIC': (SubTopic, 'subtopic_id'), 'DELETION': (DeletionProposal, 'deletion_proposal_id')}

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
    context = PolicyContext(
        high_impact=topic.impact_level == 'HIGH',
        affected_team=topic.affected_team_id is not None,
        yes_ratio=s['yes_ratio'], affected_support=s['affected_support'],
        participants=s['participants'],
        expert_reviews=db.scalar(select(func.count()).select_from(ExpertReview).where(ExpertReview.topic_id == topic.id)),
        description_length=len(topic.description),
    )
    statuses = []
    for rule in db.scalars(select(Rule).order_by(Rule.id)):
        status = policy_engine.evaluate(rule.condition['kind'], rule.condition['value'], rule.severity, context)
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
        if topic.decision_flag == 'MINORITY_CONFLICT':
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
