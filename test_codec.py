
import os
import subprocess
import struct

def test_cdecoder():
    codec_path = "tetra_codec/bin/cdecoder.exe"
    if not os.path.exists(codec_path):
        print("Codec not found")
        return

    # Try 1: Text format with $6B21 header
    with open("test_input_1.txt", "w") as f:
        # 114 bits of 0/1
        bits = "0" * 114
        f.write(f"$6B21{bits}\n")
    
    print("Testing Text Format...")
    subprocess.run([codec_path, "test_input_1.txt", "test_output_1.out"], capture_output=True)
    if os.path.exists("test_output_1.out") and os.path.getsize("test_output_1.out") > 0:
        print("Success with Text Format!")
        print(f"Output size: {os.path.getsize('test_output_1.out')}")
    else:
        print("Failed with Text Format")

    # Try 2: Binary format with 0x6B21 header
    with open("test_input_2.bin", "wb") as f:
        # Header 0x6B21 (Little Endian? Big Endian?)
        f.write(struct.pack(">H", 0x6B21)) # Big Endian
        # 114 bits packed? Or 114 bytes?
        # Usage said "...114 bits".
        # Maybe it expects 114 characters of '0'/'1'?
        pass

    # Try 3: Just bits as text
    with open("test_input_3.txt", "w") as f:
        f.write("0" * 114 + "\n")
    
    # Try 4: Soft bits (16-bit per bit)
    with open("test_input_4.bin", "wb") as f:
        # 114 bits as 16-bit integers (0 or 1)
        # Maybe it needs the header $6B21 as bits too?
        # Or maybe the header is just a marker in the stream?
        # Let's try just 114 bits first
        for _ in range(114):
            f.write(struct.pack("h", 0)) # 0
            
    print("Testing Soft Bits (114)...")
    subprocess.run([codec_path, "test_input_4.bin", "test_output_4.out"], capture_output=True)
    if os.path.exists("test_output_4.out") and os.path.getsize("test_output_4.out") > 0:
        print("Success with Soft Bits!")
        print(f"Output size: {os.path.getsize('test_output_4.out')}")
    else:
        print("Failed with Soft Bits")

    # Try 6: Text with space
    with open("test_input_6.txt", "w") as f:
        bits = "0" * 114
        f.write(f"$6B21 {bits}\n")
        
    print("Testing Text with Space...")
    subprocess.run([codec_path, "test_input_6.txt", "test_output_6.out"], capture_output=True)
    if os.path.exists("test_output_6.out") and os.path.getsize("test_output_6.out") > 0:
        print("Success with Text with Space!")
    else:
        print("Failed with Text with Space")

    # Try 7: Text with newlines
    with open("test_input_7.txt", "w") as f:
        f.write("$6B21\n")
        f.write("0" * 114 + "\n")
        
    print("Testing Text with Newlines...")
    subprocess.run([codec_path, "test_input_7.txt", "test_output_7.out"], capture_output=True)
    if os.path.exists("test_output_7.out") and os.path.getsize("test_output_7.out") > 0:
        print("Success with Text with Newlines!")
    else:
        print("Failed with Text with Newlines")
        
    # Try 8: Just 114 bits without header
    with open("test_input_8.txt", "w") as f:
        f.write("0" * 114 + "\n")
        
    print("Testing Just Bits...")
    subprocess.run([codec_path, "test_input_8.txt", "test_output_8.out"], capture_output=True)
    if os.path.exists("test_output_8.out") and os.path.getsize("test_output_8.out") > 0:
        print("Success with Just Bits!")
    else:
        print("Failed with Just Bits")


if __name__ == "__main__":
    test_cdecoder()
