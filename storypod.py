import requests
import os
import re

class StorypodAPI:
    def __init__(self, access_token, device_id, client_type=None):
        self.base_url = "https://api.storypod.com"
        self.access_token = access_token
        self.device_id = device_id
        self.client_type = client_type or f"device_{device_id}"
        self.headers = {
            "access-token": self.access_token,
            "client-source": "DEVICE",
            "client-type": self.client_type,
            "Content-Type": "application/json",
            "Accept": "*/*",
        }


    def extract_audioid(self, form_bytes, min_length=5):
        
        data = form_bytes
        # Decode to ASCII, ignoring errors
        decoded = data.decode('ascii', errors='ignore')
    
        # Find digit strings of at least `min_length`
        matches = re.findall(r'\d{' + str(min_length) + r',}', decoded)
    
        # Convert to int to remove leading zeros and deduplicate
        numbers = sorted({int(m) for m in matches if int(m) != 0})
    
        # Convert back to strings
        result = [str(n) for n in numbers]
    
        #print(result)  # Optional: remove if you only want the return
        return result

        #usage extract_audio_ids("010000050020.form", min_length=5)


    def _post(self, path, body, v="v2"):
        url = f"{self.base_url}/api/{v}/device/{path}"
        response = requests.post(url, json=body, headers=self.headers)
        return response.json()

    def _get(self, path, params=None, v="v1"):
        url = f"{self.base_url}/api/{v}/device/{path}"
        response = requests.get(url, headers=self.headers, params=params)
        return response.json()

    def get_mqtt_config(self, version="ver1.1.4"):
        return self._post("mqtt/get?languageCode=EN", {"version": version})

    def check_bluetooth_ota(self, version="ver1.1.4"):
        return self._post("ota/bluetoothversion", {"version": version})

    def check_firmware_ota(self, version, uuid, force=False):
        return self._post("ota/newversion", {
            "version": version,
            "uuid": uuid,
            "force": force
        })

    def report_ota_status(self, ota_status, bt_status, tone_status):
        body = {
            "device_id": self.device_id,
            "ota_status": str(ota_status),
            "ota_bluetooth_status": str(bt_status),
            "ota_system_tone_status": str(tone_status)
        }
        return self._post("update?languageCode=EN", body, v="v1")

    def get_crafite_playlist(self, crafite_uuid, current_audio_id, en_version, firmware):
        body = {
            "device_id": self.device_id,
            "crafite_uuid": crafite_uuid,
            "crafite_card": "",
            "current_audio_id": current_audio_id,
            "es_current_audio_id": 0,
            "en_version": en_version,
            "es_version": 0,
            "firmware": firmware
        }
        return self._post("crafite/playlist?languageCode=EN", body)

    def get_bound_crafties(self, firmware):
        return self._post("crafite/craftielist?languageCode=EN", {
            "device_id": self.device_id,
            "firmware": firmware
        })

    def get_audio_stream_url(self, audio_id, craftie_id):
        return self._post("playlist/audio/playurl?languageCode=EN", {
            "device_id": self.device_id,
            "audio_id": audio_id,
            "craftie_id": craftie_id
        })

    def get_craftie_playlist(self, crafite_uuid, language=1, filename=None):
        params = {
            "checkResult": 1,
            "device_id": self.device_id,
            "crafite_uuid": crafite_uuid,
            "language": language
        }
        url = f"{self.base_url}/api/v1/device/crafite/download/txt"
        r = requests.get(url, params=params)
        r.raise_for_status()
        
        # if filename is None:
            # filename = f"{crafite_uuid}.txt"
    
        # with open(filename, "wb") as f:
            # f.write(r.content)
            
        return self.extract_audioid(r.content)



    def direct_download_audio(self, full_url, destination="output.mp3"):
        response = requests.get(full_url, stream=True)
        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    f.write(chunk)
        return destination
        
        
    
