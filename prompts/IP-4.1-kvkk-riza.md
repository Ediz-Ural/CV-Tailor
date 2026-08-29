# PROMPT — IP-4.1: KVKK rıza ve aydınlatma

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-4.1-kvkk-riza`
- **Bağımlılıklar:** IP-1.2
- **Referans:** PROJECT_CONTEXT §10 · IS_PAKETLERI İP-4.1

---

## FAZ A — ÖN KONTROL (önceki işi DOĞRULA)
- [ ] `logs/IP-1.2-auth-jwt.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: register akışı `kvkk_consent_at` set ediyor; `users` tablosunda alan var.
> ⛔ Eksikse: `logs/BLOCKED-IP-4.1.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] Kayıtta **açık rıza metni** + onay zorunluluğu; `kvkk_consent_at` doğru kaydediliyor (IP-1.2 başlattı, burada tamamla).
- [ ] **Aydınlatma metni** sayfası/endpoint'i (içerik + erişim).
- [ ] Frontend: rıza checkbox'ı zorunlu, aydınlatma metni görüntülenebilir (IP-1.4 ekranıyla uyumlu).
- [ ] Rıza olmadan kayıt engelleniyor (backend doğrulaması).

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Rıza zamanı kaydediliyor, aydınlatma metni erişilebilir.
- [ ] Test: rıza onayı olmadan register reddediliyor; onayla `kvkk_consent_at` doluyor.
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-4.1-kvkk-riza.md` yaz (metin konumu, doğrulama kanıtı).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver. Temiz çık.
