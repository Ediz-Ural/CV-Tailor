<!-- Bu şablonu kopyalayıp logs/IP-<numara>-<slug>.md olarak doldur. Sadece KANIT yaz. -->

# Log — IP-<numara>: <başlık>

- **DURUM:** TAMAMLANDI | KISMİ | BLOCKED
- **Tarih:** <YYYY-AA-GG SS:DD>
- **İş paketi prompt'u:** prompts/IP-<numara>-<slug>.md
- **Bağımlılıklar (doğrulandı mı?):** IP-<x> ✅ / IP-<y> ✅

## 1. Ön kontrol sonucu (FAZ A)
- Hangi bağımlılık logları okundu, hangi dosyalar diske karşı doğrulandı:
  - `logs/IP-<x>.md` → DURUM: TAMAMLANDI ✅
  - Dosya kontrolü: `<yol>` var ✅
  - Doğrulama komutu: `<komut>` → çıktı özeti: <...> ✅

## 2. Yapılan işler (FAZ B)
Görev checklist'inin madde madde sonucu:
- [x] <madde 1> → üretilen/değişen dosya(lar): `<yol>`
- [x] <madde 2> → ...

## 3. Üretilen / değişen dosyalar
| Dosya | Tür (yeni/değişti) | Kısa açıklama |
|---|---|---|
| `<yol>` | yeni | <...> |

## 4. DoD doğrulaması (FAZ C)
- **DoD kriteri:** <prompt'tan kopyala>
- **Çalıştırılan komut(lar):**
  ```
  <komut>
  ```
- **Çıktı özeti:** <başarılı/başarısız + anahtar satırlar>
- **Sonuç:** DoD karşılandı ✅ / karşılanmadı ❌

## 5. Sonraki paket için notlar
- <bir sonraki İP'nin bilmesi gereken şeyler: portlar, env değişkenleri, şema isimleri, TODO'lar>

## 6. Açık sorunlar / bayraklar
- <yoksa "yok">
