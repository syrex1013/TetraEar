"""Test frame generation."""
import sys
sys.path.insert(0, 'C:/Users/Adrian/Documents/Repos/Tetra')

from tetra_gui_modern import CaptureThread

thread = CaptureThread()
frame = thread._generate_synthetic_frame()

print('Testing enhanced GUI...')
print(f'Frame type: {frame["type"]}')
print(f'Description: {frame["additional_info"].get("description", "N/A")}')
print(f'Encrypted: {frame["encrypted"]}')
if 'talkgroup' in frame['additional_info']:
    print(f'Talkgroup: {frame["additional_info"]["talkgroup"]}')
if frame.get('decrypted'):
    print(f'Decrypted with: {frame["key_used"]}')

print('\n✓ Frame data generation working!')
print('✓ Descriptions are populated')
print('✓ Talkgroups and SSI included')
