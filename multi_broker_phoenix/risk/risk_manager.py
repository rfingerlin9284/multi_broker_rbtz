from __future__ import annotations
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import yaml

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'risk_config.yaml')

@dataclass
class RiskPolicy:
    name: str
    base_risk_per_trade_pct: float
    max_open_risk_pct: float
    max_trades_per_platform: int
    allow_new_trades: bool
    triage_mode: bool

@dataclass
class RiskState:
    equity_now: float = 0.0
    equity_peak: float = 0.0
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0
    daily_pnl_pct: float = 0.0
    weekly_pnl_pct: float = 0.0
    open_risk_pct: float = 0.0
    open_trades_by_platform: Dict[str,int] = field(default_factory=dict)
    open_positions_by_symbol: Dict[str,list] = field(default_factory=dict)
    triage_mode: bool = False
    halted: bool = False
    policy: Optional[RiskPolicy] = None
    regime_by_symbol: Dict[str, Dict[str,str]] = field(default_factory=dict)
    reduced_risk_scale: float = 1.0

class RiskManager:
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._load_config()
        self.state = RiskState()

    def _load_config(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}
        except Exception:
            self.config = {}
        self.config.setdefault('max_concurrent_trades', 4)
        self.config.setdefault('max_total_open_risk_pct', 0.05)
        self.config.setdefault('default_risk_per_trade_pct', 0.0075)
        self.config.setdefault('pnl_brakes', {'daily_loss_limit_pct': -3.0, 'weekly_loss_limit_pct': -8.0})
        self.config.setdefault('platform_limits', {'OANDA': {'max_open_trades': 3}, 'COINBASE': {'max_open_trades': 3}, 'IBKR': {'max_open_trades': 3}})
        self.config.setdefault('drawdown_ladder', [
            {'name':'NORMAL','dd_min':0.0,'dd_max':0.10,'base_risk_per_trade_pct':0.0075,'max_open_risk_pct':0.05,'max_trades_per_platform':3,'allow_new_trades':True,'triage_mode':False},
            {'name':'TRIAGE','dd_min':0.10,'dd_max':0.30,'base_risk_per_trade_pct':0.0035,'max_open_risk_pct':0.03,'max_trades_per_platform':2,'allow_new_trades':True,'triage_mode':True},
            {'name':'HALTED','dd_min':0.30,'dd_max':1.0,'base_risk_per_trade_pct':0.0,'max_open_risk_pct':0.0,'max_trades_per_platform':0,'allow_new_trades':False,'triage_mode':True},
        ])
        self.config.setdefault('regime_risk_multipliers', {
            'BULL': {'LOW': 1.0, 'NORMAL': 1.0, 'HIGH': 0.75, 'EXTREME': 0.0},
            'BEAR': {'LOW': 1.0, 'NORMAL': 1.0, 'HIGH': 0.75, 'EXTREME': 0.0},
            'RANGE': {'LOW': 0.75, 'NORMAL': 0.75, 'HIGH': 0.5, 'EXTREME': 0.0},
        })

    def update_equity(self, equity: float, timestamp: Optional[datetime] = None):
        if equity <= 0:
            return
        if equity > self.state.equity_peak:
            self.state.equity_peak = equity
        self.state.equity_now = equity
        peak = self.state.equity_peak or equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        self.state.current_drawdown = dd
        self.state.max_drawdown = max(self.state.max_drawdown, dd)
        self._evaluate_drawdown_actions()

    def _evaluate_drawdown_actions(self):
        dd = self.state.current_drawdown
        ladder = self.config.get('drawdown_ladder', [])
        matched = None
        for row in ladder:
            if float(row.get('dd_min',0.0)) <= dd < float(row.get('dd_max',1.0)):
                matched = row
                break
        if matched is None and ladder:
            matched = ladder[-1]
        if matched is None:
            self.state.policy = None
            self.state.triage_mode = False
            self.state.halted = False
            self.state.reduced_risk_scale = 1.0
            return
        pol = RiskPolicy(
            name=str(matched.get('name','NORMAL')),
            base_risk_per_trade_pct=float(matched.get('base_risk_per_trade_pct', self.config['default_risk_per_trade_pct'])),
            max_open_risk_pct=float(matched.get('max_open_risk_pct', self.config['max_total_open_risk_pct'])),
            max_trades_per_platform=int(matched.get('max_trades_per_platform', 3)),
            allow_new_trades=bool(matched.get('allow_new_trades', True)),
            triage_mode=bool(matched.get('triage_mode', False)),
        )
        self.state.policy = pol
        self.state.triage_mode = pol.triage_mode
        self.state.halted = not pol.allow_new_trades
        scale_map = {'NORMAL':1.0,'TRIAGE':0.5,'HALTED':0.0}
        self.state.reduced_risk_scale = scale_map.get(pol.name.upper(), 1.0)

    def is_trading_allowed(self) -> bool:
        if self.state.halted:
            return False
        brakes = self.config.get('pnl_brakes', {})
        if self.state.daily_pnl_pct <= float(brakes.get('daily_loss_limit_pct', -3.0)):
            return False
        if self.state.weekly_pnl_pct <= float(brakes.get('weekly_loss_limit_pct', -8.0)):
            return False
        return True

    def get_effective_risk_for_trade(self, base_risk_pct: float) -> float:
        return float(base_risk_pct) * float(getattr(self.state, 'reduced_risk_scale', 1.0))

    def size_for_trade(self, candidate, account_equity: float, base_risk_pct: Optional[float] = None, fee_pct: float = 0.0, slippage_pct: float = 0.0) -> Dict[str, float]:
        """Compute position size (units) and effective risk pct accounting for fees/slippage.

        Rules:
        - Use policy base risk if not provided
        - Apply reduced risk scale and regime multipliers
        - Compute monetary risk per unit as distance to stop
        - Deduct fees+slippage from allowable risk budget conservatively
        """
        base = float(base_risk_pct if base_risk_pct is not None else getattr(self.state.policy, 'base_risk_per_trade_pct', self.config.get('default_risk_per_trade_pct', 0.0075)))
        # apply reduced risk scale
        base = self.get_effective_risk_for_trade(base)
        # regime multiplier lookup
        symbol = getattr(candidate, 'symbol', None)
        mult = 1.0
        try:
            regimes = self.state.regime_by_symbol.get(symbol) if symbol else None
            trend = regimes.get('trend') if regimes else 'RANGE'
            vol = regimes.get('vol') if regimes else 'NORMAL'
            mult = float(self.config.get('regime_risk_multipliers', {}).get(trend, {}).get(vol, 1.0))
        except Exception:
            mult = 1.0
        effective_pct = base * float(mult)
        # adjust for fees/slippage conservatively
        effective_pct = max(0.0, effective_pct - (fee_pct + slippage_pct))
        # compute size using distance to stop
        dist = abs(float(getattr(candidate, 'entry_price', 0.0)) - float(getattr(candidate, 'stop_loss', 0.0)))
        if dist <= 0:
            return {'allowed': False, 'reason': 'invalid_stop_distance', 'risk_pct': 0.0, 'size': 0.0}
        max_loss_money = float(account_equity) * effective_pct
        size = max_loss_money / dist if dist > 0 else 0.0
        if size <= 0:
            return {'allowed': False, 'reason': 'size_below_minimum', 'risk_pct': effective_pct, 'size': 0.0}
        return {'allowed': True, 'reason': 'OK', 'risk_pct': effective_pct, 'size': size}

    def can_place_trade(self, proposed_risk_pct: float, open_trades_count: int, total_open_risk_pct: float) -> Dict[str,Any]:
        if self.state.halted:
            return {'allowed': False, 'reason': 'HALTED', 'effective_risk_pct': 0.0}
        if open_trades_count >= int(self.config.get('max_concurrent_trades', 4)):
            return {'allowed': False, 'reason': 'MAX_CONCURRENT_TRADES', 'effective_risk_pct': self.get_effective_risk_for_trade(self.config['default_risk_per_trade_pct'])}
        if total_open_risk_pct + float(proposed_risk_pct) > float(self.config.get('max_total_open_risk_pct', 0.05)):
            return {'allowed': False, 'reason': 'PORTFOLIO_RISK_CAP', 'effective_risk_pct': self.get_effective_risk_for_trade(self.config['default_risk_per_trade_pct'])}
        return {'allowed': True, 'reason': 'OK', 'effective_risk_pct': self.get_effective_risk_for_trade(self.config['default_risk_per_trade_pct'])}