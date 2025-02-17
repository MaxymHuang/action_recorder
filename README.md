# Screen Recorder and Input Replay

A Python-based screen recording and input replay tool that captures screen content, keyboard, and mouse actions, with the ability to replay them later.

## Features

### Recording
- **Screen Recording**
  - Multiple monitor support with monitor selection
  - Configurable FPS (default: 15)
  - AVI video output with XVID codec
  - Pause/Resume functionality

- **Input Capture**
  - Keyboard events (press/release)
  - Mouse movements
  - Mouse clicks (left, right, middle buttons)
  - Mouse scrolling
  - Timestamps for accurate replay

### Playback
- **Event Replay**
  - Accurate timing reproduction
  - Progress indication
  - Verification recording during replay
  - Support for keyboard and mouse events
  - Pause between replays

### File Management
- **Organized Output**
  - Timestamp-based filenames
  - Separate directories for recordings
  - JSON format for event data
  - AVI format for video recordings

### Additional Features
- **Monitor Selection**
  - List available monitors
  - Display monitor details (resolution, position)
  - Monitor name detection (Windows only)

- **Recording Controls**
  - `Ctrl+C`: Stop recording
  - `Ctrl+P`: Pause/Resume
  - Selection menu for replay

## Requirements

```bash
opencv-python
numpy
mss
pynput
pyautogui
pywin32 (optional, for Windows monitor names)
```

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the script:
```bash
python prototype.py
```

### Options
1. Start new recording
2. Replay existing recording

## Configuration

Modify the `CONFIG` dictionary to customize:
```python
CONFIG = {
    "fps": 15,
    "video_format": "XVID",
    "output_dir": "recordings",
    "screen_region": None,  # None for full screen
    "monitor_number": 1     # Default to primary monitor
}
```

## Output Files

- Screen Recording: `recordings/screen_YYYYMMDD_HHMMSS.avi`
- Event Data: `recordings/events_YYYYMMDD_HHMMSS.json`
- Verification: `recordings/verification_YYYYMMDD_HHMMSS.json`

## Limitations

1. **Performance**
   - High CPU usage during recording
   - Large file sizes for long recordings
   - Memory usage increases with recording duration

2. **Compatibility**
   - Some special keys may not replay correctly
   - Monitor detection requires Windows for full features
   - Screen scaling might affect mouse position accuracy

3. **Replay**
   - No speed adjustment during replay
   - Cannot edit recorded events
   - Must replay entire recording

4. **Recording**
   - No audio recording
   - No region selection during recording
   - Limited video format options

## Future Improvements

- [ ] Add audio recording support
- [ ] Implement region selection
- [ ] Add replay speed control
- [ ] Reduce resource usage
- [ ] Add event editing capability
- [ ] Support more video formats
- [ ] Add compression options

## License

Internal use only