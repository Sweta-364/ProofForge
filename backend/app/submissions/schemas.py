from typing import Optional
from pydantic import BaseModel


class ScoreBreakdown(BaseModel):
    correctness: int   # 0–30
    code_quality: int  # 0–25
    performance: int   # 0–20
    security: int      # 0–15
    tests: int         # 0–10


class InlineComment(BaseModel):
    file: str
    line: int
    severity: str   # "praise" | "info" | "warning" | "error"
    comment: str


class LearningResource(BaseModel):
    title: str
    url: str
    why: str


class ReviewOutput(BaseModel):
    verdict: str                              # "accept" | "minor_revisions" | "major_revisions"
    overall_score: int
    score_breakdown: ScoreBreakdown
    summary: str
    inline_comments: list[InlineComment]
    learning_resources: Optional[list[LearningResource]] = None
    architectural_note: Optional[str] = None
