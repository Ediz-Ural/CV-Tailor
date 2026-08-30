# CV-Tailor

CV-Tailor, verdiğiniz bir iş ilanına göre profil havuzunuzdaki en uygun deneyim, proje ve yetkinlikleri seçip ilana özel bir CV üreten, çok kullanıcılı bir web uygulamasıdır. Havuz PDF, GitHub ve manuel girdilerden beslenir; seçilen bilgiler **uydurma eklenmeden** ilana göre yeniden ifade edilir ve Typst ile PDF olarak sunulur.

## Ekranlar

| Profil havuzu | İlan → CV |
|---|---|
| ![Profil havuzu](docs/screenshots/02-pool.png) | ![Pipeline çalışırken](docs/screenshots/03-pipeline-running.png) |

Pipeline tamamlandığında ATS skoru, önce/sonra farkı, seçilen havuz öğeleri ve PDF önizlemesi aynı ekranda açılır:

![CV sonucu](docs/screenshots/04-result.png)

| CV arşivi | Hesap ve API anahtarı |
|---|---|
| ![Arşiv](docs/screenshots/05-archive.png) | ![Hesap](docs/screenshots/06-account.png) |

## Nasıl çalışır

İki LangGraph akışı var:

**Havuz akışı** — Yüklediğiniz CV'nin PDF'i ve bağladığınız GitHub deposu ayrıştırılır, adaylar çıkarılır ve **onayınıza** sunulur. Onaylamadığınız hiçbir madde CV üretiminde kullanılmaz.

**Üretim akışı** — `JobParser` ilanı yapılandırılmış gereksinimlere çevirir → `Selector` havuzdan pgvector benzerliğiyle aday çeker ve ilana uygun olanları seçer → `CVTailor` seçilenleri ilana göre yeniden ifade eder → `Evaluator` ATS uyum skoru, eksik anahtar kelimeler ve önce/sonra farkını üretir → `TypstRenderer` PDF'i basar. Arayüz adımları canlı takip eder.

### Seçim nasıl davranıyor

Havuzunuz her alandan projeyi barındırabilir; CV'ye yalnızca ilana uyanlar girer. Beş alana yayılmış 15 projelik bir havuzla ölçüldü:

| İlan | CV'ye giren projeler |
|---|---|
| AI Engineer | 2 yapay zekâ projesi |
| Frontend Engineer | 3 frontend projesi |
| DevOps / SRE | 3 altyapı projesi |
| Mobile Engineer | 3 mobil projesi |

Dört ilanın hiçbirinde başka alandan proje CV'ye girmedi. Seçim listesi bir üst sınırdır, kota değil: ilana uyan üç proje varsa CV'de üç proje olur.

Bu davranış üç ayarla yönetilir — `SELECTOR_CANDIDATE_LIMIT` (vektör aramasının sıralamaya ilettiği aday sayısı; büyük bir portföyde yükseltin), `SELECTOR_SELECTION_LIMIT` (bir CV'deki en fazla proje sayısı) ve `SELECTOR_MIN_RELEVANCE` (bir projenin CV'ye girmesi için gereken alaka eşiği; düşürürseniz sınırdaki işler de girer, yükseltirseniz CV daralır).

## Öne çıkanlar

- **Kendi API anahtarınız.** Üretim kendi sağlayıcı hesabınızdan faturalandırılır; anahtar şifreli saklanır, hiçbir yanıtta geri dönmez.
- **Uydurma yok.** Model yalnızca onayladığınız havuz maddelerini yeniden ifade eder.
- **TR/EN arayüz** ve çok kiracılı veri izolasyonu.
- **KVKK**: açık rıza akışı, aydınlatma metni ve tek tuşla kalıcı hesap silme.

## Teknolojiler

FastAPI · LangGraph · PostgreSQL + pgvector · SQLAlchemy + Alembic · Typst · React 19 + Vite + Tailwind · Docker Compose · pytest · Vitest · Playwright

## Kurulum

### Tek komut

Windows'ta gereken tek şey Docker Desktop'ın çalışıyor ve [Node.js](https://nodejs.org/)'un kurulu olmasıdır. Gerisini script halleder:

```powershell
.\dev.ps1
```

Sırayla şunlar olur: `.env` yoksa `.env.example`'dan üretilir ve `JWT_SECRET` ile şifreleme anahtarları rastgele basılır → PostgreSQL Docker'da kaldırılır → eksikse `uv` ve Typst indirilir → bağımlılıklar kurulur → migration'lar çalışır → backend `:8000` ve arayüz `:5173` ayrı pencerelerde açılır → ikisi de sağlıklı yanıt verince tarayıcı açılır.

```
[1/6] .env hazirlaniyor... olusturuldu
[2/6] PostgreSQL (docker) baslatiliyor... hazir
[3/6] Backend bagimliliklari (uv sync)... tamam
[4/6] Migration'lar (alembic upgrade head)... tamam
[5/6] Backend :8000 ... ok
[6/6] Frontend :5173 ... ok
```

Açılan ekranda **Kayıt ol** ile hesap açın; giriş için başka bir hazırlık gerekmez. CV üretmek istediğinizde **Hesap** ekranından kendi LLM API anahtarınızı girersiniz — üretim sizin sağlayıcı hesabınızdan faturalandırılır.

| Bayrak | Ne yapar |
|---|---|
| `.\dev.ps1` | Kurar ve başlatır |
| `.\dev.ps1 -SkipInstall` | `uv sync` / `npm install` adımlarını atlar, daha hızlı yeniden başlatır |
| `.\dev.ps1 -NoBrowser` | Tarayıcıyı açmaz |
| `.\dev.ps1 -Stop` | Backend, arayüz ve veritabanını durdurur |

Script'in sessizce hallettiği dört şey:

- **`.env`'iniz ezilmez.** Yalnızca hâlâ örnek değerde ya da boş olan alanlar doldurulur; kendi girdiğiniz hiçbir değere dokunulmaz.
- **Veritabanı adresi.** `.env`'deki `DATABASE_URL` Compose için `db` host'unu gösterir. Yerelde çalışan backend aynı veritabanına `localhost` üzerinden bağlanır; bu değer dosyaya yazılmaz, sadece başlatılan sürece ortam değişkeni olarak geçer.
- **Typst.** PATH'te yoksa Windows sürümü `.tools/` altına indirilir ve `TYPST_BINARY` oraya yönlendirilir, yoksa pipeline `typst_renderer` adımında düşer.
- **Docker'dan sızan `.venv`.** `backend/.venv` Docker içinde üretilmişse Windows'ta çalışmaz ve `uv sync` onu silemez; script böyle bir ortamı tanıyıp temizler.

İlk çalıştırmada beklenecek iki şey var:

- **İlk kurulum birkaç dakika sürer** (Python bağımlılıkları, `npm install`, Typst indirmesi).
- **Havuza eklenen ilk öğe yaklaşık 1,5 dakika sürer.** `EMBEDDING_MODEL` ilk kullanımda indirilir (yaklaşık 2 GB); sonraki istekler anında döner. Ekran donmuş gibi görünebilir, beklemek yeterlidir.

### Elle kurulum

Script'i kullanmıyorsanız (ya da Windows'ta değilseniz) önce ortam dosyasını hazırlayın:

```powershell
Copy-Item .env.example .env
```

`JWT_SECRET`'i mutlaka değiştirin — `.env.example`'daki değer herkese açıktır ve onunla herhangi bir hesap için token üretilebilir:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`CREDENTIAL_ENCRYPTION_KEY` için bir Fernet anahtarı üretin (kullanıcıların GitHub token'larını ve LLM anahtarlarını şifreler):

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

#### Yol 1 — Tüm stack Docker'da

```powershell
docker compose --env-file .env -f infra/docker-compose.yml --profile app up --build
```

`--env-file .env` şart: Compose `.env` dosyasını compose dosyasının bulunduğu dizine (`infra/`) göre arar, kök dizindeki `.env` bu bayrak olmadan sessizce yok sayılır ve `LLM_API_KEY` boş kalır.

Arayüz `http://localhost:8080`, API `http://localhost:8000` üzerinde açılır. Arayüz kendi nginx'i üzerinden `/api` yolunu backend'e proxy'ler. İlk build birkaç dakika sürer: backend imajı Typst'i indirir, frontend imajı `npm ci` çalıştırır.

CV üretimi bir LLM sağlayıcı anahtarı gerektirir, **ama bu anahtar `.env`'e konmaz**: her kullanıcı kendi anahtarını uygulamadaki **Hesap** ekranından girer ve üretim o kullanıcının kendi sağlayıcı hesabından faturalandırılır. Anahtar kaydedilirken sağlayıcıya karşı doğrulanır, şifreli saklanır ve bir daha geri gösterilmez.

Tek kişilik bir kurulumda sunucunun `LLM_API_KEY` değerini paylaşmak isterseniz `ALLOW_SHARED_LLM_KEY=1` yapabilirsiniz; birden fazla hesabı olan bir kurulumda bunu açmayın, çünkü her kullanıcı sizin anahtarınızı harcar.

#### Yol 2 — Veritabanı Docker'da, uygulama yerelde

`.\dev.ps1`'in otomatikleştirdiği akış budur; elle şöyle yürür:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d db

cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload

# ikinci terminalde
cd frontend
npm install
npm run dev
```

Arayüz `http://localhost:5173` üzerinde açılır ve Vite'ın proxy'si `/api` isteklerini `http://localhost:8000` adresine iletir.

Bilinmesi gerekenler:

- **`DATABASE_URL`'i yerele çevirin.** `.env`'deki değer Compose ağı içindeki `db` host'unu gösterir; yerelde çalışan backend için `localhost` olmalıdır.
- **Sanal ortam paylaşılamaz.** `backend/.venv` sürüm kontrolüne girmez; Docker içinde üretilmiş bir venv Windows'ta çalışmaz. Yerelde her zaman `uv sync` ile kendi ortamınızı kurun.
- **PDF üretimi Typst ikilisine ihtiyaç duyar.** Backend'i Docker dışında çalıştırıyorsanız [Typst](https://github.com/typst/typst) kurulu olmalı ve `TYPST_BINARY` onu göstermelidir; aksi hâlde pipeline `typst_renderer` adımında düşer. Docker imajı Typst'i kendisi kurar.
- **`RENDER_OUTPUT_DIR` ve `FASTEMBED_CACHE_PATH`** `.env`'de Docker içi yolları (`/app/storage/...`, `/var/cache/fastembed`) gösterir; yerelde çalışırken var olan bir dizine çevirin.
- **Tarayıcıdan gelen çağrılar için origin izni gerekir.** API'yi `/api` proxy'si olmadan doğrudan çağıracaksanız origin'i `CORS_ALLOW_ORIGINS` listesine ekleyin.
- **GitHub OAuth dönüşü.** `GITHUB_OAUTH_REDIRECT_URI` backend'in callback adresini, `FRONTEND_BASE_URL` ise kullanıcının geri gönderileceği arayüz adresini gösterir.

## Testler

```powershell
# backend (gerçek PostgreSQL'e karşı)
cd backend
uv run pytest

# frontend birim testleri
cd frontend
npm test

# uçtan uca (çalışan bir backend gerektirir)
cd frontend
npx playwright install chromium
npm run test:e2e
```

Uçtan uca testler üretim build'ini gerçek bir API ve veritabanına karşı sürer; hiçbiri LLM sağlayıcısına gitmez, yani ücretli anahtar gerekmez.

Backend testleri gerçek bir PostgreSQL'e bağlanır ve tablolardaki kayıtları siler. Bu yüzden yalnızca adı `_test` veya `_ci` ile biten bir veritabanına karşı çalışırlar:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml exec db createdb -U cv_tailor cv_tailor_test
$env:DATABASE_URL = "postgresql+psycopg://cv_tailor:cv_tailor_dev@localhost:5432/cv_tailor_test"
cd backend
uv run alembic upgrade head
uv run pytest
```

Geliştirme veritabanınızın silinmesini bilerek göze alıyorsanız `CV_TAILOR_ALLOW_DESTRUCTIVE_TESTS=1` ile bu kontrolü devre dışı bırakabilirsiniz.

## Production Dağıtım

1. `.env.example` dosyasını `.env` olarak kopyalayın ve en az şu değerleri gerçek üretim değerleriyle değiştirin: `POSTGRES_PASSWORD`, `DATABASE_URL`, `JWT_SECRET`, `CREDENTIAL_ENCRYPTION_KEY`, `GITHUB_OAUTH_CLIENT_SECRET`, `FRONTEND_BASE_URL`. `LLM_API_KEY` gerekmez; kullanıcılar kendi anahtarlarını girer.
   Arayüz kendi nginx'i üzerinden API'ye gittiği için `CORS_ALLOW_ORIGINS` boş bırakılabilir; API'yi başka bir origin'den çağıracaksanız o adresi buraya yazın.
2. Production imajlarını build edip stack'i başlatın:

```powershell
docker compose --env-file .env -f infra/docker-compose.prod.yml up -d --build
```

3. Sağlık ve metrikleri kontrol edin:

```powershell
Invoke-RestMethod http://localhost:8080/api/health
Invoke-RestMethod http://localhost:8080/api/metrics
```

4. Backend JSON loglarını izleyin:

```powershell
docker compose --env-file .env -f infra/docker-compose.prod.yml logs -f backend
```

Loglarda `request_completed`, `pipeline_step_started`, `pipeline_step_completed`, `pipeline_completed` ve `pipeline_failed` event'leri JSON olarak görünür. Pipeline status yanıtındaki her adım `duration_ms` alanı taşır; `/metrics` pipeline durum sayılarını ve render kuyruğu sayaçlarını döndürür.

## Smoke Akışı

Production stack ayaktayken:

1. `POST /api/auth/register` ile kullanıcı oluşturun.
2. `POST /api/auth/login` ile token alın.
3. Token ile manuel, doğrulanmış pool item ekleyin.
4. `POST /api/cv-generation` ile ilan metni gönderin.
5. Dönen `pipeline_id` için `GET /api/cv-generation/{pipeline_id}` çağırın.
6. `status=completed`, `generated_cv_id`, `ats_score` ve adım `duration_ms` alanlarını doğrulayın.
7. PDF için `GET /api/generated-cvs/{generated_cv_id}/download` çağırın.

## Depo yapısı

```
dev.ps1     Tüm geliştirme ortamını tek komutla kuran ve başlatan script
backend/    FastAPI uygulaması, LangGraph akışları, Alembic migration'ları, pytest
frontend/   React + Vite arayüzü, Vitest birim testleri, Playwright e2e
infra/      Docker Compose (geliştirme ve üretim) ve veritabanı başlangıç betikleri
docs/       Veri saklama ve güvenlik politikası, iş paketi dokümanları
prompts/    Projenin ajan destekli geliştirme akışında kullanılan iş paketi promptları
logs/       Her iş paketi için üretilen uygulama günlükleri
state/      İş paketi durum tablosu
```

`prompts/`, `logs/` ve `state/` dizinleri uygulamanın çalışması için gerekli değildir; projenin nasıl geliştirildiğinin kaydıdır.

## Katkı ve lisans

Sorun bildirimi ve pull request'ler açıktır. Değişiklik göndermeden önce `npm run lint`, `npm test` ve `uv run pytest` komutlarının geçtiğinden emin olun; CI aynı üçünü ve uçtan uca testleri çalıştırır.

MIT lisansı altındadır, bkz. [LICENSE](LICENSE).
