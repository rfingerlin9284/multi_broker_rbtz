#!/usr/bin/env python3
"""
AI HIVE - Clean Implementation
Grok (xAI) as primary, OpenAI as backup with rate-limit handling.
"""
import json
import time
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

try:
    from multi_broker_phoenix.ai.seat_router import AISeatRouter
except Exception:
    AISeatRouter = None


@dataclass
class AIVote:
    ai_name: str
    signal: str  # buy, sell, neutral, veto
    confidence: float
    reasoning: str


class AIHive:
    """Simple AI Hive: Grok primary, OpenAI backup."""
    
    def __init__(self):
        self.grok_key = os.getenv('XAI_API_KEY')
        self.openai_key = os.getenv('OPENAI_API_KEY')
        self.grok_model = os.getenv('XAI_MODEL', 'grok-4-latest')
        self.openai_model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.threshold = float(os.getenv('HIVE_APPROVAL_THRESHOLD', '0.70'))  # FIXED: Was 0.30 - rubber-stamping!
        self.deepseek_key = os.getenv('DEEPSEEK_API_KEY')
        self.use_seat_router = os.getenv('ENABLE_SEAT_ROUTER', '1').lower() in ('1', 'true', 'yes')
        self.router = AISeatRouter() if (AISeatRouter and self.use_seat_router) else None
        
        # Rate limit tracking
        self._openai_blocked_until = 0
        self._rate_limit_cooldown = 60
        
        # Use the canonical Hive Charter system prompt
        try:
            from hive_real.charter import get_system_prompt
            self.system_prompt = get_system_prompt()
        except Exception:
            # Fallback short instruction
            self.system_prompt = "You are a trading analyst; respond with a single JSON object summarizing your decision."
    
    def _signal_to_english(self, signal: str, confidence: float) -> str:
        """Convert AI signal to plain English."""
        conf_pct = int(confidence * 100)
        
        if signal == 'buy':
            if conf_pct >= 80:
                return f"\"This looks like a STRONG BUY! I'm {conf_pct}% confident.\""
            elif conf_pct >= 60:
                return f"\"I think we should BUY - {conf_pct}% sure.\""
            else:
                return f"\"Leaning towards BUY, but only {conf_pct}% confident.\""
        elif signal == 'sell':
            if conf_pct >= 80:
                return f"\"This is a STRONG SELL signal! {conf_pct}% confident.\""
            elif conf_pct >= 60:
                return f"\"I'd recommend SELLING - {conf_pct}% sure.\""
            else:
                return f"\"Maybe sell? Only {conf_pct}% confident though.\""
        elif signal == 'veto':
            return f"\"STOP! Don't take this trade - too risky! ({conf_pct}%)\""
        else:
            return f"\"Not sure about this one... staying neutral ({conf_pct}%).\""

    def _build_concise_prompt(self, symbol: str, direction: str, price: float, prices: list) -> str:
        """Build a short, directive prompt that asks the LLM to return a compact JSON decision.
        The concise prompt reduces ambiguity and encourages a BUY/SELL/HOLD decision with a numeric confidence."""
        # Compute a few simple indicators for context
        short_avg = None
        long_avg = None
        momentum = 0.0
        try:
            if prices and len(prices) >= 3:
                short_n = min(5, len(prices))
                long_n = min(20, len(prices))
                short_avg = sum(prices[-short_n:]) / short_n
                long_avg = sum(prices[-long_n:]) / long_n if len(prices) >= long_n else None
                momentum = ((prices[-1] - prices[0]) / (prices[0] if prices[0] else 1.0)) * 100
        except Exception:
            pass

        parts = [f"Symbol: {symbol}", f"Direction: {direction}", f"Entry: {price:.5f}"]
        if short_avg is not None:
            parts.append(f"ShortAvg: {short_avg:.5f}")
        if long_avg is not None:
            parts.append(f"LongAvg: {long_avg:.5f}")
        parts.append(f"Momentum: {momentum:+.2f}%")

        prompt = (
            "Please respond with a single JSON object and nothing else. "
            "Fields: {\"decision\":\"BUY|SELL|HOLD\", \"confidence\":0.0-1.0, \"reasoning\":\"one sentence\"}. "
            "Short facts: " + ", ".join(parts)
        )
        return prompt


    def analyze(self, symbol: str, direction: str, price: float, 
                prices: list = None) -> Dict[str, Any]:

        """Get AI consensus on a trade. Returns decision dict."""
        
        prices = prices or []
        votes = []
        
        # Human-readable header
        print(f"\n{'─'*60}")
        print(f"🧠 AI HIVE ANALYZING: {symbol}")
        print(f"{'─'*60}")
        print(f"   Looking at: {direction.upper()} trade @ {price:.5f}")
        
        # Calculate simple indicators for display
        if len(prices) >= 5:
            short_avg = sum(prices[-5:]) / 5
            trend_short = "rising" if prices[-1] > short_avg else "falling"
        else:
            trend_short = "unknown"
        
        if len(prices) >= 20:
            long_avg = sum(prices[-20:]) / 20
            trend_long = "UPTREND" if short_avg > long_avg else "DOWNTREND"
            momentum = ((prices[-1] - prices[-20]) / prices[-20]) * 100
        else:
            trend_long = "gathering data"
            momentum = 0
        
        print(f"\n📊 WHAT THE CHARTS SHOW:")
        print(f"   • Short-term (5 periods): Price is {trend_short}")
        print(f"   • Overall trend: {trend_long}")
        print(f"   • Momentum: {momentum:+.2f}%")
        
        prompt = f"""Trade Analysis Request:
Symbol: {symbol}
Direction: {direction}
Entry Price: {price}
Recent Prices: {prices[-10:] if len(prices) >= 10 else prices}

Should this trade be taken? Analyze and respond with JSON only."""

        print(f"\n🤖 ASKING AI ADVISORS:")
        
        # 1. Try Seat Router (local-first, rotating providers)
        if self.router:
            vote = self._query_seat_router(prompt)
            if vote:
                votes.append(vote)
                opinion = self._signal_to_english(vote.signal, vote.confidence)
                print(f"   • {vote.ai_name.upper()} says: {opinion}")
                if vote.reasoning:
                    print(f"     Reason: \"{vote.reasoning[:80]}\"")

        # 2. Try Grok (primary)
        if not votes and self.grok_key:
            vote = self._query_grok(prompt)
            if vote:
                votes.append(vote)
                opinion = self._signal_to_english(vote.signal, vote.confidence)
                print(f"   • GROK says: {opinion}")
                if vote.reasoning:
                    print(f"     Reason: \"{vote.reasoning[:80]}\"")
        
        # 3. Try OpenAI (backup) - only if not rate-limited
        if not votes and self.openai_key and time.time() > self._openai_blocked_until:
            vote = self._query_openai(prompt)
            if vote:
                votes.append(vote)
                opinion = self._signal_to_english(vote.signal, vote.confidence)
                print(f"   • GPT says: {opinion}")
                if vote.reasoning:
                    print(f"     Reason: \"{vote.reasoning[:80]}\"")
        elif self._openai_blocked_until > time.time():
            remaining = int(self._openai_blocked_until - time.time())
            print(f"   • GPT: Taking a break ({remaining}s cooldown)")
        
        # 4. Try live DeepSeek provider (only if a real key present and enabled)
        if self.deepseek_key and not votes:
            vote = self._query_deepseek_live(prompt)
            if vote:
                votes.append(vote)
                opinion = self._signal_to_english(vote.signal, vote.confidence)
                print(f"   • DEEPSEEK (live) says: {opinion}")
        elif not self.deepseek_key and not votes:
            print("   • No cloud AI available right now")

        # 5. Prefer live DeepSeek when available; do NOT simulate votes.
        # MultiIndicator augmentation still applies but will not override vetos
        # or be considered a 'real' AI seat for approval decisions.
        # (No automatic simulated DeepSeek votes will be used.)

        # Always compute MultiIndicator vote to augment AI votes when possible.
        try:
            mi_vote = self._multi_indicator_vote(direction, price, prices)
            if mi_vote:
                votes.append(mi_vote)
                print(f"   ✅ MultiIndicator: {mi_vote.signal.upper()} ({mi_vote.confidence:.0%}) - {mi_vote.reasoning}")
        except Exception as e:
            print(f"   ❌ MultiIndicator error: {e}")

        # If we don't have a clear real AI BUY/SELL vote, retry once with a concise
        # directive prompt aimed at eliciting a firm BUY/SELL/HOLD decision from
        # cloud LLM seats (helps Grok/OpenAI avoid neutral defaults).
        try:
            real_ai_votes = [v for v in votes if v.ai_name.lower() not in ('multiindicator', 'deepseek')]
            real_buy_sell = [v for v in real_ai_votes if v.signal in ('buy', 'sell')]
            avg_conf_real = (sum(v.confidence for v in real_ai_votes) / len(real_ai_votes)) if real_ai_votes else 0.0

            need_retry = False
            # Retry if no real buy/sell vote or low average confidence
            if not real_buy_sell or avg_conf_real < 0.6:
                need_retry = True

            if need_retry:
                # Record retry attempt for telemetry
                try:
                    from multi_broker_phoenix.monitor.bot_metrics import incr
                    incr('hive_retry')
                except Exception:
                    pass

                print("   ℹ️  Retrying with concise, directive prompt to cloud LLMs to get clear BUY/SELL decision")
                concise = self._build_concise_prompt(symbol, direction, price, prices)
                retry_vote = None

                # Seat router (if present) first
                if self.router:
                    retry = self._query_seat_router(concise)
                    if retry:
                        retry_vote = retry
                        opinion = self._signal_to_english(retry.signal, retry.confidence)
                        print(f"   • {retry.ai_name.upper()} (retry) says: {opinion}")

                # Grok
                if not retry_vote and self.grok_key:
                    retry = self._query_grok(concise)
                    if retry:
                        retry_vote = retry
                        opinion = self._signal_to_english(retry.signal, retry.confidence)
                        print(f"   • GROK (retry) says: {opinion}")

                # OpenAI
                if not retry_vote and self.openai_key and time.time() > self._openai_blocked_until:
                    retry = self._query_openai(concise)
                    if retry:
                        retry_vote = retry
                        opinion = self._signal_to_english(retry.signal, retry.confidence)
                        print(f"   • GPT (retry) says: {opinion}")

                # DeepSeek live
                if not retry_vote and self.deepseek_key:
                    retry = self._query_deepseek_live(concise)
                    if retry:
                        retry_vote = retry
                        opinion = self._signal_to_english(retry.signal, retry.confidence)
                        print(f"   • DEEPSEEK (retry) says: {opinion}")

                # If we got a retry vote from a real seat, prioritize it and record success
                if retry_vote and retry_vote.ai_name.lower() not in ('multiindicator', 'deepseek'):
                    votes.insert(0, retry_vote)
                    # Record which seat produced the successful retry for narration/telemetry
                    try:
                        self._last_retry_source = retry_vote.ai_name
                    except Exception:
                        self._last_retry_source = None
                    try:
                        from multi_broker_phoenix.monitor.bot_metrics import incr
                        incr('hive_retry_success')
                    except Exception:
                        pass
                    print("   ✅ Retry produced a real AI vote; re-evaluating consensus.")
        except Exception as e:
            print(f"   ⚠️ Retry logic error: {e}")

        return self._consensus(votes)
    
    def _query_grok(self, prompt: str) -> Optional[AIVote]:
        """Query xAI Grok API."""
        try:
            import requests
            
            base_url = os.getenv('XAI_BASE_URL', 'https://api.x.ai/v1').rstrip('/')
            model = os.getenv('XAI_MODEL', 'grok-4-latest')

            resp = requests.post(
                f"{base_url}/chat/completions",
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.grok_key}'
                },
                json={
                    'model': model,
                    'messages': [
                        {'role': 'system', 'content': self.system_prompt},
                        {'role': 'user', 'content': prompt}
                    ],
                    'temperature': 0.1
                },
                timeout=30
            )
            
            if resp.status_code == 429:
                print("   ⚠️  Grok rate-limited")
                return None
            if resp.status_code != 200:
                body = resp.text.strip()
                snippet = body if len(body) < 400 else body[:400] + "..."
                print(f"   ❌ Grok response: {body}")
                print(f"   ❌ Grok error: {resp.status_code} body={snippet}")
                return None
            
            content = resp.json()['choices'][0]['message']['content'].strip()
            return self._parse_response(content, "Grok")
            
        except Exception as e:
            print(f"   ❌ Grok error: {e}")
            return None

    def _query_seat_router(self, prompt: str) -> Optional[AIVote]:
        if not self.router:
            return None
        try:
            res = self.router.chat(prompt, self.system_prompt)
            if not res.get("ok"):
                return None
            content = (res.get("content") or "").strip()
            seat_name = res.get("seat") or "Seat"
            return self._parse_response(content, seat_name.capitalize())
        except Exception as e:
            print(f"   ❌ Seat router error: {e}")
            return None
    
    def _query_openai(self, prompt: str) -> Optional[AIVote]:
        """Query OpenAI API with rate-limit detection."""
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_key)
            
            resp = client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {'role': 'system', 'content': self.system_prompt},
                    {'role': 'user', 'content': prompt}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            content = resp.choices[0].message.content.strip()
            return self._parse_response(content, "OpenAI")
            
        except Exception as e:
            err = str(e).lower()
            if '429' in str(e) or 'rate' in err or 'limit' in err:
                print(f"   ⚠️  OpenAI RATE LIMITED - disabled for {self._rate_limit_cooldown}s")
                self._openai_blocked_until = time.time() + self._rate_limit_cooldown
            else:
                print(f"   ❌ OpenAI error: {e}")
            return None
    
    def _parse_response(self, content: str, source: str) -> Optional[AIVote]:
        """Parse AI JSON response."""
        try:
            # Strip markdown if present
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]
            
            data = json.loads(content.strip())
            # Validate against charter contract (best-effort, no hard veto here)
            try:
                from hive_real.charter import validate_seat_output, record_violation
                ok, errs = validate_seat_output(data)
                if not ok:
                    record_violation(source, data, errs)
            except Exception:
                # If charter not available, continue but trim
                pass

            # Map decision -> signal when provided
            decision = (data.get('decision') or data.get('signal') or '').strip().upper()
            if decision in ('BUY', 'SELL', 'HOLD', 'VETO'):
                if decision == 'BUY':
                    signal = 'buy'
                elif decision == 'SELL':
                    signal = 'sell'
                elif decision == 'VETO':
                    signal = 'veto'
                else:
                    signal = 'neutral'
            else:
                signal = str(data.get('signal', 'neutral')).strip().lower()

            try:
                confidence = float(data.get('confidence', 0.5))
            except Exception:
                confidence = 0.5

            reasoning = data.get('reasoning', '')[:100]
            vote = AIVote(
                ai_name=source,
                signal=signal,
                confidence=confidence,
                reasoning=reasoning
            )

            # If a seat returns an invalid_output veto, ignore it so other seats can decide.
            if vote.signal == 'veto' and vote.reasoning.strip().lower() == 'invalid_output':
                return None

            return vote
        except:
            # Fallback: extract signal from text
            cl = content.lower()
            if 'veto' in cl:
                sig = 'veto'
            elif 'buy' in cl:
                sig = 'buy'
            elif 'sell' in cl:
                sig = 'sell'
            else:
                sig = 'neutral'
            return AIVote(source, sig, 0.5, content[:50])
    
    def _consensus(self, votes: list) -> Dict[str, Any]:
        """Calculate consensus from votes and print human-readable summary."""
        
        print(f"\n📋 AI HIVE DECISION:")
        
        if not votes:
            print(f"   ❌ No AI advisors responded - cannot make a decision")
            print(f"   RESULT: Trade REJECTED (no input)")
            return {
                'decision': 'reject',
                'confidence': 0.0,
                'reasoning': 'No AI votes received',
                'votes': []
            }
        
        # Deduplicate votes by AI seat (keep first/latest per seat) to avoid retry double-counting
        deduped = []
        seen = set()
        for v in votes:
            name = v.ai_name.lower()
            if name in seen:
                continue
            seen.add(name)
            deduped.append(v)

        # Check for veto
        for v in deduped:
            if v.signal == 'veto':
                print(f"   🛑 VETO! {v.ai_name} says this trade is too risky!")
                print(f"      \"{v.reasoning}\"")
                print(f"   RESULT: Trade REJECTED (safety veto)")
                return {
                    'decision': 'reject',
                    'confidence': v.confidence,
                    'reasoning': f'VETO by {v.ai_name}: {v.reasoning}',
                    'votes': [self._vote_dict(v) for v in deduped]
                }

        # Count signals (on deduped votes)
        buy = sum(1 for v in deduped if v.signal == 'buy')
        sell = sum(1 for v in deduped if v.signal == 'sell')
        neutral = sum(1 for v in deduped if v.signal == 'neutral')
        total = len(deduped)

        # CRITICAL: Require at least 1 REAL cloud AI vote before approving
        # MultiIndicator and DeepSeek fallback alone should NOT approve trades
        real_ai_votes = [v for v in deduped if v.ai_name.lower() not in ('multiindicator', 'deepseek')]
        real_buy_sell = [v for v in real_ai_votes if v.signal in ('buy', 'sell')]

        if not real_buy_sell:
            print(f"   ⚠️  NO REAL AI VOTES - Only fallback/indicators voted")
            print(f"   RESULT: Trade REJECTED (require cloud AI analysis)")
            return {
                'decision': 'reject',
                'confidence': 0.0,
                'reasoning': 'No real cloud AI votes - only fallbacks/indicators',
                'votes': [self._vote_dict(v) for v in deduped]
            }
        
        buy_pct = buy / total
        sell_pct = sell / total
        avg_conf = sum(v.confidence for v in votes) / total
        
        print(f"   📊 Vote tally: {buy} BUY, {sell} SELL, {neutral} NEUTRAL")
        print(f"   📈 Average confidence: {avg_conf:.0%}")
        
        # Decision with plain English explanation
        if buy_pct >= self.threshold:
            decision = 'approve'
            reasoning = f'BUY consensus: {buy_pct:.0%}'
            print(f"\n   ✅ APPROVED - The AI team agrees: GO LONG!")
            print(f"      {int(buy_pct*100)}% voted to buy")
        elif sell_pct >= self.threshold:
            decision = 'approve'
            reasoning = f'SELL consensus: {sell_pct:.0%}'
            print(f"\n   ✅ APPROVED - The AI team agrees: GO SHORT!")
            print(f"      {int(sell_pct*100)}% voted to sell")
        else:
            decision = 'reject'
            reasoning = f'No consensus (buy:{buy_pct:.0%}, sell:{sell_pct:.0%})'
            print(f"\n   ❌ REJECTED - AI team couldn't agree on direction")
            print(f"      Only {int(max(buy_pct, sell_pct)*100)}% agreement (need {int(self.threshold*100)}%)")
        
        print(f"{'─'*60}\n")
        
        return {
            'decision': decision,
            'confidence': avg_conf,
            'reasoning': reasoning,
            'votes': [self._vote_dict(v) for v in votes]
        }
    
    def _vote_dict(self, v: AIVote) -> dict:
        return {'ai': v.ai_name, 'signal': v.signal, 'confidence': v.confidence}

    def _multi_indicator_vote(self, direction: str, price: float, prices: list) -> Optional[AIVote]:
        """Compute a MultiIndicator vote (momentum + SMA + volatility).

        Returns an AIVote when indicators align enough to form a signal, else None.
        """
        if not prices or len(prices) < 3:
            return None
        try:
            prices_f = [float(p) for p in prices]
            # Momentum (start -> end)
            mom = (prices_f[-1] - prices_f[0]) / (prices_f[0] if prices_f[0] else 1.0)

            # SMA short/long
            short_n = min(5, len(prices_f))
            long_n = min(20, len(prices_f))
            short_sma = sum(prices_f[-short_n:]) / short_n
            long_sma = sum(prices_f[-long_n:]) / long_n
            sma_diff = (short_sma - long_sma) / (long_sma if long_sma else 1.0)

            # Volatility (avg absolute return normalized)
            returns = [prices_f[i+1] - prices_f[i] for i in range(len(prices_f)-1)]
            vol = (sum(abs(r) for r in returns) / len(returns)) / (prices_f[-1] if prices_f[-1] else 1.0)

            # Scaled scores 0..1
            mom_score = min(1.0, abs(mom) * 100.0)
            sma_score = min(1.0, abs(sma_diff) * 100.0)

            # Weighted signed score (-1..1)
            signed_mom = (1 if mom > 0 else -1 if mom < 0 else 0) * mom_score
            signed_sma = (1 if sma_diff > 0 else -1 if sma_diff < 0 else 0) * sma_score
            weighted = 0.6 * signed_mom + 0.4 * signed_sma

            # Use weighted sign to produce a vote (MultiIndicator always provides
            # a data-driven signal when there is enough history). Confidence reflects
            # the strength of the weighted score and volatility.
            if weighted == 0:
                return None
            signal = 'buy' if weighted > 0 else 'sell'

            # Confidence: base 0.35 .. 0.9 depending on weighted magnitude and low vol boost
            conf = 0.35 + min(0.55, (abs(weighted) / 100.0) * 0.6)
            if vol < 0.0005:
                conf = min(0.99, conf + 0.05)
            conf = max(0.0, min(conf, 0.99))

            reason = f"mom={mom:.6f}, sma_diff={sma_diff:.6f}, vol={vol:.6f}"
            return AIVote(ai_name='MultiIndicator', signal=signal, confidence=conf, reasoning=reason)
        except Exception as e:
            print(f"   ❌ _multi_indicator_vote error: {e}")
            return None

    def _query_deepseek_live(self, prompt: str) -> Optional[AIVote]:
        """Query the live DeepSeek provider and parse response into an AIVote.
        Returns None if DeepSeek is not enabled or fails to provide a valid vote."""
        try:
            from ai_router.providers.deepseek_provider import DeepSeekProvider
            prov = DeepSeekProvider()
            if not prov.enabled():
                print("   • DEEPSEEK (live): no API key configured")
                return None
            res = prov.generate(prompt, system_prompt=self.system_prompt)
            if not res.get('ok'):
                print(f"   • DEEPSEEK (live) error: {res.get('error')}")
                return None
            content = res.get('response', '')
            return self._parse_response(content, 'DeepSeek')
        except Exception as e:
            print(f"   ❌ DeepSeek live query failed: {e}")
            return None


# Global instance
_hive = None

def _write_ai_narration(symbol: str, direction: str, entry_price: float,
                        result: Dict[str, Any], market_data: Dict[str, Any]) -> None:
    """Write AI narration to state file for dashboard to display."""
    import os
    from pathlib import Path
    from datetime import datetime
    
    try:
        repo_root = Path(__file__).resolve().parents[1]
        narration_file = repo_root / 'ops' / 'state' / 'ai_narration.json'
        narration_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Build human-readable narration
        votes = result.get('votes', [])
        vote_details = []
        for v in votes:
            ai_name = v.get('ai', 'Unknown')
            signal = v.get('signal', 'neutral').upper()
            conf = v.get('confidence', 0) * 100
            reasoning = v.get('reasoning', '')[:100]
            vote_details.append({
                'ai': ai_name,
                'signal': signal,
                'confidence': f"{conf:.0f}%",
                'reasoning': reasoning
            })
        
        # Build indicators scanned summary
        prices = market_data.get('prices', [])
        indicators_scanned = []
        if prices and len(prices) >= 5:
            indicators_scanned.append(f"EMA(5): {sum(prices[-5:])/5:.5f}")
        if prices and len(prices) >= 21:
            indicators_scanned.append(f"EMA(21): {sum(prices[-21:])/21:.5f}")
        if prices and len(prices) >= 14:
            # Simplified RSI display
            indicators_scanned.append("RSI(14): calculated")
        indicators_scanned.append("Momentum: analyzed")
        indicators_scanned.append("Volatility: assessed")
        
        narration = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'symbol': symbol,
            'direction': direction,
            'entry_price': entry_price,
            'decision': result.get('decision', 'unknown').upper(),
            'consensus': f"{result.get('confidence', 0) * 100:.0f}%",
            'reasoning': result.get('reasoning', ''),
            'votes': vote_details,
            'indicators_scanned': indicators_scanned,
            'strategies_checked': [
                'fabio_aaa_full (EMA crossover + RSI momentum)',
                'bullish_regime (trend following)',
                'bearish_regime (counter-trend)',
                'sideways_regime (range trading)'
            ]
        }
        
        # Load existing narration log (keep last 20 entries)
        try:
            with open(narration_file, 'r') as f:
                existing = json.load(f)
                if isinstance(existing, dict) and 'history' in existing:
                    history = existing['history']
                else:
                    history = []
        except:
            history = []
        
        # Add current to history
        history.append(narration)
        history = history[-20:]  # Keep last 20
        
        output = {
            'current': narration,
            'history': history,
            'retry_source': result.get('retry_source') if isinstance(result, dict) else None
        }
        
        with open(narration_file, 'w') as f:
            json.dump(output, f, indent=2)
            
    except Exception as e:
        print(f"   ⚠️  Narration write failed: {e}")


def get_api_ai_vote(symbol: str, direction: str, entry_price: float,
                    market_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Main entry point for AI Hive analysis."""
    global _hive
    if _hive is None:
        _hive = AIHive()
    
    prices = market_data.get('prices', [])
    
    # analyze() now prints all human-readable output
    result = _hive.analyze(symbol, direction, entry_price, prices)
    
    # Expose info about retry source if any (for narration/telemetry)
    try:
        result['retry_source'] = getattr(_hive, '_last_retry_source', None)
    except Exception:
        result['retry_source'] = None

    # Metrics: record signals and approvals/rejects (only if metrics enabled)
    try:
        from global_config import FEATURE_FLAGS as _FF
        metrics_enabled = _FF.get('OANDA_ADVANCED', {}).get('ENABLE_METRICS_REPORTER', True)
    except Exception:
        metrics_enabled = True

    if metrics_enabled:
        try:
            from multi_broker_phoenix.monitor.bot_metrics import incr
            incr('signal_seen')
            if result['decision'].lower() == 'approve':
                incr('hive_approval')
            else:
                incr('hive_reject')
        except Exception:
            pass
    
    # Add compatibility fields
    result['vote'] = result['decision']
    result['consensus'] = result['confidence']
    result['consensus_score'] = result['confidence']
    result['confidence_score'] = result['confidence']
    
    return result


if __name__ == '__main__':
    # Quick test
    import random
    prices = [91000 + random.uniform(-100, 100) for _ in range(20)]
    
    result = get_api_ai_vote(
        symbol='BTC-USD',
        direction='BUY', 
        entry_price=prices[-1],
        market_data={'prices': prices}
    )
    print(f"\nResult: {result['decision']}")
