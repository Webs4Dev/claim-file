from hashlib import sha256
from pathlib import Path
import re

import pymupdf
from pydantic import BaseModel

from tools.documents import PDF_TEXT_FLAGS


# Page furniture repeated on every page. Matched from the start of the line.
NOISE_LINE_PATTERNS = [
    r"^Page \d+ of \d+$",
    r"^Auto Secure - Private Car Package Policy$",
    r"^Policy Wordings$",
    r"^Registered office:",
    r"^24\*7 Customer Support No\.:",
    r"^IRDA of India Registration No\.:",
]


# Top-level parts of a policy. A new part resets the sub-heading, so every
# chunk records which section (Section I, an IMT endorsement, a TA add-on)
# it belongs to. "Section I of the Policy ..." is a sentence, not a heading,
# so a dash or colon must follow the numeral.
PART_HEADING_PATTERNS = [
    r"^Section\s+[IVX]+\s*[–\-:]",
    r"^General Exceptions\s*:",
    r"^General Conditions\s*:",
    r"^IMT\s?\d+[A-Z]?\b",
    r"^TA\d+\b",
    r"^Auto Secure .*Add-On Covers:",
    r"^IDV and TL/CTL Criteria",
]


SUB_HEADING_PATTERNS = [
    r"^(?:[IV]+\.\s*)?What is (?:not )?covered\s*:",
    r"^Definitions?\s*:",
    r"^Special Conditions?\b.*:$",
    r"^Specific Conditions?\s*:",
    r"^Coverage Conditions?\s*:",
    r"^Coverage\s*:",
    r"^Important Conditions?\s*:",
    r"^Deductible\s*:",
    r"^No Claim Bonus\s*:?",
    r"^[A-E]\)\s+.*Conditions?\b.*:$",
    r"^Sum Insured\b.*:$",
    r"^The Schedule of Depreciation\b.*:$",
    r"^Insured.s Declared Value \(IDV\) Basis$",
    r"^Total Loss \(TL\)",
]


# Case-sensitive: only genuine ALL-CAPS lines count as headings.
ALL_CAPS_HEADING_RE = re.compile(
    r"^[A-Z][A-Z &/\-]{4,60}$"
)


# Only top-level numbered clauses ("1.", "2.") start a new chunk. Sub-clauses
# such as "i.", "a)" and bullets stay with their parent clause.
CLAUSE_START_RE = re.compile(
    r"^\d+\.\s+"
)


MIN_CLAUSE_CHUNK_CHARS = 500

MIN_CHUNK_CHARS = 200


class PolicyChunk(BaseModel):
    chunk_id: str
    source: str
    product: str
    document_type: str
    page_start: int
    page_end: int
    section: str | None
    text: str


def clean_line(line: str) -> str:
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def is_noise(line: str) -> bool:
    return any(
        re.match(pattern, line)
        for pattern in NOISE_LINE_PATTERNS
    )


def clean_page_text(text: str) -> list[str]:
    lines = []

    for raw_line in text.splitlines():
        line = clean_line(raw_line)

        if not line:
            continue

        if is_noise(line):
            continue

        lines.append(line)

    return lines


def is_part_heading(line: str) -> bool:
    return any(
        re.match(pattern, line)
        for pattern in PART_HEADING_PATTERNS
    )


def is_sub_heading(line: str) -> bool:
    if ALL_CAPS_HEADING_RE.match(line):
        return True

    return any(
        re.match(pattern, line, re.IGNORECASE)
        for pattern in SUB_HEADING_PATTERNS
    )


def is_clause_start(line: str) -> bool:
    return bool(CLAUSE_START_RE.match(line))


def format_section(
    part: str | None,
    sub: str | None,
) -> str | None:
    if part and sub:
        return f"{part} > {sub}"

    return part or sub


def create_chunk(
    lines: list[str],
    page_start: int,
    page_end: int,
    source: str,
    product: str,
    document_type: str,
    section: str | None,
    chunk_number: int,
) -> PolicyChunk:
    text = "\n".join(lines).strip()

    raw_id = (
        f"{source}:{product}:{document_type}:"
        f"{page_start}:{page_end}:{section}:"
        f"{chunk_number}:{text}"
    )

    chunk_id = sha256(
        raw_id.encode("utf-8")
    ).hexdigest()[:16]

    return PolicyChunk(
        chunk_id=chunk_id,
        source=source,
        product=product,
        document_type=document_type,
        page_start=page_start,
        page_end=page_end,
        section=section,
        text=text,
    )


def merge_short_chunks(
    raw_chunks: list[dict],
    max_chars: int,
) -> list[dict]:
    """Fold fragments into a neighbour from the same section.

    A fragment with no same-section neighbour is kept: it is the whole
    body of a short section.
    """
    merged: list[dict] = []

    for raw in raw_chunks:
        previous = merged[-1] if merged else None

        if (
            previous is not None
            and previous["section"] == raw["section"]
            and (
                len("\n".join(raw["lines"])) < MIN_CHUNK_CHARS
                or len("\n".join(previous["lines"])) < MIN_CHUNK_CHARS
            )
            and len(
                "\n".join(previous["lines"] + raw["lines"])
            ) <= max_chars
        ):
            previous["lines"].extend(raw["lines"])
            previous["page_end"] = raw["page_end"]
            continue

        merged.append(raw)

    return merged


def build_chunks(
    pages: list[tuple[int, str]],
    source: str,
    product: str,
    document_type: str,
    max_chars: int = 2200,
) -> list[PolicyChunk]:
    raw_chunks: list[dict] = []

    current_lines: list[str] = []
    current_part: str | None = None
    current_sub: str | None = None
    current_page_start: int | None = None
    current_page_end: int | None = None

    def flush() -> None:
        nonlocal current_lines
        nonlocal current_page_start
        nonlocal current_page_end

        if not current_lines:
            return

        raw_chunks.append(
            {
                "lines": current_lines,
                "page_start": current_page_start,
                "page_end": current_page_end,
                "section": format_section(
                    current_part,
                    current_sub,
                ),
            }
        )

        current_lines = []
        current_page_start = None
        current_page_end = None

    def holds_only_heading() -> bool:
        # A heading plus its UIN line, with the body still to come.
        return (
            0 < len(current_lines) <= 2
            and (
                is_part_heading(current_lines[0])
                or is_sub_heading(current_lines[0])
            )
            and len("\n".join(current_lines)) < 150
        )

    for page_number, text in pages:
        lines = clean_page_text(text)

        for line in lines:
            if is_part_heading(line):
                if not holds_only_heading():
                    flush()

                current_part = line
                current_sub = None

            elif is_sub_heading(line):
                if not holds_only_heading():
                    flush()

                current_sub = line

            elif (
                is_clause_start(line)
                and len("\n".join(current_lines))
                >= MIN_CLAUSE_CHUNK_CHARS
            ):
                flush()

            elif (
                len("\n".join(current_lines + [line]))
                > max_chars
            ):
                flush()

            if current_page_start is None:
                current_page_start = page_number

            current_page_end = page_number

            current_lines.append(line)

    flush()

    return [
        create_chunk(
            lines=raw["lines"],
            page_start=raw["page_start"],
            page_end=raw["page_end"],
            source=source,
            product=product,
            document_type=document_type,
            section=raw["section"],
            chunk_number=chunk_number,
        )
        for chunk_number, raw in enumerate(
            merge_short_chunks(
                raw_chunks,
                max_chars,
            ),
            start=1,
        )
    ]


def extract_pages(path: str) -> list[tuple[int, str]]:
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Policy document not found: {path}"
        )

    # sort=True reads text top-to-bottom, left-to-right. The default order
    # follows the PDF's internal stream, which places Section I's list of
    # covered perils before its heading.
    with pymupdf.open(path) as document:
        return [
            (
                page_number,
                page.get_text(
                    sort=True,
                    flags=PDF_TEXT_FLAGS,
                ),
            )
            for page_number, page in enumerate(
                document,
                start=1,
            )
        ]


def ingest_policy(
    path: str,
    product: str,
    document_type: str,
) -> list[PolicyChunk]:
    if not product.strip():
        raise ValueError("Product cannot be empty")

    if not document_type.strip():
        raise ValueError(
            "Document type cannot be empty"
        )

    pages = extract_pages(path)

    return build_chunks(
        pages=pages,
        source=Path(path).name,
        product=product,
        document_type=document_type,
    )
