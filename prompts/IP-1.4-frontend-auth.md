# PROMPT — IP-1.4: Frontend auth akışı

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-1.4-frontend-auth`
- **Bağımlılıklar:** IP-1.3, IP-0.4
- **Referans:** PROJECT_CONTEXT §9, §10 · IS_PAKETLERI İP-1.4

---

## FAZ A — ÖN KONTROL (önceki işleri DOĞRULA)
- [ ] `logs/IP-1.3-profil-crud.md` ve `logs/IP-0.4-frontend-kurulum.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: frontend scaffold (Tailwind/shadcn) + API client; backend `/auth/*`, `/profile`, `/me`.
- [ ] Backend auth akışı canlı çalışıyor (register/login).
> ⛔ Eksikse: `logs/BLOCKED-IP-1.4.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] Kayıt ekranı: email + parola + **KVKK onay checkbox'ı** + aydınlatma metni linki (placeholder).
- [ ] Giriş ekranı.
- [ ] Token saklama (güvenli; örn. memory + httpOnly tercih edilebilir, MVP'de localStorage kabul — logla).
- [ ] Auth guard: korumalı route'lar (giriş yoksa login'e yönlendir).
- [ ] Profil görüntüleme/düzenleme ekranı (`/profile` API'sine bağlı).
- [ ] API client'a Authorization header (Bearer token) otomatik eklenmesi.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Uçtan uca kayıt → giriş → profil düzenleme tarayıcıdan çalışıyor.
- [ ] Komut: `npm run build` hatasız.
- [ ] Manuel/otomatik akış kanıtı (ekran akışı veya e2e adımları).
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-1.4-frontend-auth.md` yaz (token saklama kararı + gerekçe, ekran listesi).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (IP-2.6, IP-3.7, IP-5.1 bu auth/layout üzerine kuracak). Temiz çık.
