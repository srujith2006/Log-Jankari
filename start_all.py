"""
Master Launcher Script - Starts all services simultaneously
Runs: app.py (Detection), gps_server.py (GPS), web_server.py (Website)
"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.absolute()

# Service configurations
SERVICES = {
    'GPS Server': {
        'script': 'gps_server.py',
        'description': '📍 GPS Location Server',
        'port': 8888,
        'delay': 1
    },
    'Detection Backend': {
        'script': 'app.py',
        'description': '🎥 Video Detection & Survivor Detection',
        'port': None,
        'delay': 3
    },
    'Web Server': {
        'script': 'web_server.py',
        'description': '🌐 Website (Register/Identify/Admin)',
        'port': 5000,
        'delay': 5
    }
}

# Store process handles
processes = {}

def print_header():
    """Print startup header"""
    print("\n")
    print("=" * 70)
    print("🚀 MyVerse Survivor Detection System - Master Launcher")
    print("=" * 70)
    print("\nStarting all services...\n")

def start_service(name, config):
    """Start a single service in a separate process"""
    script_path = PROJECT_ROOT / config['script']
    
    if not script_path.exists():
        print(f"❌ {name}: File not found at {script_path}")
        return None
    
    print(f"⏳ {config['description']}")
    print(f"   Starting: {config['script']}")
    
    try:
        # Start process
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        processes[name] = process
        
        # Small delay between starts
        time.sleep(config['delay'])
        
        if process.poll() is None:  # Process is still running
            port_info = f" (Port: {config['port']})" if config['port'] else ""
            print(f"✅ {name} started successfully{port_info}\n")
            return process
        else:
            print(f"❌ {name} failed to start\n")
            return None
            
    except Exception as e:
        print(f"❌ {name} error: {e}\n")
        return None

def print_status():
    """Print current status of all services"""
    print("\n" + "=" * 70)
    print("📊 SERVICE STATUS")
    print("=" * 70)
    
    for name, process in processes.items():
        if process and process.poll() is None:
            status = "✅ Running"
        else:
            status = "❌ Stopped"
        print(f"{status} | {name}")
    
    print("=" * 70)
    print("\n📋 ACCESS POINTS:")
    print("  🌐 Website: http://localhost:5000")
    print("  📍 GPS Server: localhost:8888")
    print("  🎥 Detection: Running in background")
    print("\n💡 Tips:")
    print("  - Check http://localhost:5000 in your browser")
    print("  - All services run simultaneously")
    print("  - Close any service to stop it individually")
    print("  - Press Ctrl+C to stop all services")
    print("=" * 70 + "\n")

def monitor_services():
    """Monitor services and restart if they crash"""
    try:
        while True:
            time.sleep(5)
            
            for name, process in list(processes.items()):
                if process and process.poll() is not None:
                    print(f"\n⚠️  {name} has stopped!")
                    print(f"   Restart: python {SERVICES[name]['script']}")
            
            # Check if all services are still running
            all_running = all(
                p and p.poll() is None for p in processes.values()
            )
            
            if not all_running:
                print("\n⚠️  WARNING: Some services are not running!")
                print_status()
    
    except KeyboardInterrupt:
        pass

def shutdown_all():
    """Gracefully shutdown all services"""
    print("\n\n" + "=" * 70)
    print("🛑 Shutting down all services...")
    print("=" * 70)
    
    for name, process in processes.items():
        if process and process.poll() is None:
            print(f"⏹️  Stopping {name}...")
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"✅ {name} stopped")
            except subprocess.TimeoutExpired:
                print(f"⚠️  Force killing {name}...")
                process.kill()
            except Exception as e:
                print(f"❌ Error stopping {name}: {e}")
    
    print("\n✅ All services stopped")
    print("=" * 70 + "\n")

def main():
    """Main launcher function"""
    print_header()
    
    # Check if Python is available
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return False
    
    # Start all services
    for name, config in SERVICES.items():
        start_service(name, config)
    
    # Print status
    print_status()
    
    # Monitor services
    try:
        print("👀 Monitoring services (Press Ctrl+C to stop)...\n")
        monitor_services()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutdown signal received...")
    finally:
        shutdown_all()

if __name__ == '__main__':
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    
    try:
        main()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        shutdown_all()
        sys.exit(1)
