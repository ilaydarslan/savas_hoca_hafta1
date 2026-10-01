from sqlalchemy import select
import sys
from app.core.database import Base, engine, SessionLocal
from app.core.security import hasher
from app.models import *
from app.services.decisions import append_ledger, cast_vote, close_vote, award

PASSWORD = 'Demo12345!'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
def seed():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)):
            print('Veritabanında kullanıcı var; seed mevcut veriyi değiştirmedi.')
            return
        teams = [Team(name=n) for n in ['Mühendislik', 'Tasarım', 'Eğitim']]
        tags = [Tag(name=n) for n in ['Artificial Intelligence','Database','Cyber Security','Education','Software Engineering']]
        db.add_all(teams+tags)
        db.flush()
        names = [('Deniz','Yılmaz'),('Ece','Demir'),('Arda','Kaya'),('Selin','Aydın'),('Mert','Çelik'),('İpek','Şahin'),('Can','Koç'),('Elif','Arslan'),('Bora','Aksoy'),('Ada','Yıldız'),('Savaş','Öztürk'),('Derya','Güneş'),('Admin','Demo')]
        users = []
        password_hash = hasher.hash(PASSWORD)
        for i,(first,last) in enumerate(names):
            user = User(first_name=first,last_name=last,username=['deniz','ece','arda','selin','mert','ipek','can','elif','bora','ada','savas','derya','admin'][i],
                        email='user@example.com' if i==0 else 'expert@example.com' if i==10 else 'admin@example.com' if i==12 else f'demo{i+1}@example.com',
                        password_hash=password_hash,birth_date='2002-05-15',address=f'Örnek Kampüs, Demo Sokak No: {i+1}',
                        team_id=teams[i%3].id,role='ADMIN' if i==12 else 'EXPERT' if i>=10 else 'USER',interests=tags[:] if i != 9 else [tags[2]])
            db.add(user)
            users.append(user)
        db.flush()
        rule_specs = [
            ('Yüksek etki desteği','Yüksek etkili kararlar en az %60 evet desteği gerektirir.','HIGH_SUPPORT',.6,'BLOCKED'),
            ('Azınlık hakkının korunması','Etkilenen takımın desteği en az %40 olmalıdır. Temsil yoksa uygulama engellenir.','MINORITY_SUPPORT',.4,'BLOCKED'),
            ('Asgari katılım','Karar için en az 3 katılımcı gerekir; çekimser oylar katılıma dahildir.','QUORUM',3,'BLOCKED'),
            ('Bilirkişi değerlendirmesi','Yüksek etkili kararlarda en az bir bilirkişi değerlendirmesi bulunmalıdır.','EXPERT_REVIEW',1,'BLOCKED'),
            ('Gerekçeli öneri','Öneri açıklaması en az 80 karakter olmalıdır.','DESCRIPTION_LENGTH',80,'WARNING'),
        ]
        for i,(name,desc,kind,value,severity) in enumerate(rule_specs):
            db.add(Rule(code=f'RULE-{i+1:03}',name=name,description=desc,category='Katılımcı yönetim',condition={'kind':kind,'value':value},severity=severity))
        titles = [
            ('Kampüste yapay zekâ okuryazarlığı atölyeleri','Education','NORMAL',None),
            ('Ortak proje havuzu ve akran eşleştirme','Software Engineering','NORMAL',None),
            ('Tasarım stüdyosunun ortak kullanım saatleri','Education','HIGH',teams[1].id),
            ('Araştırma verileri için açık veri deposu','Database','HIGH',None),
            ('Haftalık siber güvenlik çalışma grubu','Cyber Security','NORMAL',None),
            ('Ders notları için erişilebilir arşiv','Education','NORMAL',teams[2].id),
            ('Yazılım projelerinde kod inceleme oturumları','Software Engineering','NORMAL',None),
            ('Yapay zekâ araçlarının etik kullanım rehberi','Artificial Intelligence','HIGH',None),
        ]
        topics=[]
        for i,(title,category,impact,team) in enumerate(titles):
            t=Topic(title=title,description=f'{title} için öğrencilerin birlikte çalışabileceği bir süreç öneriyoruz. Pilot uygulamada gönüllü katılım sağlanacak, geri bildirimler toplanacak ve sonuçlar tüm paydaşlarla açık biçimde değerlendirilecektir.',category=category,created_by=users[i%4].id,impact_level=impact,affected_team_id=team,tags=[next(tag for tag in tags if tag.name==category)])
            db.add(t);db.flush();topics.append(t)
            award(db,t.created_by,t.id,1,'TOPIC_CREATED',f'topic-created:{t.id}')
            append_ledger(db,'TOPIC_CREATED','TOPIC',t.id,{'title':title,'created_by':t.created_by})
            if i != 7:
                t.status='VOTING'
                append_ledger(db,'TOPIC_VOTING_STARTED','TOPIC',t.id,{'actor':users[12].id})
        for i,t in enumerate(topics[:7]):
            voters=users[:7] if i==2 else users[:5]
            for j,u in enumerate(voters):
                choice = ('NO' if u.team_id==teams[1].id else 'YES') if i==2 else ('NO' if j<4 else 'YES') if i==4 else 'ABSTAIN' if j==4 else 'YES'
                cast_vote(db,u,'TOPIC',t.id,choice)
        for i in [0,1,2,3,4,5]:
            close_vote(db,users[12],'TOPIC',topics[i].id)
        comments=['Bu önerinin pilot uygulamasını küçük bir grupla başlatabiliriz.','Katılım saatlerinin ders programlarıyla uyumlu olması önemli.','Sonuçları açık bir raporda paylaşmayı öneriyorum.','Erişilebilirlik ve kaynak ihtiyacını birlikte değerlendirelim.']
        for i in range(18):
            t=topics[i%8];u=users[i%10]
            m=DiscussionMessage(topic_id=t.id,user_id=u.id,message=comments[i%4])
            db.add(m);db.flush()
            append_ledger(db,'COMMENT_CREATED','MESSAGE',m.id,{'topic_id':t.id,'user_id':u.id,'message':m.message})
        for ti,ei,rec in [(0,10,'APPROVE'),(2,11,'REVISION_REQUIRED'),(6,10,'APPROVE')]:
            r=ExpertReview(topic_id=topics[ti].id,expert_id=users[ei].id,opinion='Pilot uygulamanın kapsamı, paydaş katılımı ve ölçülebilir başarı kriterleri netleştirilmelidir. Akran değerlendirmesiyle sonuçlar izlenebilir.',recommendation=rec)
            db.add(r);db.flush()
            append_ledger(db,'EXPERT_REVIEWED','TOPIC',r.topic_id,{'expert_id':r.expert_id,'recommendation':rec})
        for ti,title in [(0,'Başlangıç atölyesi müfredatı'),(0,'Gönüllü eğitmen eşleştirmesi'),(1,'Proje havuzu etiket yapısı')]:
            s=SubTopic(topic_id=topics[ti].id,created_by=users[0].id,title=title,description='İlk aşamada gönüllülerle uygulanacak ayrıntılı alt çalışma önerisi.')
            db.add(s);db.flush()
            append_ledger(db,'SUBTOPIC_CREATED','SUBTOPIC',s.id,{'title':title,'topic_id':s.topic_id})
        message=db.get(DiscussionMessage,1)
        p=DeletionProposal(message_id=message.id,proposed_by=users[0].id,reason='Bu mesajın içeriği yeni öneride daha ayrıntılı açıklandı; geçmiş korunarak arşivlenmesini öneriyorum.')
        db.add(p);db.flush()
        append_ledger(db,'DELETION_PROPOSED','DELETION',p.id,{'message_id':message.id,'reason':p.reason})
        db.commit()
        print('Demo hazır: 13 kullanıcı, 3 takım, 8 konu, 5 kural, 37 oy, 18 mesaj, 3 uzman görüşü, 3 alt konu.')

if __name__=='__main__':
    seed()
