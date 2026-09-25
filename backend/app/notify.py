from __future__ import annotations

import os
from enum import StrEnum

import httpx

SEMAPHORE_URL = 'https://api.semaphore.co/api/v4/messages'


class NotifyResult(StrEnum):
    SENT = 'sent'
    NOT_CONFIGURED = 'not_configured'
    FAILED = 'failed'


def _oncall_numbers() -> list[str]:
    return [number.strip() for number in os.environ.get('ONCALL_SMS_NUMBERS', '').split(',') if number.strip()]


def sms_configured() -> bool:
    return bool(os.environ.get('SEMAPHORE_API_KEY', '').strip() and _oncall_numbers())


async def send_sms(text: str) -> NotifyResult:
    api_key = os.environ.get('SEMAPHORE_API_KEY', '').strip()
    numbers = _oncall_numbers()
    if not api_key or not numbers:
        return NotifyResult.NOT_CONFIGURED
    data = {'apikey': api_key, 'message': text}
    sender_name = os.environ.get('SEMAPHORE_SENDER_NAME', '').strip()
    if sender_name:
        data['sendername'] = sender_name
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for number in numbers:
                response = await client.post(SEMAPHORE_URL, data={**data, 'number': number})
                response.raise_for_status()
    except Exception:
        return NotifyResult.FAILED
    return NotifyResult.SENT
