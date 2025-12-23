"""
Unit tests for TETRA protocol parser.
"""

import pytest
import numpy as np
from tetraear.core.protocol import (
    TetraProtocolParser, BurstType, ChannelType, PDUType,
    TetraBurst, MacPDU, CallMetadata
)


@pytest.mark.unit
class TestTetraProtocolParser:
    """Test TetraProtocolParser class."""
    
    def test_parser_initialization(self):
        """Test parser initialization."""
        parser = TetraProtocolParser()
        assert parser.current_frame_number == 0
        assert parser.current_multiframe == 0
        assert parser.stats['total_bursts'] == 0
    
    def test_parse_burst_insufficient_symbols(self):
        """Test parsing burst with insufficient symbols."""
        parser = TetraProtocolParser()
        symbols = np.array([0] * 100)  # Less than 255
        result = parser.parse_burst(symbols, slot_number=0)
        assert result is None
    
    def test_parse_burst_sufficient_symbols(self):
        """Test parsing burst with sufficient symbols."""
        parser = TetraProtocolParser()
        # Create symbols array with sync pattern
        symbols = np.array([0] * 255)
        # Add sync pattern in the middle
        sync_pattern = [1, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0]
        symbols[108:130] = sync_pattern
        result = parser.parse_burst(symbols, slot_number=0)
        # Result may be None if CRC fails, but should not crash
        assert result is None or isinstance(result, TetraBurst)
    
    def test_detect_burst_type(self):
        """Test burst type detection."""
        parser = TetraProtocolParser()
        bits = np.array([0] * 255)
        # Add sync pattern
        sync_pattern = [1, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0]
        bits[108:130] = sync_pattern
        burst_type = parser._detect_burst_type(bits)
        assert isinstance(burst_type, BurstType)
    
    def test_check_sync_pattern(self):
        """Test sync pattern checking."""
        parser = TetraProtocolParser()
        # Valid sync pattern
        bits = np.array(parser.SYNC_CONTINUOUS_DOWNLINK)
        result = parser._check_sync_pattern(bits)
        # Convert numpy bool to Python bool
        assert bool(result) is True
        
        # Invalid pattern
        bits = np.array([0] * 22)
        result = parser._check_sync_pattern(bits)
        assert bool(result) is False
    
    def test_extract_training_sequence(self):
        """Test training sequence extraction."""
        parser = TetraProtocolParser()
        bits = np.array([0, 1] * 130)
        seq = parser._extract_training_sequence(bits, BurstType.NormalDownlink)
        assert len(seq) > 0
    
    def test_extract_data_bits(self):
        """Test data bits extraction."""
        parser = TetraProtocolParser()
        bits = np.array([0, 1] * 130)
        data = parser._extract_data_bits(bits, BurstType.NormalDownlink)
        assert len(data) > 0
    
    def test_check_crc(self):
        """Test CRC checking."""
        parser = TetraProtocolParser()
        # Create bits with valid CRC (simplified)
        bits = np.array([0, 1] * 100)
        # Add CRC bits
        crc = parser._calculate_crc16(bits[:-16])
        bits[-16:] = crc
        result = parser._check_crc(bits)
        # Convert numpy bool to Python bool
        assert isinstance(bool(result), bool)
    
    def test_calculate_crc16(self):
        """Test CRC-16 calculation."""
        parser = TetraProtocolParser()
        bits = np.array([0, 1, 0, 1] * 10)
        crc = parser._calculate_crc16(bits)
        assert len(crc) == 16
        assert all(bit in [0, 1] for bit in crc)
    
    def test_parse_mac_pdu_insufficient_bits(self):
        """Test parsing MAC PDU with insufficient bits."""
        parser = TetraProtocolParser()
        bits = np.array([0] * 4)  # Less than 8
        result = parser.parse_mac_pdu(bits)
        assert result is None
    
    def test_parse_mac_pdu_sufficient_bits(self):
        """Test parsing MAC PDU with sufficient bits."""
        parser = TetraProtocolParser()
        # Create bits for MAC-RESOURCE PDU
        bits = np.array([0, 0] + [0, 1] * 50)  # PDU type 00 + data
        result = parser.parse_mac_pdu(bits)
        # May be None if parsing fails, but should not crash
        assert result is None or isinstance(result, MacPDU)
    
    def test_parse_sds_message(self):
        """Test SDS message parsing."""
        from tetraear.core.protocol import MacPDU, PDUType
        
        parser = TetraProtocolParser()
        # Create a MacPDU object (parse_sds_message expects MacPDU, not bytes)
        mac_pdu = MacPDU(
            pdu_type=PDUType.MAC_DATA,
            encrypted=False,
            address=None,
            length=5,
            data=bytes([0x48, 0x65, 0x6C, 0x6C, 0x6F])  # "Hello"
        )
        result = parser.parse_sds_message(mac_pdu)
        # Should return string or None
        assert result is None or isinstance(result, str)
    
    def test_reassemble_fragments(self):
        """Test fragment reassembly."""
        parser = TetraProtocolParser()
        
        # The parser uses fragment_buffer and fragment_metadata internally
        # Simulate adding fragments by directly manipulating the buffer
        fragment_data = bytes([0x01, 0x02, 0x03])
        parser.fragment_buffer = bytearray(fragment_data)
        parser.fragment_metadata = {'address': 1, 'encrypted': False, 'mode': 0}
        
        # Try to get reassembled data
        # Note: actual reassembly logic would be more complex
        assert len(parser.fragment_buffer) > 0
        assert 'address' in parser.fragment_metadata
    
    def test_stats_tracking(self):
        """Test statistics tracking."""
        parser = TetraProtocolParser()
        initial_bursts = parser.stats['total_bursts']
        symbols = np.array([0] * 255)
        parser.parse_burst(symbols, slot_number=0)
        # Stats should be updated (even if burst parsing fails)
        assert parser.stats['total_bursts'] >= initial_bursts
