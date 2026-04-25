"""
comparator.py — Core diff engine.
Compares two normalized text strings and produces structured change records.
Detects: additions, removals, modifications, material changes, and moved paragraphs.
"""

import re
import difflib
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ─── Material Change Patterns ─────────────────────────────────────────────────

LEGAL_KEYWORDS = {
    "termination", "terminate", "liability", "indemnity", "indemnification",
    "warranty", "warranties", "confidentiality", "confidential", "arbitration",
    "jurisdiction", "governing law", "force majeure", "intellectual property",
    "assignment", "sublicense", "penalty", "penalties", "breach", "damages",
    "remedy", "remedies", "dispute", "obligation", "covenant", "waiver",
    "compliance", "default", "forfeiture", "lien", "escrow", "guarantee",
    "obligation", "exclusivity", "non-compete", "non-solicitation",
}

NUMBER_PATTERN = re.compile(
    r"""
    (?:
        \$\s*[\d,]+(?:\.\d{1,2})?          |  # monetary: $1,000.00
        [\d,]+(?:\.\d{1,2})?\s*%            |  # percentage: 15.5%
        \b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b   |  # plain numbers: 30, 1,000
        \b\d{4}-\d{2}-\d{2}\b               |  # ISO date: 2024-01-15
        \b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|
           Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|
           Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}\b  # human date: January 15, 2024
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _extract_numbers(text: str) -> List[str]:
    return NUMBER_PATTERN.findall(text)


def _has_legal_keyword(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in LEGAL_KEYWORDS)


def classify_material_change(old_text: str, new_text: str) -> List[str]:
    """Return list of material change tags for a modification."""
    tags = []
    old_nums = set(_extract_numbers(old_text))
    new_nums = set(_extract_numbers(new_text))
    changed_nums = (old_nums | new_nums) - (old_nums & new_nums)
    if changed_nums:
        # Distinguish monetary vs date vs plain number
        for n in changed_nums:
            if "$" in n:
                tags.append("💰 Monetary Value")
            elif re.search(r"%", n):
                tags.append("📊 Percentage")
            elif re.search(r"\d{4}-\d{2}-\d{2}|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec", n, re.I):
                tags.append("📅 Date/Deadline")
            else:
                tags.append("🔢 Number Change")

    if _has_legal_keyword(old_text) or _has_legal_keyword(new_text):
        tags.append("⚖️  Legal Term")

    return list(dict.fromkeys(tags))  # deduplicate, preserve order


# ─── Data Structures ──────────────────────────────────────────────────────────

@dataclass
class Change:
    change_type: str          # "added" | "removed" | "modified" | "moved"
    old_line_num: Optional[int] = None
    new_line_num: Optional[int] = None
    old_para_num: Optional[int] = None
    new_para_num: Optional[int] = None
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    similarity: float = 1.0
    material_tags: List[str] = field(default_factory=list)
    is_material: bool = False
    group_id: Optional[int] = None  # for nearby-change grouping


@dataclass
class ComparisonResult:
    changes: List[Change]
    old_line_count: int
    new_line_count: int
    old_para_count: int
    new_para_count: int
    stats: dict


# ─── Similarity ───────────────────────────────────────────────────────────────

def _similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def _strip_punctuation(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text).strip()


# ─── Paragraph Segmentation ───────────────────────────────────────────────────

def split_into_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs at blank lines."""
    paras = re.split(r"\n{2,}", text)
    return [p.strip() for p in paras if p.strip()]


def split_into_lines(text: str) -> List[str]:
    return text.split("\n")


# ─── Moved Paragraph Detection ────────────────────────────────────────────────

def detect_moved_paragraphs(
    old_paras: List[str], new_paras: List[str], threshold: float = 0.92
) -> List[Tuple[int, int]]:
    """
    Returns list of (old_idx, new_idx) pairs for paragraphs that appear
    to have moved (high similarity but different position).
    """
    moved = []
    for oi, op in enumerate(old_paras):
        for ni, np_ in enumerate(new_paras):
            if oi != ni and _similarity(op, np_) >= threshold:
                moved.append((oi, ni))
    return moved


# ─── Main Comparison ──────────────────────────────────────────────────────────

def compare_documents(
    old_text: str,
    new_text: str,
    ignore_punctuation: bool = False,
    similarity_threshold: float = 0.60,
) -> ComparisonResult:
    """
    Full comparison pipeline:
    1. Line-by-line diff for positional awareness
    2. Paragraph-level diff for semantic grouping
    3. Material change classification
    4. Nearby-change grouping
    """
    old_lines = split_into_lines(old_text)
    new_lines = split_into_lines(new_text)
    old_paras = split_into_paragraphs(old_text)
    new_paras = split_into_paragraphs(new_text)

    # --- Line-level diff via difflib ---
    matcher = difflib.SequenceMatcher(
        isjunk=lambda x: x.strip() == "",
        a=old_lines,
        b=new_lines,
        autojunk=False,
    )

    changes: List[Change] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        old_block = old_lines[i1:i2]
        new_block = new_lines[j1:j2]

        if tag == "delete":
            for rel, line in enumerate(old_block):
                if not line.strip():
                    continue
                c = Change(
                    change_type="removed",
                    old_line_num=i1 + rel + 1,
                    old_text=line,
                )
                c.material_tags = classify_material_change(line, "")
                c.is_material = bool(c.material_tags)
                changes.append(c)

        elif tag == "insert":
            for rel, line in enumerate(new_block):
                if not line.strip():
                    continue
                c = Change(
                    change_type="added",
                    new_line_num=j1 + rel + 1,
                    new_text=line,
                )
                c.material_tags = classify_material_change("", line)
                c.is_material = bool(c.material_tags)
                changes.append(c)

        elif tag == "replace":
            # Try to pair up old↔new lines by similarity
            paired = _pair_lines(old_block, new_block, i1, j1)
            for c in paired:
                if ignore_punctuation:
                    stripped_old = _strip_punctuation(c.old_text or "")
                    stripped_new = _strip_punctuation(c.new_text or "")
                    if stripped_old == stripped_new:
                        continue
                c.material_tags = classify_material_change(
                    c.old_text or "", c.new_text or ""
                )
                c.is_material = bool(c.material_tags)
                changes.append(c)

    # --- Enrich with paragraph numbers ---
    _assign_paragraph_numbers(changes, old_paras, new_paras)

    # --- Detect moved paragraphs ---
    moved_pairs = detect_moved_paragraphs(old_paras, new_paras)
    _mark_moved(changes, moved_pairs, old_paras, new_paras)

    # --- Group nearby changes ---
    _group_nearby_changes(changes, proximity=3)

    # --- Stats ---
    stats = _compute_stats(changes, old_lines, new_lines, old_paras, new_paras)

    return ComparisonResult(
        changes=changes,
        old_line_count=len(old_lines),
        new_line_count=len(new_lines),
        old_para_count=len(old_paras),
        new_para_count=len(new_paras),
        stats=stats,
    )


def _pair_lines(
    old_block: List[str],
    new_block: List[str],
    i1: int,
    j1: int,
) -> List[Change]:
    """
    Pair old lines with new lines in a replace block.
    Uses similarity scoring to match lines that are clearly related.
    Unmatched lines become pure additions/removals.
    """
    changes = []
    used_new = set()

    for oi, old_line in enumerate(old_block):
        if not old_line.strip():
            continue
        best_sim = 0.0
        best_ni = -1
        for ni, new_line in enumerate(new_block):
            if ni in used_new or not new_line.strip():
                continue
            sim = _similarity(old_line, new_line)
            if sim > best_sim:
                best_sim = sim
                best_ni = ni

        if best_ni >= 0 and best_sim >= 0.35:
            used_new.add(best_ni)
            new_line = new_block[best_ni]
            if best_sim >= 0.98:
                continue  # effectively equal
            changes.append(Change(
                change_type="modified",
                old_line_num=i1 + oi + 1,
                new_line_num=j1 + best_ni + 1,
                old_text=old_line,
                new_text=new_line,
                similarity=round(best_sim, 3),
            ))
        else:
            # No good match — pure removal
            changes.append(Change(
                change_type="removed",
                old_line_num=i1 + oi + 1,
                old_text=old_line,
            ))

    # Remaining new lines that were never paired → pure additions
    for ni, new_line in enumerate(new_block):
        if ni not in used_new and new_line.strip():
            changes.append(Change(
                change_type="added",
                new_line_num=j1 + ni + 1,
                new_text=new_line,
            ))

    return changes


def _assign_paragraph_numbers(
    changes: List[Change],
    old_paras: List[str],
    new_paras: List[str],
):
    """Assign paragraph numbers to each change by text lookup."""
    for c in changes:
        if c.old_text:
            for pi, para in enumerate(old_paras):
                if c.old_text.strip() in para:
                    c.old_para_num = pi + 1
                    break
        if c.new_text:
            for pi, para in enumerate(new_paras):
                if c.new_text.strip() in para:
                    c.new_para_num = pi + 1
                    break


def _mark_moved(
    changes: List[Change],
    moved_pairs: List[Tuple[int, int]],
    old_paras: List[str],
    new_paras: List[str],
):
    """Promote matching changes to 'moved' type if they appear in moved_pairs."""
    moved_set = {(oi + 1, ni + 1) for oi, ni in moved_pairs}
    for c in changes:
        if (c.old_para_num, c.new_para_num) in moved_set:
            c.change_type = "moved"


def _group_nearby_changes(changes: List[Change], proximity: int = 3):
    """
    Assign group IDs to changes that are close together by line number,
    so the UI can visually cluster them.
    """
    group_id = 0
    last_line = -999

    for c in sorted(
        changes,
        key=lambda x: x.old_line_num or x.new_line_num or 0,
    ):
        current_line = c.old_line_num or c.new_line_num or 0
        if current_line - last_line <= proximity:
            c.group_id = group_id
        else:
            group_id += 1
            c.group_id = group_id
        last_line = current_line


def _compute_stats(
    changes, old_lines, new_lines, old_paras, new_paras
) -> dict:
    added = sum(1 for c in changes if c.change_type == "added")
    removed = sum(1 for c in changes if c.change_type == "removed")
    modified = sum(1 for c in changes if c.change_type == "modified")
    moved = sum(1 for c in changes if c.change_type == "moved")
    material = sum(1 for c in changes if c.is_material)
    return {
        "total_changes": len(changes),
        "added": added,
        "removed": removed,
        "modified": modified,
        "moved": moved,
        "material_changes": material,
        "old_lines": len(old_lines),
        "new_lines": len(new_lines),
        "old_paragraphs": len(old_paras),
        "new_paragraphs": len(new_paras),
    }
