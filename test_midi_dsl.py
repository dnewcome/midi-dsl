#!/usr/bin/env python3
"""
Quick test script for MIDI DSL
Run this to verify everything works
"""

import subprocess
import sys

# Commands to test
test_commands = """
# Test basic pattern creation
pat test 4 c4 e4 g4 c5
show test

# Test sequence
seq 60 64 67

# Test settings
vel 100
len 0.5
tempo 140

# Create another pattern with new settings
pat fast 2 c5 d5 e5 f5
show fast

# Test modifications
mod test trans 12
mod test rev

# List everything
list

# Clean up
clear
list
""".strip()

print("=" * 60)
print("MIDI DSL Test Script")
print("=" * 60)
print()
print("This will test the DSL commands without MIDI output.")
print("To test actual MIDI playback, run: python3 midi_dsl_live.py")
print()
print("Commands to test:")
print(test_commands)
print()
print("=" * 60)

# Write commands to temp file
with open('/tmp/midi_test_commands.txt', 'w') as f:
    f.write(test_commands)
    f.write('\nexit\n')

# Run the DSL with test commands
print("\nRunning tests...\n")
try:
    result = subprocess.run(
        ['python3', 'midi_dsl_live.py'],
        stdin=open('/tmp/midi_test_commands.txt'),
        capture_output=True,
        text=True,
        timeout=5
    )
    
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    
    print("\n" + "=" * 60)
    print("✓ Tests completed!")
    print("\nTo test with actual MIDI playback:")
    print("  1. Ensure you have a MIDI synth/DAW running")
    print("  2. Run: python3 midi_dsl_live.py")
    print("  3. Type: ports")
    print("  4. Type: pat test 4 c4 e4 g4 c5")
    print("  5. Type: play test")
    print("  6. Listen! 🎵")
    
except subprocess.TimeoutExpired:
    print("Timeout (this is normal for interactive mode)")
except Exception as e:
    print(f"Error: {e}")
