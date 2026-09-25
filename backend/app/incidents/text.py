def truncate_utf8(text: str, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ''
    return text.encode('utf-8')[:max_bytes].decode('utf-8', errors='ignore')
