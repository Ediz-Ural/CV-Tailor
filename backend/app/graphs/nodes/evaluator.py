import difflib
from typing import TypedDict
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.graphs.nodes.cvtailor import TailoredCVContent, TailoredCVItem, load_selected_pool_items
from app.graphs.nodes.selector import SelectedPoolItem
from app.models.job import Job
from app.models.pool_item import PoolItem
from app.services.text_matching import normalize_text, semantic_keyword_lemmas

_CATEGORY_WEIGHTS = {
    "required_skills": 0.70,
    "preferred_skills": 0.20,
    "key_terms": 0.10,
}


class ATSKeywordMatch(BaseModel):
    keyword: str
    category: str
    matched: bool


class BeforeAfterDiff(BaseModel):
    source_pool_item_id: UUID
    title: str | None = None
    before: str
    after: str
    diff: str


class ATSEvaluation(BaseModel):
    ats_score: float = Field(ge=0.0, le=100.0)
    keyword_matches: list[ATSKeywordMatch] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    before_after_diff: list[BeforeAfterDiff] = Field(default_factory=list)


class EvaluatorState(TypedDict, total=False):
    user_id: UUID
    job_id: UUID
    db: Session
    selected_pool_items: list[SelectedPoolItem]
    tailored_cv: TailoredCVContent | None
    ats_evaluation: ATSEvaluation
    ats_score: float
    missing_keywords: list[str]
    ats_recommendations: list[str]
    before_after_diff: list[BeforeAfterDiff]


def _requirement_terms(job: Job) -> list[tuple[str, str]]:
    requirements = job.parsed_requirements_json or {}
    terms: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for category in _CATEGORY_WEIGHTS:
        values = requirements.get(category)
        if not isinstance(values, list):
            continue
        for value in values:
            keyword = str(value).strip()
            key = (category, normalize_text(keyword))
            if keyword and key not in seen:
                terms.append((category, keyword))
                seen.add(key)
    return terms


def _keyword_matches_cv(keyword: str, cv_lemmas: set[str]) -> bool:
    keyword_lemmas = semantic_keyword_lemmas(keyword)
    if not keyword_lemmas:
        return False
    if keyword_lemmas <= cv_lemmas:
        return True
    if len(keyword_lemmas) >= 3:
        overlap = len(keyword_lemmas & cv_lemmas) / len(keyword_lemmas)
        return overlap >= 0.6
    return False


def _score_matches(matches: list[ATSKeywordMatch]) -> float:
    total_weight = sum(_CATEGORY_WEIGHTS[match.category] for match in matches)
    if total_weight == 0:
        return 0.0
    matched_weight = sum(_CATEGORY_WEIGHTS[match.category] for match in matches if match.matched)
    return round((matched_weight / total_weight) * 100, 2)


def _ats_recommendations(job: Job, score: float, missing_keywords: list[str], selected_count: int) -> list[str]:
    language = job.detected_language.value
    is_tr = language == "tr"
    recommendations: list[str] = []

    if score >= 75:
        return recommendations

    if selected_count == 0:
        recommendations.append(
            "Bu ilanla eslesen onayli havuz ogesi yok. CV yukleyip cikan ilgili deneyim/proje/skill ogelerini onaylayin."
            if is_tr
            else "No verified pool item matched this job. Upload a CV and approve the relevant experience/project/skill items."
        )

    if missing_keywords:
        shown = ", ".join(missing_keywords[:8])
        recommendations.append(
            f"Ilana ait eksik sinyaller: {shown}. Gercek deneyiminizde varsa bu terimleri ilgili havuz ogelerine ekleyip onaylayin."
            if is_tr
            else f"Missing job signals: {shown}. If they are factual for your experience, add them to the relevant pool items and approve them."
        )

    if score < 50:
        recommendations.append(
            "Skor dusukse once profil havuzunu guclendirin: projeleri, staj/isyeri deneyimlerini, kullanilan teknolojileri ve olculebilir sonuclari ayri ogeler halinde girin."
            if is_tr
            else "If the score is low, strengthen the profile pool first: add projects, internships/work experience, technologies used, and measurable outcomes as separate items."
        )

    recommendations.append(
        "CV tekrar uretilmeden once onay bekleyen PDF/GitHub ogelerini kontrol edin; onaylanmayan otomatik cikarimlar CV'ye girmez."
        if is_tr
        else "Before regenerating the CV, review pending PDF/GitHub items; unapproved automatic extractions are not used in the CV."
    )
    return recommendations


def _tailored_items(content: TailoredCVContent | None) -> list[TailoredCVItem]:
    if content is None:
        return []
    return [*content.experience, *content.projects, *content.skills]


def _tailored_text(content: TailoredCVContent | None) -> str:
    if content is None:
        return ""
    parts = [content.summary]
    for item in _tailored_items(content):
        parts.extend([item.title or "", item.content, " ".join(item.technologies)])
    return "\n".join(parts)


def _unified_diff(before: str, after: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile="pool_item",
            tofile="tailored_cv",
            lineterm="",
        )
    )


def build_before_after_diff(
    source_items: list[PoolItem],
    tailored_cv: TailoredCVContent | None,
) -> list[BeforeAfterDiff]:
    source_by_id = {item.id: item for item in source_items}
    result: list[BeforeAfterDiff] = []
    for item in _tailored_items(tailored_cv):
        source = source_by_id.get(item.source_pool_item_id)
        if source is None:
            continue
        before = source.raw_content
        after = item.content
        result.append(
            BeforeAfterDiff(
                source_pool_item_id=source.id,
                title=item.title or source.title,
                before=before,
                after=after,
                diff=_unified_diff(before, after),
            )
        )
    return result


def evaluate_tailored_cv(job: Job, tailored_cv: TailoredCVContent | None, source_items: list[PoolItem]) -> ATSEvaluation:
    cv_lemmas = semantic_keyword_lemmas(_tailored_text(tailored_cv))
    keyword_matches = [
        ATSKeywordMatch(
            keyword=keyword,
            category=category,
            matched=_keyword_matches_cv(keyword, cv_lemmas),
        )
        for category, keyword in _requirement_terms(job)
    ]
    # A term listed under both required and preferred skills produced the same
    # keyword twice, and the UI rendered it twice.
    missing_keywords: list[str] = []
    seen_missing: set[str] = set()
    for match in keyword_matches:
        if match.matched:
            continue
        key = normalize_text(match.keyword)
        if key in seen_missing:
            continue
        seen_missing.add(key)
        missing_keywords.append(match.keyword)
    ats_score = _score_matches(keyword_matches)
    return ATSEvaluation(
        ats_score=ats_score,
        keyword_matches=keyword_matches,
        missing_keywords=missing_keywords,
        recommendations=_ats_recommendations(job, ats_score, missing_keywords, len(source_items)),
        before_after_diff=build_before_after_diff(source_items, tailored_cv),
    )


async def evaluator_node(state: EvaluatorState) -> dict[str, object]:
    db = state["db"]
    user_id = state["user_id"]
    job = db.scalar(select(Job).where(Job.id == state["job_id"], Job.user_id == user_id))
    if job is None:
        empty = ATSEvaluation(ats_score=0.0)
        return {
            "ats_evaluation": empty,
            "ats_score": empty.ats_score,
            "missing_keywords": empty.missing_keywords,
            "ats_recommendations": empty.recommendations,
            "before_after_diff": empty.before_after_diff,
        }

    source_items = load_selected_pool_items(db, user_id, state.get("selected_pool_items", []))
    evaluation = evaluate_tailored_cv(job, state.get("tailored_cv"), source_items)
    return {
        "ats_evaluation": evaluation,
        "ats_score": evaluation.ats_score,
        "missing_keywords": evaluation.missing_keywords,
        "ats_recommendations": evaluation.recommendations,
        "before_after_diff": evaluation.before_after_diff,
    }
