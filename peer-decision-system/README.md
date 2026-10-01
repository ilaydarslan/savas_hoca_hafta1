# Müşterek — Akran Öğrenme ve Katılımcı Karar Alma Sistemi

Üniversite topluluğu için çalışan, Türkçe arayüzlü bir katılımcı karar alma prototipi. Kullanıcılar konu önerir, tartışır, eşit oyla karar alır; etkilenen grubun desteği ve yönetmelik uygunluğu ayrıca kontrol edilir.

## Teknolojiler

- React, Vite, TypeScript, React Router, Tailwind CSS, Axios, React Flow (`@xyflow/react`), Lucide
- Python 3.12+, FastAPI, SQLAlchemy, Pydantic, SQLite
- JWT (HS256, 8 saat), Argon2 parola hash'i
- Pytest ve FastAPI TestClient
- Harici AI servisi, API anahtarı veya Docker gerektirmez.

## Klasör yapısı

```text
peer-decision-system/
  backend/
    app/
      core/       # Veritabanı, JWT, parola hash'i
      models/     # 16 ilişkisel tablo ve veritabanı kısıtları
      schemas/    # Pydantic giriş doğrulaması
      routers/    # REST API ve yetkilendirme
      services/   # Karar, yönetmelik, puan, ledger, mock AI
      seed/       # Tekrar çalıştırılabilir demo seed
      main.py
    tests/
    requirements.txt
    requirements.lock.txt
    .env.example
  frontend/
    src/
      api/ auth/ components/ pages/ types/ hooks/ utils/
    package.json
    pnpm-lock.yaml
  start-demo.ps1
  README.md
```

## Windows kurulumu

### Bu bilgisayarda tek tikla acma

Projenin bir ust klasorundeki **Uygulamayi Ac.cmd** dosyasina cift tiklayin. Backend ve frontend arka planda baslar, hazir oldugunda varsayilan tarayicinizda **http://localhost:5173** acilir. Codex'i acmaniz gerekmez. Bilgisayari yeniden baslattiktan sonra ayni dosyayi tekrar calistirin. Calisan servisler tekrar baslatilmaz; mevcut veriler korunur. Servisler Windows uzerinden bagimsiz, gizli surecler olarak acilir; baslatan komut penceresine bagli kalmaz. Bunun icin zamanlanmis gorev veya otomatik acilis kaydi olusturulmaz. Isterseniz bu dosyaya Windows'tan masaustu kisayolu olusturabilirsiniz.

Bu adres yereldir; bu bilgisayarda calisir. Internette yayinlanmis bir adres degildir.

Python 3.12 veya üzeri ve Node.js 22 LTS veya üzeri kurulu olmalı. Aşağıdaki komutları PowerShell'de proje kökünde çalıştırın. Windows Python Launcher yoksa `py -3` yerine `python` kullanın.

```powershell
cd "C:\projenin-bulundugu-klasor\peer-decision-system"
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.lock.txt
cd frontend
npm install
cd ..
```

`requirements.lock.txt` test edilen tam sürümleri sabitler. `requirements.txt` taşınabilir bağımlılık aralıklarını içerir. pnpm kullanıyorsanız frontend klasöründe `pnpm install --frozen-lockfile` çalıştırabilirsiniz; pnpm kilit dosyası projeye dahildir.

### 1. Demo verilerini oluşturun

```powershell
cd backend
..\.venv\Scripts\python.exe -m app.seed.demo
```

Seed mevcut kullanıcı varsa hiçbir veriyi değiştirmez. SQLite dosyası backend çalışma dizininde `peer_decision.db` olarak oluşur. Seed tamamen kurgusal ad, adres ve doğum tarihi kullanır.

### 2. Backend'i başlatın

Backend klasöründe:

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- API: http://localhost:8000/api/v1
- Swagger: http://localhost:8000/docs
- Sağlık kontrolü: http://localhost:8000/health

### 3. Frontend'i başlatın

Yeni bir PowerShell penceresinde:

```powershell
cd "C:\projenin-bulundugu-klasor\peer-decision-system\frontend"
npm run dev
```

Arayüz: http://localhost:5173 — Vite `/api` isteklerini 8000 portundaki backend'e yönlendirir. Alternatif backend için `VITE_API_URL` tanımlanabilir. CORS varsayılan olarak localhost ve 127.0.0.1:5173 adreslerini kabul eder.

Bağımlılıklar kurulduktan sonra proje kökünde `powershell -ExecutionPolicy Bypass -File .\start-demo.ps1` komutu da iki servisi gizli pencerelerde başlatır ve tarayıcıyı açar. Tarayıcı açılmasın istiyorsanız `-NoBrowser` ekleyin. Zaten çalışan portları yeniden başlatmaz; işlem kimliklerini ve adresleri gösterir. Loglar backend ve frontend klasörlerindeki `.log` dosyalarına yazılır.

## Demo hesapları

Tüm demo hesaplarının şifresi: **Demo12345!**

| E-posta | Kullanıcı | Rol |
|---|---|---|
| user@example.com | deniz | USER |
| expert@example.com | savas | EXPERT |
| admin@example.com | admin | ADMIN |
| demo12@example.com | derya | EXPERT |
| demo2@example.com – demo10@example.com | ece, arda, selin, mert, ipek, can, elif, bora, ada | USER |

Seed: **10 USER, 2 EXPERT, 1 ADMIN; 3 takım; 5 tag; 8 konu; 5 kural; 37 oy; 18 mesaj; 3 uzman görüşü; 3 alt konu ve 1 arşivleme teklifi.**

## Sunum akışı

1. `user@example.com` ile giriş yapın; kişisel istatistik, bekleyen oylar, puan hareketleri ve ledger durumunu inceleyin.
2. Konu önerin. Konu **PROPOSED** oluşur; sahibi veya yönetici oylamayı başlatabilir.
3. İlgili üç farklı hesapla oy kullanın. `demo10@example.com` yalnızca Cyber Security ilgisine sahiptir; diğer takımlara/alanlara ait konularda oy veremez.
4. Konu sahibi veya yönetici oylamayı sonuçlandırsın. Yeterli katılım yoksa oylama açık kalır.
5. **Konu #3: Tasarım stüdyosunun ortak kullanım saatleri** genel destek yüksek olmasına rağmen etkilenen takım desteği yetersiz olduğu için `MINORITY_CONFLICT` gösterir.
6. **Konu #4: Araştırma verileri için açık veri deposu** kabul edilmiştir, ancak yüksek etkili karar için bilirkişi görüşü eksik olduğundan `RULE-004` nedeniyle `BLOCKED` durumundadır. İlgili uzman görüş ekleyebilir; konu sahibi/yönetici politika kontrolünü yeniden çalıştırabilir.
7. Kabul edilmiş **konu #1** altında tartışma, alt konular ve mesaj #1 için açık arşivleme teklifini gösterin. Teklife üç evet oyu verip sonuçlandırınca mesaj `ARCHIVED` olur; içerik ve geçmiş yerinde kalır.
8. Graph'ta ilişki türüyle filtreleyin; bir düğüme tıklayarak komşularını inceleyin.
9. Ledger zincirini doğrulayın, bir kaydı açarak önceki hash, veri hash'i ve içeriğini görün.
10. Admin ile kullanıcı rolü ve kural yönetimini gösterin. Kural değişince kabul edilen konular yeniden kontrol edilir.

## Sayfalar ve özellikler

`/login`, `/register`, `/`, `/topics`, `/topics/new`, `/topics/:id`, `/votes`, `/graph`, `/ledger`, `/rules`, `/profile`, `/admin`, `/admin/users`, `/admin/rules`.

Konu detayında Genel bakış, Oylama, Tartışma, Alt konular, Bilirkişi görüşleri, AI Analysis ve Yönetmelik kontrolleri bulunur. Sayfalar API'ye bağlıdır; yüklenme, boş sonuç ve hata durumları gösterilir.

## Mimari ve karar modeli

### Kurumsal karar yetkisi (demo)

Yeni konu formunda karar alanı/türü seçilir: öğrenci topluluğu, bölüm, fakülte veya Ankara Üniversitesi. Topluluk konuları mevcut ilgi alanı/takım oylamasını kullanır. Kurumsal konularda yalnızca ilgili kurul üyeleri oylamayı başlatabilir, oy verebilir ve sonuçlandırabilir. ADMIN ve EXPERT rolleri tek başına kurul yetkisi sağlamaz; bölüm/fakülte üyeliği de üniversite yetkisi sağlamaz. Alt konu ve arşivleme oyları ana konunun yetki kapsamını devralır. Quorum, çoğunluk, azınlık ve politika kontrolleri geçerliliğini korur.

Herkes kurumsal öneri oluşturabilir ve tartışabilir. Yetkisiz katılımcıya **“Bu kararı siz alamazsınız”** uyarısı ve yetkili organ gösterilir. Öneri sahibi/yönetici **Yetkili kurula yönlendir** düğmesiyle öneriyi uygulama içi kurul gündemine alır. Konular listesinde **Kurul gündeminde** etiketi görünür. Bu işlem gerçek üniversiteye e-posta veya bildirim göndermez.

`admin@example.com` ile **Yönetim paneli → Kullanıcılar → Kurul üyelikleri** alanından demo üyeleri atayın. Başlangıçta kimseye otomatik kurul yetkisi verilmez. Üç kullanıcıya aynı kurul üyeliği atayarak oylama senaryosunu gösterebilirsiniz. Üyelik ekleme/kaldırma ve kurul değerlendirme talepleri ledger'a kaydedilir. Kullanıcı kendi profilinden kurul üyeliği edinemez.

Mevcut konular veri kaybı olmadan COMMUNITY kapsamına taşınır; eski konuların bağlamı otomatik yorumlanmaz. Karar kapsamı metinden anlaşılmaz; formda seçilir ve oluşturulduktan sonra değiştirilemez. Gerçekte kurumsal olan bir önerinin yanlışlıkla topluluk olarak sınıflandırılması bu MVP'de otomatik tespit edilmez. Üretim kullanımında kapsam doğrulama/onay süreci eklenmelidir.

**Ankara Üniversitesi ve kurul adları yalnızca örnek yetki eşlemesidir; gerçek mevzuat veya gerçek kurul üyelikleri değildir.** Demo tek bölüm/fakülte/üniversite kapsamı kullanır; birden çok kurum ve gerçek yetki dağılımı için doğrulanmış kurumsal model gerekir.

### Veritabanı ve yetkiler

SQLAlchemy modelleri: User, Team, Tag, UserInterest, Topic, TopicTag, SubTopic, Vote, DiscussionMessage, DeletionProposal, ExpertReview, Rule, RuleCheck, LedgerEntry, PointEvent. FK'ler SQLite'ta da aktiftir. Vote tam olarak bir hedefe bağlıdır; her hedef türünde `(user_id, target_id)` benzersiz kısıtı vardır. API doğrulaması ve DB kısıtı çift oyu birlikte engeller.

Kayıtta rol atanamaz; her yeni hesap USER olur. Backend JWT'yi ve güncel rolü her korumalı istekte denetler. EXPERT sadece tag eşleşen konularda görüş yazabilir. Konu sahibi veya ADMIN oylamayı başlatıp kapatabilir; alt konuda teklif sahibi, arşivlemede teklif sahibi veya ADMIN kapatabilir. Son ADMIN'in rolü düşürülemez. Parola hash'i hiçbir API cevabında dönmez.

JWT `sessionStorage` içinde tutulur; çıkış token'ı tarayıcıdan kaldırır. Bu MVP'de sunucu taraflı token iptal listesi yoktur; alınmış token 8 saat dolana kadar geçerlidir. `JWT_SECRET` tanımlanmazsa backend yerel `.jwt-secret` dosyasında rastgele bir anahtar oluşturur. `.env.example` içindeki örnek anahtar gerçek kullanımda değiştirilmelidir.

### Majority / minority

- Oylama yetkisi: kullanıcı ilgi tag'lerinden en az biri konu tag'leriyle eşleşmeli **veya** kullanıcı doğrudan etkilenen takıma üye olmalıdır. ADMIN de aynı oy yetkisi kuralına tabidir.
- Quorum: **3 katılımcı**, `services/decisions.py` içindeki `QUORUM` sabiti.
- `ABSTAIN` quorum'a eklenir; `YES/(YES+NO)` hesabına girmez. Sadece çekimser oylar kabul oluşturmaz.
- NORMAL: oran **%50'den büyük**; HIGH: **en az %60**.
- Etkilenen takım için aynı destek hesabı ayrıca yapılır. Destek <%40 ise veya takımın belirleyici oyu yoksa karar otomatik uygulanmaz.
- `MINORITY_CONFLICT` durumunda ana konu VOTING kalır, politika durumu BLOCKED olur. Eksik katılımcılar oy verebilir; uzman görüşü istenebilir. Oy değiştirilemez. Uzman tek başına sonucu değiştiremez. Mevcut öneri değişecekse yeni konu önerilir; geçmiş korunur.
- Oy anındaki takım Vote üzerinde saklanır; sonradan profil değişikliği eski oyların takım dağılımını değiştirmez.
- Alt konu ve arşivleme teklifleri ana konunun etki/takım korumasını devralır. Çatışmada sonuçlandırılmaz, uyarı dönülür.
- Kabul edilmek ile uygulanabilir olmak ayrıdır: `can_apply` ancak kabul + engelleyici politika bulunmaması + azınlık çatışması bulunmaması durumunda doğrudur.
- Bu prototip dış dünyada karar icra etmez; uygulanabilirlik bilgisini gösterir.

### Puan ve r

Yeni konu +1; kabul edilen konu +3; kabul edilen alt konu +2; yönetici tarafından kaliteli bulunan katkı +2; ilgili uzman tarafından faydalı doğrulanan katkı +2. Mesaj yazmak tek başına puan getirmez. Kalite ve uzman ödülleri, kullanıcı/konu/ödül türü başına bir kez verilir; tek bir konudaki yorum sayısıyla puan çoğaltılamaz. Günlük **10**, konu başına **8** puan sınırı uygulanır. Limit dolunca kalan miktar kadar puan verilir. Her hareket ayrı PointEvent kaydıdır.

`r = clamp(1 + puan / 100, 0.8, 1.2)`. Başlangıç 1.0; bu sürümde negatif puan olmadığından r düşmez. **r hiçbir zaman oy ağırlığı değildir.** Dashboard ve profil üzerinde itibar göstergesidir.

### Ledger

Append-only API: ledger için sadece okuma ve doğrulama vardır; update/delete yoktur. SHA-256 ile kanonik JSON payload hash'lenir. Kayıt hash'i event türü, entity türü/id, veri hash'i, önceki hash ve zaman bilgisini kapsar. `verify_ledger()` tüm zinciri baştan hesaplar, ilk hatalı kaydı bildirir. Liste en yeni 300 kaydı gösterir; doğrulama tüm kayıtları kapsar. Yazılar, olayın veritabanı değişikliğiyle aynı transaction içinde kaydedilir.

Bu **blockchain-inspired audit ledger**'dır; dağıtık konsensüs veya fiziksel değişmezlik sağlamaz. DB'ye doğrudan erişen birinin bütün zinciri yeniden hesaplamasını ya da kuyruk kayıtlarını kesmesini bağımsız bir hash sabitlemesi olmadan tespit edemez. MVP tek backend worker ile çalışır; süreç içi kilit yazıları sıralar. Çoklu worker/çoklu sunucu için DB seviyesinde ledger head kilidi ve migration gerekir.

### Rule / ontology engine

JSON koşullu beş desteklenen koşul türü: HIGH_SUPPORT, MINORITY_SUPPORT, QUORUM, EXPERT_REVIEW, DESCRIPTION_LENGTH. Eşik ihlal edilirse ilgili kuralın WARNING/BLOCKED seviyesi uygulanır; aksi COMPLIANT olur. Her kontrol RuleCheck geçmişine açıklamasıyla kaydedilir. Kurallar değişince ACCEPTED konular tekrar kontrol edilir. Temel çoğunluk, asgari katılım ve azınlık koruması ayrıca karar motorunda korunur; admin kuralı gevşetse de bu sınırların altına inilmez.

İlk üç kural karar mantığını açıklar. RULE-004 yüksek etkili kararlar için en az bir uzman görüşü gerektirir; görüşün olumlu olması şart değildir, uzman sonucu belirlemez. RULE-005 kısa gerekçeler için uyarı verir. Gerçek OWL/RDF veya semantic-web ontolojisi kullanılmaz.

### AI ve graph

Mock AI ücretsiz ve deterministiktir; summary, argumentsFor, argumentsAgainst, possibleRuleConflicts, similarTopics üretir. `AnalysisProvider` arayüzü gerçek LLM sağlayıcısının bağlanacağı sınırdır. Mevcut çıktı LLM üretimi gibi sunulmaz; karar vermez.

Graph ilişkisel tablolardan türetilir. USER/TOPIC/TEAM düğümleri; MEMBER_OF, CREATED, VOTED_ON, COMMENTED_ON, INTERESTED_IN kenarları vardır. Alt konu ve arşivleme oyları ana konuya bağlanır. React Flow ile yakınlaştırma, gezinme, düğüm seçimi, ilişki filtresi ve arama yapılır. Ayrı graph DB yoktur.

### PostgreSQL'e geçiş

`DATABASE_URL` değişkeni SQLAlchemy bağlantı URL'sidir. PostgreSQL için `psycopg[binary]` sürücüsü kurulup `postgresql+psycopg://...` kullanılabilir. SQLite'a özel alan türleri kullanılmaz; foreign key ve unique constraint'ler modeldedir. Mevcut SQLite verilerinin taşınması ve migration bu prototipte otomatik yapılmaz. Çoklu worker'a geçmeden ledger kilit stratejisi değiştirilmelidir.

## Test ve derleme

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm run build
```

Testler izole in-memory SQLite üzerinde çalışır; demo verilerini değiştirmez. Kapsam: tekrar oy API/DB engeli; ilgisiz kullanıcı; normal eşitlik ve çoğunluk; çekimser katılım; %60 sınırı; azınlık ve temsil yokluğu; quorum; blocked policy; uzman sonrası kontrol; ledger bozulması; fiziksel silme olmadan arşivleme; r'nin eşit oyu bozmaması; puan sınırları; alt konu ve DB hedef kısıtları; geçmiş takım; JWT/rol/giriş doğrulama; uzman alanı; ledger yazma/silme endpoint'lerinin yokluğu; kayıtta rol yükseltme engeli; yorum spam'inin puan üretmemesi; konu yaşam döngüsü; kural düzenlemede tekrar kontrol.

## MVP sınırları

Gerçek blockchain, ücretli AI, e-posta doğrulaması, parola sıfırlama, dosya yükleme, bildirim gönderimi ve harici karar yürütme yoktur. Takım/ilgi alanları demo kapsamında kullanıcı tarafından seçilir; üretimde üyelik doğrulaması gerekir. Kullanıcı ve kural yönetimi ekleme/düzenleme odaklıdır; audit ilişkilerini korumak için kullanıcı/kural fiziksel silme sunulmaz. Konu statü enum'unda ARCHIVED bulunur; bu sürüm konu arşivleme için ayrıca iş akışı sunmaz. Mesaj arşivleme tam çalışır. TestClient bağımlılığından bir upstream deprecation uyarısı gelebilir; test başarısını etkilemez.
