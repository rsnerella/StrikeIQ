"""
Institutional Feature Engineering for StrikeIQ
Computes advanced market microstructure features
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import logging
import time

logger = logging.getLogger(__name__)

@dataclass
class FeatureSnapshot:
    """Complete feature snapshot for AI processing"""
    timestamp: float
    spot: float
    
    # Gamma Features
    gex_profile: Dict[str, float]
    gamma_flip_probability: float
    call_wall_strength: float
    put_wall_strength: float
    call_wall_strike: Optional[float]
    put_wall_strike: Optional[float]
    
    # OI Features
    pcr_trend: float
    oi_concentration: float
    oi_buildup_rate: float
    call_oi_distribution: Dict[str, float]
    put_oi_distribution: Dict[str, float]
    
    # Liquidity Features
    liquidity_vacuum: float
    order_flow_imbalance: float
    market_impact: float
    spread_widening: float
    
    # Volatility Features
    iv_regime: str  # LOW, MEDIUM, HIGH
    volatility_expansion: float
    term_structure: float
    implied_volatility_surface: Dict[str, float]
    
    # Microstructure Features
    dealer_hedging_pressure: float
    institutional_flow: float
    support_resistance_levels: Dict[str, List[float]]
    pin_probability: float

class OptionChainSnapshot:
    """Wrapper class to ensure proper snapshot structure for feature engine"""
    def __init__(self, chains, spot):
        self.strikes = chains
        self.spot = spot


class FeatureEngine:
    """Institutional-grade feature engineering"""
    
    def __init__(self):
        self.gamma_calculator = GammaCalculator()
        self.oi_analyzer = OIAnalyzer()
        self.liquidity_detector = LiquidityDetector()
        self.volatility_analyzer = VolatilityAnalyzer()
        self.microstructure_analyzer = MicrostructureAnalyzer()
        
    def compute_features(self, option_chain_snapshot, spot_price) -> FeatureSnapshot:
        """Compute complete feature set with safety validation"""
        start_time = time.time()
        
        try:
            # CRITICAL: Validate snapshot structure with proper error handling
            if not self._validate_snapshot(option_chain_snapshot):
                raise Exception("Invalid option chain snapshot structure - validation failed")
            
            # Compute features with timeout protection
            if time.time() - start_time > 0.2:  # 200ms timeout
                logger.warning("Feature computation timeout - using default features")
                return self.get_default_features(spot_price)
            
            # Gamma Features
            gamma_features = self.gamma_calculator.compute_gamma_features(option_chain_snapshot, spot_price)
            
            # Check timeout after each major computation
            if time.time() - start_time > 0.2:
                logger.warning("Feature computation timeout during gamma analysis")
                return self.get_default_features(spot_price)
            
            # OI Features
            oi_features = self.oi_analyzer.compute_oi_features(option_chain_snapshot)
            
            if time.time() - start_time > 0.2:
                logger.warning("Feature computation timeout during OI analysis")
                return self.get_default_features(spot_price)
            
            # Liquidity Features
            liquidity_features = self.liquidity_detector.detect_liquidity_features(option_chain_snapshot)
            
            if time.time() - start_time > 0.2:
                logger.warning("Feature computation timeout during liquidity analysis")
                return self.get_default_features(spot_price)
            
            # Volatility Features
            volatility_features = self.volatility_analyzer.analyze_volatility(option_chain_snapshot)
            
            if time.time() - start_time > 0.2:
                logger.warning("Feature computation timeout during volatility analysis")
                return self.get_default_features(spot_price)
            
            # Microstructure Features
            microstructure_features = self.microstructure_analyzer.analyze_microstructure(option_chain_snapshot)
            
            # Create feature snapshot
            features = FeatureSnapshot(
                timestamp=getattr(option_chain_snapshot, 'timestamp', time.time()),
                spot=spot_price,
                **gamma_features,
                **oi_features,
                **liquidity_features,
                **volatility_features,
                **microstructure_features
            )
            
            # DEBUG: Log computed features
            print("[FEATURE DEBUG]", {
                'timestamp': features.timestamp,
                'spot': features.spot,
                'oi_total': sum(features.call_oi_distribution.values()) + sum(features.put_oi_distribution.values()),
                'oi_skew': features.pcr_trend,
                'gex': features.gex_profile.get('net_gamma', 0),
                'iv': features.implied_volatility_surface.get('avg_iv', 0),
                'delta': features.dealer_hedging_pressure
            })
            
            return features
            
        except Exception as e:
            logger.error(f"Feature computation failed: {e}")
            # CRITICAL: Only use defaults if actual computation fails, not for validation errors
            if "Invalid snapshot structure" in str(e):
                # Re-raise validation errors to be handled upstream
                raise e
            return self.get_default_features(spot_price)
    
    def _validate_snapshot(self, option_chain_snapshot) -> bool:
        """Validate option chain snapshot structure"""
        try:
            # CRITICAL: Raise exception for invalid structure instead of returning False
            if not option_chain_snapshot:
                raise Exception("Invalid snapshot structure - snapshot is None")
            
            # Check if snapshot has strikes attribute
            if not hasattr(option_chain_snapshot, 'strikes'):
                raise Exception("Invalid snapshot structure - missing strikes attribute")
            
            # Get strikes - handle both dict and list formats
            strikes = getattr(option_chain_snapshot, 'strikes', None)
            if strikes is None:
                raise Exception("Invalid snapshot structure - strikes is None")
            
            # Handle dict format (expected) vs list format
            if isinstance(strikes, dict):
                if len(strikes) == 0:
                    raise Exception("Invalid snapshot structure - empty strikes dict")
                
                # Check if at least some strikes have valid structure
                valid_strikes = 0
                sample_strikes = list(strikes.items())[:3]  # Check first 3 strikes
                print("[DEBUG SNAPSHOT]", sample_strikes)
                
                for strike_key, strike_data in sample_strikes:
                    if isinstance(strike_data, dict):
                        # Ensure strike key is float
                        try:
                            float_strike = float(strike_key)
                        except (ValueError, TypeError):
                            raise Exception(f"Invalid strike key format: {strike_key}")
                        
                        # Check for both CE and PE
                        has_ce = 'CE' in strike_data and isinstance(strike_data['CE'], dict)
                        has_pe = 'PE' in strike_data and isinstance(strike_data['PE'], dict)
                        
                        if has_ce or has_pe:
                            valid_strikes += 1
                
                if valid_strikes == 0:
                    raise Exception("Invalid snapshot structure - no valid CE/PE data found")
                
                return True
                
            elif isinstance(strikes, list):
                if len(strikes) == 0:
                    raise Exception("Invalid snapshot structure - empty strikes list")
                
                # Check first few strikes
                valid_strikes = 0
                for strike_data in strikes[:3]:
                    if isinstance(strike_data, dict) and 'strike' in strike_data:
                        try:
                            float(strike_data['strike'])
                        except (ValueError, TypeError):
                            continue
                        
                        has_ce = 'CE' in strike_data and isinstance(strike_data['CE'], dict)
                        has_pe = 'PE' in strike_data and isinstance(strike_data['PE'], dict)
                        
                        if has_ce or has_pe:
                            valid_strikes += 1
                
                if valid_strikes == 0:
                    raise Exception("Invalid snapshot structure - no valid strike data in list")
                
                return True
            else:
                raise Exception(f"Invalid snapshot structure - strikes is {type(strikes)}, expected dict or list")
            
        except Exception as e:
            logger.error(f"Snapshot validation failed: {e}")
            # Re-raise to trigger proper error handling in compute_features
            raise e
    
    def get_default_features(self, spot_price) -> FeatureSnapshot:
        """Default features for error cases"""
        raise Exception("Feature engine must not fallback - fix snapshot structure instead")

class GammaCalculator:
    """Advanced gamma exposure calculations"""
    
    def compute_gamma_features(self, option_chain, spot):
        try:
            # Calculate gamma profile
            total_gamma = 0
            call_gamma = 0
            put_gamma = 0
            
            call_wall_strength = 0
            put_wall_strength = 0
            call_wall_strike = None
            put_wall_strike = None
            
            for strike_data in option_chain.strikes:
                if not isinstance(strike_data, dict):
                    continue
                    
                strike = strike_data.get('strike')
                if not strike:
                    continue
                
                # Call gamma
                if 'CE' in strike_data and isinstance(strike_data['CE'], dict):
                    ce_data = strike_data['CE']
                    ce_gamma = ce_data.get('gamma', 0)
                    call_gamma += ce_gamma
                    total_gamma += ce_gamma
                    
                    # Track call wall
                    ce_oi = ce_data.get('oi', 0)
                    if ce_oi > call_wall_strength:
                        call_wall_strength = ce_oi
                        call_wall_strike = strike
                
                # Put gamma
                if 'PE' in strike_data and isinstance(strike_data['PE'], dict):
                    pe_data = strike_data['PE']
                    pe_gamma = pe_data.get('gamma', 0)
                    put_gamma += pe_gamma
                    total_gamma += pe_gamma
                    
                    # Track put wall
                    pe_oi = pe_data.get('oi', 0)
                    if pe_oi > put_wall_strength:
                        put_wall_strength = pe_oi
                        put_wall_strike = strike
            
            # Calculate gamma flip probability
            net_gamma = call_gamma - put_gamma
            gamma_flip_probability = self.calculate_gamma_flip_probability(net_gamma, spot)
            
            return {
                'gex_profile': {
                    'total_gamma': total_gamma,
                    'call_gamma': call_gamma,
                    'put_gamma': put_gamma,
                    'net_gamma': net_gamma
                },
                'gamma_flip_probability': gamma_flip_probability,
                'call_wall_strength': min(1.0, call_wall_strength / 10000000),
                'put_wall_strength': min(1.0, put_wall_strength / 10000000),
                'call_wall_strike': call_wall_strike,
                'put_wall_strike': put_wall_strike
            }
            
        except Exception as e:
            logger.error(f"Gamma calculation failed: {e}")
            print("[BLOCKED] Feature engine failed → skipping broadcast")
            return None
    
    def calculate_gamma_flip_probability(self, net_gamma, spot):
        """Calculate probability of gamma flip"""
        # Simplified calculation - can be enhanced
        if abs(net_gamma) < spot * 0.01:
            return 0.5
        elif net_gamma > 0:
            return min(0.9, 0.5 + (net_gamma / (spot * 100)))
        else:
            return max(0.1, 0.5 + (net_gamma / (spot * 100)))
    
    def get_default_gamma_features(self):
        return {
            'gex_profile': {'total_gamma': 0, 'call_gamma': 0, 'put_gamma': 0, 'net_gamma': 0},
            'gamma_flip_probability': 0.0,
            'call_wall_strength': 0.0,
            'put_wall_strength': 0.0,
            'call_wall_strike': None,
            'put_wall_strike': None
        }

class OIAnalyzer:
    """Open interest analysis"""
    
    def compute_oi_features(self, option_chain):
        try:
            total_call_oi = 0
            total_put_oi = 0
            call_oi_distribution = {}
            put_oi_distribution = {}
            
            # Get strikes from option chain - handle both dict and list formats
            strikes = getattr(option_chain, 'strikes', None)
            if not strikes:
                raise Exception("No strikes data available for OI analysis")
            
            # Handle dict format
            if isinstance(strikes, dict):
                for strike_key, strike_data in strikes.items():
                    if not isinstance(strike_data, dict):
                        continue
                    
                    # Call OI
                    if 'CE' in strike_data and isinstance(strike_data['CE'], dict):
                        ce_oi = strike_data['CE'].get('oi', 0)
                        if ce_oi > 0:  # Only include non-zero OI
                            total_call_oi += ce_oi
                            call_oi_distribution[str(float(strike_key))] = ce_oi
                    
                    # Put OI
                    if 'PE' in strike_data and isinstance(strike_data['PE'], dict):
                        pe_oi = strike_data['PE'].get('oi', 0)
                        if pe_oi > 0:  # Only include non-zero OI
                            total_put_oi += pe_oi
                            put_oi_distribution[str(float(strike_key))] = pe_oi
            
            # Handle list format
            elif isinstance(strikes, list):
                for strike_data in strikes:
                    if not isinstance(strike_data, dict):
                        continue
                        
                    strike = strike_data.get('strike')
                    if not strike:
                        continue
                    
                    # Call OI
                    if 'CE' in strike_data and isinstance(strike_data['CE'], dict):
                        ce_oi = strike_data['CE'].get('oi', 0)
                        if ce_oi > 0:  # Only include non-zero OI
                            total_call_oi += ce_oi
                            call_oi_distribution[str(float(strike))] = ce_oi
                    
                    # Put OI
                    if 'PE' in strike_data and isinstance(strike_data['PE'], dict):
                        pe_oi = strike_data['PE'].get('oi', 0)
                        if pe_oi > 0:  # Only include non-zero OI
                            total_put_oi += pe_oi
                            put_oi_distribution[str(float(strike))] = pe_oi
            
            # VALIDATION: Ensure we have real OI data
            if total_call_oi == 0 and total_put_oi == 0:
                raise Exception("No valid OI data found - all OI values are zero")
            
            # Calculate PCR and features
            pcr = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0
            pcr_trend = self.calculate_pcr_trend(pcr)
            oi_concentration = self.calculate_oi_concentration(call_oi_distribution, put_oi_distribution)
            oi_buildup_rate = self.calculate_oi_buildup_rate(option_chain)
            
            # DEBUG: Log OI metrics
            print("[OI DEBUG]", {
                'total_call_oi': total_call_oi,
                'total_put_oi': total_put_oi,
                'pcr': pcr,
                'pcr_trend': pcr_trend,
                'oi_concentration': oi_concentration,
                'call_strikes': len(call_oi_distribution),
                'put_strikes': len(put_oi_distribution)
            })
            
            return {
                'pcr_trend': pcr_trend,
                'oi_concentration': oi_concentration,
                'oi_buildup_rate': oi_buildup_rate,
                'call_oi_distribution': call_oi_distribution,
                'put_oi_distribution': put_oi_distribution
            }
            
        except Exception as e:
            logger.error(f"OI analysis failed: {e}")
            # CRITICAL: Re-raise if no real data, otherwise return defaults
            if "No valid OI data found" in str(e):
                raise e
            return self.get_default_oi_features()
    
    def calculate_pcr_trend(self, current_pcr):
        """Calculate PCR trend - simplified"""
        # In production, this would use historical PCR data
        if current_pcr > 1.2:
            return 0.3  # Bullish trend
        elif current_pcr < 0.8:
            return -0.3  # Bearish trend
        else:
            return 0.0  # Neutral
    
    def calculate_oi_concentration(self, call_dist, put_dist):
        """Calculate OI concentration risk"""
        # Calculate Herfindahl index for concentration
        total_oi = sum(call_dist.values()) + sum(put_dist.values())
        if total_oi == 0:
            return 0.0
        
        all_oi = list(call_dist.values()) + list(put_dist.values())
        concentration = sum((oi / total_oi) ** 2 for oi in all_oi)
        
        return min(1.0, concentration)
    
    def calculate_oi_buildup_rate(self, option_chain):
        """Calculate OI buildup rate - simplified"""
        # In production, this would compare with previous snapshots
        return 0.0
    
    def get_default_oi_features(self):
        return {
            'pcr_trend': 0.0,
            'oi_concentration': 0.0,
            'oi_buildup_rate': 0.0,
            'call_oi_distribution': {},
            'put_oi_distribution': {}
        }

class LiquidityDetector:
    """Liquidity vacuum and flow detection"""
    
    def detect_liquidity_features(self, option_chain):
        try:
            total_volume = 0
            total_oi = 0
            spread_sum = 0
            spread_count = 0
            
            for strike_data in option_chain.strikes:
                if not isinstance(strike_data, dict):
                    continue
                    
                for option_type in ['CE', 'PE']:
                    if option_type in strike_data and isinstance(strike_data[option_type], dict):
                        option_data = strike_data[option_type]
                        total_volume += option_data.get('volume', 0)
                        total_oi += option_data.get('oi', 0)
                        
                        bid = option_data.get('bid', 0)
                        ask = option_data.get('ask', 0)
                        if bid > 0 and ask > 0:
                            spread = (ask - bid) / ask
                            spread_sum += spread
                            spread_count += 1
            
            # Calculate liquidity metrics
            avg_spread = spread_sum / spread_count if spread_count > 0 else 0.1
            liquidity_vacuum = self.calculate_liquidity_vacuum(total_volume, total_oi)
            order_flow_imbalance = self.calculate_order_flow_imbalance(option_chain)
            market_impact = self.calculate_market_impact(avg_spread, total_volume)
            
            return {
                'liquidity_vacuum': liquidity_vacuum,
                'order_flow_imbalance': order_flow_imbalance,
                'market_impact': market_impact,
                'spread_widening': avg_spread
            }
            
        except Exception as e:
            logger.error(f"Liquidity detection failed: {e}")
            return self.get_default_liquidity_features()
    
    def calculate_liquidity_vacuum(self, volume, oi):
        """Calculate liquidity vacuum indicator"""
        # Simplified calculation
        if volume < 1000 and oi > 1000000:
            return 0.8  # High vacuum
        elif volume < 5000 and oi > 500000:
            return 0.5  # Medium vacuum
        else:
            return 0.0  # No vacuum
    
    def calculate_order_flow_imbalance(self, option_chain):
        """Calculate order flow imbalance - simplified"""
        # In production, this would use real order flow data
        return 0.0
    
    def calculate_market_impact(self, avg_spread, volume):
        """Calculate market impact score"""
        if avg_spread > 0.05 and volume < 10000:
            return 0.8  # High impact
        elif avg_spread > 0.02 and volume < 50000:
            return 0.5  # Medium impact
        else:
            return 0.0  # Low impact
    
    def get_default_liquidity_features(self):
        return {
            'liquidity_vacuum': 0.0,
            'order_flow_imbalance': 0.0,
            'market_impact': 0.0,
            'spread_widening': 0.0
        }

class VolatilityAnalyzer:
    """Volatility regime analysis"""
    
    def analyze_volatility(self, option_chain):
        try:
            iv_values = []
            
            for strike_data in option_chain.strikes:
                if not isinstance(strike_data, dict):
                    continue
                    
                for option_type in ['CE', 'PE']:
                    if option_type in strike_data and isinstance(strike_data[option_type], dict):
                        iv = strike_data[option_type].get('iv', 0)
                        if iv > 0:
                            iv_values.append(iv)
            
            if not iv_values:
                return self.get_default_volatility_features()
            
            avg_iv = sum(iv_values) / len(iv_values)
            iv_regime = self.classify_iv_regime(avg_iv)
            volatility_expansion = self.calculate_volatility_expansion(iv_values)
            term_structure = self.calculate_term_structure(option_chain)
            
            return {
                'iv_regime': iv_regime,
                'volatility_expansion': volatility_expansion,
                'term_structure': term_structure,
                'implied_volatility_surface': {'avg_iv': avg_iv}
            }
            
        except Exception as e:
            logger.error(f"Volatility analysis failed: {e}")
            return self.get_default_volatility_features()
    
    def classify_iv_regime(self, avg_iv):
        """Classify IV regime"""
        if avg_iv < 15:
            return "LOW"
        elif avg_iv > 25:
            return "HIGH"
        else:
            return "MEDIUM"
    
    def calculate_volatility_expansion(self, iv_values):
        """Calculate volatility expansion - simplified"""
        # In production, this would compare with historical IV
        if len(iv_values) < 2:
            return 0.0
        return max(iv_values) - min(iv_values)
    
    def calculate_term_structure(self, option_chain):
        """Calculate term structure - simplified"""
        # In production, this would compare different expiries
        return 0.0
    
    def get_default_volatility_features(self):
        return {
            'iv_regime': "MEDIUM",
            'volatility_expansion': 0.0,
            'term_structure': 0.0,
            'implied_volatility_surface': {'avg_iv': 20.0}
        }

class MicrostructureAnalyzer:
    """Market microstructure analysis"""
    
    def analyze_microstructure(self, option_chain):
        try:
            dealer_hedging_pressure = self.calculate_dealer_hedging_pressure(option_chain)
            institutional_flow = self.detect_institutional_flow(option_chain)
            support_resistance = self.calculate_support_resistance(option_chain)
            pin_probability = self.calculate_pin_probability(option_chain)
            
            return {
                'dealer_hedging_pressure': dealer_hedging_pressure,
                'institutional_flow': institutional_flow,
                'support_resistance_levels': support_resistance,
                'pin_probability': pin_probability
            }
            
        except Exception as e:
            logger.error(f"Microstructure analysis failed: {e}")
            return self.get_default_microstructure_features()
    
    def calculate_dealer_hedging_pressure(self, option_chain):
        """Calculate dealer hedging pressure"""
        # Simplified calculation based on gamma imbalance
        total_gamma = 0
        for strike_data in option_chain.strikes:
            if not isinstance(strike_data, dict):
                continue
                
            for option_type in ['CE', 'PE']:
                if option_type in strike_data and isinstance(strike_data[option_type], dict):
                    gamma = strike_data[option_type].get('gamma', 0)
                    total_gamma += gamma
        
        return min(1.0, abs(total_gamma) / 1000000)
    
    def detect_institutional_flow(self, option_chain):
        """Detect institutional flow - simplified"""
        # In production, this would use trade size analysis
        return 0.0
    
    def calculate_support_resistance(self, option_chain):
        """Calculate support/resistance from option chain"""
        support_levels = []
        resistance_levels = []
        
        max_put_oi = 0
        max_call_oi = 0
        support_strike = None
        resistance_strike = None
        
        for strike_data in option_chain.strikes:
            if not isinstance(strike_data, dict):
                continue
                
            strike = strike_data.get('strike')
            if not strike:
                continue
            
            # Find max put OI for support
            if 'PE' in strike_data and isinstance(strike_data['PE'], dict):
                put_oi = strike_data['PE'].get('oi', 0)
                if put_oi > max_put_oi:
                    max_put_oi = put_oi
                    support_strike = strike
            
            # Find max call OI for resistance
            if 'CE' in strike_data and isinstance(strike_data['CE'], dict):
                call_oi = strike_data['CE'].get('oi', 0)
                if call_oi > max_call_oi:
                    max_call_oi = call_oi
                    resistance_strike = strike
        
        if support_strike:
            support_levels.append(support_strike)
        if resistance_strike:
            resistance_levels.append(resistance_strike)
        
        return {
            'support': support_levels,
            'resistance': resistance_levels
        }
    
    def calculate_pin_probability(self, option_chain):
        """Calculate pin probability"""
        # Simplified calculation based on OI concentration
        total_oi = 0
        max_oi = 0
        
        for strike_data in option_chain.strikes:
            if not isinstance(strike_data, dict):
                continue
                
            for option_type in ['CE', 'PE']:
                if option_type in strike_data and isinstance(strike_data[option_type], dict):
                    oi = strike_data[option_type].get('oi', 0)
                    total_oi += oi
                    max_oi = max(max_oi, oi)
        
        if total_oi == 0:
            return 0.0
        
        return min(1.0, max_oi / total_oi)
    
    def get_default_microstructure_features(self):
        return {
            'dealer_hedging_pressure': 0.0,
            'institutional_flow': 0.0,
            'support_resistance_levels': {'support': [], 'resistance': []},
            'pin_probability': 0.0
        }
