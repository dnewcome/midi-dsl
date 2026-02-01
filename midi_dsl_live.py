#!/usr/bin/env python3
"""
Terse MIDI Pattern DSL - REPL with Live MIDI Output
A concise language for generating and manipulating MIDI patterns in real-time.

Syntax Examples:
  pat melody 4 c4 e4 g4 c5  # define pattern over 4 beats
  vel 80                     # set velocity
  len 0.5                    # set note length (beats)
  play melody                # play pattern via MIDI!
  mod melody trans 12        # transpose up octave
  stop                       # stop playback
"""

import re
import sched
import threading
from time import perf_counter, sleep
from dataclasses import dataclass
from typing import List, Dict, Optional

try:
    import mido
    MIDI_AVAILABLE = True
except ImportError:
    MIDI_AVAILABLE = False
    print("Warning: mido not installed. Install with: pip install mido[ports-rtmidi]")
    print("Running in simulation mode (no actual MIDI output)")
    print()

# MIDI note mapping (simple subset)
NOTE_MAP = {
    'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11,
    'c4': 60, 'd4': 62, 'e4': 64, 'f4': 65, 'g4': 67, 'a4': 69, 'b4': 71,
    'c5': 72, 'd5': 74, 'e5': 76, 'f5': 77, 'g5': 79, 'a5': 81, 'b5': 83,
}

@dataclass
class Note:
    """Single MIDI note"""
    pitch: int        # MIDI note number (0-127)
    velocity: int     # Volume (0-127)
    duration: float   # Length in beats
    offset: float     # Start time in beats

@dataclass
class Pattern:
    """A sequence of notes forming a pattern"""
    name: str
    notes: List[Note]
    tempo: int = 120
    
    def __repr__(self):
        return f"Pattern({self.name}: {len(self.notes)} notes)"

class DSLState:
    """Runtime state for the DSL"""
    def __init__(self):
        self.patterns: Dict[str, Pattern] = {}
        self.current_vel = 80
        self.current_len = 0.25
        self.current_tempo = 120
        
    def reset(self):
        """Clear all state"""
        self.__init__()

class MIDIPlayer:
    """Handles MIDI playback using sched and mido"""
    
    def __init__(self):
        self.port = None
        self.scheduler = None
        self.scheduler_thread = None
        self.active_notes = set()  # Track playing notes for cleanup
        
        if MIDI_AVAILABLE:
            try:
                # Try to open default MIDI output
                self.port = mido.open_output()
                print(f"✓ MIDI output: {self.port.name}")
            except Exception as e:
                print(f"✗ Could not open MIDI port: {e}")
                ports = mido.get_output_names()
                if ports:
                    print("Available ports:", ports)
                else:
                    print("No MIDI ports found. You may need to:")
                    print("  - Install a virtual MIDI driver (e.g., loopMIDI on Windows)")
                    print("  - Connect a MIDI device")
                self.port = None
        
    def list_ports(self):
        """List available MIDI ports"""
        if not MIDI_AVAILABLE:
            return "MIDI not available (install mido)"
        
        ports = mido.get_output_names()
        if not ports:
            return "No MIDI output ports found"
        
        lines = ["Available MIDI ports:"]
        for i, name in enumerate(ports):
            current = " (current)" if self.port and self.port.name == name else ""
            lines.append(f"  {i}: {name}{current}")
        return "\n".join(lines)
    
    def set_port(self, port_name_or_index):
        """Change MIDI output port"""
        if not MIDI_AVAILABLE:
            return "MIDI not available"
        
        try:
            # Close existing port
            if self.port:
                self.all_notes_off()
                self.port.close()
            
            # Open new port
            ports = mido.get_output_names()
            
            # Try as index first
            try:
                idx = int(port_name_or_index)
                if 0 <= idx < len(ports):
                    self.port = mido.open_output(ports[idx])
                    return f"Switched to port: {self.port.name}"
                else:
                    return f"Port index {idx} out of range (0-{len(ports)-1})"
            except ValueError:
                # Try as port name
                self.port = mido.open_output(port_name_or_index)
                return f"Switched to port: {self.port.name}"
                
        except Exception as e:
            return f"Error setting port: {e}"
    
    def send_note_on(self, pitch: int, velocity: int):
        """Send MIDI note on"""
        if self.port:
            msg = mido.Message('note_on', note=pitch, velocity=velocity)
            self.port.send(msg)
            self.active_notes.add(pitch)
    
    def send_note_off(self, pitch: int):
        """Send MIDI note off"""
        if self.port:
            msg = mido.Message('note_off', note=pitch)
            self.port.send(msg)
            self.active_notes.discard(pitch)
    
    def all_notes_off(self):
        """Emergency: turn off all notes"""
        if self.port:
            for pitch in list(self.active_notes):
                self.send_note_off(pitch)
            # Also send MIDI all notes off message
            for channel in range(16):
                self.port.send(mido.Message('control_change', 
                                           control=123, 
                                           value=0, 
                                           channel=channel))
    
    def play_pattern(self, pattern: Pattern):
        """Play a pattern using the scheduler"""
        if not self.port:
            return "No MIDI output available (use 'ports' to list available ports)"
        
        # Cancel any existing scheduler
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            return "Already playing (use 'stop' first)"
        
        # Create new scheduler
        self.scheduler = sched.scheduler(perf_counter, sleep)
        
        # Calculate beat duration in seconds
        beat_duration = 60.0 / pattern.tempo
        
        # Add 2ms latency compensation for better timing
        LATENCY_COMP = 0.002
        
        # Schedule all notes
        for note in pattern.notes:
            # Schedule note on
            note_on_time = (note.offset * beat_duration) + LATENCY_COMP
            self.scheduler.enter(
                note_on_time,
                1,  # priority
                self.send_note_on,
                argument=(note.pitch, note.velocity)
            )
            
            # Schedule note off
            note_off_time = note_on_time + (note.duration * beat_duration)
            self.scheduler.enter(
                note_off_time,
                1,
                self.send_note_off,
                argument=(note.pitch,)
            )
        
        # Run scheduler in background thread
        def run_scheduler():
            try:
                self.scheduler.run()
            except Exception as e:
                print(f"\nScheduler error: {e}")
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        # Calculate total duration
        if pattern.notes:
            total_duration = max(n.offset + n.duration for n in pattern.notes) * beat_duration
            return f"♪ Playing '{pattern.name}' ({total_duration:.2f}s, {pattern.tempo} BPM)"
        return "Pattern is empty"
    
    def stop_playback(self):
        """Stop current playback"""
        # Clear scheduler
        if self.scheduler:
            # Empty the queue
            for event in list(self.scheduler.queue):
                try:
                    self.scheduler.cancel(event)
                except ValueError:
                    pass
        
        # Turn off all notes
        self.all_notes_off()
        
        return "■ Playback stopped"
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_playback()
        if self.port:
            self.port.close()

class DSLInterpreter:
    """Interpreter for the MIDI DSL"""
    
    def __init__(self):
        self.state = DSLState()
        self.player = MIDIPlayer()
        
    def parse_note(self, token: str) -> Optional[int]:
        """Convert note name or number to MIDI pitch"""
        # Try direct MIDI number
        if token.isdigit():
            pitch = int(token)
            return pitch if 0 <= pitch <= 127 else None
        
        # Try note name
        token = token.lower()
        if token in NOTE_MAP:
            return NOTE_MAP[token]
        
        # Try note with octave (e.g., "c#4", "db5")
        match = re.match(r'([a-g])([#b]?)(\d)', token)
        if match:
            note, accidental, octave = match.groups()
            pitch = NOTE_MAP[note] + (12 * int(octave))
            if accidental == '#':
                pitch += 1
            elif accidental == 'b':
                pitch -= 1
            return pitch if 0 <= pitch <= 127 else None
        
        return None
    
    def execute(self, line: str) -> str:
        """Execute a DSL command and return result"""
        line = line.strip()
        if not line or line.startswith('#'):
            return ""
        
        tokens = line.split()
        if not tokens:
            return ""
        
        cmd = tokens[0].lower()
        args = tokens[1:]
        
        try:
            # PATTERN DEFINITION
            if cmd == "pat":
                return self.cmd_pattern(args)
            
            # SEQUENCE DEFINITION (shorthand)
            elif cmd == "seq":
                return self.cmd_sequence(args)
            
            # SET VELOCITY
            elif cmd == "vel":
                return self.cmd_velocity(args)
            
            # SET NOTE LENGTH
            elif cmd == "len":
                return self.cmd_length(args)
            
            # SET TEMPO
            elif cmd == "tempo":
                return self.cmd_tempo(args)
            
            # PLAY PATTERN
            elif cmd == "play":
                return self.cmd_play(args)
            
            # STOP PLAYING
            elif cmd == "stop":
                return self.cmd_stop(args)
            
            # MODIFY PATTERN
            elif cmd == "mod":
                return self.cmd_modify(args)
            
            # LIST PATTERNS
            elif cmd == "list":
                return self.cmd_list()
            
            # SHOW PATTERN
            elif cmd == "show":
                return self.cmd_show(args)
            
            # DELETE PATTERN
            elif cmd == "del":
                return self.cmd_delete(args)
            
            # CLEAR ALL
            elif cmd == "clear":
                self.state.reset()
                return "Cleared all patterns and state"
            
            # MIDI PORTS
            elif cmd == "ports":
                return self.player.list_ports()
            
            elif cmd == "port":
                if not args:
                    return "Usage: port <name_or_index>"
                return self.player.set_port(args[0])
            
            # HELP
            elif cmd == "help":
                return self.cmd_help()
            
            else:
                return f"Unknown command: {cmd} (try 'help')"
                
        except Exception as e:
            return f"Error: {str(e)}"
    
    def cmd_pattern(self, args: List[str]) -> str:
        """pat <name> <beats> <note1> <note2> ..."""
        if len(args) < 3:
            return "Usage: pat <name> <beats> <note1> [note2 ...]"
        
        name = args[0]
        try:
            beats = int(args[1])
        except ValueError:
            return f"Invalid beats: {args[1]}"
        
        notes = []
        note_tokens = args[2:]
        
        if not note_tokens:
            return "No notes specified"
        
        beat_duration = beats / len(note_tokens)
        
        for i, token in enumerate(note_tokens):
            pitch = self.parse_note(token)
            if pitch is None:
                return f"Invalid note: {token}"
            
            note = Note(
                pitch=pitch,
                velocity=self.state.current_vel,
                duration=self.state.current_len,
                offset=i * beat_duration
            )
            notes.append(note)
        
        pattern = Pattern(name=name, notes=notes, tempo=self.state.current_tempo)
        self.state.patterns[name] = pattern
        
        return f"Created pattern '{name}' with {len(notes)} notes over {beats} beats"
    
    def cmd_sequence(self, args: List[str]) -> str:
        """seq <note1> <note2> ... (quick sequential pattern)"""
        if not args:
            return "Usage: seq <note1> [note2 ...]"
        
        notes = []
        for i, token in enumerate(args):
            pitch = self.parse_note(token)
            if pitch is None:
                return f"Invalid note: {token}"
            
            note = Note(
                pitch=pitch,
                velocity=self.state.current_vel,
                duration=self.state.current_len,
                offset=i * self.state.current_len
            )
            notes.append(note)
        
        # Store in temp pattern
        pattern = Pattern(name="_seq", notes=notes, tempo=self.state.current_tempo)
        self.state.patterns["_seq"] = pattern
        
        return f"Sequence: {len(notes)} notes → MIDI: {[n.pitch for n in notes]}"
    
    def cmd_velocity(self, args: List[str]) -> str:
        """vel <0-127>"""
        if len(args) != 1:
            return f"Usage: vel <0-127> (current: {self.state.current_vel})"
        
        try:
            vel = int(args[0])
            if not 0 <= vel <= 127:
                return "Velocity must be 0-127"
            self.state.current_vel = vel
            return f"Velocity set to {vel}"
        except ValueError:
            return f"Invalid velocity: {args[0]}"
    
    def cmd_length(self, args: List[str]) -> str:
        """len <beats>"""
        if len(args) != 1:
            return f"Usage: len <beats> (current: {self.state.current_len})"
        
        try:
            length = float(args[0])
            if length <= 0:
                return "Length must be positive"
            self.state.current_len = length
            return f"Note length set to {length} beats"
        except ValueError:
            return f"Invalid length: {args[0]}"
    
    def cmd_tempo(self, args: List[str]) -> str:
        """tempo <bpm>"""
        if len(args) != 1:
            return f"Usage: tempo <bpm> (current: {self.state.current_tempo})"
        
        try:
            tempo = int(args[0])
            if not 20 <= tempo <= 300:
                return "Tempo must be 20-300 BPM"
            self.state.current_tempo = tempo
            return f"Tempo set to {tempo} BPM"
        except ValueError:
            return f"Invalid tempo: {args[0]}"
    
    def cmd_play(self, args: List[str]) -> str:
        """play <pattern>"""
        if len(args) != 1:
            return "Usage: play <pattern>"
        
        name = args[0]
        if name not in self.state.patterns:
            return f"Pattern '{name}' not found"
        
        pattern = self.state.patterns[name]
        
        # Actually play the pattern via MIDI
        return self.player.play_pattern(pattern)
    
    def cmd_stop(self, args: List[str]) -> str:
        """stop playback"""
        return self.player.stop_playback()
    
    def cmd_modify(self, args: List[str]) -> str:
        """mod <pattern> <operation> [params]"""
        if len(args) < 2:
            return "Usage: mod <pattern> <op> [params]\nOps: trans, rev, double, half, shift"
        
        name = args[0]
        if name not in self.state.patterns:
            return f"Pattern '{name}' not found"
        
        pattern = self.state.patterns[name]
        op = args[1].lower()
        params = args[2:]
        
        # TRANSPOSE
        if op == "trans":
            if not params:
                return "Usage: mod <pat> trans <semitones>"
            try:
                semitones = int(params[0])
                for note in pattern.notes:
                    note.pitch = max(0, min(127, note.pitch + semitones))
                return f"Transposed '{name}' by {semitones} semitones"
            except ValueError:
                return f"Invalid semitones: {params[0]}"
        
        # REVERSE
        elif op == "rev":
            pattern.notes.reverse()
            # Recalculate offsets
            max_offset = max(n.offset for n in pattern.notes)
            for note in pattern.notes:
                note.offset = max_offset - note.offset
            return f"Reversed '{name}'"
        
        # DOUBLE TEMPO
        elif op == "double":
            for note in pattern.notes:
                note.offset *= 0.5
                note.duration *= 0.5
            return f"Doubled speed of '{name}'"
        
        # HALF TEMPO
        elif op == "half":
            for note in pattern.notes:
                note.offset *= 2
                note.duration *= 2
            return f"Halved speed of '{name}'"
        
        # TIME SHIFT
        elif op == "shift":
            if not params:
                return "Usage: mod <pat> shift <beats>"
            try:
                shift = float(params[0])
                for note in pattern.notes:
                    note.offset += shift
                return f"Shifted '{name}' by {shift} beats"
            except ValueError:
                return f"Invalid shift: {params[0]}"
        
        else:
            return f"Unknown operation: {op}"
    
    def cmd_list(self) -> str:
        """List all patterns"""
        if not self.state.patterns:
            return "No patterns defined"
        
        lines = ["Patterns:"]
        for name, pat in self.state.patterns.items():
            lines.append(f"  {name}: {len(pat.notes)} notes, {pat.tempo} BPM")
        return "\n".join(lines)
    
    def cmd_show(self, args: List[str]) -> str:
        """Show pattern details"""
        if len(args) != 1:
            return "Usage: show <pattern>"
        
        name = args[0]
        if name not in self.state.patterns:
            return f"Pattern '{name}' not found"
        
        pattern = self.state.patterns[name]
        lines = [f"Pattern '{name}':"]
        lines.append(f"  Tempo: {pattern.tempo} BPM")
        lines.append(f"  Notes ({len(pattern.notes)}):")
        
        for i, note in enumerate(pattern.notes):
            lines.append(
                f"    {i+1}. pitch={note.pitch} vel={note.velocity} "
                f"dur={note.duration:.2f} @{note.offset:.2f}b"
            )
        
        return "\n".join(lines)
    
    def cmd_delete(self, args: List[str]) -> str:
        """Delete a pattern"""
        if len(args) != 1:
            return "Usage: del <pattern>"
        
        name = args[0]
        if name in self.state.patterns:
            del self.state.patterns[name]
            return f"Deleted pattern '{name}'"
        return f"Pattern '{name}' not found"
    
    def cmd_help(self) -> str:
        """Show help text"""
        return """
MIDI Pattern DSL - Commands:

PATTERN CREATION:
  pat <name> <beats> <note...>  Create pattern over N beats
  seq <note...>                    Quick sequence (saves as '_seq')
  
STATE:
  vel <0-127>                      Set velocity for new notes
  len <beats>                      Set note length for new notes
  tempo <bpm>                      Set tempo for new patterns
  
PLAYBACK:
  play <pattern>                   Play pattern via MIDI ♪
  stop                             Stop playback ■
  
MIDI SETUP:
  ports                            List available MIDI ports
  port <name_or_index>             Switch MIDI output port
  
MODIFICATION:
  mod <pat> trans <semi>           Transpose by semitones
  mod <pat> rev                    Reverse pattern
  mod <pat> double                 Double speed
  mod <pat> half                   Half speed
  mod <pat> shift <beats>          Time shift
  
UTILITY:
  list                             List all patterns
  show <pattern>                   Show pattern details
  del <pattern>                    Delete pattern
  clear                            Clear all state
  help                             Show this help

NOTES: c d e f g a b (with octave: c4 d5)
       Sharps: c# d#  Flats: db eb
       Or MIDI numbers: 60 64 67

EXAMPLES:
  pat melody 4 c4 e4 g4 c5        # 4-beat melody
  vel 100                          # loud notes
  len 0.5                          # half beat each
  play melody                      # play it!
  mod melody trans 12              # up an octave
  play melody                      # play modified version
  stop                             # stop playback
"""

def repl():
    """Run the REPL"""
    interpreter = DSLInterpreter()
    
    print("=" * 60)
    print("♪  MIDI Pattern DSL - Live Playback REPL  ♪")
    print("=" * 60)
    print("Type 'help' for commands, 'exit' or Ctrl+D to quit")
    print()
    
    while True:
        try:
            line = input("midi> ").strip()
            
            if not line:
                continue
            
            if line.lower() in ('exit', 'quit', 'q'):
                print("Stopping playback and cleaning up...")
                interpreter.player.cleanup()
                print("Goodbye!")
                break
            
            result = interpreter.execute(line)
            if result:
                print(result)
                
        except EOFError:
            print("\nStopping playback and cleaning up...")
            interpreter.player.cleanup()
            print("Goodbye!")
            break
        except KeyboardInterrupt:
            print("\n(Use 'exit' or Ctrl+D to quit)")
            interpreter.player.stop_playback()
            continue

if __name__ == "__main__":
    repl()
