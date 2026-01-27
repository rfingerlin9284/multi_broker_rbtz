import os
from unittest import mock
from tools.notify import _slack_notify, _email_notify, notify_reconcile



def test_slack_notify(monkeypatch):
    monkeypatch.setenv('SLACK_WEBHOOK_URL', 'http://example.local/webhook')
    called = {}

    def fake_post(url, json=None, timeout=None):
        called['url'] = url
        class R: 
            status_code = 200
            def raise_for_status(self):
                return None
        return R()

    with mock.patch('requests.post', fake_post):
        assert _slack_notify('hello') is True
        assert 'example.local' in called['url']


def test_email_notify(monkeypatch, tmp_path):
    monkeypatch.delenv('SLACK_WEBHOOK_URL', raising=False)
    monkeypatch.setenv('ALERT_EMAIL_TO', 'ops@example.com')
    monkeypatch.setenv('ALERT_EMAIL_FROM', 'phoenix@example.com')
    # Patch smtplib.SMTP to a fake object
    class FakeSMTP:
        def __init__(self, server, port, timeout=None):
            pass
        def sendmail(self, frm, to, msg):
            assert 'Subject' in msg
        def quit(self):
            pass
    with mock.patch('smtplib.SMTP', FakeSMTP):
        assert _email_notify('subj', 'body') is True


def test_notify_reconcile_disabled(monkeypatch):
    monkeypatch.delenv('ENABLE_RECONCILE_ALERTS', raising=False)
    # By default it's not '1' so should not attempt to send
    assert notify_reconcile('msg') is False


def test_notify_reconcile_uses_slack(monkeypatch):
    monkeypatch.setenv('ENABLE_RECONCILE_ALERTS', '1')
    monkeypatch.setenv('SLACK_WEBHOOK_URL', 'http://example.local')
    with mock.patch('requests.post') as fake_post:
        fake_post.return_value.status_code = 200
        fake_post.return_value.raise_for_status = lambda: None
        assert notify_reconcile('msg') is True
