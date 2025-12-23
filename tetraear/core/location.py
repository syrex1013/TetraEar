"""
GPS and location data parser for TETRA.
Parses LIP (Location Information Protocol) and GPS coordinates from SDS messages.
"""

import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class LocationParser:
    """Parse GPS and location data from TETRA messages."""
    
    @staticmethod
    def parse_coordinates(text: str) -> Optional[Tuple[float, float]]:
        """
        Parse latitude/longitude from text.
        
        Returns:
            (latitude, longitude) or None
        """
        if not text:
            return None
        
        # Try decimal format: Lat: XX.XXXXX Lon: YY.YYYYY
        decimal_pattern = r'Lat:?\s*(-?\d+\.?\d*)\s+Lon:?\s*(-?\d+\.?\d*)'
        match = re.search(decimal_pattern, text, re.IGNORECASE)
        if match:
            try:
                lat = float(match.group(1))
                lon = float(match.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lat, lon)
            except ValueError:
                pass
        
        # Try DMS format: 52°14'30"N 21°00'30"E
        dms_pattern = r'(\d+)°(\d+)[\'′](\d+(?:\.\d+)?)[\"″]([NS])\s+(\d+)°(\d+)[\'′](\d+(?:\.\d+)?)[\"″]([EW])'
        match = re.search(dms_pattern, text)
        if match:
            try:
                # Latitude
                lat_deg = int(match.group(1))
                lat_min = int(match.group(2))
                lat_sec = float(match.group(3))
                lat_dir = match.group(4)
                
                lat = lat_deg + lat_min / 60 + lat_sec / 3600
                if lat_dir == 'S':
                    lat = -lat
                
                # Longitude
                lon_deg = int(match.group(5))
                lon_min = int(match.group(6))
                lon_sec = float(match.group(7))
                lon_dir = match.group(8)
                
                lon = lon_deg + lon_min / 60 + lon_sec / 3600
                if lon_dir == 'W':
                    lon = -lon
                
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lat, lon)
            except ValueError:
                pass
        
        # Try compact format: N52.2417 E021.0083
        compact_pattern = r'([NS])(\d+\.?\d*)\s+([EW])(\d+\.?\d*)'
        match = re.search(compact_pattern, text)
        if match:
            try:
                lat = float(match.group(2))
                if match.group(1) == 'S':
                    lat = -lat
                
                lon = float(match.group(4))
                if match.group(3) == 'W':
                    lon = -lon
                
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lat, lon)
            except ValueError:
                pass
        
        return None
    
    @staticmethod
    def format_coordinates(lat: float, lon: float) -> str:
        """
        Format coordinates for display.
        
        Returns:
            Formatted string like "52.2417°N, 21.0083°E"
        """
        lat_dir = 'N' if lat >= 0 else 'S'
        lon_dir = 'E' if lon >= 0 else 'W'
        
        return f"{abs(lat):.4f}°{lat_dir}, {abs(lon):.4f}°{lon_dir}"
    
    @staticmethod
    def get_google_maps_url(lat: float, lon: float) -> str:
        """Get Google Maps URL for coordinates."""
        return f"https://www.google.com/maps?q={lat},{lon}"
    
    @staticmethod
    def get_openstreetmap_url(lat: float, lon: float) -> str:
        """Get OpenStreetMap URL for coordinates."""
        return f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=15"
    
    @staticmethod
    def parse_lip_message(data: bytes) -> Optional[dict]:
        """
        Parse LIP (Location Information Protocol) message.
        
        Returns:
            dict with location info or None
        """
        if not data or len(data) < 10:
            return None
        
        try:
            # LIP structure (simplified):
            # PDU Type (1 byte)
            # Location fields...
            
            pdu_type = data[0]
            
            # Type 0: Short Location Report
            if pdu_type == 0x00 and len(data) >= 10:
                # Extract lat/lon from binary (24 bits each)
                lat_raw = int.from_bytes(data[1:4], 'big', signed=True)
                lon_raw = int.from_bytes(data[4:7], 'big', signed=True)
                
                # Convert to degrees (WGS84)
                # Range: ±180° mapped to ±2^23
                lat = (lat_raw / (2**23)) * 180
                lon = (lon_raw / (2**23)) * 180
                
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return {
                        'type': 'LIP Short Report',
                        'latitude': lat,
                        'longitude': lon,
                        'formatted': LocationParser.format_coordinates(lat, lon)
                    }
            
            # Type 1: Long Location Report (with altitude, speed, etc.)
            elif pdu_type == 0x01 and len(data) >= 16:
                lat_raw = int.from_bytes(data[1:4], 'big', signed=True)
                lon_raw = int.from_bytes(data[4:7], 'big', signed=True)
                
                lat = (lat_raw / (2**23)) * 180
                lon = (lon_raw / (2**23)) * 180
                
                # Additional fields
                altitude = int.from_bytes(data[7:9], 'big', signed=True)
                speed = int.from_bytes(data[9:11], 'big')
                heading = int.from_bytes(data[11:13], 'big')
                
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return {
                        'type': 'LIP Long Report',
                        'latitude': lat,
                        'longitude': lon,
                        'altitude': altitude,
                        'speed': speed / 10,  # km/h
                        'heading': heading,
                        'formatted': LocationParser.format_coordinates(lat, lon)
                    }
        
        except Exception as e:
            logger.debug(f"Error parsing LIP: {e}")
        
        return None
    
    @staticmethod
    def extract_location_from_frame(frame: dict) -> Optional[dict]:
        """
        Extract location information from a frame.
        
        Returns:
            dict with location data or None
        """
        # Check SDS message for text coordinates
        sds_msg = frame.get('sds_message', '') or frame.get('decoded_text', '')
        
        if '[LIP]' in sds_msg or '[LOC]' in sds_msg or '[GPS]' in sds_msg:
            # Try to parse as text coordinates
            coords = LocationParser.parse_coordinates(sds_msg)
            if coords:
                lat, lon = coords
                return {
                    'type': 'GPS Text',
                    'latitude': lat,
                    'longitude': lon,
                    'formatted': LocationParser.format_coordinates(lat, lon),
                    'source': 'SDS Message'
                }
            
            # Try to parse as LIP binary (if hex data present)
            # Extract hex data after marker
            hex_data = sds_msg.split(':', 1)[-1].strip()
            try:
                data_bytes = bytes.fromhex(hex_data.replace(' ', ''))
                lip_data = LocationParser.parse_lip_message(data_bytes)
                if lip_data:
                    lip_data['source'] = 'LIP Message'
                    return lip_data
            except:
                pass
        
        # Check MAC PDU data for binary LIP
        if 'mac_pdu' in frame and 'data' in frame['mac_pdu']:
            data = frame['mac_pdu']['data']
            if isinstance(data, (bytes, bytearray)):
                lip_data = LocationParser.parse_lip_message(data)
                if lip_data:
                    lip_data['source'] = 'MAC PDU'
                    return lip_data
        
        return None
