# CV-Tailor

CV-Tailor, kullanıcının verdiği bir iş ilanına göre profil havuzundaki en uygun deneyim, proje ve yetkinlikleri seçerek ilana özel CV üreten çok kullanıcılı bir web uygulamasıdır. Profil havuzu PDF, GitHub ve manuel girdilerden beslenir; seçilen bilgiler uydurma eklenmeden ilana göre yeniden ifade edilir ve PDF olarak sunulur.

## Yerel Geliştirme

Her iki yolda da önce ortam dosyasını hazırlayın:

```powershell
Copy-Item .env.example .env
```

`JWT_SECRET` ve `LLM_API_KEY` alanlarını doldurun. `GITHUB_TOKEN_ENCRYPTION_KEY` için bir Fernet anahtarı üretin:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Yol 1 — Tüm stack Docker'da

```powershell
docker compose -f infra/docker-compose.yml --profile app up --build
```

Arayüz `http://localhost:8080`, API `http://localhost:8000` üzerinde açılır. Arayüz kendi nginx'i üzerinden `/api` yolunu backend'e proxy'ler.

### Yol 2 — Veritabanı Docker'da, uygulama yerelde

Arayüzde anlık yenileme (HMR) isteyen geliştirme akışı budur.

```powershell
docker compose -f infra/docker-compose.yml up -d db

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

- **Sanal ortam paylaşılamaz.** `backend/.venv` sürüm kontrolüne girmez; Docker içinde üretilmiş bir venv Windows'ta çalışmaz. Yerelde her zaman `uv sync` ile kendi ortamınızı kurun.
- **PDF üretimi Typst ikilisine ihtiyaç duyar.** Backend'i Docker dışında çalıştırıyorsanız [Typst](https://github.com/typst/typst) kurulu olmalı ve `TYPST_BINARY` onu göstermelidir; aksi hâlde pipeline `typst_renderer` adımında düşer. Docker imajı Typst'i kendisi kurar.
- **Tarayıcıdan gelen çağrılar için origin izni gerekir.** API'yi `/api` proxy'si olmadan doğrudan çağıracaksanız origin'i `CORS_ALLOW_ORIGINS` listesine ekleyin.
- **GitHub OAuth dönüşü.** `GITHUB_OAUTH_REDIRECT_URI` backend'in callback adresini, `FRONTEND_BASE_URL` ise kullanıcının geri gönderileceği arayüz adresini gösterir.

## Testler

```powershell
cd backend
uv run pytest

cd frontend
npm test
```

Backend testleri gerçek bir PostgreSQL'e bağlanır ve tablolardaki kayıtları siler. Bu yüzden yalnızca adı `_test` veya `_ci` ile biten bir veritabanına karşı çalışırlar:

```powershell
docker compose -f infra/docker-compose.yml exec db createdb -U cv_tailor cv_tailor_test
$env:DATABASE_URL = "postgresql+psycopg://cv_tailor:cv_tailor_dev@localhost:5432/cv_tailor_test"
cd backend
uv run alembic upgrade head
uv run pytest
```

Geliştirme veritabanınızın silinmesini bilerek göze alıyorsanız `CV_TAILOR_ALLOW_DESTRUCTIVE_TESTS=1` ile bu kontrolü devre dışı bırakabilirsiniz.

## Production Dağıtım

1. `.env.example` dosyasını `.env` olarak kopyalayın ve en az şu değerleri gerçek üretim değerleriyle değiştirin: `POSTGRES_PASSWORD`, `DATABASE_URL`, `JWT_SECRET`, `LLM_API_KEY`, `GITHUB_OAUTH_CLIENT_SECRET`, `GITHUB_TOKEN_ENCRYPTION_KEY`, `FRONTEND_BASE_URL`.
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
