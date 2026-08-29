# BLOCKED - IP-0.3: Backend temel kurulum

- **DURUM:** BLOCKED
- **Tarih:** 2026-06-13
- **Is paketi:** `IP-0.3-backend-kurulum`

## Engelleyen kosul
- Zorunlu bagimlilik IP-0.2 tamamlanmamis.
- `logs/IP-0.2-docker-altyapi.md` mevcut, ancak `DURUM: BLOCKED` kaydi iceriyor; beklenen `DURUM: TAMAMLANDI` kaniti yok.
- IP-0.2 loguna gore Docker Desktop Linux engine erisilemedigi icin `db` servisi, healthcheck ve pgvector sorgusu dogrulanamamis.

## Disk kaniti
- `../infra/docker-compose.yml` mevcut.
- `../.env.example` mevcut.
- `../infra/initdb/01-extensions.sql` mevcut.
- Dosyalarin varligi, tamamlanmamis IP-0.2 DoD kosulunun yerine gecmez.

## Gerekli duzeltme
1. Docker Desktop Linux engine'i calisir hale getir.
2. IP-0.2 icin `docker compose -f infra/docker-compose.yml up -d db` komutunu, servis healthcheck'ini ve `vector` extension sorgusunu basariyla dogrula.
3. `logs/IP-0.2-docker-altyapi.md` dosyasini gercek kanitla `DURUM: TAMAMLANDI` olarak guncelle.
4. Ardindan IP-0.3 paketini temiz bir oturumda yeniden calistir.

## Bu oturumda yapilmayanlar
- Faz B-E uygulanmadi.
- Backend proje dosyalari veya proje durumu degistirilmedi.
