from pathlib import Path

import pymupdf


# Expand ligatures such as "ﬁ" into plain letters so extracted text matches
# keyword searches ("influence", not "inﬂuence").
PDF_TEXT_FLAGS = (
    pymupdf.TEXTFLAGS_TEXT
    & ~pymupdf.TEXT_PRESERVE_LIGATURES
)


SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".txt",
}


def get_file_extension(
    path: str,
) -> str:
    return Path(path).suffix.lower()


def is_supported_document(
    path: str,
) -> bool:
    return (
        get_file_extension(path)
        in SUPPORTED_DOCUMENT_EXTENSIONS
    )


def read_pdf(
    path: str,
) -> str:
    with pymupdf.open(path) as document:
        pages = []

        for page in document:
            pages.append(
                page.get_text(flags=PDF_TEXT_FLAGS)
            )

        return "\n".join(pages)


def read_text(
    path: str,
) -> str:
    return Path(path).read_text(
        encoding="utf-8"
    )


def read_document(
    path: str,
) -> str:
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Document not found: {path}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"Document path is not a file: {path}"
        )

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return read_pdf(path)

    if extension == ".txt":
        return read_text(path)

    raise ValueError(
        f"Unsupported document type: {extension}"
    )


def validate_document_file(
    path: str,
) -> tuple[bool, str]:
    file_path = Path(path)

    if not file_path.exists():
        return (
            False,
            "Document file does not exist.",
        )

    if not file_path.is_file():
        return (
            False,
            "Document path does not point to a file.",
        )

    if not is_supported_document(path):
        return (
            False,
            f"Unsupported document type: {file_path.suffix}",
        )

    try:
        text = read_document(path)
    except Exception as error:
        return (
            False,
            f"Document could not be read: {error}",
        )

    if not text.strip():
        return (
            False,
            "Document contains no readable text.",
        )

    return (
        True,
        "Document can be read successfully.",
    )


def get_document_info(
    path: str,
) -> dict:
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Document not found: {path}"
        )

    if not file_path.is_file():
        raise ValueError(
            f"Document path is not a file: {path}"
        )

    return {
        "file_name": file_path.name,
        "file_extension": file_path.suffix.lower(),
        "file_size": file_path.stat().st_size,
        "supported": is_supported_document(path),
    }