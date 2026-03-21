import logging

logger = logging.getLogger(__name__)

class AnalyticsEngine:

    def analyze(self, snapshot):
        """
        Analyze option chain snapshot for key metrics
        """
        try:
            calls = snapshot.get("calls", {})
            puts = snapshot.get("puts", {})

            # Calculate Put/Call Ratio (PCR)
            call_oi = sum(c.get("oi", 0) for c in calls.values())
            put_oi = sum(p.get("oi", 0) for p in puts.values())

            pcr = put_oi / call_oi if call_oi else 0

            # Calculate Institutional Gamma Exposure (GEX)
            # Standard GEX = Gamma * OI * Contract Multiplier (75 for NIFTY, 15 for BANKNIFTY)
            symbol = snapshot.get("symbol", "NIFTY")
            multiplier = 75 if "NIFTY" in symbol and "BANK" not in symbol else 15 if "BANKNIFTY" in symbol else 1
            
            call_gex = sum(c.get("gamma", 0) * c.get("oi", 0) * multiplier for c in calls.values())
            put_gex = sum(p.get("gamma", 0) * p.get("oi", 0) * multiplier for p in puts.values())
            
            # Dealer Perspective:
            # Manufacturers are SHORT calls (negative gamma) and SHORT puts (positive gamma)
            # We follow the convention: Net GEX = Call GEX - Put GEX
            net_gex = call_gex - put_gex
            
            # Determine Gamma Regime
            gamma_regime = "POSITIVE_GAMMA" if net_gex > 0 else "SHORT_GAMMA"
            
            # Find Flip Level (Strike where GEX crosses zero)
            # This is a linear interpolation between the two strikes where GEX changes sign
            all_strikes = sorted([float(s) for s in set(calls.keys()) | set(puts.keys())])
            gex_flip = 0
            
            if len(all_strikes) > 1:
                for i in range(len(all_strikes) - 1):
                    s1 = str(int(all_strikes[i]))
                    s2 = str(int(all_strikes[i+1]))
                    
                    g1 = (calls.get(s1, {}).get("gamma", 0) * calls.get(s1, {}).get("oi", 0)) - \
                         (puts.get(s1, {}).get("gamma", 0) * puts.get(s1, {}).get("oi", 0))
                    
                    g2 = (calls.get(s2, {}).get("gamma", 0) * calls.get(s2, {}).get("oi", 0)) - \
                         (puts.get(s2, {}).get("gamma", 0) * puts.get(s2, {}).get("oi", 0))
                    
                    if (g1 > 0 and g2 < 0) or (g1 < 0 and g2 > 0):
                        # Simple linear interpolation for flip level
                        # flip = s1 + (s2-s1) * |g1| / (|g1| + |g2|)
                        try:
                            gex_flip = all_strikes[i] + (all_strikes[i+1] - all_strikes[i]) * abs(g1) / (abs(g1) + abs(g2))
                        except ZeroDivisionError:
                            gex_flip = all_strikes[i]
                        break
            
            if not gex_flip:
                gex_flip = snapshot.spot if hasattr(snapshot, 'spot') else 0

            # Determine Market Bias
            bias = "NEUTRAL"
            if pcr < 0.9:
                bias = "BULLISH"
            elif pcr > 1.1:
                bias = "BEARISH"

            result = {
                "pcr": round(pcr, 2),
                "net_gex": round(net_gex, 2),
                "gex_flip": round(gex_flip, 2),
                "regime": gamma_regime,
                "gamma_exposure": round(abs(net_gex), 2), # Legacy support
                "liquidity_pressure": call_oi + put_oi,
                "market_bias": bias
            }

            logger.debug(f"Analytics computed for {symbol}: {result}")
            return result

        except Exception as e:
            logger.error(f"Analytics engine error: {e}")
            return {
                "pcr": 0,
                "gamma_exposure": 0,
                "liquidity_pressure": 0,
                "market_bias": "NEUTRAL"
            }

analytics_engine = AnalyticsEngine()
