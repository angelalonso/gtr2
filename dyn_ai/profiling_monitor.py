#!/usr/bin/env python3
"""External monitor - attach to running process by name"""

import psutil
import time
import csv
from datetime import datetime

def monitor_by_name(process_name, duration=300, interval=0.5, output="metrics.csv"):
    """Monitor a process by name (e.g., 'python')"""
    
    target_pid = None
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if process_name in proc.info['name'].lower():
            # Find your specific script
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'dyn_ai' in cmdline or 'live_ai' in cmdline:
                target_pid = proc.info['pid']
                break
    
    if not target_pid:
        print(f"Process '{process_name}' not found. Start your program first.")
        return
    
    proc = psutil.Process(target_pid)
    print(f"Monitoring PID {target_pid} for {duration}s...")
    
    with open(output, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'cpu_percent', 'memory_rss_mb', 'memory_percent', 'threads'])
        
        start = time.time()
        while time.time() - start < duration:
            try:
                mem = proc.memory_info()
                writer.writerow([
                    datetime.now().isoformat(),
                    proc.cpu_percent(interval=0.1),
                    mem.rss / 1024 / 1024,
                    proc.memory_percent(),
                    proc.num_threads()
                ])
                time.sleep(interval)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
    
    print(f"Saved to {output}")

if __name__ == "__main__":
    monitor_by_name("python", duration=300, interval=0.5)
