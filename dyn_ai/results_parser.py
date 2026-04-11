"""
Race Results Parser - Extracts lap times and driver info from raceresults.txt

Slot 000 = user player  →  stored on RaceResults directly
Slot 001+ = AI drivers  →  stored in RaceResults.ai_results (one dict each)

Each AI result dict contains:
    name, vehicle, team,
    qual_time, qual_time_sec,
    best_lap, best_lap_sec,
    race_time, race_time_sec,
    laps
"""

import re
import logging
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── Pre-compiled patterns ──────────────────────────────────────────────────────

_SCENE_PATTERN      = re.compile(r'Scene=(.*?)(?:\n|$)',    re.IGNORECASE)
_AIDB_PATTERN       = re.compile(r'AIDB=(.*?)(?:\n|$)',     re.IGNORECASE)
_SLOT_PATTERN       = re.compile(r'\[Slot(\d+)\](.*?)(?=\[Slot|\[END\]|$)', re.DOTALL)
_DRIVER_PATTERN     = re.compile(r'Driver=(.*?)(?:\n|$)',   re.IGNORECASE)
_VEHICLE_PATTERN    = re.compile(r'Vehicle=(.*?)(?:\n|$)',  re.IGNORECASE)
_TEAM_PATTERN       = re.compile(r'Team=(.*?)(?:\n|$)',     re.IGNORECASE)
_QUAL_TIME_PATTERN  = re.compile(r'QualTime=(.*?)(?:\n|$)', re.IGNORECASE)
_BEST_LAP_PATTERN   = re.compile(r'BestLap=(.*?)(?:\n|$)', re.IGNORECASE)
_RACE_TIME_PATTERN  = re.compile(r'RaceTime=(.*?)(?:\n|$)', re.IGNORECASE)
_LAPS_PATTERN       = re.compile(r'Laps=(.*?)(?:\n|$)',     re.IGNORECASE)


# ── Data class ─────────────────────────────────────────────────────────────────

@dataclass
class RaceResults:
    """Container for one parsed raceresults.txt"""

    # Track / file metadata
    track_name:   Optional[str]  = None
    track_folder: Optional[str]  = None
    aiw_file:     Optional[str]  = None
    aiw_path:     Optional[Path] = None
    qual_ratio:   Optional[float] = None
    race_ratio:   Optional[float] = None

    # User result (Slot000)
    user_name:            Optional[str]   = None
    user_vehicle:         Optional[str]   = None
    user_team:            Optional[str]   = None
    user_best_lap:        Optional[str]   = None
    user_best_lap_sec:    float           = 0.0
    user_qualifying:      Optional[str]   = None
    user_qualifying_sec:  float           = 0.0
    user_race_time:       Optional[str]   = None
    user_laps:            Optional[int]   = None

    # All AI results (Slot001+)
    ai_results: List[Dict] = field(default_factory=list)
    
    # Computed AI stats (populated after parsing)
    qual_best_ai_lap: Optional[str] = None
    qual_best_ai_lap_sec: float = 0.0
    qual_worst_ai_lap: Optional[str] = None
    qual_worst_ai_lap_sec: float = 0.0
    best_ai_lap: Optional[str] = None
    best_ai_lap_sec: float = 0.0
    worst_ai_lap: Optional[str] = None
    worst_ai_lap_sec: float = 0.0

    def has_data(self) -> bool:
        return bool(self.ai_results or self.user_best_lap or self.user_qualifying)

    def _compute_ai_stats(self):
        """Calculate fastest and slowest AI times from ai_results"""
        if not self.ai_results:
            return
        
        # Qualifying stats
        qual_times = []
        for ai in self.ai_results:
            qual_sec = ai.get('qual_time_sec')
            if qual_sec and qual_sec > 0:
                qual_times.append((qual_sec, ai))
        
        if qual_times:
            qual_times.sort(key=lambda x: x[0])
            # Fastest (smallest time)
            fastest_qual_sec, fastest_qual_ai = qual_times[0]
            self.qual_best_ai_lap_sec = fastest_qual_sec
            self.qual_best_ai_lap = fastest_qual_ai.get('qual_time')
            
            # Slowest (largest time)
            slowest_qual_sec, slowest_qual_ai = qual_times[-1]
            self.qual_worst_ai_lap_sec = slowest_qual_sec
            self.qual_worst_ai_lap = slowest_qual_ai.get('qual_time')
        
        # Race stats (using best_lap_sec, not race_time)
        race_times = []
        for ai in self.ai_results:
            best_sec = ai.get('best_lap_sec')
            if best_sec and best_sec > 0:
                race_times.append((best_sec, ai))
        
        if race_times:
            race_times.sort(key=lambda x: x[0])
            # Fastest (smallest time)
            fastest_race_sec, fastest_race_ai = race_times[0]
            self.best_ai_lap_sec = fastest_race_sec
            self.best_ai_lap = fastest_race_ai.get('best_lap')
            
            # Slowest (largest time)
            slowest_race_sec, slowest_race_ai = race_times[-1]
            self.worst_ai_lap_sec = slowest_race_sec
            self.worst_ai_lap = slowest_race_ai.get('best_lap')

    def to_dict(self) -> dict:
        # Compute stats before returning dict
        self._compute_ai_stats()
        
        return {
            # track / file
            "track_name":           self.track_name,
            "track_folder":         self.track_folder,
            "aiw_file":             self.aiw_file,
            "qual_ratio":           self.qual_ratio,
            "race_ratio":           self.race_ratio,
            # user
            "user_name":            self.user_name,
            "user_vehicle":         self.user_vehicle,
            "user_team":            self.user_team,
            "user_best_lap":        self.user_best_lap,
            "user_best_lap_sec":    self.user_best_lap_sec,
            "user_qualifying":      self.user_qualifying,
            "user_qualifying_sec":  self.user_qualifying_sec,
            "user_race_time":       self.user_race_time,
            "user_laps":            self.user_laps,
            # AI computed stats
            "qual_best_ai_lap":     self.qual_best_ai_lap,
            "qual_best_ai_lap_sec": self.qual_best_ai_lap_sec,
            "qual_worst_ai_lap":    self.qual_worst_ai_lap,
            "qual_worst_ai_lap_sec": self.qual_worst_ai_lap_sec,
            "best_ai_lap":          self.best_ai_lap,
            "best_ai_lap_sec":      self.best_ai_lap_sec,
            "worst_ai_lap":         self.worst_ai_lap,
            "worst_ai_lap_sec":     self.worst_ai_lap_sec,
            # AI — full list
            "ai_results":           self.ai_results,
        }


# ── Public parse function ──────────────────────────────────────────────────────

def parse_race_results(file_path: Path, base_path: Optional[Path] = None) -> Optional[RaceResults]:
    """Parse raceresults.txt and return a RaceResults object, or None on error."""
    try:
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        results = RaceResults()

        # ── Header: track name and AIW path ───────────────────────────────────
        race_match = re.search(r'\[Race\](.*?)(?=\[|$)', content, re.DOTALL)
        if race_match:
            race_section = race_match.group(1)

            scene_match = _SCENE_PATTERN.search(race_section)
            if scene_match:
                scene = scene_match.group(1).strip()
                scene_path = Path(scene.replace('\\', '/'))
                results.track_folder = scene_path.parent.name
                track_name = scene_path.stem
                track_name = re.sub(r'^\d+', '', track_name)   # strip leading digits
                results.track_name = track_name
                logger.info(f"Track: {results.track_name}  (folder: {results.track_folder})")

            aiw_match = _AIDB_PATTERN.search(race_section)
            if aiw_match:
                aiw_path_str = aiw_match.group(1).strip()
                results.aiw_path = Path(aiw_path_str.replace('\\', '/'))
                results.aiw_file = results.aiw_path.name   # e.g. "4Monza.AIW"
                logger.info(f"AIW: {results.aiw_file}")

        # ── Driver slots ──────────────────────────────────────────────────────
        for slot_str, slot_content in _SLOT_PATTERN.findall(content):
            slot = int(slot_str)

            name    = _extract(slot_content, _DRIVER_PATTERN)
            vehicle = _extract(slot_content, _VEHICLE_PATTERN)
            team    = _extract(slot_content, _TEAM_PATTERN)
            qual    = _extract(slot_content, _QUAL_TIME_PATTERN)
            best    = _extract(slot_content, _BEST_LAP_PATTERN)
            rtime   = _extract(slot_content, _RACE_TIME_PATTERN)
            laps_s  = _extract(slot_content, _LAPS_PATTERN)

            laps = int(laps_s) if laps_s and laps_s.isdigit() else None

            if slot == 0:
                # ── User ──────────────────────────────────────────────────────
                results.user_name    = name
                results.user_vehicle = vehicle
                results.user_team    = team
                results.user_best_lap       = best
                results.user_best_lap_sec   = _to_sec(best) or 0.0
                results.user_qualifying     = qual
                results.user_qualifying_sec = _to_sec(qual) or 0.0
                results.user_race_time      = rtime
                results.user_laps           = laps
                logger.info(
                    f"User: {name}  vehicle={vehicle}  "
                    f"qual={qual}  best={best}  race={rtime}  laps={laps}"
                )
            else:
                # ── AI driver ─────────────────────────────────────────────────
                ai = {
                    "name":         name,
                    "vehicle":      vehicle,
                    "team":         team,
                    "qual_time":    qual,
                    "qual_time_sec": _to_sec(qual),
                    "best_lap":     best,
                    "best_lap_sec": _to_sec(best),
                    "race_time":    rtime,
                    "race_time_sec": _to_sec(rtime),
                    "laps":         laps,
                }
                results.ai_results.append(ai)

        logger.info(
            f"Parsed {len(results.ai_results)} AI drivers  "
            f"(user: {results.user_name}, best: {results.user_best_lap})"
        )
        
        # Log AI stats for debugging
        results._compute_ai_stats()
        logger.info(f"AI Qualifying - Best: {results.qual_best_ai_lap} ({results.qual_best_ai_lap_sec:.3f}s), "
                   f"Worst: {results.qual_worst_ai_lap} ({results.qual_worst_ai_lap_sec:.3f}s)")
        logger.info(f"AI Race - Best: {results.best_ai_lap} ({results.best_ai_lap_sec:.3f}s), "
                   f"Worst: {results.worst_ai_lap} ({results.worst_ai_lap_sec:.3f}s)")

        # ── AIW ratios ────────────────────────────────────────────────────────
        if results.aiw_file and base_path:
            _parse_aiw_ratios(results, base_path)

        return results

    except Exception as e:
        logger.error(f"Error parsing race results: {e}", exc_info=True)
        return None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract(text: str, pattern: re.Pattern) -> Optional[str]:
    """Return the first captured group from *pattern* in *text*, stripped."""
    m = pattern.search(text)
    return m.group(1).strip() if m else None


def _to_sec(time_str: Optional[str]) -> Optional[float]:
    """
    Convert a time string to total seconds.

    Accepts:
        "1:54.027"      →  114.027
        "0:17:06.061"   →  1026.061   (h:mm:ss.ms format used by RaceTime)
        "94.027"        →  94.027
    """
    if not time_str:
        return None
    time_str = time_str.strip()
    try:
        parts = time_str.split(':')
        if len(parts) == 3:
            # h:mm:ss.ms  (RaceTime)
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:
            # m:ss.ms  (lap times)
            return int(parts[0]) * 60 + float(parts[1])
        else:
            return float(time_str)
    except (ValueError, IndexError):
        return None


# ── AIW ratio parsing (unchanged logic) ───────────────────────────────────────

_AIW_CACHE: dict = {}
_CACHE_MAX_SIZE = 50


def _parse_aiw_ratios(results: RaceResults, base_path: Path) -> None:
    import os
    track_folder = results.track_folder or results.track_name
    cache_key = f"{track_folder}_{results.aiw_file}"

    if cache_key in _AIW_CACHE:
        aiw_path = _AIW_CACHE[cache_key]
    else:
        aiw_path = _find_aiw_file(results.aiw_file, track_folder, base_path)
        if aiw_path:
            if len(_AIW_CACHE) >= _CACHE_MAX_SIZE:
                _AIW_CACHE.pop(next(iter(_AIW_CACHE)))
            _AIW_CACHE[cache_key] = aiw_path

    if not aiw_path or not aiw_path.exists():
        logger.warning(f"AIW file not found: {results.aiw_file}")
        return

    try:
        with open(aiw_path, 'rb') as f:
            raw = f.read()
        content = raw.replace(b'\x00', b'').decode('utf-8', errors='ignore')

        wp = re.search(r'\[Waypoint\](.*?)(?=\[|$)', content, re.DOTALL | re.IGNORECASE)
        if wp:
            section = wp.group(1)
            qm = re.search(r'QualRatio\s*=\s*\(?([\d.]+)\)?', section, re.IGNORECASE)
            if qm:
                results.qual_ratio = float(qm.group(1))
            rm = re.search(r'RaceRatio\s*=\s*\(?([\d.]+)\)?', section, re.IGNORECASE)
            if rm:
                results.race_ratio = float(rm.group(1))

        logger.info(f"Ratios — Qual: {results.qual_ratio}  Race: {results.race_ratio}")
    except Exception as e:
        logger.error(f"Error parsing AIW ratios: {e}")


def _find_aiw_file(aiw_filename: str, track_folder: str, base_path: Path) -> Optional[Path]:
    import os
    locations_path = base_path / 'GameData' / 'Locations'
    if not locations_path.exists():
        return None

    filename_norm = Path(aiw_filename).name

    if track_folder:
        for folder in locations_path.iterdir():
            if folder.is_dir() and folder.name.lower() == track_folder.lower():
                for f in folder.iterdir():
                    if f.is_file() and f.name.lower() == filename_norm.lower():
                        return f
                for ext in ['.AIW', '.aiw']:
                    c = folder / f"{folder.name}{ext}"
                    if c.exists():
                        return c
                for g in ['*.AIW', '*.aiw']:
                    hits = list(folder.glob(g))
                    if hits:
                        return hits[0]

    for root, _, files in os.walk(locations_path):
        for f in files:
            if f.lower() == filename_norm.lower():
                return Path(root) / f

    return None
