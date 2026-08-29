# PROMPT — IP-2.6: Frontend — Havuz ekranı

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-2.6-frontend-havuz`
- **Bağımlılıklar:** IP-2.1, IP-1.4
- **Referans:** PROJECT_CONTEXT §9 · IS_PAKETLERI İP-2.6

---

## FAZ A — ÖN KONTROL (önceki işleri DOĞRULA)
- [ ] `logs/IP-2.1-manuel-havuz.md` ve `logs/IP-1.4-frontend-auth.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: havuz API'leri (manuel CRUD; mümkünse pending/approve/reject IP-2.4'ten), frontend auth + layout.
- [ ] Backend havuz endpoint'leri canlı çalışıyor.
> ⛔ Eksikse: `logs/BLOCKED-IP-2.6.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] Havuz listesi ekranı: kaynak etiketli (pdf/github/manual), tip filtreleri (experience/project/skill).
      Skill/teknoloji etiketleri **monospace** (§9).
- [ ] Manuel ekleme formu (`pool_items` create).
- [ ] Onay bekleyen öğeler için onay/ret UI (varsa `/pool/pending`, `/pool/approve`, `/pool/reject`).
- [ ] GitHub bağla butonu + sync durumu göstergesi (pipeline log stili, monospace).
- [ ] Dark-mode-first, temiz/yapısal yoğun veri ekranı (§9 ilkeleri).

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Kullanıcı havuzunu üç kaynaktan doldurup yönetebiliyor (en az manuel + pending onay akışı UI).
- [ ] Komut: `npm run build` hatasız.
- [ ] Akış kanıtı: manuel öğe ekle → listede görünüyor; pending öğeyi onayla → durum değişiyor.
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-2.6-frontend-havuz.md` yaz (ekran/komponent listesi, kullanılan API'ler).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver. Temiz çık.
