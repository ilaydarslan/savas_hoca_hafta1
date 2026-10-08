"""Contribution rewards and daily/topic limits."""
from sqlalchemy import select, func
from app.models import PointEvent, User, now
from app.services.records import require

DAILY_POINT_LIMIT = 10
TOPIC_POINT_LIMIT = 8

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
