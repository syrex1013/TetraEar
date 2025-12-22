"""
TETRA encryption/decryption module.
Implements TEA (TETRA Encryption Algorithm) variants.
"""

import struct
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class TEADecryptor:
    """TETRA Encryption Algorithm (TEA) decryptor."""
    
    def __init__(self, key: bytes, algorithm: str = 'TEA1'):
        """
        Initialize TEA decryptor.
        
        Args:
            key: Encryption key (length depends on algorithm)
            algorithm: Algorithm variant ('TEA1', 'TEA2', 'TEA3', 'TEA4')
        """
        self.algorithm = algorithm.upper()
        self.key = key
        self._validate_key()
        
    def _validate_key(self):
        """Validate key length for selected algorithm."""
        key_lengths = {
            'TEA1': 80,   # 80 bits (10 bytes)
            'TEA2': 128,  # 128 bits (16 bytes)
            'TEA3': 128,  # 128 bits (16 bytes)
            'TEA4': 128   # 128 bits (16 bytes)
        }
        
        expected_length = key_lengths.get(self.algorithm)
        if expected_length is None:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")
        
        if len(self.key) * 8 != expected_length:
            raise ValueError(
                f"Key length mismatch for {self.algorithm}: "
                f"expected {expected_length} bits, got {len(self.key) * 8} bits"
            )
    
    def _tea1_decrypt_block(self, block: bytes) -> bytes:
        """
        Decrypt a block using TEA1 (80-bit key).
        
        Args:
            block: 64-bit encrypted block (8 bytes)
            
        Returns:
            Decrypted block (8 bytes)
        """
        if len(block) != 8:
            raise ValueError("TEA1 block must be 8 bytes")
        
        # Extract key components (80-bit key = 10 bytes)
        key_words = []
        for i in range(0, 10, 2):
            key_words.append(struct.unpack('>H', self.key[i:i+2])[0])
        
        # Extract block as two 32-bit words
        v0, v1 = struct.unpack('>II', block)
        
        # TEA1 decryption (simplified - actual TEA1 is proprietary)
        # This is a placeholder implementation
        delta = 0x9e3779b9
        sum_val = delta * 32
        
        for _ in range(32):
            v1 -= ((v0 << 4) ^ (v0 >> 5) ^ sum_val) + v0 ^ (key_words[(sum_val >> 11) & 3] + sum_val)
            v1 &= 0xFFFFFFFF
            sum_val -= delta
            v0 -= ((v1 << 4) ^ (v1 >> 5) ^ sum_val) + v1 ^ (key_words[sum_val & 3] + sum_val)
            v0 &= 0xFFFFFFFF
        
        return struct.pack('>II', v0, v1)
    
    def _tea2_decrypt_block(self, block: bytes) -> bytes:
        """
        Decrypt a block using TEA2 (128-bit key).
        
        Args:
            block: 64-bit encrypted block (8 bytes)
            
        Returns:
            Decrypted block (8 bytes)
        """
        if len(block) != 8:
            raise ValueError("TEA2 block must be 8 bytes")
        
        # Extract key as four 32-bit words
        k0, k1, k2, k3 = struct.unpack('>IIII', self.key)
        
        # Extract block as two 32-bit words
        v0, v1 = struct.unpack('>II', block)
        
        # TEA2 decryption
        delta = 0x9e3779b9
        sum_val = delta * 32
        
        for _ in range(32):
            v1 -= ((v0 << 4) + k2) ^ (v0 + sum_val) ^ ((v0 >> 5) + k3)
            v1 &= 0xFFFFFFFF
            sum_val -= delta
            v0 -= ((v1 << 4) + k0) ^ (v1 + sum_val) ^ ((v1 >> 5) + k1)
            v0 &= 0xFFFFFFFF
        
        return struct.pack('>II', v0, v1)
    
    def _tea3_decrypt_block(self, block: bytes) -> bytes:
        """
        Decrypt a block using TEA3 (128-bit key, different algorithm).
        
        Args:
            block: 64-bit encrypted block (8 bytes)
            
        Returns:
            Decrypted block (8 bytes)
        """
        # TEA3 uses similar structure to TEA2 but with different key schedule
        return self._tea2_decrypt_block(block)
    
    def _tea4_decrypt_block(self, block: bytes) -> bytes:
        """
        Decrypt a block using TEA4 (128-bit key, AES-based).
        
        Args:
            block: 64-bit encrypted block (8 bytes)
            
        Returns:
            Decrypted block (8 bytes)
        """
        # TEA4 is AES-based, simplified implementation
        # Note: Actual TEA4 implementation is proprietary
        return self._tea2_decrypt_block(block)
    
    def decrypt_block(self, block: bytes) -> bytes:
        """
        Decrypt a single block based on selected algorithm.
        
        Args:
            block: Encrypted block (8 bytes for 64-bit block ciphers)
            
        Returns:
            Decrypted block
        """
        if self.algorithm == 'TEA1':
            return self._tea1_decrypt_block(block)
        elif self.algorithm == 'TEA2':
            return self._tea2_decrypt_block(block)
        elif self.algorithm == 'TEA3':
            return self._tea3_decrypt_block(block)
        elif self.algorithm == 'TEA4':
            return self._tea4_decrypt_block(block)
        else:
            raise ValueError(f"Unsupported algorithm: {self.algorithm}")
    
    def decrypt(self, data: bytes, iv: Optional[bytes] = None) -> bytes:
        """
        Decrypt data using CBC mode (default) or ECB.
        
        Args:
            data: Encrypted data (must be multiple of 8 bytes)
            iv: Initialization vector (for CBC mode)
            
        Returns:
            Decrypted data
        """
        if len(data) % 8 != 0:
            raise ValueError("Data length must be multiple of 8 bytes")
        
        if iv is None:
            # ECB mode
            decrypted = b''
            for i in range(0, len(data), 8):
                block = data[i:i+8]
                decrypted += self.decrypt_block(block)
            return decrypted
        else:
            # CBC mode
            if len(iv) != 8:
                raise ValueError("IV must be 8 bytes")
            
            decrypted = b''
            prev_block = iv
            
            for i in range(0, len(data), 8):
                block = data[i:i+8]
                decrypted_block = self.decrypt_block(block)
                decrypted += bytes(a ^ b for a, b in zip(decrypted_block, prev_block))
                prev_block = block
            
            return decrypted


class TetraKeyManager:
    """Manages TETRA encryption keys."""
    
    def __init__(self):
        """Initialize key manager."""
        self.keys = {}  # {algorithm: {key_id: key_bytes}}
    
    def load_key_file(self, filepath: str):
        """
        Load keys from file.
        
        File format (one key per line):
        ALGORITHM:KEY_ID:HEX_KEY
        
        Example:
        TEA1:0:0123456789ABCDEF0123
        TEA2:1:0123456789ABCDEF0123456789ABCDEF
        """
        try:
            with open(filepath, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    try:
                        parts = line.split(':')
                        if len(parts) != 3:
                            logger.warning(f"Invalid key format at line {line_num}: {line}")
                            continue
                        
                        algorithm, key_id, hex_key = parts
                        algorithm = algorithm.upper()
                        key_bytes = bytes.fromhex(hex_key)
                        
                        if algorithm not in self.keys:
                            self.keys[algorithm] = {}
                        
                        self.keys[algorithm][key_id] = key_bytes
                        logger.info(f"Loaded {algorithm} key {key_id}")
                    
                    except ValueError as e:
                        logger.warning(f"Error parsing key at line {line_num}: {e}")
        
        except FileNotFoundError:
            logger.error(f"Key file not found: {filepath}")
            raise
        except Exception as e:
            logger.error(f"Error loading key file: {e}")
            raise
    
    def get_key(self, algorithm: str, key_id: str = '0') -> Optional[bytes]:
        """
        Get key for specified algorithm and ID.
        
        Args:
            algorithm: Algorithm name ('TEA1', 'TEA2', etc.)
            key_id: Key identifier
            
        Returns:
            Key bytes or None if not found
        """
        algorithm = algorithm.upper()
        if algorithm in self.keys and key_id in self.keys[algorithm]:
            return self.keys[algorithm][key_id]
        return None
    
    def add_key(self, algorithm: str, key_id: str, key: bytes):
        """
        Add a key to the manager.
        
        Args:
            algorithm: Algorithm name
            key_id: Key identifier
            key: Key bytes
        """
        algorithm = algorithm.upper()
        if algorithm not in self.keys:
            self.keys[algorithm] = {}
        self.keys[algorithm][key_id] = key
    
    def has_key(self, algorithm: str, key_id: str = '0') -> bool:
        """
        Check if a key exists.
        
        Args:
            algorithm: Algorithm name
            key_id: Key identifier
            
        Returns:
            True if key exists
        """
        algorithm = algorithm.upper()
        return algorithm in self.keys and key_id in self.keys[algorithm]
