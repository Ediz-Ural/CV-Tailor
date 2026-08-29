# PROMPT — IP-2.1: Manuel havuz girişi

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-2.1-manuel-havuz`
- **Bağımlılıklar:** IP-2.0, IP-1.1
- **Referans:** PROJECT_CONTEXT §6 · IS_PAKETLERI İP-2.1

---

## FAZ A — ÖN KONTROL (önceki işleri DOĞRULA)
- [ ] `logs/IP-2.0-llm-embedding.md` ve `logs/IP-1.1-db-sema.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: `pool_items` modeli/tablosu (`vector` kolonlu), `embeddings.py`, `detect_language`.
- [ ] embedding boyutu ↔ `pool_items.embedding` boyutu uyuşuyor (canlı kontrol).
> ⛔ Eksikse: `logs/BLOCKED-IP-2.1.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] `pool_items` CRUD endpoint'leri (kullanıcıya özel): `type` (experience|project|skill),
      `title`, `raw_content`, `tags[]`, `technologies[]`.
- [ ] Kayıtta otomatik: `source="manual"`, dil tespiti (`language`), embedding üretimi (`embedding`).
- [ ] Manuel girişler `verified_by_user=true` (kullanıcı kendi girdi).
- [ ] Tüm sorgular `user_id` ile izole.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Kullanıcı manuel öğe ekleyebiliyor, embedding DB'ye yazılıyor.
- [ ] Test: öğe ekle → DB'de `embedding` dolu, `source=manual`, `verified_by_user=true`, `language` set.
- [ ] Test: başka kullanıcının öğelerine erişilemiyor (izolasyon).
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-2.1-manuel-havuz.md` yaz (endpoint listesi, embedding yazma kanıtı).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (IP-2.2/2.3 aynı `pool_items` formatına yazacak; IP-2.6 ve IP-3.2 bunu kullanacak). Temiz çık.
