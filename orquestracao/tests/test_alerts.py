from pipeline_monday.alerts import notify


def test_success_does_not_send():
    assert notify({'status': 'success'}, env={}) == 'not_needed'


def test_missing_channel_explicit():
    assert notify({'status': 'failed'}, env={}) == 'not_configured'


def test_alert_requires_tls_and_does_not_leak_payloads():
    calls = []
    class SMTP:
        def __init__(self, host, port, timeout):
            assert port == 587
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def ehlo(self):
            pass
        def starttls(self, context):
            calls.append('tls')
        def login(self, *args):
            assert calls == ['tls']
        def send_message(self, message, **kwargs):
            assert 'private-source-payload' not in str(message)
            assert 'example-secret' not in str(message)
            return {}
    env = dict(MONDAY_ALERT_SMTP_HOST='smtp.example.test', EMAIL_REMETENTE='from@example.test',
               EMAIL_SENHA_APP='example-secret', EMAIL_DESTINATARIOS='to@example.test')
    result = {'status': 'failed', 'products': {'backlog': {'status': 'failed', 'payload': 'private-source-payload'}}}
    assert notify(result, env=env, factory=SMTP) == 'sent'
