#!/usr/bin/env python3
import json
from pathlib import Path

# Check captured frames for unencrypted text
frames_file = Path('logs/continuous_20251223_214944.jsonl')
unencrypted_texts = []

with open(frames_file, 'r', encoding='utf-8') as f:
    for line in f:
        frame = json.loads(line)
        if not frame.get('encrypted', True):
            text = frame.get('decoded_text') or frame.get('sds_message', '')
            if text and not text.startswith('[BIN'):
                # Check if it has actual readable content
                clean = text.replace('[GSM7]', '').replace('[LOC]', '').strip()
                if len(clean) > 3:
                    unencrypted_texts.append({
                        'type': frame.get('type_name'),
                        'text': text,
                        'mac_pdu': frame.get('mac_pdu', {}),
                        'frame_num': frame.get('number')
                    })

print(f'Found {len(unencrypted_texts)} unencrypted text frames\n')
for i, t in enumerate(unencrypted_texts[:20], 1):
    print(f"{i}. [{t['type']}] {t['text'][:80]}")

# Also check the hex payloads
print("\n\n=== Checking hex payloads ===")
for i, t in enumerate(unencrypted_texts[:5], 1):
    if t['mac_pdu'].get('data'):
        print(f"\n{i}. Type: {t['type']}")
        print(f"   Text: {t['text']}")
        print(f"   Hex: {t['mac_pdu']['data'][:50]}...")
