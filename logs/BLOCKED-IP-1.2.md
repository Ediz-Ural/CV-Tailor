# BLOCKED - IP-1.2: Auth (JWT) + tenant izolasyonu

- **DURUM:** BLOCKED
- **Tarih:** 2026-06-13
- **Is paketi:** `IP-1.2-auth-jwt`

## Dogrulanan bagimlilik
- `logs/IP-1.1-db-sema.md` mevcut ve `DURUM: TAMAMLANDI`.
- `backend/app/models/user.py` dosyasinda `kvkk_consent_at` alani mevcut.
- `backend/migrations/versions/20260613_0002_multi_tenant_schema.py` users tablosunu ve KVKK alanini olusturuyor.
- `docker compose -f infra/docker-compose.yml --profile app run --rm backend uv run --no-sync alembic upgrade head` basarili.
- PostgreSQL sorgusu `users` tablosunda `id`, `email`, `hashed_password`, `created_at`, `kvkk_consent_at` kolonlarini dondurdu.

## Engel
- Yazilmasi gereken proje kodu `C:\Users\LENOVO\OneDrive\Desktop\cv-tailor\backend` altinda.
- Oturumun yazilabilir koku yalnizca `C:\Users\LENOVO\OneDrive\Desktop\cv-tailor\codex`.
- Sandbox disi yazma izni istendi ancak izin istegi sonuclanmadi; bekleyen komut temiz bicimde sonlandirildi.
- Backend dosyalarinda degisiklik veya yarim dosya birakilmadi.

## Onerilen duzeltme
- `C:\Users\LENOVO\OneDrive\Desktop\cv-tailor` repo kokunu yazilabilir workspace root olarak acin veya backend dizinine yazma iznini onaylayip IP-1.2 paketini yeniden calistirin.
