"""
Unit tests for TETRA encryption/decryption module.
"""

import pytest
import struct
from tetraear.core.crypto import TEADecryptor, TetraKeyManager


@pytest.mark.unit
class TestTEADecryptor:
    """Test TEADecryptor class."""
    
    def test_tea1_initialization(self, sample_tea1_key):
        """Test TEA1 decryptor initialization."""
        decryptor = TEADecryptor(sample_tea1_key, algorithm='TEA1')
        assert decryptor.algorithm == 'TEA1'
        assert decryptor.key == sample_tea1_key
    
    def test_tea2_initialization(self, sample_tea2_key):
        """Test TEA2 decryptor initialization."""
        decryptor = TEADecryptor(sample_tea2_key, algorithm='TEA2')
        assert decryptor.algorithm == 'TEA2'
        assert decryptor.key == sample_tea2_key
    
    def test_invalid_key_length_tea1(self):
        """Test that invalid key length raises error for TEA1."""
        invalid_key = bytes([0x00] * 8)  # 64 bits, should be 80
        with pytest.raises(ValueError, match="Key length mismatch"):
            TEADecryptor(invalid_key, algorithm='TEA1')
    
    def test_invalid_key_length_tea2(self):
        """Test that invalid key length raises error for TEA2."""
        invalid_key = bytes([0x00] * 8)  # 64 bits, should be 128
        with pytest.raises(ValueError, match="Key length mismatch"):
            TEADecryptor(invalid_key, algorithm='TEA2')
    
    def test_unknown_algorithm(self, sample_tea1_key):
        """Test that unknown algorithm raises error."""
        with pytest.raises(ValueError, match="Unknown algorithm"):
            TEADecryptor(sample_tea1_key, algorithm='TEA5')
    
    def test_decrypt_block_tea1(self, sample_tea1_key, sample_encrypted_frame):
        """Test TEA1 block decryption."""
        decryptor = TEADecryptor(sample_tea1_key, algorithm='TEA1')
        result = decryptor.decrypt_block(sample_encrypted_frame)
        assert len(result) == 8
        assert isinstance(result, bytes)
    
    def test_decrypt_block_tea2(self, sample_tea2_key, sample_encrypted_frame):
        """Test TEA2 block decryption."""
        decryptor = TEADecryptor(sample_tea2_key, algorithm='TEA2')
        result = decryptor.decrypt_block(sample_encrypted_frame)
        assert len(result) == 8
        assert isinstance(result, bytes)
    
    def test_decrypt_block_invalid_size(self, sample_tea1_key):
        """Test that invalid block size raises error."""
        decryptor = TEADecryptor(sample_tea1_key, algorithm='TEA1')
        invalid_block = bytes([0x00] * 4)  # 4 bytes, should be 8
        with pytest.raises(ValueError, match="block must be 8 bytes"):
            decryptor.decrypt_block(invalid_block)
    
    def test_decrypt_ecb_mode(self, sample_tea1_key):
        """Test ECB mode decryption."""
        decryptor = TEADecryptor(sample_tea1_key, algorithm='TEA1')
        # Encrypt 16 bytes (2 blocks)
        encrypted_data = bytes([0x12] * 16)
        result = decryptor.decrypt(encrypted_data, iv=None)
        assert len(result) == 16
        assert isinstance(result, bytes)
    
    def test_decrypt_cbc_mode(self, sample_tea1_key):
        """Test CBC mode decryption."""
        decryptor = TEADecryptor(sample_tea1_key, algorithm='TEA1')
        encrypted_data = bytes([0x12] * 16)
        iv = bytes([0x00] * 8)
        result = decryptor.decrypt(encrypted_data, iv=iv)
        assert len(result) == 16
        assert isinstance(result, bytes)
    
    def test_decrypt_invalid_length(self, sample_tea1_key):
        """Test that non-multiple-of-8 data raises error."""
        decryptor = TEADecryptor(sample_tea1_key, algorithm='TEA1')
        invalid_data = bytes([0x00] * 7)  # Not multiple of 8
        with pytest.raises(ValueError, match="must be multiple of 8 bytes"):
            decryptor.decrypt(invalid_data)
    
    def test_decrypt_cbc_invalid_iv(self, sample_tea1_key):
        """Test that invalid IV size raises error."""
        decryptor = TEADecryptor(sample_tea1_key, algorithm='TEA1')
        encrypted_data = bytes([0x00] * 8)
        invalid_iv = bytes([0x00] * 4)  # Should be 8 bytes
        with pytest.raises(ValueError, match="IV must be 8 bytes"):
            decryptor.decrypt(encrypted_data, iv=invalid_iv)
    
    def test_tea3_decrypt(self, sample_tea2_key, sample_encrypted_frame):
        """Test TEA3 decryption (uses TEA2 structure)."""
        decryptor = TEADecryptor(sample_tea2_key, algorithm='TEA3')
        result = decryptor.decrypt_block(sample_encrypted_frame)
        assert len(result) == 8
    
    def test_tea4_decrypt(self, sample_tea2_key, sample_encrypted_frame):
        """Test TEA4 decryption (uses TEA2 structure)."""
        decryptor = TEADecryptor(sample_tea2_key, algorithm='TEA4')
        result = decryptor.decrypt_block(sample_encrypted_frame)
        assert len(result) == 8


@pytest.mark.unit
class TestTetraKeyManager:
    """Test TetraKeyManager class."""
    
    def test_key_manager_initialization(self):
        """Test key manager initialization."""
        manager = TetraKeyManager()
        assert manager.keys == {}
    
    def test_add_key(self):
        """Test adding a key."""
        manager = TetraKeyManager()
        key = bytes([0x00] * 10)
        manager.add_key('TEA1', '0', key)
        assert manager.has_key('TEA1', '0')
        assert manager.get_key('TEA1', '0') == key
    
    def test_get_key_not_found(self):
        """Test getting a non-existent key."""
        manager = TetraKeyManager()
        assert manager.get_key('TEA1', '0') is None
    
    def test_has_key(self):
        """Test checking if key exists."""
        manager = TetraKeyManager()
        assert not manager.has_key('TEA1', '0')
        manager.add_key('TEA1', '0', bytes([0x00] * 10))
        assert manager.has_key('TEA1', '0')
    
    def test_load_key_file(self, tmp_path):
        """Test loading keys from file."""
        key_file = tmp_path / "keys.txt"
        key_file.write_text(
            "# Comment line\n"
            "TEA1:0:00112233445566778899\n"
            "TEA2:1:00112233445566778899AABBCCDDEEFF\n"
        )
        
        manager = TetraKeyManager()
        manager.load_key_file(str(key_file))
        
        assert manager.has_key('TEA1', '0')
        assert manager.has_key('TEA2', '1')
        assert manager.get_key('TEA1', '0') == bytes.fromhex('00112233445566778899')
        assert manager.get_key('TEA2', '1') == bytes.fromhex('00112233445566778899AABBCCDDEEFF')
    
    def test_load_key_file_not_found(self):
        """Test loading non-existent key file."""
        manager = TetraKeyManager()
        with pytest.raises(FileNotFoundError):
            manager.load_key_file("nonexistent.txt")
    
    def test_load_key_file_invalid_format(self, tmp_path):
        """Test loading key file with invalid format."""
        key_file = tmp_path / "keys.txt"
        key_file.write_text("INVALID_FORMAT\n")
        
        manager = TetraKeyManager()
        # Should not raise, but log warning
        manager.load_key_file(str(key_file))
        assert len(manager.keys) == 0
    
    def test_case_insensitive_algorithm(self):
        """Test that algorithm names are case-insensitive."""
        manager = TetraKeyManager()
        key = bytes([0x00] * 10)
        manager.add_key('tea1', '0', key)
        assert manager.has_key('TEA1', '0')
        assert manager.get_key('TEA1', '0') == key
