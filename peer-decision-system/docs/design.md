# Geliştirme tasarım notları

Bu belge uygulama revizyonunun çalışma notudur; teslim edilecek ödev raporu değildir. 8 Ekim 2026 tarihinde paylaşılan dört ders PDF'i incelendi. Aşağıdaki uygulama eşlemesi bu notlara dayanır; ayrı laboratuvar ödevlerinin tamamının bu projeye zorunlu olduğu varsayılmamıştır. Aşağıdaki modeller mevcut kodu açıklar; dersin tüm gereksinimlerini veya bütün SOLID ilkelerine tam uyumu kanıtlama iddiası taşımaz.

## Aktörler ve kullanım durumları

| Aktör | Kullanım durumu ve sınır |
|---|---|
| Katılımcı | Öneri ve tartışma oluşturur; topluluk oylamasında ilgi alanı veya takım eşleşmesi gerekir. |
| Konu/teklif sahibi | Topluluk konusunu/teklifini yönetir; kurumsal kapsamda sahiplik tek başına yeterli değildir. |
| İlgili uzman | EXPERT rolü ve konu etiketi eşleşmesiyle görüş verir; tek başına kabul/ret kararı vermez. |
| Yönetici | Kullanıcı rolleri, kurul üyelikleri ve kuralları yönetir; kurul oyu için ayrıca üyelik gerekir. |
| Yetkili kurul üyesi | Yalnızca üyeliği olan kurumsal kapsamda oylama ve değerlendirme sürecini yönetir. |

Roller bir kişide birleşebilir. Kurul üyeliği `AuthorityMembership` ile rolden ayrı tutulur. Üniversite adları ve yetki eşlemesi demo verisidir.

### Kullanım durumu görünümü

Bu Mermaid akış görünümü aktör–kullanım durumu bağlantılarını gösterir; ayrıntılı yetki koşulları yukarıdaki tabloda ve aşağıdaki kabul ölçütlerindedir.

```mermaid
flowchart LR
    Participant[Katılımcı] --> Propose([Konu öner])
    Participant --> Discuss([Tartışmaya katıl])
    Participant --> Vote([Yetkisi olan oylamada oy kullan])
    Owner[Konu veya teklif sahibi] --> Manage([Topluluk oylamasını yönet])
    Board[İlgili kurul üyesi] --> BoardManage([Kurumsal oylamayı yönet])
    Board --> Vote
    Owner --> Request([Topluluk konusu için uzman görüşü iste])
    Board --> BoardRequest([Kurumsal konu için uzman görüşü iste])
    Expert[İlgili uzman] --> Review([Uzman görüşü ekle])
    Admin[Yönetici] --> Roles([Rol ve kurul üyeliği düzenle])
    Admin --> Rules([Politika kurallarını yönet])
    Admin --> Manage
    Admin --> Request
    Participant --> Audit([Kayıt defterini doğrula])
```

## Gereksinim–kod–test izlenebilirliği

Test adları mevcut testleri gösterir; bu tablo kendi başına testlerin çalıştırıldığı anlamına gelmez.

| Kimlik / kullanım durumu | Kabul ölçütü | Uygulama noktası | Doğrulama |
|---|---|---|---|
| G1 / Öneri oluştur, oylamaya aç | Başlangıç PROPOSED; yetkili yönetici VOTING yapar | `routers/api.py:start_voting`, `services/authority.py` | `test_proposed_topic_lifecycle`, `test_owner_and_admin_cannot_start_without_membership` |
| G2 / Oy kullan | İlgili/yetkili kullanıcı hedef başına yalnızca bir oy verir | `services/decisions.py:cast_vote`, `models.Vote` | `test_duplicate_vote_api`, `test_duplicate_vote_database`, `test_unrelated_cannot_vote` |
| G3 / Oylamayı sonuçlandır | En az 3 katılımcı; NORMAL >%50, HIGH ≥%60; çekimser oy yalnızca katılıma eklenir | `services/decisions.py:summary,close_vote` | `test_normal_majority_and_abstention`, `test_high_sixty_percent`, `test_no_quorum_remains_open` |
| G4 / Etkilenen grubu koru | Destek <%40 veya belirleyici grup oyu yoksa çoğunluk tek başına kabul sağlamaz | `services/decisions.py:close_vote` | `test_minority_conflict`, `test_unrepresented_affected_team_blocks`, `test_team_snapshot_stays_stable` |
| G5 / Politika kontrolü | Kabul ile uygulanabilirlik ayrıdır; zorunlu ihlal BLOCKED üretir | `services/policy.py`, `services/decisions.py:check_policy` | `test_policy_blocks_accepted_high_without_expert`, `test_rule_edit_rechecks_accepted_topics` |
| G6 / Uzman değerlendirmesini tamamla | Görüş bekleme işareti temizlenir; kabul edilmiş konunun politikası yeniden hesaplanır; azınlık engeli korunur | `routers/api.py:add_review,request_review,rerun_policy` | `test_policy_review_unblocks_without_changing_vote`, `test_expert_scope_and_no_unilateral_decision`; ek API regresyon kapsamı: `test_review_workflow.py` |
| G7 / Kurumsal yetkiyi uygula | ADMIN rolü kurul üyeliğinin yerine geçmez; üyelik kaldırılınca yetki kalkar | `services/authority.py` | `test_only_admin_assigns_membership_and_board_can_decide`, `test_wrong_board_and_revocation` |
| G8 / Geçmişi koru | Arşivleme içeriği silmez; olay değişiklikleri hash zincirinde denetlenir | `services/ledger.py`, `services/decisions.py:close_vote` | `test_archive_preserves_message`, `test_ledger_detects_payload_and_metadata_tamper` |
| G9 / Katkı puanı | Günlük 10, konu başına 8; puan oy ağırlığını değiştirmez | `services/points.py` | `test_point_limits_and_idempotence`, `test_reputation_does_not_weight_vote` |

`test_review_workflow.py` ek regresyonları: `test_accepted_review_request_resolves_and_restores_applicability`, `test_expert_review_rechecks_policy_for_accepted_high_impact_topic`, `test_closing_vote_preserves_pending_expert_request`, `test_expert_review_does_not_override_minority_conflict`, `test_institutional_management_matches_board_authority`. Sonuçlar ayrıca test çalıştırma çıktısıyla doğrulanmalıdır.

## Tasarım kararları ve GoF

`policy.py` içinde **GoF Strategy** uygulanır. `PolicyEngine`, koşul türüne göre `RuleStrategy` sözleşmesini sağlayan bir algoritmayı seçer. `PolicyContext` değişmez değerlendirme verisini taşır; stratejiler HTTP veya veritabanı sorgusu yapmaz. `check_policy` oy özetini ve uzman görüşü sayısını bir kez hazırlayıp tüm kurallarda kullanır. Bilinmeyen kayıtlı koşul türü sessiz onay yerine BLOCKED üretir. Yeni algoritma için strateji ve kayıt eklenir; HTTP üzerinden yeni tür kabul edilecekse Pydantic koşul şeması da güncellenmelidir.

Ledger, puan ve kayıt bulma sorumlulukları ayrı modüllere taşınmıştır. Bu ayrım SRP yönünde iyileştirmedir. `AnalysisProvider`, `Depends(get_analysis_provider)` üzerinden sağlanır; test veya başka sağlayıcı ile değiştirme sınırı oluşturur. Bağımlılık enjeksiyonu ve SRP ayrı GoF kalıpları olarak sayılmaz. `summary` içindeki NORMAL/HIGH çoğunluk hesabı halen koşulludur; uygulanmamış bir Strategy olarak gösterilmez. Durum diyagramı da tek başına GoF State kalıbı uygulandığı anlamına gelmez.

Servisler halen SQLAlchemy modellerine ve bazı HTTP hatalarına bağlıdır; router çok sayıda uç noktayı birleştirir. Dolayısıyla bu revizyon tam bir katman ayrıştırması değildir. İhtiyaç doğmadan her modele Repository veya her işleme sınıf eklenmemiştir.

## Sınıf diyagramı

Oklar mevcut modellerdeki ilişkileri ve politika sınıflarındaki bağımlılıkları gösterir. `Vote` üç hedeften **tam olarak birine** bağlıdır; bu ayrıca DB kısıtıyla korunur. Görsel, tüm sütunları göstermeyen bir UML özetidir.

```mermaid
classDiagram
    class User {
        id
        role
        points
    }
    class Topic {
        id
        status
        decision_scope
        policy_status
        decision_flag
    }
    class Vote {
        choice
        team_id
    }
    User "1" --> "0..*" AuthorityMembership : üyelik
    User "0..*" --> "0..1" Team : takım
    User "0..*" --> "0..*" Tag : ilgi
    User "1" --> "0..*" Topic : oluşturur
    Topic "0..*" --> "0..*" Tag : etiket
    Topic "1" --> "0..*" SubTopic : içerir
    Topic "1" --> "0..*" DiscussionMessage : tartışma
    DiscussionMessage "1" --> "0..1" DeletionProposal : arşivleme teklifi
    User "1" --> "0..*" Vote : kullanır
    Vote "0..*" --> "0..1" Topic : hedef
    Vote "0..*" --> "0..1" SubTopic : hedef
    Vote "0..*" --> "0..1" DeletionProposal : hedef
    Topic "1" --> "0..*" ExpertReview : değerlendirme
    User "1" --> "0..*" ExpertReview : uzman
    Topic "1" --> "0..*" RuleCheck : kontrol geçmişi
    Rule "1" --> "0..*" RuleCheck : koşul
    class RuleStrategy {
        <<interface>>
        fails(context, threshold) bool
    }
    class PolicyEngine {
        evaluate(kind, threshold, severity, context) str
    }
    class PolicyContext {
        <<immutable>>
        high_impact
        affected_team
        yes_ratio
        affected_support
        participants
        expert_reviews
        description_length
    }
    RuleStrategy <|.. HighSupport
    RuleStrategy <|.. MinoritySupport
    RuleStrategy <|.. Quorum
    RuleStrategy <|.. ExpertReviewRequired
    RuleStrategy <|.. DescriptionLength
    PolicyEngine o--> RuleStrategy : kayıtlı stratejiler
    PolicyEngine ..> PolicyContext : değerlendirir
    RuleStrategy ..> PolicyContext : okur
```

## Sekans: oy kullanma

```mermaid
sequenceDiagram
    actor U as Katılımcı
    participant UI as React arayüz
    participant API as API router
    participant D as decisions.cast_vote
    participant A as authority
    participant DB as SQLAlchemy / SQLite
    participant L as ledger
    U->>UI: Oy tercihi
    UI->>API: POST /votes
    API->>API: JWT ve giriş şeması doğrulama
    API->>API: write_lock al
    API->>D: cast_vote(db, user, hedef, tercih)
    D->>DB: Hedefi ve ana konuyu yükle
    D->>A: Kurumsal yetki kontrolü
    D->>D: Açık oylama ve katılım uygunluğu
    D->>DB: Önceki oy kontrolü
    alt Yetki veya durum uygun değil / tekrar oy
        D-->>API: HTTP hatası
        API-->>UI: 403 veya 409
    else Geçerli oy
        D->>DB: Vote ekle ve flush
        D->>L: VOTE_CAST ekle
        L->>DB: Önceki hash ile LedgerEntry ekle
        D-->>API: Oy kaydı
        API->>DB: Aynı transaction için commit
        API-->>UI: 201
    end
```

DB benzersizlik kısıtı, uygulama kontrolüne ek güvence sağlar. Ledger yazımı başarısızsa işlem commit edilmez. Süreç içi kilit yalnızca tek backend worker varsayımında yazıları sıralar.

## Sekans: uzman görüşünü tamamlama

```mermaid
sequenceDiagram
    actor M as Yetkili konu yöneticisi
    actor E as İlgili uzman
    participant API as API router
    participant DB as Veritabanı
    participant D as decisions.check_policy
    participant P as PolicyEngine
    participant L as ledger
    M->>API: POST /topics/id/request-expert-review
    API->>API: can_manage kontrolü
    API->>DB: Azınlık işareti yoksa EXPERT_REVIEW_REQUESTED
    API->>L: EXPERT_REVIEW_REQUESTED
    API->>DB: commit
    E->>API: POST /topics/id/expert-reviews
    API->>API: EXPERT rolü ve etiket eşleşmesi
    API->>DB: ExpertReview ekle ve flush
    API->>DB: EXPERT_REVIEW_REQUESTED varsa temizle
    alt Topic ACCEPTED
        API->>D: check_policy(db, topic)
        D->>DB: Oy özeti, görüş sayısı ve kurallar
        D->>P: Her koşulu PolicyContext ile değerlendir
        P-->>D: COMPLIANT / WARNING / BLOCKED
        D->>DB: RuleCheck kayıtları ve policy_status
        D->>L: RULE_CHECKED
    end
    API->>L: EXPERT_REVIEWED
    API->>DB: commit
    API-->>E: 201
```

Görüşün olumlu olması zorunlu değildir; uzman kararı devralmaz. Görüş, azınlık çatışması işaretini silmez ve oyları değiştirmez. Uygulanabilirlik için konu ACCEPTED, politika COMPLIANT/WARNING ve bekleyen karar işareti bulunmaması gerekir.

## Konu durum modeli

```mermaid
stateDiagram-v2
    [*] --> PROPOSED: Öneri oluştur
    PROPOSED --> VOTING: Yetkili yönetici başlatır
    VOTING --> VOTING: Quorum yok / sonuçlandırma reddi
    VOTING --> VOTING: Çoğunluk var, azınlık çatışması var
    VOTING --> ACCEPTED: Quorum + çoğunluk + grup koruması
    VOTING --> REJECTED: Quorum var, çoğunluk yok
    ACCEPTED --> ACCEPTED: Politika veya uzman görüşü güncellemesi
```

`policy_status` ve `decision_flag`, ana durumdan ayrı boyutlardır: ACCEPTED olmak uygulanabilir olmakla aynı değildir. Model enum'unda ARCHIVED bulunsa da konu arşivleme uç noktası yoktur; diyagramda uygulanmış geçiş gibi gösterilmez. Mesaj arşivleme ayrı bir teklif ve oylama akışıdır.

## Modül bağımlılık grafı

Ok yönü kullanan modülden kullanılan modüle doğrudur. Bu geliştirme grafı, uygulamadaki kullanıcı/konu/takım ilişki grafından farklıdır.

```mermaid
flowchart TD
    UI[React sayfaları] --> Client[api/client.ts]
    Client --> API[routers/api.py]
    API --> Security[core/security.py]
    API --> Schemas[schemas]
    API --> Decisions[services/decisions.py]
    API --> Authority[services/authority.py]
    API --> AI[AnalysisProvider bağımlılığı]
    API --> Provider[get_analysis_provider]
    Provider --> Mock[MockAnalysisProvider]
    Provider --> AI
    Decisions --> Policy[services/policy.py]
    Decisions --> Ledger[services/ledger.py]
    Decisions --> Points[services/points.py]
    Decisions --> Records[services/records.py]
    Decisions --> Authority
    Decisions --> Models[SQLAlchemy modelleri]
    Points --> Models
    Points --> Records
    Ledger --> Models
    API --> Models
    API --> Database[core/database.py]
    Models --> Database
```

## Doğrulama ve açık sınırlar

Backend regresyonları izole veritabanında çalıştırılmalı; özellikle bekleyen uzman talebinin sonuçlandırmada korunması, görüş sonrası çözülmesi, azınlık işaretinin korunması ve kurul üyelerinin yönetim işlemleri doğrulanmalıdır. Frontend için üretim derlemesi ve ilgili ekran akışları kontrol edilmelidir. Bu not herhangi bir çalıştırılmamış testi başarılı ilan etmez.

Ledger dağıtık blockchain değildir; bütün zincirin yetkili DB erişimiyle yeniden yazılmasını veya son kayıtların kesilmesini bağımsız bir referans olmadan kanıtlayamaz. Mock analiz gerçek LLM çıktısı değildir. Takım/ilgi üyelikleri demoda kullanıcı tarafından seçilir. Ders notlarıyla uygulama eşlemesi aşağıdadır; nihai rapor ve GitHub yayını ayrı aşamadır.

8 Ekim 2026 doğrulaması: izole backend testlerinde 47 test geçti; TypeScript kontrolü ve Vite üretim derlemesi tamamlandı. Mevcut Starlette/httpx deprecation uyarısı ve Vite 500 kB paket boyutu uyarısı sürüyor. Mermaid kaynakları kodla karşılaştırıldı; görsel render kontrolü henüz yapılmadı.


## Ders notlarına göre uygulama revizyonu — 8 Ekim 2026

Sayfa numaraları PDF içindeki fiziksel sayfalardır; slayt altındaki basılı numara farklı olabilir.

| Kaynak | Uygulamaya uyarlama | Sınır |
|---|---|---|
| YZM_Hafta02_Problem_Cerceveleme, s. 9–10, 16–17, 48 | `/engineering`: sekiz başlıklı, yönetici tarafından kaydedilen problem kanvası; metrik hedefleri ölçülmüş sonuçlardan ayrı | Hedefler taslak; gerçek paydaş görüşmesi yapılmadı |
| Aynı not, s. 25–30, 38, 41, 52–56 | Sabit COMMUNITY ve Türkçe anahtar kelime stratejisi; sınıf dağılımı, macro-F1, karışıklık matrisi, hatalar ve p95 hesaplama | 32 elle yazılmış sentetik örnek; bağımsız görülmemiş test kümesi değil |
| S01_YZ_Muhendisligine_Giris, s. 36–40 | Kapsam önerisi yalnız yardımcıdır; son seçim kullanıcıda, oy yetkisi ayrı deterministik kurallarda | Gerçek iş değeri, kullanıcı süresi ve maliyet iyileşmesi ölçülmedi |
| S02_Temel_Modelleri_Anlamak, s. 44–51 | Girdi doğrulama, sınırlı çıktı etiketleri, belirsizlikte insana bırakma; ekran gerçek model iddiasında bulunmaz | LLM eğitimi/API çağrısı, token ve sıcaklık deneyi eklenmedi; ayrı mini laboratuvar |
| tasarim_desenleri, s. 8–12, 36–37, 57–58 | Çalışan PolicyEngine/RuleStrategy; sorumluluk ayrımı; kapsam önerisinde iki değiştirilebilir strateji; görsel sınıf, use-case, sekans ve bağımlılık diyagramları | DI, Registry ve basit fonksiyonlar otomatik olarak ayrı GoF deseni sayılmaz. s.59 duygu analizi notebook ödevi ayrı bir örnektir |

### Yeni uygulama akışları

- Yeni konu formu başlık ve gerekçeden kapsam önerisi ister. Öneri otomatik kaydetmez, rol/üyelik değiştirmez; kullanıcı “Önerilen alanı seç” ile seçer. Metin değişince eski öneri temizlenir.
- Kanvas `project_canvas` tablosunda tutulur. Oturum açan kullanıcılar okuyabilir; yalnız ADMIN kaydeder. Her kayıt aynı transaction içinde ledger'a yazılır. Mevcut konu ve oylar korunur.
- Değerlendirme sorgusu her iki yöntemi aynı sabit JSON veri üzerinde gerçekten çalıştırır. SHA-256 ve veri sürümü görüntülenir. REVIEW bir öneriden kaçınma sütunudur; gerçek dört sınıfın macro-F1 hesabına beşinci gerçek sınıf olarak katılmaz.
- “Kapsama”, dört kapsamdan birini önerebilme oranıdır. Kapsam önerilmiş olsa da insan onayı gerekir. p95 yalnız süreç içi predict sürelerini ölçer, ağ veya uçtan uca API gecikmesini değil.
- Sentetik v1 ölçümü: sabit referans doğruluk 0,25 / macro-F1 0,10; anahtar kelime doğruluk 0,59375 / macro-F1 yaklaşık 0,6914. Hata ve çekimser örnekler saklanmıştır; bu sayılar ürün başarı iddiası değildir.

Yeni testler: `test_engineering.py` (Türkçe, belirsizlik, metrik hesabı, tekrar üretilebilirlik, oturum, kayıt değiştirmeme), `test_canvas.py` (yetki, kalıcılık, audit, şema doğrulama). Toplam 58 backend testi geçti. Gerçek kullanıcı veri toplama, bağımsız etiketleme ve kör test gelecekteki ölçüm işidir.
