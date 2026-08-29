from fastapi import APIRouter
from pydantic import BaseModel


class KvkkSection(BaseModel):
    title: str
    body: str


class KvkkNoticeResponse(BaseModel):
    version: str
    title: str
    explicit_consent_text: str
    sections: list[KvkkSection]


router = APIRouter(tags=["kvkk"])

KVKK_NOTICE = KvkkNoticeResponse(
    version="2026-06-21",
    title="CV Tailor KVKK Aydinlatma Metni",
    explicit_consent_text=(
        "CV Tailor hesabimi olusturarak profil, CV, is ilani ve GitHub kaynakli kisisel "
        "verilerimin CV hazirlama, ilan uyumu analizi, profil havuzu yonetimi ve hizmet guvenligi "
        "amaclariyla islenmesine acik riza veriyorum."
    ),
    sections=[
        KvkkSection(
            title="Veri sorumlusu ve kapsam",
            body=(
                "CV Tailor, hesap olusturma, profil yonetimi, CV uretimi ve GitHub entegrasyonu "
                "kapsaminda kullanicinin sagladigi kisisel verileri isler."
            ),
        ),
        KvkkSection(
            title="Islenen veri kategorileri",
            body=(
                "Email, parola hash'i, profil bilgileri, egitim ve deneyim icerikleri, manuel/PDF/GitHub "
                "kaynakli havuz ogeleri, ilan metinleri, uretilen CV icerikleri ve sistem guvenligi kayitlari islenebilir."
            ),
        ),
        KvkkSection(
            title="Isleme amaclari",
            body=(
                "Veriler hesap kimlik dogrulamasi, kullaniciya ait profil havuzunun yonetimi, ilana gore CV "
                "uyarlama, ATS uyum skoru olusturma, PDF uretimi, hizmet guvenligi ve hata ayiklama amaclariyla kullanilir."
            ),
        ),
        KvkkSection(
            title="Saklama ve silme",
            body=(
                "Veriler hesap aktif oldugu surece saklanir. Hesap silme akisi tamamlandiginda kullaniciya ait "
                "tenant verileri cascade silme kurallariyla kaldirilacak sekilde tasarlanir."
            ),
        ),
        KvkkSection(
            title="Haklar",
            body=(
                "Kullanici KVKK kapsaminda verilerine erisim, duzeltme, silme, islemeyi sinirlama ve rizasini "
                "geri cekme haklarini kullanabilir."
            ),
        ),
    ],
)


@router.get("/kvkk/aydinlatma", response_model=KvkkNoticeResponse)
def read_kvkk_notice() -> KvkkNoticeResponse:
    return KVKK_NOTICE
