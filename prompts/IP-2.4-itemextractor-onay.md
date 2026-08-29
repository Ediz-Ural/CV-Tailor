# PROMPT — IP-2.4: ItemExtractor + onay akışı

> Codex: **ÖNCE `architect.md` oku**, sonra 5 fazı (A→E) sırayla uygula. Tek paket, temiz oturum.

- **Slug:** `IP-2.4-itemextractor-onay`
- **Bağımlılıklar:** IP-2.2, IP-2.3
- **Referans:** PROJECT_CONTEXT §7 (Graph 1), §8 etik · IS_PAKETLERI İP-2.4

---

## FAZ A — ÖN KONTROL (önceki işleri DOĞRULA)
- [ ] `logs/IP-2.2-pdf-parser.md` ve `logs/IP-2.3-github-analiz.md` var ve `DURUM: TAMAMLANDI`.
- [ ] Diskte: PDF ve GitHub'dan `verified_by_user=false` öğeler üretiliyor.
> ⛔ Eksikse: `logs/BLOCKED-IP-2.4.md` yaz, DUR.

## FAZ B — GÖREV (checklist)
- [ ] ItemExtractor node: PDF + GitHub çıktılarını **tek `pool_items` formatına normalize** et
      (dil tespiti + embedding tutarlı). Tekrarlanan/çok benzer öğeleri tekille (opsiyonel, notla).
- [ ] Onay endpoint'leri:
      - `GET /pool/pending` → onay bekleyen (`verified_by_user=false`) öğeler.
      - `POST /pool/approve` (id listesi) → seçilenler `verified_by_user=true`.
      - `POST /pool/reject` (id listesi) → reddedilenler silinir/pasifleştirilir.
- [ ] **Etik kural:** Onaylanmadan hiçbir otomatik öğe `verified=true` olmaz (Selector yalnız verified seçer).

## FAZ C — DOĞRULAMA (DoD)
- [ ] **DoD:** Otomatik çıkarılan hiçbir öğe kullanıcı onayı olmadan CV'ye girmiyor.
- [ ] Test: pending listesi onaysızları gösteriyor → approve → `verified_by_user=true`; reject → kayıt gidiyor.
- [ ] Test: izolasyon (başka kullanıcının pending'ine erişilemiyor).
- [ ] Çıktıları logla.

## FAZ D — KAYIT
- [ ] `logs/IP-2.4-itemextractor-onay.md` yaz (normalize kuralları, onay/ret endpoint kanıtı).
- [ ] `state/PROGRESS.md` güncelle.

## FAZ E — ÇIKIŞ
- [ ] Özet ver (IP-2.5 bunları LangGraph'a bağlayacak). Temiz çık.
