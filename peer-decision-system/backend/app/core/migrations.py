from sqlalchemy import inspect, text

def migrate_authority(engine):
    """Additive migration: existing topics keep their community-vote semantics."""
    columns = {c['name'] for c in inspect(engine).get_columns('topics')}
    with engine.begin() as connection:
        if 'decision_scope' not in columns:
            connection.execute(text("ALTER TABLE topics ADD COLUMN decision_scope VARCHAR(20) NOT NULL DEFAULT 'COMMUNITY'"))
        if 'authority_requested' not in columns:
            connection.execute(text('ALTER TABLE topics ADD COLUMN authority_requested INTEGER NOT NULL DEFAULT 0'))
