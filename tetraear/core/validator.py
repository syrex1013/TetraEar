"""
TETRA signal validation module.
Validates if detected frames are real TETRA signals or just noise.
"""

import logging

logger = logging.getLogger(__name__)


class TetraSignalValidator:
    """Validates TETRA signal authenticity."""
    
    # Valid MCC ranges (ITU-T E.212)
    VALID_MCC_MIN = 200  # Start of assigned MCCs
    VALID_MCC_MAX = 799  # End of commonly assigned MCCs
    
    # Common TETRA countries in Europe (for Poland/nearby)
    EUROPEAN_TETRA_MCCS = {
        202, 204, 206, 208, 212, 213, 214, 216, 218, 219, 220, 222, 225, 226,
        228, 230, 231, 232, 234, 235, 238, 240, 242, 244, 246, 247, 248, 250,
        255, 257, 259, 260, 262, 266, 268, 270, 272, 274, 276, 278, 280, 282,
        283, 284, 286, 288, 290, 292, 293, 294, 295, 297
    }
    
    # Poland TETRA operators (MCC 260)
    POLAND_MNC = {
        1: "Plus/Polkomtel",
        2: "T-Mobile Poland",
        3: "Orange Poland",
        6: "Play",
        # TETRA PMR networks often use different MNC ranges
        98: "Mission Critical",
        99: "Emergency Services"
    }
    
    def __init__(self, expected_country_mcc=None):
        """
        Initialize validator.
        
        Args:
            expected_country_mcc: Expected MCC for your location (e.g., 260 for Poland)
        """
        self.expected_mcc = expected_country_mcc
        self.detected_networks = set()
        self.frame_count = 0
        self.valid_frame_count = 0
        
    def validate_mcc_mnc(self, mcc, mnc):
        """
        Validate MCC/MNC values.
        
        Returns:
            (is_valid, confidence, reason)
        """
        if mcc is None:
            return (False, 0.0, "No MCC present")
        
        # Check if MCC is in valid range
        if mcc < self.VALID_MCC_MIN or mcc > self.VALID_MCC_MAX:
            return (False, 0.0, f"MCC {mcc} out of valid range ({self.VALID_MCC_MIN}-{self.VALID_MCC_MAX})")
        
        # Check if MCC is in known TETRA countries
        confidence = 0.5  # Base confidence for valid range
        
        if mcc in self.EUROPEAN_TETRA_MCCS:
            confidence = 0.8  # Higher confidence for known TETRA countries
        
        # Check if MCC matches expected location
        if self.expected_mcc and mcc == self.expected_mcc:
            confidence = 0.95  # Very high confidence
            reason = f"MCC {mcc} matches expected location"
        elif self.expected_mcc and mcc != self.expected_mcc:
            # Different country - could be neighbor or roaming
            confidence = 0.6
            reason = f"MCC {mcc} differs from expected {self.expected_mcc}"
        else:
            reason = f"MCC {mcc} is valid"
        
        # Validate MNC
        if mnc is not None and mnc > 999:
            confidence *= 0.5  # Reduce confidence for suspicious MNC
            reason += f" but MNC {mnc} seems high"
        
        # Track detected network
        self.detected_networks.add((mcc, mnc))
        
        return (True, confidence, reason)
    
    def validate_frame(self, frame):
        """
        Validate entire frame for TETRA authenticity.
        
        Returns:
            (is_valid, confidence, issues)
        """
        self.frame_count += 1
        issues = []
        confidence = 1.0
        
        # Check 1: CRC
        if 'crc_ok' in frame:
            if not frame['crc_ok']:
                confidence *= 0.3
                issues.append("CRC failed")
        
        # Check 2: Frame structure
        if 'type_name' not in frame or frame['type_name'] is None:
            confidence *= 0.5
            issues.append("No frame type")
        
        # Check 3: MCC/MNC validation
        mcc = None
        mnc = None
        
        if 'call_metadata' in frame:
            mcc = frame['call_metadata'].get('mcc')
            mnc = frame['call_metadata'].get('mnc')
        elif 'additional_info' in frame:
            mcc = frame['additional_info'].get('mcc')
            mnc = frame['additional_info'].get('mnc')
        
        if mcc is not None:
            valid, mcc_conf, reason = self.validate_mcc_mnc(mcc, mnc)
            if not valid:
                confidence = 0.0
                issues.append(reason)
            else:
                confidence *= mcc_conf
                if mcc_conf < 0.7:
                    issues.append(reason)
        else:
            # No MCC/MNC in this frame
            # Only accept if we've seen at least one valid network before
            if len(self.detected_networks) == 0:
                confidence *= 0.4
                issues.append("No network ID and no valid network seen yet")
        
        # Check 4: Encryption sanity
        if frame.get('encrypted'):
            enc_alg = frame.get('encryption_algorithm')
            if enc_alg not in ['TEA1', 'TEA2', 'TEA3', 'TEA4']:
                confidence *= 0.7
                issues.append(f"Unknown encryption: {enc_alg}")
        
        # Check 5: If "decrypted" with suspiciously high confidence from random keys
        if frame.get('decrypted') and frame.get('decrypt_confidence'):
            # Real TETRA decryption with correct key should have high confidence
            # But noise can randomly decrypt with common keys
            conf = frame.get('decrypt_confidence', 0)
            if conf < 180:  # Low confidence decryption
                confidence *= 0.6
                issues.append(f"Low decrypt confidence: {conf}")
        
        # Determine if valid
        is_valid = confidence >= 0.5 and len(issues) <= 2
        
        if is_valid:
            self.valid_frame_count += 1
        
        return (is_valid, confidence, issues)
    
    def get_statistics(self):
        """Get validation statistics."""
        valid_rate = self.valid_frame_count / max(1, self.frame_count)
        
        return {
            'total_frames': self.frame_count,
            'valid_frames': self.valid_frame_count,
            'valid_rate': valid_rate * 100,
            'detected_networks': list(self.detected_networks),
            'is_likely_tetra': valid_rate > 0.3  # At least 30% valid frames
        }
    
    def format_network_info(self, mcc, mnc):
        """Format network information for display."""
        if mcc == 260:  # Poland
            operator = self.POLAND_MNC.get(mnc, f"Unknown (MNC {mnc})")
            return f"🇵🇱 Poland MCC 260 - {operator}"
        else:
            return f"MCC {mcc} MNC {mnc}"
