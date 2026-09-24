import asyncio
from urllib.parse import parse_qs

import httpx

from app.notify import NotifyResult, send_sms


def test_semaphore_adapter_posts_expected_form(monkeypatch):
    seen = []

    async def handler(request):
        seen.append((request.url, parse_qs(request.content.decode())))
        return httpx.Response(200, json={'message': 'success'})

    monkeypatch.setenv('SEMAPHORE_API_KEY', 'test-key')
    monkeypatch.setenv('ONCALL_SMS_NUMBERS', '+639171234567,+639189876543')
    monkeypatch.setenv('SEMAPHORE_SENDER_NAME', 'AqOne')
    original = httpx.AsyncClient

    def client(*args, **kwargs):
        kwargs['transport'] = httpx.MockTransport(handler)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, 'AsyncClient', client)
    result = asyncio.run(send_sms('SOS Bangka 17'))
    assert result is NotifyResult.SENT
    assert len(seen) == 2
    assert all(str(url) == 'https://api.semaphore.co/api/v4/messages' for url, _ in seen)
    assert seen[0][1] == {
        'apikey': ['test-key'], 'number': ['+639171234567'], 'message': ['SOS Bangka 17'], 'sendername': ['AqOne']
    }


def test_missing_sms_configuration_returns_without_network_call(monkeypatch):
    monkeypatch.delenv('SEMAPHORE_API_KEY', raising=False)
    monkeypatch.delenv('ONCALL_SMS_NUMBERS', raising=False)
    def unexpected_client(*args, **kwargs):
        raise AssertionError('network client created')

    monkeypatch.setattr(httpx, 'AsyncClient', unexpected_client)
    assert asyncio.run(send_sms('SOS')) is NotifyResult.NOT_CONFIGURED


def test_partial_sms_configuration_returns_without_network_call(monkeypatch):
    monkeypatch.setenv('SEMAPHORE_API_KEY', 'test-key')
    monkeypatch.delenv('ONCALL_SMS_NUMBERS', raising=False)
    def unexpected_client(*args, **kwargs):
        raise AssertionError('network client created')

    monkeypatch.setattr(httpx, 'AsyncClient', unexpected_client)
    assert asyncio.run(send_sms('SOS')) is NotifyResult.NOT_CONFIGURED
