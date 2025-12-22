"""
TETRA frame decoder module.
"""

import numpy as np
from bitstring import BitArray
import logging
from typing import Optional

from tetra_crypto import TEADecryptor, TetraKeyManager
from tetra_protocol import TetraProtocolParser, TetraBurst, MacPDU, CallMetadata

logger = logging.getLogger(__name__)


class TetraDecoder:
    """Decodes TETRA frames from demodulated symbols."""
    
    def __init__(self, key_manager: Optional[TetraKeyManager] = None, auto_decrypt: bool = True):
        """
        Initialize TETRA decoder.
        
        Args:
            key_manager: Optional key manager for decryption
            auto_decrypt: Automatically try common keys if no key manager provided
        """
        # TETRA frame structure constants
        self.SYNC_PATTERN = [0, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0,
                            1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 0, 1, 0, 0]
        self.FRAME_LENGTH = 510  # bits per frame
        self.key_manager = key_manager
        self.auto_decrypt = auto_decrypt
        self.protocol_parser = TetraProtocolParser()  # Add protocol parser
        self._setup_common_keys()
    
    def _setup_common_keys(self):
        """Setup common/known TETRA keys for auto-decryption (OpenEar style)."""
        self.common_keys = {
            'TEA1': [
                # Null/default keys
                bytes.fromhex('00000000000000000000'),  # All zeros
                bytes.fromhex('FFFFFFFFFFFFFFFFFFFFFFFF'),  # All ones
                
                # Test patterns
                bytes.fromhex('0123456789ABCDEF0123'),  # Sequential
                bytes.fromhex('FEDCBA9876543210FEDC'),  # Reverse sequential
                
                # Common weak keys
                bytes.fromhex('1111111111111111111111'),  # All 1s
                bytes.fromhex('AAAAAAAAAAAAAAAAAAAA'),  # Pattern A
                bytes.fromhex('5555555555555555555555'),  # Pattern 5
                
                # Default manufacturer keys (common in testing)
                bytes.fromhex('0001020304050607080910'),
                bytes.fromhex('1234567890ABCDEF1234'),
                bytes.fromhex('DEADBEEFCAFEBABEFACE'),
                
                # Network default keys (some networks use these)
                bytes.fromhex('A0B1C2D3E4F506172839'),
                bytes.fromhex('112233445566778899AA'),
                bytes.fromhex('0F0F0F0F0F0F0F0F0F0F'),
            ],
            'TEA2': [
                # Null/default keys
                bytes.fromhex('00000000000000000000000000000000'),  # All zeros
                bytes.fromhex('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF'),  # All ones
                
                # Test patterns
                bytes.fromhex('0123456789ABCDEF0123456789ABCDEF'),  # Sequential
                bytes.fromhex('FEDCBA9876543210FEDCBA9876543210'),  # Reverse
                
                # Common patterns
                bytes.fromhex('11111111111111111111111111111111'),
                bytes.fromhex('AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'),
                bytes.fromhex('55555555555555555555555555555555'),
                
                # Manufacturer defaults
                bytes.fromhex('000102030405060708091011121314151617'),
                bytes.fromhex('1234567890ABCDEF1234567890ABCDEF'),
                bytes.fromhex('DEADBEEFCAFEBABEDEADBEEFCAFEBABE'),
                
                # Network defaults
                bytes.fromhex('A0B1C2D3E4F5061728394A5B6C7D8E9F'),
                bytes.fromhex('1122334455667788990011223344556677'),
            ]
        }
        logger.debug(f"Auto-decrypt enabled with {sum(len(v) for v in self.common_keys.values())} common keys (OpenEar style)")
        
    def symbols_to_bits(self, symbols):
        """
        Convert π/4-DQPSK symbols to bits.
        
        Args:
            symbols: Array of symbol values (0-7)
            
        Returns:
            Bit array
        """
        bits = []
        for symbol in symbols:
            # π/4-DQPSK: 3 bits per symbol
            # Map symbol to 3-bit value
            bit3 = (symbol >> 2) & 1
            bit2 = (symbol >> 1) & 1
            bit1 = symbol & 1
            bits.extend([bit3, bit2, bit1])
        
        return np.array(bits)
    
    def find_sync(self, bits, threshold=0.96):
        """
        Find TETRA synchronization pattern.
        
        Args:
            bits: Bit stream
            threshold: Correlation threshold (default 0.94 for strict matching)
            
        Returns:
            List of sync positions
        """
        sync_positions = []
        sync_pattern = np.array(self.SYNC_PATTERN)
        sync_len = len(sync_pattern)
        
        for i in range(len(bits) - sync_len):
            window = bits[i:i+sync_len]
            correlation = np.sum(window == sync_pattern) / sync_len
            
            if correlation >= threshold:
                sync_positions.append(i)
                logger.debug(f"Found sync at position {i}, correlation: {correlation:.2f}")
        
        return sync_positions
    
    def decode_frame(self, bits, start_pos):
        """
        Decode a TETRA frame starting at given position.
        
        Args:
            bits: Bit stream
            start_pos: Start position of frame
            
        Returns:
            Decoded frame data or None
        """
        if start_pos + self.FRAME_LENGTH > len(bits):
            return None
        
        frame_bits = bits[start_pos:start_pos+self.FRAME_LENGTH]
        frame = BitArray(frame_bits)
        
        # Extract frame header (first 32 bits)
        header = frame[0:32]
        
        # Extract frame type (first 4 bits)
        frame_type = header[0:4].uint
        
        # Extract frame number (next 8 bits)
        frame_number = header[4:12].uint
        
        # Parse additional fields based on frame type
        additional_info = {}
        
        # Map frame types (MAC PDU types for downlink)
        # 0: MAC-RESOURCE
        # 1: MAC-FRAG
        # 2: MAC-END
        # 3: MAC-BROADCAST
        # 4: MAC-SUPPL
        # 5: MAC-U-SIGNAL (Uplink only? No, D-MAC-SYNC etc)
        # Let's use a more comprehensive mapping
        
        frame_type_name = "Unknown"
        
        # Heuristic: If it's a TCH (Traffic Channel) burst, it might be Type 1 (Traffic)
        # But standard MAC PDUs use the values below.
        # We'll try to infer from context or just map standard PDUs
        
        if frame_type == 0:
            frame_type_name = "MAC-RESOURCE"
            additional_info['description'] = 'Resource allocation'
            if len(header) >= 24:
                additional_info['network_id'] = header[12:24].uint
        elif frame_type == 1:
            # Could be MAC-FRAG or Traffic depending on context
            # For this decoder, we'll assume Traffic if it looks like voice
            frame_type_name = "MAC-FRAG" 
            additional_info['description'] = 'Fragment'
        elif frame_type == 2:
            frame_type_name = "MAC-END"
            additional_info['description'] = 'End of transmission'
        elif frame_type == 3:
            frame_type_name = "MAC-BROADCAST"
            additional_info['description'] = 'Broadcast info'
        elif frame_type == 4:
            frame_type_name = "MAC-SUPPL"
            additional_info['description'] = 'Supplementary'
        elif frame_type == 5:
            frame_type_name = "MAC-U-SIGNAL" # Or D-MAC-SYNC?
            additional_info['description'] = 'Signaling'
        elif frame_type == 6:
            frame_type_name = "MAC-DATA"
            additional_info['description'] = 'User Data'
        elif frame_type == 7:
            frame_type_name = "MAC-U-BLK"
            additional_info['description'] = 'Block'
        else:
            frame_type_name = f"Type {frame_type}"
            additional_info['description'] = f'Raw type {frame_type}'

        # Extract encryption indicator - be aggressive, assume encrypted unless proven clear
        encrypted = True  # Default to encrypted
        encryption_algorithm = 'TEA1'  # Default algorithm
        key_id = '0'
        
        # Check for clear mode indicators
        # In MAC-RESOURCE (type 0), encryption flag is often at bit 39 (after fill bits)
        # This is highly dependent on PDU type.
        # Simplified check: Look for "Air Interface Encryption" element
        
        # For now, we'll rely on the protocol parser for detailed analysis
        # but keep the basic structure here
        
        frame_data = {
            'type': frame_type,
            'type_name': frame_type_name, # Add human readable name
            'number': frame_number,
            'bits': frame_bits,
            'header': header.bin,
            'position': start_pos,
            'encrypted': encrypted,
            'encryption_algorithm': encryption_algorithm,
            'key_id': key_id,
            'additional_info': additional_info
        }
        
        # Parse protocol layers (PHY/MAC/higher) - with error handling
        try:
            # Parse burst structure - be more lenient
            burst = self.protocol_parser.parse_burst(
                np.array(frame_bits), 
                slot_number=frame_number % 4
            )
            
            if burst:
                frame_data['burst_crc'] = burst.crc_ok
                
                # Parse MAC PDU even if CRC failed (may still be partially valid)
                try:
                    mac_pdu = self.protocol_parser.parse_mac_pdu(burst.data_bits)
                    
                    if mac_pdu:
                        frame_data['mac_pdu'] = {
                            'type': mac_pdu.pdu_type.name,
                            'encrypted': mac_pdu.encrypted,
                            'address': mac_pdu.address,
                            'length': mac_pdu.length,
                            'data': mac_pdu.data  # Add data field
                        }
                        
                        # Update encryption status from MAC PDU
                        # Be more conservative: only trust MAC PDU if we have strong evidence
                        if mac_pdu.encrypted:
                            # MAC PDU explicitly says encrypted - trust it
                            encrypted = True
                            frame_data['encrypted'] = True
                            if not encryption_algorithm:
                                encryption_algorithm = 'TEA1'
                                frame_data['encryption_algorithm'] = 'TEA1'
                        else:
                            # MAC PDU says not encrypted - verify with heuristics
                            # Check data entropy to confirm it's really clear mode
                            if len(mac_pdu.data) > 0:
                                # Calculate simple entropy check
                                unique_bytes = len(set(mac_pdu.data))
                                total_bytes = len(mac_pdu.data)
                                entropy_ratio = unique_bytes / max(total_bytes, 1)
                                
                                # Low entropy suggests clear mode (structured data)
                                # High entropy suggests encrypted (random-looking)
                                # Threshold: if >70% unique bytes, likely encrypted
                                if entropy_ratio > 0.7 and total_bytes > 8:
                                    # High entropy - likely encrypted despite flag
                                    logger.debug(f"Frame {frame_number}: High entropy ({entropy_ratio:.2f}) suggests encryption despite clear flag")
                                    encrypted = True
                                    frame_data['encrypted'] = True
                                else:
                                    # Low entropy - likely clear mode
                                    encrypted = False
                                    frame_data['encrypted'] = False
                                    frame_data['encryption_algorithm'] = None
                                    logger.debug(f"Frame {frame_number}: Low entropy ({entropy_ratio:.2f}) confirms clear mode")
                            else:
                                # No data to check - trust MAC PDU flag
                                encrypted = False
                                frame_data['encrypted'] = False
                                frame_data['encryption_algorithm'] = None
                        
                        # Extract call metadata if available
                        call_meta = self.protocol_parser.parse_call_metadata(mac_pdu)
                        if call_meta:
                            frame_data['call_metadata'] = {
                                'call_type': call_meta.call_type,
                                'talkgroup_id': call_meta.talkgroup_id,
                                'source_ssi': call_meta.source_ssi,
                                'dest_ssi': call_meta.dest_ssi,
                                'channel': call_meta.channel_allocated,
                                'encryption': call_meta.encryption_enabled,
                                'encryption_alg': call_meta.encryption_algorithm
                            }
                            
                            # Update additional_info with metadata
                            if call_meta.talkgroup_id:
                                additional_info['talkgroup'] = call_meta.talkgroup_id
                            if call_meta.source_ssi:
                                additional_info['source_ssi'] = call_meta.source_ssi
                        
                        # Try to decode SDS message if not encrypted
                        if not mac_pdu.encrypted:
                            sds_text = self.protocol_parser.parse_sds_message(mac_pdu)
                            if sds_text:
                                frame_data['sds_message'] = sds_text
                                additional_info['sds_text'] = sds_text[:50]  # First 50 chars
                except Exception as e:
                    logger.debug(f"MAC PDU parsing error: {e}")
                    # Continue even if MAC parsing fails
        except Exception as e:
            logger.debug(f"Protocol parsing error: {e}")
        
        # NOW attempt decryption if marked as encrypted
        if frame_data.get('encrypted') and (self.key_manager or self.auto_decrypt):
            frame_data = self._decrypt_frame(frame_data)
            
            # If decryption successful, try to parse SDS again with decrypted data
            if frame_data.get('decrypted') and 'decrypted_bytes' in frame_data:
                try:
                    # Create a temporary MacPDU with decrypted data
                    decrypted_bytes = bytes.fromhex(frame_data['decrypted_bytes'])
                    
                    # Use protocol parser to handle SDS data properly
                    sds_text = self.protocol_parser.parse_sds_data(decrypted_bytes)
                    if sds_text:
                        frame_data['sds_message'] = sds_text
                        frame_data['decoded_text'] = sds_text
                        additional_info['sds_text'] = sds_text[:50]
                except:
                    pass
        
        return frame_data

    def _decrypt_frame(self, frame_data: dict) -> dict:
        """
        Decrypt frame payload - AGGRESSIVE bruteforce with all common keys.
        Auto-tries common keys if no key manager or key not found.
        
        Args:
            frame_data: Frame data dictionary
            
        Returns:
            Updated frame data with decrypted payload
        """
        algorithm = frame_data.get('encryption_algorithm', 'TEA1')
        key_id = frame_data.get('key_id', '0')
        
        # Extract payload once (after header, typically starts at bit 32)
        payload_bits = frame_data['bits'][32:]
        
        # Convert to bytes
        try:
            payload_bytes = BitArray(payload_bits).tobytes()
        except Exception as e:
            frame_data['decrypted'] = False
            frame_data['decryption_error'] = f'Invalid payload format: {e}'
            logger.debug(f"Payload format error: {e}")
            return frame_data
        
        # Ensure payload is multiple of 8 bytes for block cipher
        if len(payload_bytes) < 8:
            frame_data['decrypted'] = False
            frame_data['decryption_error'] = 'Payload too short for decryption'
            return frame_data
        
        if len(payload_bytes) % 8 != 0:
            padding = 8 - (len(payload_bytes) % 8)
            payload_bytes += b'\x00' * padding
        
        keys_to_try = []
        
        # Try key from key manager first
        if self.key_manager and self.key_manager.has_key(algorithm, key_id):
            key = self.key_manager.get_key(algorithm, key_id)
            keys_to_try.append((key, f"{algorithm} key_id={key_id} (from file)"))
            logger.info(f"Trying key from file for {algorithm}")
        
        # ALWAYS add common keys for bruteforce (OpenEar style)
        if algorithm in self.common_keys:
            for idx, common_key in enumerate(self.common_keys[algorithm]):
                keys_to_try.append((common_key, f"{algorithm} common_key_{idx}"))
        
        # Also try with other algorithms if primary fails
        for other_alg in ['TEA1', 'TEA2', 'TEA3']:
            if other_alg != algorithm and other_alg in self.common_keys:
                for idx, common_key in enumerate(self.common_keys[other_alg][:5]):  # Try first 5
                    keys_to_try.append((common_key, f"{other_alg} common_key_{idx} (cross-try)"))
        
        # If no keys to try, bail out
        if not keys_to_try:
            frame_data['decrypted'] = False
            frame_data['decryption_error'] = 'No keys available'
            logger.warning("No keys available for decryption")
            return frame_data
        
        logger.info(f"Trying {len(keys_to_try)} keys for frame {frame_data['number']}")
        
        # Try each key
        best_result = None
        best_score = 0
        
        for key, key_desc in keys_to_try:
            try:
                decryptor = TEADecryptor(key, algorithm)
                decrypted_payload = decryptor.decrypt(payload_bytes)
                
                # Score the decrypted data (how "good" it looks)
                # More lenient scoring for TETRA
                score = 0
                
                # Count printable ASCII (32-126)
                printable_count = sum(1 for b in decrypted_payload if 32 <= b <= 126)
                score += printable_count * 2
                
                # Check for reasonable byte distribution (not all same)
                unique_bytes = len(set(decrypted_payload))
                if unique_bytes > len(decrypted_payload) // 8:  # At least 12.5% unique (more lenient)
                    score += 30
                
                # Penalize all zeros or all 0xFF (but less)
                if decrypted_payload == b'\x00' * len(decrypted_payload):
                    score -= 50  # Less penalty
                if decrypted_payload == b'\xFF' * len(decrypted_payload):
                    score -= 50
                
                # Check for common TETRA patterns
                if len(decrypted_payload) >= 4:
                    # Look for reasonable header patterns
                    first_bytes = decrypted_payload[:4]
                    # Add points if it looks like structured data
                    if first_bytes[0] != 0 and first_bytes[0] != 0xFF:
                        score += 10
                    
                    # Check for TETRA-specific byte patterns (common in traffic)
                    # TETRA often has specific sync bytes
                    if first_bytes[0] in [0x01, 0x02, 0x03, 0x04, 0x05, 0x08, 0x0A, 0x0C]:
                        score += 20
                
                # More lenient entropy check
                if unique_bytes > 1:  # Any diversity is good
                    score += 10
                
                if score > best_score:
                    best_score = score
                    best_result = (decrypted_payload, key_desc)
                
                # Lower threshold - accept more attempts
                if score > 50:  # Was 200, now 50 for more lenient acceptance
                    logger.info(f"Good decryption score {score} with {key_desc}")
                    break
                    
            except Exception as e:
                logger.debug(f"Key {key_desc} failed: {e}")
                continue
        
        # Use the best result if we found one (more lenient threshold)
        if best_result and best_score > 10:  # Was > 0, now > 10 to avoid total garbage
            decrypted_payload, key_desc = best_result
            
            # Convert back to bits
            decrypted_bits = BitArray(decrypted_payload)
            
            frame_data['decrypted'] = True
            frame_data['decrypted_payload'] = decrypted_bits.bin
            frame_data['decrypted_bytes'] = decrypted_payload.hex()
            frame_data['key_used'] = key_desc
            frame_data['decrypt_confidence'] = best_score
            logger.info(f"✓ Decrypted frame {frame_data['number']} using {key_desc} (confidence: {best_score})")
        else:
            # All keys failed or low confidence
            frame_data['decrypted'] = False
            if not keys_to_try:
                frame_data['decryption_error'] = 'No keys available'
            else:
                frame_data['decryption_error'] = f'Tried {len(keys_to_try)} key(s), best score: {best_score}'
                logger.debug(f"All keys failed for frame {frame_data['number']}, best score: {best_score}")
        
        return frame_data
    
    def decode(self, symbols):
        """
        Decode TETRA frames from symbol stream.
        
        Args:
            symbols: Demodulated symbols
            
        Returns:
            List of decoded frames
        """
        # Convert symbols to bits
        bits = self.symbols_to_bits(symbols)
        
        # Find synchronization patterns
        sync_positions = self.find_sync(bits)
        
        if not sync_positions:
            logger.warning("No synchronization patterns found")
            return []
        
        # Decode frames
        frames = []
        for pos in sync_positions:
            frame = self.decode_frame(bits, pos)
            if frame:
                frames.append(frame)
                logger.info(f"Decoded frame {frame['number']} (type: {frame['type']}) at position {pos}")
        
        return frames
    
    def format_frame_info(self, frame):
        """
        Format frame information for display with meaningful interpretation.
        
        Args:
            frame: Decoded frame dictionary
            
        Returns:
            Formatted string
        """
        info = f"Frame #{frame['number']} (Type: {self._get_frame_type_name(frame['type'])})"
        info += f"\n  Position: {frame['position']}"
        info += f"\n  Header: {frame['header'][:32]}..."
        
        # Add frame type specific info
        frame_type = frame['type']
        if frame_type == 0:
            info += "\n  📡 Broadcast Frame - System information"
        elif frame_type == 1:
            info += "\n  📞 Traffic Frame - Voice/Data channel"
        elif frame_type == 2:
            info += "\n  🔗 Control Frame - Signaling"
        elif frame_type == 3:
            info += "\n  📋 MAC Frame - Medium Access Control"
        
        if frame.get('encrypted'):
            info += f"\n  🔒 Encrypted: Yes ({frame.get('encryption_algorithm', 'Unknown')})"
            if frame.get('decrypted'):
                info += f"\n  ✅ Decrypted: Yes"
                if 'key_used' in frame:
                    info += f" - {frame['key_used']}"
                if 'decrypted_bytes' in frame:
                    # Try to interpret payload
                    payload_hex = frame['decrypted_bytes'][:64]
                    info += f"\n  📦 Payload (hex): {payload_hex}..."
                    
                    # Try to decode as text using protocol parser
                    try:
                        payload_bytes = bytes.fromhex(frame['decrypted_bytes'])
                        text = self.protocol_parser.parse_sds_data(payload_bytes)
                        if text:
                            info += f"\n  📝 Content: {text}"
                            frame['decoded_text'] = text  # Store for GUI
                    except:
                        pass
            else:
                info += f"\n  ❌ Decrypted: No"
                if 'decryption_error' in frame:
                    info += f" ({frame['decryption_error']})"
        else:
            info += f"\n  🔓 Encrypted: No"
            # Show raw payload for unencrypted frames
            if len(frame['bits']) > 32:
                payload_bits = frame['bits'][32:96]  # Next 64 bits
                payload_hex = ''.join(f"{int(payload_bits[i:i+8].tobytes().hex(), 16):02x}" 
                                     for i in range(0, min(64, len(payload_bits)), 8) 
                                     if i+8 <= len(payload_bits))
                info += f"\n  📦 Payload: {payload_hex}..."
        
        return info
    
    def _get_frame_type_name(self, frame_type):
        """Get human-readable frame type name."""
        frame_types = {
            0: "Broadcast",
            1: "Traffic",
            2: "Control", 
            3: "MAC",
            4: "Supplementary",
            5: "Reserved",
            6: "Reserved",
            7: "Reserved"
        }
        return frame_types.get(frame_type, f"Unknown({frame_type})")
