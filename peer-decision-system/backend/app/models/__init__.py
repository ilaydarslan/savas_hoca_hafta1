from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, UniqueConstraint, CheckConstraint, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

def now():
    return datetime.now(timezone.utc).isoformat()

class Team(Base):
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

class Tag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)

class UserInterest(Base):
    __tablename__ = 'user_interests'
    user_id = Column(ForeignKey('users.id'), primary_key=True)
    tag_id = Column(ForeignKey('tags.id'), primary_key=True)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    first_name = Column(String(80), nullable=False)
    last_name = Column(String(80), nullable=False)
    username = Column(String(80), unique=True, nullable=False)
    email = Column(String(200), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    birth_date = Column(String(10))
    address = Column(String(500), default='')
    team_id = Column(ForeignKey('teams.id'))
    role = Column(String(10), default='USER', nullable=False)
    points = Column(Integer, default=0, nullable=False)
    reputation_coefficient = Column(Float, default=1.0, nullable=False)
    team = relationship('Team')
    interests = relationship('Tag', secondary='user_interests')
    authorities = relationship('AuthorityMembership', cascade='all, delete-orphan')
    __table_args__ = (CheckConstraint("role IN ('USER','EXPERT','ADMIN')"), CheckConstraint('reputation_coefficient >= 0.8 AND reputation_coefficient <= 1.2'))

class TopicTag(Base):
    __tablename__ = 'topic_tags'
    topic_id = Column(ForeignKey('topics.id'), primary_key=True)
    tag_id = Column(ForeignKey('tags.id'), primary_key=True)

class Topic(Base):
    __tablename__ = 'topics'
    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    created_by = Column(ForeignKey('users.id'), nullable=False)
    created_at = Column(String, default=now, nullable=False)
    affected_team_id = Column(ForeignKey('teams.id'))
    impact_level = Column(String(10), default='NORMAL', nullable=False)
    status = Column(String(20), default='PROPOSED', nullable=False)
    decision_flag = Column(String(40))
    policy_status = Column(String(20), default='PENDING', nullable=False)
    decision_scope = Column(String(20), default='COMMUNITY', server_default='COMMUNITY', nullable=False)
    authority_requested = Column(Integer, default=0, server_default='0', nullable=False)
    creator = relationship('User')
    affected_team = relationship('Team')
    tags = relationship('Tag', secondary='topic_tags')
    __table_args__ = (CheckConstraint("status IN ('PROPOSED','VOTING','ACCEPTED','REJECTED','ARCHIVED')"), CheckConstraint("impact_level IN ('NORMAL','HIGH')"))

class SubTopic(Base):
    __tablename__ = 'subtopics'
    id = Column(Integer, primary_key=True)
    topic_id = Column(ForeignKey('topics.id'), nullable=False)
    created_by = Column(ForeignKey('users.id'), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), default='VOTING', nullable=False)
    created_at = Column(String, default=now)

class DiscussionMessage(Base):
    __tablename__ = 'discussion_messages'
    id = Column(Integer, primary_key=True)
    topic_id = Column(ForeignKey('topics.id'), nullable=False)
    user_id = Column(ForeignKey('users.id'), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), default='ACTIVE', nullable=False)
    created_at = Column(String, default=now)
    author = relationship('User')

class DeletionProposal(Base):
    __tablename__ = 'deletion_proposals'
    id = Column(Integer, primary_key=True)
    message_id = Column(ForeignKey('discussion_messages.id'), unique=True, nullable=False)
    proposed_by = Column(ForeignKey('users.id'), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default='VOTING', nullable=False)
    created_at = Column(String, default=now)

class Vote(Base):
    __tablename__ = 'votes'
    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('users.id'), nullable=False)
    topic_id = Column(ForeignKey('topics.id'))
    subtopic_id = Column(ForeignKey('subtopics.id'))
    deletion_proposal_id = Column(ForeignKey('deletion_proposals.id'))
    choice = Column(String(10), nullable=False)
    # Team at vote time keeps minority results stable after profile changes.
    team_id = Column(ForeignKey('teams.id'))
    created_at = Column(String, default=now)
    __table_args__ = (
        UniqueConstraint('user_id','topic_id'), UniqueConstraint('user_id','subtopic_id'), UniqueConstraint('user_id','deletion_proposal_id'),
        CheckConstraint("choice IN ('YES','NO','ABSTAIN')"),
        CheckConstraint('(CASE WHEN topic_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN subtopic_id IS NOT NULL THEN 1 ELSE 0 END + CASE WHEN deletion_proposal_id IS NOT NULL THEN 1 ELSE 0 END) = 1'),
    )

class ExpertReview(Base):
    __tablename__ = 'expert_reviews'
    id = Column(Integer, primary_key=True)
    expert_id = Column(ForeignKey('users.id'), nullable=False)
    topic_id = Column(ForeignKey('topics.id'), nullable=False)
    opinion = Column(Text, nullable=False)
    recommendation = Column(String(30), nullable=False)
    created_at = Column(String, default=now)
    expert = relationship('User')

class Rule(Base):
    __tablename__ = 'rules'
    id = Column(Integer, primary_key=True)
    code = Column(String(30), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    condition = Column(JSON, nullable=False)
    severity = Column(String(20), nullable=False)

class RuleCheck(Base):
    __tablename__ = 'rule_checks'
    id = Column(Integer, primary_key=True)
    topic_id = Column(ForeignKey('topics.id'), nullable=False)
    rule_id = Column(ForeignKey('rules.id'), nullable=False)
    status = Column(String(20), nullable=False)
    detail = Column(Text, nullable=False)
    created_at = Column(String, default=now)

class LedgerEntry(Base):
    __tablename__ = 'ledger_entries'
    id = Column(Integer, primary_key=True)
    event_type = Column(String(60), nullable=False)
    entity_type = Column(String(40), nullable=False)
    entity_id = Column(Integer, nullable=False)
    payload = Column(JSON, nullable=False)
    data_hash = Column(String(64), nullable=False)
    previous_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), unique=True, nullable=False)
    created_at = Column(String, default=now, nullable=False)

class PointEvent(Base):
    __tablename__ = 'point_events'
    id = Column(Integer, primary_key=True)
    user_id = Column(ForeignKey('users.id'), nullable=False)
    topic_id = Column(ForeignKey('topics.id'), nullable=False)
    amount = Column(Integer, nullable=False)
    reason = Column(String(50), nullable=False)
    source = Column(String(100), unique=True, nullable=False)
    created_at = Column(String, default=now, nullable=False)

class AuthorityMembership(Base):
    __tablename__ = 'authority_memberships'
    user_id = Column(ForeignKey('users.id'), primary_key=True)
    scope = Column(String(20), primary_key=True)
    __table_args__ = (CheckConstraint("scope IN ('DEPARTMENT','FACULTY','UNIVERSITY')"),)
