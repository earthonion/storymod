#!/usr/bin/env python3
"""
Universal Audio Decoder - Pure Python Version
Discovers XOR keys for encrypted audio files using brute force
No assumptions about control bytes - tests pure XOR on every byte

Usage: python audio_decoder.py [file_or_directory]
"""

import os
import sys
import argparse
import time
from collections import Counter

def apply_pure_xor(data, xor_key):
    """Apply pure XOR - every single byte gets XORed"""
    return bytes(b ^ xor_key for b in data)

def analyze_audio_quality(data):
    """Comprehensive audio quality analysis"""
    if not data or len(data) < 10:
        return 0, 0, {}
    
    analysis = {}
    score = 0
    
    # 1. MP3 Sync Pattern Detection
    mp3_syncs = 0
    sync_positions = []
    
    for i in range(len(data) - 1):
        if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
            mp3_syncs += 1
            sync_positions.append(i)
    
    analysis['mp3_syncs'] = mp3_syncs
    analysis['sync_positions'] = sync_positions[:10]  # Store first 10 positions
    
    # Score based on MP3 syncs
    if mp3_syncs > 0:
        score += mp3_syncs * 20  # 20 points per sync
        
    # Bonus for syncs distributed throughout file (not clustered)
    if mp3_syncs > 1 and len(sync_positions) > 1:
        avg_distance = (sync_positions[-1] - sync_positions[0]) / (len(sync_positions) - 1)
        if 100 < avg_distance < 5000:  # Reasonable frame spacing
            score += 50
    
    # 2. Valid MP3 Header at Start
    if (len(data) >= 4 and 
        data[0] == 0xFF and 
        (data[1] & 0xE0) == 0xE0):
        
        score += 200  # Big bonus for valid start
        analysis['valid_header'] = True
        
        # Extract MP3 frame info
        try:
            mpeg_version = (data[1] >> 3) & 0x03
            layer = (data[1] >> 1) & 0x03
            bitrate_index = (data[2] >> 4) & 0x0F
            sample_rate_index = (data[2] >> 2) & 0x03
            
            analysis['mpeg_version'] = mpeg_version
            analysis['layer'] = layer
            analysis['bitrate_index'] = bitrate_index
            analysis['sample_rate_index'] = sample_rate_index
            
            # Bonus for valid ranges
            if 1 <= bitrate_index <= 14:  # Valid bitrate
                score += 30
            if sample_rate_index <= 2:  # Valid sample rate
                score += 30
                
        except:
            pass
    else:
        analysis['valid_header'] = False
    
    # 3. File Size Analysis
    file_size = len(data)
    analysis['file_size'] = file_size
    
    if 10000 < file_size < 50000000:  # Reasonable audio file size
        score += 20
    if 50000 < file_size < 10000000:  # Even better size range
        score += 50
    
    # 4. Entropy Analysis (avoid too uniform or too random)
    sample_size = min(1000, len(data))
    byte_counts = Counter(data[:sample_size])
    
    max_count = max(byte_counts.values()) if byte_counts else 0
    unique_bytes = len(byte_counts)
    
    analysis['unique_bytes_in_sample'] = unique_bytes
    analysis['max_byte_frequency'] = max_count
    
    # Penalty for too uniform (wrong key) or too random (not audio)
    uniformity = max_count / float(sample_size)
    if uniformity > 0.4:  # More than 40% same byte = probably wrong
        score -= 100
    elif uniformity < 0.02:  # Less than 2% max frequency = too random
        score -= 50
    else:
        score += 20  # Good entropy
    
    # Bonus for reasonable byte distribution
    if 50 < unique_bytes < 200:  # Good variety
        score += 30
    
    # 5. Look for Other Audio Format Headers
    # ID3 tags
    if len(data) >= 3 and data[:3] == b'ID3':
        score += 100
        analysis['has_id3'] = True
    
    # RIFF/WAV
    if len(data) >= 4 and data[:4] == b'RIFF':
        score += 100
        analysis['has_riff'] = True
    
    # 6. Frame consistency analysis
    if mp3_syncs >= 2:
        distances = []
        for i in range(len(sync_positions) - 1):
            distances.append(sync_positions[i + 1] - sync_positions[i])
        
        if distances:
            avg_distance = sum(distances) / len(distances)
            analysis['avg_frame_distance'] = avg_distance
            
            # Audio frames should be relatively consistent in size
            if 100 < avg_distance < 2000:  # Typical MP3 frame sizes
                score += 40
    
    return max(0, score), mp3_syncs, analysis

def analyze_chunk_quality(chunk_data):
    """Fast quality analysis for small chunks"""
    if not chunk_data or len(chunk_data) < 10:
        return 0
    
    score = 0
    
    # 1. Look for audio magic bytes (highest priority)
    magic_score = 0
    
    # MP3 sync patterns
    for i in range(len(chunk_data) - 1):
        if chunk_data[i] == 0xFF and (chunk_data[i + 1] & 0xE0) == 0xE0:
            magic_score += 100  # High score for MP3 sync
            if i == 0:  # Extra bonus if at start
                magic_score += 50
    
    # Other format headers
    format_headers = [
        (b'ID3', 150),      # ID3v2 tag
        (b'RIFF', 120),     # WAV file  
        (b'fLaC', 120),     # FLAC
        (b'OggS', 120),     # OGG
        (b'FORM', 100),     # AIFF
    ]
    
    for header, points in format_headers:
        for offset in range(min(len(chunk_data) - len(header), 32)):
            if chunk_data[offset:offset+len(header)] == header:
                magic_score += points
                break
    
    score += magic_score
    
    # 2. Basic entropy check (avoid obviously wrong keys)
    byte_counts = Counter(chunk_data[:min(512, len(chunk_data))])
    if byte_counts:
        max_count = max(byte_counts.values())
        uniformity = max_count / len(chunk_data[:min(512, len(chunk_data))])
        
        # Penalize highly uniform data (wrong key)
        if uniformity > 0.5:
            score -= 50
        elif uniformity > 0.3:
            score -= 20
        else:
            score += 10  # Good entropy
    
    # 3. Reasonable byte variety
    unique_bytes = len(byte_counts)
    if 20 < unique_bytes < 200:  # Good variety for audio
        score += 20
    
    return max(0, score)

def discover_xor_key(file_path, verbose=False, chunk_size=4096):
    """Discover XOR key using efficient chunk scoring"""
    
    print(f"Analyzing: {os.path.basename(file_path)}")
    
    # Read the file
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return None
    
    if len(data) < 100:
        print(f"Warning: File very small ({len(data)} bytes)")
        return None
    
    print(f"File size: {len(data)} bytes")
    
    # Phase 1: Fast chunk scoring
    print("Phase 1: Scoring chunks with all XOR keys...")
    chunk_data = data[:chunk_size]
    key_scores = []
    
    for xor_key in range(256):
        if verbose and xor_key % 64 == 0:
            print(f"  Scoring keys 0x{xor_key:02X}-0x{min(xor_key + 63, 255):02X}...")
        
        # Quick XOR of just the chunk
        decrypted_chunk = apply_pure_xor(chunk_data, xor_key)
        
        # Score the chunk
        chunk_score = analyze_chunk_quality(decrypted_chunk)
        
        if chunk_score > 0:
            key_scores.append((xor_key, chunk_score))
    
    # Sort by chunk score (best first)
    key_scores.sort(key=lambda x: x[1], reverse=True)
    
    print(f"Phase 1 complete: {len(key_scores)} keys with positive scores")
    
    if not key_scores:
        print("No promising keys found in chunk analysis")
        return None
    
    if verbose:
        print("Top chunk scores:")
        for i, (key, score) in enumerate(key_scores[:5]):
            print(f"  {i+1}. Key 0x{key:02X}: chunk_score={score}")
    
    # Phase 2: Full file analysis of ONLY the best key
    best_key = key_scores[0][0]
    best_chunk_score = key_scores[0][1]
    
    print(f"Phase 2: Full analysis of best key 0x{best_key:02X} (chunk_score={best_chunk_score})")
    
    # Apply XOR to full file with best key
    decrypted_data = apply_pure_xor(data, best_key)
    
    # Comprehensive analysis
    full_score, mp3_syncs, analysis = analyze_audio_quality(decrypted_data)
    
    if full_score > 0:
        candidates = [(best_key, full_score, mp3_syncs, len(decrypted_data), analysis)]
        print(f"✓ Best key confirmed: 0x{best_key:02X} (full_score={full_score}, MP3_syncs={mp3_syncs})")
        return candidates
    else:
        print(f"✗ Best key failed full validation (score={full_score})")
        return None

def discover_xor_key_with_alts(file_path, verbose=False, chunk_size=4096, num_alts=3):
    """Discover XOR key and alternatives using chunk scoring"""
    
    print(f"Analyzing: {os.path.basename(file_path)}")
    
    # Read the file
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return None
    
    if len(data) < 100:
        print(f"Warning: File very small ({len(data)} bytes)")
        return None
    
    print(f"File size: {len(data)} bytes")
    
    # Phase 1: Fast chunk scoring
    print("Phase 1: Scoring chunks with all XOR keys...")
    chunk_data = data[:chunk_size]
    key_scores = []
    
    for xor_key in range(256):
        if verbose and xor_key % 64 == 0:
            print(f"  Scoring keys 0x{xor_key:02X}-0x{min(xor_key + 63, 255):02X}...")
        
        # Quick XOR of just the chunk
        decrypted_chunk = apply_pure_xor(chunk_data, xor_key)
        
        # Score the chunk
        chunk_score = analyze_chunk_quality(decrypted_chunk)
        
        if chunk_score > 0:
            key_scores.append((xor_key, chunk_score))
    
    # Sort by chunk score (best first)
    key_scores.sort(key=lambda x: x[1], reverse=True)
    
    print(f"Phase 1 complete: {len(key_scores)} keys with positive scores")
    
    if not key_scores:
        print("No promising keys found in chunk analysis")
        return None
    
    if verbose:
        print("Top chunk scores:")
        for i, (key, score) in enumerate(key_scores[:5]):
            print(f"  {i+1}. Key 0x{key:02X}: chunk_score={score}")
    
    # Phase 2: Full file analysis of top candidates
    top_keys = key_scores[:num_alts + 1]  # Best + alternatives
    print(f"Phase 2: Full analysis of top {len(top_keys)} keys...")
    
    candidates = []
    
    for i, (xor_key, chunk_score) in enumerate(top_keys):
        if verbose:
            print(f"  Analyzing key 0x{xor_key:02X} (chunk_score={chunk_score})...")
        
        # Apply XOR to full file
        decrypted_data = apply_pure_xor(data, xor_key)
        
        # Comprehensive analysis
        full_score, mp3_syncs, analysis = analyze_audio_quality(decrypted_data)
        
        if full_score > 0:
            candidates.append((xor_key, full_score, mp3_syncs, len(decrypted_data), analysis))
    
    # Sort by full score (best first)
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    print(f"Phase 2 complete: {len(candidates)} keys confirmed")
    
    if candidates:
        print("\nConfirmed candidates:")
        for i, (key, score, mp3_syncs, size, analysis) in enumerate(candidates):
            valid_header = "✓" if analysis.get('valid_header', False) else "✗"
            print(f"  {i+1}. Key 0x{key:02X}: Score={score:3d}, MP3_syncs={mp3_syncs:2d}, Header={valid_header}")
    
    return candidates

def decrypt_file(input_path, output_path, xor_key):
    """Decrypt file using XOR key"""
    
    try:
        with open(input_path, 'rb') as f:
            data = f.read()
        
        decrypted_data = apply_pure_xor(data, xor_key)
        
        with open(output_path, 'wb') as f:
            f.write(decrypted_data)
        
        print(f"Decrypted {len(data)} bytes -> {len(decrypted_data)} bytes")
        
        # Validate the result
        score, mp3_syncs, analysis = analyze_audio_quality(decrypted_data)
        print(f"Validation: Score={score}, MP3_syncs={mp3_syncs}, Valid_header={analysis.get('valid_header', False)}")
        
        return True
        
    except Exception as e:
        print(f"Error during decryption: {e}")
        return False

def process_single_file(file_path, chunk_size=4096, show_alts=False):
    """Process a single file with optimized chunk-based analysis"""
    
    print("="*80)
    print("ULTRA-OPTIMIZED SINGLE FILE ANALYSIS")
    print("="*80)
    
    if show_alts:
        candidates = discover_xor_key_with_alts(file_path, verbose=True, chunk_size=chunk_size)
    else:
        candidates = discover_xor_key(file_path, verbose=True, chunk_size=chunk_size)
    
    if not candidates:
        print("No valid XOR keys found!")
        return
    
    # Use the best key
    best_key = candidates[0][0]
    best_score = candidates[0][1]
    
    print(f"\nUsing best key: 0x{best_key:02X} (score: {best_score})")
    
    # Generate output filename
    base_name = os.path.splitext(file_path)[0]
    output_path = f"{base_name}_decrypted_key{best_key:02X}.mp3"
    
    # Decrypt
    if decrypt_file(file_path, output_path, best_key):
        print(f"SUCCESS! Decrypted to: {output_path}")
        
        # Save alternatives only if requested and available
        if show_alts and len(candidates) > 1:
            print("\nSaving alternative decryptions...")
            for i, (key, score, mp3_syncs, size, analysis) in enumerate(candidates[1:4]):
                alt_output = f"{base_name}_alt{i+2}_key{key:02X}.mp3"
                decrypt_file(file_path, alt_output, key)
                print(f"Alternative {i+2}: {alt_output}")

def process_directory(dir_path, chunk_size=4096, show_alts=False):
    """Process all files in a directory with ultra-optimized analysis"""
    
    print("="*80)
    print("ULTRA-OPTIMIZED BATCH DIRECTORY ANALYSIS")
    print("="*80)
    
    # Find potential audio files
    extensions = ['.abc', '.dat', '.bin', '.enc']
    files_to_process = []
    
    for filename in os.listdir(dir_path):
        if any(filename.lower().endswith(ext) for ext in extensions):
            files_to_process.append(filename)
    
    if not files_to_process:
        print("No files with audio extensions found!")
        return
    
    print(f"Found {len(files_to_process)} files to process")
    print(f"Using chunk size: {chunk_size} bytes for initial scoring")
    print(f"Alternatives: {'Enabled' if show_alts else 'Disabled (use --show-alts to enable)'}")
    
    # Process each file
    all_results = {}
    total_start_time = time.time()
    
    for i, filename in enumerate(files_to_process, 1):
        print(f"\n[{i}/{len(files_to_process)}] " + "="*50)
        print(f"PROCESSING: {filename}")
        print("="*60)
        
        file_start_time = time.time()
        file_path = os.path.join(dir_path, filename)
        
        if show_alts:
            candidates = discover_xor_key_with_alts(file_path, chunk_size=chunk_size)
        else:
            candidates = discover_xor_key(file_path, chunk_size=chunk_size)
        
        if candidates:
            best_key = candidates[0][0]
            best_score = candidates[0][1]
            all_results[filename] = (best_key, best_score, candidates[:3] if show_alts else [candidates[0]])
            
            processing_time = time.time() - file_start_time
            print(f"BEST KEY: 0x{best_key:02X} (score: {best_score}) - {processing_time:.1f}s")
            
            # Decrypt with best key
            base_name = os.path.splitext(file_path)[0]
            output_path = f"{base_name}_decrypted.mp3"
            decrypt_file(file_path, output_path, best_key)
            
            # Save alternatives if requested
            if show_alts and len(candidates) > 1:
                for j, (key, score, mp3_syncs, size, analysis) in enumerate(candidates[1:3]):
                    alt_output = f"{base_name}_alt{j+2}_key{key:02X}.mp3"
                    decrypt_file(file_path, alt_output, key)
                    print(f"  Alternative {j+2}: key 0x{key:02X}")
        else:
            all_results[filename] = (None, 0, [])
            processing_time = time.time() - file_start_time
            print(f"NO VALID KEY FOUND - {processing_time:.1f}s")
    
    total_time = time.time() - total_start_time
    
    # Final summary
    print("\n" + "="*80)
    print("ULTRA-OPTIMIZED BATCH PROCESSING COMPLETE")
    print("="*80)
    
    print(f"\nTIMING: Total processing time: {total_time:.1f} seconds")
    print(f"Average per file: {total_time/len(files_to_process):.1f} seconds")
    
    print("\nKEY DISCOVERY SUMMARY:")
    successful_files = 0
    all_keys = []
    
    for filename, (key, score, candidates) in all_results.items():
        if key is not None:
            print(f"  {filename:30} -> 0x{key:02X} (score: {score})")
            all_keys.append(key)
            successful_files += 1
        else:
            print(f"  {filename:30} -> FAILED")
    
    print(f"\nSTATISTICS:")
    print(f"  Files processed: {len(files_to_process)}")
    print(f"  Successful: {successful_files}")
    print(f"  Failed: {len(files_to_process) - successful_files}")
    print(f"  Success rate: {successful_files/len(files_to_process)*100:.1f}%")
    
    if all_keys:
        print(f"\nKEY ANALYSIS:")
        unique_keys = sorted(set(all_keys))
        print(f"  Keys found: {[hex(k) for k in unique_keys]}")
        print(f"  Unique keys: {len(unique_keys)}")
        print(f"  Range: 0x{min(all_keys):02X} - 0x{max(all_keys):02X}")
        
        if len(unique_keys) == 1:
            print("  PATTERN: All files use the SAME key!")
        elif len(unique_keys) == len(all_keys):
            print("  PATTERN: Every file uses a DIFFERENT key!")
        else:
            print("  PATTERN: Mixed - some files share keys")
        
        # Look for sequential patterns
        if len(unique_keys) > 1:
            differences = [unique_keys[i+1] - unique_keys[i] for i in range(len(unique_keys)-1)]
            if all(d == differences[0] for d in differences):
                print(f"  PATTERN: Keys are SEQUENTIAL with step {differences[0]}!")
            
            # Show key distribution
            print(f"  Key distribution:")
            key_counts = Counter(all_keys)
            for key in sorted(key_counts.keys()):
                print(f"    0x{key:02X}: {key_counts[key]} files")

def main():
    """Main function with ultra-optimization and optional alternatives"""
    
    parser = argparse.ArgumentParser(description='Ultra-Optimized Universal Audio Decoder')
    parser.add_argument('path', nargs='?', help='File or directory to process')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('-c', '--chunk-size', type=int, default=4096, 
                        help='Chunk size for initial scoring (default: 4096)')
    parser.add_argument('--show-alts', action='store_true', 
                        help='Generate alternative decryptions (slower but more thorough)')
    
    args = parser.parse_args()
    
    # Validate chunk size
    if args.chunk_size < 512:
        print("Warning: Very small chunk size may miss audio headers")
        args.chunk_size = 512
    elif args.chunk_size > 32768:
        print("Warning: Large chunk size reduces optimization benefits")
        args.chunk_size = 32768
    
    # Get path from command line or prompt user
    if args.path:
        target_path = args.path
    else:
        target_path = input("Enter file or directory path: ").strip()
    
    if not os.path.exists(target_path):
        print(f"Error: Path '{target_path}' does not exist!")
        return
    
    print(f"ULTRA-OPTIMIZATION: Using {args.chunk_size} byte chunks for scoring")
    print(f"Strategy: Score ALL keys on chunks, decrypt ONLY the highest scoring key")
    print(f"Alternatives: {'Enabled' if args.show_alts else 'Disabled (use --show-alts to enable)'}")
    print("This provides maximum speed with excellent accuracy!\n")
    
    if os.path.isfile(target_path):
        process_single_file(target_path, args.chunk_size, args.show_alts)
    elif os.path.isdir(target_path):
        process_directory(target_path, args.chunk_size, args.show_alts)
    else:
        print(f"Error: '{target_path}' is neither a file nor directory!")

if __name__ == "__main__":
    main()
