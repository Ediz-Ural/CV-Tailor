from enum import Enum


class PoolItemSource(str, Enum):
    PDF = "pdf"
    GITHUB = "github"
    MANUAL = "manual"


class PoolItemType(str, Enum):
    EXPERIENCE = "experience"
    PROJECT = "project"
    SKILL = "skill"
    EDUCATION = "education"


class ContentLanguage(str, Enum):
    TR = "tr"
    EN = "en"
    MIXED = "mixed"
