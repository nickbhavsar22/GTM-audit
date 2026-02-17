"""Enums, agent names, scoring thresholds, and other constants."""

from enum import Enum


class AuditType(str, Enum):
    QUICK = "quick"
    FULL = "full"


class AuditStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentName(str, Enum):
    WEB_SCRAPER = "web_scraper"
    SCREENSHOT = "screenshot"
    COMPANY_RESEARCH = "company_research"
    COMPETITOR = "competitor"
    REVIEW_SENTIMENT = "review_sentiment"
    SEO = "seo"
    MESSAGING = "messaging"
    VISUAL_DESIGN = "visual_design"
    CONVERSION = "conversion"
    SOCIAL = "social"
    ICP = "icp"
    REPORT = "report"


AGENT_DISPLAY_NAMES: dict[str, str] = {
    AgentName.WEB_SCRAPER: "Web Scraper",
    AgentName.SCREENSHOT: "Visual Screenshot Capture",
    AgentName.COMPANY_RESEARCH: "Company Research",
    AgentName.COMPETITOR: "Competitor Intelligence",
    AgentName.REVIEW_SENTIMENT: "Reviews & Sentiment",
    AgentName.SEO: "SEO & Visibility",
    AgentName.MESSAGING: "Messaging & Positioning",
    AgentName.VISUAL_DESIGN: "Visual & Design",
    AgentName.CONVERSION: "Conversion Optimization",
    AgentName.SOCIAL: "Social & Engagement",
    AgentName.ICP: "ICP & Segmentation",
    AgentName.REPORT: "Report Generation",
}

ALL_AGENT_NAMES: list[str] = [a.value for a in AgentName]

# Agents that run in a quick audit (subset)
QUICK_AUDIT_AGENTS: list[str] = [
    AgentName.WEB_SCRAPER,
    AgentName.SCREENSHOT,
    AgentName.COMPANY_RESEARCH,
    AgentName.SEO,
    AgentName.MESSAGING,
    AgentName.COMPETITOR,
    AgentName.REPORT,
]


class Grade(str, Enum):
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    C_PLUS = "C+"
    C = "C"
    C_MINUS = "C-"
    D = "D"
    F = "F"


GRADE_THRESHOLDS: list[tuple[float, Grade]] = [
    (95, Grade.A_PLUS),
    (90, Grade.A),
    (85, Grade.A_MINUS),
    (80, Grade.B_PLUS),
    (75, Grade.B),
    (70, Grade.B_MINUS),
    (65, Grade.C_PLUS),
    (60, Grade.C),
    (55, Grade.C_MINUS),
    (40, Grade.D),
    (0, Grade.F),
]


def score_to_grade(score: float) -> Grade:
    """Convert a 0-100 score to a letter grade."""
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return Grade.F


class Impact(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Effort(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
