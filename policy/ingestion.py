from collections import Counter
from hashlib import sha256
from pathlib import Path
import re

import pymupdf
from pydantic import BaseModel


class PolicyChunk(BaseModel):
    chunk_id: str
    source: str
    product: str
    document_type: str
    page_start: int
    page_end: int
    section: str | None
    text: str


# ---------------------------------------------------------------------------
# Line-level noise filtering (headers/footers repeated on every page)
# ---------------------------------------------------------------------------

NOISE_LINE_PATTERNS = [
    r"^Page \d+ of \d+$",
    r"^Auto Secure - Private Car Package Policy$",
    r"^Registered office:.*",
    r"^\d*\s*Customer Support No\.:.*",
    r"^IRDA of India Registration No\.:.*",
    r"^24\*?$",
]


def normalize_line(text: str) -> str:
    """Collapse whitespace and drop known page boilerplate. Returns "" to discard."""
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return ""

    for pattern in NOISE_LINE_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            return ""

    return text


# ---------------------------------------------------------------------------
# Heading and clause-marker detection
# ---------------------------------------------------------------------------

# A line starting with one of these is the start of a new numbered/lettered
# clause, not a heading. These are treated as unit boundaries: content is
# never split in the middle of a clause, but a clause is never mistaken for
# a heading either.
CLAUSE_START_RE = re.compile(
    r"^(\d{1,3}\.\s|\(\d{1,3}\)\s|[ivxlcdm]{1,6}\.\s|[IVXLCDM]{1,6}\.\s|"
    r"[a-zA-Z]\)\s|[•▪●]\s)"
)

# Fallback heading patterns for headings that PyMuPDF doesn't style distinctly
# (same font size/weight as body text). Only consulted when the font-based
# signal (see is_heading_line) is inconclusive.
HEADING_FALLBACK_PATTERNS = [
    r"^TA\d+\s*-\s*.+",
    r"^Section\s+[IVX]+.*",
    r"^Definitions?\s*:?.*$",
    r"^What is Covered\s*:?.*$",
    r"^What is not Covered\s*:?.*$",
    r"^Special Conditions?\s*:?.*$",
    r"^Coverage Conditions?\s*:?.*$",
    r"^Conditions during the contract\s*:?.*$",
    r"^Exclusions?\s*:?.*$",
    r"^[A-Z][A-Z &/\-]{4,60}$",
]


def get_body_font_size(document: "pymupdf.Document") -> float:
    """Estimate the document's dominant body-text font size (by character
    count, not line count, so a couple of big headings don't skew it)."""
    sizes: Counter = Counter()

    for page in document:
        page_dict = page.get_text("dict")

        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    size = round(span["size"], 1)
                    sizes[size] += len(span["text"])

    if not sizes:
        return 10.0

    return sizes.most_common(1)[0][0]


def is_heading_line(text: str, avg_size: float, bold_ratio: float, body_size: float) -> bool:
    word_count = len(text.split())

    if word_count == 0 or word_count > 14:
        return False

    # Clause markers ("1. ...", "IV. ...") are body content, never headings,
    # regardless of how they happen to be styled.
    if CLAUSE_START_RE.match(text):
        return False

    is_larger = avg_size >= body_size + 1.2
    is_strongly_bold = bold_ratio >= 0.8

    if is_larger or (is_strongly_bold and word_count <= 10):
        return True

    return any(re.match(pattern, text, re.IGNORECASE) for pattern in HEADING_FALLBACK_PATTERNS)


# ---------------------------------------------------------------------------
# Table extraction
# ---------------------------------------------------------------------------

# PyMuPDF's find_tables() reliably flags two kinds of false/bad matches on
# real-world policy PDFs:
#
# 1. A page's boxed header/footer boilerplate (address, support number, IRDA
#    registration) gets detected as a one-row "table" on essentially every
#    page, because it sits inside a drawn box.
# 2. When a genuine table has no horizontal gridlines between data rows
#    (common for simple two-column rate tables), PyMuPDF's row detection
#    collapses all data rows into a single row per column, with the
#    individual rows joined by "\n" inside one cell -- and its bounding-box
#    estimate can even overshoot into unrelated paragraph text below the
#    table. We detect and repair the row-collapse case, and simply discard
#    (not trust) a table if it looks like it swallowed real prose.

CONTAMINATION_RE = re.compile(r"\n\s*\d{1,2}\.\s+[A-Z]")


def is_boilerplate_table(flat_text: str) -> bool:
    return "Registered office:" in flat_text or "IRDA of India Registration No.:" in flat_text


def is_contaminated_table(flat_text: str) -> bool:
    """True if the extracted table looks like it swallowed a numbered
    policy clause ("...\\n5. Rate of depreciation...") rather than being a
    clean data table. When this fires we don't trust the table at all."""
    return bool(CONTAMINATION_RE.search(flat_text))


def expand_merged_rows(rows: list[list[str | None]]) -> list[list[str]]:
    """Undo PyMuPDF's row-collapse: if a row's cells contain multiple
    "\\n"-joined values because no gridlines separated the real rows,
    reconstruct the individual rows. Uses the cell with the fewest wrapped
    lines as the source of truth for how many real rows there are, since a
    numeric/short column is unlikely to line-wrap while a label column is.
    """
    expanded: list[list[str]] = []

    for row in rows:
        cells = [("" if c is None else str(c)) for c in row]
        split_cells = [cell.split("\n") for cell in cells]
        multi_line_lengths = [len(sc) for sc in split_cells if len(sc) > 1]

        # Require at least two cells to be multi-line before assuming a
        # row-collapse happened. A single wrapped cell (e.g. a long address
        # in an otherwise normal one-record-per-row table) is just word
        # wrap, not evidence that several rows got merged into this one.
        if len(multi_line_lengths) < 2:
            expanded.append(cells)
            continue

        target_rows = min(multi_line_lengths)
        grouped_cells: list[list[str]] = []
        reconstructable = True

        for sc in split_cells:
            n = len(sc)

            if n == target_rows:
                grouped_cells.append(sc)
            elif n == 1:
                grouped_cells.append([sc[0]] + [""] * (target_rows - 1))
            elif n % target_rows == 0:
                group_size = n // target_rows
                grouped_cells.append(
                    [
                        " ".join(sc[i * group_size:(i + 1) * group_size]).strip()
                        for i in range(target_rows)
                    ]
                )
            else:
                reconstructable = False
                break

        if not reconstructable:
            expanded.append(cells)
            continue

        for i in range(target_rows):
            expanded.append([gc[i] for gc in grouped_cells])

    return expanded


def format_table(rows: list[list[str | None]]) -> str:
    cleaned_rows = [
        [("" if cell is None else str(cell).strip()) for cell in row]
        for row in rows
        if row
    ]

    if not cleaned_rows:
        return ""

    return "Table:\n" + "\n".join(" | ".join(row) for row in cleaned_rows)


# ---------------------------------------------------------------------------
# Page -> ordered content items (heading / text / table), layout-aware
# ---------------------------------------------------------------------------


def extract_page_items(page: "pymupdf.Page", body_size: float) -> list[dict]:
    """Return this page's content as an ordered (top-to-bottom) list of
    {"kind": "heading" | "text" | "table", "text": str} items.

    Tables are detected via PyMuPDF's grid detection and rendered as a single
    structured block; any text line that falls inside a detected table's
    bounding box is excluded from normal paragraph flow so it isn't also
    emitted as a disconnected fragment.
    """
    items: list[tuple[float, dict]] = []
    table_bboxes: list["pymupdf.Rect"] = []

    try:
        table_finder = page.find_tables()
    except Exception:
        table_finder = None

    if table_finder is not None:
        for table in table_finder.tables:
            try:
                rows = table.extract()
            except Exception:
                continue

            if not rows:
                continue

            flat_text = "\n".join(str(cell) for row in rows for cell in row if cell)

            if is_boilerplate_table(flat_text):
                # Not a real table -- exclude its region from normal line
                # flow too, since it's just the repeated page boilerplate.
                table_bboxes.append(pymupdf.Rect(table.bbox))
                continue

            if is_contaminated_table(flat_text):
                # Looks like the detected bounding box swallowed real prose
                # along with (or instead of) a table. Don't trust it as a
                # table, and don't exclude its bbox either -- let the normal
                # per-line heading/text classification handle this region
                # so the swallowed content isn't lost.
                continue

            # Row-collapse (all data crammed into one row per column) only
            # happens when PyMuPDF thinks the whole table body is a single
            # row. A table that already has several distinct rows (e.g. one
            # row per office in an address table) is fine as-is -- one of
            # its cells simply wraps to multiple lines, which is normal.
            if len(rows) <= 2:
                rows = expand_merged_rows(rows)

            table_text = format_table(rows)

            if not table_text:
                continue

            bbox = pymupdf.Rect(table.bbox)
            table_bboxes.append(bbox)
            items.append((bbox.y0, {"kind": "table", "text": table_text}))

    page_dict = page.get_text("dict")

    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue

        for line in block.get("lines", []):
            spans = line.get("spans", [])

            if not spans:
                continue

            line_bbox = pymupdf.Rect(line["bbox"])

            if any(line_bbox.intersects(bbox) for bbox in table_bboxes):
                continue

            text = normalize_line("".join(span["text"] for span in spans))

            if not text:
                continue

            sizes = [span["size"] for span in spans]
            bold_flags = [bool(span["flags"] & 16) for span in spans]
            avg_size = sum(sizes) / len(sizes)
            bold_ratio = sum(bold_flags) / len(bold_flags)

            kind = "heading" if is_heading_line(text, avg_size, bold_ratio, body_size) else "text"
            items.append((line_bbox.y0, {"kind": kind, "text": text}))

    items.sort(key=lambda item: item[0])

    return [item for _, item in items]


# ---------------------------------------------------------------------------
# Chunk assembly
# ---------------------------------------------------------------------------


def create_chunk(
    text: str,
    page_start: int,
    page_end: int,
    source: str,
    product: str,
    document_type: str,
    section: str | None,
    chunk_number: int,
) -> PolicyChunk:
    text = text.strip()

    raw_id = (
        f"{source}:{product}:{document_type}:"
        f"{page_start}:{page_end}:{section}:"
        f"{chunk_number}:{text}"
    )

    chunk_id = sha256(raw_id.encode("utf-8")).hexdigest()[:16]

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
    pages: list[tuple[int, list[dict]]],
    source: str,
    product: str,
    document_type: str,
    max_chars: int = 2500,
    min_chars: int = 250,
) -> list[PolicyChunk]:
    """Assemble ordered per-page content items into chunks.

    Unlike a plain character-count splitter, this only ever breaks between
    complete units (paragraphs/clauses/tables), so a clause is never split
    mid-sentence. Headings only start a new chunk once the current one has
    picked up a reasonable amount of body text (min_chars); a heading with
    little or no body merges into the following content instead of being
    emitted as an empty stub. The section heading is also prefixed into the
    chunk's own text, so retrieval sees the heading context even though the
    embedding call only looks at chunk.text.
    """
    chunks: list[PolicyChunk] = []
    chunk_number = 0

    pending_units: list[str] = []
    pending_page_start: int | None = None
    pending_page_end: int | None = None
    current_section: str | None = None
    current_unit_lines: list[str] = []

    def pending_length() -> int:
        return sum(len(unit) + 2 for unit in pending_units)

    def flush_unit() -> None:
        nonlocal current_unit_lines

        if not current_unit_lines:
            return

        unit_text = " ".join(current_unit_lines).strip()
        current_unit_lines = []

        if unit_text:
            pending_units.append(unit_text)

    def flush_chunk(carry_overlap: bool, page_number: int) -> None:
        nonlocal pending_units, pending_page_start, pending_page_end, chunk_number

        if not pending_units:
            return

        body = "\n\n".join(pending_units)
        text = f"Section: {current_section}\n\n{body}" if current_section else body

        chunk_number += 1
        chunks.append(
            create_chunk(
                text=text,
                page_start=pending_page_start,
                page_end=pending_page_end,
                source=source,
                product=product,
                document_type=document_type,
                section=current_section,
                chunk_number=chunk_number,
            )
        )

        overlap_unit = pending_units[-1] if carry_overlap else None

        pending_units = []
        pending_page_start = None
        pending_page_end = None

        if overlap_unit:
            pending_units.append(overlap_unit)
            pending_page_start = page_number
            pending_page_end = page_number

    for page_number, items in pages:
        for item in items:
            kind, text = item["kind"], item["text"]

            if pending_page_start is None:
                pending_page_start = page_number

            pending_page_end = page_number

            if kind == "table":
                flush_unit()
                flush_chunk(carry_overlap=False, page_number=page_number)

                chunk_number += 1
                table_text = f"Section: {current_section}\n\n{text}" if current_section else text
                chunks.append(
                    create_chunk(
                        text=table_text,
                        page_start=page_number,
                        page_end=page_number,
                        source=source,
                        product=product,
                        document_type=document_type,
                        section=current_section,
                        chunk_number=chunk_number,
                    )
                )
                pending_page_start = None
                pending_page_end = None
                continue

            if kind == "heading":
                flush_unit()

                if pending_length() >= min_chars:
                    flush_chunk(carry_overlap=False, page_number=page_number)
                    current_section = text
                elif current_section is None:
                    current_section = text
                else:
                    # Small sub-heading: keep it attached to the content
                    # already accumulated instead of emitting a stub chunk.
                    pending_units.append(f"[{text}]")

                continue

            # Regular body text line.
            if CLAUSE_START_RE.match(text) and current_unit_lines:
                flush_unit()

                if pending_length() > max_chars:
                    flush_chunk(carry_overlap=True, page_number=page_number)

            current_unit_lines.append(text)

        # End of page: close any wrapped-line-in-progress unit, but let a
        # section continue across the page break rather than force-flushing.
        flush_unit()

        if pending_length() > max_chars:
            flush_chunk(carry_overlap=True, page_number=page_number)

    flush_unit()
    flush_chunk(carry_overlap=False, page_number=pending_page_end or 0)

    return chunks


def ingest_policy(
    path: str,
    product: str,
    document_type: str,
) -> list[PolicyChunk]:
    file_path = Path(path)

    if file_path.suffix.lower() != ".pdf":
        raise ValueError("Policy ingestion currently supports PDF files only")

    with pymupdf.open(path) as document:
        body_size = get_body_font_size(document)

        pages = [
            (page_number, extract_page_items(page, body_size))
            for page_number, page in enumerate(document, start=1)
        ]

    return build_chunks(
        pages=pages,
        source=file_path.name,
        product=product,
        document_type=document_type,
    )