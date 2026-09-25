import time

RESERVED_SENDERS = {'mdrrmo', 'coastguard', 'pcg', 'pagasa', 'admin', 'official'}


def normalise_sender(name: str) -> str:
    folded = name.casefold().replace('0', 'o').replace('1', 'l')
    return ''.join(char for char in folded if char.isalpha())


def sender_is_reserved(name: str) -> bool:
    normalized = normalise_sender(name)
    return any(reserved in normalized for reserved in RESERVED_SENDERS)


def chat_origin(credential_kind: str | None) -> str:
    return {
        'operator': 'mdrrmo',
        'vessel': 'app',
        'gateway': 'mesh',
    }.get(credential_kind, 'app')


class RateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[tuple[str, str], tuple[float, float]] = {}

    def allow(self, sender: str, client_ip: str) -> bool:
        # ponytail: per-process buckets do not coordinate across instances; move to Postgres if scaled out.
        now = time.monotonic()
        key = normalise_sender(sender), client_ip
        tokens, updated_at = self._buckets.get(key, (6.0, now))
        tokens = min(6.0, tokens + max(0.0, now - updated_at) * 0.1)
        if tokens < 1.0:
            self._buckets[key] = tokens, now
            return False
        self._buckets[key] = tokens - 1.0, now
        return True
