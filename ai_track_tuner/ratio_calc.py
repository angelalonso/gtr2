"""
Ratio Calculator Logic for AIW Ratio Editor
Contains the calculation logic and data structures for ratio calculations
"""

from dataclasses import dataclass, asdict
from typing import Optional, Tuple, List, Dict
import csv
from pathlib import Path
from datetime import datetime
import math


@dataclass
class TrackParameters:
    """Parameters for the exponential formula per track"""
    A: float  # Range above minimum time
    k: float  # Decay constant
    B: float  # Fastest possible time (asymptote)
    source_data: List[Tuple[float, float]]  # (ratio, median_time) pairs used for fitting


@dataclass
class LapTimes:
    """Container for lap time data"""
    pole: float = 0.0
    last_ai: float = 0.0
    player: float = 0.0
    
    @property
    def avg_ai(self) -> float:
        """Calculate average AI time"""
        if self.pole > 0 and self.last_ai > 0:
            return (self.pole + self.last_ai) / 2
        return 0.0
    
    @property
    def median_ai(self) -> float:
        """Calculate median AI time (same as avg for two points)"""
        return self.avg_ai
    
    @property
    def ai_spread(self) -> float:
        """Calculate spread between best and worst AI"""
        if self.pole > 0 and self.last_ai > 0:
            return self.last_ai - self.pole
        return 0.0
    
    @property
    def ai_range(self) -> Tuple[float, float]:
        """Get the AI time range (best, worst)"""
        return self.pole, self.last_ai
    
    def are_valid(self) -> bool:
        """Check if all times are valid"""
        return self.pole > 0 and self.last_ai > 0 and self.player > 0


@dataclass
class RatioConfig:
    """Configuration for ratio calculations"""
    historic_csv: str = ""
    goal_percent: float = 50.0
    goal_offset: float = 0.0
    percent_ratio: float = 0.01  # Default: 0.01 ratio points per 1% change
    use_exponential_model: bool = False
    
    # Exponential model parameters
    exponential_default_A: float = 300.0      # Time range above minimum (seconds)
    exponential_default_k: float = 3.0        # Decay constant
    exponential_default_B: float = 100.0      # Fastest possible time (seconds)
    exponential_power_factor: float = 1.0     # Curve shape modifier (p)
    exponential_ratio_offset: float = 0.0     # Horizontal shift (R0)
    exponential_min_ratio: float = 0.1        # Minimum allowed ratio
    exponential_max_ratio: float = 10.0       # Maximum allowed ratio


@dataclass
class PredictedTimes:
    """Predicted AI times for a given ratio"""
    best: float  # Predicted best AI time
    worst: float  # Predicted worst AI time
    median: float  # Predicted median AI time
    spread: float  # Predicted spread between best and worst
    
    def to_dict(self) -> dict:
        """Convert to dictionary for display"""
        return {
            'best': f"{self.best:.3f}s",
            'worst': f"{self.worst:.3f}s",
            'median': f"{self.median:.3f}s",
            'spread': f"{self.spread:.3f}s"
        }


@dataclass
class CalculationDetails:
    """Detailed results of a ratio calculation"""
    current_ratio: float  # Original ratio (usually 1.0)
    new_ratio: float  # Calculated new ratio
    current_position: float  # Current percentage position of user time
    target_position: float  # Target percentage position (goal_percent)
    ai_best: float
    ai_worst: float
    ai_avg: float
    player_time: float
    time_difference: float  # player - ai_avg
    percent_difference: float  # (player - ai_avg) / ai_spread * 100
    ratio_change: float  # How much the ratio needs to change
    goal_offset_applied: bool  # Whether offset was applied
    calculation_method: str = "linear"  # "linear" or "exponential"
    track_params: Optional[TrackParameters] = None
    curve_info: Optional[dict] = None  # Formula and parameter info
    predicted_times: Optional[PredictedTimes] = None  # Predicted AI times at new ratio
    
    def to_dict(self) -> dict:
        """Convert to dictionary for CSV export"""
        result = {
            'current_ratio': f"{self.current_ratio:.6f}",
            'new_ratio': f"{self.new_ratio:.6f}",
            'current_position': f"{self.current_position:.2f}%",
            'target_position': f"{self.target_position:.2f}%",
            'ai_best': f"{self.ai_best:.3f}",
            'ai_worst': f"{self.ai_worst:.3f}",
            'ai_avg': f"{self.ai_avg:.3f}",
            'player_time': f"{self.player_time:.3f}",
            'time_diff': f"{self.time_difference:+.3f}",
            'percent_diff': f"{self.percent_difference:+.2f}%",
            'ratio_change': f"{self.ratio_change:+.6f}",
            'method': self.calculation_method
        }
        
        # Add curve info if available
        if self.curve_info:
            result.update({
                'curve_A': f"{self.curve_info.get('A', 0):.1f}",
                'curve_k': f"{self.curve_info.get('k', 0):.3f}",
                'curve_B': f"{self.curve_info.get('B', 0):.1f}",
                'curve_p': f"{self.curve_info.get('p', 1.0):.2f}",
                'curve_R0': f"{self.curve_info.get('R0', 0):.2f}",
                'formula': self.curve_info.get('formula_inverse', ''),
                'source': self.curve_info.get('source', 'default')
            })
        
        # Add predicted times if available
        if self.predicted_times:
            result.update({
                'pred_best': f"{self.predicted_times.best:.3f}",
                'pred_worst': f"{self.predicted_times.worst:.3f}",
                'pred_median': f"{self.predicted_times.median:.3f}",
                'pred_spread': f"{self.predicted_times.spread:.3f}"
            })
        
        return result


@dataclass
class CalculatedRatios:
    """Result of ratio calculations with details"""
    qual_ratio: Optional[float] = None
    race_ratio: Optional[float] = None
    qual_error: Optional[str] = None
    race_error: Optional[str] = None
    qual_details: Optional[CalculationDetails] = None
    race_details: Optional[CalculationDetails] = None
    
    def has_qual_ratio(self) -> bool:
        """Check if QualRatio was successfully calculated"""
        return self.qual_ratio is not None and self.qual_error is None
    
    def has_race_ratio(self) -> bool:
        """Check if RaceRatio was successfully calculated"""
        return self.race_ratio is not None and self.race_error is None
    
    def any_ratio_calculated(self) -> bool:
        """Check if any ratio was successfully calculated"""
        return self.has_qual_ratio() or self.has_race_ratio()


class AdjustableExponentialModel:
    """
    Adjustable exponential model with configurable parameters
    Formula: T = A * e^(-k * (R - R0)^p) + B
    Inverse: R = R0 + (-(1/k) * ln((T - B)/A))^(1/p)
    """
    
    def __init__(self, params=None):
        """
        Initialize with parameters from config
        
        Args:
            params: Dictionary with exponential parameters
                   (default_A, default_k, default_B, power_factor, 
                    ratio_offset, min_ratio, max_ratio)
        """
        if params is None:
            # Use defaults
            self.default_A = 300.0
            self.default_k = 3.0
            self.default_B = 100.0
            self.power_factor = 1.0
            self.ratio_offset = 0.0
            self.min_ratio = 0.1
            self.max_ratio = 10.0
        else:
            self.default_A = params.get('default_A', 300.0)
            self.default_k = params.get('default_k', 3.0)
            self.default_B = params.get('default_B', 100.0)
            self.power_factor = params.get('power_factor', 1.0)
            self.ratio_offset = params.get('ratio_offset', 0.0)
            self.min_ratio = params.get('min_ratio', 0.1)
            self.max_ratio = params.get('max_ratio', 10.0)
    
    def get_formula_string(self, track_params=None):
        """Get a human-readable formula string with current parameters"""
        if track_params:
            A = track_params.A
            k = track_params.k
            B = track_params.B
            source = "track-specific"
        else:
            A = self.default_A
            k = self.default_k
            B = self.default_B
            source = "default"
        
        # Format parameters nicely
        A_str = f"{A:.1f}"
        k_str = f"{k:.3f}"
        B_str = f"{B:.1f}"
        p_str = f"{self.power_factor:.2f}"
        
        # Format R0 with sign
        if self.ratio_offset >= 0:
            R0_str = f"+{self.ratio_offset:.2f}"
        else:
            R0_str = f"{self.ratio_offset:.2f}"
        
        # Build the formula strings
        if self.power_factor == 1.0:
            forward = f"T = {A_str} × e^(-{k_str} × (R {R0_str})) + {B_str}"
            inverse = f"R = {R0_str} + (-(1/{k_str}) × ln((T - {B_str})/{A_str}))"
        else:
            forward = f"T = {A_str} × e^(-{k_str} × (R {R0_str})^{p_str}) + {B_str}"
            inverse = f"R = {R0_str} + (-(1/{k_str}) × ln((T - {B_str})/{A_str}))^(1/{p_str})"
        
        return {
            'forward': forward,
            'inverse': inverse,
            'source': source,
            'params': {
                'A': A, 'k': k, 'B': B, 'p': self.power_factor, 'R0': self.ratio_offset
            }
        }
    
    def predict_times_for_ratio(self, R, track_params=None, current_spread=None):
        """
        Predict best and worst AI times for a given ratio
        
        Args:
            R: Ratio value
            track_params: Optional track-specific parameters
            current_spread: Current spread between best and worst (for scaling)
            
        Returns:
            PredictedTimes object
        """
        # Get median time prediction
        if track_params:
            median = self.time_from_ratio(R, track_params)
        else:
            median = self.time_from_ratio(R)
        
        # Estimate spread based on current spread if available
        if current_spread and current_spread > 0:
            # Assume spread scales with ratio (higher ratio = closer times)
            # This is a heuristic - you might want to model this differently
            spread_factor = 1.0 / (1.0 + R * 0.5)  # Spread decreases as ratio increases
            spread = current_spread * spread_factor
        else:
            # Default spread as percentage of median time
            spread = median * 0.03  # Assume 3% spread by default
        
        # Calculate best and worst
        best = median - (spread / 2)
        worst = median + (spread / 2)
        
        return PredictedTimes(
            best=best,
            worst=worst,
            median=median,
            spread=spread
        )
    
    def time_from_ratio(self, R, track_params=None):
        """
        Calculate predicted time from ratio
        
        T = A * e^(-k * (R - R0)^p) + B
        
        Args:
            R: Ratio value
            track_params: Optional track-specific parameters (overrides defaults)
            
        Returns:
            float: Predicted time in seconds
        """
        # Use track-specific params if available, otherwise defaults
        if track_params:
            A = track_params.A
            k = track_params.k
            B = track_params.B
        else:
            A = self.default_A
            k = self.default_k
            B = self.default_B
        
        # Apply adjustments
        adjusted_R = max(0, R - self.ratio_offset)
        return A * math.exp(-k * (adjusted_R ** self.power_factor)) + B
    
    def ratio_from_time(self, T, track_params=None):
        """
        Calculate required ratio for target time
        
        R = R0 + (-(1/k) * ln((T - B)/A))^(1/p)
        
        Args:
            T: Target median time in seconds
            track_params: Optional track-specific parameters (overrides defaults)
            
        Returns:
            float: Required ratio
        """
        # Use track-specific params if available, otherwise defaults
        if track_params:
            A = track_params.A
            k = track_params.k
            B = track_params.B
        else:
            A = self.default_A
            k = self.default_k
            B = self.default_B
        
        # Check if target is achievable
        if T <= B:
            raise ValueError(f"Target time {T:.3f}s is faster than track limit {B:.3f}s")
        
        t_minus_b = T - B
        if t_minus_b <= 0:
            raise ValueError("Target time below track limit")
        
        ratio_arg = t_minus_b / A
        if ratio_arg <= 0:
            raise ValueError("Invalid ratio calculation - target too low")
        
        # Calculate inner part: -(1/k) * ln(ratio_arg)
        inner = -(1.0 / k) * math.log(ratio_arg)
        
        if inner < 0:
            raise ValueError("Invalid calculation - result would be negative")
        
        # Apply power factor and offset
        if self.power_factor != 1.0:
            R = self.ratio_offset + (inner ** (1.0 / self.power_factor))
        else:
            R = self.ratio_offset + inner
        
        # Clamp to valid range
        return max(self.min_ratio, min(self.max_ratio, R))
    
    def get_curve_info(self, track_params=None):
        """Get information about the current curve"""
        formula = self.get_formula_string(track_params)
        
        if track_params:
            return {
                'A': track_params.A,
                'k': track_params.k,
                'B': track_params.B,
                'p': self.power_factor,
                'R0': self.ratio_offset,
                'min_R': self.min_ratio,
                'max_R': self.max_ratio,
                'formula_forward': formula['forward'],
                'formula_inverse': formula['inverse'],
                'source': formula['source'],
                'params': formula['params']
            }
        else:
            return {
                'A': self.default_A,
                'k': self.default_k,
                'B': self.default_B,
                'p': self.power_factor,
                'R0': self.ratio_offset,
                'min_R': self.min_ratio,
                'max_R': self.max_ratio,
                'formula_forward': formula['forward'],
                'formula_inverse': formula['inverse'],
                'source': formula['source'],
                'params': formula['params']
            }


class TrackModelDatabase:
    """Database of track-specific exponential models derived from historical data"""
    
    def __init__(self, csv_path: Optional[str] = None):
        self.track_parameters: Dict[str, TrackParameters] = {}
        if csv_path:
            self.load_from_historic(csv_path)
    
    def load_from_historic(self, csv_path: str) -> None:
        """Load and fit exponential models from historic CSV data"""
        try:
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                
                # Group data by track
                track_data: Dict[str, List[Tuple[float, float]]] = {}
                
                for row in reader:
                    # Only use rows with AI times
                    if row.get('Qual AI Best (s)') and row.get('Qual AI Worst (s)'):
                        try:
                            track = row['Track Name']
                            ratio = float(row['Current QualRatio'])
                            
                            # Calculate median AI time
                            best = float(row['Qual AI Best (s)'])
                            worst = float(row['Qual AI Worst (s)'])
                            if best > 0 and worst > 0:
                                median = (best + worst) / 2
                                
                                if track not in track_data:
                                    track_data[track] = []
                                track_data[track].append((ratio, median))
                        except (ValueError, KeyError):
                            continue
                
                # Fit exponential model for each track with enough data
                for track, points in track_data.items():
                    if len(points) >= 3:  # Need at least 3 points for reliable fit
                        params = self._fit_exponential_model(points)
                        if params:
                            self.track_parameters[track] = params
                            print(f"Loaded exponential model for {track} (A={params.A:.2f}, k={params.k:.3f}, B={params.B:.2f})")
        
        except Exception as e:
            print(f"Error loading track models: {e}")
    
    def _fit_exponential_model(self, points: List[Tuple[float, float]]) -> Optional[TrackParameters]:
        """
        Fit exponential model T = A * e^(-k*R) + B to data points
        Uses three-point method if exactly 3 points, otherwise uses approximation
        """
        # Sort by ratio
        points.sort(key=lambda x: x[0])
        
        if len(points) == 3:
            # Use the three-point method from the analysis
            R1, T1 = points[0]  # Lowest ratio (slowest times)
            R2, T2 = points[1]  # Middle ratio
            R3, T3 = points[2]  # Highest ratio (fastest times)
            
            try:
                # Solve for k using the three-point method
                # x = e^(-0.5k * (R2-R1))? Actually let's use the method from analysis
                # Assuming equally spaced for simplicity, we can approximate
                
                # Better: Use the method from analysis with any three points
                # We'll use the general approach
                
                # First, estimate B as slightly less than fastest time
                B_estimate = T3 * 0.98  # Assume asymptote is 2% faster than best seen
                
                # Transform to linear form: ln(T - B) = ln(A) - k*R
                # Try different B values to find best linear fit
                best_r2 = -1
                best_params = None
                
                for B_test in [T3 * f for f in [0.95, 0.96, 0.97, 0.98, 0.99]]:
                    transformed = [(R, math.log(T - B_test)) for R, T in points if T > B_test]
                    if len(transformed) < 2:
                        continue
                    
                    # Linear regression on transformed data
                    n = len(transformed)
                    sum_x = sum(R for R, _ in transformed)
                    sum_y = sum(y for _, y in transformed)
                    sum_xy = sum(R * y for R, y in transformed)
                    sum_x2 = sum(R * R for R, _ in transformed)
                    
                    denominator = n * sum_x2 - sum_x * sum_x
                    if abs(denominator) < 1e-10:
                        continue
                    
                    k = (n * sum_xy - sum_x * sum_y) / denominator
                    lnA = (sum_y - k * sum_x) / n
                    A = math.exp(lnA)
                    
                    # Calculate R-squared
                    y_mean = sum_y / n
                    ss_tot = sum((y - y_mean) ** 2 for _, y in transformed)
                    ss_res = sum((y - (lnA - k * R)) ** 2 for R, y in transformed)
                    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                    
                    if r2 > best_r2:
                        best_r2 = r2
                        best_params = TrackParameters(
                            A=A, k=k, B=B_test,
                            source_data=points
                        )
                
                return best_params
                
            except (ValueError, ZeroDivisionError, OverflowError) as e:
                print(f"Error fitting exponential model: {e}")
                return None
        
        return None
    
    def get_parameters(self, track_name: str) -> Optional[TrackParameters]:
        """Get exponential parameters for a track"""
        # Try exact match first
        if track_name in self.track_parameters:
            return self.track_parameters[track_name]
        
        # Try case-insensitive partial match
        track_lower = track_name.lower()
        for key, params in self.track_parameters.items():
            if track_lower in key.lower() or key.lower() in track_lower:
                return params
        
        return None


class RatioCalculator:
    """Handles all ratio calculation logic"""
    
    MIN_RATIO = 0.1
    MAX_RATIO = 10.0
    EPSILON = 0.001  # Tolerance for division by zero
    DEFAULT_RATIO = 1.0  # Default ratio value
    
    def __init__(self):
        self.track_db = TrackModelDatabase()
        self.exponential_model = None  # Will be initialized with config
    
    def load_historic_data(self, csv_path: str):
        """Load historic data for exponential models"""
        self.track_db.load_from_historic(csv_path)
    
    def configure_exponential_model(self, config: RatioConfig):
        """Configure the exponential model with settings from config"""
        params = {
            'default_A': config.exponential_default_A,
            'default_k': config.exponential_default_k,
            'default_B': config.exponential_default_B,
            'power_factor': config.exponential_power_factor,
            'ratio_offset': config.exponential_ratio_offset,
            'min_ratio': config.exponential_min_ratio,
            'max_ratio': config.exponential_max_ratio
        }
        self.exponential_model = AdjustableExponentialModel(params)
    
    def calculate_single_ratio(
        self,
        times: LapTimes, 
        config: RatioConfig,
        track_name: str = "",
        current_ratio: float = DEFAULT_RATIO
    ) -> Tuple[Optional[float], Optional[str], Optional[CalculationDetails]]:
        """
        Calculate the ratio needed to place user time at the goal percentage position
        
        Args:
            times: LapTimes object with pole, last_ai, player times
            config: RatioConfig with goal_percent, goal_offset, percent_ratio
            track_name: Name of the track (for exponential model)
            current_ratio: Current ratio value (default 1.0)
            
        Returns:
            Tuple of (new_ratio_value, error_message, calculation_details)
        """
        # Validate inputs
        if not times.are_valid():
            return None, "Incomplete lap times", None
        
        if times.pole <= 0:
            return None, "Pole time must be greater than 0", None
        if times.last_ai <= 0:
            return None, "Last AI time must be greater than 0", None
        if times.player <= 0:
            return None, "Player time must be greater than 0", None
        
        # Use exponential model if enabled and track parameters available
        if config.use_exponential_model:
            # Ensure exponential model is configured
            if not self.exponential_model:
                self.configure_exponential_model(config)
            
            # Get track parameters
            track_params = self.track_db.get_parameters(track_name)
            
            return self._calculate_exponential(times, config, track_name, track_params, current_ratio)
        else:
            # Linear method (original)
            return self._calculate_linear(times, config, current_ratio)
    
    def _calculate_linear(
        self,
        times: LapTimes,
        config: RatioConfig,
        current_ratio: float
    ) -> Tuple[Optional[float], Optional[str], Optional[CalculationDetails]]:
        """Linear calculation method"""
        ai_spread = times.ai_spread
        
        if ai_spread < RatioCalculator.EPSILON:
            return None, "AI times are too close (no meaningful spread)", None
        
        # Calculate current percentage position of user time
        # 0% = best AI time, 100% = worst AI time
        current_position = ((times.player - times.pole) / ai_spread) * 100
        
        # Calculate target position (goal_percent + goal_offset)
        target_position = config.goal_percent + config.goal_offset
        
        # Calculate how much we need to shift the percentage
        position_shift = target_position - current_position
        
        # Calculate ratio change needed
        # If percent_ratio is 0.01, then 1% shift = 0.01 ratio change
        ratio_change = position_shift * config.percent_ratio
        
        # Calculate new ratio
        new_ratio = current_ratio + ratio_change
        
        # Clamp to valid range
        new_ratio = max(RatioCalculator.MIN_RATIO, 
                       min(RatioCalculator.MAX_RATIO, new_ratio))
        
        # Calculate time values for display
        avg_ai = times.avg_ai
        time_diff = times.player - avg_ai
        percent_diff = (time_diff / ai_spread) * 100
        
        # Simple predicted times for linear method (linear interpolation)
        predicted_best = times.pole * (new_ratio / current_ratio)
        predicted_worst = times.last_ai * (new_ratio / current_ratio)
        predicted_median = (predicted_best + predicted_worst) / 2
        predicted_spread = predicted_worst - predicted_best
        
        predicted_times = PredictedTimes(
            best=predicted_best,
            worst=predicted_worst,
            median=predicted_median,
            spread=predicted_spread
        )
        
        # Create details object
        details = CalculationDetails(
            current_ratio=current_ratio,
            new_ratio=new_ratio,
            current_position=current_position,
            target_position=target_position,
            ai_best=times.pole,
            ai_worst=times.last_ai,
            ai_avg=avg_ai,
            player_time=times.player,
            time_difference=time_diff,
            percent_difference=percent_diff,
            ratio_change=ratio_change,
            goal_offset_applied=(config.goal_offset != 0),
            calculation_method="linear",
            predicted_times=predicted_times
        )
        
        return new_ratio, None, details
    
    def _calculate_exponential(
        self,
        times: LapTimes,
        config: RatioConfig,
        track_name: str,
        track_params: Optional[TrackParameters],
        current_ratio: float
    ) -> Tuple[Optional[float], Optional[str], Optional[CalculationDetails]]:
        """Exponential calculation method"""
        
        # Calculate target median AI time based on player time and goal
        ai_spread = times.ai_spread
        target_position = config.goal_percent + config.goal_offset
        
        # Convert percentage position to time position
        # If player is at position P%, then median AI time should be at 50%
        # So: player_time = AI_best + (P/100) * spread
        # We want median AI time (at 50%) to be: target_median = player_time - ((P - 50)/100) * spread
        position_diff = (target_position - 50) / 100  # Convert to decimal (e.g., 60% -> +0.1)
        target_median_time = times.player - position_diff * ai_spread
        
        # Apply the exponential formula
        try:
            # Calculate required ratio using adjustable model
            new_ratio = self.exponential_model.ratio_from_time(target_median_time, track_params)
            
            # Get curve info for display
            curve_info = self.exponential_model.get_curve_info(track_params)
            
            # Predict AI times at new ratio
            predicted_times = self.exponential_model.predict_times_for_ratio(
                new_ratio, track_params, ai_spread
            )
            
            # Calculate details for display
            avg_ai = times.avg_ai
            current_position = ((times.player - times.pole) / ai_spread) * 100
            time_diff = times.player - avg_ai
            percent_diff = (time_diff / ai_spread) * 100
            ratio_change = new_ratio - current_ratio
            
            details = CalculationDetails(
                current_ratio=current_ratio,
                new_ratio=new_ratio,
                current_position=current_position,
                target_position=target_position,
                ai_best=times.pole,
                ai_worst=times.last_ai,
                ai_avg=avg_ai,
                player_time=times.player,
                time_difference=time_diff,
                percent_difference=percent_diff,
                ratio_change=ratio_change,
                goal_offset_applied=(config.goal_offset != 0),
                calculation_method="exponential",
                track_params=track_params,
                curve_info=curve_info,
                predicted_times=predicted_times
            )
            
            return new_ratio, None, details
            
        except (ValueError, ZeroDivisionError) as e:
            return None, f"Exponential calculation error: {e}", None
    
    def calculate_all(
        self,
        qual_times: LapTimes, 
        race_times: LapTimes,
        config: RatioConfig,
        track_name: str = "",
        current_qual: float = DEFAULT_RATIO,
        current_race: float = DEFAULT_RATIO
    ) -> CalculatedRatios:
        """
        Calculate both QualRatio and RaceRatio from lap times
        
        Args:
            qual_times: LapTimes for qualifying
            race_times: LapTimes for race
            config: RatioConfig with calculation parameters
            track_name: Name of the track (for exponential model)
            current_qual: Current QualRatio value
            current_race: Current RaceRatio value
            
        Returns:
            CalculatedRatios object with results and details
        """
        result = CalculatedRatios()
        
        # Configure exponential model if needed
        if config.use_exponential_model and not self.exponential_model:
            self.configure_exponential_model(config)
        
        # Calculate QualRatio
        if qual_times.are_valid():
            qual_ratio, qual_error, qual_details = self.calculate_single_ratio(
                qual_times, config, track_name, current_qual
            )
            result.qual_ratio = qual_ratio
            result.qual_error = qual_error
            result.qual_details = qual_details
        else:
            result.qual_error = "Incomplete qualifying times"
        
        # Calculate RaceRatio
        if race_times.are_valid():
            race_ratio, race_error, race_details = self.calculate_single_ratio(
                race_times, config, track_name, current_race
            )
            result.race_ratio = race_ratio
            result.race_error = race_error
            result.race_details = race_details
        else:
            result.race_error = "Incomplete race times"
        
        return result
    
    @staticmethod
    def format_ratio(ratio: Optional[float], decimal_places: int = 6) -> str:
        """Format a ratio value for display"""
        if ratio is None:
            return "---"
        return f"{ratio:.{decimal_places}f}"
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """Format time in seconds for display"""
        return f"{seconds:.3f}s"
    
    @staticmethod
    def format_percent(percent: float) -> str:
        """Format percentage for display"""
        return f"{percent:+.2f}%"


class HistoricCSVHandler:
    """Handles reading and writing to the historic CSV file"""
    
    HEADERS = [
        'timestamp',
        'track_name',
        'current_qual',
        'new_qual',
        'qual_current_pos',
        'qual_target_pos',
        'qual_ai_best',
        'qual_ai_worst',
        'qual_ai_avg',
        'qual_player_time',
        'current_race',
        'new_race',
        'race_current_pos',
        'race_target_pos',
        'race_ai_best',
        'race_ai_worst',
        'race_ai_avg',
        'race_player_time',
        'goal_percent',
        'goal_offset',
        'percent_ratio',
        'calculation_method'
    ]
    
    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path) if csv_path else None
    
    def is_valid(self) -> bool:
        """Check if CSV path is valid"""
        return self.csv_path is not None and self.csv_path.parent.exists()
    
    def ensure_file_exists(self):
        """Create CSV file with headers if it doesn't exist"""
        if not self.csv_path:
            return False
        
        if not self.csv_path.exists():
            try:
                self.csv_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.csv_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(self.HEADERS)
                return True
            except Exception as e:
                print(f"Error creating CSV file: {e}")
                return False
        return True
    
    def save_calculation(
        self,
        track_name: str,
        qual_times: LapTimes,
        race_times: LapTimes,
        results: CalculatedRatios,
        config: RatioConfig,
        current_qual: float,
        current_race: float
    ) -> bool:
        """
        Save a calculation to the CSV file
        
        Args:
            track_name: Name of the track
            qual_times: Qualifying lap times
            race_times: Race lap times
            results: Calculated ratios with details
            config: Configuration used for calculation
            current_qual: Current QualRatio value
            current_race: Current RaceRatio value
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.is_valid():
            return False
        
        if not self.ensure_file_exists():
            return False
        
        try:
            row = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'track_name': track_name,
                
                # Qualifying data
                'current_qual': f"{current_qual:.6f}",
                'new_qual': f"{results.qual_ratio:.6f}" if results.qual_ratio else "",
                'qual_current_pos': f"{results.qual_details.current_position:.2f}%" if results.qual_details else "",
                'qual_target_pos': f"{results.qual_details.target_position:.2f}%" if results.qual_details else "",
                'qual_ai_best': f"{qual_times.pole:.3f}" if qual_times.pole > 0 else "",
                'qual_ai_worst': f"{qual_times.last_ai:.3f}" if qual_times.last_ai > 0 else "",
                'qual_ai_avg': f"{qual_times.avg_ai:.3f}" if qual_times.avg_ai > 0 else "",
                'qual_player_time': f"{qual_times.player:.3f}" if qual_times.player > 0 else "",
                
                # Race data
                'current_race': f"{current_race:.6f}",
                'new_race': f"{results.race_ratio:.6f}" if results.race_ratio else "",
                'race_current_pos': f"{results.race_details.current_position:.2f}%" if results.race_details else "",
                'race_target_pos': f"{results.race_details.target_position:.2f}%" if results.race_details else "",
                'race_ai_best': f"{race_times.pole:.3f}" if race_times.pole > 0 else "",
                'race_ai_worst': f"{race_times.last_ai:.3f}" if race_times.last_ai > 0 else "",
                'race_ai_avg': f"{race_times.avg_ai:.3f}" if race_times.avg_ai > 0 else "",
                'race_player_time': f"{race_times.player:.3f}" if race_times.player > 0 else "",
                
                # Configuration
                'goal_percent': config.goal_percent,
                'goal_offset': config.goal_offset,
                'percent_ratio': config.percent_ratio,
                'calculation_method': results.qual_details.calculation_method if results.qual_details else "linear"
            }
            
            with open(self.csv_path, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.HEADERS)
                writer.writerow(row)
            
            return True
            
        except Exception as e:
            print(f"Error saving to CSV: {e}")
            return False
    
    def load_history(self, limit: int = 100) -> List[dict]:
        """Load recent history from CSV file"""
        if not self.is_valid() or not self.csv_path.exists():
            return []
        
        try:
            with open(self.csv_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                return rows[-limit:]  # Return most recent entries
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return []


class TimeConverter:
    """Utility for converting between time formats"""
    
    @staticmethod
    def seconds_to_mmssms(seconds: float) -> Tuple[int, int, int]:
        """
        Convert seconds to minutes, seconds, milliseconds
        
        Returns:
            Tuple of (minutes, seconds, milliseconds)
        """
        total_seconds = max(0, seconds)
        minutes = int(total_seconds) // 60
        secs = int(total_seconds) % 60
        ms = int((total_seconds - int(total_seconds)) * 1000)
        return minutes, secs, ms
    
    @staticmethod
    def mmssms_to_seconds(minutes: int, seconds: int, milliseconds: int) -> float:
        """
        Convert minutes, seconds, milliseconds to total seconds
        """
        result = minutes * 60 + seconds + milliseconds / 1000.0
        # DEBUG: Print calculation
        print(f"DEBUG - TimeConverter: {minutes}m {seconds}s {result}result")
        return result
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """Format time as mm:ss.ms for display"""
        minutes, secs, ms = TimeConverter.seconds_to_mmssms(seconds)
        return f"{minutes}:{secs:02d}.{ms:03d}"
