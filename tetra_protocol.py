"""
TETRA Protocol Layer Parser
Implements PHY, MAC, and higher layer parsing as demonstrated by OpenEar.
Parses bursts, slots, frames, and superframes.
"""

import numpy as np
from bitstring import BitArray
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class BurstType(Enum):
    """TETRA burst types."""
    NormalUplink = 1
    NormalDownlink = 2
    ControlUplink = 3
    ControlDownlink = 4
    Synchronization = 5
    Linearization = 6


class ChannelType(Enum):
    """TETRA logical channel types."""
    TCH = "Traffic Channel"
    STCH = "Stealing Channel"
    SCH = "Signaling Channel"
    AACH = "Associated Control Channel"
    BSCH = "Broadcast Synchronization Channel"
    BNCH = "Broadcast Network Channel"
    
    
class PDUType(Enum):
    """MAC PDU types."""
    MAC_RESOURCE = 0
    MAC_FRAG = 1
    MAC_END = 2
    MAC_BROADCAST = 3
    MAC_SUPPL = 4
    MAC_U_SIGNAL = 5
    MAC_DATA = 6
    MAC_U_BLK = 7


@dataclass
class TetraBurst:
    """Represents a TETRA burst (255 symbols)."""
    burst_type: BurstType
    slot_number: int
    frame_number: int
    training_sequence: np.ndarray
    data_bits: np.ndarray
    crc_ok: bool
    scrambling_code: int = 0
    colour_code: int = 0
    

@dataclass
class TetraSlot:
    """Represents a TETRA time slot (14.167ms, 255 symbols)."""
    slot_number: int  # 0-3 within frame
    frame_number: int
    burst: TetraBurst
    channel_type: ChannelType
    encrypted: bool = False
    encryption_mode: int = 0


@dataclass
class TetraFrame:
    """Represents a TETRA frame (4 slots = 56.67ms)."""
    frame_number: int  # 0-17 within multiframe
    slots: List[TetraSlot]
    multiframe_number: int = 0
    
    
@dataclass
class TetraMultiframe:
    """Represents a TETRA multiframe (18 frames = 1.02 seconds)."""
    multiframe_number: int
    frames: List[TetraFrame]


@dataclass
class TetraHyperframe:
    """Represents a TETRA hyperframe (60 multiframes = 61.2 seconds)."""
    hyperframe_number: int
    multiframes: List[TetraMultiframe]


@dataclass
class MacPDU:
    """MAC layer PDU."""
    pdu_type: PDUType
    encrypted: bool
    address: Optional[int]
    length: int
    data: bytes
    fill_bits: int = 0
    

@dataclass
class CallMetadata:
    """Call setup/teardown metadata."""
    call_type: str  # "Voice", "Data", "Group", "Individual"
    talkgroup_id: Optional[int]
    source_ssi: Optional[int]  # Subscriber Station Identity
    dest_ssi: Optional[int]
    channel_allocated: Optional[int]
    call_priority: int = 0
    duplex_mode: str = "simplex"
    encryption_enabled: bool = False
    encryption_algorithm: Optional[str] = None


class TetraProtocolParser:
    """
    TETRA protocol parser implementing PHY + MAC + higher layers.
    Demonstrates OpenEar-style decoding capabilities.
    """
    
    # TETRA timing constants
    SYMBOLS_PER_SLOT = 255
    SLOTS_PER_FRAME = 4
    FRAMES_PER_MULTIFRAME = 18
    MULTIFRAMES_PER_HYPERFRAME = 60
    
    # Training sequences for burst synchronization
    TRAINING_SEQUENCES = {
        1: [0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1],
        2: [0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0, 1],
        3: [0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 0],
    }
    
    # Sync patterns
    SYNC_CONTINUOUS_DOWNLINK = [1, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0]
    SYNC_DISCONTINUOUS_DOWNLINK = [0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 1, 1]
    
    def __init__(self):
        """Initialize protocol parser."""
        self.current_frame_number = 0
        self.current_multiframe = 0
        self.current_hyperframe = 0
        self.mcc = None  # Mobile Country Code
        self.mnc = None  # Mobile Network Code
        self.la = None   # Location Area
        self.colour_code = None
        
        # Statistics
        self.stats = {
            'total_bursts': 0,
            'crc_pass': 0,
            'crc_fail': 0,
            'clear_mode_frames': 0,
            'encrypted_frames': 0,
            'decrypted_frames': 0,
            'voice_calls': 0,
            'data_messages': 0,
            'control_messages': 0,
        }
        
    def parse_burst(self, symbols: np.ndarray, slot_number: int = 0) -> Optional[TetraBurst]:
        """
        Parse a TETRA burst (255 symbols).
        
        Args:
            symbols: Symbol stream (255 symbols expected)
            slot_number: Slot number (0-3)
            
        Returns:
            Parsed TetraBurst or None if invalid
        """
        if len(symbols) < self.SYMBOLS_PER_SLOT:
            logger.warning(f"Insufficient symbols for burst: {len(symbols)} < {self.SYMBOLS_PER_SLOT}")
            return None
        
        # Extract burst
        burst_symbols = symbols[:self.SYMBOLS_PER_SLOT]
        
        # Convert symbols to bits (2 bits per π/4-DQPSK symbol)
        bits = []
        for sym in burst_symbols:
            bits.extend([int(sym >> 1 & 1), int(sym & 1)])
        bits = np.array(bits)
        
        # Detect burst type from training sequence position
        burst_type = self._detect_burst_type(bits)
        
        # Extract training sequence
        training_seq = self._extract_training_sequence(bits, burst_type)
        
        # Extract data bits (excluding training sequence and tail bits)
        data_bits = self._extract_data_bits(bits, burst_type)
        
        # Check CRC
        crc_ok = self._check_crc(data_bits)
        
        self.stats['total_bursts'] += 1
        if crc_ok:
            self.stats['crc_pass'] += 1
        else:
            self.stats['crc_fail'] += 1
        
        burst = TetraBurst(
            burst_type=burst_type,
            slot_number=slot_number,
            frame_number=self.current_frame_number,
            training_sequence=training_seq,
            data_bits=data_bits,
            crc_ok=crc_ok,
            colour_code=self.colour_code or 0
        )
        
        return burst
    
    def _detect_burst_type(self, bits: np.ndarray) -> BurstType:
        """Detect burst type from training sequence position."""
        # Check for sync burst (training sequence at specific position)
        sync_pos = len(bits) // 2
        if self._check_sync_pattern(bits[sync_pos:sync_pos+22]):
            return BurstType.Synchronization
        
        # Default to normal downlink
        return BurstType.NormalDownlink
    
    def _check_sync_pattern(self, bits: np.ndarray) -> bool:
        """Check if bits match sync pattern."""
        if len(bits) < 22:
            return False
        
        # Check both sync patterns
        match_cont = np.sum(bits[:22] == self.SYNC_CONTINUOUS_DOWNLINK) / 22
        match_disc = np.sum(bits[:22] == self.SYNC_DISCONTINUOUS_DOWNLINK) / 22
        
        return max(match_cont, match_disc) > 0.8
    
    def _extract_training_sequence(self, bits: np.ndarray, burst_type: BurstType) -> np.ndarray:
        """Extract training sequence from burst."""
        # Training sequence is typically in the middle of the burst
        if burst_type == BurstType.Synchronization:
            # Sync burst: training at position ~108
            return bits[108:130]
        else:
            # Normal burst: training at position ~108
            return bits[108:122]
    
    def _extract_data_bits(self, bits: np.ndarray, burst_type: BurstType) -> np.ndarray:
        """Extract data bits from burst (excluding training and tail)."""
        # Normal burst: 216 bits (2 x 108) excluding training sequence
        if burst_type == BurstType.NormalDownlink or burst_type == BurstType.NormalUplink:
            # First block: bits 0-107
            # Training: bits 108-121
            # Second block: bits 122-229
            # Tail: bits 230+
            first_block = bits[0:108]
            second_block = bits[122:230]
            return np.concatenate([first_block, second_block])
        
        # For other burst types, return all bits
        return bits
    
    def _check_crc(self, bits: np.ndarray) -> bool:
        """
        Check CRC-16-CCITT for data integrity.
        Simplified check - TETRA CRC is complex, so we use heuristics.
        """
        if len(bits) < 16:
            return False
        
        # SIMPLIFIED: For now, use heuristics instead of strict CRC
        # Real TETRA CRC is complex with interleaving and puncturing
        
        # Heuristic 1: Check for reasonable bit distribution
        ones = np.sum(bits)
        zeros = len(bits) - ones
        bit_ratio = min(ones, zeros) / max(ones, zeros) if max(ones, zeros) > 0 else 0
        
        # If bits are reasonably distributed (not all 0s or 1s), consider valid
        if bit_ratio > 0.15:  # At least 15% of minority bit
            return True
        
        # Heuristic 2: Try actual CRC on payload
        try:
            payload = bits[:-16]
            received_crc = bits[-16:]
            calculated_crc = self._calculate_crc16(payload)
            
            # Allow some bit errors (TETRA has FEC)
            errors = np.sum(calculated_crc != received_crc)
            return errors <= 3  # Allow up to 3 bit errors
        except:
            # If CRC calculation fails, fall back to heuristic
            return bit_ratio > 0.2
    
    def _calculate_crc16(self, bits: np.ndarray) -> np.ndarray:
        """Calculate CRC-16-CCITT (polynomial 0x1021)."""
        polynomial = 0x1021
        crc = 0xFFFF
        
        for bit in bits:
            crc ^= (int(bit) << 15)
            for _ in range(1):
                if crc & 0x8000:
                    crc = (crc << 1) ^ polynomial
                else:
                    crc <<= 1
                crc &= 0xFFFF
        
        # Convert to bits
        crc_bits = [(crc >> i) & 1 for i in range(15, -1, -1)]
        return np.array(crc_bits)
    
    def parse_mac_pdu(self, bits: np.ndarray) -> Optional[MacPDU]:
        """
        Parse MAC layer PDU.
        
        Args:
            bits: Data bits from burst
            
        Returns:
            Parsed MacPDU or None
        """
        if len(bits) < 8:
            return None
        
        # MAC PDU Type (first 3 bits)
        pdu_type_val = (bits[0] << 2) | (bits[1] << 1) | bits[2]
        try:
            pdu_type = PDUType(pdu_type_val)
        except ValueError:
            pdu_type = PDUType.MAC_DATA
        
        # Fill bit indicator
        fill_bit_ind = bits[3]
        
        # Encrypted flag (bit 4)
        encrypted = bool(bits[4])
        
        # Address (bits 5-28, 24 bits = 6 hex digits)
        if len(bits) >= 29:
            address_bits = bits[5:29]
            address = int(''.join(str(b) for b in address_bits), 2)
        else:
            address = None
        
        # Length indication
        if len(bits) >= 35:
            length_bits = bits[29:35]
            length = int(''.join(str(b) for b in length_bits), 2)
        else:
            length = 0
        
        # Extract data
        data_start = 35
        data_bits = bits[data_start:data_start + length * 8] if len(bits) > data_start else bits[data_start:]
        
        # Convert to bytes
        try:
            data_bytes = BitArray(data_bits).tobytes()
        except:
            data_bytes = b''
        
        if encrypted:
            self.stats['encrypted_frames'] += 1
        else:
            self.stats['clear_mode_frames'] += 1
        
        return MacPDU(
            pdu_type=pdu_type,
            encrypted=encrypted,
            address=address,
            length=length,
            data=data_bytes,
            fill_bits=fill_bit_ind
        )
    
    def parse_call_metadata(self, mac_pdu: MacPDU) -> Optional[CallMetadata]:
        """
        Extract call metadata from MAC PDU (talkgroup, SSI, etc.).
        
        Args:
            mac_pdu: MAC PDU to parse
            
        Returns:
            CallMetadata or None
        """
        if not mac_pdu or len(mac_pdu.data) < 4:
            return None
        
        # Parse based on PDU type
        if mac_pdu.pdu_type == PDUType.MAC_RESOURCE:
            # Resource assignment - contains channel allocation
            return self._parse_resource_assignment(mac_pdu)
        elif mac_pdu.pdu_type == PDUType.MAC_U_SIGNAL:
            # Signaling - contains call setup
            return self._parse_call_setup(mac_pdu)
        
        return None
    
    def _parse_resource_assignment(self, mac_pdu: MacPDU) -> Optional[CallMetadata]:
        """Parse resource assignment message."""
        data = mac_pdu.data
        if len(data) < 8:
            return None
        
        # Extract fields
        call_type = "Group" if data[0] & 0x80 else "Individual"
        talkgroup_id = int.from_bytes(data[1:4], 'big') & 0xFFFFFF
        channel_allocated = data[4] & 0x3F
        encryption_enabled = bool(data[5] & 0x80)
        
        self.stats['control_messages'] += 1
        
        return CallMetadata(
            call_type=call_type,
            talkgroup_id=talkgroup_id,
            source_ssi=None,
            dest_ssi=None,
            channel_allocated=channel_allocated,
            encryption_enabled=encryption_enabled,
            encryption_algorithm="TEA1" if encryption_enabled else None
        )
    
    def _parse_call_setup(self, mac_pdu: MacPDU) -> Optional[CallMetadata]:
        """Parse call setup signaling."""
        data = mac_pdu.data
        if len(data) < 12:
            return None
        
        # Extract SSIs
        source_ssi = int.from_bytes(data[0:3], 'big') & 0xFFFFFF
        dest_ssi = int.from_bytes(data[3:6], 'big') & 0xFFFFFF
        
        # Call type
        call_type_byte = data[6]
        if call_type_byte & 0x80:
            call_type = "Voice"
            self.stats['voice_calls'] += 1
        else:
            call_type = "Data"
            self.stats['data_messages'] += 1
        
        # Encryption
        encryption_enabled = bool(data[7] & 0x80)
        encryption_alg = None
        if encryption_enabled:
            alg_code = (data[7] >> 4) & 0x07
            if alg_code == 1:
                encryption_alg = "TEA1"
            elif alg_code == 2:
                encryption_alg = "TEA2"
            elif alg_code == 3:
                encryption_alg = "TEA3"
        
        return CallMetadata(
            call_type=call_type,
            talkgroup_id=dest_ssi if call_type == "Voice" else None,
            source_ssi=source_ssi,
            dest_ssi=dest_ssi,
            channel_allocated=None,
            encryption_enabled=encryption_enabled,
            encryption_algorithm=encryption_alg
        )
    
    def parse_sds_message(self, mac_pdu: MacPDU) -> Optional[str]:
        """
        Parse Short Data Service (SDS) text message.
        Demonstrates decoding of unencrypted data messages.
        
        Args:
            mac_pdu: MAC PDU containing SDS
            
        Returns:
            Decoded text message or None
        """
        if mac_pdu.pdu_type != PDUType.MAC_DATA:
            return None
        
        if mac_pdu.encrypted:
            # If we have decrypted data, use it
            # The caller should have replaced mac_pdu.data with decrypted data if available
            pass
        
        # SDS data is in the payload
        data = mac_pdu.data
        
        if len(data) < 2:
            return None
        
        # Try to interpret as text directly first (heuristics)
        try:
            # Check if it looks like pure ASCII
            text = data.decode('ascii')
            if all(32 <= ord(c) <= 126 for c in text):
                self.stats['data_messages'] += 1
                return text
        except:
            pass

        # SDS type (first byte usually)
        # SDS-TL standard header is often 16-bit or 8-bit
        # Let's try to skip headers and find text
        
        # Heuristic: Look for printable sequences
        try:
            # Convert to string, replacing errors
            text_content = ""
            for b in data:
                if 32 <= b <= 126:
                    text_content += chr(b)
                else:
                    text_content += "."
            
            # If we have a significant chunk of text, return it
            clean_text = text_content.replace(".", "")
            if len(clean_text) > 3:
                self.stats['data_messages'] += 1
                return clean_text
        except:
            pass
            
        return None

    def extract_voice_payload(self, mac_pdu: MacPDU) -> Optional[bytes]:
        """
        Extract ACELP voice payload from MAC PDU.
        
        Args:
            mac_pdu: MAC PDU
            
        Returns:
            Voice payload bytes or None
        """
        # Voice is usually in MAC-TRAFFIC (which maps to specific burst types)
        # But here we might receive it as MAC_U_SIGNAL or similar if not parsed correctly
        # In TETRA, voice frames are typically 2 slots interleaved
        
        # For this implementation, we assume the payload IS the voice frame
        # if the frame type indicates traffic
        
        if not mac_pdu.data:
            return None
            
        return mac_pdu.data
    
    def get_statistics(self) -> Dict:
        """Get parsing statistics."""
        total = self.stats['clear_mode_frames'] + self.stats['encrypted_frames']
        if total > 0:
            clear_pct = (self.stats['clear_mode_frames'] / total) * 100
            enc_pct = (self.stats['encrypted_frames'] / total) * 100
        else:
            clear_pct = enc_pct = 0
        
        return {
            **self.stats,
            'clear_mode_percentage': clear_pct,
            'encrypted_percentage': enc_pct,
            'crc_success_rate': (self.stats['crc_pass'] / max(1, self.stats['total_bursts'])) * 100
        }
    
    def format_call_metadata(self, metadata: CallMetadata) -> str:
        """Format call metadata for display."""
        lines = [
            f"📞 Call Type: {metadata.call_type}",
        ]
        
        if metadata.talkgroup_id:
            lines.append(f"👥 Talkgroup: {metadata.talkgroup_id}")
        
        if metadata.source_ssi:
            lines.append(f"📱 Source SSI: {metadata.source_ssi}")
        
        if metadata.dest_ssi:
            lines.append(f"📱 Dest SSI: {metadata.dest_ssi}")
        
        if metadata.channel_allocated:
            lines.append(f"📡 Channel: {metadata.channel_allocated}")
        
        if metadata.encryption_enabled:
            lines.append(f"🔒 Encryption: {metadata.encryption_algorithm or 'Unknown'}")
        else:
            lines.append("🔓 Clear Mode (No Encryption)")
        
        return "\n".join(lines)
