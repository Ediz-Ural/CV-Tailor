# PROMPT — IP-1.1: Veritabanı şeması (multi-tenant)

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-1.1-db-sema`
- **Bağımlılıklar:** IP-0.3
- **Referans:** PROJECT_CONTEXT §6 · IS_PAKETLERI İP-1.1

---

## FAZ A — ÖN KONTROL (bir önceki işi DOĞRULA)
- [ ] `logs/IP-0.3-backend-kurulum.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: `backend/app/db/session.py`, Alembic kurulu, db servisi pgvector ile çalışıyor.
- [ ] `alembic upgrade head` çalışıyor.
> ⛔ Eksikse: `logs/BLOCKED-IP-1.1.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
SQLAlchemy modelleri + Alembic migration ile §6'daki TÜM tablolar (her tabloda `user_id` izolasyonu):
- [ ] `users` (id, email, hashed_password, created_at, **kvkk_consent_at**).
- [ ] `profiles` (id, user_id FK, full_name, contact, education[], personal_info).
- [ ] `pool_items` (id, user_id FK, source enum[pdf|github|manual], type enum[experience|project|skill],
      raw_content, title, tags[], technologies[], language[tr|en|mixed], **embedding vector**, verified_by_user bool, created_at).
- [ ] `jobs` (id, user_id FK, source_url, raw_text, detected_language, parsed_requirements_json, created_at).
- [ ] `generated_cvs` (id, user_id FK, job_id FK, selected_pool_item_ids[], output_language, typst_source, pdf_path, ats_score, created_at).
- [ ] `github_connections` (id, user_id FK, github_username, access_token_encrypted, last_synced).
- [ ] `embedding` için `pgvector` tipi; boyut sabitini (örn. 1024) `config`'te tanımla, modele yansıt (IP-2.0 ile tutarlı olacak — notu logla).
- [ ] Her tabloda `user_id` index. (pgvector ivfflat/hnsw index'i not olarak bırakılabilir, sonra eklenebilir.)
- [ ] Tek bir Alembic migration üret.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Migration uygulanıyor, tüm tablolar oluşuyor.
- [ ] Komut: `alembic upgrade head` → başarı.
- [ ] Komut: `\dt` veya `SELECT table_name FROM information_schema.tables` ile 6 tablo görülüyor.
- [ ] `pool_items.embedding` kolonunun tipi `vector` (psql `\d pool_items`).
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-1.1-db-sema.md` yaz (embedding boyutu, enum değerleri, index'ler dahil).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (embedding boyutu IP-2.0 ile eşleşmeli notu). Temiz çık.
