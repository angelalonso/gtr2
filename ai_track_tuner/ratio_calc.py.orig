"""
Ratio Calculator Logic for AIW Ratio Editor
Contains the calculation logic and data structures for ratio calculations
"""

from dataclasses import dataclass, asdict
from typing import Optional, Tuple, List
import csv
from pathlib import Path
from datetime import datetime


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
    
    def to_dict(self) -> dict:
        """Convert to dictionary for CSV export"""
        return {
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
            'ratio_change': f"{self.ratio_change:+.6f}"
        }


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


class RatioCalculator:
    """Handles all ratio calculation logic"""
    
    MIN_RATIO = 0.1
    MAX_RATIO = 10.0
    EPSILON = 0.001  # Tolerance for division by zero
    DEFAULT_RATIO = 1.0  # Default ratio value
    
    @staticmethod
    def calculate_single_ratio(
        times: LapTimes, 
        config: RatioConfig,
        current_ratio: float = DEFAULT_RATIO
    ) -> Tuple[Optional[float], Optional[str], Optional[CalculationDetails]]:
        """
        Calculate the ratio needed to place user time at the goal percentage position
        
        Args:
            times: LapTimes object with pole, last_ai, player times
            config: RatioConfig with goal_percent, goal_offset, percent_ratio
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
            goal_offset_applied=(config.goal_offset != 0)
        )
        
        return new_ratio, None, details
    
    @staticmethod
    def calculate_all(
        qual_times: LapTimes, 
        race_times: LapTimes,
        config: RatioConfig,
        current_qual: float = DEFAULT_RATIO,
        current_race: float = DEFAULT_RATIO
    ) -> CalculatedRatios:
        """
        Calculate both QualRatio and RaceRatio from lap times
        
        Args:
            qual_times: LapTimes for qualifying
            race_times: LapTimes for race
            config: RatioConfig with calculation parameters
            current_qual: Current QualRatio value
            current_race: Current RaceRatio value
            
        Returns:
            CalculatedRatios object with results and details
        """
        result = CalculatedRatios()
        
        # Calculate QualRatio
        if qual_times.are_valid():
            qual_ratio, qual_error, qual_details = RatioCalculator.calculate_single_ratio(
                qual_times, config, current_qual
            )
            result.qual_ratio = qual_ratio
            result.qual_error = qual_error
            result.qual_details = qual_details
        else:
            result.qual_error = "Incomplete qualifying times"
        
        # Calculate RaceRatio
        if race_times.are_valid():
            race_ratio, race_error, race_details = RatioCalculator.calculate_single_ratio(
                race_times, config, current_race
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
        'percent_ratio'
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
                'percent_ratio': config.percent_ratio
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
        return minutes * 60 + seconds + milliseconds / 1000.0
    
    @staticmethod
    def format_time(seconds: float) -> str:
        """Format time as mm:ss.ms for display"""
        minutes, secs, ms = TimeConverter.seconds_to_mmssms(seconds)
        return f"{minutes}:{secs:02d}.{ms:03d}"
