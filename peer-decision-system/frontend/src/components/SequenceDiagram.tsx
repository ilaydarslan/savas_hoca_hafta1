import {useId, useState} from 'react'

type Step = {from:number;to:number;message:string;detail:string;condition?:string;response?:boolean}
type Flow = {id:string;name:string;endpoint:string;purpose:string;actors:string[];steps:Step[];failures:string[];references:string[]}

const flows:Flow[] = [
  {
    id:'vote',name:'Oy kullanma',endpoint:'POST /votes',
    purpose:'Bir oyun kaydı ile denetim izinin aynı veritabanı işlemi içinde nasıl tutulduğunu gösterir.',
    actors:['Kullanıcı','API / auth','Karar servisi','Kayıt defteri','Veritabanı'],
    steps:[
      {from:0,to:1,message:'Oy gönder',detail:'VoteInput: target_type, target_id ve choice. current_user oturumu doğrular; API write_lock içine girer.'},
      {from:1,to:2,message:'cast_vote çağır',detail:'Hedef ve ana konu target() ile çözülür; require_authority kapsam yetkisini denetler.'},
      {from:2,to:2,message:'Açık oylama ve uygunluk',detail:'Hedef VOTING olmalı. eligible(), kurumsal kapsamda kurul üyeliğini; toplulukta ilgili takım veya ilgi alanını kontrol eder.'},
      {from:2,to:4,message:'Önceki oyu sorgula',detail:'Aynı kullanıcı ve aynı hedef için mevcut Vote kaydı aranır.'},
      {from:2,to:4,message:'Vote ekle + flush',detail:'Kullanıcı, tercih ve oy anındaki team_id ile Vote eklenir. flush henüz commit değildir.'},
      {from:2,to:3,message:'VOTE_CAST olayı',detail:'append_ledger aynı db oturumuna olay türünü, hedefi ve oy bilgilerini alır.'},
      {from:3,to:4,message:'Önceki hash → yeni kayıt',detail:'Son LedgerEntry okunur; veri ve zincir hash değerleri hesaplanır; LedgerEntry eklenir ve flush yapılır.'},
      {from:2,to:1,message:'Vote nesnesini döndür',detail:'cast_vote oluşturduğu Vote nesnesini API katmanına döndürür.',response:true},
      {from:1,to:4,message:'commit(db)',detail:'Oy ve kayıt defteri girdisi birlikte kalıcı hale gelir.'},
      {from:1,to:0,message:'201 · oy kaydı',detail:'API row(result) ile oluşturulan oy kaydını döndürür.',response:true},
    ],
    failures:['Yetki veya uygunluk yoksa 403; oylama kapalıysa ya da aynı hedefe tekrar oy verilirse 409 döner.','Veritabanı benzersizlik denetiminden IntegrityError gelirse rollback yapılır ve 409 döner; ikinci oy kalıcılaşmaz.'],
    references:['app/routers/api.py → vote','app/services/decisions.py → cast_vote, target, eligible','app/services/ledger.py → append_ledger'],
  },
  {
    id:'close',name:'Oylamayı sonuçlandırma',endpoint:'POST /topics/{id}/close-voting',
    purpose:'Katılım ve çoğunluk koşullarının hangi karar dallarına yol açtığını, yönetmelik denetiminin ne zaman çalıştığını gösterir.',
    actors:['Kullanıcı','API / auth','Karar servisi','Kural / puan','Kayıt defteri','Veritabanı'],
    steps:[
      {from:0,to:1,message:'Oylamayı kapat',detail:'current_user kimliği doğrular; close_topic API işlevi write_lock içinde çalışır.'},
      {from:1,to:2,message:'close_vote(TOPIC)',detail:'require_authority, can_manage ve VOTING durumu denetlenir.'},
      {from:2,to:5,message:'Oy özeti / summary',detail:'Katılım, evet oranı, çoğunluk ve etkilenen grubun desteği hesaplanır. Yetersiz katılımda akış burada 409 ile kesilir.'},
      {from:2,to:4,message:'MINORITY_CONFLICT',condition:'çoğunluk + grup itirazı',detail:'Çoğunluk var ancak etkilenen grubun desteği yetersizse konu VOTING kalır, decision_flag=MINORITY_CONFLICT ve policy_status=BLOCKED olur; olay eklenir. Kabul/red adımları atlanır.'},
      {from:2,to:2,message:'ACCEPTED / REJECTED',condition:'grup itirazı dalı yoksa',detail:'Çoğunluk sağlanıyorsa ACCEPTED, sağlanmıyorsa REJECTED atanır. Önceki MINORITY_CONFLICT bayrağı temizlenir.'},
      {from:2,to:3,message:'check_policy + award',condition:'yalnızca ACCEPTED',detail:'Her Rule için PolicyEngine.evaluate çağrılır; RuleCheck ve policy_status üretilir, RULE_CHECKED olayı eklenir. award ile konu sahibine limitler ve tekrar denetimi altında 3 puan verilir.'},
      {from:2,to:4,message:'TOPIC_ACCEPTED / REJECTED',condition:'grup itirazı dalı yoksa',detail:'Sonuç olayı append_ledger ile aynı işlemde eklenir. Kabul durumu, policy_status değerinin COMPLIANT olduğunu garanti etmez.'},
      {from:4,to:5,message:'Hash zincirine ekle + flush',detail:'Bu şema defter çağrılarını topluca gösterir; her append_ledger çağrısı ilgili anda önceki hash değerini okuyup yeni LedgerEntry yazar.'},
      {from:2,to:1,message:'Seçilen dalın sonucunu döndür',detail:'Normal dal: status ve policy_status. Azınlık çatışması dalı: status=VOTING, decision_flag ve message.',response:true},
      {from:1,to:5,message:'commit(db)',detail:'Seçilen dalın durum, kontrol, puan ve defter değişiklikleri birlikte kalıcılaşır.'},
      {from:1,to:0,message:'200 · dalın sonucu',detail:'API close_vote sonucunu olduğu gibi döndürür.',response:true},
    ],
    failures:['Yetkisiz kullanıcı 403; VOTING dışındaki konu veya 3 kişiden az katılım 409 üretir. Yetersiz katılımda oylama açık kalır.','Çoğunluk varken etkilenen grubun desteği yetersizse işlem hata değil, 200 / VOTING sonucudur; kabul veya red oluşmaz.','Şemadaki koşullu adımlar alternatif dallardır; tek istekte bütün dallar yürütülmez.'],
    references:['app/routers/api.py → close_topic','app/services/decisions.py → close_vote, summary, check_policy','app/services/policy.py → PolicyEngine.evaluate','app/services/points.py → award'],
  },
  {
    id:'review',name:'Bilirkişi görüşü',endpoint:'POST /topics/{id}/expert-reviews',
    purpose:'Uzman görüşünün kaydedilmesini ve kabul edilmiş bir konuda yönetmelik kontrolünü nasıl yenilediğini gösterir.',
    actors:['Bilirkişi','API / auth','Karar / PolicyEngine','Kayıt defteri','Veritabanı'],
    steps:[
      {from:0,to:1,message:'Görüşü gönder',detail:'ReviewInput doğrulanır; current_user kimliği doğrular ve add_review write_lock içine girer.'},
      {from:1,to:4,message:'Konuyu oku',detail:'require(db, Topic, id) ile konu bulunur.'},
      {from:1,to:1,message:'EXPERT + alan eşleşmesi',detail:'Kullanıcı rolü EXPERT olmalı ve kullanıcının ilgi alanları ile konunun etiketleri kesişmelidir. ADMIN olmak tek başına yeterli değildir.'},
      {from:1,to:4,message:'ExpertReview ekle + flush',detail:'topic_id, expert_id ve doğrulanmış görüş alanları ile kayıt oluşturulur.'},
      {from:1,to:1,message:'Görüş talebi bayrağını temizle',condition:'EXPERT_REVIEW_REQUESTED ise',detail:'Yalnızca bu bayrak None yapılır. MINORITY_CONFLICT bayrağı bu adımla kaldırılmaz.'},
      {from:1,to:2,message:'check_policy(db, topic)',condition:'konu ACCEPTED ise',detail:'Yeni görüş sayısı dahil PolicyContext hazırlanır; kurallar değerlendirilir; RuleCheck kayıtları ve policy_status güncellenir.'},
      {from:2,to:3,message:'RULE_CHECKED',condition:'konu ACCEPTED ise',detail:'Yönetmelik denetimi sonucu aynı veritabanı işleminde kayıt defterine eklenir.'},
      {from:1,to:3,message:'EXPERT_REVIEWED',detail:'Bilirkişi kimliği ve görüş alanlarıyla ayrı denetim olayı eklenir.'},
      {from:3,to:4,message:'Hash zincirine ekle + flush',detail:'Her defter çağrısı kendi anında son hash değerini okur ve yeni LedgerEntry ekler. Bu ok, iki olası çağrıyı özetler.'},
      {from:1,to:4,message:'commit(db)',detail:'Görüş, bayrak değişikliği, varsa yönetmelik denetimi ve defter kayıtları birlikte kalıcılaşır.'},
      {from:1,to:0,message:'201 · görüş kaydı',detail:'row(review) döner. Görüş tek başına konu durumunu ACCEPTED veya REJECTED yapmaz.',response:true},
    ],
    failures:['Konu bulunamazsa 404; EXPERT rolü veya etiket eşleşmesi yoksa 403 döner.','Konu ACCEPTED değilse yönetmelik kontrolü çalışmaz; görüş ve EXPERT_REVIEWED olayı yine kaydedilir.'],
    references:['app/routers/api.py → add_review','app/services/decisions.py → check_policy','app/services/policy.py → PolicyEngine.evaluate','app/services/ledger.py → append_ledger'],
  },
]

export function SequenceDiagram(){
  const [selected,setSelected]=useState('vote')
  const id=useId().replace(/:/g,'')
  const flow=flows.find(item=>item.id===selected)!
  const spacing=230, left=112, width=flow.actors.length*spacing, height=140+flow.steps.length*91
  return <div className="panel eng-diagram-panel">
    <h3>Sekans diyagramları · gerçek istek akışları</h3>
    <p>Sekans diyagramı “hangi bileşen, hangi sırayla kimi çağırıyor?” sorusunu yanıtlar. Dikey kesikli çizgiler katılımcıları, yatay oklar çağrıları, kesikli oklar dönüşleri gösterir.</p>
    <div className="eng-diagram-options" aria-label="Sekans akışı">{flows.map(item=><button type="button" key={item.id} className={`button ${item.id===selected?'primary':'secondary'}`} aria-pressed={selected===item.id} onClick={()=>setSelected(item.id)}>{item.name}</button>)}</div>
    <h4>{flow.name}</h4><code>{flow.endpoint}</code><p>{flow.purpose}</p>
    <p className="eng-caption">Üstten alta okunur. Köşeli parantezler koşullu adımlardır. Numaraların ayrıntıları şemanın altında yer alır; küçük ekranda şemayı yatay kaydırabilirsin.</p>
    <div className="eng-sequence-scroll" tabIndex={0} aria-label={`${flow.name} şeması; yatay kaydırılabilir`}>
      <svg viewBox={`0 0 ${width} ${height}`} style={{minWidth:width,width:'100%',maxHeight:'none'}} role="img" aria-labelledby={`${id}-title ${id}-description`}>
        <title id={`${id}-title`}>{flow.name}: {flow.endpoint}</title><desc id={`${id}-description`}>{flow.purpose} Numaralı metin karşılığı aşağıdaki listede.</desc>
        <defs><marker id={`${id}-arrow`} markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#39664f"/></marker></defs>
        {flow.actors.map((actor,index)=><g key={actor}><rect x={index*spacing+15} y="16" width="194" height="48" rx="8" fill="#e9f1ec" stroke="#90ad9d"/><text x={index*spacing+left} y="46" textAnchor="middle" fontSize="15" fill="#173b2b">{actor}</text><line x1={index*spacing+left} x2={index*spacing+left} y1="64" y2={height-20} stroke="#adc0b5" strokeDasharray="6 6"/></g>)}
        {flow.steps.map((step,index)=>{const start=step.from*spacing+left,end=step.to*spacing+left,y=126+index*91,self=step.from===step.to;const center=self?start+79:(start+end)/2;return <g key={`${flow.id}-${index}`}>
          {step.condition&&<text x={center} y={y-33} textAnchor="middle" fontSize="11" fill="#876f29" stroke="white" strokeWidth="5" paintOrder="stroke">[{step.condition}]</text>}
          <text x={center} y={y-12} textAnchor="middle" fontSize="13" fill="#173b2b" stroke="white" strokeWidth="5" paintOrder="stroke">{index+1}. {step.message}</text>
          {self?<path d={`M${start},${y} h70 v23 h-70`} fill="none" stroke="#39664f" strokeWidth="1.5" markerEnd={`url(#${id}-arrow)`}/>:<line x1={start} x2={end} y1={y} y2={y} stroke="#39664f" strokeWidth="1.5" strokeDasharray={step.response?'6 4':undefined} markerEnd={`url(#${id}-arrow)`}/>}
        </g>})}
      </svg>
    </div>
    <h4>Akışın adım adım karşılığı</h4><ol style={{paddingLeft:24,lineHeight:1.8,fontSize:13}}>{flow.steps.map((step,index)=><li key={`${flow.id}-${index}`} style={{marginBottom:10}}><strong>{flow.actors[step.from]} → {flow.actors[step.to]}: {step.message}.</strong> {step.condition&&<em>Koşul: {step.condition}. </em>}{step.detail}</li>)}</ol>
    <h4>Alternatif ve başarısızlık yolları</h4><ul className="eng-notes">{flow.failures.map(item=><li key={item}>{item}</li>)}</ul>
    <details><summary>Koddaki karşılığı</summary><ul>{flow.references.map(item=><li key={item}><code>{item}</code></li>)}</ul><p>Dosya yolları backend klasörüne göredir. Şema ağ trafiği kaydı değil, mevcut işlevlerden çıkarılmış tasarım görünümüdür.</p></details>
  </div>
}
