# Veri Saklama ve Guvenlik Politikasi

## Kapsam

Bu politika CV Tailor icin hesap, profil, havuz ogeleri, is ilanlari, uretilen CV'ler,
PDF dosyalari ve GitHub OAuth token saklama davranisini tanimlar.

## Saklama

- Kullanici hesabi aktif oldugu surece `users`, `profiles`, `pool_items`, `jobs`,
  `generated_cvs` ve `github_connections` satirlari kullaniciya bagli olarak saklanir.
- Tum tenant verileri `user_id` ile izole edilir; tenant'a ait tablolarda `user_id`
  foreign key ve index bulunur.
- GitHub OAuth token degeri `github_connections.access_token_encrypted` alaninda
  Fernet ile sifreli saklanir. Sifreleme anahtari sadece ortam degiskeni
  `GITHUB_TOKEN_ENCRYPTION_KEY` uzerinden gelir.
- Parolalar `users.hashed_password` alaninda bcrypt hash olarak saklanir; plaintext
  parola veritabanina yazilmaz.
- JWT imzalama sirri `JWT_SECRET` ortam degiskeninden yonetilir. Uygulama JWT'nin
  kendisini veritabaninda saklamaz.

## Silme

- `DELETE /account` akisi yalnizca `confirmation="HESABIMI SIL"` degeriyle calisir.
- Hesap silindiginde `users` satiri silinir; `ondelete="CASCADE"` ile profil,
  havuz, ilan, uretilen CV ve GitHub baglanti satirlari kaldirilir.
- `generated_cvs.pdf_path` ile izlenen PDF dosyalari hesap silme akisi sirasinda
  dosya sisteminden silinir.

## Loglama

- Uygulama loglari token, parola, secret, Authorization header, JWT ve email icin
  merkezi redaksiyon filtresi kullanir.
- Loglarda GitHub token plaintext yazilmaz. Guvenlik testleri log redaksiyonunu ve
  paket loglarinda test token fixture'larinin bulunmadigini dogrular.

## Kod Uyumu

- Token sifreleme: `backend/app/core/security.py`
- Hassas log redaksiyonu: `backend/app/core/logging.py`
- GitHub token yazimi: `backend/app/api/github.py`
- GitHub token okuma/decrypt: `backend/app/services/github.py`,
  `backend/app/graphs/pool_graph.py`
- Hesap silme ve PDF temizligi: `backend/app/api/auth.py`
- Sema cascade kurallari: `backend/migrations/versions/20260613_0002_multi_tenant_schema.py`
- Guvenlik kontrolleri: `backend/tests/test_security_controls.py`
