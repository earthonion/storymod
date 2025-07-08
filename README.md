# Goals

  - FTP server hosting sd card
  - Logs over wifi/bt serial
  - Play custom crafties via mp3
  - export storypod crafties to mp3
  - bluetooth speaker mode?
  - listen to network traffic

-----

## Notes

  - seems to run xradio firmware [XRADIO IOT CEDARX 1.3.14]
  - stores wifi creds in plain text in the logs
  - connects to amazon mqtt [mqtt\_host = a1f7oqdu8j5opv-ats.iot.us-east-1.amazonaws.com, mqtt\_port = 443, mqtt\_topic\_prefix = storypod.]
  - api server : [https://api.storypod.com/api/v1/](https://api.storypod.com/api/v1/) or v2/

-----

## Device & OS Internals

  - **Storage:** The device uses NAND flash storage (NAND driver version 2018-11-20).
  - **SD Card:** The SD card controller is identified as `mmc-0`, supporting speeds up to 52MHz.
  - **Audio:** The core media player is part of the `cedarx` framework. The audio HAL is configured for a specific format and rate (`format: 0x4, rate: 0x2000`).
 
-----

## Local File System

  - **System Sounds:** Default system sounds are located in `file:///tone/`.
  - **Downloaded Content:**
      - White noise tracks are stored at `file:///bedtime/system_white_noise_ocean.mp3`.
      - **Craftie Audio:** Downloaded Craftie audio files are stored in `file:///craftie/[CRAFITE_UUID]/[AUDIO_UUID].abc`.
          - Example: `file:///craftie/010000040019/40202.abc`.
          - they appear to be encrypted, however the logs show that they are downloaded as an mp3
            - Example: `http://audiocnd.storypod.com/audios/ffffffff-ffff-ffff-ffff-ffffffffffff.mp3?Expires=0000000000&Policy=[POLICY_len_220chars]&Signature=[signature_length_344char]&Key-Pair-Id=[KEYPAIRID]`
          
-----

## API & Endpoints

  - [https://api.storypod.com/api/v1/device/update?languageCode=EN](https://api.storypod.com/api/v1/device/update?languageCode=EN)
  - [https://api.storypod.com/api/v1/device/updatestatus?languageCode=EN](https://api.storypod.com/api/v1/device/updatestatus?languageCode=EN)
  - [https://api.storypod.com/api/v1/device/download/delete?languageCode=EN](https://api.storypod.com/api/v1/device/download/delete?languageCode=EN)
  - [http://api.storypod.com/api/v1/device/crafite/download/txt?checkResult=1\&device\_id=](https://www.google.com/search?q=http://api.storypod.com/api/v1/device/crafite/download/txt%3FcheckResult%3D1%26device_id%3D)[YOURDEVICEUUID]\&crafite\_uuid=[CRAFITE\_UUID]\&language=1
  - [https://api.storypod.com/api/v2/device/user/device/binding?languageCode=EN](https://api.storypod.com/api/v2/device/user/device/binding?languageCode=EN)
  - [https://api.storypod.com/api/v2/device/audio/history?languageCode=EN](https://api.storypod.com/api/v2/device/audio/history?languageCode=EN)
  - [https://api.storypod.com/api/v2/device/audio/download/default?languageCode=EN](https://api.storypod.com/api/v2/device/audio/download/default?languageCode=EN)
  - [https://api.storypod.com/api/v2/device/playlist/audio/playurl?languageCode=EN](https://api.storypod.com/api/v2/device/playlist/audio/playurl?languageCode=EN)
  - [https://api.storypod.com/api/v2/device/crafite/craftielist?languageCode=EN](https://api.storypod.com/api/v2/device/crafite/craftielist?languageCode=EN)
  - [https://api.storypod.com/api/v2/device/crafite/playlist?languageCode=EN](https://api.storypod.com/api/v2/device/crafite/playlist?languageCode=EN)
  - [https://api.storypod.com/api/v2/device/crafite/playlist?languageCode=ES](https://api.storypod.com/api/v2/device/crafite/playlist?languageCode=ES)
  - [https://api.storypod.com/api/v2/device/deviceaudioversion/latest?languageCode=EN](https://api.storypod.com/api/v2/device/deviceaudioversion/latest?languageCode=EN)
  - [https://api.storypod.com/api/v2/device/get?languageCode=EN](https://api.storypod.com/api/v2/device/get?languageCode=EN)
  - [https://api.storypod.com/api/v2/device/mqtt/get?languageCode=EN](https://api.storypod.com/api/v2/device/mqtt/get?languageCode=EN)
  - [https://api.storypod.com/api/v2/device/ota/bluetoothversion?version=ver1.1.4\&uuid=](https://api.storypod.com/api/v2/device/ota/bluetoothversion?version=ver1.1.4&uuid=)[YOURDEVICEUUID]\&force=false
  - [https://api.storypod.com/api/v2/device/ota/newversion?version=StoryPod\_0.0.7.16\&uuid=](https://api.storypod.com/api/v2/device/ota/newversion?version=StoryPod_0.0.7.16&uuid=)[YOURDEVICEUUID]\&force=false
  - [http://id.gurobot.cn/device\_online?chip\_id=](http://id.gurobot.cn/device_online?chip_id=)[chipid]\&mac=[MAC\_ADDR]\&token=[TOKEN]\&uuid=[YOURDEVICEUUID]\&re\_load\_uuid=0

### API Details

  - **API Responses:** The device receives detailed JSON responses.
      - `/api/v2/device/get` returns device `uuid`, `isOnline` status, and firmware versions.
      - `/api/v2/device/ota/newversion` response contains a `hasNewVersion` boolean and update details.
  - **MQTT Configuration:** The endpoint `https://api.storypod.com/api/v2/device/mqtt/get` delivers unique credentials for the Amazon MQTT server, including `mqttHost`, `clientId`, `privateKey`, and `clientCrt`.

### Expanded MQTT Process

The device follows a multi-step process to establish its connection to the AWS IoT MQTT broker.

1.  **Requesting Credentials**: The process begins when the device sends a POST request to the `https://api.storypod.com/api/v2/device/mqtt/get?languageCode=EN` endpoint.

      * The body of this request is a JSON object containing the device's unique UUID and a version number: `{"uuid":"[YOURDEVICEUUID]","version":"1.5"}`.

2.  **Receiving Configuration**: The device parses the response from the server, which contains the necessary connection details.

      * **MQTT Type**: `awsiot`
      * **Hostname**: `a1f7oqdu8j5opv-ats.iot.us-east-1.amazonaws.com`
      * **Port**: `443`
      * **Topic Prefix**: `storypod`
      * **AWS Thing Name**: `Storypod_WBN_Production`

3.  **Initializing the Client**: The device initializes a client using the **AWS IoT SDK Version 3.0.1**.

      * It constructs a unique `client_id` for the session by combining a prefix, its MAC address, and a random number. The resulting format is `StoryPod_[MAC_ADDRESS]_[RANDOM_NUMBER]`.

4.  **Defining Topics**: Before connecting, the client sets its specific topics for communication using its UUID.

      * **Publish Topic**: The device sends messages to `storypod/[YOUR_UUID]/app`.
      * **Subscribe Topic**: The device listens for commands on `storypod/[YOUR_UUID]/device`.

5.  **Connecting**: Finally, the device uses these parameters to connect to the AWS IoT service and begin sending and receiving messages.

-----

## Signed Audio Endpoints

*Note: These are for the actual Craftie audio files and require authentication parameters (Expires, Policy, Signature, Key-Pair-Id) to access.*

  - **Generic format**: `http://audiocnd.storypod.com/audios/[AUDIO_UUID].mp3`
  - **Example**: `http://audiocnd.storypod.com/audios/1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d.mp3?Expires=...`

-----

## Unencrypted Audio

  - [http://piccdn.storypod.com/snd\_eft/Numbers/1To5.mp3](http://piccdn.storypod.com/snd_eft/Numbers/1To5.mp3)
  - [http://piccdn.storypod.com/snd\_eft/Numbers/6To10.mp3](http://piccdn.storypod.com/snd_eft/Numbers/6To10.mp3)
  - [http://piccdn.storypod.com/snd\_eft/Numbers/11To15.mp3](http://piccdn.storypod.com/snd_eft/Numbers/11To15.mp3)
  - [http://piccdn.storypod.com/snd\_eft/Numbers/16To20.mp3](http://piccdn.storypod.com/snd_eft/Numbers/16To20.mp3)
  - [https://piccdn.storypod.com/white\_noise/system\_white\_noise\_crickets.mp3](https://piccdn.storypod.com/white_noise/system_white_noise_crickets.mp3)
  - [https://piccdn.storypod.com/white\_noise/system\_white\_noise\_ocean.mp3](https://piccdn.storypod.com/white_noise/system_white_noise_ocean.mp3)
