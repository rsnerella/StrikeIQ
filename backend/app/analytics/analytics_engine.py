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

            # Calculate Gamma Exposure
            gamma = sum(abs(c.get("gamma", 0)) for c in calls.values())
            gamma += sum(abs(p.get("gamma", 0)) for p in puts.values())

            # Calculate Liquidity Pressure
            liquidity = call_oi + put_oi

            # Determine Market Bias
            bias = "NEUTRAL"
            if pcr < 0.9:
                bias = "BULLISH"
            elif pcr > 1.1:
                bias = "BEARISH"

            result = {
                "pcr": round(pcr, 2),
                "gamma_exposure": round(gamma, 2),
                "liquidity_pressure": liquidity,
                "market_bias": bias
            }

            logger.debug(f"Analytics computed: {result}")
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
