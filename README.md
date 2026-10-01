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
