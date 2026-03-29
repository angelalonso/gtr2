#!/usr/bin/env python3
"""
Test Harness for Live AI Tuner
Launches the application with test configuration and simulates game behavior
Uses existing test data from ./test_mocks
"""

import os
import sys
import time
import yaml
import subprocess
import logging
import shutil
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LiveAITunerTestHarness:
    """Test harness for Live AI Tuner using existing test data"""
    
    def __init__(self, test_dir: str = "./test_mocks"):
        self.test_dir = Path(test_dir).absolute()
        self.app_process = None
        self.log_queue = queue.Queue()
        self.log_thread = None
        self.app_log_file = None
        
        # Paths (using existing structure)
        self.user_data_dir = self.test_dir / "UserData"
        self.log_results_dir = self.user_data_dir / "Log" / "Results"
        self.results_file = self.log_results_dir / "raceresults.txt"
        self.test_config_path = self.test_dir / "cfg_test.yml"
        self.app_logs_dir = self.test_dir / "app_logs"
        
        # Create logs directory
        self.app_logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Track information from existing data
        self.tracks = self._discover_tracks()
        
        # Default test scenario
        self.default_scenario = {
            "description": "Default test - user slightly faster than AI",
            "user_time": "1:56.500",
            "ai_best": "1:57.234",
            "ai_worst": "2:01.567",
            "track_index": 0
        }
        
        # Full test scenarios
        self.full_test_scenarios = [
            {
                "description": "User faster than AI - should decrease ratios",
                "user_time": "1:54.500",
                "ai_best": "1:57.234",
                "ai_worst": "2:01.567",
                "track_index": 0
            },
            {
                "description": "User slower than AI - should increase ratios",
                "user_time": "2:00.000",
                "ai_best": "1:57.234",
                "ai_worst": "2:01.567",
                "track_index": 0
            },
            {
                "description": "User close to AI - minor adjustment",
                "user_time": "1:57.500",
                "ai_best": "1:57.234",
                "ai_worst": "2:01.567",
                "track_index": 0
            },
            {
                "description": "Different track - Spa",
                "user_time": "2:20.000",
                "ai_best": "2:22.500",
                "ai_worst": "2:27.000",
                "track_index": 1 if len(self.tracks) > 1 else 0
            },
            {
                "description": "Different track - Silverstone",
                "user_time": "1:52.000",
                "ai_best": "1:54.000",
                "ai_worst": "1:58.000",
                "track_index": 2 if len(self.tracks) > 2 else 0
            }
        ]
    
    def _discover_tracks(self) -> List[Dict]:
        """Discover existing tracks from test_mocks/GameData/Locations"""
        tracks = []
        locations_dir = self.test_dir / "GameData" / "Locations"
        
        if not locations_dir.exists():
            logger.warning(f"Locations directory not found: {locations_dir}")
            return []
        
        for track_dir in locations_dir.iterdir():
            if track_dir.is_dir():
                # Find AIW files in the track directory
                aiw_files = list(track_dir.glob("*.AIW")) + list(track_dir.glob("*.aiw"))
                for aiw_file in aiw_files:
                    tracks.append({
                        "name": track_dir.name,
                        "folder": track_dir.name,
                        "aiw_file": aiw_file.name,
                        "aiw_path": aiw_file
                    })
                    logger.info(f"Discovered track: {track_dir.name} with AIW: {aiw_file.name}")
                    break  # Take first AIW file per track
        
        return tracks
    
    def create_test_config(self) -> bool:
        """Create test configuration pointing to existing test data"""
        logger.info("Creating test configuration...")
        
        test_config = {
            'base_path': str(self.test_dir),
            'formulas_dir': str(self.test_dir / 'track_formulas'),
            'auto_apply': False,
            'backup_enabled': True
        }
        
        try:
            with open(self.test_config_path, 'w') as f:
                yaml.dump(test_config, f, default_flow_style=False, indent=2)
            logger.info(f"  Created test config: {self.test_config_path}")
            logger.info(f"  Base path: {self.test_dir}")
            return True
        except Exception as e:
            logger.error(f"  Failed to create test config: {e}")
            return False
    
    def backup_original_results(self) -> bool:
        """Backup the original raceresults.txt if it exists"""
        if self.results_file.exists():
            backup_path = self.results_file.with_suffix('.txt.backup')
            try:
                shutil.copy2(self.results_file, backup_path)
                logger.info(f"  Backed up original results to: {backup_path}")
                return True
            except Exception as e:
                logger.error(f"  Failed to backup results: {e}")
                return False
        return True
    
    def restore_results(self) -> bool:
        """Restore the original raceresults.txt"""
        backup_path = self.results_file.with_suffix('.txt.backup')
        if backup_path.exists():
            try:
                shutil.copy2(backup_path, self.results_file)
                logger.info(f"  Restored original results from backup")
                return True
            except Exception as e:
                logger.error(f"  Failed to restore results: {e}")
                return False
        return True
    
    def _get_race_results_content(self, track: Dict, user_time: str, 
                                   ai_best: str, ai_worst: str, 
                                   user_name: str = "TestDriver") -> str:
        """Generate race results file content"""
        aiw_filename = track["aiw_file"]
        trk_filename = aiw_filename.replace('.AIW', '.TRK').replace('.aiw', '.trk')
        
        return f"""[Race]
Scene=GAMEDATA\\LOCATIONS\\{track["folder"]}\\{trk_filename}
AIDB=GAMEDATA\\LOCATIONS\\{track["folder"]}\\{aiw_filename}
DamageModel=1
Flags=1
StartLine=1
NumLaps=3

[Slot0]
Driver={user_name}
Vehicle=Test_Car
Team=Test_Team
QualTime={user_time}
BestLap={user_time}
Laps=3
Position=1
Class=1

[Slot1]
Driver=AI_Driver_1
Team=AI_Team_1
QualTime={ai_best}
BestLap={ai_best}
Laps=3
Position=2
Class=1

[Slot2]
Driver=AI_Driver_2
Team=AI_Team_2
QualTime={ai_worst}
BestLap={ai_worst}
Laps=3
Position=3
Class=1

[END]
"""
    
    def simulate_race(self, scenario: Dict, wait_before: float = 1.0) -> bool:
        """Simulate a race by modifying the results file"""
        if not self.tracks:
            logger.error("No tracks discovered")
            return False
        
        track_index = scenario.get("track_index", 0)
        if track_index >= len(self.tracks):
            logger.warning(f"Track index {track_index} out of range, using first track")
            track_index = 0
        
        track = self.tracks[track_index]
        
        # Generate content
        content = self._get_race_results_content(
            track,
            scenario["user_time"],
            scenario["ai_best"],
            scenario["ai_worst"]
        )
        
        # Wait if requested
        if wait_before > 0:
            time.sleep(wait_before)
        
        # Write to file (this will trigger the file monitor)
        logger.info(f"  Writing race results for {track['name']}...")
        logger.info(f"  User time: {scenario['user_time']}, AI best: {scenario['ai_best']}, AI worst: {scenario['ai_worst']}")
        try:
            with open(self.results_file, 'w') as f:
                f.write(content)
            
            # Update file modification time to ensure it's detected
            os.utime(self.results_file, None)
            logger.info(f"  ✓ Results written successfully")
            return True
        except Exception as e:
            logger.error(f"  Failed to write results: {e}")
            return False
    
    def _log_reader_thread(self, pipe, log_file, source_name):
        """Thread to read from a pipe and log to file and queue"""
        try:
            for line in iter(pipe.readline, ''):
                if line:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    formatted_line = f"[{timestamp}] [{source_name}] {line.rstrip()}"
                    
                    # Add to queue for real-time display
                    self.log_queue.put(formatted_line)
                    
                    # Write to log file
                    log_file.write(formatted_line + '\n')
                    log_file.flush()
                    
                    # Also print to console with appropriate coloring
                    if "ERROR" in line or "CRITICAL" in line:
                        print(f"\033[91m{formatted_line}\033[0m")  # Red
                    elif "WARNING" in line:
                        print(f"\033[93m{formatted_line}\033[0m")  # Yellow
                    elif "INFO" in line:
                        print(f"\033[92m{formatted_line}\033[0m")  # Green
                    else:
                        print(formatted_line)
        except Exception as e:
            logger.error(f"Log reader thread error for {source_name}: {e}")
    
    def launch_application(self, no_gui: bool = False) -> bool:
        """Launch the Live AI Tuner application and capture logs"""
        logger.info("Launching Live AI Tuner...")
        
        # Create a log file for this run
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.app_log_file = self.app_logs_dir / f"app_log_{timestamp}.txt"
        
        # Get the path to dyn_ai.py
        script_dir = Path(__file__).parent
        app_script = script_dir / "dyn_ai.py"
        
        if not app_script.exists():
            logger.error(f"Application script not found: {app_script}")
            return False
        
        # Build command
        cmd = [
            sys.executable,
            "-u",  # Unbuffered output
            str(app_script),
            "--config", str(self.test_config_path)
        ]
        
        if no_gui:
            cmd.append("--no-gui")
            logger.info("  Running in console mode")
        
        try:
            # Start the process with pipes for stdout and stderr
            self.app_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=os.environ.copy()  # Pass through environment
            )
            
            # Open log file
            log_file = open(self.app_log_file, 'w', encoding='utf-8')
            log_file.write(f"=== Live AI Tuner Log - {datetime.now().isoformat()} ===\n")
            log_file.write(f"Command: {' '.join(cmd)}\n")
            log_file.write(f"PID: {self.app_process.pid}\n")
            log_file.write("=" * 80 + "\n\n")
            
            # Start log reader threads
            stdout_thread = threading.Thread(
                target=self._log_reader_thread,
                args=(self.app_process.stdout, log_file, "STDOUT"),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=self._log_reader_thread,
                args=(self.app_process.stderr, log_file, "STDERR"),
                daemon=True
            )
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Store log file and threads for cleanup
            self.log_file_handle = log_file
            self.log_threads = (stdout_thread, stderr_thread)
            
            # Wait for application to initialize
            logger.info("  Waiting for application to initialize...")
            time.sleep(3)
            
            # Check if process is still running
            if self.app_process.poll() is not None:
                # Process died, read any remaining output
                time.sleep(1)  # Give threads time to capture output
                logger.error(f"  ❌ Application exited immediately with code {self.app_process.returncode}")
                logger.error(f"  Check log file for details: {self.app_log_file}")
                
                # Display last few lines from log
                self._display_recent_logs()
                return False
            
            logger.info(f"  ✓ Application launched with PID: {self.app_process.pid}")
            logger.info(f"  ✓ Log file: {self.app_log_file}")
            return True
            
        except Exception as e:
            logger.error(f"  Failed to launch application: {e}")
            return False
    
    def _display_recent_logs(self, lines: int = 20):
        """Display recent lines from the log file"""
        if not self.app_log_file or not self.app_log_file.exists():
            return
        
        logger.error(f"\n  Recent logs from {self.app_log_file}:")
        logger.error("  " + "-" * 50)
        
        try:
            with open(self.app_log_file, 'r') as f:
                all_lines = f.readlines()
                recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
                for line in recent:
                    line = line.strip()
                    if line:
                        logger.error(f"    {line}")
        except Exception as e:
            logger.error(f"    Could not read log file: {e}")
    
    def stop_application(self):
        """Stop the application gracefully and capture final logs"""
        if self.app_process:
            logger.info("Stopping application...")
            
            # Try graceful termination
            self.app_process.terminate()
            
            try:
                self.app_process.wait(timeout=5)
                logger.info("  Application stopped gracefully")
            except subprocess.TimeoutExpired:
                logger.warning("  Application didn't terminate, killing...")
                self.app_process.kill()
                self.app_process.wait()
                logger.info("  Application killed")
            
            # Give log threads a moment to finish
            time.sleep(1)
            
            # Close log file
            if hasattr(self, 'log_file_handle'):
                self.log_file_handle.write("\n" + "=" * 80 + "\n")
                self.log_file_handle.write(f"=== Application stopped at {datetime.now().isoformat()} ===\n")
                self.log_file_handle.close()
            
            # Display summary of errors if any
            self._check_for_errors_in_log()
            
            self.app_process = None
    
    def _check_for_errors_in_log(self):
        """Check the log file for errors and display summary"""
        if not self.app_log_file or not self.app_log_file.exists():
            return
        
        errors = []
        warnings = []
        
        try:
            with open(self.app_log_file, 'r') as f:
                for line in f:
                    if "ERROR" in line or "CRITICAL" in line:
                        errors.append(line.strip())
                    elif "WARNING" in line:
                        warnings.append(line.strip())
            
            if errors:
                logger.warning(f"\n  Found {len(errors)} errors in log:")
                for error in errors[-5:]:  # Show last 5 errors
                    logger.warning(f"    {error}")
            
            if warnings:
                logger.info(f"  Found {len(warnings)} warnings in log")
                
        except Exception as e:
            logger.error(f"  Could not check log for errors: {e}")
    
    def run_integration_tests(self) -> bool:
        """Run integration tests to verify setup"""
        logger.info("\n" + "=" * 60)
        logger.info("Running Integration Tests")
        logger.info("=" * 60)
        
        try:
            # Test 1: Check if tracks exist
            logger.info("\n[Test 1] Checking test data...")
            if not self.tracks:
                logger.error("  No tracks found in test data")
                return False
            logger.info(f"  ✓ Found {len(self.tracks)} tracks:")
            for track in self.tracks:
                logger.info(f"    - {track['name']}: {track['aiw_file']}")
            
            # Test 2: Check results file location
            logger.info("\n[Test 2] Checking results file location...")
            if not self.log_results_dir.exists():
                logger.error(f"  Results directory not found: {self.log_results_dir}")
                return False
            logger.info(f"  ✓ Results directory exists: {self.log_results_dir}")
            
            # Test 3: Import and test AIW manager
            logger.info("\n[Test 3] Testing AIWManager...")
            try:
                from aiw_manager import AIWManager
                aiw_manager = AIWManager(self.test_dir / 'backups')
                
                # Try to read the first track's AIW file
                if self.tracks:
                    track = self.tracks[0]
                    qual, race = aiw_manager.read_ratios(track['aiw_path'])
                    logger.info(f"  ✓ Read {track['name']} ratios: Qual={qual}, Race={race}")
            except Exception as e:
                logger.error(f"  AIWManager test failed: {e}")
                return False
            
            # Test 4: Test results parser
            logger.info("\n[Test 4] Testing Results Parser...")
            try:
                from results_parser import parse_race_results
                if self.results_file.exists():
                    results = parse_race_results(self.results_file, self.test_dir)
                    if results and results.track_name:
                        logger.info(f"  ✓ Parsed track: {results.track_name}")
                        logger.info(f"  ✓ User time: {results.user_best_lap}")
                    else:
                        logger.warning("  Results file exists but couldn't parse")
                else:
                    logger.warning("  Results file not found, creating initial file...")
                    # Create initial results file
                    if self.tracks:
                        initial_content = self._get_race_results_content(
                            self.tracks[0],
                            "1:55.000",
                            "1:57.000",
                            "2:02.000"
                        )
                        with open(self.results_file, 'w') as f:
                            f.write(initial_content)
                        logger.info("  ✓ Created initial results file")
            except Exception as e:
                logger.error(f"  Results parser test failed: {e}")
                return False
            
            logger.info("\n" + "=" * 60)
            logger.info("✓ All integration tests passed!")
            logger.info("=" * 60)
            return True
            
        except Exception as e:
            logger.error(f"Integration test failed: {e}", exc_info=True)
            return False
    
    def run_user_interactive_test(self):
        """Run user-interactive test - single change after 5 seconds"""
        logger.info("\n" + "=" * 60)
        logger.info("User-Interactive Test Mode")
        logger.info("=" * 60)
        logger.info("This will:")
        logger.info("  1. Launch the application")
        logger.info("  2. Wait 5 seconds")
        logger.info("  3. Make ONE change to raceresults.txt")
        logger.info("  4. Keep application running for you to observe")
        logger.info("=" * 60)
        
        # Create test configuration
        if not self.create_test_config():
            logger.error("Failed to create test configuration")
            return False
        
        # Backup original results file
        self.backup_original_results()
        
        # Run integration tests
        if not self.run_integration_tests():
            logger.error("Integration tests failed")
            return False
        
        # Launch the application
        if not self.launch_application(no_gui=False):
            logger.error("Failed to launch application")
            return False
        
        try:
            # Wait 5 seconds
            logger.info("\nWaiting 5 seconds before making change...")
            for i in range(5, 0, -1):
                logger.info(f"  {i}...")
                time.sleep(1)
            
            # Make one change
            logger.info("\nMaking ONE change to raceresults.txt...")
            track_name = self.tracks[self.default_scenario["track_index"]]['name']
            logger.info(f"  Simulating race at {track_name}")
            self.simulate_race(self.default_scenario, wait_before=0)
            
            logger.info("\n" + "=" * 60)
            logger.info("✓ Test change complete!")
            logger.info("Application is now running and monitoring.")
            logger.info(f"Log file: {self.app_log_file}")
            logger.info("Press Enter to stop the application...")
            logger.info("=" * 60)
            
            input()
            
        except KeyboardInterrupt:
            logger.info("\nTest interrupted by user")
        finally:
            self.stop_application()
            self.restore_results()
        
        return True
    
    def run_full_test(self):
        """Run full test with multiple race simulations"""
        logger.info("\n" + "=" * 60)
        logger.info("Full Test Mode - Multiple Race Simulations")
        logger.info("=" * 60)
        
        # Create test configuration
        if not self.create_test_config():
            logger.error("Failed to create test configuration")
            return False
        
        # Backup original results file
        self.backup_original_results()
        
        # Run integration tests
        if not self.run_integration_tests():
            logger.error("Integration tests failed")
            return False
        
        # Launch the application
        if not self.launch_application(no_gui=False):
            logger.error("Failed to launch application")
            return False
        
        try:
            # Wait for application to be ready
            logger.info("\nWaiting 3 seconds for application to stabilize...")
            time.sleep(3)
            
            # Run through all scenarios
            for i, scenario in enumerate(self.full_test_scenarios, 1):
                if i > 1:
                    logger.info(f"\nWaiting 5 seconds before next scenario...")
                    time.sleep(5)
                
                logger.info(f"\n[Scenario {i}/{len(self.full_test_scenarios)}] {scenario['description']}")
                
                # Get track name
                track_idx = scenario.get("track_index", 0)
                track_name = self.tracks[track_idx]['name'] if track_idx < len(self.tracks) else "Unknown"
                logger.info(f"  Track: {track_name}")
                
                # Simulate the race
                self.simulate_race(scenario, wait_before=2)
            
            logger.info("\n" + "=" * 60)
            logger.info("✓ Full test complete!")
            logger.info(f"Log file: {self.app_log_file}")
            logger.info("Application is still running. Press Enter to stop...")
            logger.info("=" * 60)
            
            input()
            
        except KeyboardInterrupt:
            logger.info("\nTest interrupted by user")
        finally:
            self.stop_application()
            self.restore_results()
        
        return True


def countdown_timer(seconds: int, message: str):
    """Display a countdown timer"""
    for i in range(seconds, 0, -1):
        print(f"\r{message} {i}... ", end="", flush=True)
        time.sleep(1)
    print()


def main():
    """Main entry point with timeout selection"""
    print("\n" + "=" * 60)
    print("Live AI Tuner Test Harness")
    print("=" * 60)
    print("\nSelect test mode:")
    print("  1. User-interactive test (default) - one change after 5 seconds")
    print("  2. Full test - multiple race simulations")
    print("  3. Integration tests only")
    print("\nDefault option (1) will be selected in 3 seconds...")
    print("=" * 60)
    
    # Countdown for default selection
    choice = None
    timeout = 3
    
    print("\nEnter choice (1-3) or press Enter for default: ", end="", flush=True)
    
    # Use a simpler approach with threading for cross-platform compatibility
    import threading
    
    user_input = [None]
    
    def get_input():
        try:
            user_input[0] = sys.stdin.readline().strip()
        except:
            pass
    
    input_thread = threading.Thread(target=get_input)
    input_thread.daemon = True
    input_thread.start()
    
    # Wait for input or timeout
    for i in range(timeout, 0, -1):
        if user_input[0] is not None:
            break
        print(f"\rEnter choice (1-3) or press Enter for default: (waiting {i}s) ", end="", flush=True)
        time.sleep(1)
    
    if user_input[0] is not None:
        choice = user_input[0]
    else:
        print("\n")
        choice = "1"  # Default to user-interactive
    
    # Process choice
    harness = LiveAITunerTestHarness()
    
    if choice == "1" or choice == "":
        print("\nRunning user-interactive test...")
        success = harness.run_user_interactive_test()
    elif choice == "2":
        print("\nRunning full test...")
        success = harness.run_full_test()
    elif choice == "3":
        print("\nRunning integration tests only...")
        harness.create_test_config()
        success = harness.run_integration_tests()
    else:
        print(f"\nInvalid choice: {choice}")
        print("Running user-interactive test (default)...")
        success = harness.run_user_interactive_test()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
