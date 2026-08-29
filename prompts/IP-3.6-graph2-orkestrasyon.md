# PROMPT — IP-3.6: Graph 2 orkestrasyonu (LangGraph — CV Üretme)

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-3.6-graph2-orkestrasyon`
- **Bağımlılıklar:** IP-3.5 (ve zincir: IP-3.1→3.2→3.3→3.4→3.5)
- **Referans:** PROJECT_CONTEXT §7 (Graph 2) · IS_PAKETLERI İP-3.6

---

## FAZ A — ÖN KONTROL (önceki işleri DOĞRULA)
- [ ] `logs/IP-3.5-typst-render.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Zincir bütünlüğü: IP-3.1, IP-3.2, IP-3.3, IP-3.4 logları **hepsi** TAMAMLANDI.
- [ ] Diskte: JobParser, Selector, CVTailor, Evaluator, TypstRenderer node'ları mevcut ve tekil çalışıyor.
> ⛔ Eksikse: `logs/BLOCKED-IP-3.6.md` yaz (hangi node eksik), DUR.

## FAZ B — GÖREV (checklist)
- [ ] LangGraph (`backend/app/graphs/cv_graph.py`): **JobParser → Selector → CVTailor → Evaluator → TypstRenderer** zinciri.
- [ ] State şeması (girdi: user_id + ilan; ara: gereksinimler, seçilenler, tailor içerik, skor; çıktı: generated_cv).
- [ ] İlan girişi bu graph'ı **tetikler** (tetikleyici endpoint).
- [ ] Uzun süren adımlar (LLM ~10–30sn) için **durum/progress takibi** (job id + status sorgulama endpoint'i).
- [ ] Render adımı arka plan kuyruğunda (IP-3.5 ile uyumlu).

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** İlan ver → uçtan uca optimize PDF CV + ATS skoru otomatik üretiliyor.
- [ ] Test (entegrasyon): havuzu dolu bir kullanıcı + örnek ilan → `generated_cvs` kaydı + PDF + ats_score.
- [ ] Test: progress/durum endpoint'i adımları raporluyor.
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-3.6-graph2-orkestrasyon.md` yaz (graph dosyası, tetikleyici, progress mekanizması, uçtan uca kanıt).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (IP-3.7 frontend, IP-5.2 testler bunu kullanacak). Temiz çık.
