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
    title="CV Tailor KVKK Aydınlatma Metni",
    explicit_consent_text=(
        "CV Tailor hesabımı oluşturarak profil, CV, iş ilanı ve GitHub kaynaklı kişisel "
        "verilerimin CV hazırlama, ilan uyumu analizi, profil havuzu yönetimi ve hizmet güvenliği "
        "amaçlarıyla işlenmesine açık rıza veriyorum."
    ),
    sections=[
        KvkkSection(
            title="Veri sorumlusu ve kapsam",
            body=(
                "CV Tailor, hesap oluşturma, profil yönetimi, CV üretimi ve GitHub entegrasyonu "
                "kapsamında kullanıcının sağladığı kişisel verileri işler."
            ),
        ),
        KvkkSection(
            title="İşlenen veri kategorileri",
            body=(
                "E-posta, parola hash'i, profil bilgileri, eğitim ve deneyim içerikleri, manuel/PDF/GitHub "
                "kaynaklı havuz öğeleri, ilan metinleri, üretilen CV içerikleri ve sistem güvenliği "
                "kayıtları işlenebilir."
            ),
        ),
        KvkkSection(
            title="İşleme amaçları",
            body=(
                "Veriler hesap kimlik doğrulaması, kullanıcıya ait profil havuzunun yönetimi, ilana göre CV "
                "uyarlama, ATS uyum skoru oluşturma, PDF üretimi, hizmet güvenliği ve hata ayıklama "
                "amaçlarıyla kullanılır."
            ),
        ),
        KvkkSection(
            title="Saklama ve silme",
            body=(
                "Veriler hesap aktif olduğu sürece saklanır. Hesap silme akışı tamamlandığında kullanıcıya ait "
                "tenant verileri cascade silme kurallarıyla kaldırılacak şekilde tasarlanır."
            ),
        ),
        KvkkSection(
            title="Haklar",
            body=(
                "Kullanıcı KVKK kapsamında verilerine erişim, düzeltme, silme, işlemeyi sınırlama ve rızasını "
                "geri çekme haklarını kullanabilir."
            ),
        ),
    ],
)


@router.get("/kvkk/aydinlatma", response_model=KvkkNoticeResponse)
def read_kvkk_notice() -> KvkkNoticeResponse:
    return KVKK_NOTICE
