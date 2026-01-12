"""Notification helpers: Slack webhook or SMTP email fallback.

Environment variables:
- SLACK_WEBHOOK_URL: if set, use Slack Incoming Webhook (POST JSON with text)
- ALERT_EMAIL_TO: comma-separated recipients for email fallback
- ALERT_EMAIL_FROM: sender address (optional)
- SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASS: optional SMTP settings
- ENABLE_RECONCILE_ALERTS: if '1' enable alerts
"""
from __future__ import annotations
import os
import json
import logging
import smtplib
from typing import Optional

import requests

logger = logging.getLogger(__name__)


def _slack_notify(text: str) -> bool:
    url = os.getenv('SLACK_WEBHOOK_URL')
    if not url:
        return False
    payload = {'text': text}
    try:
        r = requests.post(url, json=payload, timeout=5)
        r.raise_for_status()
        return True
    except Exception as exc:
        logger.exception('Slack notify failed: %s', exc)
        return False


def _email_notify(subject: str, body: str) -> bool:
    to_list = os.getenv('ALERT_EMAIL_TO')
    if not to_list:
        return False
    frm = os.getenv('ALERT_EMAIL_FROM', f'phoenix@{os.getenv("HOSTNAME","localhost")}')
    smtp = os.getenv('SMTP_SERVER') or 'localhost'
    port = int(os.getenv('SMTP_PORT', '25'))
    msg = f"From: {frm}\nTo: {to_list}\nSubject: {subject}\n\n{body}"
    try:
        if os.getenv('SMTP_USER') and os.getenv('SMTP_PASS'):
            server = smtplib.SMTP(smtp, port, timeout=10)
            server.starttls()
            server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASS'))
            server.sendmail(frm, [x.strip() for x in to_list.split(',')], msg)
            server.quit()
        else:
            s = smtplib.SMTP(smtp, port, timeout=10)
            s.sendmail(frm, [x.strip() for x in to_list.split(',')], msg)
            s.quit()
        return True
    except Exception as exc:
        logger.exception('Email notify failed: %s', exc)
        return False


def notify_reconcile(message: str) -> bool:
    """Send reconcile alert to Slack or email. Returns True if a notifier succeeded."""
    if os.getenv('ENABLE_RECONCILE_ALERTS', '0') != '1':
        logger.info('Alerts disabled (ENABLE_RECONCILE_ALERTS != 1)')
        return False
    # Prefer Slack
    ok = False
    try:
        ok = _slack_notify(message)
    except Exception:
        logger.exception('Slack notify raised')
        ok = False
    if ok:
        return True
    # fallback to email
    try:
        subject = 'Phoenix Reconcile Alert'
        return _email_notify(subject, message)
    except Exception:
        logger.exception('Email notify raised')
        return False
