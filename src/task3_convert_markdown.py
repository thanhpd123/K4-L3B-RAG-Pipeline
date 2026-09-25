"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Input:
    data/landing/legal/
        *.pdf
        *.doc
        *.docx

    data/landing/news/
        *.json

Output:
    data/standardized/legal/
        *.md

    data/standardized/news/
        *.md
"""

from pathlib import Path
import json


LANDING_DIR = (
    Path(__file__).parent.parent
    / "data"
    / "landing"
)

OUTPUT_DIR = (
    Path(__file__).parent.parent
    / "data"
    / "standardized"
)


SUPPORTED_DOCS = {
    ".pdf",
    ".doc",
    ".docx"
}


# ======================================================
# Legal document conversion
# ======================================================

def convert_file_to_markdown(path: Path) -> str:
    """
    Convert PDF/DOC/DOCX sang markdown.

    Ưu tiên MarkItDown.
    """

    try:
        from markitdown import MarkItDown

        converter = MarkItDown()

        result = converter.convert(
            str(path)
        )

        content = result.text_content


        if content and content.strip():
            return content.strip()


    except Exception as error:

        print(
            f"MarkItDown failed for {path.name}: {error}"
        )


    # --------------------------------------------------
    # Fallback PDF
    # --------------------------------------------------

    if path.suffix.lower() == ".pdf":

        try:
            import fitz

            doc = fitz.open(path)

            pages = []

            for page in doc:

                text = page.get_text()

                if text.strip():
                    pages.append(text)


            return "\n\n".join(pages).strip()


        except Exception as error:

            print(
                f"PDF fallback failed: {error}"
            )


    # --------------------------------------------------
    # Fallback DOCX
    # --------------------------------------------------

    if path.suffix.lower() == ".docx":

        try:
            from docx import Document

            doc = Document(path)

            paragraphs = [
                p.text
                for p in doc.paragraphs
                if p.text.strip()
            ]

            return "\n\n".join(
                paragraphs
            ).strip()


        except Exception as error:

            print(
                f"DOCX fallback failed: {error}"
            )


    return ""



def convert_legal_docs() -> None:
    """
    Convert legal documents.
    """

    legal_dir = (
        LANDING_DIR
        / "legal"
    )


    output_dir = (
        OUTPUT_DIR
        / "legal"
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    for file in legal_dir.iterdir():


        if (
            not file.is_file()
            or file.suffix.lower()
            not in SUPPORTED_DOCS
        ):
            continue



        print(
            f"Converting legal: {file.name}"
        )


        markdown = convert_file_to_markdown(
            file
        )


        # Không tạo file rỗng
        if not markdown.strip():

            print(
                f"Skip empty: {file.name}"
            )

            continue



        output_file = (
            output_dir
            / f"{file.stem}.md"
        )


        # overwrite để tránh file trùng
        output_file.write_text(
            markdown,
            encoding="utf-8"
        )


        print(
            f"Saved: {output_file}"
        )



# ======================================================
# News conversion
# ======================================================

def convert_news_articles() -> None:
    """
    Convert JSON articles sang Markdown.
    """

    news_dir = (
        LANDING_DIR
        / "news"
    )


    output_dir = (
        OUTPUT_DIR
        / "news"
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )


    for file in news_dir.glob(
        "*.json"
    ):

        print(
            f"Converting news: {file.name}"
        )


        data = json.loads(
            file.read_text(
                encoding="utf-8"
            )
        )


        title = data.get(
            "title",
            "Unknown"
        )


        url = data.get(
            "url",
            ""
        )


        date = data.get(
            "date_crawled",
            ""
        )


        content = data.get(
            "content_markdown",
            ""
        )


        if not content.strip():

            print(
                f"Skip empty: {file.name}"
            )

            continue



        header = (
            f"# {title}\n\n"
            f"**Source:** {url}\n\n"
            f"**Crawled:** {date}\n\n"
            "---\n\n"
        )


        markdown = (
            header
            + content.strip()
        )


        output_file = (
            output_dir
            / f"{file.stem}.md"
        )


        output_file.write_text(
            markdown,
            encoding="utf-8"
        )


        print(
            f"Saved: {output_file}"
        )



# ======================================================
# Main
# ======================================================

def convert_all() -> None:
    """
    Convert toàn bộ corpus.
    """

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


    convert_legal_docs()

    convert_news_articles()


    print(
        "\nConversion completed."
    )



if __name__ == "__main__":

    convert_all()