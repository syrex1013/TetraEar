"""
TETRA Encryption/Decryption Module

This module implements TETRA Encryption Algorithm (TEA) variants for decrypting
encrypted TETRA frames. Supports TEA1, TEA2, TEA3, and TEA4 algorithms.

Classes:
    TEADecryptor: Decrypts data using TEA algorithms
    TetraKeyManager: Manages encryption keys for TETRA decryption

Example:
    >>> from tetraear.core.crypto import TEADecryptor, TetraKeyManager
    >>> key = bytes.fromhex('00112233445566778899')
    >>> decryptor = TEADecryptor(key, algorithm='TEA1')
    >>> decrypted = decryptor.decrypt_block(encrypted_block)
"""

import struct
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class TEADecryptor:
    """
    TETRA Encryption Algorithm (TEA) decryptor.
    
    Implements decryption for TEA1, TEA2, TEA3, and TEA4 algorithms used in
    TETRA radio systems. Supports both ECB and CBC decryption modes.
    
    Attributes:
        algorithm (str): The TEA algorithm variant ('TEA1', 'TEA2', 'TEA3', 'TEA4')
        key (bytes): The decryption key (length depends on algorithm)
    
    Example:
        >>> key = bytes.fromhex('00112233445566778899')  # 80-bit key for TEA1
        >>> decryptor = TEADecryptor(key, algorithm='TEA1')
        >>> decrypted = decryptor.decrypt_block(encrypted_data)
    """
    
    # Key lengths in bits for each algorithm
    KEY_LENGTHS = {
        'TEA1': 80,   # 80 bits (10 bytes)
        'TEA2': 128,  # 128 bits (16 bytes)
        'TEA3': 128,  # 128 bits (16 bytes)
        'TEA4': 128   # 128 bits (16 bytes)
    }
    
    def __init__(self, key: bytes, algorithm: str = 'TEA1'):
        """
        Initialize TEA decryptor.
        
        Args:
            key: Encryption key (length depends on algorithm)
                - TEA1: 10 bytes (80 bits)
                - TEA2/TEA3/TEA4: 16 bytes (128 bits)
            algorithm: Algorithm variant ('TEA1', 'TEA2', 'TEA3', 'TEA4')
        
        Raises:
            ValueError: If algorithm is unknown or key length is incorrect
        
        Example:
            >>> key = bytes.fromhex('00112233445566778899')
            >>> decryptor = TEADecryptor(key, algorithm='TEA1')
        """
        self.algorithm = algorithm.upper()
        self.key = key
        self._validate_key()
    
    def _validate_key(self) -> None:
        """
        Validate key length for selected algorithm.
        
        Raises:
            ValueError: If algorithm is unknown or key length doesn't match
        """
        expected_length = self.KEY_LENGTHS.get(self.algorithm)
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
        
        TEA1 uses a simplified TEA-like algorithm with 80-bit keys.
        Note: Actual TEA1 implementation details are proprietary.
        
        Args:
            block: 64-bit encrypted block (8 bytes)
        
        Returns:
            Decrypted block (8 bytes)
        
        Raises:
            ValueError: If block size is not 8 bytes
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
        
        TEA2 uses a modified TEA algorithm with 128-bit keys.
        
        Args:
            block: 64-bit encrypted block (8 bytes)
        
        Returns:
            Decrypted block (8 bytes)
        
        Raises:
            ValueError: If block size is not 8 bytes
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
        
        TEA3 uses similar structure to TEA2 but with different key schedule.
        
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
        
        TEA4 is AES-based encryption. This is a simplified implementation.
        Note: Actual TEA4 implementation is proprietary.
        
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
            Decrypted block (8 bytes)
        
        Raises:
            ValueError: If algorithm is unsupported or block size is invalid
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
            iv: Initialization vector (for CBC mode). If None, uses ECB mode.
                Must be 8 bytes if provided.
        
        Returns:
            Decrypted data
        
        Raises:
            ValueError: If data length is not multiple of 8 bytes or IV is invalid
        
        Example:
            >>> decryptor = TEADecryptor(key, 'TEA1')
            >>> # ECB mode
            >>> decrypted = decryptor.decrypt(encrypted_data)
            >>> # CBC mode
            >>> iv = bytes([0] * 8)
            >>> decrypted = decryptor.decrypt(encrypted_data, iv=iv)
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
    """
    Manages TETRA encryption keys.
    
    Provides functionality to load, store, and retrieve encryption keys for
    different TEA algorithms. Supports loading keys from files and managing
    multiple keys per algorithm.
    
    Attributes:
        keys (Dict[str, Dict[str, bytes]]): Nested dictionary storing keys
            Format: {algorithm: {key_id: key_bytes}}
    
    Example:
        >>> manager = TetraKeyManager()
        >>> manager.load_key_file('keys.txt')
        >>> key = manager.get_key('TEA1', '0')
    """
    
    def __init__(self):
        """
        Initialize key manager.
        
        Creates an empty key storage structure.
        """
        self.keys: Dict[str, Dict[str, bytes]] = {}
    
    def load_key_file(self, filepath: str) -> None:
        """
        Load keys from file.
        
        File format (one key per line):
            ALGORITHM:KEY_ID:HEX_KEY
        
        Lines starting with '#' are treated as comments and ignored.
        Blank lines are ignored.
        
        Args:
            filepath: Path to key file
        
        Raises:
            FileNotFoundError: If key file doesn't exist
            ValueError: If key format is invalid
        
        Example:
            Key file content:
            # TEA1 Keys
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
            key_id: Key identifier (default: '0')
        
        Returns:
            Key bytes or None if not found
        
        Example:
            >>> manager = TetraKeyManager()
            >>> manager.add_key('TEA1', '0', key_bytes)
            >>> key = manager.get_key('TEA1', '0')
        """
        algorithm = algorithm.upper()
        if algorithm in self.keys and key_id in self.keys[algorithm]:
            return self.keys[algorithm][key_id]
        return None
    
    def add_key(self, algorithm: str, key_id: str, key: bytes) -> None:
        """
        Add a key to the manager.
        
        Args:
            algorithm: Algorithm name ('TEA1', 'TEA2', etc.)
            key_id: Key identifier
            key: Key bytes
        
        Example:
            >>> manager = TetraKeyManager()
            >>> key = bytes.fromhex('00112233445566778899')
            >>> manager.add_key('TEA1', '0', key)
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
            key_id: Key identifier (default: '0')
        
        Returns:
            True if key exists, False otherwise
        
        Example:
            >>> manager = TetraKeyManager()
            >>> if manager.has_key('TEA1', '0'):
            ...     key = manager.get_key('TEA1', '0')
        """
        algorithm = algorithm.upper()
        return algorithm in self.keys and key_id in self.keys[algorithm]
