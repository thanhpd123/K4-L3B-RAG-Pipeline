"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Kiểm tra các tài liệu đã được đặt trong:
data/landing/legal/

Yêu cầu:
- Có tối thiểu 3 file PDF/DOC/DOCX
- Tên file không dấu
- File hợp lệ
"""

from pathlib import Path


DATA_DIR = (
    Path(__file__).parent.parent
    / "data"
    / "landing"
    / "legal"
)


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx"
}


def setup_directory() -> None:
    """
    Tạo thư mục legal nếu chưa tồn tại.
    """

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        f"Ready: {DATA_DIR}"
    )



def validate_documents() -> None:
    """
    Kiểm tra tài liệu trong folder legal.
    """

    documents = []


    for file in DATA_DIR.iterdir():

        if (
            file.is_file()
            and file.suffix.lower()
            in SUPPORTED_EXTENSIONS
        ):
            documents.append(file)



    print(
        f"Found {len(documents)} documents"
    )


    if len(documents) < 3:
        raise ValueError(
            "Need at least 3 legal documents"
        )


    print(
        "\nLegal documents:"
    )

    for doc in documents:

        size = doc.stat().st_size / 1024

        print(
            f"- {doc.name} ({size:.2f} KB)"
        )


    print(
        "\nValidation passed!"
    )



def collect_documents():
    """
    Entry point cho task1.
    """

    validate_documents()



if __name__ == "__main__":

    setup_directory()

    collect_documents()