import os
os.environ['JWT_SECRET'] = 'test-only-secret-32-characters-not-for-production'
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.core.database import Base, get_db
from app.core.security import hasher, token
from app.main import app
from app.models import Team, Tag, User, Topic, Rule

@pytest.fixture
def db():
    engine = create_engine('sqlite://', connect_args={'check_same_thread':False}, poolclass=StaticPool)
    @event.listens_for(engine,'connect')
    def foreign_keys(connection,_):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine,expire_on_commit=False)() as session:
        yield session
    engine.dispose()

@pytest.fixture
def setup(db):
    teams=[Team(name='A'),Team(name='B')];tags=[Tag(name='Education'),Tag(name='Database')]
    db.add_all(teams+tags);db.flush()
    hashed=hasher.hash('Demo12345!')
    users=[]
    for i in range(8):
        u=User(first_name='Test',last_name=str(i),username=f'user{i}',email=f'test{i}@example.com',password_hash=hashed,
               team_id=teams[0 if i<3 else 1].id,interests=[tags[1] if i==7 else tags[0]],role='ADMIN' if i==0 else 'EXPERT' if i==6 else 'USER')
        db.add(u);users.append(u)
    db.flush()
    topic=Topic(title='Test topic',description='An adequately detailed proposal for students to discuss and decide on together in this demonstration.',category='Education',created_by=users[1].id,tags=[tags[0]],status='VOTING')
    db.add(topic)
    for i,(kind,value) in enumerate([('HIGH_SUPPORT',.6),('MINORITY_SUPPORT',.4),('QUORUM',3),('EXPERT_REVIEW',1),('DESCRIPTION_LENGTH',80)]):
        db.add(Rule(code=f'RULE-{i+1:03}',name=kind,description=kind,category='Test',condition={'kind':kind,'value':value},severity='BLOCKED' if i<4 else 'WARNING'))
    db.commit()
    return users,topic,teams,tags

@pytest.fixture
def client(db):
    def override():
        yield db
    app.dependency_overrides[get_db]=override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()

def auth(user):
    return {'Authorization':f'Bearer {token(user)}'}
