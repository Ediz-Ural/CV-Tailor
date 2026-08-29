# PROMPT — IP-1.3: Profil CRUD

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-1.3-profil-crud`
- **Bağımlılıklar:** IP-1.2
- **Referans:** PROJECT_CONTEXT §6 · IS_PAKETLERI İP-1.3

---

## FAZ A — ÖN KONTROL (bir önceki işi DOĞRULA)
- [ ] `logs/IP-1.2-auth-jwt.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: `/auth/register`, `/auth/login`, `get_current_user` dependency.
- [ ] register→login→korumalı endpoint akışı çalışıyor (canlı doğrula).
> ⛔ Eksikse: `logs/BLOCKED-IP-1.3.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] `profiles` için CRUD endpoint'leri: `full_name`, `contact`, `education[]`, `personal_info`.
      - `GET /profile` (kendi profili), `PUT/PATCH /profile`, gerekirse `POST` (ilk oluşturma).
- [ ] Tüm işlemler `get_current_user`'dan gelen `user_id` ile filtrelenir.
- [ ] **İzolasyon:** kullanıcı yalnızca kendi profiline erişir/düzenler (başkasınınkine 403/404).
- [ ] Pydantic şemaları (request/response) ile doğrulama.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Kullanıcı kendi profilini oluşturup güncelleyebiliyor.
- [ ] Test: iki kullanıcı oluştur; A, B'nin profiline erişemiyor (izolasyon testi).
- [ ] Test: profil oluştur → güncelle → oku, değerler tutuyor.
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-1.3-profil-crud.md` yaz (endpoint listesi, izolasyon testi kanıtı).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver. Temiz çık.
