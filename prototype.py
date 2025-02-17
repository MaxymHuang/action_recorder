import cv2
import numpy as np
import mss
import time
import threading
import json
from pathlib import Path
from pynput import keyboard, mouse
import pyautogui
# Make win32api import optional
try:
    import win32api
    HAS_WIN32API = True
except ImportError:
    HAS_WIN32API = False

# Disable PyAutoGUI's failsafe and increase speed
pyautogui.FAILSAFE = False
pyautogui.MINIMUM_DURATION = 0  # Remove minimum movement time
pyautogui.PAUSE = 0  # Remove pause between actions
from typing import Dict, List, Optional
from queue import Queue, Empty  # Add Empty to imports
from threading import Lock
from datetime import datetime  # Add datetime to imports

# Configuration
CONFIG = {
    "fps": 15,
    "video_format": "XVID",
    "output_dir": "recordings",
    "screen_region": None,  # None for full screen, or (x, y, width, height)
    "monitor_number": 1     # Default to primary monitor
}

# Global variables
events: List[Dict] = []
start_time: float = 0
is_paused: bool = False
pause_start_time: Optional[float] = None
total_pause_duration: float = 0
events_queue = Queue()
events_lock = Lock()

def ensure_output_directory():
    Path(CONFIG["output_dir"]).mkdir(parents=True, exist_ok=True)

def get_timestamp_filename(prefix: str, ext: str) -> str:
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return f"{CONFIG['output_dir']}/{prefix}_{timestamp}.{ext}"

def save_events(filename: str):
    with open(filename, 'w') as f:
        json.dump(events, f, indent=2)

def load_events(filename: str) -> List[Dict]:
    with open(filename, 'r') as f:
        return json.load(f)

def validate_screen_position(x: int, y: int) -> tuple:
    screen_width, screen_height = pyautogui.size()
    x = max(0, min(x, screen_width - 1))
    y = max(0, min(y, screen_height - 1))
    return (x, y)

def record_screen(stop_event: threading.Event, pause_event: threading.Event):
    sct = mss.mss()
    
    try:
        # Use selected monitor or region
        if CONFIG["screen_region"]:
            monitor = CONFIG["screen_region"]
        else:
            # Add 1 because mss.monitors[0] is the "all in one" monitor
            monitor = sct.monitors[CONFIG["monitor_number"]]
        
        width = monitor["width"]
        height = monitor["height"]
        
        filename = get_timestamp_filename("screen", "avi")
        fourcc = cv2.VideoWriter_fourcc(*CONFIG["video_format"])
        out = cv2.VideoWriter(filename, fourcc, CONFIG["fps"], (width, height))
        
        frames_captured = 0
        last_frame_time = time.time()
        
        while not stop_event.is_set():
            if not pause_event.is_set():
                current_time = time.time()
                frame_delta = current_time - last_frame_time
                
                if frame_delta >= 1/CONFIG["fps"]:
                    img = sct.grab(monitor)
                    frame = np.array(img)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    out.write(frame)
                    frames_captured += 1
                    last_frame_time = current_time
    except Exception as e:
        print(f"Error during recording: {e}")
    finally:
        try:
            out.release()
        except:
            pass
        print(f"Recorded {frames_captured} frames to {filename}")

def toggle_pause(pause_event: threading.Event):
    global is_paused, pause_start_time, total_pause_duration
    if not is_paused:
        pause_event.set()
        pause_start_time = time.time()
        print("\nRecording paused...")
    else:
        pause_event.clear()
        total_pause_duration += time.time() - (pause_start_time or 0)
        print("Recording resumed...")
    is_paused = not is_paused

def process_event(event_data: Dict):
    """Thread-safe event processing"""
    global events
    with events_lock:
        events.append(event_data)

def on_press(key):
    if is_paused:
        return
    try:
        k = key.char if hasattr(key, 'char') and key.char is not None else str(key)
    except Exception:
        k = str(key)
    events_queue.put({
        "type": "keyboard",
        "event": "press",
        "key": k,
        "time": time.time() - start_time - total_pause_duration
    })

def on_release(key):
    if is_paused:
        return
    try:
        k = key.char if key.char is not None else str(key)
    except Exception:
        k = str(key)
    events_queue.put({
        "type": "keyboard",
        "event": "release",
        "key": k,
        "time": time.time() - start_time - total_pause_duration
    })

def on_move(x, y):
    if is_paused:
        return
    events_queue.put({
        "type": "mouse",
        "event": "move",
        "position": (x, y),
        "time": time.time() - start_time - total_pause_duration
    })

def on_click(x, y, button, pressed):
    if is_paused:
        return
    events_queue.put({
        "type": "mouse",
        "event": "click",
        "button": str(button),
        "position": (x, y),
        "pressed": pressed,
        "time": time.time() - start_time - total_pause_duration
    })

def on_scroll(x, y, dx, dy):
    if is_paused:
        return
    events_queue.put({
        "type": "mouse",
        "event": "scroll",
        "position": (x, y),
        "scroll": (dx, dy),
        "time": time.time() - start_time - total_pause_duration
    })

def convert_key(key: str) -> str:
    """Convert pynput key representation to pyautogui format."""
    # Special key mappings
    key_mapping = {
        'Key.space': 'space',
        'Key.enter': 'enter',
        'Key.esc': 'esc',
        'Key.tab': 'tab',
        'Key.backspace': 'backspace',
        'Key.delete': 'delete',
        'Key.shift': 'shift',
        'Key.ctrl': 'ctrl',
        'Key.alt': 'alt',
        'Key.up': 'up',
        'Key.down': 'down',
        'Key.left': 'left',
        'Key.right': 'right',
        'Key.page_up': 'pageup',
        'Key.page_down': 'pagedown',
        'Key.home': 'home',
        'Key.end': 'end',
        'Key.caps_lock': 'capslock',
        'Key.cmd': 'win',
        'Key.insert': 'insert'
    }
    
    # Check if it's a special key
    if key in key_mapping:
        return key_mapping[key]
    
    # Remove quotes if present
    key = key.strip("'")
    
    return key

def convert_button(button: str) -> str:
    """Convert pynput mouse button representation to pyautogui format."""
    button_mapping = {
        'Button.left': 'left',
        'Button.right': 'right',
        'Button.middle': 'middle'
    }
    return button_mapping.get(button, 'left')  # Default to left if unknown

def replay_actions(events_list: List[Dict]):
    print("Starting replay in 3 seconds...")
    for i in range(3, 0, -1):
        print(f"{i}...")
        time.sleep(1)
    
    start_replay = time.time()
    total_events = len(events_list)
    
    for i, event in enumerate(events_list, 1):
        # Progress indication
        if i % 10 == 0:  # Show progress every 10 events
            progress = (i / total_events) * 100
            print(f"Progress: {progress:.1f}% ({i}/{total_events} events)")
            
        try:
            time_to_wait = event["time"] - (time.time() - start_replay)
            if time_to_wait > 0:
                time.sleep(time_to_wait)
            
            if event["type"] == "keyboard":
                key_value = convert_key(event["key"])
                if event["event"] == "press":
                    pyautogui.keyDown(key_value)
                elif event["event"] == "release":
                    pyautogui.keyUp(key_value)
                    
            elif event["type"] == "mouse":
                x, y = validate_screen_position(*event["position"])
                if event["event"] == "move":
                    pyautogui.moveTo(x, y)
                elif event["event"] == "click":
                    button = convert_button(event["button"])
                    if event["pressed"]:
                        pyautogui.mouseDown(x=x, y=y, button=button)
                    else:
                        pyautogui.mouseUp(x=x, y=y, button=button)
                elif event["event"] == "scroll":
                    dx, dy = event["scroll"]
                    pyautogui.scroll(dy, x=x, y=y)
                    
        except Exception as e:
            print(f"Error during replay of event {i}: {e}")
            continue
    
    print("\nReplay finished.")

def process_events():
    """Process events from queue"""
    while not stop_recording_event.is_set():
        try:
            event = events_queue.get(timeout=0.1)
            process_event(event)
        except Empty:  # Use imported Empty exception
            continue

def list_recordings() -> List[Path]:
    """List all available recording files"""
    recordings_dir = Path(CONFIG["output_dir"])
    if not recordings_dir.exists():
        return []
    return sorted(recordings_dir.glob("events_*.json"), reverse=True)  # Most recent first

def display_recordings(recordings: List[Path]) -> None:
    """Display available recordings with details"""
    print("\nAvailable recordings:")
    for i, rec in enumerate(recordings, 1):
        # Extract timestamp from filename
        timestamp = rec.stem.split('_', 1)[1]
        # Convert to datetime for better formatting
        dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
        # Get file size
        size = rec.stat().st_size / 1024  # Size in KB
        print(f"{i}. {dt.strftime('%Y-%m-%d %H:%M:%S')} ({size:.1f}KB) - {rec.name}")

def select_recording() -> Optional[tuple[List[Dict], str]]:
    """Let user select a recording to replay"""
    recordings = list_recordings()
    if not recordings:
        print("No recordings found in", CONFIG["output_dir"])
        return None
    
    display_recordings(recordings)
    
    while True:
        try:
            choice = input("\nEnter recording number to replay (0 to cancel): ")
            if choice == "0":
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(recordings):
                events = load_events(str(recordings[idx]))
                return events, str(recordings[idx])
            print(f"Please enter a number between 1 and {len(recordings)}")
        except ValueError:
            print("Please enter a valid number")

def verify_replay(events_list: List[Dict], original_events_file: str):
    """Record and save verification of replay actions"""
    stop_verification = threading.Event()
    pause_verification = threading.Event()
    verification_start = time.time()

    # Start screen recording for verification
    verification_thread = threading.Thread(
        target=record_screen, 
        args=(stop_verification, pause_verification)
    )
    verification_thread.start()

    # Perform replay
    try:
        replay_actions(events_list)
    finally:
        # Stop verification recording
        stop_verification.set()
        verification_thread.join()

    # Save verification info
    verification_info = {
        "original_recording": original_events_file,
        "verification_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "events_replayed": len(events_list)
    }
    
    verification_file = get_timestamp_filename("verification", "json")
    with open(verification_file, 'w') as f:
        json.dump(verification_info, f, indent=2)

def list_monitors():
    """List all available monitors and their details"""
    sct = mss.mss()
    print("\nAvailable monitors:")
    for i, monitor in enumerate(sct.monitors[1:], 1):  # Skip the "all in one" monitor
        print(f"Monitor {i}:")
        print(f"  Position: ({monitor['left']}, {monitor['top']})")
        print(f"  Resolution: {monitor['width']}x{monitor['height']}")
        
        # Only try to get monitor name if win32api is available
        if HAS_WIN32API:
            try:
                device = win32api.EnumDisplayDevices(None, i-1)
                print(f"  Name: {device.DeviceString}")
            except Exception:
                print("  Name: Unknown")
        print()

def select_monitor():
    """Let user select which monitor to record"""
    sct = mss.mss()
    monitor_count = len(sct.monitors) - 1  # Subtract 1 for the "all in one" monitor
    
    if monitor_count == 1:
        print("Only one monitor detected, using primary monitor.")
        return 1
    
    list_monitors()
    
    while True:
        try:
            choice = input(f"Select monitor to record (1-{monitor_count}): ")
            monitor_num = int(choice)
            if 1 <= monitor_num <= monitor_count:
                return monitor_num
            print(f"Please enter a number between 1 and {monitor_count}")
        except ValueError:
            print("Please enter a valid number")

if __name__ == "__main__":
    ensure_output_directory()
    
    while True:
        print("\n0. Exit program")
        print("1. Start new recording")
        print("2. Replay existing recording")
        
        choice = input("\nEnter your choice (0-2): ")
        
        if choice == "0":
            print("Exiting program...")
            break
        elif choice == "1":
            ensure_output_directory()
            
            # Select monitor before starting recording
            CONFIG["monitor_number"] = select_monitor()
            
            stop_recording_event = threading.Event()
            pause_event = threading.Event()
            start_time = time.time()
            
            # Initialize these at the start
            is_paused = False
            pause_start_time = None
            total_pause_duration = 0

            # Start event processing thread
            events_thread = threading.Thread(target=process_events, daemon=True)
            events_thread.start()

            keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
            
            # Start listeners before screen recording
            keyboard_listener.start()
            mouse_listener.start()

            screen_thread = threading.Thread(target=record_screen, args=(stop_recording_event, pause_event))
            screen_thread.start()

            print("\nRecording... Controls:")
            print("- Press Ctrl+C in this console to stop recording")
            print("- Press Pause key to pause/resume recording")

            try:
                while True:
                    with keyboard.Events() as events:
                        event = events.get(0.1)  # 100ms timeout
                        if event and isinstance(event, keyboard.Events.Press):
                            if event.key == keyboard.Key.pause:
                                toggle_pause(pause_event)
            except KeyboardInterrupt:
                print("\nStopping recording...")
                stop_recording_event.set()
                screen_thread.join()
                events_thread.join(timeout=1)
                keyboard_listener.stop()
                mouse_listener.stop()

            events_file = get_timestamp_filename("events", "json")
            save_events(events_file)
            print(f"Recorded {len(events)} events to {events_file}")

            replay = input("Would you like to replay the recording? (y/n): ").lower()
            if replay == 'y':
                replay_actions(events)
        elif choice == "2":
            result = select_recording()
            if result:
                events, original_file = result
                print("\nStarting replay with verification recording...")
                verify_replay(events, original_file)
                print("\nReplay and verification completed.")
                print("You can find the verification recording in the recordings directory.")
        else:
            print("Invalid choice. Please enter 0, 1, or 2.")
        
        # Ask if user wants to continue after recording or replay
        if choice in ["1", "2"]:
            continue_choice = input("\nReturn to main menu? (y/n): ").lower()
            if continue_choice != 'y':
                print("Exiting program...")
                break
