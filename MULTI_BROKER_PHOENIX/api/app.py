"""Small Flask API exposing platform status and test-order preview/confirm endpoints."""
from __future__ import annotations
from flask import Flask, request, jsonify
from typing import Any, Dict
from multi_broker_phoenix.config.runtime import resolve_execution_type, get_trading_mode
from multi_broker_phoenix.risk.risk_manager import RiskManager
from multi_broker_phoenix.engines.paper_engine import PaperEngine
from multi_broker_phoenix.brokers.coinbase_connector import CoinbaseConnector
from multi_broker_phoenix.brokers.ibkr_connector import IBKRConnector
try:
    from multi_broker_phoenix.brokers.oanda_connector import OANDAConnector
except Exception:
    OANDAConnector = None

app = Flask(__name__)

# singletons used by the API for now
RM = RiskManager()
ENGINE = PaperEngine()
COIN = CoinbaseConnector(paper_mode=True, engine=ENGINE)
IB = IBKRConnector(paper_mode=True, engine=ENGINE)
OANDA = None
if OANDAConnector is not None:
    try:
        OANDA = OANDAConnector()
    except Exception:
        OANDA = None

PLATFORMS = {
    'COINBASE': {'supports_platform_paper': False, 'connector': COIN},
    'IBKR': {'supports_platform_paper': True, 'connector': IB},
    'OANDA': {'supports_platform_paper': True, 'connector': OANDA},
}


@app.route('/platforms', methods=['GET'])
def platforms():
    out = {}
    mode = get_trading_mode()
    for k, v in PLATFORMS.items():
        conn = v.get('connector')
        creds = False
        if k == 'OANDA':
            creds = bool(getattr(conn, 'token', None) and getattr(conn, 'account_id', None)) if conn else False
        if k == 'IBKR':
            # IBKR paper depends on gateway availability; check env
            creds = bool(getattr(conn, 'engine', None))
        out[k] = {
            'supports_platform_paper': v.get('supports_platform_paper', False),
            'creds_present': creds,
            'effective_execution_type': resolve_execution_type(k, supports_platform_paper=v.get('supports_platform_paper', False))
        }
    return jsonify({'mode': mode, 'platforms': out})


def _parse_candidate(data: Dict[str, Any]):
    # Expect candidate dict: strategy_id, symbol, platform, entry_price, stop_loss, side
    return data.get('candidate') or {}


@app.route('/actions/test-order/preview', methods=['POST'])
def preview_test_order():
    payload = request.get_json() or {}
    cand = _parse_candidate(payload)
    if not cand:
        return jsonify({'allowed': False, 'reason': 'missing_candidate'}), 400
    # Minimal validation
    symbol = cand.get('symbol')
    platform = cand.get('platform')
    entry = float(cand.get('entry_price', 0.0))
    stop = float(cand.get('stop_loss', 0.0))
    if entry <= 0 or stop <= 0:
        return jsonify({'allowed': False, 'reason': 'invalid_prices'}), 400
    # Determine execution type
    exec_type = resolve_execution_type(platform or 'COINBASE', supports_platform_paper=(platform in ('OANDA', 'IBKR')))
    # Build TradeCandidate-like minimal object
    class C:
        pass
    c = C()
    c.strategy_id = cand.get('strategy_id', 'manual_test')
    c.symbol = symbol
    c.platform = platform
    c.entry_price = entry
    c.stop_loss = stop
    c.side = cand.get('side')
    # Risk checks
    if not RM.is_trading_allowed():
        return jsonify({'allowed': False, 'reason': 'risk_halted'})
    # sizing
    sizing = RM.size_for_trade(c, RM.state.equity_now or 100000.0, fee_pct=0.001, slippage_pct=0.001)
    return jsonify({
        'allowed': sizing.get('allowed', False),
        'reason': sizing.get('reason', 'OK' if sizing.get('allowed') else 'sizing_rejected'),
        'risk_pct': sizing.get('risk_pct', 0.0),
        'size': sizing.get('size', 0.0),
        'fees_est': (sizing.get('size', 0.0) * 0.001 * (c.entry_price or 0.0)),
        'est_fill': c.entry_price,
        'execution_type': exec_type,
        'preview_candidate': cand,
    })


@app.route('/actions/test-order/confirm', methods=['POST'])
def confirm_test_order():
    payload = request.get_json() or {}
    cand = _parse_candidate(payload)
    if not cand:
        return jsonify({'status': 'error', 'reason': 'missing_candidate'}), 400
    mode = payload.get('mode') or 'simulated'
    # Build candidate object
    class C:
        pass
    c = C()
    c.strategy_id = cand.get('strategy_id', 'manual_test')
    c.symbol = cand.get('symbol')
    c.platform = cand.get('platform')
    c.entry_price = float(cand.get('entry_price', 0.0))
    c.stop_loss = float(cand.get('stop_loss', 0.0))
    c.side = cand.get('side')
    # Optional confidence filter to reduce noisy signals
    try:
        conf_threshold = float(os.getenv('OANDA_SIGNAL_CONFIDENCE_THRESHOLD', '0.70'))
        confidence_val = cand.get('confidence')
        if confidence_val is not None and float(confidence_val) < conf_threshold:
            return jsonify({'status': 'error', 'reason': 'low_confidence', 'confidence': confidence_val}), 400
    except Exception:
        pass

    # If the request explicitly asked for platform_paper mode, enforce it and check creds.
        exec_type = 'PLATFORM_PAPER'
        if c.platform == 'OANDA' and (OANDA is None or not getattr(OANDA, 'token', None)):
            return jsonify({'status': 'error', 'reason': 'oanda_creds_missing'}), 403
        if c.platform == 'IBKR' and not getattr(IB, 'engine', None):
            return jsonify({'status': 'error', 'reason': 'ibkr_gateway_unavailable'}), 403
    else:
        exec_type = resolve_execution_type(c.platform, supports_platform_paper=(c.platform in ('OANDA', 'IBKR')))
        # If execution_type is PLATFORM_PAPER but creds missing -> error
        if exec_type == 'PLATFORM_PAPER':
            if c.platform == 'OANDA' and (OANDA is None or not getattr(OANDA, 'token', None)):
                return jsonify({'status': 'error', 'reason': 'oanda_creds_missing'}), 403
            if c.platform == 'IBKR' and not getattr(IB, 'engine', None):
                return jsonify({'status': 'error', 'reason': 'ibkr_gateway_unavailable'}), 403
    # Final sizing
    sizing = RM.size_for_trade(c, RM.state.equity_now or 100000.0, fee_pct=0.001, slippage_pct=0.001)
    if not sizing.get('allowed'):
        return jsonify({'status': 'error', 'reason': 'sizing_rejected'}), 400
    size = sizing['size']
    # Place order according to execution_type
    if exec_type == 'PLATFORM_PAPER':
        if c.platform == 'OANDA' and OANDA is not None:
            res = OANDA.place_paper_order(c, units=1 if c.side=='BUY' else -1)
            ENGINE._record_audit({'type':'TEST_ORDER','mode':'PLATFORM_PAPER','platform':'OANDA','result':res})
            return jsonify({'status':'ok','result':res})
        if c.platform == 'IBKR':
            res = IB.place_paper_order(c, size)
            ENGINE._record_audit({'type':'TEST_ORDER','mode':'PLATFORM_PAPER','platform':'IBKR','result':res})
            return jsonify({'status':'ok','result':res})
    # Otherwise simulate via connector or engine
    if c.platform == 'COINBASE':
        try:
            res = COIN.place_paper_order(c, size)
        except Exception:
            res = ENGINE.place_order(c, size, execution_type='SIMULATED')
    else:
        res = ENGINE.place_order(c, size, execution_type='SIMULATED')
    ENGINE._record_audit({'type':'TEST_ORDER','mode':'SIMULATED','platform':c.platform,'result':res})
    return jsonify({'status':'ok','result':res})


if __name__ == '__main__':
    app.run(port=8000, debug=True)
