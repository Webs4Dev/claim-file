from pathlib import Path
import pymupdf


def read_pdf(path: str) -> str:
    with pymupdf.open(path) as document:
        text = ""

        for page in document:
            text += page.get_text()

        return text

def read_document(path: str) -> str:
    file_path = Path(path)

    if file_path.suffix.lower() == ".pdf":
        return read_pdf(path)

    if file_path.suffix.lower() == ".txt":
        return file_path.read_text(encoding="utf-8")

    raise ValueError(
        f"Unsupported document type: {file_path.suffix}"
    )