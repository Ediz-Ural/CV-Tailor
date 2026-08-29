# PROJECT_CONTEXT.md

Bu dosya projenin tüm kararlarını ve mimarisini içeren referans bilgi dosyasıdır.

---

## 1. Ürün Özeti

Kullanıcının verdiği bir iş ilanına göre, kullanıcının profil havuzundan en uygun
deneyim/proje/yetkinlikleri seçip o ilana özel optimize edilmiş bir CV üreten,
çok kullanıcılı bir web uygulaması.

**Çekirdek değer önerisi:** Tek sabit CV yerine; PDF + GitHub + manuel girişten
beslenen bir "yetkinlik havuzu" tutulur. Her ilan için bu havuzdan ilana en uygun
parçalar seçilir, ilana göre yeniden ifade edilir (uydurma bilgi eklemeden) ve
PDF olarak render edilir.

**Hedef pazar:** Türkiye. Ancak Türkiye'de iş ilanları sıkça İngilizce (özellikle
teknoloji/GenAI rolleri), bazen Türkçe, bazen karma dildedir. Sistem hem Türkçe
hem İngilizce ilanları birinci sınıf işler.

---

## 2. Dil Desteği (Türkçe + İngilizce)

Türkiye pazarında ilanlar İngilizce, Türkçe veya karma olabilir. Bu yüzden:

- **İlan parse etme:** Hem İngilizce hem Türkçe (ve karma dilli) ilanlardan
  gereksinim/skill/anahtar terim çıkarılır.
- **CV üretme:** Çıktı dili ilanın diline göre seçilir — İngilizce ilana İngilizce
  CV, Türkçe ilana Türkçe CV. Karma ilanlarda baskın dil esas alınır.
- **Karma içerik:** CV'ler ve ilanlar karma dilli olabilir (Türkçe açıklama +
  İngilizce teknik terim). Teknik terimler (ör. "machine learning", "FastAPI")
  çevrilmeden korunur.
- **Havuz (pool) içeriği:** Kullanıcının deneyim/proje parçaları farklı dillerde
  girilmiş olabilir; CV üretiminde hedef ilana uygun dile uyarlanır.

---

## 3. Kapsam

### Kapsam İÇİ
- Kullanıcı iş ilanını **metin yapıştırarak** veya **URL vererek** girer.
  URL verildiğinde tek bir sayfa fetch edilir (kullanıcının açık isteğiyle, tek sayfa
  → scraping değil). LinkedIn / Kariyer.net dahil herhangi bir ilan URL'si parse edilebilir.
- Profil havuzu üç kaynaktan dolar: **PDF CV yükleme**, **GitHub OAuth analizi**, **manuel giriş**.
- İlana göre havuzdan seçim + CV tailoring + ATS uyum skoru + before/after.
- **Çok kullanıcılı** (multi-tenant).
- **GitHub analizi MVP'nin parçasıdır.**
- KVKK uyumu baştan tasarıma dahildir.

### Kapsam DIŞI (şimdilik)
- LinkedIn / Kariyer.net / secretcv gibi sitelerden **otomatik toplu ilan tarama** (scraping).
  Yasal/teknik olarak riskli; bilinçli olarak kapsam dışı.
- Otomatik ilan toplama (İŞKUR / RSS / link havuzu) → ileride opsiyonel eklenti, MVP değil.
- Türkiye dışı pazarlar.

### Kapsam gerekçesi
Değerin büyük kısmı CV tailoring tarafında; otomatik scraping yasal risk taşır ve
değerin küçük kısmını oluşturur. "Kullanıcı ilanı verir, sistem optimize eder"
akışı hızlı çalışır hale gelir ve yasal sorunu yoktur.

---

## 4. Teknoloji Yığını

| Katman | Seçim | Not |
|---|---|---|
| Backend | **FastAPI** (Python) | Async, pydantic v2, structured outputs |
| Veritabanı | **PostgreSQL** | Multi-tenant; SQLite yetersiz (concurrency) |
| Vektör arama | **pgvector** (Postgres içinde) | Ayrı vektör servisi yok; multi-user filtreleme kolay |
| Orkestrasyon | **LangGraph** | İki ayrı graph (bkz. §7) |
| LLM | **API (OpenAI/Anthropic)** | MVP'de API; ileride vLLM self-host'a geçiş mümkün |
| Embedding | **Çok dilli model** (multilingual-e5 / BGE-m3) | Saf İngilizce model Türkçe'de zayıf |
| PDF Render | **Typst** (CLI, subprocess) | LaTeX değil — hızlı (ms seviyesi), küçük imaj, tek binary |
| Auth | **JWT** + kullanıcı tablosu | Multi-tenant |
| Arka plan işleri | **Celery / RQ** (veya başlangıçta FastAPI BackgroundTasks) | GitHub sync ve render kuyruğu için |
| Frontend | **React + TypeScript + Vite** | Bkz. §9 tasarım sistemi |
| Frontend stil | **Tailwind CSS + shadcn/ui + Framer Motion** | Dark-mode-first |

### Render notu (Typst)
- Typst CLI subprocess ile çağrılır; tek binary, container imajı küçük kalır.
- Render ~10–50ms; darboğaz LLM çağrılarıdır (~10–30sn), render değil.
- Render'lar senkron HTTP içinde değil, arka plan kuyruğunda çalışır.
- Her render izole geçici dizinde + timeout ile (bozuk girdi sonsuz döngüye sokmasın).
- "Jake's Resume" tarzı CV şablonu Typst'e taşınır.

### Türkçe'ye özgü teknik kurallar
- ATS keyword eşleşmesi **exact string match ile yapılmaz** — Türkçe sondan eklemeli
  ("geliştirici / geliştirme / geliştiren" aynı kök, exact match tutmaz).
- Çözüm: **lemmatization (Zemberek veya stanza)** veya **embedding tabanlı semantic match**.
- CV'ler ve ilanlar karma dilli olabilir (TR açıklama + EN teknik terim).

---

## 5. Mimari Genel Bakış

```
[React/TS Frontend] ── REST ──> [FastAPI Backend]
                                     │
                 ┌───────────────────┼────────────────────┐
                 │                   │                    │
          [PostgreSQL+pgvector]  [LangGraph Pipelines]  [Typst Render Worker]
                                     │                    (kuyruk)
                          ┌──────────┴──────────┐
                   [Graph 1: Havuz Doldur]  [Graph 2: CV Üret]
                          │
                  [GitHub OAuth API] [PDF Parser] [LLM API]
```

---

## 6. Veri Modeli (multi-tenant — her tabloda user_id)

Satır seviyesi izolasyon esastır. Her sorgu user_id ile filtrelenir.

```sql
users (
  id, email, hashed_password, created_at,
  kvkk_consent_at            -- KVKK açık rıza zamanı
)

profiles (
  id, user_id FK,
  full_name, contact, education[], personal_info
)

pool_items (                 -- sistemin kalbi
  id, user_id FK,
  source        -- enum: pdf | github | manual
  type          -- enum: experience | project | skill
  raw_content,
  title,
  tags[],                    -- alan etiketleri (ör: deep-learning, web-dev)
  technologies[],
  language,                  -- içeriğin dili (tr | en | mixed)
  embedding     vector,      -- pgvector, semantic seçim için
  verified_by_user bool,     -- kullanıcı onayladı mı (GitHub/PDF çıktısı için)
  created_at
)

jobs (
  id, user_id FK,
  source_url, raw_text,
  detected_language,         -- ilanın dili (tr | en | mixed) → CV çıktı dilini belirler
  parsed_requirements_json,  -- JobParser çıktısı
  created_at
)

generated_cvs (
  id, user_id FK, job_id FK,
  selected_pool_item_ids[],
  output_language,           -- üretilen CV'nin dili
  typst_source,              -- üretilen Typst kaynağı
  pdf_path,
  ats_score,
  created_at
)

github_connections (
  id, user_id FK,
  github_username,
  access_token_encrypted,    -- asla plaintext
  last_synced
)
```

---

## 7. LangGraph Pipeline'ları (iki ayrı graph)

### Graph 1 — Havuz Doldurma (profil oluşturma/güncelleme tetikler)
1. **PDFParser** — yüklenen CV'yi ayrıştırır (deneyim, eğitim, skill).
2. **GitHubAnalyzer** — (PDFParser ile paralel) repo'ları çeker, filtreler, README'leri LLM ile etiketler.
3. **ItemExtractor** — hepsini `pool_items` formatına normalize eder, içerik dilini tespit eder, embedding üretir.
4. Çıktı `verified_by_user=false` kaydedilir; kullanıcı onay ekranında onaylayınca `true` olur.

### Graph 2 — CV Üretme (ilan girilince tetikler)
1. **JobParser** — ilanın dilini tespit eder; ilandan structured gereksinim çıkarır (zorunlu/tercihen skill, deneyim yılı, anahtar terimler). Türkçe ve İngilizce ilanları işler. JSON şema ile.
2. **Selector** — havuzdan en alakalı **verified** item'ları seçer (semantic + LLM). Dil farkı seçimi engellemez (örn. EN ilana TR havuz öğesi de seçilebilir).
3. **CVTailor** — seçilenleri ilana göre yeniden ifade eder ve **ilanın diline uyarlar** (EN ilan → EN CV, TR ilan → TR CV). Teknik terimler korunur. **Uydurma bilgi eklemez** — sadece var olanı öne çıkarır/yeniden ifade eder.
4. **Evaluator** — ATS uyum skoru, eksik keyword listesi, before/after diff.
5. **TypstRenderer** — Typst şablonuna basar, PDF üretir (arka plan kuyruğunda).

---

## 8. GitHub Entegrasyonu

- **OAuth** ile bağlanma; kullanıcı token'ı `github_connections`'da **şifreli** saklanır.
- Çekerken filtrele: **fork olmayanlar**, en az birkaç commit'i olanlar, README'si olanlar.
  Boş / fork / tutorial repo'ları elenir — yoksa havuz çöple dolar.
- Sinyal kaynağı: repo adı tek başına güvenilmez. **README içeriği + dil dağılımı +
  commit sayısı + orijinal mi fork mu** birlikte değerlendirilir.
- Her repo için README + diller + topics → LLM ile structured çıkarım:
  `{ alan, teknolojiler, kısa_açıklama }`.
- Çıkanlar `verified_by_user=false` → kullanıcıya "şunlar bulundu, hangileri eklensin?" onayı sunulur.
- **Doğruluk/etik:** Otomatik çıkarılan hiçbir şey kullanıcı onayı olmadan CV'ye girmez
  (mülakatta yanlış/abartı bilgi riskini önler).
- Rate limit: authenticated istek 5000/saat (kullanıcı token'ı). Sync background job olarak çalışır.

---

## 9. Frontend & Tasarım Sistemi

**Genel yön:** Temiz SaaS yapısal iskelet (Linear/Vercel tipi) + cesur tipografi
(premium/yenilikçi his) + monospace aksanlar (kod, skill etiketleri, pipeline logları
için AI-native karakter). **Dark-mode-first.**

### Stack
- React + TypeScript + Vite
- Tailwind CSS
- shadcn/ui (komponent temeli)
- Framer Motion (akıcı micro-interaction)

### Tasarım İlkeleri
- Dark-mode-first; light mode ikincil ama desteklenir.
- Yoğun veri ekranları (profil, havuz, ilan girişi) → temiz/yapısal, az gürültü.
- Vitrin anları (CV sonucu, ATS skoru) → büyük tipografi, güçlü kontrast.
- Kod/skill/teknoloji etiketleri ve pipeline logları → monospace.
- Bol whitespace, ince borderlar, subtle micro-interaction. Aşırı gradient/glow yok.
- Arayüz Türkçe ve İngilizce içeriği aynı ekranda gösterebilir (i18n hazır olmalı).

### Tasarım Tokenları (başlangıç)
- Tipografi: sans-serif gövde + monospace aksan (ör. Inter + JetBrains Mono / Geist + Geist Mono).
- Ölçek: büyük başlıklar (vitrin), normal gövde 14–16px, mono etiketler 12–13px.
- Renk: koyu nötr zemin + tek bir canlı aksan rengi (durum renkleri: success/warning/danger ayrı).
- Köşe yarıçapı: orta (kartlar biraz daha yuvarlak).
- Animasyon: kısa, amaçlı geçişler; sayfa/komponent giriş animasyonları subtle.

### Üretim notu
Görsel yön/mockup üretmek için Claude Design (veya inline mockup) kullanılabilir;
production React/TS kodunu Claude Code + Codex yazar.

---

## 10. KVKK / Gizlilik

Çok kullanıcılı + PDF CV + GitHub + kişisel bilgi → kişisel veri işleniyor.

- Kayıtta **açık rıza metni** + onay zamanı (`kvkk_consent_at`).
- **"Hesabımı sil"** akışı → tüm `user_id` satırları cascade silinir.
- GitHub token'ı **şifreli** saklanır (asla plaintext).
- **Aydınlatma metni** sunulur.
- Veri saklama/silme politikası baştan tasarıma dahil.

---

## 11. Önerilen Yapım Sırası (yüksek seviye)

1. **İskelet:** FastAPI + Postgres/pgvector + JWT auth + multi-tenant şema + profil CRUD.
2. **Havuz doldurma:** PDF parse + manuel giriş → ardından GitHub OAuth + analiz.
3. **CV üretme pipeline'ı:** JobParser → Selector → CVTailor → Evaluator → TypstRenderer.
4. **Frontend:** ekranlar (auth, profil/havuz, ilan girişi, CV sonucu).
5. **KVKK akışları:** rıza, aydınlatma, hesap silme.

---

## 12. Sözlük / Kısaltmalar

- **Havuz (pool):** Kullanıcının tüm deneyim/proje/skill parçalarının kaynak-etiketli koleksiyonu.
- **Tailoring:** İlana göre havuzdan seçim + yeniden ifade (uydurma yok), ilanın diline uyarlama.
- **ATS:** Applicant Tracking System — keyword/uyum skoru bu sisteme göre optimize edilir.
- **verified_by_user:** Otomatik çıkarılan bir havuz öğesinin kullanıcı tarafından onaylanma durumu.
- **detected_language / output_language:** İlanın tespit edilen dili ve buna göre seçilen CV çıktı dili.
