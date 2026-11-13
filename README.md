# LexGünlük

Mobil uyumlu, ücretsiz yayınlanabilen günlük Yargıtay kararları uygulaması.

## Ne çalışıyor?
- GitHub Actions her gün Türkiye saatiyle 08.15 civarı Yargıtay'ın kamuya açık karar arama arayüzünden **3 gerçek kararı** indirip JSON arşivine eklemeyi dener. Github zamanlayıcısı gecikebilir / görev başarısız olabilir.
- Başlıklar arama konularıdır, karar özeti **iddiasında değildir**. Alıntılar gerçek metinden otomatik seçilir; karar tam metninin ve bağlamının doğrulanması gerekir.
- 3 karar bulunamazsa bulunanlar yayımlanır; hiç bulunamazsa gün değişmiş gibi yapılmaz. Başarısız günün hata kayıtları Actions bölümündedir.
- Beğenilen kararlar cihazın `localStorage` alanında saklanır (başka cihazla senkronize olmaz). LinkedIn taslakları gerçekten getirilen kararların künye ve seçilmiş alıntılarıyla hazırlanır.
- PWA: iPhone Safari > Paylaş > Ana Ekrana Ekle. Android Chrome > Ana ekrana ekle / Uygulamayı yükle.

## GitHub Pages'te ücretsiz yayına alma
1. Bu klasörün **içeriğini** yeni bir GitHub deposuna yükleyin (isterseniz mevcut `lexgunluk` deposunun içine taşıyın). GitHub Pages statik web sayfasının erişimini herkese açar. Gizli müvekkil verisi yüklemeyin.
2. GitHub deposunda `Settings > Pages > Build and deployment > Deploy from a branch > main > /(root)` seçin. Sitenin URL'si `https://KULLANICI.github.io/DEPO/` biçimindedir.
3. `Actions > Günlük Yargıtay Kararları > Run workflow` seçeneğiyle ilk kararları çekin.
4. `Settings > Actions > General > Workflow permissions` alanında gereken durumlarda `Read and write permissions` verin. Bazı hesaplarda organizasyon politikası kısıtlayabilir.
5. İş akışı her gün 05:15 UTC'de tetiklenir; Türkiye'de 08:15'tir. GitHub otomasyon zamanlaması kesin değildir.
6. iPhone Safari ile siteyi açıp paylaş menüsünden `Ana Ekrana Ekle`yi seçin.

## Yerel önizleme
Klasörde `python -m http.server 8000` ardından `http://localhost:8000` açın. `file://` yoluyla çift tıklamak JSON yüklemesini engelleyebilir. İlk kurulumda gerçek karar olmadığı için boş durum görünmesi **bilinçli**dir.

## Önemli sınırlamalar
- Yargıtay karar arama sayfası belgelenmiş / garantili resmî API sunmuyor; web arayüzünün dahili sorgu uç noktaları kullanılıyor. Erişim engeli ve değişiklik olursa otomatik veri akışı durabilir.
- Kararlar her gün **yeni yayımlanmış** kararlar olmak zorunda değil; o gün seçilmiş daha eski kararlar olabilir.
- Farklı cihazlarda ortak favoriler ve hesap girişi için ayrıca bir veritabanı ve kullanıcı hesabı gerekir.
- Her paylaşım taslağı yayımlanmadan önce insan tarafından denetlenmelidir. Hukuki değerlendirmede tam metin esastır.
- Üçüncü taraf açık kaynak araştırmasına göre bu uç noktalar 2026'da çalışıyordu. Bu paket içinde uçtan uca canlı Yargıtay bağlantısı testi bu ortamda yapılmadı.
