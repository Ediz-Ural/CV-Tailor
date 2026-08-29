# PROMPT — IP-5.1: i18n (TR/EN arayüz)

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-5.1-i18n`
- **Bağımlılıklar:** IP-1.4
- **Referans:** PROJECT_CONTEXT §2, §9 · IS_PAKETLERI İP-5.1

---

## FAZ A — ÖN KONTROL (önceki işi DOĞRULA)
- [ ] `logs/IP-1.4-frontend-auth.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: frontend çalışıyor (`npm run build` geçiyor), temel ekranlar mevcut.
> ⛔ Eksikse: `logs/BLOCKED-IP-5.1.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] Frontend i18n altyapısı (`react-i18next` veya benzeri) kur.
- [ ] TR + EN çeviri kaynakları; mevcut ekran metinlerini anahtarlara taşı.
- [ ] Dil değiştirici (UI) + tarayıcı/kullanıcı tercihine göre varsayılan.
- [ ] **Karma içerik:** TR açıklama + EN teknik terim aynı ekranda düzgün gösteriliyor (teknik terimler çevrilmez).

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Arayüz dili değiştirilebiliyor, karma içerik düzgün gösteriliyor.
- [ ] Komut: `npm run build` hatasız.
- [ ] Test: TR↔EN geçişinde metinler değişiyor; teknik terimler korunuyor.
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-5.1-i18n.md` yaz (i18n kütüphanesi, dil dosyaları konumu).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver. Temiz çık.
