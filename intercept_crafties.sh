#!/bin/bash

# StorypPod Audio Interceptor v2
# Captures HTTP requests to audiocnd.storypod.com and replays them to download files locally

INTERFACE="${1:-any}"  # Network interface to monitor (default: any)
OUTPUT_DIR="${2:-./downloads}"  # Output directory for downloaded files
PROCESSED_URLS_FILE="$OUTPUT_DIR/processed_urls.txt"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}StorypPod Audio Interceptor v2${NC}"
echo "Interface: $INTERFACE"
echo "Output directory: $OUTPUT_DIR"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"
touch "$PROCESSED_URLS_FILE"

# Function to download URL
download_url() {
    local url="$1"
    
    # Check if already processed
    if grep -Fxq "$url" "$PROCESSED_URLS_FILE"; then
        return 0
    fi
    
    # Add to processed list
    echo "$url" >> "$PROCESSED_URLS_FILE"
    
    # Extract filename from URL
    filename=$(echo "$url" | grep -oP '/audios/[^?]+\.mp3' | sed 's|.*/||')
    
    if [ -n "$filename" ]; then
        echo -e "${GREEN}Found new audio file: $filename${NC}"
        
        # Download the file with the same headers as the original request
        curl -s \
             -H "User-Agent: Allwinner/CedarX 2.7" \
             -H "Range: bytes=0-" \
             -H "Connection: close" \
             "$url" \
             -o "$OUTPUT_DIR/$filename" \
             --fail
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Downloaded: $filename${NC}"
        else
            echo -e "${RED}✗ Failed to download: $filename${NC}"
        fi
    fi
}

# Function to monitor in real-time using tcpdump with text output
monitor_realtime() {
    echo -e "${YELLOW}Starting real-time monitoring...${NC}"
    echo "Press Ctrl+C to stop"
    echo ""
    
    # Use tcpdump with text output and pipe to processing
    sudo tcpdump -i "$INTERFACE" -A -s 0 \
                 host audiocnd.storypod.com and port 80 2>/dev/null | \
    while IFS= read -r line; do
        # Look for GET requests to /audios/
        if echo "$line" | grep -q "GET /audios/.*\.mp3"; then
            # Extract the full URL
            url_path=$(echo "$line" | grep -oP 'GET \K/audios/[^[:space:]]+')
            if [ -n "$url_path" ]; then
                full_url="http://audiocnd.storypod.com$url_path"
                echo -e "${YELLOW}Intercepted request: $url_path${NC}"
                download_url "$full_url"
            fi
        fi
    done
}

# Function to process existing pcap file
process_existing() {
    local pcap_file="$1"
    echo -e "${YELLOW}Processing existing pcap file: $pcap_file${NC}"
    
    # Extract HTTP requests using tshark
    tshark -r "$pcap_file" -Y "http.request and http.host == \"audiocnd.storypod.com\"" \
           -T fields -e http.request.full_uri 2>/dev/null | while read -r url; do
        
        if [ -n "$url" ]; then
            download_url "$url"
        fi
    done
}

# Alternative method using tshark live capture
monitor_tshark() {
    echo -e "${YELLOW}Starting tshark live monitoring...${NC}"
    echo "Press Ctrl+C to stop"
    echo ""
    
    # Use tshark for live capture
    sudo tshark -i "$INTERFACE" -f "host audiocnd.storypod.com and port 80" \
                -Y "http.request" -T fields -e http.request.full_uri \
                2>/dev/null | while read -r url; do
        
        if [ -n "$url" ] && echo "$url" | grep -q "audiocnd.storypod.com"; then
            echo -e "${YELLOW}Intercepted request: $url${NC}"
            download_url "$url"
        fi
    done
}

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    # Kill any background processes
    jobs -p | xargs -r kill 2>/dev/null
    echo -e "${GREEN}Done!${NC}"
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Check if required tools are installed
check_dependencies() {
    local missing=""
    
    if ! command -v tcpdump &> /dev/null; then
        missing="$missing tcpdump"
    fi
    
    if ! command -v curl &> /dev/null; then
        missing="$missing curl"
    fi
    
    if [ -n "$missing" ]; then
        echo -e "${RED}Error: Missing required tools:$missing${NC}"
        echo "Install with: sudo apt install$missing"
        exit 1
    fi
}

# Usage function
usage() {
    echo "Usage: $0 [interface] [output_dir]"
    echo "       $0 -f <pcap_file> [output_dir]"
    echo "       $0 -t [interface] [output_dir]  # Use tshark method"
    echo ""
    echo "Options:"
    echo "  -f <file>    Process existing pcap file instead of live capture"
    echo "  -t           Use tshark for live capture (requires tshark)"
    echo "  -h           Show this help"
    echo ""
    echo "Examples:"
    echo "  $0                          # Monitor all interfaces, save to ./downloads"
    echo "  $0 eth0 /tmp/audio          # Monitor eth0, save to /tmp/audio"
    echo "  $0 -f capture.pcap          # Process existing capture file"
    echo "  $0 -t eth0                  # Use tshark method on eth0"
}

# Parse command line arguments
if [ "$1" = "-h" ]; then
    usage
    exit 0
elif [ "$1" = "-f" ]; then
    if [ -z "$2" ]; then
        echo -e "${RED}Error: Please specify pcap file${NC}"
        usage
        exit 1
    fi
    if [ ! -f "$2" ]; then
        echo -e "${RED}Error: File $2 not found${NC}"
        exit 1
    fi
    OUTPUT_DIR="${3:-./downloads}"
    mkdir -p "$OUTPUT_DIR"
    PROCESSED_URLS_FILE="$OUTPUT_DIR/processed_urls.txt"
    touch "$PROCESSED_URLS_FILE"
    
    # Check if tshark is available for pcap processing
    if ! command -v tshark &> /dev/null; then
        echo -e "${RED}Error: tshark is required for pcap processing. Install with: sudo apt install tshark${NC}"
        exit 1
    fi
    
    process_existing "$2"
    exit 0
elif [ "$1" = "-t" ]; then
    # Use tshark method
    INTERFACE="${2:-any}"
    OUTPUT_DIR="${3:-./downloads}"
    mkdir -p "$OUTPUT_DIR"
    PROCESSED_URLS_FILE="$OUTPUT_DIR/processed_urls.txt"
    touch "$PROCESSED_URLS_FILE"
    
    if ! command -v tshark &> /dev/null; then
        echo -e "${RED}Error: tshark is required for this method. Install with: sudo apt install tshark${NC}"
        exit 1
    fi
    
    check_dependencies
    monitor_tshark
    exit 0
fi

# Check dependencies
check_dependencies

# Start monitoring with tcpdump
monitor_realtime
