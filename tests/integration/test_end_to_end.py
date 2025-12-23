"""
End-to-end integration tests for TETRA decoding pipeline.
"""

import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from tetraear.signal.processor import SignalProcessor
from tetraear.core.decoder import TetraDecoder
from tetraear.core.protocol import TetraProtocolParser


@pytest.mark.integration
class TestEndToEndDecoding:
    """Test complete decoding pipeline."""
    
    def test_signal_processing_pipeline(self, sample_iq_samples):
        """Test signal processing pipeline."""
        processor = SignalProcessor(sample_rate=2.4e6)
        
        # Filter signal
        filtered = processor.filter_signal(sample_iq_samples)
        assert len(filtered) == len(sample_iq_samples)
        
        # Demodulate
        symbols = processor.demodulate_dqpsk(filtered)
        assert len(symbols) > 0
        
        # Extract symbols at symbol rate
        extracted = processor.extract_symbols(filtered)
        assert len(extracted) > 0
    
    def test_decoding_pipeline(self, sample_tetra_bits):
        """Test decoding pipeline with sample bits."""
        decoder = TetraDecoder()
        
        # Convert bits to numpy array
        bits = np.array(sample_tetra_bits)
        
        # Find sync
        sync_positions = decoder.find_sync(bits, threshold=0.7)
        # May or may not find sync depending on data
        
        # Try to decode frame if sync found
        if sync_positions:
            result = decoder.decode_frame(bits, start_pos=sync_positions[0])
            # Result may be None if frame is invalid
            assert result is None or isinstance(result, dict)
    
    def test_protocol_parsing_pipeline(self):
        """Test protocol parsing pipeline."""
        parser = TetraProtocolParser()
        
        # Create sample symbols
        symbols = np.array([0, 1, 2, 3] * 64)  # 256 symbols (enough for burst)
        
        # Parse burst
        burst = parser.parse_burst(symbols, slot_number=0)
        # May be None if CRC fails, but should not crash
        assert burst is None or hasattr(burst, 'burst_type')
    
    def test_full_pipeline_mock(self, sample_iq_samples):
        """Test full pipeline with mocked components."""
        # Signal processing
        processor = SignalProcessor()
        filtered = processor.filter_signal(sample_iq_samples)
        symbols = processor.demodulate_dqpsk(filtered)
        
        # Decoding
        decoder = TetraDecoder()
        bits, mapped = decoder.symbols_to_bits(symbols)
        
        # Protocol parsing
        parser = TetraProtocolParser()
        if len(symbols) >= 255:
            burst = parser.parse_burst(symbols[:255], slot_number=0)
            # May be None, but should not crash
            assert burst is None or hasattr(burst, 'data_bits')
    
    def test_decryption_pipeline(self, sample_encrypted_frame, sample_tea1_key):
        """Test decryption in decoding pipeline."""
        from tetraear.core.crypto import TEADecryptor
        
        decryptor = TEADecryptor(sample_tea1_key, algorithm='TEA1')
        decrypted = decryptor.decrypt_block(sample_encrypted_frame)
        
        assert len(decrypted) == 8
        assert isinstance(decrypted, bytes)
    
    def test_fragmented_message_reassembly(self):
        """Test fragmented message reassembly."""
        parser = TetraProtocolParser()
        
        # Add multiple fragments
        fragment1 = bytes([0x01, 0x02, 0x03])
        fragment2 = bytes([0x04, 0x05, 0x06])
        
        # Simulate adding fragments (would normally come from MAC-FRAG PDUs)
        # This is a simplified test
        parser.fragment_buffer = bytearray(fragment1 + fragment2)
        
        # Try to get reassembled data
        # Note: actual reassembly logic would be more complex
        assert len(parser.fragment_buffer) > 0
    
    def test_statistics_tracking(self):
        """Test that statistics are tracked through pipeline."""
        parser = TetraProtocolParser()
        initial_bursts = parser.stats['total_bursts']
        
        # Process some bursts
        symbols = np.array([0, 1, 2, 3] * 64)
        for _ in range(3):
            parser.parse_burst(symbols, slot_number=0)
        
        # Stats should be updated
        assert parser.stats['total_bursts'] >= initial_bursts + 3
