# MIDI Pattern DSL - Live Playback Edition

A terse, ALGOL-inspired domain-specific language for creating and manipulating MIDI patterns with **real-time MIDI output**.

## Features

✨ **Live MIDI Playback** - Hear your patterns immediately via MIDI
⏱️ **Accurate Timing** - Uses Python's `sched` module with 2ms latency compensation
🎹 **Terse Syntax** - Clean, minimal commands inspired by ALGOL
🎵 **Pattern Manipulation** - Transpose, reverse, speed up/slow down in real-time
🔧 **MIDI Port Management** - List and switch between MIDI outputs

## Installation

### 1. Install Dependencies

```bash
pip install mido[ports-rtmidi]
```

This installs:
- `mido` - High-level MIDI library
- `python-rtmidi` - Low-level MIDI I/O (installed automatically via `[ports-rtmidi]`)

### 2. Setup MIDI Output

**macOS:**
- Built-in MIDI works out of the box
- Or install a software synth like SimpleSynth

**Windows:**
- Install [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) for virtual MIDI ports
- Or use Microsoft GS Wavetable Synth (built-in)

**Linux:**
- Install `timidity` or `fluidsynth`:
  ```bash
  sudo apt-get install timidity  # or fluidsynth
  timidity -iA  # Run as ALSA server
  ```

### 3. Connect to a Synth

You need something to receive MIDI and make sound:
- **DAW**: Ableton, FL Studio, Reaper, GarageBand, etc.
- **Soft Synth**: Vital, Surge, Dexed, ZynAddSubFX
- **Hardware**: MIDI keyboard, sound module

## Quick Start

```bash
python3 midi_dsl_live.py
```

### First Commands

```
midi> ports                      # List available MIDI ports
midi> port 0                     # Select a port (if needed)
midi> pat test 4 c4 e4 g4 c5    # Create a pattern
midi> play test                  # Hear it play!
midi> stop                       # Stop playback
```

## Language Reference

### Pattern Creation

```
pat <name> <beats> <note1> [note2 ...]
```
Create a pattern spanning N beats with given notes.

```
seq <note1> [note2 ...]
```
Quick sequential pattern (stored as '_seq').

**Examples:**
```
pat melody 4 c4 e4 g4 c5        # 4-beat melody
pat bass 4 c3 c3 f3 g3          # Bass line
seq 60 64 67 72                  # Quick sequence
```

### State Management

```
vel <0-127>          Set velocity (volume) for new notes
len <beats>          Set note length (duration)
tempo <bpm>          Set tempo (20-300 BPM)
```

**Examples:**
```
vel 100              # Loud notes
len 0.5              # Half beat duration
tempo 140            # Fast tempo
```

### Playback

```
play <pattern>       Play pattern via MIDI
stop                 Stop playback
```

**Examples:**
```
play melody          # Play the melody
stop                 # Emergency stop
```

### MIDI Setup

```
ports                         List available MIDI ports
port <name_or_index>          Switch MIDI output port
```

**Examples:**
```
ports                # See what's available
port 0               # Use first port
port "IAC Driver"    # Use by name
```

### Pattern Modification

```
mod <pattern> trans <semitones>    Transpose
mod <pattern> rev                   Reverse
mod <pattern> double                2x speed
mod <pattern> half                  0.5x speed
mod <pattern> shift <beats>         Time shift
```

**Examples:**
```
mod melody trans 12       # Up an octave
mod melody rev            # Play backwards
mod melody double         # Twice as fast
```

### Utility

```
list                 List all patterns
show <pattern>       Show pattern details
del <pattern>        Delete pattern
clear                Clear all state
help                 Show help
```

## Note Syntax

Multiple ways to specify notes:

1. **MIDI numbers**: `60 64 67` (C4, E4, G4)
2. **Note names with octave**: `c4 e4 g4`
3. **Sharps**: `c#4 d#5`
4. **Flats**: `db4 eb5`

## Complete Example Session

```bash
# Setup
vel 80
len 0.25
tempo 120

# Create patterns
pat melody 4 c4 e4 g4 c5
pat bass 4 c3 c3 f3 g3
pat fast 2 c5 d5 e5 f5 g5 a5 b5 c6

# Play them
play melody
# (listen)
stop

play bass
# (listen)
stop

# Modify and replay
mod melody trans 12      # Up an octave
play melody

mod melody rev           # Reverse
play melody

mod fast double          # Super fast
play fast

# Cleanup
stop
clear
```

## Timing Details

### Accuracy

The sequencer uses:
- **Python's `sched` module** for event scheduling
- **2ms latency compensation** for better timing
- **`perf_counter()`** for high-resolution timing

**Expected jitter:**
- Linux/macOS: 2-5ms
- Windows: 5-15ms

For most musical applications at typical tempos (80-140 BPM), this is **perfectly acceptable** and often imperceptible.

### Improving Timing

For better timing, consider the hybrid approach:
1. **Keep this Python DSL** for the interface
2. **Port timing engine to C** (see your cquencer project!)
3. **Bridge via ctypes** or subprocess

## Troubleshooting

### "No MIDI output available"

1. Run `ports` to see available ports
2. If none appear:
   - **Windows**: Install loopMIDI
   - **macOS**: Should work by default
   - **Linux**: Start timidity (`timidity -iA`)

### "Already playing"

Use `stop` before playing another pattern.

### No sound when playing

1. Check MIDI port: `ports`
2. Ensure something is receiving MIDI (DAW, synth)
3. Check synth volume/settings

### Notes stuck on

Emergency stop: `stop`

This sends MIDI note-off for all active notes plus MIDI "all notes off" (CC 123).

## Advanced Usage

### Using with a DAW

1. Set DAW to receive MIDI on a virtual port
2. Load a synth/instrument
3. Run the DSL: `python3 midi_dsl_live.py`
4. Select the port: `port "Your Virtual Port"`
5. Create and play patterns!

### Recording

Most DAWs can record incoming MIDI:
1. Arm a MIDI track
2. Play your pattern from the DSL
3. Record in the DAW

### Pattern Development Workflow

```bash
# Quick iteration
pat test 4 c4 e4 g4 c5
play test
# (adjust)
mod test trans 2
play test
# (sounds good!)
```

## Known Limitations

- **Single pattern playback**: Can't play multiple patterns simultaneously
- **No looping**: Patterns play once (future enhancement)
- **Basic timing**: 2-15ms jitter depending on OS (see timing section)
- **No MIDI CC**: Only note on/off (could be added)

## Future Enhancements

See README for ideas:
- Loop counts: `loop <pattern> <count>`
- Chords: `chord c4 e4 g4`
- Scales: `scale major c4`
- Probability: `prob 0.5 <note>`
- Save/load patterns
- Multiple simultaneous patterns

## Credits

Built with:
- [mido](https://github.com/mido/mido) - MIDI objects for Python
- [python-rtmidi](https://github.com/SpotlightKid/python-rtmidi) - RtMidi bindings
- Python's `sched` module for scheduling

## License

MIT - Use freely!
