"""
Unit tests for TETRA decoder module.
"""

import pytest
import numpy as np
from bitstring import BitArray
from tetraear.core.decoder import TetraDecoder
from tetraear.core.crypto import TetraKeyManager


@pytest.mark.unit
class TestTetraDecoder:
    """Test TetraDecoder class."""
    
    def test_decoder_initialization(self):
        """Test decoder initialization."""
        decoder = TetraDecoder()
        assert decoder.FRAME_LENGTH == 510
        assert decoder.auto_decrypt is True
        assert decoder.protocol_parser is not None
    
    def test_decoder_with_key_manager(self):
        """Test decoder initialization with key manager."""
        key_manager = TetraKeyManager()
        decoder = TetraDecoder(key_manager=key_manager)
        assert decoder.key_manager == key_manager
    
    def test_decoder_auto_decrypt_disabled(self):
        """Test decoder with auto-decrypt disabled."""
        decoder = TetraDecoder(auto_decrypt=False)
        assert decoder.auto_decrypt is False
    
    def test_symbols_to_bits_dqpsk(self):
        """Test symbol to bit conversion for DQPSK."""
        decoder = TetraDecoder()
        symbols = np.array([0, 1, 2, 3])
        bits, mapped = decoder.symbols_to_bits(symbols)
        assert len(bits) == len(symbols) * 2
        assert len(mapped) == len(symbols)
    
    def test_symbols_to_bits_8psk(self):
        """Test symbol to bit conversion for 8-PSK."""
        decoder = TetraDecoder()
        symbols = np.array([0, 1, 2, 3, 4, 5, 6, 7])
        bits, mapped = decoder.symbols_to_bits(symbols)
        assert len(bits) == len(mapped) * 2
    
    def test_find_sync_insufficient_bits(self):
        """Test sync finding with insufficient bits."""
        decoder = TetraDecoder()
        bits = np.array([0] * 10)  # Less than 22
        sync_positions = decoder.find_sync(bits)
        assert len(sync_positions) == 0
    
    def test_find_sync_with_pattern(self):
        """Test sync finding with sync pattern."""
        decoder = TetraDecoder()
        # Create bits with sync pattern
        bits = np.array([0] * 100)
        sync_pattern = np.array([1, 1, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0, 1, 1, 1, 0, 1, 0, 0])
        bits[20:42] = sync_pattern
        sync_positions, max_corr = decoder.find_sync(bits, threshold=0.8, return_max_corr=True)
        # Should find sync if pattern is strong enough
        assert isinstance(sync_positions, list)
        assert isinstance(max_corr, float)
    
    def test_find_sync_no_pattern(self):
        """Test sync finding without sync pattern."""
        decoder = TetraDecoder()
        bits = np.random.randint(0, 2, size=100)
        sync_positions = decoder.find_sync(bits, threshold=0.9)
        # May or may not find sync depending on random data
        assert isinstance(sync_positions, list)
    
    def test_decode_frame_insufficient_bits(self):
        """Test frame decoding with insufficient bits."""
        decoder = TetraDecoder()
        bits = np.array([0] * 100)
        result = decoder.decode_frame(bits, start_pos=0)
        assert result is None
    
    def test_decode_frame_sufficient_bits(self):
        """Test frame decoding with sufficient bits."""
        decoder = TetraDecoder()
        bits = np.array([0, 1] * 300)  # 600 bits > 510
        result = decoder.decode_frame(bits, start_pos=0)
        # May return None if frame is invalid, but should not crash
        assert result is None or isinstance(result, dict)
    
    def test_set_keys(self):
        """Test setting user keys."""
        decoder = TetraDecoder()
        keys = ['00112233445566778899', '00112233445566778899AABBCCDDEEFF']
        decoder.set_keys(keys)
        assert len(decoder.user_keys) > 0
    
    def test_set_keys_invalid_format(self):
        """Test setting keys with invalid format."""
        decoder = TetraDecoder()
        keys = ['invalid_key_format']
        # Should not crash, but may log warnings
        decoder.set_keys(keys)
        # May or may not add keys depending on validation
    
    def test_common_keys_setup(self):
        """Test that common keys are set up."""
        decoder = TetraDecoder()
        assert hasattr(decoder, 'common_keys')
        assert 'TEA1' in decoder.common_keys
        assert 'TEA2' in decoder.common_keys
        assert len(decoder.common_keys['TEA1']) > 0
    
    def test_sync_pattern_attributes(self):
        """Test sync pattern attributes."""
        decoder = TetraDecoder()
        assert hasattr(decoder, 'SYNC_PATTERN')
        assert len(decoder.SYNC_PATTERN) > 0
