export const date=(s:string)=>new Date(s).toLocaleDateString('tr-TR',{day:'numeric',month:'short',year:'numeric'})
export const percent=(n:number)=>`%${Math.round(n*100)}`
export const labels:Record<string,string>={PROPOSED:'Öneri',VOTING:'Oylamada',ACCEPTED:'Kabul edildi',REJECTED:'Reddedildi',ARCHIVED:'Arşivlendi',COMPLIANT:'Uyumlu',WARNING:'Uyarı',BLOCKED:'Engellendi',PENDING:'Kontrol bekliyor',MINORITY_CONFLICT:'Azınlık desteği yetersiz',EXPERT_REVIEW_REQUESTED:'Uzman görüşü bekliyor',YES:'Evet',NO:'Hayır',ABSTAIN:'Çekimser',TOPIC:'Konu',SUBTOPIC:'Alt konu',DELETION:'Arşivleme',APPROVE:'Olumlu görüş',REJECT:'Olumsuz görüş',REVISION_REQUIRED:'Revizyon gerekli',TOPIC_CREATED:'Konu önerildi',TOPIC_ACCEPTED:'Konu kabul edildi',SUBTOPIC_ACCEPTED:'Alt konu kabul edildi',EXPERT_USEFUL:'Uzman doğrulaması',QUALITY_CONTRIBUTION:'Kaliteli katkı'}

export const decimal=(n:number)=>n.toLocaleString('tr-TR',{minimumFractionDigits:2,maximumFractionDigits:2})
export const displayNames:Record<string,string>={
 USER:'Katılımcı',EXPERT:'Bilirkişi',ADMIN:'Yönetici',
 'Artificial Intelligence':'Yapay zekâ',Database:'Veritabanı','Cyber Security':'Siber güvenlik',Education:'Eğitim','Software Engineering':'Yazılım mühendisliği',
 MEMBER_OF:'Takım üyesi',CREATED:'Konu oluşturdu',VOTED_ON:'Oy kullandı',COMMENTED_ON:'Yorum yaptı',INTERESTED_IN:'İlgi alanı',
 HIGH_SUPPORT:'Yüksek etkili kararlarda destek oranı',MINORITY_SUPPORT:'Etkilenen takımın destek oranı',QUORUM:'Asgari katılımcı sayısı',EXPERT_REVIEW:'Bilirkişi görüşü sayısı',DESCRIPTION_LENGTH:'Açıklama uzunluğu'
}
export const displayName=(value:string)=>displayNames[value]||value
