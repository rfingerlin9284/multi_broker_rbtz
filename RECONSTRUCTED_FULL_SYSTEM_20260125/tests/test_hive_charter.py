from hive_real.charter import validate_seat_output


def test_validate_good_output():
    good = {
        "seat": "GROK",
        "decision": "BUY",
        "confidence": 0.85,
        "pair": "EUR_USD",
        "timeframe": "M5",
        "entry": {"type":"market","price":1.12},
        "stop_loss": {"price":1.118, "reason":"invalidation"},
        "take_profit": {"price":1.128, "reason":"target"},
        "r_multiple_est": 1.6,
        "key_reasons": ["trend","rsi"],
        "invalidation": ["price below support"],
        "self_heal_actions": ["NONE"],
        "key_reasons": ["trend","rsi"],
        "veto_reason": ""
    }
    ok, errs = validate_seat_output(good)
    assert ok


def test_validate_bad_output():
    bad = {"seat": "GROK", "decision": "MAYBE", "confidence": 2}
    ok, errs = validate_seat_output(bad)
    assert not ok
    assert any('invalid_confidence' in e or 'invalid_decision' in e or 'missing' in e for e in errs)
