# PROMPT — IP-1.2: Auth (JWT) + tenant izolasyonu

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-1.2-auth-jwt`
- **Bağımlılıklar:** IP-1.1
- **Referans:** PROJECT_CONTEXT §4, §6, §10 · IS_PAKETLERI İP-1.2

---

## FAZ A — ÖN KONTROL (bir önceki işi DOĞRULA)
- [ ] `logs/IP-1.1-db-sema.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: `users` modeli (`kvkk_consent_at` dahil), migration uygulanmış.
- [ ] `alembic upgrade head` çalışıyor; `users` tablosu mevcut.
> ⛔ Eksikse: `logs/BLOCKED-IP-1.2.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] `POST /auth/register`: email + parola (bcrypt hash ile sakla) + **KVKK rıza zamanı** (`kvkk_consent_at` set edilir).
      Rıza onayı verilmeden kayıt reddedilir.
- [ ] `POST /auth/login`: doğru kimlikte JWT access token döner (exp + sub=user_id).
- [ ] `get_current_user` dependency: token'ı çözer, `user_id`'yi çıkarır, geçersizde 401.
- [ ] **Tenant izolasyon katmanı:** tüm korumalı sorgularda otomatik `user_id` filtresi için yardımcı/dependency.
- [ ] Korumalı örnek endpoint `GET /me` (current user bilgisi) ekle.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Kayıt + giriş çalışıyor; token ile korumalı endpoint erişilebiliyor.
- [ ] Komut/test: register → login → `GET /me` (token ile 200, tokensiz 401).
- [ ] Test: parola DB'de **hash** olarak saklanıyor (plaintext değil) — doğrula.
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-1.2-auth-jwt.md` yaz (endpoint listesi, token formatı, KVKK alanının doldurulduğu kanıtı).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (IP-4.1 KVKK akışları bunu tamamlayacak; IP-1.3 profil bunu kullanacak). Temiz çık.
