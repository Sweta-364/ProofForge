"""
AI review pipeline: AST analysis (tree-sitter) → security scan (bandit) → Claude review.
"""
import asyncio
import difflib
import json
import logging
from pathlib import Path

import anthropic

from app.config import settings
from app.submissions.prompts import REVIEW_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class ReviewPipeline:
    def __init__(self):
        self.anthropic_client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # ── AST analysis ────────────────────────────────────────────────────────────

    async def run_ast_analysis(self, code_files: dict[str, str]) -> dict:
        """Parse Python files with tree-sitter and return quality metrics."""
        import tree_sitter_python as tspython
        from tree_sitter import Language, Parser

        PY_LANGUAGE = Language(tspython.language())
        parser = Parser(PY_LANGUAGE)

        results: dict = {
            "anti_patterns": [],
            "max_complexity": 0,
            "max_nesting": 0,
            "issues": [],
            "overall_ast_score": 100,
        }

        for filepath, content in code_files.items():
            if not filepath.endswith(".py"):
                continue
            tree = parser.parse(bytes(content, "utf-8"))
            self._check_global_mutable_state(tree, content, results)
            complexity = self._estimate_complexity(tree, content)
            results["max_complexity"] = max(results["max_complexity"], complexity)
            nesting = self._max_nesting_depth(tree)
            results["max_nesting"] = max(results["max_nesting"], nesting)

        score = 100
        score -= len(results["anti_patterns"]) * 10
        if results["max_complexity"] > 10:
            score -= (results["max_complexity"] - 10) * 3
        if results["max_nesting"] > 4:
            score -= (results["max_nesting"] - 4) * 5
        results["overall_ast_score"] = max(0, score)
        return results

    def _check_global_mutable_state(self, tree, content: str, results: dict) -> None:
        """Detect module-level mutable container assignments."""
        lines = content.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Only top-level lines (no leading indent)
            if (
                not line.startswith(" ")
                and not line.startswith("\t")
                and "=" in stripped
                and any(token in stripped for token in ["{}", "[]", "set()"])
            ):
                results["anti_patterns"].append(
                    f"global_mutable_state at line {i + 1}: {stripped[:60]}"
                )

    def _estimate_complexity(self, tree, content: str) -> int:
        keywords = ["if ", "elif ", "for ", "while ", "except ", "and ", "or "]
        return sum(content.count(kw) for kw in keywords) + 1

    def _max_nesting_depth(self, tree) -> int:
        max_indent = 0
        for line in tree.root_node.text.decode("utf-8").split("\n"):
            indent = len(line) - len(line.lstrip())
            max_indent = max(max_indent, indent // 4)
        return max_indent

    # ── Security scan ───────────────────────────────────────────────────────────

    async def run_security_scan(self, submission_dir: Path) -> dict:
        """Run Bandit over submitted Python files; never crash the pipeline."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "bandit", "-r", str(submission_dir), "-f", "json", "-q",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            raw = json.loads(stdout.decode()) if stdout else {"results": []}
            findings = raw.get("results", [])

            score = 15
            for f in findings:
                sev = f.get("issue_severity", "")
                if sev == "HIGH":
                    score -= 5
                elif sev == "MEDIUM":
                    score -= 3
                else:
                    score -= 1

            return {
                "findings": [
                    {
                        "severity": f["issue_severity"],
                        "issue": f["issue_text"],
                        "line": f["line_number"],
                        "file": Path(f["filename"]).name,
                    }
                    for f in findings[:10]
                ],
                "security_score": max(0, score),
            }
        except Exception as e:
            logger.warning("Security scan failed: %s", e)
            return {"findings": [], "security_score": 15}

    # ── Claude review ───────────────────────────────────────────────────────────

    async def call_claude_review(
        self,
        problem_meta: dict,
        code_files: dict[str, str],
        test_results: dict,
        ast_output: dict,
        security_output: dict,
        original_files: dict[str, str],
    ) -> dict:
        """Call Claude API with structured context; return parsed review JSON."""
        diff_lines: list[str] = []
        for filepath, content in code_files.items():
            original = original_files.get(filepath, "")
            if original != content:
                orig_lines = original.splitlines(keepends=True)
                new_lines = content.splitlines(keepends=True)
                diff = list(
                    difflib.unified_diff(
                        orig_lines, new_lines,
                        fromfile=f"a/{filepath}",
                        tofile=f"b/{filepath}",
                    )
                )
                diff_lines.extend(diff[:100])

        nl = "\n"
        failing_tests = [
            t for t in test_results.get("tests", []) if t["status"] != "passed"
        ]
        fail_lines = nl.join(
            f"  FAIL: {t['name']} — {str(t.get('error', ''))[:200]}"
            for t in failing_tests[:5]
        )

        file_dump = nl.join(
            f"=== {fp} ==={nl}{content}"
            for fp, content in list(code_files.items())[:3]
        )

        security_lines = nl.join(
            f"  {f['severity']}: {f['issue']} (line {f['line']})"
            for f in security_output["findings"][:5]
        )

        user_prompt = f"""ISSUE BEING FIXED:
Title: {problem_meta['title']}
Difficulty: {problem_meta['difficulty']}
Description: {str(problem_meta.get('description', ''))[:800]}

CODE DIFF (student's changes vs original broken code):
{"".join(diff_lines) if diff_lines else "No diff available — full file submitted"}

FULL SUBMITTED CODE:
{file_dump}

TEST RESULTS:
- Total: {test_results['total']} tests
- Passed: {test_results['passed']}
- Failed: {test_results['failed']}
- Status: {test_results['status']}
{fail_lines}

AST ANALYSIS:
- Cyclomatic complexity: ~{ast_output['max_complexity']}
- Max nesting depth: {ast_output['max_nesting']}
- Anti-patterns: {', '.join(ast_output['anti_patterns']) or 'none detected'}
- AST quality score: {ast_output['overall_ast_score']}/100

SECURITY SCAN:
- Findings: {len(security_output['findings'])}
{security_lines}

REVIEWER NOTE (not shown to student):
{problem_meta.get('optimal_hint', 'No hint available')}"""

        raw_text = ""
        try:
            provider = settings.REVIEW_PROVIDER.lower()
            if provider == "mock":
                logger.info("REVIEW_PROVIDER=mock — returning deterministic dev review")
                return self._mock_review(test_results, ast_output, security_output)
            if provider == "openai_compat":
                raw_text = await self._call_openai_compat(user_prompt)
            else:
                response = self.anthropic_client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=1500,
                    system=REVIEW_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                raw_text = response.content[0].text
            review = json.loads(raw_text)
            required = [
                "verdict", "overall_score", "score_breakdown",
                "summary", "inline_comments", "learning_resources",
            ]
            for field in required:
                if field not in review:
                    raise ValueError(f"Missing required field: {field}")
            return review
        except json.JSONDecodeError as e:
            logger.error("Claude review JSON parse failed: %s. Raw: %s", e, raw_text[:500])
            return {"error": "review_parse_failed", "raw": raw_text[:200]}
        except Exception as e:
            logger.error("Claude review pipeline error: %s", e)
            return {"error": "review_unavailable", "message": str(e)}

    # ── Dev-only review providers ────────────────────────────────────────────

    async def _call_openai_compat(self, user_prompt: str) -> str:
        """Call any OpenAI-compatible chat completions API (Groq, Gemini,
        OpenRouter — all have free tiers) using the DEV_LLM_* settings."""
        import httpx

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.DEV_LLM_BASE_URL.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.DEV_LLM_API_KEY}"},
                json={
                    "model": settings.DEV_LLM_MODEL,
                    "max_tokens": 1500,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                },
            )
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]

        # Free-tier models often wrap JSON in markdown fences despite json mode
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text
            text = text.rsplit("```", 1)[0]
        return text.strip()

    def _mock_review(
        self, test_results: dict, ast_output: dict, security_output: dict
    ) -> dict:
        """Deterministic schema-valid review built from pipeline signals —
        lets the full submit→review→portfolio flow run with no LLM key."""
        all_passed = test_results.get("failed", 1) == 0
        correctness = 30 if all_passed else 10
        code_quality = min(25, ast_output.get("overall_ast_score", 0) // 4)
        security = min(20, security_output.get("security_score", 0))
        testing = 15 if all_passed else 5
        overall = correctness + code_quality + security + testing
        return {
            "verdict": "accept" if all_passed and overall >= 60 else "major_revisions",
            "overall_score": overall,
            "score_breakdown": {
                "correctness": correctness,
                "code_quality": code_quality,
                "security": security,
                "testing": testing,
            },
            "summary": (
                "[MOCK REVIEW — REVIEW_PROVIDER=mock] "
                + (
                    "All tests pass and no blocking issues were detected."
                    if all_passed
                    else f"{test_results.get('failed', '?')} test(s) still failing — fix them before resubmitting."
                )
            ),
            "inline_comments": [],
            "learning_resources": [
                {
                    "title": "ProofForge mock review mode",
                    "url": "https://localhost/dev-docs",
                    "relevance": "Set REVIEW_PROVIDER=openai_compat or anthropic for real AI reviews",
                }
            ],
            "architectural_note": "Generated without an LLM (dev mock mode).",
        }


# Module-level singleton
review_pipeline = ReviewPipeline()
