# IŞ PAKETLERI (IS_PAKETLERI.md)

Bu dosya, `PROJECT_CONTEXT.md` içindeki kararlara dayanarak projenin **adım adım nasıl
inşa edileceğini** tanımlar. Her iş paketi (İP) bağımsız test edilebilir bir çıktı üretir
ve bir öncekinin üzerine inşa edilir. Sıra, bağımlılıkları minimize edecek şekilde dizilmiştir.

**Okuma sırası:** Önce `PROJECT_CONTEXT.md` (ne ve neden), sonra bu dosya (nasıl ve hangi sırayla).

**Kısaltmalar:** İP = İş Paketi. DoD = Definition of Done (bitti sayılma kriteri).

---

## Faz 0 — Proje İskeleti ve Geliştirme Ortamı

### İP-0.1 — Repo ve monorepo yapısı
- [ ] Git repo başlat (`git init`), `.gitignore` (Python, Node, `.env`, `__pycache__`, `node_modules`, `dist`).
- [ ] Klasör yapısı:
  ```
  /backend        FastAPI uygulaması
  /frontend       React + TS + Vite
  /infra          docker-compose, Dockerfile'lar
  /docs           PROJECT_CONTEXT.md, IS_PAKETLERI.md
  ```
- [ ] `README.md` — kısa kurulum talimatı.
- **DoD:** Repo klonlanıp klasör yapısı görülebiliyor.

### İP-0.2 — Yerel altyapı (Docker Compose)
- [ ] `docker-compose.yml`: PostgreSQL (pgvector imajı: `pgvector/pgvector`), backend, frontend.
- [ ] `.env.example` dosyası (DB URL, JWT secret, LLM API key, GitHub OAuth client id/secret placeholder).
- [ ] PostgreSQL'de `CREATE EXTENSION vector;` migration'ı.
- **DoD:** `docker compose up` ile Postgres + pgvector ayağa kalkıyor.

### İP-0.3 — Backend temel kurulum
- [ ] Python proje (poetry veya uv), bağımlılıklar: `fastapi`, `uvicorn`, `pydantic v2`,
  `sqlalchemy`/`sqlmodel`, `alembic`, `psycopg`, `pgvector`, `python-jose`/`pyjwt`, `passlib[bcrypt]`.
- [ ] `app/main.py` — FastAPI app + `/health` endpoint.
- [ ] Ayar yönetimi (`pydantic-settings` ile `.env` okuma).
- [ ] Alembic migration altyapısı.
- **DoD:** `GET /health` → `200 {"status":"ok"}`.

### İP-0.4 — Frontend temel kurulum
- [ ] Vite + React + TypeScript scaffold.
- [ ] Tailwind CSS + shadcn/ui kurulumu, dark-mode-first tema.
- [ ] Tasarım tokenları (§9): renk paleti, tipografi (Inter + JetBrains Mono), radius.
- [ ] Temel layout (sidebar/topbar iskeleti) + API client (fetch/axios + base URL).
- **DoD:** `npm run dev` ile boş ama temalı bir uygulama açılıyor; backend `/health`'e istek atabiliyor.

---

## Faz 1 — Kimlik Doğrulama ve Çok Kullanıcılı Şema

### İP-1.1 — Veritabanı şeması (multi-tenant)
- [ ] §6'daki tüm tablolar için SQLAlchemy modelleri + Alembic migration:
  `users`, `profiles`, `pool_items`, `jobs`, `generated_cvs`, `github_connections`.
- [ ] `pool_items.embedding` → `vector` tipi (boyut: seçilen embedding modeline göre, ör. 1024).
- [ ] Her tabloda `user_id` FK + index. pgvector için ivfflat/hnsw index (sonra eklenebilir).
- **DoD:** Migration uygulanıyor, tablolar oluşuyor.

### İP-1.2 — Auth (JWT)
- [ ] Kayıt (`POST /auth/register`): email + parola (bcrypt hash) + **KVKK rıza zamanı** (`kvkk_consent_at`).
- [ ] Giriş (`POST /auth/login`): JWT access token döner.
- [ ] `get_current_user` dependency — her korumalı endpoint'te `user_id` çıkarılır.
- [ ] **Tenant izolasyon kuralı:** Tüm sorgular `user_id` ile filtrelenir (yardımcı katman/dependency).
- **DoD:** Kayıt + giriş çalışıyor; token ile korumalı bir test endpoint'i erişilebiliyor.

### İP-1.3 — Profil CRUD
- [ ] `profiles` için CRUD: `full_name`, `contact`, `education[]`, `personal_info`.
- [ ] Sadece kendi profiline erişim (izolasyon testi).
- **DoD:** Kullanıcı kendi profilini oluşturup güncelleyebiliyor.

### İP-1.4 — Frontend auth akışı
- [ ] Kayıt + giriş ekranları, KVKK onay checkbox'ı (+ aydınlatma metni linki).
- [ ] Token saklama + auth guard (korumalı route'lar).
- [ ] Profil görüntüleme/düzenleme ekranı.
- **DoD:** Uçtan uca kayıt → giriş → profil düzenleme tarayıcıdan çalışıyor.

---

## Faz 2 — Havuz Doldurma (Graph 1)

> Bu faz §7 Graph 1'i hayata geçirir. Embedding ve LLM altyapısı burada kurulur.

### İP-2.0 — LLM ve Embedding altyapısı (ortak servis katmanı)
- [ ] LLM çağrı sarmalayıcı (provider-agnostik arayüz; structured output / JSON şema desteği).
- [ ] Çok dilli embedding servisi (multilingual-e5 veya BGE-m3) — metin → vektör.
- [ ] Dil tespiti yardımcı fonksiyonu (tr | en | mixed).
- [ ] Retry + timeout + hata yönetimi.
- **DoD:** Bir metin verince embedding vektörü ve JSON structured çıktı alınabiliyor.

### İP-2.1 — Manuel havuz girişi (en basit kaynak, önce bu)
- [ ] `pool_items` CRUD: `type` (experience|project|skill), `title`, `raw_content`, `tags[]`, `technologies[]`.
- [ ] Kayıtta `source=manual`, dil tespiti + embedding üretimi otomatik.
- [ ] Manuel girişler `verified_by_user=true` (kullanıcı zaten kendi girdi).
- **DoD:** Kullanıcı manuel öğe ekleyebiliyor, embedding DB'ye yazılıyor.

### İP-2.2 — PDF CV parse (PDFParser node)
- [ ] PDF yükleme endpoint'i (dosya boyutu/limit kontrolü).
- [ ] PDF metin çıkarımı (`pypdf`/`pdfplumber`) + LLM ile structured çıkarım: deneyim, eğitim, skill.
- [ ] Çıkanlar `pool_items` formatına normalize → `source=pdf`, `verified_by_user=false`.
- **DoD:** Bir PDF CV yüklenince havuza aday öğeler (onaysız) düşüyor.

### İP-2.3 — GitHub OAuth + analiz (GitHubAnalyzer node)
- [ ] GitHub OAuth akışı; token `github_connections`'da **şifreli** saklanır (asla plaintext).
- [ ] Repo çekme + **filtreleme**: fork olmayan, commit'i olan, README'si olan repolar (§8).
- [ ] Her repo: README + diller + topics → LLM structured çıkarım `{alan, teknolojiler, kısa_açıklama}`.
- [ ] Çıkanlar `pool_items` → `source=github`, `verified_by_user=false`.
- [ ] **Arka plan job** olarak çalışır (rate limit: 5000/saat); senkron HTTP'yi bloklamaz.
- **DoD:** Kullanıcı GitHub bağlayınca, filtrelenmiş repolardan aday öğeler havuza düşüyor.

### İP-2.4 — ItemExtractor + onay akışı
- [ ] PDF + GitHub çıktılarını tek formata normalize eden node (dil tespiti + embedding).
- [ ] **Onay ekranı:** "Şunlar bulundu, hangileri eklensin?" → seçilenler `verified_by_user=true`.
- [ ] Reddedilenler silinir/pasifleştirilir.
- **DoD:** Otomatik çıkarılan hiçbir öğe kullanıcı onayı olmadan CV'ye girmiyor (etik kural).

### İP-2.5 — Graph 1 orkestrasyonu (LangGraph)
- [ ] PDFParser ∥ GitHubAnalyzer (paralel) → ItemExtractor → onay.
- [ ] Profil oluşturma/güncelleme bu graph'ı tetikler.
- **DoD:** Tek tetikleme ile PDF + GitHub paralel işlenip havuz onaya hazır geliyor.

### İP-2.6 — Frontend: Havuz ekranı
- [ ] Havuz listesi (kaynak etiketli: pdf/github/manual; tip filtreleri).
- [ ] Manuel ekleme formu; onay bekleyen öğeler için onay/ret UI.
- [ ] GitHub bağla butonu + sync durumu (mono pipeline logları stili).
- **DoD:** Kullanıcı havuzunu üç kaynaktan doldurup yönetebiliyor.

---

## Faz 3 — CV Üretme Pipeline'ı (Graph 2)

> §7 Graph 2. Sistemin çekirdek değeri burada.

### İP-3.1 — İlan girişi + JobParser
- [ ] İlan girişi: **metin yapıştır** veya **URL** (URL verilince tek sayfa fetch — scraping değil).
- [ ] JobParser node: ilan dilini tespit (`detected_language`) + structured gereksinim çıkarımı
  (zorunlu/tercihen skill, deneyim yılı, anahtar terimler) — TR + EN + karma, JSON şema ile.
- [ ] `jobs` tablosuna kaydet.
- **DoD:** İlan yapıştır/URL ver → dili tespit edilmiş, structured gereksinimler JSON olarak elde.

### İP-3.2 — Selector (semantik + LLM seçim)
- [ ] İlan gereksinimleri ↔ havuzdaki **verified** `pool_items` arasında pgvector semantic arama.
- [ ] LLM ile en alakalı item seçimi/sıralaması. Dil farkı seçimi engellemez (EN ilana TR öğe seçilebilir).
- [ ] Türkçe için **exact string match yok** — lemmatization (Zemberek/stanza) veya semantic match.
- **DoD:** Bir ilana karşı havuzdan en alakalı öğeler (id listesi + skor) dönüyor.

### İP-3.3 — CVTailor
- [ ] Seçilen öğeleri ilana göre **yeniden ifade** et + **ilanın diline uyarla** (EN→EN, TR→TR).
- [ ] Teknik terimler korunur (çevrilmez). **Uydurma bilgi eklemez** — sadece var olanı öne çıkarır.
- [ ] `output_language` belirlenir, tailor edilmiş içerik üretilir.
- **DoD:** Seçilen öğelerden ilana özel, doğru dilde, uydurmasız CV içeriği üretiliyor.

### İP-3.4 — Evaluator (ATS skoru)
- [ ] ATS uyum skoru (semantic/lemmatize keyword eşleşmesi — Türkçe exact match değil).
- [ ] Eksik keyword listesi + before/after diff.
- **DoD:** Üretilen CV için ATS skoru, eksik keyword'ler ve before/after çıktısı var.

### İP-3.5 — TypstRenderer + render kuyruğu
- [ ] "Jake's Resume" tarzı şablon Typst'e taşınır.
- [ ] Typst CLI subprocess ile çağrılır; **izole geçici dizin + timeout**.
- [ ] Render **arka plan kuyruğunda** (Celery/RQ veya başta BackgroundTasks), senkron HTTP'de değil.
- [ ] Çıktı `generated_cvs`'e: `typst_source`, `pdf_path`, `selected_pool_item_ids[]`, `ats_score`, `output_language`.
- **DoD:** Pipeline sonunda indirilebilir bir PDF üretiliyor.

### İP-3.6 — Graph 2 orkestrasyonu (LangGraph)
- [ ] JobParser → Selector → CVTailor → Evaluator → TypstRenderer zinciri.
- [ ] İlan girişi bu graph'ı tetikler; uzun süren adımlar (LLM ~10–30sn) için durum/progress takibi.
- **DoD:** İlan ver → uçtan uca optimize PDF CV + ATS skoru otomatik üretiliyor.

### İP-3.7 — Frontend: İlan girişi + CV sonucu
- [ ] İlan giriş ekranı (metin/URL toggle), pipeline ilerleme göstergesi (mono log stili).
- [ ] **Vitrin ekranı** (§9): büyük tipografi ile ATS skoru, before/after, seçilen öğeler, PDF indir/önizleme.
- **DoD:** Kullanıcı ilan verip sonucu görsel olarak güçlü bir ekranda görüp PDF indirebiliyor.

---

## Faz 4 — KVKK / Gizlilik Akışları

### İP-4.1 — Rıza ve aydınlatma
- [ ] Kayıtta açık rıza metni + `kvkk_consent_at` (İP-1.2'de başlatıldı, burada tamamlanır).
- [ ] Aydınlatma metni sayfası.
- **DoD:** Rıza zamanı kaydediliyor, aydınlatma metni erişilebilir.

### İP-4.2 — Hesap silme (cascade)
- [ ] "Hesabımı sil" akışı → tüm `user_id` satırları cascade silinir (tüm tablolarda).
- [ ] GitHub token + üretilen PDF dosyaları da temizlenir.
- **DoD:** Hesap silinince kullanıcıya ait hiçbir veri kalmıyor (doğrulama testi).

### İP-4.3 — Veri saklama/güvenlik kontrolleri
- [ ] GitHub token şifreleme doğrulaması (asla plaintext logu/DB'de).
- [ ] Veri saklama/silme politikasının kod ile uyumu.
- **DoD:** Güvenlik kontrol listesi geçiyor.

---

## Faz 5 — Sağlamlaştırma ve Yayın

### İP-5.1 — i18n (TR/EN arayüz)
- [ ] Frontend i18n altyapısı; TR + EN içerik aynı ekranda gösterilebilir.
- **DoD:** Arayüz dili değiştirilebiliyor, karma içerik düzgün gösteriliyor.

### İP-5.2 — Test ve kalite
- [ ] Backend birim/entegrasyon testleri (auth izolasyonu, parser'lar, pipeline node'ları).
- [ ] Tenant izolasyon testleri (bir kullanıcı diğerinin verisine erişemez).
- [ ] Pipeline için altın örnek (golden) testler: örnek ilan → beklenen seçim/skor.
- **DoD:** CI'da testler geçiyor.

### İP-5.3 — Gözlemlenebilirlik ve dağıtım
- [ ] Yapısal loglama, pipeline adım süreleri, hata izleme.
- [ ] Üretim Dockerfile'ları, ortam değişkenleri, dağıtım dokümanı.
- **DoD:** Uygulama bir ortama dağıtılıp uçtan uca çalışıyor.

---

## Kritik Bağımlılık Sırası (özet)

```
Faz 0 (iskelet)
  └─> Faz 1 (auth + şema)
        └─> Faz 2 (havuz)  ── İP-2.0 LLM/embedding ÖNCE kurulmalı
              ├─ İP-2.1 manuel (en kolay, önce)
              ├─ İP-2.2 PDF
              └─ İP-2.3 GitHub
        └─> Faz 3 (CV üretme) ── havuzda veri olmadan test edilemez
              JobParser → Selector → CVTailor → Evaluator → TypstRenderer
  └─> Faz 4 (KVKK) — auth'tan sonra paralel ilerleyebilir
  └─> Faz 5 (sağlamlaştırma) — sürekli, en sonda yoğunlaşır
```

## Genel Prensipler (her İP için geçerli)
- **Önce en basit kaynak/yol:** manuel giriş → PDF → GitHub; metin yapıştırma → URL.
- **Multi-tenant her zaman:** her sorgu `user_id` ile filtrelenir, her İP'de izolasyon testi.
- **Uydurma yok / onay zorunlu:** otomatik çıkarımlar `verified_by_user=false` başlar.
- **Dil her zaman birinci sınıf:** TR + EN + karma; teknik terimler korunur.
- **Her İP bağımsız test edilebilir bir çıktı verir** (DoD karşılanmadan sonrakine geçme).
