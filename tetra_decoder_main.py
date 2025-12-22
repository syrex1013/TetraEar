"""
Main TETRA decoder application using RTL-SDR.
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

from rtl_capture import RTLCapture
from signal_processor import SignalProcessor
from tetra_decoder import TetraDecoder
from tetra_crypto import TetraKeyManager
from frequency_scanner import FrequencyScanner


def setup_logging(log_file=None):
    """
    Setup logging configuration.
    
    Args:
        log_file: Optional log file path
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        # Overwrite log file on each start
        handlers.append(logging.FileHandler(log_file, mode='w'))
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )


def main():
    """Main decoder application."""
    parser = argparse.ArgumentParser(
        description='TETRA Decoder using RTL-SDR',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-f', '--frequency',
        type=float,
        default=400e6,
        help='Center frequency in Hz (default: 400 MHz)'
    )
    
    parser.add_argument(
        '-s', '--sample-rate',
        type=float,
        default=1.8e6,
        help='Sample rate in Hz (default: 1.8 MHz)'
    )
    
    parser.add_argument(
        '-g', '--gain',
        type=str,
        default='auto',
        help='Gain setting: auto or numeric value (default: auto)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output file for decoded data'
    )
    
    parser.add_argument(
        '--log',
        type=str,
        help='Log file path (default: tetra_decoder.log)'
    )
    
    parser.add_argument(
        '--samples',
        type=int,
        default=1024*1024,
        help='Number of samples per capture (default: 1048576)'
    )
    
    parser.add_argument(
        '-k', '--keys',
        type=str,
        help='Path to key file for decryption'
    )
    
    parser.add_argument(
        '--auto-decrypt',
        action='store_true',
        default=True,
        help='Automatically try common keys for encrypted frames (default: enabled)'
    )
    
    parser.add_argument(
        '--no-auto-decrypt',
        action='store_false',
        dest='auto_decrypt',
        help='Disable automatic decryption attempts'
    )
    
    parser.add_argument(
        '--scan',
        action='store_true',
        help='Enable frequency scanning mode (finds TETRA signals automatically)'
    )
    
    parser.add_argument(
        '--scan-poland',
        action='store_true',
        help='Scan Poland TETRA frequency ranges (380-385, 390-395, 410-430 MHz)'
    )
    
    parser.add_argument(
        '--scan-start',
        type=float,
        help='Start frequency for scanning in MHz'
    )
    
    parser.add_argument(
        '--scan-end',
        type=float,
        help='End frequency for scanning in MHz'
    )
    
    parser.add_argument(
        '--min-power',
        type=float,
        default=-70,
        help='Minimum signal power in dB for detection (default: -70)'
    )
    
    parser.add_argument(
        '--min-confidence',
        type=float,
        default=0.4,
        help='Minimum confidence threshold for TETRA detection (default: 0.4)'
    )
    
    parser.add_argument(
        '--decode-found',
        action='store_true',
        help='After scanning, decode found channels automatically'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_file = args.log or 'tetra_decoder.log'
    setup_logging(log_file)
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("TETRA Decoder Starting")
    logger.info("=" * 60)
    
    # Determine if scanning mode
    scanning = args.scan or args.scan_poland
    
    if scanning:
        logger.info("Mode: Frequency Scanning")
        if args.scan_poland:
            logger.info("Target: Poland TETRA frequency ranges")
        elif args.scan_start and args.scan_end:
            logger.info(f"Range: {args.scan_start} - {args.scan_end} MHz")
        else:
            logger.info("Range: Poland TETRA frequency ranges (default)")
    else:
        logger.info("Mode: Single Frequency Decoding")
        logger.info(f"Frequency: {args.frequency/1e6:.2f} MHz")
    
    logger.info(f"Sample Rate: {args.sample_rate/1e6:.2f} MHz")
    logger.info(f"Gain: {args.gain}")
    logger.info(f"Samples per capture: {args.samples}")
    logger.info(f"Auto-decrypt: {'Enabled' if args.auto_decrypt else 'Disabled'}")
    
    # Initialize key manager if key file provided
    key_manager = None
    if args.keys:
        try:
            key_manager = TetraKeyManager()
            key_manager.load_key_file(args.keys)
            logger.info(f"Loaded encryption keys from: {args.keys}")
        except Exception as e:
            logger.error(f"Failed to load key file: {e}")
            logger.warning("Continuing without decryption support")
    
    # Initialize components
    capture = RTLCapture(
        frequency=args.frequency,
        sample_rate=args.sample_rate,
        gain=args.gain if args.gain == 'auto' else float(args.gain)
    )
    
    processor = SignalProcessor(sample_rate=args.sample_rate)
    decoder = TetraDecoder(key_manager=key_manager, auto_decrypt=args.auto_decrypt)
    
    # Open output file if specified
    output_file = None
    if args.output:
        output_file = open(args.output, 'w')
        output_file.write(f"TETRA Decoder Output - Started: {datetime.now()}\n")
        output_file.write("=" * 60 + "\n\n")
    
    # Initialize frame counter
    frame_count = 0
    
    try:
        # Open RTL-SDR device
        if not capture.open():
            logger.error("Failed to open RTL-SDR device")
            return 1
        
        # Scanning mode
        if scanning:
            scanner = FrequencyScanner(capture, sample_rate=args.sample_rate)
            
            try:
                if args.scan_poland:
                    found_channels = scanner.scan_poland(
                        min_power=args.min_power,
                        min_confidence=args.min_confidence
                    )
                elif args.scan_start and args.scan_end:
                    found_channels = scanner.scan_range(
                        args.scan_start * 1e6,
                        args.scan_end * 1e6,
                        min_power=args.min_power,
                        min_confidence=args.min_confidence
                    )
                else:
                    # Default to Poland ranges
                    found_channels = scanner.scan_poland(
                        min_power=args.min_power,
                        min_confidence=args.min_confidence
                    )
                
                # Print found channels
                scanner.print_found_channels()
                
                # Save found channels to output file if specified
                if args.output:
                    with open(args.output, 'w') as f:
                        f.write(f"TETRA Channel Scan Results - {datetime.now()}\n")
                        f.write("=" * 80 + "\n\n")
                        for channel in found_channels:
                            f.write(f"Frequency: {channel['frequency_mhz']:.3f} MHz\n")
                            f.write(f"  Power: {channel['power_db']:.1f} dB\n")
                            f.write(f"  Confidence: {channel['confidence']:.2f}\n")
                            f.write(f"  Sync Detected: {channel.get('sync_detected', False)}\n")
                            f.write("\n")
                
                # Decode found channels if requested
                if args.decode_found and found_channels:
                    logger.info("\nStarting decoding on found channels...")
                    logger.info("Press Ctrl+C to stop\n")
                    
                    frame_count = 0
                    output_file = None
                    if args.output:
                        output_file = open(args.output, 'a')
                        output_file.write("\n" + "=" * 80 + "\n")
                        output_file.write("Decoded Frames:\n")
                        output_file.write("=" * 80 + "\n\n")
                    
                    try:
                        for channel in found_channels:
                            freq = channel['frequency']
                            logger.info(f"\nTuning to {freq/1e6:.3f} MHz...")
                            capture.set_frequency(freq)
                            time.sleep(0.5)  # Allow PLL to lock
                            
                            # Decode for a short time on each channel
                            for _ in range(5):  # 5 captures per channel
                                try:
                                    samples = capture.read_samples(args.samples)
                                    demodulated = processor.process(samples)
                                    frames = decoder.decode(demodulated)
                                    
                                    if frames:
                                        frame_count += len(frames)
                                        logger.info(f"Found {len(frames)} frame(s) on {freq/1e6:.3f} MHz")
                                        
                                        for frame in frames:
                                            frame_info = decoder.format_frame_info(frame)
                                            logger.info(frame_info)
                                            
                                            if output_file:
                                                output_file.write(
                                                    f"{datetime.now()} - {freq/1e6:.3f} MHz - {frame_info}\n"
                                                )
                                                output_file.flush()
                                    
                                    time.sleep(1)
                                    
                                except KeyboardInterrupt:
                                    raise
                                except Exception as e:
                                    logger.debug(f"Error decoding on {freq/1e6:.3f} MHz: {e}")
                                    
                        if output_file:
                            output_file.write(f"\nTotal frames decoded: {frame_count}\n")
                            output_file.close()
                    
                    except KeyboardInterrupt:
                        logger.info("\nStopping decoder...")
                        if output_file:
                            output_file.close()
                
                logger.info(f"\nScan complete. Found {len(found_channels)} channel(s)")
                return 0
                
            except KeyboardInterrupt:
                logger.info("\nScan interrupted by user")
                return 0
        
        # Single frequency decoding mode
        logger.info("Starting signal capture and decoding...")
        logger.info("Press Ctrl+C to stop\n")
        
        frame_count = 0
        
        while True:
            try:
                # Capture samples
                logger.debug("Capturing samples...")
                samples = capture.read_samples(args.samples)
                logger.debug(f"Captured {len(samples)} samples")
                
                # Process signal
                logger.debug("Processing signal...")
                demodulated = processor.process(samples)
                logger.debug(f"Demodulated {len(demodulated)} symbols")
                
                # Decode frames
                logger.debug("Decoding frames...")
                frames = decoder.decode(demodulated)
                
                if frames:
                    frame_count += len(frames)
                    logger.info(f"\nFound {len(frames)} frame(s) in this capture")
                    
                    for frame in frames:
                        frame_info = decoder.format_frame_info(frame)
                        logger.info(frame_info)
                        
                        if output_file:
                            output_file.write(f"{datetime.now()} - {frame_info}\n")
                            output_file.flush()
                    
                    logger.info(f"Total frames decoded: {frame_count}\n")
                else:
                    logger.debug("No frames found in this capture")
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                logger.info("\nStopping decoder...")
                break
            except Exception as e:
                logger.error(f"Error during processing: {e}", exc_info=True)
                time.sleep(1)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1
    
    finally:
        # Cleanup
        capture.close()
        if output_file:
            output_file.write(f"\nDecoder stopped: {datetime.now()}\n")
            output_file.write(f"Total frames decoded: {frame_count}\n")
            output_file.close()
        
        logger.info("=" * 60)
        logger.info(f"TETRA Decoder Stopped - Total frames: {frame_count}")
        logger.info("=" * 60)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
