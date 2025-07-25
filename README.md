# StoryPod Reverse Engineering Documentation

[![Join our Discord](https://img.shields.io/discord/1392219938726481982?logo=discord&color=7289DA&label=Discord)](https://discord.gg/RdM4kXQYTu)

## Project Goals

This project aims to reverse engineer the StoryPod device to enable:

- **FTP server hosting** for SD card access
- **Wireless logging** via WiFi/Bluetooth serial
- **Custom audio playback** for Crafties via MP3
- **Bluetooth speaker mode** functionality  
- **Network traffic monitoring** capabilities

## Key Discoveries

### Device Architecture
- Runs **XRADIO IOT CEDARX 1.3.14** firmware
- **Security concern**: WiFi credentials stored in plain text in logs
- Connects to Amazon MQTT broker: `a1f7oqdu8j5opv-ats.iot.us-east-1.amazonaws.com:443`
- API endpoints: `https://api.storypod.com/api/v1/` and `v2/`

### Hardware Components

| Component | Model | Purpose |
|-----------|-------|---------|
| **CPU** | XR872at ARM Cortex MCU | Main processor |
| **Storage** | Gigadevice GD25Q64CSIG NOR Flash | Internal storage |
| **Bluetooth** | BK3266L | Wireless connectivity |
| **Audio Amp** | HT6873 | Audio amplification |
| **NFC Reader** | NXP SLRC61003 | Craftie detection |

**Audio Framework**: Uses the `cedarx` media player with HAL configured for format `0x4` and rate `0x2000`.
## Crafties

the crafties are little plushies with a NFC ICODE SLIX ISO 15693 chip. the data contains the Serial number and the craftie UUID encrypted with AES.
## Extracting Craftie Audio

### Prerequisites
1. **Physical access**: Disassemble your StoryPod to access the internal micro SD card
2. **Backup**: Copy all SD card contents to a safe location before modification

### Decryption Process
```bash
# Decrypt single file
python decrypt_crafties.py 00000.abc

# Decrypt entire folder
python decrypt_crafties.py crafties/100000000000/
```

The script bruteforces the XOR encryption key and outputs standard MP3 files.

## File System Structure

### System Audio Locations
- **System sounds**: `file:///tone/`
- **White noise**: `file:///bedtime/system_white_noise_ocean.mp3`
- **Craftie audio**: `file:///craftie/[CRAFTIE_UUID]/[AUDIO_UUID].abc`

### Example Paths
```
file:///craftie/010000040019/40202.abc
```

**Note**: `.abc` files are encrypted MP3s downloaded from:
```
http://audiocnd.storypod.com/audios/[UUID].mp3?Expires=[TIME]&Policy=[POLICY]&Signature=[SIG]&Key-Pair-Id=[ID]
```

## Logging System

### Log Access
- **Location**: `/logcat/storypod_logcat_[num].txt` on SD card
- **Automatic upload**: Logs sent to Chinese servers on device shutdown
- **Security note**: Contains valid API access tokens

### Upload Example
```http
PUT /analysis/log/storypod/20250711/[STORYPOD_UUID]/lucky_storypod_1752170748.log HTTP/1.1
Authorization: OSS LTAI4GDaEphKffffffff6MWb:Gddfdjnsdjnsk8cfWGLbvmyMthAA8=
Host: storypod.oss-us-west-1.aliyuncs.com
```

## API Reference

### Core Endpoints

#### Device Management
- `GET /api/v1/device/update?languageCode=EN` - Device updates
- `GET /api/v1/device/updatestatus?languageCode=EN` - Update status
- `GET /api/v2/device/get?languageCode=EN` - Device info (UUID, online status, firmware)

#### Craftie Management  
- `GET /api/v2/device/crafite/craftielist?languageCode=EN` - Available Crafties
- `POST /api/v2/device/crafite/playlist?languageCode=EN` - Playlist after NFC scan
- `GET /api/v1/device/crafite/download/txt` - Craftie content download

#### Audio & Content
- `GET /api/v2/device/audio/history?languageCode=EN` - Play history
- `GET /api/v2/device/audio/download/default?languageCode=EN` - Default audio
- `GET /api/v2/device/playlist/audio/playurl?languageCode=EN` - Streaming URLs

#### System Services
- `GET /api/v2/device/mqtt/get?languageCode=EN` - MQTT credentials
- `GET /api/v2/device/ota/newversion` - Firmware updates
- `GET http://id.gurobot.cn/device_online` - Chinese server check-in

### NFC Workflow

When a Craftie is scanned, the device:

1. **Reads NFC data**: Extracts `crafite_uuid` and `crafite_psyid`
2. **API request**: Posts to `/api/v2/device/crafite/playlist`
3. **Downloads content**: Fetches from `/api/v1/device/crafite/download/txt`

**Example log entry**:
```
[INFO] crafite_uuid = 010000090099, crafite_psyid = ffffffff530104e0
[DBUG] post_body = {"device_id":"DEVICE_UUID","crafite_uuid":"010000090099","crafite_card":"ffffffff530104e0"...}
```

**Access token extraction**: Look for `access-token` header in logs - valid for all API requests.

## MQTT Integration

### Connection Process

1. **Request credentials**: `POST /api/v2/device/mqtt/get`
   ```json
   {"uuid":"[DEVICE_UUID]","version":"1.5"}
   ```

2. **Receive configuration**:
   - **Host**: `a1f7oqdu8j5opv-ats.iot.us-east-1.amazonaws.com`
   - **Port**: `443`
   - **Thing name**: `Storypod_WBN_Production`
   - **Client ID**: `StoryPod_[MAC]_[RANDOM]`

3. **Topic structure**:
   - **Publish**: `storypod/[UUID]/app`
   - **Subscribe**: `storypod/[UUID]/device`

**SDK**: AWS IoT SDK Version 3.0.1

## Audio Content URLs

### Signed Craftie Audio
```
http://audiocnd.storypod.com/audios/[AUDIO_UUID].mp3?[AUTH_PARAMS]
```

**Security issue**: Uses HTTP (no TLS) - vulnerable to MITM attacks. Use `intercept_crafties.sh` for capture.

### Public Audio Files
- Numbers 1-5: `http://piccdn.storypod.com/snd_eft/Numbers/1To5.mp3`
- Numbers 6-10: `http://piccdn.storypod.com/snd_eft/Numbers/6To10.mp3`
- Ocean sounds: `https://piccdn.storypod.com/white_noise/system_white_noise_ocean.mp3`
- Cricket sounds: `https://piccdn.storypod.com/white_noise/system_white_noise_crickets.mp3`

## UART Access

UART RX and TX connect directly to the D+ and D- pins of the micro USB charge port. To access UART:

1. **Hardware Setup**: Cut an old USB cable - white and green wires are RX/TX, black is ground
2. **Connection**: Connect to a USB-to-UART adapter or Arduino
3. **Settings**: 115200 baud

### Known UART Commands

#### Test Mode Commands
```bash
test pcba_test 1          # Enter test/manufacturing mode
test pcba_test 0          # Exit test mode  
test ls /path             # File system browser
test get_device           # Device info (UUID, chip ID, battery)
test get_license          # License information
test get_test_result      # Test results
test get_wlan_status      # WiFi status
test connect_wlan ssid password  # Connect to WiFi
test machine_test         # Hardware test
test upload               # File upload (needs parameters)
test delete /path         # Delete files
test clear                # Clear operation
test reset                # Factory reset (WIPES SD CARD!)
```

#### NFC Commands
```bash
nfc make_init             # Initialize NFC
nfc make_read             # Read NFC card (includes UID and Craftie UUID)
nfc make_write crafite_uuid # Write AES encrypted UUID to NFC card User Data
```

#### CedarX Audio Framework
```bash
cedarx showbuf            # Show audio buffer status
cedarx bufinfo            # Buffer information
cedarx aacsbr             # AAC SBR codec settings
cedarx setbuf file://path size1 size2 size3  # Set audio buffer
cedarx setvol 100         # Set volume (0-100)
cedarx getpos             # Get playback position
cedarx play               # Start playback (CRASHES - avoid)
cedarx stop               # Stop playback
cedarx seek               # Seek position (CRASHES - avoid)
```

#### System Commands
```bash
reboot                    # Restart device
```

### Command Examples
```bash
# Enter test mode
test pcba_test 1 #says something in Chinese then tests LEDs 
test get_device
test ls /

# Read NFC Craftie card
nfc make_init
nfc make_read

# Audio buffer configuration
cedarx showbuf
cedarx setbuf file://test_audio/test_speaker.mp3 160078 4096 0 #returns success but unsure of what this does
```

### Safety Notes
- **`test reset`** wipes the SD card completely
- **`cedarx play`** and **`cedarx seek`** cause system crashes/reboots
- Always backup SD card contents before experimenting
- Battery level affects stability - keep device charged

## Flash Memory Analysis

The NOR flash contains ARM instructions with embedded Chinese test audio. Due to security concerns (contains WiFi credentials and device UUID), flash dumps are not shared publicly. Use the provided SPI flasher code for your own analysis.

## Security Considerations

- **Plaintext credentials** in logs and flash
- **Unencrypted HTTP** for audio downloads  
- **Automatic log uploads** to foreign servers
- **Weak XOR encryption** for Craftie audio
- **Access tokens** exposed in logs

---

*This documentation is for educational and research purposes. Always respect device warranties and applicable laws when reverse engineering hardware.*