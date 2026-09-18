from hashlib import sha256
from pathlib import Path
import re

import pymupdf
from pydantic import BaseModel


NOISE_LINE_PATTERNS = [
    r"^Page \d+ of \d+$",
    r"^Auto Secure - Private Car Package Policy$",
    r"^Registered office:",
    r"^7 Customer Support No\.:",
    r"^IRDA of India Registration No\.:",
    r"^24\*$",
]


CLAUSE_START_RE = re.compile(
    r"^(?:"
    r"\d+(?:\.\d+)*[.)]"
    r"|[a-zA-Z]\)"
    r"|[ivxIVX]+\."
    r"|[•\-]"
    r")\s+"
)


HEADING_FALLBACK_PATTERNS = [
    r"^TA\d+\s*-\s*.+",
    r"^Section\s+[IVX]+.*",
    r"^Definitions?\s*:?.*$",
    r"^What is Covered\s*:?.*$",
    r"^What is not Covered\s*:?.*$",
    r"^What is not covered\s*:?.*$",
    r"^Special Conditions?\s*:?.*$",
    r"^Special conditions.*$",
    r"^Coverage Conditions?\s*:?.*$",
    r"^Conditions during the contract\s*:?.*$",
    r"^Exclusions?\s*:?.*$",
    r"^General Exceptions\s*:?.*$",
    r"^Important Conditions\s*:?.*$",
    r"^No Claim Bonus\s*:?.*$",
    r"^[A-Z][A-Z &/\-]{4,60}$",
]


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
        re.fullmatch(pattern, line, re.IGNORECASE)
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


def is_heading(line: str) -> bool:
    return any(
        re.match(pattern, line, re.IGNORECASE)
        for pattern in HEADING_FALLBACK_PATTERNS
    )


def is_clause_start(line: str) -> bool:
    return bool(CLAUSE_START_RE.match(line))


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


def build_chunks(
    pages: list[tuple[int, str]],
    source: str,
    product: str,
    document_type: str,
    max_chars: int = 2200,
) -> list[PolicyChunk]:
    chunks = []
    chunk_number = 0

    current_lines: list[str] = []
    current_section: str | None = None
    current_page_start: int | None = None
    current_page_end: int | None = None

    def flush() -> None:
        nonlocal current_lines
        nonlocal current_page_start
        nonlocal current_page_end
        nonlocal chunk_number

        if not current_lines:
            return

        chunk_number += 1

        chunks.append(
            create_chunk(
                lines=current_lines,
                page_start=current_page_start,
                page_end=current_page_end,
                source=source,
                product=product,
                document_type=document_type,
                section=current_section,
                chunk_number=chunk_number,
            )
        )

        current_lines = []
        current_page_start = None
        current_page_end = None

    for page_number, text in pages:
        lines = clean_page_text(text)

        for line in lines:
            if is_heading(line):
                flush()

                current_section = line
                current_lines.append(line)
                current_page_start = page_number
                current_page_end = page_number

                continue

            if is_clause_start(line) and current_lines:
                previous_text = "\n".join(current_lines)

                if len(previous_text) >= 100:
                    flush()

            if current_page_start is None:
                current_page_start = page_number

            current_page_end = page_number

            candidate = "\n".join(
                current_lines + [line]
            )

            if (
                len(candidate) > max_chars
                and current_lines
            ):
                flush()

                current_page_start = page_number
                current_page_end = page_number

            current_lines.append(line)

    flush()

    return chunks


def extract_pages(path: str) -> list[tuple[int, str]]:
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Policy document not found: {path}"
        )

    with pymupdf.open(path) as document:
        return [
            (page_number, page.get_text())
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