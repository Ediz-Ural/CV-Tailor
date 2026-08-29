# Log - IP-1.2: Auth (JWT) + tenant izolasyonu

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-13 16:03
- **Is paketi prompt'u:** `prompts/IP-1.2-auth-jwt.md`
- **Bagimliliklar (dogrulandi mi?):** IP-1.1 tamamlandi; log, model, migration ve PostgreSQL tablo kontrolleri gecti.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-1.1-db-sema.md` mevcut ve `DURUM: TAMAMLANDI`.
- `backend/app/models/user.py` dosyasinda `hashed_password` ve `kvkk_consent_at` alanlari mevcut.
- `backend/migrations/versions/20260613_0002_multi_tenant_schema.py` migration'i `users` tablosunu ve KVKK alanini olusturuyor.
- `docker compose -f infra/docker-compose.yml --profile app run --rm backend uv run --no-sync alembic upgrade head` basarili oldu.
- PostgreSQL `information_schema.columns` sorgusu `id`, `email`, `hashed_password`, `kvkk_consent_at` kolonlarini dondurdu.

## 2. Yapilan isler (FAZ B)
- [x] `POST /auth/register`: normalize email, bcrypt parola hash'i ve zorunlu KVKK rizasi ile kullanici kaydi eklendi.
- [x] `POST /auth/login`: basarili kimlik dogrulamada `sub=user_id` ve `exp` claim'li JWT access token eklendi.
- [x] `get_current_user`: Bearer token cozumleme, kullanici yukleme ve gecersiz/eksik token icin 401 eklendi.
- [x] `TenantScope` ve `get_tenant_scope`: korumali sorgulara zorunlu `model.user_id == current_user.id` filtresi uygulayan katman eklendi.
- [x] `GET /me`: token sahibinin bilgilerini donduren korumali endpoint eklendi.
- [x] Auth, hash ve iki kullanicili tenant izolasyonu testleri eklendi.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `backend/app/core/security.py` | yeni | Bcrypt hash/dogrulama ve JWT uretimi |
| `backend/app/schemas/auth.py` | yeni | Register, login, token ve user semalari |
| `backend/app/schemas/__init__.py` | yeni | Auth sema dis aktarlari |
| `backend/app/api/dependencies.py` | yeni | `get_current_user` ve tenant scope dependency |
| `backend/app/api/auth.py` | yeni | Register, login ve `/me` endpoint'leri |
| `backend/app/api/__init__.py` | yeni | API paketi |
| `backend/app/main.py` | degisti | Auth router uygulamaya baglandi |
| `backend/tests/test_auth.py` | yeni | Auth akisi, hash, 401 ve tenant izolasyonu testleri |
| `backend/pyproject.toml` | degisti | Calisma zamaninda kullanilan bcrypt dogrudan bagimliligi |
| `backend/uv.lock` | degisti | Bcrypt dogrudan bagimlilik kaydi |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Kayit + giris calisiyor; token ile korumali endpoint erisilebiliyor.
- **Calistirilan komutlar:**
  ```text
  docker compose -f infra/docker-compose.yml --profile app build backend
  docker compose -f infra/docker-compose.yml --profile app run --rm backend uv run --no-sync alembic upgrade head
  docker compose -f infra/docker-compose.yml --profile app run --rm backend uv run pytest -q
  ```
- **Cikti ozeti:** Backend imaji frozen lock ile kuruldu. Alembic head basarili uygulandi. Pytest `8 passed, 1 warning` dondurdu.
- **Endpoint kaniti:** Test akisi register `201`, login `200`, Bearer token ile `/me` `200`, tokensiz ve gecersiz token ile `/me` `401` dogruladi.
- **Token formati:** JWT Bearer access token; `sub` kayitli kullanicinin UUID'si, `exp` ayarlanan sona erme zamani.
- **Parola/KVKK kaniti:** DB sorgusunda parola plaintext'ten farkli ve `$2` bcrypt prefix'li; `kvkk_consent_at` bos degil. Riza `false` kaydi `400` ile reddedildi.
- **Tenant kaniti:** Iki kullaniciya ait iki profil arasinda `TenantScope`, yalnizca current user satirini dondurdu.
- **Sonuc:** DoD karsilandi.

## 5. Sonraki paket icin notlar
- IP-1.3 korumali profil sorgularinda `Tenant` dependency veya `TenantScope.apply(...)` kullanmalidir.
- IP-1.4 istemcisi login yanitindaki `access_token` degerini `Authorization: Bearer <token>` olarak gondermelidir.
- IP-4.1 kayitta baslatilan KVKK metni ve aydinlatma akisini tamamlayacaktir.

## 6. Acik sorunlar / bayraklar
- FastAPI TestClient kaynakli mevcut Starlette deprecation warning'i devam ediyor; test sonucunu etkilemiyor.
