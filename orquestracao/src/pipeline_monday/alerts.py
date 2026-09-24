"""Optional explicitly configured SMTP alert. No payloads, credentials or item data."""

import os
import smtplib
import ssl
from email.message import EmailMessage


def notify(result, *, env=None, factory=smtplib.SMTP):
    if result['status'] not in {'failed', 'partial'}:
        return 'not_needed'
    env = os.environ if env is None else env
    keys = ('MONDAY_ALERT_SMTP_HOST', 'EMAIL_REMETENTE', 'EMAIL_SENHA_APP', 'EMAIL_DESTINATARIOS')
    if not all(env.get(k) for k in keys):
        return 'not_configured'
    try:
        recipients = [v.strip() for v in env['EMAIL_DESTINATARIOS'].split(',') if v.strip()]
        if not recipients or any('\n' in v or '\r' in v or '@' not in v for v in recipients):
            return 'invalid_configuration'
        message = EmailMessage()
        message['Subject'] = '[pipeline-monday] Falha na atualizacao diaria'
        message['From'] = env['EMAIL_REMETENTE']
        message['To'] = ', '.join(recipients)
        failures = [key for key, value in result['products'].items()
                    if value['status'] in {'failed', 'blocked'}]
        message.set_content('Produtos com falha/bloqueio: ' + ', '.join(failures)
                            + '\nConsulte os logs do job pipeline-monday em us-central1. '
                            + 'Verifique a ultima publicacao valida antes de consumir. '
                            + 'Nao remova locks sem confirmar que o executor parou.')
        with factory(env['MONDAY_ALERT_SMTP_HOST'], 587, timeout=20) as smtp:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
            smtp.login(env['EMAIL_REMETENTE'], env['EMAIL_SENHA_APP'])
            refused = smtp.send_message(message, to_addrs=recipients)
            return 'partially_refused' if refused else 'sent'
    except Exception:
        return 'delivery_failed'
