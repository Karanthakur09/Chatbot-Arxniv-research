def is_valid_pdf(data: bytes) -> bool:
    return data.startswith(b"%PDF")