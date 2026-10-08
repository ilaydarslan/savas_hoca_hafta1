# Graf ve diyagram kullanım rehberi

Uygulamayı açıp giriş yapın. Sol menüde **Analiz ve tasarım → Tasarım diyagramları** bölümüne gidin. Dar ekranda menü sol üstteki düğmeden açılır. Aşağıdaki localhost bağlantıları yalnız uygulama çalışan bilgisayarda açılır.

| Görünüm | Nerede? | Ne anlatır? | Koddaki karşılığı |
|---|---|---|---|
| Canlı ilişki grafı | [İlişki haritası](http://localhost:5173/graph) | Kim hangi takımda, hangi konuyu açtı, oyladı veya tartıştı? | `routers/api.py:graph`, `pages/System.tsx:Graph` |
| Sınıf diyagramı | [Sınıflar](http://localhost:5173/engineering?tab=design&diagram=classes) | User, Topic, Vote, ExpertReview, Rule ve RuleCheck arasındaki ilişkiler ve çokluklar | `models/__init__.py`, `pages/Engineering.tsx` |
| Kullanım durumları | [Use case](http://localhost:5173/engineering?tab=design&diagram=usecases) | Katılımcı, uzman, yönetici ve kurul üyesi hangi işlemleri başlatır? | `services/authority.py`, `routers/api.py` |
| Sekanslar | [Sekans](http://localhost:5173/engineering?tab=design&diagram=sequence) | Oy, sonuçlandırma ve uzman görüşünde çağrılar hangi sırayla yapılır? | `components/SequenceDiagram.tsx`, `services/decisions.py` |
| Strategy / bağımlılık | [GoF Strategy](http://localhost:5173/engineering?tab=design&diagram=strategy) | Politika motoru değiştirilebilir algoritmaları ortak sözleşmeyle nasıl çağırır? | `services/policy.py` |
| Durum diyagramı | [Durum akışı](http://localhost:5173/engineering?tab=design&diagram=state) | PROPOSED → VOTING → ACCEPTED / REJECTED; hangi koşulda açık kalır? | `start_voting`, `close_vote`, `topic_json` |

## Canlı graf ile tasarım modeli arasındaki fark

İlişki haritası `GET /api/v1/graph` yanıtından üretilir. Düğümler kullanıcı, takım ve konudur. Kenarlar MEMBER_OF, CREATED, VOTED_ON, COMMENTED_ON ve INTERESTED_IN ilişkilerini taşır. Bir düğüme tıklayarak komşularını ve ilişki türünü filtreleyebilirsiniz. Bu grafik kayıtları görselleştirir; oy hakkını hesaplayan mekanizma değildir. Yetki kontrolleri sunucudadır. Alt konu ve arşivleme oyları bu özet görünümde ana konuya bağlanır.

Sınıf, kullanım durumu, sekans ve durum çizimleri mevcut koddan çıkarılmış tasarım modelleridir. Yeni işlem yapıldığında şekilleri değişmez; alan modeli veya akış değişirse geliştirici bu çizimleri de günceller. Çizimlerin altında metin karşılıkları ve sınırlar vardır. Sınıf ve kullanım durumu görünümleri okunabilirlik için sadeleştirilmiştir; bütün tablo sütunlarını veya her uç noktayı göstermez.

## Üç sekansı sunarken

1. **Oy kullanma:** kullanıcı tercihini API'ye yollar; oturum, kurul/katılım yetkisi, oylamanın açık olması ve tekrar oy denetlenir. Vote ile VOTE_CAST ledger girdisi aynı transaction içinde kaydedilir. Başarısızlık yollarında 403/409 sonuçları açıklanır.
2. **Oylamayı sonuçlandırma:** katılım üçten azsa oylama açık kalır. Çoğunluk sağlansa bile etkilenen grubun desteği yetersizse MINORITY_CONFLICT oluşur. Kabul edilen konuda kurallar, puan ve kayıt defteri güncellenir. Kabul ile uygulanabilirlik ayrı kavramlardır.
3. **Bilirkişi görüşü:** EXPERT rolü ve etiket eşleşmesi denetlenir. Yeni görüş bekleyen uzman talebini çözer; ACCEPTED konuda politika yeniden değerlendirilir. Azınlık çatışması ve oylar uzman tarafından değiştirilemez.

Dikey çizgiler bileşenlerin yaşam çizgileridir. Oklar çağrıları, kesikli oklar dönüşleri gösterir. Koşul etiketli adımlar aynı istekte mutlaka birlikte çalışmaz. Bu bir canlı ağ kaydı değildir. Küçük ekranda şema yatay kaydırılabilir; altında her adımın tam metni bulunur.

## GoF gerçekten nerede çalışıyor?

`PolicyEngine.evaluate()` kural türünü alıp `RuleStrategy.fails(context, threshold)` sözleşmesini uygulayan sınıfı çağırır: HighSupport, MinoritySupport, Quorum, ExpertReviewRequired veya DescriptionLength. Stratejiler veritabanı ve HTTP bilmeden değerlendirme yapar. Veriler `PolicyContext` içinde bir kez hazırlanır. Yeni koşul algoritması motorun değerlendirme kodunu değiştirmeden kayıt tablosuna eklenebilir; HTTP giriş şemasında izin verilen türler ayrıca güncellenir.

Bağımlılık enjeksiyonu, sorumluluk ayrımı ve Registry ayrı GoF kalıplarıymış gibi sayılmıyor. Durum akışı çizilmiş olması da GoF State sınıflarının uygulandığı anlamına gelmez.

## Diğer analiz ekranları

**Problem kanvası** iş hedefi, karar, görev, veri, metrik, baseline, kısıt ve riskleri saklar. Yalnız yönetici düzenler; değişiklik ledger'a kaydolur. **Ölçüm ve hata analizi** aynı 32 sentetik örnekte sabit referansı ve Türkçe anahtar kelime yöntemini çalıştırır. Makro F1, sınıf sonuçları, karışıklık matrisi ve hatalar gerçekten hesaplanır. Bu örnekler bağımsız saha testi değildir; iyi skor, gerçek kullanıcı başarısı iddiasına dönüştürülmez.

## Son kontrol

58 backend testi, TypeScript denetimi ve üretim derlemesi doğrulanmıştır. Yerel ekran kontrolünde kanvas kaydı, ölçüm çalıştırma, kapsam önerisi ve diyagram yönlendirmeleri kontrol edilmiştir. Frontend eski istek yanıtlarının yeni konuya karışmasını önler; kanvas taslağı ve ölçüm sonuçları analiz sekmeleri arasında korunur.
