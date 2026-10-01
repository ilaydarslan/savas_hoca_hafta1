import {Link} from 'react-router-dom'
import {ArrowUpRight,MessageSquare,Users,CheckCircle2} from 'lucide-react'
import type {ReactNode} from 'react'
import type {Topic,Summary} from '../types'
import {date,labels,percent,displayName} from '../utils/format'
export function Badge({value}:{value:string}){return <span className={`badge ${value.toLowerCase()}`}>{labels[value]||value}</span>}
export function RuleSeverityBadge({severity}:{severity:string}){
 const mandatory=severity==='BLOCKED'
 return <span className={`badge ${mandatory?'blocked':'warning'}`} title={mandatory?'Bu kurala uyulmazsa karar uygulanamaz.':'Bu kural eksikliği belirtir; tek başına kararı engellemez.'}>{mandatory?'Zorunlu kural':'Uyarı kuralı'}</span>
}
export function Heading({eyebrow,title,description,action}:{eyebrow?:string;title:string;description?:string;action?:ReactNode}){return <header className="page-heading"><div>{eyebrow&&<div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{description&&<p>{description}</p>}</div>{action}</header>}
export function Notice({children,kind='error'}:{children:ReactNode;kind?:string}){return <div role={kind==='error'?'alert':'status'} className={`notice ${kind}`}>{children}</div>}
export function Empty({children}:{children:ReactNode}){return <div className="empty"><MessageSquare size={26}/><p>{children}</p></div>}
export function Loading(){return <div className="loading" role="status">Veriler yükleniyor…</div>}
export function VoteMeter({votes}:{votes:Summary}){return <div className="vote-meter"><div className="flex justify-between gap-3"><span>Evet desteği <strong>{percent(votes.yes_ratio)}</strong></span><span><Users size={14}/> {votes.participants} katılımcı</span></div><div className="meter"><i style={{width:`${Math.round(votes.yes_ratio*100)}%`}}/></div></div>}
export function TopicCard({topic}:{topic:Topic}){
 return <Link to={`/topics/${topic.id}`} className="topic-card">
  <div className="topic-copy">
   <div className="topic-kicker"><span className="topic-number">#{String(topic.id).padStart(3,'0')}</span><span className="category">{displayName(topic.category)}</span></div>
   <h3>{topic.title}</h3><p>{topic.description}</p>
   <div className="topic-byline"><span>{topic.creator}</span><time>{date(topic.created_at)}</time>{topic.authority?.restricted&&<span className="authority-caption">{topic.authority.requested?'Kurul gündeminde':'Kurul yetkisi gerekli'}</span>}</div>
   {topic.decision_flag&&<div className="topic-flag"><Badge value={topic.decision_flag}/></div>}
  </div>
  <div className="topic-result"><Badge value={topic.status}/><strong>{topic.votes.participants?percent(topic.votes.yes_ratio):'—'}</strong><small>{topic.votes.participants?'evet desteği':'Henüz oy yok'}</small><span>{topic.votes.participants} katılımcı</span></div>
 </Link>
}
export function Verified({verified}:{verified:boolean}){return <span className={`verified ${verified?'':'bad'}`}><CheckCircle2 size={16}/>{verified?'Kayıt zinciri doğrulandı':'Kayıt zincirinde bütünlük hatası'}</span>}
