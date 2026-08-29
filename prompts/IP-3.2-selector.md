# PROMPT — IP-3.2: Selector (semantik + LLM seçim)

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-3.2-selector`
- **Bağımlılıklar:** IP-3.1, IP-2.1
- **Referans:** PROJECT_CONTEXT §4 (Türkçe kurallar), §7 (Graph 2) · IS_PAKETLERI İP-3.2

---

## FAZ A — ÖN KONTROL (önceki işleri DOĞRULA)
- [ ] `logs/IP-3.1-jobparser.md` ve `logs/IP-2.1-manuel-havuz.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: `jobs.parsed_requirements_json` üretiliyor; `pool_items` embedding'li ve `verified_by_user` alanlı.
> ⛔ Eksikse: `logs/BLOCKED-IP-3.2.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] Selector node (`backend/app/graphs/nodes/selector.py`): ilan gereksinimleri ↔ havuz arası
      **pgvector semantic arama** (cosine/inner product), yalnız **`verified_by_user=true`** öğeler.
- [ ] LLM ile en alakalı öğeleri seç/sırala (skorla).
- [ ] **Dil farkı seçimi engellemez** (EN ilana TR havuz öğesi de seçilebilir).
- [ ] **Türkçe için exact string match YOK** → lemmatization (Zemberek/stanza) veya embedding semantic match.
- [ ] Çıktı: seçilen `pool_item_id`'ler + skorlar.

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Bir ilana karşı havuzdan en alakalı öğeler (id listesi + skor) dönüyor.
- [ ] Test: verified olmayan öğeler **seçilmiyor**.
- [ ] Test: TR/EN karma senaryoda dil farkına rağmen alakalı öğe seçiliyor; "geliştirici/geliştirme" kök varyasyonu eşleşiyor.
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-3.2-selector.md` yaz (benzerlik metriği, lemmatization yöntemi, seçim mantığı).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (IP-3.3 CVTailor seçilenleri yeniden ifade edecek). Temiz çık.
