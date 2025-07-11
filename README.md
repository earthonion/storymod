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
- **Security concern**: WiFi credentials stored in plain text in logs sent over unencrypted connection to Chinese servers every power down
- Connects to Amazon MQTT broker: `a1f7oqdu8j5opv-ats.iot.us-east-1.amazonaws.com:443`
- API endpoints: `https://api.storypod.com/api/v1/` and `v2/`

### Hardware Components

| Component | Model | Purpose |
|-----------|-------|---------|
| **CPU** | XR872at ARM Cortex MCU | Main processor |
| **Storage** | Gigadevice GD25Q64CSIG NOR Flash | Internal storage |
| **Mass Storage** | 16gb micro SD card | Mass storage (for Craftie audio/ logs) |
| **Bluetooth** | BK3266L | Wireless connectivity |
| **Audio Amp** | HT6873 | Audio amplification |
| **NFC Reader** | NXP SLRC61003 | Craftie detection |

**Audio Framework**: Uses the `cedarx` media player with HAL configured for format `0x4` and rate `0x2000`.

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

Has issues with Q & A crafties. Further research needed.

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
`.form` files are the playlist files. They hold the audio IDs for the tracks. along with information about the craftie.

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