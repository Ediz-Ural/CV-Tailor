# Log - IP-2.6: Frontend havuz ekrani

- **DURUM:** TAMAMLANDI
- **Tarih:** 2026-06-18 19:09
- **Is paketi prompt'u:** `prompts/IP-2.6-frontend-havuz.md`
- **Bagimliliklar (dogrulandi mi?):** IP-2.1 tamamlandi; IP-1.4 tamamlandi.

## 1. On kontrol sonucu (FAZ A)
- `logs/IP-2.1-manuel-havuz.md` mevcut ve `DURUM: TAMAMLANDI`.
- `logs/IP-1.4-frontend-auth.md` mevcut ve `DURUM: TAMAMLANDI`.
- Disk kontrolu:
  - `backend/app/api/pool_items.py` mevcut; manuel `pool_items` CRUD endpointleri var.
  - `backend/app/api/pool.py` mevcut; `/pool/pending`, `/pool/approve`, `/pool/reject` endpointleri var.
  - `backend/app/api/github.py` mevcut; `/github/oauth/start` ve `/github/sync` endpointleri var.
  - `frontend/src/App.tsx`, `frontend/src/lib/api.ts`, `frontend/src/lib/auth.ts` mevcut; auth guard ve layout var.
- Canli backend kontrolu:
  ```text
  docker compose -f infra/docker-compose.yml --profile app up -d --no-build backend
  PowerShell Invoke-RestMethod: register -> login -> POST /pool-items -> GET /pool-items -> GET /pool/pending
  ```
- Cikti ozeti: manuel kayit `source=manual`, `verified_by_user=true`; liste sayisi `1`; pending endpointi HTTP 200 dondurdu.

## 2. Yapilan isler (FAZ B)
- [x] `/pool` korumali route eklendi; mevcut auth guard ve workspace layout icine baglandi.
- [x] Havuz listesi eklendi: kaynak etiketleri `pdf/github/manual`, tip filtreleri `experience/project/skill`, onay durumu, dil ve embedding boyutu gosteriliyor.
- [x] Skill/teknoloji ve tag etiketleri monospace stillendi.
- [x] Manuel ekleme formu eklendi; `POST /pool-items` ile `type`, `title`, `raw_content`, `tags`, `technologies` gonderiliyor.
- [x] Onay bekleyen otomatik ogeler icin `GET /pool/pending`, `POST /pool/approve`, `POST /pool/reject` UI aksiyonlari eklendi.
- [x] GitHub bagla ve sync butonlari eklendi; `/github/oauth/start` ve `/github/sync` cagrilari pipeline log stili monospace durum paneline yaziliyor.
- [x] Dark-mode-first, yogun veri ekranina uygun iki kolonlu havuz/list/form/pending/sync duzeni uygulandi.

## 3. Uretilen / degisen dosyalar
| Dosya | Tur | Kisa aciklama |
|---|---|---|
| `frontend/src/App.tsx` | degisti | `/pool` route, workspace navigation, havuz listesi, manuel form, pending approve/reject UI, GitHub sync paneli |
| `logs/IP-2.6-frontend-havuz.md` | yeni | Is paketi kanit kaydi |
| `state/PROGRESS.md` | degisti | IP-2.6 tamamlandi durumu |

## 4. DoD dogrulamasi (FAZ C)
- **DoD kriteri:** Kullanici havuzunu uc kaynaktan doldurup yonetebiliyor (en az manuel + pending onay akisi UI).
- **Calistirilan komutlar:**
  ```text
  npm run build
  npm run lint
  docker compose -f infra/docker-compose.yml exec -T backend sh -c "uv sync --frozen && uv run --no-sync pytest tests/test_pool_approval.py -q -p no:cacheprovider --basetemp=/tmp/ip26-pool-approval"
  PowerShell Invoke-RestMethod: register -> login -> POST /pool-items -> GET /pool-items -> seed pending pdf/github item -> POST /pool/approve
  ```
- **Cikti ozeti:**
  - `npm run build`: Vite 8.0.16 ile `2145 modules transformed`; `dist/` hatasiz uretildi.
  - `npm run lint`: ESLint hatasiz tamamlandi.
  - Canli akista `Manual DoD Project` olusturuldu ve listede `manual_listed=1` olarak goruldu.
  - Canli approve akisi `approved_count=1`, `approved_verified=true`, `approved_source=pdf` dondurdu.
  - Backend approval testi `2 passed, 2 warnings`; pending listeleme, approve, reject ve tenant izolasyonu dogrulandi.
- **Sonuc:** DoD karsilandi.

## 5. Kullanilan API'ler
- `GET /me`
- `GET /pool-items`
- `POST /pool-items`
- `GET /pool/pending`
- `POST /pool/approve`
- `POST /pool/reject`
- `POST /github/oauth/start`
- `POST /github/sync`

## 6. Sonraki paket icin notlar
- GitHub OAuth client env degerleri yoksa `/github/oauth/start` 500 dondurur; UI bunu pipeline log ve hata mesaji olarak gosterir.
- IP-3.7, ayni `WorkspaceShell` navigasyon desenini genisletebilir.
- Havuz listesi su an silme/duzenleme UI'i icermiyor; prompt kapsaminda manuel create ve pending onay akisi istendi.

## 7. Acik sorunlar / bayraklar
- PowerShell `Invoke-WebRequest` ile ham pending JSON tekrar kontrol denemesi yerel null referans hatasina dustu; `Invoke-RestMethod` approve yaniti ve backend approval testi onay durumunu dogruladi.
