"""Scoring system — dataclasses for scores, recommendations, and audit reports."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from config.constants import Grade, Impact, Effort, score_to_grade


class MatrixPlacement(str, Enum):
    """Priority matrix quadrant."""
    QUICK_WIN = "Quick Win"          # High impact, Low effort
    STRATEGIC_BET = "Strategic Bet"  # High impact, High effort
    LOW_HANGING = "Low Hanging"      # Low impact, Low effort
    DISTRACTION = "Distraction"      # Low impact, High effort


@dataclass
class Recommendation:
    """A single actionable recommendation from an audit."""
    area: str                                   # e.g., "SEO", "Messaging"
    issue: str                                  # What's wrong
    recommendation: str                         # What to do
    current_state: str = ""                     # Description of current state
    best_practice: str = ""                     # Industry standard
    impact: Impact = Impact.MEDIUM
    effort: Effort = Effort.MEDIUM
    implementation_steps: list[str] = field(default_factory=list)
    success_metrics: list[str] = field(default_factory=list)
    timeline: str = ""                          # e.g., "1-2 weeks"
    screenshot_ref: str = ""                    # Reference to screenshot

    @property
    def priority_score(self) -> int:
        """Higher score = higher priority (impact high + effort low = best)."""
        impact_scores = {Impact.HIGH: 3, Impact.MEDIUM: 2, Impact.LOW: 1}
        effort_scores = {Effort.LOW: 3, Effort.MEDIUM: 2, Effort.HIGH: 1}
        return impact_scores[self.impact] * effort_scores[self.effort]

    @property
    def matrix_placement(self) -> MatrixPlacement:
        if self.impact == Impact.HIGH and self.effort in (Effort.LOW, Effort.MEDIUM):
            return MatrixPlacement.QUICK_WIN
        elif self.impact == Impact.HIGH and self.effort == Effort.HIGH:
            return MatrixPlacement.STRATEGIC_BET
        elif self.impact in (Impact.LOW, Impact.MEDIUM) and self.effort == Effort.LOW:
            return MatrixPlacement.LOW_HANGING
        else:
            return MatrixPlacement.DISTRACTION


@dataclass
class ScoreItem:
    """An individual scoring criterion within a module."""
    name: str
    score: float            # 0-100
    max_score: float = 100
    weight: float = 1.0
    notes: str = ""

    @property
    def percentage(self) -> float:
        if self.max_score == 0:
            return 0
        return (self.score / self.max_score) * 100


@dataclass
class ModuleScore:
    """Score for a single analysis module (e.g., SEO, Messaging)."""
    name: str                                           # Module display name
    agent_name: str                                     # Agent identifier
    items: list[ScoreItem] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    analysis_text: str = ""                             # Human-readable analysis
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)  # Screenshot references
    extra_data: dict = field(default_factory=dict)  # Agent-specific data (competitors, pillars, etc.)

    @property
    def percentage(self) -> float:
        if not self.items:
            return 0
        total_weight = sum(item.weight for item in self.items)
        if total_weight == 0:
            return 0
        weighted_sum = sum(item.percentage * item.weight for item in self.items)
        return weighted_sum / total_weight

    @property
    def grade(self) -> Grade:
        return score_to_grade(self.percentage)


@dataclass
class AuditReport:
    """Aggregate report for the entire audit."""
    company_name: str = ""
    company_url: str = ""
    audit_type: str = "full"
    audit_date: str = ""
    modules: list[ModuleScore] = field(default_factory=list)

    @property
    def overall_percentage(self) -> float:
        scored_modules = [m for m in self.modules if m.items]
        if not scored_modules:
            return 0
        return sum(m.percentage for m in scored_modules) / len(scored_modules)

    @property
    def overall_grade(self) -> Grade:
        return score_to_grade(self.overall_percentage)

    def get_all_recommendations(self) -> list[Recommendation]:
        """Get all recommendations sorted by priority score (highest first)."""
        recs = []
        for module in self.modules:
            recs.extend(module.recommendations)
        return sorted(recs, key=lambda r: r.priority_score, reverse=True)

    def get_quick_wins(self, limit: int = 5) -> list[Recommendation]:
        """Get top quick wins (high impact, low effort)."""
        return [
            r
            for r in self.get_all_recommendations()
            if r.matrix_placement == MatrixPlacement.QUICK_WIN
        ][:limit]

    def get_top_strengths(self, limit: int = 5) -> list[str]:
        strengths = []
        for module in self.modules:
            for s in module.strengths:
                strengths.append(f"[{module.name}] {s}")
        return strengths[:limit]

    def get_critical_gaps(self, limit: int = 5) -> list[str]:
        weaknesses = []
        for module in self.modules:
            for w in module.weaknesses:
                weaknesses.append(f"[{module.name}] {w}")
        return weaknesses[:limit]
