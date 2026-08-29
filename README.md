# CV-Tailor

CV-Tailor, kullanıcının verdiği bir iş ilanına göre profil havuzundaki en uygun deneyim, proje ve yetkinlikleri seçerek ilana özel CV üreten çok kullanıcılı bir web uygulamasıdır. Profil havuzu PDF, GitHub ve manuel girdilerden beslenir; seçilen bilgiler uydurma eklenmeden ilana göre yeniden ifade edilir ve PDF olarak sunulur.

## Yerel Geliştirme

```powershell
Copy-Item .env.example .env
docker compose -f infra/docker-compose.yml --profile app up --build
```

Backend `http://localhost:8000`, frontend geliştirme servisi `http://localhost:5173` üzerinde kullanılır.

## Production Dağıtım

1. `.env.example` dosyasını `.env` olarak kopyalayın ve en az şu değerleri gerçek üretim değerleriyle değiştirin: `POSTGRES_PASSWORD`, `DATABASE_URL`, `JWT_SECRET`, `LLM_API_KEY`, `GITHUB_OAUTH_CLIENT_SECRET`, `GITHUB_TOKEN_ENCRYPTION_KEY`.
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
