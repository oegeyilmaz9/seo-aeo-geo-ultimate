# SEO skill seti: neyi nerede bulabilirsin?

Normal SEO çalışmalarına devam ediyoruz. HTML içerikleri, title/meta, internal linkler, robots.txt, sitemap.xml, schema, keyword araştırması ve performans kendi işlevlerini koruyor. Aynı kamusal bilgiyi daha kolay okunabilen `.md` dosyalarıyla da sunuyoruz. HTML ve Markdown aynı onaylı kaynak sürümüne dayanır.

## Bilgiye doğrudan git

| İhtiyacın | Doğrudan belge |
| --- | --- |
| Bütün repo içeriğini görmek | [Tam harita](../sitemap.md) |
| Nereden başlayacağını bulmak | [llms.txt](../llms.txt) |
| Tek talebin doğru SEO akışına dönüşmesi | [seo yönlendiricisi](../skills/seo/SKILL.md) |
| Markdown katmanı, gizlilik ve kabul kuralları | [Markdown sözleşmesi](MARKDOWN-DISCOVERY.md) |
| Üretim ve kontrol komutları | [Çalışan başlangıç rehberi](MARKDOWN-QUICKSTART.md) |
| Keyword, intent, kümeler ve cevap sahipliği | [Keyword araştırma protokolü](../skills/seo-research/references/keyword-research-protocol.md) |
| Araştırmayı gerçek karara dönüştürmek | [Keyword karar şablonu](KEYWORD-DECISION-TEMPLATE.md) |
| Yapılan adımı belgelemek | [Çalışma notu şablonu](WORK-NOTE-TEMPLATE.md) |
| Teknik sorumluluklar | [seo-technical](../skills/seo-technical/SKILL.md) |
| Bütün sayfa envanteri ve URL kararları | [seo-sitemap](../skills/seo-sitemap/SKILL.md) |
| Kaynaklar ve olgu doğruluğu | [seo-content](../skills/seo-content/SKILL.md) |
| Konu haritaları ve soru→cevap erişimi | [seo-architecture](../skills/seo-architecture/SKILL.md) |
| Gerçek yayın kontrolü | [Canlı yayın protokolü](LIVE-RELEASE-VERIFICATION.md) |

## Bir sitede nasıl çalışır?

1. Bütün uygun kamusal sayfalar belirlenir; dışarıda bırakılan adreslerin nedeni özel kayıtta tutulur.
2. Aynı kaynak içeriğinden gerçek cevapları taşıyan `.md` belgeleri üretilir.
3. `llms.txt → sitemap.md → konu haritası → cevap.md` bağlantıları oluşturulur. Fiyat arayan doğrudan fiyat/koşul cevabına, kurulum arayan kurulum adımlarına gider.
4. robots.txt `#` yorumları ve sitemap.xml XML yorumları, bu gerçek adreslere kısa yol tarifi verir. Mevcut tarama kuralları ve XML kayıtları korunur. llms.txt içinde iki kısa gezinme cümlesi bulunur.
5. Yerel kontrol, normal yayın süreci ve bütün beyan edilen kaynakların canlı kontrolü ayrı yapılır. İçerik değiştiğinde HTML, Markdown ve haritalar birlikte yenilenir.

Yorumları okuyan bir LLM için mesaj: “Bilgi arıyorsan haritadan ilgili Markdown cevabına git. Kaynaklarını kullan; cevap yoksa eksik olduğunu belirt.” Standart parserlar yorumları komut saymaz; her motorun bu katmanı kullanacağına dair garanti yoktur.

## Her adımın belgesi

Araştırma, karar, uygulama ve doğrulama `.md` belgelerinde tutulur. Özel `index.md`, her belgenin adresini, durumunu ve sonucunu gösterir. Ham JSON/CSV/ölçüm kanıtları ve native protokoller korunur; kamusal bilgi katmanına özel raporlar veya erişime kapalı içerik taşınmaz.

Keyword tarafında talep verisi, kullanıcı niyeti, SERP ve içerik boşlukları incelenir. Her anlamlı soru tek canonical HTML sahibine ve gerçek Markdown cevap bölümüne bağlanır. Eksik veri uydurulmaz; belirsiz/planlanan adres gerçek cevap gibi sunulmaz.

## Bu reponun haritası

Repo zaten Markdown belgeleri içerdiği için bunları yeniden kopyalamıyoruz. Tam harita, 27 skillin giriş belgelerine, kendi referanslarına, protokollere ve araç/örnek kaynaklarına doğrudan gider. Kod, şema, görsel, test fixture ve workflow dosyaları kendi formatında kalır. Haritaların tam kapsamı, değişikliklerden sonra yeniden üretilip CI içinde kontrol edilir.

GitHub üstündeki `robots.txt` yönetimi bize ait değildir. Native yönlendirme kuralı, kendi sitemizde çalışırken uygulanır; repo yayınlamak bir müşteri sitesini deploy etmek anlamına gelmez.
