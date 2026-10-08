from app.core.transactions import commit, write_lock
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db
from app.core.security import current_user, admin, hasher, token
from app.models import (
    AuthorityMembership, DeletionProposal, DiscussionMessage, ExpertReview, LedgerEntry, PointEvent, Rule, RuleCheck, SubTopic, Tag, Team, Topic, User, Vote
)
from app.schemas import (
    AuthorityInput, Login, MessageInput, ProfileInput, ReasonInput, Register, ReviewInput, RoleInput, RuleInput, SubInput, TopicInput, VoteInput
)
from app.services.decisions import QUORUM, TARGETS, summary, eligible, target, cast_vote, close_vote, check_policy
from app.services.records import require
from app.services.ledger import append_ledger, verify_ledger
from app.services.points import award
from app.services.ai import AnalysisProvider, get_analysis_provider
from app.services.authority import SCOPES, authority_info, require_authority, can_manage

router = APIRouter(prefix='/api/v1')

def row(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
def public_user(user):
    return {**{k: v for k,v in row(user).items() if k != 'password_hash'}, 'team': user.team.name if user.team else None, 'tags': [row(t) for t in user.interests], 'authority_scopes': [m.scope for m in user.authorities]}
def validate_refs(db, team_id, tag_ids):
    if team_id is not None:
        require(db, Team, team_id)
    return [require(db, Tag, id) for id in sorted(set(tag_ids))]
def topic_json(db, topic, user):
    s = summary(db, topic)
    own_vote = db.scalar(select(Vote).where(Vote.user_id == user.id, Vote.topic_id == topic.id))
    return {**row(topic), 'creator': topic.creator.username, 'affected_team': topic.affected_team.name if topic.affected_team else None,
            'tags': [row(t) for t in topic.tags], 'votes': s, 'can_vote': eligible(user, topic) and topic.status == 'VOTING' and own_vote is None,
            'my_vote': own_vote.choice if own_vote else None,
            'can_manage': can_manage(user, topic), 'authority': authority_info(user, topic),
            'can_review': user.role == 'EXPERT' and bool({t.id for t in user.interests} & {t.id for t in topic.tags}),
            'can_apply': topic.status == 'ACCEPTED' and topic.policy_status in ('COMPLIANT','WARNING') and not topic.decision_flag}

@router.get('/metadata')
def metadata(db: Session = Depends(get_db)):
    return {'teams': [row(t) for t in db.scalars(select(Team))], 'tags': [row(t) for t in db.scalars(select(Tag))], 'quorum': QUORUM, 'decision_scopes': [{'id': key, **value} for key,value in SCOPES.items()]}

@router.post('/auth/register', status_code=201)
def register(data: Register, db: Session = Depends(get_db)):
    with write_lock:
        tags = validate_refs(db, data.team_id, data.tag_ids)
        if db.scalar(select(User).where((User.email == str(data.email).lower()) | (User.username == data.username))):
            raise HTTPException(409, 'E-posta veya kullanıcı adı zaten kullanılıyor.')
        user = User(**data.model_dump(exclude={'password','tag_ids','birth_date','email'}), email=str(data.email).lower(),
                    birth_date=str(data.birth_date) if data.birth_date else None, password_hash=hasher.hash(data.password), interests=tags)
        db.add(user)
        db.flush()
        append_ledger(db, 'USER_REGISTERED', 'USER', user.id, {'username': user.username})
        commit(db)
        return {'access_token': token(user), 'token_type': 'bearer', 'user': public_user(user)}

@router.post('/auth/login')
def login(data: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if not user or not hasher.verify(data.password, user.password_hash):
        raise HTTPException(401, 'E-posta veya şifre hatalı.')
    return {'access_token': token(user), 'token_type': 'bearer', 'user': public_user(user)}

@router.get('/auth/me')
def me(user=Depends(current_user)):
    return public_user(user)

@router.put('/users/me')
def profile(data: ProfileInput, user=Depends(current_user), db: Session = Depends(get_db)):
    with write_lock:
        user.interests = validate_refs(db, data.team_id, data.tag_ids)
        for key, value in data.model_dump(exclude={'tag_ids','birth_date'}).items():
            setattr(user, key, value)
        user.birth_date = str(data.birth_date) if data.birth_date else None
        append_ledger(db, 'PROFILE_UPDATED', 'USER', user.id, {'team_id': user.team_id, 'tag_ids': data.tag_ids})
        commit(db)
        return public_user(user)

@router.get('/topics')
def topics(user=Depends(current_user), db: Session = Depends(get_db)):
    return [topic_json(db, t, user) for t in db.scalars(select(Topic).order_by(Topic.id.desc()))]

@router.post('/topics', status_code=201)
def create_topic(data: TopicInput, user=Depends(current_user), db: Session = Depends(get_db)):
    with write_lock:
        tags = validate_refs(db, data.affected_team_id, data.tag_ids)
        topic = Topic(**data.model_dump(exclude={'tag_ids'}), created_by=user.id, tags=tags)
        db.add(topic)
        db.flush()
        award(db, user.id, topic.id, 1, 'TOPIC_CREATED', f'topic-created:{topic.id}')
        append_ledger(db, 'TOPIC_CREATED', 'TOPIC', topic.id, {'title': topic.title, 'created_by': user.id})
        commit(db)
        return topic_json(db, topic, user)

@router.get('/topics/{id}')
def topic_detail(id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    return topic_json(db, require(db, Topic, id), user)

@router.post('/topics/{id}/start-voting')
def start_voting(id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    with write_lock:
        topic = require(db, Topic, id)
        require_authority(user, topic)
        if not can_manage(user, topic):
            raise HTTPException(403, 'Bu konuyu yönetme yetkiniz yok. Toplulukta konu sahibi/yönetici, kurumsal kararlarda ilgili kurul üyesi olmalısınız.')
        if topic.status != 'PROPOSED':
            raise HTTPException(409, 'Yalnızca öneri durumundaki konular oylamaya açılır.')
        topic.status = 'VOTING'
        append_ledger(db, 'TOPIC_VOTING_STARTED', 'TOPIC', id, {'actor': user.id})
        commit(db)
        return topic_json(db, topic, user)

@router.post('/topics/{id}/close-voting')
def close_topic(id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    with write_lock:
        result = close_vote(db, user, 'TOPIC', id)
        commit(db)
        return result

@router.post('/votes', status_code=201)
def vote(data: VoteInput, user=Depends(current_user), db: Session = Depends(get_db)):
    with write_lock:
        try:
            result = cast_vote(db, user, data.target_type, data.target_id, data.choice)
            commit(db)
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'Bu hedef için zaten oy kullandınız.')
        return row(result)

@router.get('/topics/{id}/votes/summary')
def vote_summary(id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    return summary(db, require(db, Topic, id))

@router.get('/votes/pending')
def pending(user=Depends(current_user), db: Session = Depends(get_db)):
    result = []
    for kind, (model, field) in TARGETS.items():
        for obj in db.scalars(select(model).where(model.status == 'VOTING')):
            _, topic, _ = target(db, kind, obj.id)
            if eligible(user, topic) and not db.scalar(select(Vote).where(Vote.user_id == user.id, getattr(Vote, field) == obj.id)):
                result.append({'target_type': kind, 'target_id': obj.id, 'topic_id': topic.id, 'title': getattr(obj, 'title', f'Mesaj arşivleme · {topic.title}'), 'votes': summary(db, topic, kind, obj.id)})
    return result

@router.get('/topics/{id}/messages')
def messages(id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    require(db, Topic, id)
    return [{**row(m), 'author': m.author.username} for m in db.scalars(select(DiscussionMessage).where(DiscussionMessage.topic_id == id).order_by(DiscussionMessage.id))]

@router.post('/topics/{id}/messages', status_code=201)
def post_message(id: int, data: MessageInput, user=Depends(current_user), db: Session = Depends(get_db)):
    with write_lock:
        require(db, Topic, id)
        message = DiscussionMessage(topic_id=id, user_id=user.id, message=data.message)
        db.add(message)
        db.flush()
        append_ledger(db, 'COMMENT_CREATED', 'MESSAGE', message.id, {'topic_id': id, 'user_id': user.id, 'message': data.message})
        commit(db)
        return row(message)

@router.post('/messages/{id}/endorse')
def endorse(id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    with write_lock:
        message = require(db, DiscussionMessage, id)
        topic = require(db, Topic, message.topic_id)
        if message.status != 'ACTIVE' or user.id == message.user_id:
            raise HTTPException(409, 'Kendi katkınızı veya arşivlenmiş katkıyı doğrulayamazsınız.')
        if user.role == 'EXPERT' and {t.id for t in user.interests} & {t.id for t in topic.tags}:
            reason = 'EXPERT_USEFUL'
        elif user.role == 'ADMIN':
            reason = 'QUALITY_CONTRIBUTION'
        else:
            raise HTTPException(403, 'İlgili uzman veya yönetici olmalısınız.')
        award(db, message.user_id, topic.id, 2, reason, f'{reason}:{message.user_id}:{topic.id}')
        append_ledger(db, 'CONTRIBUTION_ENDORSED', 'MESSAGE', id, {'actor': user.id, 'reason': reason})
        commit(db)
        return {'message': 'Katkı doğrulandı; puan limitleri uygulandı.'}

@router.post('/messages/{id}/deletion-proposals', status_code=201)
def propose_deletion(id: int, data: ReasonInput, user=Depends(current_user), db: Session = Depends(get_db)):
    with write_lock:
        message = require(db, DiscussionMessage, id)
        if message.status != 'ACTIVE':
            raise HTTPException(409, 'Mesaj zaten arşivlenmiş.')
        if db.scalar(select(DeletionProposal).where(DeletionProposal.message_id == id)):
            raise HTTPException(409, 'Bu mesaj için zaten bir teklif var.')
        proposal = DeletionProposal(message_id=id, proposed_by=user.id, reason=data.reason)
        db.add(proposal)
        db.flush()
        append_ledger(db, 'DELETION_PROPOSED', 'DELETION', proposal.id, {'message_id': id, 'reason': data.reason})
        commit(db)
        return row(proposal)

@router.get('/topics/{id}/deletion-proposals')
def deletion_list(id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    topic = require(db, Topic, id)
    proposals = db.scalars(select(DeletionProposal).join(DiscussionMessage).where(DiscussionMessage.topic_id == id)).all()
    return [child_json(db, p, topic, user, 'DELETION') for p in proposals]

def child_json(db, obj, topic, user, kind):
    field = TARGETS[kind][1]
    own = db.scalar(select(Vote).where(Vote.user_id == user.id, getattr(Vote, field) == obj.id))
    return {**row(obj), 'votes': summary(db, topic, kind, obj.id), 'my_vote': own.choice if own else None,
            'can_vote': eligible(user, topic) and obj.status == 'VOTING' and own is None,
            'can_manage': can_manage(user, topic, obj.created_by if kind == 'SUBTOPIC' else obj.proposed_by)}

@router.get('/topics/{id}/subtopics')
def subtopics(id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    topic = require(db, Topic, id)
    return [child_json(db, s, topic, user, 'SUBTOPIC') for s in db.scalars(select(SubTopic).where(SubTopic.topic_id == id))]

@router.post('/topics/{id}/subtopics', status_code=201)
def create_subtopic(id: int, data: SubInput, user=Depends(current_user), db: Session = Depends(get_db)):
    with write_lock:
        topic = require(db, Topic, id)
        if topic.status != 'ACCEPTED':
            raise HTTPException(409, 'Alt konu yalnızca kabul edilen konularda açılabilir.')
        obj = SubTopic(topic_id=id, created_by=user.id, **data.model_dump())
        db.add(obj)
        db.flush()
        append_ledger(db, 'SUBTOPIC_CREATED', 'SUBTOPIC', obj.id, {'topic_id': id, 'title': obj.title})
        commit(db)
        return row(obj)

@router.post('/subtopics/{id}/close-voting')
def close_subtopic(id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    with write_lock:
        result = close_vote(db, user, 'SUBTOPIC', id)
        commit(db)
        return result

@router.post('/deletion-proposals/{id}/close-voting')
def close_deletion(id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    with write_lock:
        result = close_vote(db, user, 'DELETION', id)
        commit(db)
        return result

@router.get('/topics/{id}/expert-reviews')
def reviews(id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    require(db, Topic, id)
    return [{**row(r), 'expert': r.expert.username} for r in db.scalars(select(ExpertReview).where(ExpertReview.topic_id == id))]

@router.post('/topics/{id}/expert-reviews', status_code=201)
def add_review(id: int, data: ReviewInput, user=Depends(current_user), db: Session = Depends(get_db)):
    with write_lock:
        topic = require(db, Topic, id)
        if user.role != 'EXPERT' or not {t.id for t in user.interests} & {t.id for t in topic.tags}:
            raise HTTPException(403, 'Bu konuda uzmanlık alanı eşleşen EXPERT rolü gerekiyor.')
        review = ExpertReview(topic_id=id, expert_id=user.id, **data.model_dump())
        db.add(review)
        db.flush()
        if topic.decision_flag == 'EXPERT_REVIEW_REQUESTED':
            topic.decision_flag = None
        if topic.status == 'ACCEPTED':
            check_policy(db, topic)
        append_ledger(db, 'EXPERT_REVIEWED', 'TOPIC', id, {'expert_id': user.id, **data.model_dump()})
        commit(db)
        return row(review)

@router.get('/topics/{id}/policy-checks')
def policy_checks(id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    require(db, Topic, id)
    return [row(r) for r in db.scalars(select(RuleCheck).where(RuleCheck.topic_id == id).order_by(RuleCheck.id.desc()))]

@router.post('/topics/{id}/check-policy')
def rerun_policy(id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    with write_lock:
        topic = require(db, Topic, id)
        if not can_manage(user, topic):
            raise HTTPException(403, 'Bu konuyu yönetme yetkiniz yok. Toplulukta konu sahibi/yönetici, kurumsal kararlarda ilgili kurul üyesi olmalısınız.')
        if topic.status != 'ACCEPTED':
            raise HTTPException(409, 'Konu önce kabul edilmiş olmalı.')
        check_policy(db, topic)
        commit(db)
        return {'policy_status': topic.policy_status}

@router.post('/topics/{id}/request-expert-review')
def request_review(id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    with write_lock:
        topic = require(db, Topic, id)
        if not can_manage(user, topic):
            raise HTTPException(403, 'Bu konuyu yönetme yetkiniz yok. Toplulukta konu sahibi/yönetici, kurumsal kararlarda ilgili kurul üyesi olmalısınız.')
        if topic.decision_flag != 'MINORITY_CONFLICT':
            topic.decision_flag = 'EXPERT_REVIEW_REQUESTED'
        append_ledger(db, 'EXPERT_REVIEW_REQUESTED', 'TOPIC', id, {'actor': user.id})
        commit(db)
        return {'message': 'Bilirkişi görüşü istendi. Görüş kararı tek başına değiştirmez.'}

@router.get('/topics/{id}/ai-analysis')
def ai_analysis(id: int, user=Depends(current_user), db: Session = Depends(get_db), provider: AnalysisProvider = Depends(get_analysis_provider)):
    topic = require(db, Topic, id)
    similar = [t for t in db.scalars(select(Topic).where(Topic.id != id)) if {a.id for a in t.tags} & {a.id for a in topic.tags}][:4]
    return provider.analyze(topic, similar, db.scalars(select(Rule)).all())

@router.get('/rules')
def rules(user=Depends(current_user), db: Session = Depends(get_db)):
    return [row(r) for r in db.scalars(select(Rule).order_by(Rule.code))]

@router.post('/admin/rules', status_code=201)
def create_rule(data: RuleInput, user=Depends(admin), db: Session = Depends(get_db)):
    with write_lock:
        rule = Rule(**data.model_dump())
        db.add(rule)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, 'Kural kodu zaten var.')
        append_ledger(db, 'RULE_CREATED', 'RULE', rule.id, data.model_dump())
        for topic in db.scalars(select(Topic).where(Topic.status == 'ACCEPTED')).all():
            check_policy(db, topic)
        commit(db)
        return row(rule)

@router.put('/admin/rules/{id}')
def update_rule(id: int, data: RuleInput, user=Depends(admin), db: Session = Depends(get_db)):
    with write_lock:
        rule = require(db, Rule, id)
        duplicate = db.scalar(select(Rule).where(Rule.code == data.code, Rule.id != id))
        if duplicate:
            raise HTTPException(409, 'Kural kodu zaten var.')
        for key, value in data.model_dump().items():
            setattr(rule, key, value)
        append_ledger(db, 'RULE_UPDATED', 'RULE', id, data.model_dump())
        for topic in db.scalars(select(Topic).where(Topic.status == 'ACCEPTED')).all():
            check_policy(db, topic)
        commit(db)
        return row(rule)

@router.get('/admin/users')
def users(user=Depends(admin), db: Session = Depends(get_db)):
    return [public_user(u) for u in db.scalars(select(User))]

@router.put('/admin/users/{id}/authorities')
def set_authorities(id: int, data: AuthorityInput, user=Depends(admin), db: Session = Depends(get_db)):
    with write_lock:
        other = require(db, User, id)
        scopes = set(data.scopes)
        old = {m.scope for m in other.authorities}
        for membership in list(other.authorities):
            if membership.scope not in scopes:
                other.authorities.remove(membership)
        for scope in scopes - old:
            other.authorities.append(AuthorityMembership(scope=scope))
        append_ledger(db, 'AUTHORITY_MEMBERSHIP_CHANGED', 'USER', id, {'actor': user.id, 'old': sorted(old), 'scopes': sorted(scopes)})
        commit(db)
        return public_user(other)

@router.post('/topics/{id}/refer-to-authority')
def refer_to_authority(id: int, user=Depends(current_user), db: Session = Depends(get_db)):
    with write_lock:
        topic = require(db, Topic, id)
        if topic.decision_scope == 'COMMUNITY' or topic.status != 'PROPOSED':
            raise HTTPException(409, 'Yalnızca kurul yetkisi gerektiren öneriler yönlendirilebilir.')
        if topic.created_by != user.id and user.role != 'ADMIN':
            raise HTTPException(403, 'Yalnızca öneri sahibi veya yönetici yönlendirebilir.')
        if not topic.authority_requested:
            topic.authority_requested = 1
            append_ledger(db, 'AUTHORITY_REVIEW_REQUESTED', 'TOPIC', id, {'actor': user.id, 'scope': topic.decision_scope})
        commit(db)
        return {'message': 'Öneri uygulama içindeki yetkili kurul gündemine alındı. Gerçek üniversiteye bildirim gönderilmedi.'}

@router.patch('/admin/users/{id}')
def update_role(id: int, data: RoleInput, user=Depends(admin), db: Session = Depends(get_db)):
    with write_lock:
        other = require(db, User, id)
        if other.role == 'ADMIN' and data.role != 'ADMIN' and db.scalar(select(func.count()).select_from(User).where(User.role == 'ADMIN')) <= 1:
            raise HTTPException(409, 'Son yönetici hesabının rolü değiştirilemez.')
        other.role = data.role
        append_ledger(db, 'USER_ROLE_CHANGED', 'USER', id, {'actor': user.id, 'role': data.role})
        commit(db)
        return public_user(other)

@router.get('/ledger/verify')
def verify(user=Depends(current_user), db: Session = Depends(get_db)):
    return verify_ledger(db)

@router.get('/ledger')
def ledger(user=Depends(current_user), db: Session = Depends(get_db)):
    return [row(e) for e in db.scalars(select(LedgerEntry).order_by(LedgerEntry.id.desc()).limit(300))]

@router.get('/users/me/dashboard')
def dashboard(user=Depends(current_user), db: Session = Depends(get_db)):
    return {'user': public_user(user),
            'created_topics': db.scalar(select(func.count()).select_from(Topic).where(Topic.created_by == user.id)),
            'accepted_topics': db.scalar(select(func.count()).select_from(Topic).where(Topic.created_by == user.id, Topic.status == 'ACCEPTED')),
            'votes_cast': db.scalar(select(func.count()).select_from(Vote).where(Vote.user_id == user.id)),
            'discussion_contributions': db.scalar(select(func.count()).select_from(DiscussionMessage).where(DiscussionMessage.user_id == user.id)),
            'expert_reviews': db.scalar(select(func.count()).select_from(ExpertReview).where(ExpertReview.expert_id == user.id)),
            'pending_votes': pending(user, db), 'ledger': verify_ledger(db),
            'activities': [row(e) for e in db.scalars(select(PointEvent).where(PointEvent.user_id == user.id).order_by(PointEvent.id.desc()).limit(20))],
            'my_votes': [row(v) for v in db.scalars(select(Vote).where(Vote.user_id == user.id).order_by(Vote.id.desc()).limit(20))]}

@router.get('/graph')
def graph(user=Depends(current_user), db: Session = Depends(get_db)):
    nodes, edges = [], []
    def edge(source, target, kind):
        edges.append({'id': f'{kind}:{source}:{target}', 'source': source, 'target': target, 'label': kind})
    teams = db.scalars(select(Team)).all()
    users = db.scalars(select(User)).all()
    topics = db.scalars(select(Topic)).all()
    for index, team in enumerate(teams):
        nodes.append({'id': f'team-{team.id}', 'type': 'TEAM', 'label': team.name, 'x': 0, 'y': index*180})
    for index, u in enumerate(users):
        uid = f'user-{u.id}'
        nodes.append({'id': uid, 'type': 'USER', 'label': u.username, 'x': 350, 'y': index*90})
        if u.team_id:
            edge(uid, f'team-{u.team_id}', 'MEMBER_OF')
        for t in topics:
            if {a.id for a in u.interests} & {a.id for a in t.tags}:
                edge(uid, f'topic-{t.id}', 'INTERESTED_IN')
    for index, t in enumerate(topics):
        nodes.append({'id': f'topic-{t.id}', 'type': 'TOPIC', 'label': t.title, 'x': 760, 'y': index*150})
        edge(f'user-{t.created_by}', f'topic-{t.id}', 'CREATED')
    for vote in db.scalars(select(Vote)):
        kind = 'TOPIC' if vote.topic_id else 'SUBTOPIC' if vote.subtopic_id else 'DELETION'
        _, topic, _ = target(db, kind, vote.topic_id or vote.subtopic_id or vote.deletion_proposal_id)
        edge(f'user-{vote.user_id}', f'topic-{topic.id}', 'VOTED_ON')
    for m in db.scalars(select(DiscussionMessage)):
        edge(f'user-{m.user_id}', f'topic-{m.topic_id}', 'COMMENTED_ON')
    return {'nodes': nodes, 'edges': list({e['id']: e for e in edges}.values())}
