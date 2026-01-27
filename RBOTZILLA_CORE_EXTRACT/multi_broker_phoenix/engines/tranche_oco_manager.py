"""Tranche OCO Trade Manager

Implements staged (3-tranche) execution and partial-stop mechanics for
strategies that supply a `tranche_plan` on their TradeCandidate (e.g.,
FABIO_AAA_FULL). This manager is intentionally conservative and **only**
activates when the candidate either has a `tranche_plan` attribute or
its `strategy_id` equals 'fabio_aaa_full'.

The manager simulates the lifecycle in-memory and uses the PaperEngine
for initial entry placement only (the paper engine stores filled entries).
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional


class TrancheOCOTradeManager:
    def __init__(self, paper_engine):
        self.paper_engine = paper_engine
        # Tracking active plans: id -> plan state
        self.active_plans: Dict[str, Dict[str, Any]] = {}

    def supports_candidate(self, candidate: Any) -> bool:
        return getattr(candidate, 'strategy_id', '') == 'fabio_aaa_full' or hasattr(candidate, 'tranche_plan')

    def execute_tranche_plan(self, candidate: Any, total_size_usd: float) -> Optional[Dict[str, Any]]:
        """Start the tranche plan: place initial entry (first tranche) and register plan state.

        Returns a dict with plan_id and placed order (paper_engine order dict) or None if not supported.
        """
        if not self.supports_candidate(candidate):
            return None
        plan = getattr(candidate, 'tranche_plan', None)
        if not plan or len(plan) == 0:
            return None

        # Convert total USD to units based on entry price
        entry_price = float(getattr(candidate, 'entry_price', getattr(candidate, 'entry', 0.0)))
        if entry_price <= 0:
            return None
        total_units = float(total_size_usd) / entry_price

        # Build plan state
        plan_state = {
            'candidate': candidate,
            'entry_price': entry_price,
            'total_units': total_units,
            'remaining_units': total_units,
            'tranches': [],  # each tranche: {units, stop_price, take_price, closed}
            'first_tranche_closed': False
        }

        # Populate tranches with computed units
        tranches_state = []
        for t in plan:
            alloc = float(t.get('pct_allocation', 0.0))
            units = round(total_units * alloc, 8)
            tranches_state.append({
                'units': units,
                'stop_price': float(t['stop_price']),
                'take_price': float(t['take_price']),
                'closed': False,
                'note': t.get('note', '')
            })
        plan_state['tranches'] = tranches_state

        # Place initial tranche entry via PaperEngine: only the first tranche size
        first_units = tranches_state[0]['units']
        placed = self.paper_engine.place_order(candidate, size=first_units, execution_type='TRANCHE_ENTRY')

        plan_id = placed.get('id') if isinstance(placed, dict) else f"plan-{id(candidate)}"
        plan_state['plan_id'] = plan_id
        plan_state['placed_first'] = placed
        plan_state['remaining_units'] = max(0.0, plan_state['remaining_units'] - first_units)

        # Save state
        self.active_plans[plan_id] = plan_state
        return {'plan_id': plan_id, 'placed': placed}

    def simulate_market_tick(self, price: float) -> List[Dict[str, Any]]:
        """Simulate a market price tick and process tranche hits.

        Returns a list of events describing actions taken (take, stop, move_stop).
        """
        events: List[Dict[str, Any]] = []
        to_remove = []
        for plan_id, ps in list(self.active_plans.items()):
            candidate = ps['candidate']
            tranches = ps['tranches']
            entry = ps['entry_price']
            is_long = str(getattr(candidate, 'side', 'BUY')).upper() in ('BUY', 'LONG')

            # Check each tranche in order
            for idx, t in enumerate(tranches):
                if t['closed']:
                    continue
                # Check take
                take_hit = price >= t['take_price'] if is_long else price <= t['take_price']
                stop_hit = price <= t['stop_price'] if is_long else price >= t['stop_price']

                if take_hit:
                    t['closed'] = True
                    ps['remaining_units'] = max(0.0, ps['remaining_units'] - t['units'])
                    events.append({'plan_id': plan_id, 'event': 'take', 'tranche': idx, 'units': t['units'], 'price': price})
                    # After first tranche closed, move stops of remaining tranches to breakeven
                    if not ps['first_tranche_closed']:
                        ps['first_tranche_closed'] = True
                        for j in range(len(tranches)):
                            if not tranches[j]['closed']:
                                tranches[j]['stop_price'] = entry  # move to breakeven
                                events.append({'plan_id': plan_id, 'event': 'move_stop_to_breakeven', 'tranche': j, 'new_stop': entry})
                    continue
                if stop_hit:
                    # stop everything: close remaining units
                    closed_units = 0.0
                    for j in range(len(tranches)):
                        if not tranches[j]['closed']:
                            closed_units += tranches[j]['units']
                            tranches[j]['closed'] = True
                    ps['remaining_units'] = 0.0
                    events.append({'plan_id': plan_id, 'event': 'stop_all', 'closed_units': closed_units, 'price': price})
                    to_remove.append(plan_id)
                    break
            # remove completed plans (all tranches closed)
            all_closed = all(t['closed'] for t in tranches)
            if all_closed:
                events.append({'plan_id': plan_id, 'event': 'completed'})
                to_remove.append(plan_id)
        for pid in to_remove:
            self.active_plans.pop(pid, None)
        return events


__all__ = ['TrancheOCOTradeManager']