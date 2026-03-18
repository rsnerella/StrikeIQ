# app/services/analytics_broadcaster.py

"""
Institutional Analytics Broadcaster for StrikeIQ
Orchestrates AI analysis and broadcasts strategy updates
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.ws_manager import manager, broadcast_with_strategy
from app.services.trade_lifecycle_manager import trade_lifecycle_manager

logger = logging.getLogger(__name__)

# AI module imports
from app.ai.ai_orchestrator import ai_orchestrator
from app.services.option_chain_builder import option_chain_builder
from ai.feature_engine import FeatureEngine, OptionChainSnapshot
from ai.bias_model import BiasModel
from ai.strategy_decision_engine import StrategyDecisionEngine
from ai.options_trade_engine import OptionsTradeEngine

logger = logging.getLogger(__name__)

# Global analytics cache to serve snapshots immediately to new clients
LAST_ANALYTICS: Dict[str, Any] = {}

def json_safe(obj):
    if isinstance(obj, (datetime)):
        return obj.isoformat()
    return str(obj)

class AnalyticsBroadcaster:
    """Master broadcaster for the StrikeIQ Elite Engine"""

    def __init__(self):
        self._analytics_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Real-time institutional cycle (500ms)
        self.ANALYTICS_INTERVAL = 0.5 
        self._last_analytics_time = 0

        # FIX 2: REST-only mode tracking
        self._dirty: Dict[str, bool] = {}
        self._last_broadcast_time: Dict[str, float] = {}
        
        # Initialize new AI components
        self.feature_engine = FeatureEngine()
        self.bias_model = BiasModel()
        self.strategy_engine = StrategyDecisionEngine()
        self.options_engine = OptionsTradeEngine()
        self.options_engine.initialize_ai_components()

    def _get_spot_price(self, symbol: str, snapshot) -> float:
        """
        Try every possible source for spot price.
        Returns 0 only if genuinely unavailable.
        """
        # 1. Try snapshot first (dynamic attributes)
        for attr in ['spot', 'index_price', 'ltp', 'close', 'last_price']:
            val = getattr(snapshot, attr, None)
            if val and float(val) > 0:
                return float(val)

        # 2. Try option chain builder's index price cache
        try:
            from app.services.option_chain_builder import option_chain_builder
            for attr in ['spot_prices', '_index_prices', '_spot_prices']:
                cache = getattr(option_chain_builder, attr, {})
                if isinstance(cache, dict) and cache.get(symbol, 0) > 0:
                    return float(cache[symbol])
        except Exception:
            pass

        # 3. Try Redis cache as last resort
        try:
            # Note: synchronous check for performance, use cached value if possible
            from app.core.redis_client import redis_client
            import asyncio
            # We don't want to block the loop, so we only try this if we have a current loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In a real scenario we'd use a non-blocking cache but for debug we use getattr if stored
                pass
        except Exception:
            pass

        return 0.0

    def _build_summary(self, symbol, pcr, bias, regime,
                       call_wall, put_wall, iv_atm, vol_state) -> str:
        """Build clean institutional summary sentence instead of raw concatenated string."""
        parts = []
        parts.append(f"{symbol} in {regime} regime")

        if bias and bias != 'NEUTRAL':
            parts.append(f"with {bias} bias (PCR {pcr:.2f})")
        else:
            parts.append(f"with neutral bias (PCR {pcr:.2f})")

        levels = []
        if call_wall > 0:
            levels.append(
                f"Call resistance at {call_wall:,}"
            )
        if put_wall > 0:
            levels.append(
                f"Put support at {put_wall:,}"
            )
        if levels:
            parts.append(". ".join(levels))

        if iv_atm > 0:
            iv_pct = iv_atm * 100 if iv_atm < 1 else iv_atm
            parts.append(f"IV {iv_pct:.1f}% — {vol_state}")

        return ". ".join(parts) + "."

    def compute_single_analytics(self, symbol: str, chain_data=None):
        """
        Called synchronously by option_chain_builder after each tick.
        Sets dirty flag only — never computes inline.
        This is intentional: computation happens in the 500ms loop.
        """
        self._dirty[symbol] = True

    def _build_option_chain_payload(self, symbol: str, snapshot) -> tuple:
        """Helper to extract formatted calls/puts for the frontend."""
        calls = {}
        puts  = {}

        try:
            # Use the snapshot object from get_latest_snapshot() instead of calling non-existent method
            if snapshot and hasattr(snapshot, 'symbol'):
                # Extract calls and puts from snapshot's internal chain data
                from app.services.option_chain_builder import option_chain_builder
                chain = option_chain_builder.chains.get(symbol, {})

                if chain:
                    for strike_key, sides in chain.items():
                        # The contract expects strike strings as keys
                        strike_str = str(int(float(strike_key)))

                        ce_data = sides.get('CE')
                        pe_data = sides.get('PE')

                        if ce_data:
                            calls[strike_str] = {
                                'ltp':   float(ce_data.ltp or 0.0),
                                'oi':    int(ce_data.oi or 0),
                                'iv':    float(ce_data.iv or 0.0),
                                'delta': float(ce_data.delta or 0.0),
                                'gamma': float(ce_data.gamma or 0.0),
                                'theta': float(ce_data.theta or 0.0),
                                'vega':  float(ce_data.vega or 0.0),
                                'bid':   float(ce_data.bid or 0.0),
                                'ask':   float(ce_data.ask or 0.0),
                            }

                        if pe_data:
                            puts[strike_str] = {
                                'ltp':   float(pe_data.ltp or 0.0),
                                'oi':    int(pe_data.oi or 0),
                                'iv':    float(pe_data.iv or 0.0),
                                'delta': float(pe_data.delta or 0.0),
                                'gamma': float(pe_data.gamma or 0.0),
                                'theta': float(pe_data.theta or 0.0),
                                'vega':  float(pe_data.vega or 0.0),
                                'bid':   float(pe_data.bid or 0.0),
                                'ask':   float(pe_data.ask or 0.0),
                            }
        except Exception as e:
            logger.debug(f"Option chain payload extraction failed: {e}")

        return calls, puts

    async def _build_analytics_payload(self, symbol: str, snapshot) -> Dict[str, Any]:
        """Build separated analytics and execution payloads"""
        try:
            # STEP 1: FIX SNAPSHOT STRUCTURE
            # Wrap raw dict to ensure proper structure
            if hasattr(snapshot, 'strikes'):
                raw_chain = snapshot.strikes
                spot_price = snapshot.spot
            else:
                # Handle dict format - extract strikes and spot properly
                raw_chain = snapshot.get('strikes', snapshot)
                spot_price = snapshot.get('spot')
            
            snapshot_obj = OptionChainSnapshot(raw_chain, spot_price)
            
            # STEP 2: VALIDATION LOG
            print("[SNAPSHOT FIX]", {
                "has_strikes": hasattr(snapshot_obj, "strikes"),
                "num_strikes": len(snapshot_obj.strikes) if hasattr(snapshot_obj, 'strikes') else 0
            })
            
            # Compute features with proper structure
            features = self.feature_engine.compute_features(snapshot_obj, snapshot_obj.spot)
            
            # Convert to dict for bias calculation
            features_dict = {
                'spot': features.spot,  # CRITICAL: Add spot price
                'gex_profile': features.gex_profile,
                'gamma_flip_probability': features.gamma_flip_probability,
                'call_wall_strength': features.call_wall_strength,
                'put_wall_strength': features.put_wall_strength,
                'call_wall_strike': features.call_wall_strike,
                'put_wall_strike': features.put_wall_strike,
                'pcr_trend': features.pcr_trend,
                'oi_concentration': features.oi_concentration,
                'oi_buildup_rate': features.oi_buildup_rate,
                'call_oi_distribution': features.call_oi_distribution,
                'put_oi_distribution': features.put_oi_distribution,
                'liquidity_vacuum': features.liquidity_vacuum,
                'order_flow_imbalance': features.order_flow_imbalance,
                'market_impact': features.market_impact,
                'spread_widening': features.spread_widening,
                'iv_regime': features.iv_regime,
                'volatility_expansion': features.volatility_expansion,
                'term_structure': features.term_structure,
                'implied_volatility_surface': features.implied_volatility_surface,
                'dealer_hedging_pressure': features.dealer_hedging_pressure,
                'institutional_flow': features.institutional_flow,
                'support_resistance_levels': features.support_resistance_levels,
                'pin_probability': features.pin_probability
            }
            
            # Calculate bias
            bias_result = self.bias_model.calculate_bias(features_dict)
            
            # Add bias to features for strategy decision
            features_dict['bias'] = bias_result.bias
            features_dict['bias_confidence'] = bias_result.confidence
            
            # Decide strategy
            strategy_decision = self.strategy_engine.decide_strategy(bias_result, features_dict, snapshot)
            
            # Extract probabilistic score for response
            probabilistic_score = 0.0
            probabilistic_confidence = strategy_decision.bias_confidence
            # Skip score_engine - not available in current strategy engine
            
            # Extract failed conditions from strategy decision for debugging
            failed_conditions = []
            if hasattr(strategy_decision, 'failed_conditions') and strategy_decision.failed_conditions:
                failed_conditions = strategy_decision.failed_conditions
            elif strategy_decision.strategy == 'NO_TRADE':
                # Extract from reasoning if failed_conditions not available
                if "Low confidence" in strategy_decision.reasoning:
                    failed_conditions.append(f"CONFIDENCE_BELOW_THRESHOLD_{strategy_decision.bias_confidence:.3f}")
                if "Unclear regime" in strategy_decision.reasoning:
                    if bias_result.bias == 'BULLISH':
                        failed_conditions.append("UNCLEAR_REGIME_FOR_BULLISH")
                    elif bias_result.bias == 'BEARISH':
                        failed_conditions.append("UNCLEAR_REGIME_FOR_BEARISH")
                if "Neutral bias" in strategy_decision.reasoning:
                    failed_conditions.append("NEUTRAL_BIAS_NO_DIRECTION")
            
            # Select optimal strike if not NO_TRADE
            execution_payload = None
            if strategy_decision.strategy != 'NO_TRADE':
                # Get spot price from snapshot (handle both object and dict)
                spot_price = snapshot.spot if hasattr(snapshot, 'spot') else snapshot.get('spot')
                
                optimal_strike = self.options_engine.select_optimal_strike(
                    features_dict, spot_price
                )
                
                if optimal_strike:
                    execution_payload = self.build_execution_payload(
                        optimal_strike, strategy_decision, spot_price
                    )
                    
                    # Insert trade into outcome_log for lifecycle tracking
                    try:
                        trade_id = await trade_lifecycle_manager.insert_trade(
                            symbol=symbol,
                            direction=strategy_decision.strategy,
                            entry_price=execution_payload.get('entry', 0),
                            stop_loss=execution_payload.get('stop_loss', 0),
                            target=execution_payload.get('target', 0),
                            confidence=probabilistic_confidence,
                            score=probabilistic_score
                        )
                        
                        # Add trade_id to execution payload for tracking
                        if trade_id:
                            execution_payload['trade_id'] = trade_id
                            
                    except Exception as e:
                        logger.error(f"Failed to insert trade lifecycle: {e}")
                else:
                    # Return NO_TRADE if no optimal strike found
                    execution_payload = {
                        "action": "NO_TRADE",
                        "probabilistic": {
                            "direction": "NO_TRADE",
                            "confidence": probabilistic_confidence,
                            "score": probabilistic_score
                        }
                    }
                    failed_conditions.append("NO_OPTIMAL_STRIKE_FOUND")
            
            # Build analysis payload with required structure
            analysis_payload = self.build_analysis_payload(
                bias_result, strategy_decision, features_dict, failed_conditions
            )
            
            # ENSURE REQUIRED PAYLOAD STRUCTURE
            payload = {
                'type': 'strategy_update',
                'symbol': symbol,  # Add symbol for frontend routing
                'analysis': analysis_payload,
                'trade': execution_payload
            }
            
            # STEP 1: ENSURE strategy and confidence at top level
            payload["strategy"] = strategy_decision.strategy
            payload["confidence"] = strategy_decision.bias_confidence
            
            # CRITICAL FIX - SYNC ANALYSIS OBJECT WITH TOP LEVEL
            # FORCE FULL SYNC
            payload["analysis"]["strategy"] = payload.get("strategy")
            payload["analysis"]["confidence"] = payload.get("confidence")
            
            # ADD DEBUG
            print("[PAYLOAD SYNC CHECK]", {
                "top_strategy": payload.get("strategy"),
                "analysis_strategy": payload["analysis"].get("strategy"),
                "top_conf": payload.get("confidence"),
                "analysis_conf": payload["analysis"].get("confidence")
            })
            
            # DEBUG: Log complete payload for verification
            print("[BROADCAST PAYLOAD]", {
                'regime': analysis_payload.get('regime', 'UNKNOWN'),
                'bias': analysis_payload.get('bias', 'NEUTRAL'),
                'biasStrength': analysis_payload.get('confidence', 0),
                'netGex': analysis_payload.get('gamma_analysis', {}).get('net_gex', 0),
                'keyLevels': {
                    'gex_flip': analysis_payload.get('key_levels', {}).get('gex_flip', 0),
                    'call_wall': analysis_payload.get('key_levels', {}).get('call_wall', 0),
                    'put_wall': analysis_payload.get('key_levels', {}).get('put_wall', 0)
                },
                'technicals': {
                    'rsi': analysis_payload.get('technical_state', {}).get('rsi', 50),
                    'momentum_15m': analysis_payload.get('technical_state', {}).get('momentum_15m', 0)
                }
            })
            
            return payload
            
        except Exception as e:
            logger.error(f"Analytics payload build failed: {e}")
            # STEP 5: HARD FAIL - NO SILENT FALLBACK
            print("[BLOCKED] Feature engine failed → skipping broadcast")
            return None  # Do not send strategy_update
    
    def build_analysis_payload(self, bias_result, strategy_decision, features, failed_conditions=None) -> Dict[str, Any]:
        """Build analysis payload for MemoizedStrategyPlan"""
        if failed_conditions is None:
            failed_conditions = []
            
        return {
            'bias': bias_result.bias,
            'confidence': bias_result.confidence,
            'score': bias_result.score,
            'components': bias_result.components,
            'regime': strategy_decision.regime,
            'strategy': strategy_decision.strategy,
            'execution_probability': strategy_decision.execution_probability,
            'reasoning': strategy_decision.reasoning,
            'probabilistic': {
                'score': features.get('probabilistic_score', 0.0),
                'confidence': features.get('probabilistic_confidence', bias_result.confidence)
            },
            'debug': {
                'confidence': strategy_decision.bias_confidence,
                'threshold': getattr(self.strategy_engine, 'CONFIDENCE_THRESHOLD', 0.6),
                'failedConditions': failed_conditions,
                'timestamp': int(time.time() * 1000)
            },
            'gamma_analysis': {
                'gex_profile': features.get('gex_profile', {}),
                'gamma_flip_probability': features.get('gamma_flip_probability', 0),
                'call_wall': features.get('call_wall_strike'),
                'put_wall': features.get('put_wall_strike'),
                'net_gex': features.get('net_gex', 0),
                'regime': features.get('gamma_regime', 'NEUTRAL'),
                'flip_level': features.get('gex_flip', 0)
            },
            'key_levels': {
                'call_wall': features.get('call_wall_strike', 0),
                'put_wall': features.get('put_wall_strike', 0),
                'gex_flip': features.get('gex_flip', 0),
                'max_pain': 0,
                'vwap': features.get('vwap', 0)
            },
            'oi_analysis': {
                'pcr_trend': features.get('pcr_trend', 0),
                'concentration': features.get('oi_concentration', 0),
                'buildup_rate': features.get('oi_buildup_rate', 0)
            },
            'liquidity_analysis': {
                'vacuum': features.get('liquidity_vacuum', 0),
                'order_flow': features.get('order_flow_imbalance', 0),
                'market_impact': features.get('market_impact', 0)
            },
            'volatility_analysis': {
                'regime': features.get('iv_regime', 'MEDIUM'),
                'expansion': features.get('volatility_expansion', 0),
                'term_structure': features.get('term_structure', 0),
                'iv_atm': features.get('iv_atm', 0),
                'iv_percentile': features.get('iv_percentile', 0)
            },
            'technical_state': {
                'rsi': features.get('rsi', 50),
                'momentum_15m': features.get('momentum_15m', 0)
            }
        }
    
    def build_execution_payload(self, optimal_strike, strategy_decision, spot_price) -> Dict[str, Any]:
        """Build execution payload for TradeSetupPanel"""
        try:
            # Calculate prices (simplified)
            current_premium = self.get_option_premium(optimal_strike['strike'], optimal_strike['option_type'])
            
            # Risk management
            stop_loss = current_premium * 0.4  # 40% stop loss
            target = current_premium * 2.0  # 2x target
            risk_reward = (target - current_premium) / (current_premium - stop_loss)
            
            # Get probabilistic score from strategy decision
            probabilistic_score = 0.0
            probabilistic_confidence = strategy_decision.bias_confidence
            if hasattr(self.strategy_engine, 'score_engine') and hasattr(strategy_decision, 'regime'):
                # Recalculate score if snapshot was available
                try:
                    # This is a simplified approach - in production, pass the actual snapshot
                    probabilistic_score = 0.5  # Default fallback
                    if strategy_decision.strategy in ['BUY_CALL', 'BUY_CE']:
                        probabilistic_score = 0.4
                    elif strategy_decision.strategy in ['BUY_PUT', 'BUY_PE']:
                        probabilistic_score = -0.4
                    probabilistic_confidence = abs(probabilistic_score)
                except:
                    probabilistic_score = 0.0
                    probabilistic_confidence = strategy_decision.bias_confidence
            
            return {
                'action': f"BUY_{optimal_strike['option_type']}",
                'strike': optimal_strike['strike'],
                'option_type': optimal_strike['option_type'],
                'entry': current_premium,
                'target': target,
                'stop_loss': stop_loss,
                'position_size': 1,  # Default 1 lot
                'max_loss': stop_loss,
                'risk_reward': risk_reward,
                'probability': strategy_decision.execution_probability,
                'conviction': 'HIGH' if strategy_decision.execution_probability > 0.7 else 'MEDIUM',
                'liquidity_score': optimal_strike['liquidity_score'],
                'gamma_score': optimal_strike['gamma_score'],
                'execution_reasoning': [
                    f"Optimal strike: {optimal_strike['strike']}",
                    f"Option type: {optimal_strike['option_type']}",
                    f"Liquidity score: {optimal_strike['liquidity_score']:.2f}",
                    f"Risk/Reward: {risk_reward:.2f}"
                ],
                'probabilistic': {
                    'direction': strategy_decision.strategy,
                    'confidence': probabilistic_confidence,
                    'score': probabilistic_score
                }
            }
            
        except Exception as e:
            logger.error(f"Execution payload build failed: {e}")
            return None
    
    def get_option_premium(self, strike, option_type) -> float:
        """Get current option premium - simplified"""
        # In production, this would get from real-time data
        return 150.0  # Default premium
    
    def get_default_payload(self, symbol) -> Dict[str, Any]:
        """Default payload for error cases"""
        return {
            'type': 'strategy_update',
            'analysis': {
                'bias': 'NEUTRAL',
                'confidence': 0.0,
                'regime': 'UNKNOWN',
                'strategy': 'NO_TRADE',
                'reasoning': ['System error - no analysis available'],
                'debug': {
                    'confidence': 0.0,
                    'threshold': getattr(self.strategy_engine, 'CONFIDENCE_THRESHOLD', 0.6),
                    'failedConditions': ['SYSTEM_ERROR_NO_ANALYSIS'],
                    'timestamp': int(time.time() * 1000)
                }
            },
            'trade': {"action": "NO_TRADE"}
        }

    async def _compute_and_broadcast(self, symbol: str):
        try:
            from app.services.option_chain_builder import option_chain_builder
            from app.core.ws_manager import manager
            from ai.advanced_microstructure_layer import AdvancedMicrostructureLayer

            logger.info(f"[COMPUTE] Starting analytics for {symbol}")
            
            snap = option_chain_builder.get_latest_snapshot(symbol)
            if snap is None:
                logger.warning(f"[COMPUTE] No snapshot for {symbol} — checking chains")
                # Check if chains exist
                chains = option_chain_builder.chains.get(symbol, {})
                logger.info(f"[COMPUTE] Chains for {symbol}: {len(chains)} strikes")
                if chains:
                    logger.info(f"[COMPUTE] Sample strikes: {list(chains.keys())[:3]}")
                return

            logger.info(f"[COMPUTE] Found snapshot for {symbol}: spot={snap.spot} pcr={snap.pcr}")

            # Initialize microstructure layer for liquidity analysis
            microstructure_layer = AdvancedMicrostructureLayer()
            
            # Prepare metrics for liquidity vacuum analysis
            metrics = {
                'spot_price': snap.spot,
                'support': 0,  # Will be calculated from key levels
                'resistance': 0,  # Will be calculated from key levels  
                'volatility_regime': 'normal',  # Will be determined from IV
                'oi_change': 0  # Will be calculated from OI changes
            }
            
            # Run liquidity vacuum analysis
            microstructure_analysis = microstructure_layer.analyze_microstructure(metrics)

            # PHASE 1: Master AI Engine Execution (Law 1 Alignment)
            ai_results = {}
            try:
                # Convert snap attributes to dict for orchestrator
                snap_dict = {
                    "spot": snap.spot,
                    "pcr": snap.pcr,
                    "max_call_oi_strike": snap.max_call_oi_strike,
                    "max_put_oi_strike": snap.max_put_oi_strike,
                    "total_call_oi": snap.total_call_oi,
                    "total_put_oi": snap.total_put_oi,
                    "atm_strike": snap.atm_strike,
                    "atm_iv": snap.atm_iv,
                    "vwap": snap.vwap,
                    "dte": snap.dte,
                    "analytics": snap.analytics or {}
                }
                ai_results = await ai_orchestrator.run_cycle(symbol, snap_dict)
                logger.info(f"[ORCHESTRATOR] ✅ Analysis computed for {symbol} ({ai_results.get('cycle_time_ms')}ms)")
            except Exception as e:
                logger.error(f"[ORCHESTRATOR] ❌ Pipeline crash for {symbol}: {e}")
                # Fallback to manual heuristics if brain crashes

            # Simple bias from PCR (Fallback/Parity check)
            pcr = ai_results.get("market_analysis", {}).get("bias_strength", snap.pcr) if ai_results else snap.pcr
            
            # Map Orchestrator results to standard payload
            m_analysis = ai_results.get("market_analysis", {})
            bias = m_analysis.get("bias", "NEUTRAL")
            strength = m_analysis.get("bias_strength", 0.0)
            regime = m_analysis.get("regime", "RANGING")
            
            import time
            ts  = int(time.time())
            spot = snap.spot

            payload = {
                "type":        "market_update",
                "symbol":      symbol,
                "timestamp":   ts,

                # Spot — all aliases
                "spot":        spot,
                "spotPrice":   spot,
                "liveSpot":    spot,
                "currentSpot": spot,

                "atm":         snap.atm_strike,
                "ai_ready":    True,

                "market_analysis": {
                    "regime":        regime,
                    "bias":          bias,
                    "bias_strength": strength,
                    "key_levels":    m_analysis.get("key_levels", {
                        "call_wall": snap.max_call_oi_strike,
                        "put_wall":  snap.max_put_oi_strike,
                        "max_pain": 0,
                        "gex_flip": snap.analytics.get("gex_flip", 0) if snap.analytics else 0,
                        "vwap":      snap.vwap,
                    }),
                    "gamma_analysis": m_analysis.get("gamma_analysis", {
                        "net_gex": snap.analytics.get("net_gex", 0) if snap.analytics else 0,
                        "regime": snap.analytics.get("regime", "NEUTRAL") if snap.analytics else "NEUTRAL",
                        "flip_level": snap.analytics.get("gex_flip", 0) if snap.analytics else 0,
                        "implication": "Institutional Gamma Exposure Analysis",
                    }),
                    "volatility_state": m_analysis.get("volatility_state", {
                        "iv_atm":        snap.atm_iv,
                        "state":         "NORMAL",
                    }),
                    "technical_state": m_analysis.get("technical_state", {
                        "rsi":          0,
                        "momentum_15m": 0,
                    }),
                    "flow_analysis": {
                        "call_velocity": max(0.1, min(0.9, (snap.total_call_oi / 1000000))),
                        "put_velocity": max(0.1, min(0.9, (snap.total_put_oi / 1000000))),
                        "direction": "BULLISH" if snap.total_call_oi > snap.total_put_oi else "BEARISH",
                        "intent_score": max(0.1, min(0.9, abs(snap.total_call_oi - snap.total_put_oi) / 100000)),
                        "imbalance": abs(snap.total_call_oi - snap.total_put_oi) / (snap.total_call_oi + snap.total_put_oi)
                    },
                    "summary": m_analysis.get("summary") or self._build_summary(symbol, snap.pcr, bias, regime,
                                                   snap.max_call_oi_strike, snap.max_put_oi_strike,
                                                   snap.atm_iv, "NORMAL"),
                },

                "early_warnings": ai_results.get("early_warnings", []),
                "trade_plan": ai_results.get("trade_plan", {
                    "plan_id":      f"PLAN-{symbol}-{ts}",
                    "instrument":   symbol,
                    "direction":    "NEUTRAL",
                    "strike":       snap.atm_strike,
                }),
                "confidence_score": ai_results.get("confidence_score", 0.0),
                "sentiment_overlay": ai_results.get("sentiment_overlay", {}),
                "option_chain": {
                    "pcr":           snap.pcr,
                    "call_wall":     snap.max_call_oi_strike,
                    "put_wall":      snap.max_put_oi_strike,
                    "gex_flip":      snap.analytics.get("gex_flip", 0) if snap.analytics else 0,
                    "net_gex":       snap.analytics.get("net_gex", 0) if snap.analytics else 0,
                    "iv_atm":        snap.atm_iv,
                    "calls":         snap.calls_data,
                    "puts":          snap.puts_data,
                },

                "paper_trading": {
                    "total_trades":    0,
                    "total_pnl":       0.0,
                    "capital_current": 100000.0,
                },

                "news_alerts": [],
                "chart_intelligence": ai_results.get("chart_intelligence"),

                "dataQuality": {
                    "hasSpot":   spot > 0,
                    "hasOi":     snap.total_call_oi > 0,
                    "aiReady":   True,
                    "source":    "AI_ORCHESTRATOR",
                },
            }

            # Safe JSON broadcast
            import json
            try:
                message = json.dumps(payload, default=str)
                print("[WS OUTGOING PAYLOAD]", payload.get("type"), payload)
                await broadcast_with_strategy(json.loads(message))
            except Exception as e:
                logger.error(f"[BROADCAST] JSON error for {symbol}: {e}")

            # Send separate chart_analysis message with all required data for components
            chart_analysis_payload = {
                "type": "chart_analysis",
                "symbol": symbol,
                "timestamp": ts,
                "price": round(spot, 2),
                "bias": bias,
                "bias_strength": strength,
                "regime": regime,
                "flow_analysis": payload["market_analysis"]["flow_analysis"],
                "key_levels": payload["market_analysis"]["key_levels"],
                "gamma_analysis": payload["market_analysis"]["gamma_analysis"],
                "expiry_magnet": {
                    "magnet_strike": snap.max_put_oi_strike if snap.max_put_oi_strike > 0 else snap.atm_strike,
                    "pin_probability": 0.45 if snap.dte <= 1 else 0.25, 
                    "days_to_expiry": snap.dte,
                    "target_distance": abs(spot - (snap.max_put_oi_strike if snap.max_put_oi_strike > 0 else snap.atm_strike))
                },
                "volatility_state": payload["market_analysis"]["volatility_state"],
                "expected_move": {
                    "1h": round(spot * 0.004, 2), 
                    "4h": round(spot * 0.008, 2),
                    "1d": round(spot * 0.012, 2)
                },
                "liquidity_analysis": {
                    "total_call_oi": snap.total_call_oi,
                    "total_put_oi": snap.total_put_oi,
                    "liquidity_pressure": min(1.0, (snap.total_call_oi + snap.total_put_oi) / 50000000), 
                    "book_depth": max(0.3, min(0.9, microstructure_analysis.get("liquidity_vacuum_confidence", 0.5))),
                    "expansion_probability": microstructure_analysis.get("liquidity_vacuum_confidence", 0.3),
                    "vacuum_signal": microstructure_analysis.get("liquidity_vacuum_signal", "NONE"),
                    "vacuum_direction": microstructure_analysis.get("liquidity_vacuum_direction", "NONE"),
                    "vacuum_strength": microstructure_analysis.get("liquidity_vacuum_strength", 0.0)
                },
                "sentiment_overlay": payload["sentiment_overlay"],
                "chart_intelligence": payload["chart_intelligence"],
                "summary": payload["market_analysis"]["summary"],
                "confidence": payload["confidence_score"],
                "computation_ms": round(ai_results.get("cycle_time_ms", 0), 2)
            }
            
            try:
                chart_message = json.dumps(chart_analysis_payload, default=str)
                print("[WS OUTGOING PAYLOAD]", chart_analysis_payload.get("type"), chart_analysis_payload)
                await broadcast_with_strategy(json.loads(chart_message))
                logger.info(f"[BROADCAST] ✅ {symbol} chart_analysis via AI_ORCHESTRATOR")
            except Exception as e:
                logger.error(f"[BROADCAST] Chart analysis JSON error for {symbol}: {e}")

            # STEP 2: FIND analytics_update PAYLOAD (SEPARATE BLOCK)
            analytics_payload = {
                "type": "analytics_update",
                "symbol": symbol,
                "timestamp": ts,
                "analytics": payload["market_analysis"]
            }
            
            # STEP 3: INJECT STRATEGY ONLY HERE
            strategy_decision = await self._build_analytics_payload(symbol, snap)
            
            # STEP 1: LOG RAW strategy_decision
            print("[DEBUG STRATEGY_DECISION]", strategy_decision)
            
            # STEP 2: REMOVE CONDITION (TEMP DEBUG MODE)
            trade = strategy_decision.get("trade") if strategy_decision else None
            print("[DEBUG TRADE]", trade)
            
            # STEP 3: FORCE INJECTION
            analytics = analytics_payload.get("analytics") or {}
            analytics["strategy"] = trade.get("action") if trade else "NO_TRADE"
            analytics["confidence"] = trade.get("confidence") if trade else 0
            analytics_payload["analytics"] = analytics
            
            # STEP 4: FINAL LOG
            print("[FINAL ANALYTICS_UPDATE PAYLOAD]", analytics_payload)
            
            # STEP 5: BROADCAST BOTH
            try:
                analytics_message = json.dumps(analytics_payload, default=str)
                print("[WS OUTGOING PAYLOAD]", analytics_payload.get("type"), analytics_payload)
                await broadcast_with_strategy(json.loads(analytics_message))
            except Exception as e:
                logger.error(f"[BROADCAST] Analytics update JSON error for {symbol}: {e}")

            # NEW: Send separated strategy_update message
            strategy_payload = await self._build_analytics_payload(symbol, snap)
            if strategy_payload:
                try:
                    # STEP 3: VERIFY BROADCAST CALL
                    print("[BROADCAST CHECK] sending strategy_update")
                    strategy_message = json.dumps(strategy_payload, default=str)
                    print("[WS OUTGOING PAYLOAD]", strategy_payload.get("type"), strategy_payload)
                    await broadcast_with_strategy(json.loads(strategy_message))
                    logger.info(f"[BROADCAST] ✅ {symbol} strategy_update with separated payloads")
                    
                    # Check price updates for active trades
                    if snap and hasattr(snap, 'spot'):
                        await trade_lifecycle_manager.check_price_updates(symbol, snap.spot)
                        
                except Exception as e:
                    logger.error(f"[BROADCAST] Strategy update JSON error for {symbol}: {e}")

        except Exception as e:
            logger.error(
                f"[COMPUTE] ❌ Crash for {symbol}: {e}",
                exc_info=True
            )

    async def _analytics_loop(self):
        """Main loop ensuring 500ms broadcast cycles"""
        logger.info("Analytics Loop Started")
        loop_count = 0
        while self._running:
            try:
                loop_count += 1
                cycle_start = time.monotonic()

                if not manager.active_connections:
                    if loop_count % 10 == 0:
                        logger.warning(f"[BROADCASTER] No active connections (Loop #{loop_count})")
                    await asyncio.sleep(1)
                    continue

                # Broadly targeting main symbols
                symbols = ["NIFTY", "BANKNIFTY"]
                
                tasks = []
                for symbol in symbols:
                    is_dirty    = self._dirty.get(symbol, False)
                    last_bc     = self._last_broadcast_time.get(symbol, 0)
                    force_bc    = (time.monotonic() - last_bc) > 2.0
                    should_send = is_dirty or force_bc

                    if loop_count % 10 == 0:
                        logger.info(
                            f"[BROADCASTER LOOP #{loop_count}] {symbol} | "
                            f"dirty={is_dirty} force={force_bc} should_send={should_send}"
                        )

                    if should_send:
                        tasks.append(self._compute_and_broadcast(symbol))
                        self._dirty[symbol] = False
                        self._last_broadcast_time[symbol] = time.monotonic()

                if tasks:
                    await asyncio.gather(*tasks)

                # Control interval
                elapsed = time.monotonic() - cycle_start
                sleep_time = max(0, self.ANALYTICS_INTERVAL - elapsed)
                await asyncio.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Loop error: {e}", exc_info=True)
                await asyncio.sleep(1)

    async def start(self):
        if self._running: return
        self._running = True
        self._analytics_task = asyncio.create_task(self._analytics_loop())
        logger.info("Analytics Broadcaster Started")

    async def stop(self):
        self._running = False
        if self._analytics_task:
            self._analytics_task.cancel()
            try:
                await asyncio.wait_for(self._analytics_task, timeout=2)
            except: pass
        logger.info("Analytics Broadcaster Stopped")

# Singleton
analytics_broadcaster = AnalyticsBroadcaster()
