"""
TETRA Protocol Layer Parser

This module implements PHY, MAC, and higher layer parsing for TETRA frames.
Parses bursts, slots, frames, and superframes according to ETSI TETRA standards.

Classes:
    TetraProtocolParser: Main protocol parser for TETRA frames
    TetraBurst: Represents a TETRA burst
    MacPDU: Represents a MAC layer PDU
    CallMetadata: Metadata for TETRA calls

Enums:
    BurstType: TETRA burst types
    ChannelType: TETRA logical channel types
    PDUType: MAC PDU types

Example:
    >>> from tetraear.core.protocol import TetraProtocolParser
    >>> parser = TetraProtocolParser()
    >>> burst = parser.parse_burst(symbols, slot_number=0)
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
    encryption_mode: int = 0  # 0=Clear, 1=Class2, 2=Class3, 3=Reserved
    reassembled_data: Optional[bytes] = None  # For fragmented messages
    

@dataclass
class CallMetadata:
    """Call setup/teardown metadata."""
    call_type: str  # "Voice", "Data", "Group", "Individual"
    talkgroup_id: Optional[int]
    source_ssi: Optional[int]  # Subscriber Station Identity
    dest_ssi: Optional[int]
    channel_allocated: Optional[int]
    call_identifier: Optional[int] = None
    call_priority: int = 0
    mcc: Optional[int] = None
    mnc: Optional[int] = None
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
        
        # Fragmentation handling
        self.fragment_buffer = bytearray()
        self.fragment_metadata = {}
        
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
        
        # SIMPLIFIED: Use a soft CRC check since we do not do full channel decoding.
        ones = int(np.sum(bits))
        zeros = len(bits) - ones
        if ones == 0 or zeros == 0:
            return False

        try:
            payload = bits[:-16]
            received_crc = bits[-16:]
            calculated_crc = self._calculate_crc16(payload)
            
            errors = int(np.sum(calculated_crc != received_crc))
            if errors == 0:
                return True

            # Allow a small error budget without channel decoding.
            if errors <= 2:
                return True

            # Try reversed bit order to handle endianness mismatches.
            reversed_crc = self._calculate_crc16(payload[::-1])
            errors_rev = int(np.sum(reversed_crc != received_crc))
            if errors_rev == 0:
                return True
            if errors_rev <= 2:
                return True
        except Exception:
            return False
        
        return False
    
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
        Handles fragmentation (MAC-RESOURCE, MAC-FRAG, MAC-END).
        
        Args:
            bits: Data bits from burst
            
        Returns:
            Parsed MacPDU or None
        """
        if len(bits) < 8:
            return None
        
        # MAC PDU Type (first 2 bits for Downlink)
        # 00: MAC-RESOURCE
        # 01: MAC-FRAG
        # 10: MAC-BROADCAST
        # 11: MAC-ENCRYPTED (or other, depending on context)
        
        pdu_type_int = (bits[0] << 1) | bits[1]
        
        # Map to internal Enum
        if pdu_type_int == 0:
            pdu_type = PDUType.MAC_RESOURCE
        elif pdu_type_int == 1:
            pdu_type = PDUType.MAC_FRAG
        elif pdu_type_int == 2:
            pdu_type = PDUType.MAC_BROADCAST
        else:
            # Type 3 is often MAC-END or MAC-U-SIGNAL depending on context/uplink/downlink
            # For Downlink, 11 is often reserved or proprietary, or MAC-D-BLCK
            # Let's assume MAC-END for now if it fits the structure
            pdu_type = PDUType.MAC_END

        # Encryption Mode (Bits 2-3)
        # 00: Class 1 (Clear)
        # 01: Class 2 (SCK)
        # 10: Class 3 (DCK)
        # 11: Reserved
        encryption_mode_val = (bits[2] << 1) | bits[3]
        encrypted = encryption_mode_val > 0
        
        # Default fields
        address = None
        length = 0
        data_bytes = b''
        fill_bit_ind = 0
        
        # Parse based on PDU Type
        if pdu_type == PDUType.MAC_RESOURCE:
            # MAC-RESOURCE
            # Bits: Type(2), EncMode(2), Fill(1), ...
            fill_bit_ind = bits[4]
            
            # Position pointer
            pos = 5
            
            # Encryption (already parsed mode)
            
            # Address (24 bits)
            if len(bits) >= pos + 24:
                address_bits = bits[pos:pos+24]
                address = int(''.join(str(b) for b in address_bits), 2)
                pos += 24
            else:
                return None # Truncated
            
            # Length (6 bits)
            if len(bits) >= pos + 6:
                length_bits = bits[pos:pos+6]
                length = int(''.join(str(b) for b in length_bits), 2)
                pos += 6
            else:
                return None # Truncated
                
            # Data
            # If length is 0, it might mean "rest of slot" or specific rule
            # Standard says: Length indicator 000000 means Null PDU or similar?
            # Actually, length is in octets (bytes) usually.
            
            data_len_bits = length * 8
            
            # STRICT CHECK: Data length cannot exceed remaining bits significantly
            if data_len_bits > len(bits) - pos + 16: # Allow small margin
                return None
            
            if data_len_bits > 0 and len(bits) >= pos + data_len_bits:
                data_bits = bits[pos:pos + data_len_bits]
            else:
                data_bits = bits[pos:]
                
            try:
                data_bytes = BitArray(data_bits).tobytes()
            except:
                data_bytes = b''
                
            # Start fragmentation buffer
            # Only start if this looks like the beginning of a message
            self.fragment_buffer = bytearray(data_bytes)
            self.fragment_metadata = {'address': address, 'encrypted': encrypted, 'mode': encryption_mode_val}
            
        elif pdu_type == PDUType.MAC_FRAG:
            # MAC-FRAG
            # Bits: Type(2), EncMode(2), Fill(1), ...
            fill_bit_ind = bits[4]
            pos = 5
            
            data_bits = bits[pos:]
            try:
                data_bytes = BitArray(data_bits).tobytes()
            except:
                data_bytes = b''
                
            # Append to buffer
            self.fragment_buffer.extend(data_bytes)
            
            # Restore metadata
            if self.fragment_metadata:
                encrypted = self.fragment_metadata.get('encrypted', False)
                address = self.fragment_metadata.get('address')
            
        elif pdu_type == PDUType.MAC_BROADCAST:
            # MAC-BROADCAST
            # Bits: Type(2), BroadcastType(2), ...
            # BroadcastType: 00=SYSINFO, 01=ACCESS-DEFINE, ...
            broadcast_type = (bits[2] << 1) | bits[3]
            
            pos = 4
            # SYSINFO (Type 0)
            if broadcast_type == 0:
                # Parse SYSINFO elements
                # MCC(10), MNC(14), CC(6), ...
                if len(bits) >= pos + 30:
                    self.mcc = int(''.join(str(b) for b in bits[pos:pos+10]), 2)
                    self.mnc = int(''.join(str(b) for b in bits[pos+10:pos+24]), 2)
                    self.colour_code = int(''.join(str(b) for b in bits[pos+24:pos+30]), 2)
                    
                    # STRICT CHECK: MCC/MNC sanity - Real TETRA networks
                    # MCC must be 200-799 (valid ITU-T E.212 range)
                    if self.mcc < 200 or self.mcc > 799:
                        logger.debug(f"Invalid MCC {self.mcc} in SYNC - not real TETRA")
                        return None
                    if self.mnc > 999:
                        logger.debug(f"Invalid MNC {self.mnc} in SYNC - not real TETRA")
                        return None
                    
                    logger.info(f"Valid TETRA SYNC: MCC={self.mcc} MNC={self.mnc}")
                else:
                    return None
            
            data_bits = bits[pos:]
            try:
                data_bytes = BitArray(data_bits).tobytes()
            except:
                data_bytes = b''
                
        else:
            # Fallback / MAC-END
            # Bits: Type(2), EncMode(2), Fill(1), Length(6)?
            # MAC-END usually has structure: Type(2), EncMode(2), Fill(1), Length(6)
            fill_bit_ind = bits[4]
            pos = 5
            
            # Assuming Length is present for MAC-END
            if len(bits) >= pos + 6:
                length_bits = bits[pos:pos+6]
                length = int(''.join(str(b) for b in length_bits), 2)
                pos += 6
            else:
                # If no length field, treat as invalid for MAC-END
                return None
                
            data_len_bits = length * 8
            
            # STRICT CHECK
            if data_len_bits > len(bits) - pos + 16:
                return None
                
            if data_len_bits > 0 and len(bits) >= pos + data_len_bits:
                data_bits = bits[pos:pos + data_len_bits]
            else:
                data_bits = bits[pos:]
                
            try:
                data_bytes = BitArray(data_bits).tobytes()
            except:
                data_bytes = b''
                
            # Append and Finalize
            self.fragment_buffer.extend(data_bytes)
            
            # Restore metadata
            if self.fragment_metadata:
                encrypted = self.fragment_metadata.get('encrypted', False)
                address = self.fragment_metadata.get('address')

        if encrypted:
            self.stats['encrypted_frames'] += 1
        else:
            self.stats['clear_mode_frames'] += 1
        
        # Create PDU
        pdu = MacPDU(
            pdu_type=pdu_type,
            encrypted=encrypted,
            address=address,
            length=length,
            data=data_bytes,
            fill_bits=fill_bit_ind,
            encryption_mode=encryption_mode_val
        )
        
        # Attach reassembled data if this is the end
        # Logic:
        # 1. MAC-RESOURCE with full length (no fragmentation) -> Single packet
        # 2. MAC-END -> End of fragmentation chain
        
        # Check if MAC-RESOURCE is self-contained (not fragmented)
        # Usually indicated by a flag or context, but here we assume if it's MAC-RESOURCE
        # and we don't see a "More Bit" (which we haven't parsed yet), it might be single.
        # BUT, standard says MAC-RESOURCE starts a transaction.
        # If we treat every MAC-RESOURCE as start of buffer, and MAC-END as end.
        
        if pdu_type == PDUType.MAC_END:
             if self.fragment_buffer:
                pdu.reassembled_data = bytes(self.fragment_buffer)
                if self.fragment_metadata:
                    if not pdu.address: pdu.address = self.fragment_metadata.get('address')
                    # Inherit encryption from start of chain
                    pdu.encrypted = self.fragment_metadata.get('encrypted', False)
                
                # Clear buffer
                self.fragment_buffer = bytearray()
                self.fragment_metadata = {}
        
        elif pdu_type == PDUType.MAC_RESOURCE:
            # If this is a single-slot message (no fragmentation), we should treat it as such.
            # However, without parsing the "More Bit" (TM-SDU header), we can't be sure.
            # Heuristic: If length is small enough to fit in slot and we don't see MAC-FRAG next...
            # Better: Always expose current data, but also expose reassembled if MAC-END.
            # For MAC-RESOURCE, we just started the buffer. If it's a short message, 
            # it might be the whole message.
            # Let's tentatively set reassembled_data to current data for MAC-RESOURCE
            # so single-frame messages work.
            pdu.reassembled_data = bytes(data_bytes)
            
        return pdu
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
        elif mac_pdu.pdu_type == PDUType.MAC_BROADCAST:
            # Broadcast - contains network info
            return self._parse_broadcast(mac_pdu)
        
        return None
    
    def _parse_resource_assignment(self, mac_pdu: MacPDU) -> Optional[CallMetadata]:
        """Parse resource assignment message."""
        data = mac_pdu.data
        if len(data) < 8:
            return None
        
        # Extract fields (Heuristic mapping)
        # Byte 0: [CallType(1) | ... ]
        call_type = "Group" if data[0] & 0x80 else "Individual"
        
        # Bytes 1-3: Talkgroup/SSI (24 bits)
        talkgroup_id = int.from_bytes(data[1:4], 'big') & 0xFFFFFF
        
        # Byte 4: Channel Allocation
        channel_allocated = data[4] & 0x3F
        
        # Byte 5: Encryption & Priority
        encryption_enabled = bool(data[5] & 0x80)
        call_priority = (data[5] >> 2) & 0x0F  # Guessing priority location (4 bits)
        
        # Bytes 6-7: Call Identifier (14 bits)
        # Usually in the lower bits of byte 6 and upper of byte 7
        call_identifier = ((data[6] & 0x0F) << 10) | (data[7] << 2) # Rough guess
        
        # Try to find Source SSI (Calling Party) in the payload (TM-SDU)
        # This is a heuristic search for a 24-bit SSI that is NOT the talkgroup
        source_ssi = None
        if len(data) > 10:
            # Scan for potential SSIs (3 bytes)
            # Valid SSI range: 1 - 16777215 (0 is reserved, >16M is reserved/short)
            # We skip the first few bytes which are MAC header
            for i in range(8, len(data) - 3):
                val = int.from_bytes(data[i:i+3], 'big') & 0xFFFFFF
                # Heuristic: SSI should be different from TG, and look "reasonable"
                # Most user SSIs are > 1000 and < 16000000
                if val != talkgroup_id and 1000 < val < 16000000:
                    # Check if it looks like a valid SSI (not all FFs or 00s)
                    if val != 0xFFFFFF and val != 0:
                        source_ssi = val
                        break
        
        self.stats['control_messages'] += 1
        
        return CallMetadata(
            call_type=call_type,
            talkgroup_id=talkgroup_id,
            source_ssi=source_ssi,
            dest_ssi=None,
            channel_allocated=channel_allocated,
            call_identifier=call_identifier,
            call_priority=call_priority,
            mcc=self.mcc,
            mnc=self.mnc,
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
            elif alg_code == 4:
                encryption_alg = "TEA4"
        
        return CallMetadata(
            call_type=call_type,
            talkgroup_id=dest_ssi if call_type == "Voice" else None,
            source_ssi=source_ssi,
            dest_ssi=dest_ssi,
            channel_allocated=None,
            call_identifier=None,
            call_priority=0,
            mcc=self.mcc,
            mnc=self.mnc,
            encryption_enabled=encryption_enabled,
            encryption_algorithm=encryption_alg
        )

    def _parse_broadcast(self, mac_pdu: MacPDU) -> Optional[CallMetadata]:
        """
        Parse MAC-BROADCAST (SYSINFO/SYNC).
        Extracts MCC, MNC, LA, Color Code.
        """
        data = mac_pdu.data
        if len(data) < 5:
            return None
            
        # D-MLE-SYNC structure (approximate):
        # MCC (10 bits)
        # MNC (14 bits)
        # Neighbour Cell Info...
        
        try:
            # Convert to bits for easier parsing
            bits = BitArray(data)
            
            # MCC: 10 bits
            mcc = bits[0:10].uint
            
            # MNC: 14 bits
            mnc = bits[10:24].uint
            
            # Colour Code: 6 bits (often follows)
            colour_code = bits[24:30].uint
            
            # VALIDATE: Real TETRA networks use MCC 200-799 (ITU-T E.212)
            # Values outside this range indicate noise/invalid data
            if mcc < 200 or mcc > 799:
                logger.debug(f"Invalid MCC {mcc} - likely noise, not real TETRA")
                return None
            
            # VALIDATE: MNC should be reasonable (0-999 typically)
            if mnc > 999:
                logger.debug(f"Invalid MNC {mnc} - likely noise, not real TETRA")
                return None
            
            # Update parser state
            self.mcc = mcc
            self.mnc = mnc
            self.colour_code = colour_code
            
            logger.info(f"Decoded TETRA network: MCC={mcc} MNC={mnc} CC={colour_code}")
            
            # Return metadata with just network info
            return CallMetadata(
                call_type="Broadcast",
                talkgroup_id=None,
                source_ssi=None,
                dest_ssi=None,
                channel_allocated=None,
                mcc=mcc,
                mnc=mnc,
                encryption_enabled=False
            )
        except:
            return None
    
    def parse_sds_message(self, mac_pdu: MacPDU) -> Optional[str]:
        """
        Parse Short Data Service (SDS) text message.
        
        Args:
            mac_pdu: MAC PDU containing SDS
            
        Returns:
            Decoded text message or None
        """
        if mac_pdu.pdu_type != PDUType.MAC_DATA and mac_pdu.pdu_type != PDUType.MAC_SUPPL:
            return None
        
        # SDS data is in the payload
        return self.parse_sds_data(mac_pdu.data)

    def parse_sds_data(self, data: bytes) -> Optional[str]:
        """
        Parse SDS data payload based on Protocol Identifier (PID) or heuristics.
        Supports SDS-1 (Text), SDS-TL (PID), and GSM 7-bit encoding.
        
        Args:
            data: Raw data bytes
            
        Returns:
            Decoded text string or None
        """
        if not data or len(data) < 1:
            return None
        
        # Strip trailing null bytes for text detection
        data_stripped = data.rstrip(b'\x00')
        if not data_stripped:
            return None
            
        # --- Check for User-Defined SDS Types (based on user examples) ---
        # Example 1: SDS-1 Text (05 00 Length ...)
        if len(data) > 3 and data[0] == 0x05 and data[1] == 0x00:
            # User example: 05 00 C8 48 45 4C 4C 4F -> HELLO
            # Payload starts at offset 3
            payload = data[3:].rstrip(b'\x00')
            try:
                text = payload.decode('ascii')
                if self._is_valid_text(text):
                    self.stats['data_messages'] += 1
                    return f"[SDS-1] {text}"
            except:
                pass

        # Example 2: SDS with GSM 7-bit (07 00 Length ...)
        if len(data) > 3 and data[0] == 0x07 and data[1] == 0x00:
            # User example: 07 00 D2 D4 79 9E 2F 03 -> STATUS OK
            candidates: List[str] = []

            # Some SDS payloads include a septet count at offset 2.
            septet_count = data[2]
            payload_3 = data[3:]
            if payload_3:
                max_septets = (len(payload_3) * 8) // 7
                if 0 < septet_count <= min(160, max_septets):
                    candidates.append(self._unpack_gsm7bit(payload_3, septet_count=septet_count))
                    candidates.append(self._unpack_gsm7bit_with_udh(payload_3, septet_count=septet_count))
                candidates.append(self._unpack_gsm7bit(payload_3))
                candidates.append(self._unpack_gsm7bit_with_udh(payload_3))

            # Fallback: decode starting at offset 2 (treat offset-2 byte as packed content).
            payload_2 = data[2:]
            if payload_2:
                candidates.append(self._unpack_gsm7bit(payload_2))
                candidates.append(self._unpack_gsm7bit_with_udh(payload_2))

            best = ""
            best_score = 0.0
            seen = set()
            for text in candidates:
                text = text.strip("\x00").strip()
                if not text or text in seen:
                    continue
                seen.add(text)
                s = self._score_text(text)
                if s > best_score:
                    best_score = s
                    best = text

            if best and self._is_valid_text(best, threshold=0.55):
                self.stats['data_messages'] += 1
                return f"[SDS-GSM] {best}"

        # --- Standard SDS-TL PID Checks ---
        pid = data[0]
        payload = data[1:].rstrip(b'\x00')
        
        if pid == 0x82:  # Text Messaging (ISO 8859-1)
            try:
                text = payload.decode('latin-1')
                if self._is_valid_text(text):
                    self.stats['data_messages'] += 1
                    return f"[TXT] {text}"
            except:
                pass
                
        elif pid == 0x03:  # Simple Text Messaging (ASCII)
            try:
                text = payload.decode('ascii')
                if self._is_valid_text(text):
                    self.stats['data_messages'] += 1
                    return f"[TXT] {text}"
            except:
                pass
            
        elif pid == 0x83:  # Location
            # Try to parse LIP
            lip_text = self.parse_lip(payload)
            if lip_text:
                return f"[LIP] {lip_text}"
            return f"[LOC] Location Data: {payload.hex()}"
            
        elif pid == 0x0C:  # GPS
            # Try to parse LIP (PID 0x0C is often used for LIP too)
            lip_text = self.parse_lip(payload)
            if lip_text:
                return f"[LIP] {lip_text}"
            return f"[GPS] GPS Data: {payload.hex()}"
            
        # --- Fallback Heuristics ---
        
        # Use stripped data for text detection
        test_data = data_stripped
        
        # Check for 7-bit GSM packing or 8-bit text
        # Heuristic: if > 60% of bytes are printable, treat as text
        printable_count = sum(1 for b in test_data if 32 <= b <= 126 or b in (10, 13))
        if len(test_data) > 0 and (printable_count / len(test_data)) > 0.6:
             try:
                # Try multiple encodings
                text = None
                for encoding in ['utf-8', 'latin-1', 'ascii', 'cp1252']:
                    try:
                        text = test_data.decode(encoding, errors='strict')
                        if self._is_valid_text(text, threshold=0.6):
                            self.stats['data_messages'] += 1
                            return f"[TXT] {text}"
                    except:
                        continue
                
                # If strict decode failed, try with errors='replace'
                if not text:
                    text = test_data.decode('latin-1', errors='replace')
                    if self._is_valid_text(text, threshold=0.6):
                        self.stats['data_messages'] += 1
                        return f"[TXT] {text}"
             except:
                pass
        
        # Try GSM 7-bit unpacking as last resort (with UDH handling)
        try:
            candidates = [
                self._unpack_gsm7bit(test_data),
                self._unpack_gsm7bit_with_udh(test_data),
            ]
            best = ""
            best_score = 0.0
            seen = set()
            for text in candidates:
                text = text.strip("\x00").strip()
                if not text or text in seen:
                    continue
                seen.add(text)
                score = self._score_text(text)
                if score > best_score:
                    best_score = score
                    best = text
            if best and self._is_valid_text(best, threshold=0.55):
                self.stats['data_messages'] += 1
                return f"[GSM7] {best}"
        except Exception:
            pass
        
        # Check for Encrypted Binary SDS (High Entropy)
        if len(test_data) > 8:
            unique_bytes = len(set(test_data))
            entropy_ratio = unique_bytes / len(test_data)
            if entropy_ratio > 0.7:
                # Show hex dump for analysis
                hex_preview = test_data[:32].hex(' ').upper()
                if len(test_data) > 32:
                    hex_preview += "..."
                return f"[BIN-ENC] SDS (Binary/Encrypted) - {len(test_data)} bytes | {hex_preview}"

        # Default to Hex dump for binary data
        def hex_preview(buf: bytes, max_bytes: int = 48) -> str:
            if len(buf) <= max_bytes:
                return buf.hex(" ").upper()
            return buf[:max_bytes].hex(" ").upper() + " ..."

        pid = data_stripped[0]
        payload = data_stripped[1:]

        parts = [f"PID=0x{pid:02X}", f"HEX={hex_preview(data_stripped, max_bytes=32)}"]

        if payload:
            printable_count = sum(1 for b in payload if 32 <= b <= 126 or b in (10, 13, 9))
            if (printable_count / len(payload)) >= 0.85:
                try:
                    ascii_text = payload.decode("latin-1", errors="replace").replace("\r", "").replace("\x00", "")
                    ascii_text = "".join(c for c in ascii_text if c.isprintable() or c in "\n\t").strip()
                    if ascii_text:
                        parts.append(f"ASCII=\"{ascii_text[:60]}\"")
                except Exception:
                    pass

            tlv_items = []
            idx = 0
            while idx + 2 <= len(payload):
                tag = payload[idx]
                length = payload[idx + 1]
                if length == 0 or idx + 2 + length > len(payload):
                    break
                value = payload[idx + 2: idx + 2 + length]
                tlv_items.append(f"{tag:02X}:{length}={hex_preview(value, max_bytes=12)}")
                idx += 2 + length
                if len(tlv_items) >= 4:
                    break
            if tlv_items and idx >= max(3, int(len(payload) * 0.75)):
                parts.append("TLV=" + " ".join(tlv_items))

            if len(payload) in (2, 4, 6, 8, 10, 12) and len(payload) <= 12:
                words_le = [int.from_bytes(payload[i:i + 2], "little") for i in range(0, len(payload), 2)]
                words_be = [int.from_bytes(payload[i:i + 2], "big") for i in range(0, len(payload), 2)]
                parts.append("u16le=" + ",".join(f"0x{w:04X}" for w in words_le))
                parts.append("u16be=" + ",".join(f"0x{w:04X}" for w in words_be))

        return "[BIN] " + " | ".join(parts)

    def parse_lip(self, data: bytes) -> Optional[str]:
        """
        Parse Location Information Protocol (LIP) payload.
        ETSI TS 100 392-18-1.
        Handles Basic Location Report (Short/Long).
        """
        if not data or len(data) < 2:
            return None
            
        try:
            # LIP PDU Type (first 2 bits)
            # 00: Short Location Report
            # 01: Long Location Report
            # 10: Location Report with Ack
            # 11: Reserved/Extended
            
            # Convert to bits for easier parsing
            bits = BitArray(data)
            pdu_type = bits[0:2].uint
            
            if pdu_type == 0: # Short Location Report
                # Structure: Type(2), Time Elapsed(2), Lat(24), Long(25), Pos Error(3), Horizontal Vel(5), Direction(4)
                # Total ~65 bits
                if len(bits) < 65:
                    return None
                    
                # Time Elapsed (0-3) - 0=Current, 1=<5s, 2=<5min, 3=>5min
                time_elapsed = bits[2:4].uint
                
                # Latitude (24 bits, 2's complement)
                lat_raw = bits[4:28].int
                # Scaling: lat_raw * 90 / 2^23
                latitude = lat_raw * 90.0 / (1 << 23)
                
                # Longitude (25 bits, 2's complement)
                lon_raw = bits[28:53].int
                # Scaling: lon_raw * 180 / 2^24
                longitude = lon_raw * 180.0 / (1 << 24)
                
                return f"Lat: {latitude:.5f}, Lon: {longitude:.5f} (Short)"
                
            elif pdu_type == 1: # Long Location Report
                # Structure: Type(2), Time Elapsed(2), Lat(25), Long(26), Pos Error(3), Horizontal Vel(8), Direction(9)
                # Total ~75 bits
                if len(bits) < 75:
                    return None
                    
                # Latitude (25 bits)
                lat_raw = bits[4:29].int
                latitude = lat_raw * 90.0 / (1 << 24)
                
                # Longitude (26 bits)
                lon_raw = bits[29:55].int
                longitude = lon_raw * 180.0 / (1 << 25)
                
                return f"Lat: {latitude:.5f}, Lon: {longitude:.5f} (Long)"
                
            # Heuristic for raw NMEA (sometimes sent as text in LIP PID)
            try:
                text = data.decode('ascii')
                if "$GPGGA" in text or "$GPRMC" in text:
                    return f"NMEA: {text.strip()}"
            except:
                pass
                
        except Exception as e:
            logger.debug(f"LIP parsing error: {e}")
            
        return None

    _GSM7_DEFAULT_ALPHABET = [
        "@", "£", "$", "¥", "è", "é", "ù", "ì", "ò", "Ç", "\n", "Ø", "ø", "\r", "Å", "å",
        "Δ", "_", "Φ", "Γ", "Λ", "Ω", "Π", "Ψ", "Σ", "Θ", "Ξ", "\x1b", "Æ", "æ", "ß", "É",
        " ", "!", "\"", "#", "¤", "%", "&", "'", "(", ")", "*", "+", ",", "-", ".", "/",
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", ":", ";", "<", "=", ">", "?",
        "¡", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O",
        "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "Ä", "Ö", "Ñ", "Ü", "§",
        "¿", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o",
        "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z", "ä", "ö", "ñ", "ü", "à",
    ]

    _GSM7_EXTENSION_TABLE = {
        0x0A: "\f",
        0x14: "^",
        0x28: "{",
        0x29: "}",
        0x2F: "\\",
        0x3C: "[",
        0x3D: "~",
        0x3E: "]",
        0x40: "|",
        0x65: "€",
    }

    def _unpack_gsm7bit(
        self,
        data: bytes,
        septet_count: Optional[int] = None,
        skip_bits: int = 0,
    ) -> str:
        """
        Unpack GSM 03.38 7-bit packed data into text.

        Args:
            data: Packed septets (octet stream)
            septet_count: Optional number of septets to decode
            skip_bits: Number of leading bits to skip (for UDH alignment)
        """
        if not data:
            return ""

        bits: List[int] = []
        for b in data:
            for i in range(8):
                bits.append((b >> i) & 1)

        if skip_bits:
            if skip_bits >= len(bits):
                return ""
            bits = bits[skip_bits:]

        max_septets = len(bits) // 7
        if septet_count is None or septet_count > max_septets:
            septet_count = max_septets

        septets: List[int] = []
        for idx in range(septet_count):
            base = idx * 7
            val = 0
            for offset in range(7):
                val |= (bits[base + offset] << offset)
            septets.append(val)

        out: List[str] = []
        escaped = False
        for code in septets:
            if escaped:
                out.append(self._GSM7_EXTENSION_TABLE.get(code, ""))
                escaped = False
                continue
            if code == 0x1B:
                escaped = True
                continue
            out.append(self._gsm_map(code))

        return "".join(out)

    def _unpack_gsm7bit_with_udh(self, data: bytes, septet_count: Optional[int] = None) -> str:
        """
        Unpack GSM 03.38 7-bit packed data with UDH handling.

        The first octet is treated as UDHL when it yields a plausible header length.
        """
        if not data or len(data) < 2:
            return ""

        udh_len = data[0]
        if udh_len <= 0:
            return ""

        udh_total = udh_len + 1
        if udh_total > len(data):
            return ""

        skip_bits = udh_total * 8
        payload_septets = None
        if septet_count is not None:
            udh_septets = (skip_bits + 6) // 7
            if septet_count > udh_septets:
                payload_septets = septet_count - udh_septets

        return self._unpack_gsm7bit(
            data,
            septet_count=payload_septets,
            skip_bits=skip_bits,
        )

    def _gsm_map(self, code: int) -> str:
        """Map GSM 03.38 default-alphabet code to character."""
        if 0 <= code < len(self._GSM7_DEFAULT_ALPHABET):
            ch = self._GSM7_DEFAULT_ALPHABET[code]
            return "" if ch == "\x1b" else ch
        return ""

    def _score_text(self, text: str) -> float:
        """Score decoded text to select the most plausible candidate."""
        if not text:
            return 0.0
        printable = sum(1 for c in text if c.isprintable() and c not in "\x1b")
        alnum = sum(1 for c in text if c.isalnum() or c.isspace())
        alpha = sum(1 for c in text if c.isalpha())
        return (printable / len(text)) + (alnum / len(text)) + (0.5 if alpha > 0 else 0.0)

    def _is_valid_text(self, text: str, threshold: float = 0.8) -> bool:
        """Check if string looks like valid human-readable text."""
        if not text or len(text) < 2:
            return False
            
        # Remove common whitespace
        clean_text = ''.join(c for c in text if c not in '\n\r\t ')
        if not clean_text:
            return False
            
        # Check ratio of printable characters
        printable = sum(1 for c in text if c.isprintable() or c in '\n\r\t')
        ratio = printable / len(text)
        
        # Check for excessive repetition (padding)
        if len(text) > 4 and text.count(text[0]) == len(text):
            return False
            
        # Check for high density of symbols (binary data often looks like symbols)
        alnum = sum(1 for c in text if c.isalnum() or c == ' ')
        alnum_ratio = alnum / len(text)
        
        return ratio >= threshold and alnum_ratio > 0.5



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
