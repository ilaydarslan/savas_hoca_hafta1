import {Link} from 'react-router-dom'
import {useApi} from '../hooks/useApi'
import {Heading,Loading,Notice,TopicCard,Verified,Empty,Badge} from '../components/UI'
import {NewTopicLink} from '../components/Layout'
import type {DashboardData,Topic} from '../types'
import {date,labels,decimal} from '../utils/format'

export function Dashboard(){
 const {data:d,error}=useApi<DashboardData>('/users/me/dashboard')
 const {data:topics,error:topicError}=useApi<Topic[]>('/topics')
 if(error)return <Notice>{error}</Notice>
 if(!d)return <Loading/>
 return <>
  <Heading title="Genel bakış" description={`${d.user.first_name} ${d.user.last_name} · ${d.user.team||'Takım seçilmedi'}`} action={<NewTopicLink/>}/>
  <div className="overview-numbers">
   <div><strong>{d.created_topics}</strong><span>Önerdiğin konu</span><small>{d.accepted_topics} kabul edildi</small></div>
   <div><strong>{d.votes_cast}</strong><span>Kullandığın oy</span><small>{d.pending_votes.length} oylama bekliyor</small></div>
   <div><strong>{d.discussion_contributions}</strong><span>Tartışma katkısı</span><small>{d.expert_reviews} bilirkişi görüşü</small></div>
   <div><strong>{d.user.points}</strong><span>Katkı puanı</span><small>r = {decimal(d.user.reputation_coefficient)}</small></div>
  </div>
  <div className="dashboard-columns">
   <section>
    <div className="section-heading"><h2>Oylamaya açık konular</h2><Link to="/topics">Tüm konular</Link></div>
    {topicError&&<Notice>{topicError}</Notice>}
    <div className="topic-directory">{topics?.filter(t=>t.status==='VOTING').slice(0,5).map(t=><TopicCard key={t.id} topic={t}/>)}</div>
    {topics&&!topics.some(t=>t.status==='VOTING')&&<Empty>Açık konu oylaması bulunmuyor.</Empty>}
    <section className="recent-vote-section"><div className="section-heading"><h2>Son oyların</h2><Link to="/votes">Oylamalar</Link></div>
     {d.my_votes.length?<div className="personal-votes">{d.my_votes.slice(0,6).map(v=><div key={v.id}>{v.topic_id?<Link to={`/topics/${v.topic_id}`}>{topics?.find(t=>t.id===v.topic_id)?.title||`Konu #${v.topic_id}`}</Link>:<span>{v.subtopic_id?`Alt konu #${v.subtopic_id}`:`Arşivleme #${v.deletion_proposal_id}`}</span>}<Badge value={v.choice}/></div>)}</div>:<p>Henüz oy kullanmadın.</p>}
    </section>
   </section>
   <aside className="right-column">
    <section className="desk-section"><div className="section-heading"><h2>Katılımını bekleyenler</h2><span>{d.pending_votes.length}</span></div>{d.pending_votes.length?<div className="pending-list">{d.pending_votes.slice(0,5).map(p=><Link key={`${p.target_type}-${p.target_id}`} to={`/topics/${p.topic_id}`}><small>{labels[p.target_type]}</small><span>{p.title}</span></Link>)}</div>:<p>Bekleyen oylaman yok.</p>}<Link className="desk-link" to="/votes">Oylama merkezine git</Link></section>
    <section className="desk-section"><div className="section-heading"><h2>Puan hareketleri</h2></div>{d.activities.length?d.activities.slice(0,4).map(a=><div className="activity" key={a.id}><span className="point-bubble">+{a.amount}</span><div><Link to={`/topics/${a.topic_id}`}>{labels[a.reason]||a.reason}</Link><small>{date(a.created_at)}</small></div></div>):<p>Henüz puan hareketi yok.</p>}</section>
    <section className="desk-section"><Verified verified={d.ledger.verified}/><Link className="desk-link" to="/ledger">İşlem defteri · {d.ledger.count} kayıt</Link></section>
   </aside>
  </div>
 </>
}
