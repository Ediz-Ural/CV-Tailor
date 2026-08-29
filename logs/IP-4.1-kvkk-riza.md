# Log - IP-4.1: KVKK riza ve aydinlatma

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-21 12:57
- **Is paketi prompt'u:** `prompts/IP-4.1-kvkk-riza.md`
- **Bagimliliklar (dogrulandi mi?):** IP-1.2 tamamlandi; log, register akisi ve `users.kvkk_consent_at` alani dogrulandi.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-1.2-auth-jwt.md` mevcut ve `DURUM: TAMAMLANDI`.
- `backend/app/api/auth.py` register akisi `kvkk_consent` false ise `400` donduruyor, true ise `kvkk_consent_at=datetime.now(UTC)` set ediyor.
- `backend/app/models/user.py` dosyasinda `kvkk_consent_at` alani mevcut.
- `backend/migrations/versions/20260613_0002_multi_tenant_schema.py` migration'i `users.kvkk_consent_at` kolonunu olusturuyor.

## 2. Yapilan isler (FAZ B)
- [x] Kayitta acik riza onayi zorunlulugu korundu; backend testinde rizasiz register reddi ve onayli register sonrasi `kvkk_consent_at` dolumu dogrulandi.
- [x] Public aydinlatma metni endpoint'i eklendi: `GET /kvkk/aydinlatma`.
- [x] Frontend kayit ekraninda aydinlatma ve acik riza metni API'den yuklenip goruntulenebilir hale getirildi.
- [x] Riza olmadan kayit backend dogrulamasi ile engelleniyor.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `backend/app/api/kvkk.py` | yeni | KVKK aydinlatma ve acik riza metni response modeli ve endpoint'i |
| `backend/app/main.py` | degisti | KVKK router uygulamaya baglandi |
| `backend/tests/test_auth.py` | degisti | Public aydinlatma endpoint'i testi eklendi; mevcut riza testi korundu |
| `frontend/src/App.tsx` | degisti | Kayit formu aydinlatma/acik riza metnini API'den yukleyip panelde gosteriyor |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Riza zamani kaydediliyor, aydinlatma metni erisilebilir.
- **Calistirilan komutlar:**
  ```text
  python -m pytest backend/tests/test_auth.py -q -p no:cacheprovider
  npm run build
  ```
- **Cikti ozeti:** Pytest `5 passed, 2 warnings` dondurdu. Frontend build `tsc -b && vite build` ile basarili tamamlandi.
- **Endpoint kaniti:** `test_kvkk_notice_is_public_and_contains_explicit_consent_text` testi `GET /kvkk/aydinlatma` icin `200`, `version=2026-06-21`, acik riza metni ve `Isleme amaclari` bolumunu dogruladi.
- **Riza kaniti:** `test_registration_requires_kvkk_consent_and_stores_a_hash` testi `kvkk_consent=false` icin `400`, onayli kayit sonrasi DB'de `kvkk_consent_at is not None` dogruladi.
- **Sonuc:** DoD karsilandi.

## 5. Sonraki paket icin notlar
- IP-4.2 hesap silme akisi, bu paketteki metinde belirtilen cascade silme beklentisini kod ve test ile dogrulamalidir.

## 6. Acik sorunlar / bayraklar
- Aydinlatma metni urun ici teknik taslak olarak eklendi; hukuki nihai metin icin uzman onayi gerekebilir.
