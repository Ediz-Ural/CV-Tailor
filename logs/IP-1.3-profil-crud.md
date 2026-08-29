# Log - IP-1.3: Profil CRUD

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-13 16:13
- **Is paketi prompt'u:** `prompts/IP-1.3-profil-crud.md`
- **Bagimliliklar (dogrulandi mi?):** IP-1.2 tamamlandi; log, auth dosyalari, migration ve canli auth akisi dogrulandi.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-1.2-auth-jwt.md` mevcut ve `DURUM: TAMAMLANDI`.
- `backend/app/api/auth.py` icinde `POST /auth/register` ve `POST /auth/login` mevcut.
- `backend/app/api/dependencies.py` icinde `get_current_user` mevcut.
- `docker compose -f infra/docker-compose.yml --profile app run --rm backend uv run --no-sync alembic upgrade head` basarili oldu.
- `docker compose -f infra/docker-compose.yml --profile app run --rm backend uv run pytest -q tests/test_auth.py::test_register_login_and_me_flow` sonucu `1 passed, 1 warning`; register `201`, login `200`, Bearer `/me` `200` akisi dogrulandi.

## 2. Yapilan isler (FAZ B)
- [x] `POST /profile`: token sahibine ilk profil olusturma; ikinci olusturma `409`.
- [x] `GET /profile`: yalnizca token sahibinin profilini okuma; profil yoksa `404`.
- [x] `PUT /profile`: token sahibinin profilini tam degistirme.
- [x] `PATCH /profile`: token sahibinin profilini kismi guncelleme.
- [x] `DELETE /profile`: token sahibinin profilini silme; sonrasinda okuma `404`.
- [x] Tum sorgular `TenantScope` ile `profiles.user_id == current_user.id` filtresinden geciyor.
- [x] Pydantic request/response semalari `full_name`, `contact`, `education[]` ve `personal_info` alanlarini dogruluyor.
- [x] `profiles.user_id` icin benzersiz kisit eklenerek kullanici basina tek profil DB seviyesinde guvenceye alindi.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `backend/app/api/profile.py` | yeni | Tenant filtreli profil CRUD endpoint'leri |
| `backend/app/schemas/profile.py` | yeni | Profil create/replace/patch/response Pydantic semalari |
| `backend/tests/test_profile.py` | yeni | CRUD, dogrulama ve iki kullanicili izolasyon testleri |
| `backend/migrations/versions/20260613_0003_profile_unique_user.py` | yeni | `profiles.user_id` benzersiz kisiti |
| `backend/app/main.py` | degisti | Profil router uygulamaya baglandi |
| `backend/app/models/profile.py` | degisti | `user_id` tekilligi modele yansitildi |
| `backend/app/schemas/__init__.py` | degisti | Profil semalari dis aktarildi |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Kullanici kendi profilini olusturup guncelleyebiliyor; iki kullanici birbirinin profiline erisemiyor.
- **Calistirilan komutlar:**
  ```text
  docker compose -f infra/docker-compose.yml --profile app build backend
  docker compose -f infra/docker-compose.yml --profile app run --rm backend uv run --no-sync alembic upgrade head
  docker compose -f infra/docker-compose.yml --profile app run --rm backend uv run pytest -q tests/test_profile.py
  docker compose -f infra/docker-compose.yml --profile app run --rm backend uv run pytest -q
  ```
- **Migration ciktisi:** `20260613_0002 -> 20260613_0003` upgrade basarili.
- **Profil test ciktisi:** `3 passed, 1 warning`.
- **Tam regresyon ciktisi:** `11 passed, 1 warning`.
- **CRUD kaniti:** POST `201`; PUT/PATCH/GET `200`; guncellenen alanlar sonraki GET yanitinda korundu; DELETE `204`.
- **Izolasyon kaniti:** A ve B ayri profiller olusturdu. A'nin PATCH islemi B'nin degerini degistirmedi. A kendi profilini sildikten sonra B profili mevcutken A'nin `GET /profile` istegi `404`, B'nin istegi `200` dondu.
- **Dogrulama kaniti:** Kimliksiz GET `401`; nesne olmayan `education[]` ve `education: null` `422` dondu.
- **Uyari:** Mevcut Starlette TestClient deprecation warning'i test sonucunu etkilemiyor.
- **Sonuc:** DoD karsilandi.

## 5. Sonraki paket icin notlar
- IP-1.4 frontend profil ekrani `POST /profile`, `GET /profile`, `PUT/PATCH /profile` endpoint'lerini Bearer token ile kullanabilir.
- Profil yokken `GET /profile` `404`; ilk kayit `POST /profile`; sonraki kayit girisimi `409` doner.

## 6. Acik sorunlar / bayraklar
- Starlette TestClient deprecation warning'i devam ediyor; testler basarili.
