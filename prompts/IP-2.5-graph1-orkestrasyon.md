# PROMPT — IP-2.5: Graph 1 orkestrasyonu (LangGraph — Havuz Doldurma)

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-2.5-graph1-orkestrasyon`
- **Bağımlılıklar:** IP-2.4
- **Referans:** PROJECT_CONTEXT §7 (Graph 1) · IS_PAKETLERI İP-2.5

---

## FAZ A — ÖN KONTROL (önceki işleri DOĞRULA)
- [ ] `logs/IP-2.4-itemextractor-onay.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: PDFParser, GitHubAnalyzer, ItemExtractor + onay akışı çalışıyor.
- [ ] (Zincir bütünlüğü) IP-2.2 ve IP-2.3 logları da TAMAMLANDI.
> ⛔ Eksikse: `logs/BLOCKED-IP-2.5.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] LangGraph kur (`backend/app/graphs/pool_graph.py`).
- [ ] Graph 1 düğümleri: **PDFParser ∥ GitHubAnalyzer (paralel)** → **ItemExtractor** → onay için hazırla.
- [ ] State şeması (girdi: user_id + kaynaklar; çıktı: normalize edilmiş onaysız öğeler).
- [ ] Profil oluşturma/güncelleme bu graph'ı **tetikler** (tetikleyici endpoint veya servis).
- [ ] Uzun süren adımlar için arka plan çalıştırma (senkron HTTP'yi bloklamadan).

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Tek tetikleme ile PDF + GitHub paralel işlenip havuz onaya hazır geliyor.
- [ ] Test: graph'ı tetikle (örnek PDF + bağlı GitHub) → pending öğeler oluşuyor; paralel çalışma doğrulanır.
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-2.5-graph1-orkestrasyon.md` yaz (graph dosyası, düğüm sırası, tetikleyici).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver. Temiz çık.
