# Müşterek

Üniversite topluluğu için geliştirilen akran öğrenme ve katılımcı karar alma web uygulaması.

Kullanıcılar konu önerir, tartışır ve eşit oyla kararlara katılır. Sistem, kurul yetkilerini, etkilenen grubun desteğini ve yönetmelik uygunluğunu kontrol eder. Kurul ve yönetmelik örnekleri eğitim amaçlıdır.

## Teknik altyapı

- Arayüz: React, TypeScript, Vite ve Tailwind CSS
- Sunucu: Python ve FastAPI
- Veritabanı: SQLite ve SQLAlchemy
- Oturum: JWT; parola saklama: Argon2
- Testler: Pytest

## Kurulum ve çalıştırma

Kaynak kodlar, demo hesapları ve ayrıntılı kurulum adımları [peer-decision-system/README.md](peer-decision-system/README.md) dosyasındadır.

İlk kurulum tamamlandıktan sonra Windows üzerinde `Uygulamayi Ac.cmd` dosyasına çift tıklayın. Uygulama varsayılan tarayıcıda `http://localhost:5173` adresinde açılır. Bilgisayar yeniden başlatıldığında aynı dosyayı tekrar çalıştırın.

GitHub deposu kaynak kodları paylaşır. Uygulamanın çevrimiçi çalışması için ayrıca sunucuya kurulması gerekir.

Yerel veritabanı, oturum anahtarı, bağımlılık klasörleri ve günlükler depoya dahil edilmez. Kurulum sırasında örnek veriler demo oluşturma komutuyla hazırlanır.


## Analiz, diyagramlar ve son düzenlemeler

Güncellenmiş dört sayfalık [uygulama raporu](peer-decision-system/docs/Musterek_Guncellenmis_Proje_Raporu.pdf), kullanılan araçları, karar sürecini ve yapılan düzenlemeleri sade bir dille anlatır. Graf, sınıf ilişkileri ve oy verme sekansı görsellerini de içerir.

Uygulamadaki **Analiz ve tasarım** menüsünden problem kanvası, ölçüm/hata analizi ve tasarım diyagramları açılır. **İlişki haritası** ise veritabanındaki güncel kullanıcı, takım, konu, oy ve tartışma ilişkilerini gösterir.

- [Graf ve diyagramları nerede, nasıl kullanıyoruz?](peer-decision-system/docs/diagram-guide.md)
- [Gereksinim–kod–test eşlemesi ve tasarım notları](peer-decision-system/docs/design.md)

Revizyon: GoF Strategy ile yönetmelik değerlendirmesi; ayrı puan ve kayıt defteri servisleri; bilirkişi talebi ve kurul yetkisi düzeltmeleri; kaydedilebilir problem kanvası; sentetik baseline ölçümü; insan onaylı kapsam önerisi. Yerel veriler ve oturum anahtarları paylaşılmaz.
