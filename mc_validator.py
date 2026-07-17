import httpx
import base64
import time
import json
def get_xuid_from_token(token):
    payload_b64 = token.split(".")[1]
    # JWT base64url needs padding restored
    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))
    return payload["xuid"]
def get_name_from_token(token):
    payload_b64 = token.split(".")[1]
    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))
    return payload["pfd"][0]["name"]
def get_uuid_from_token(token):
    payload_b64 = token.split(".")[1]
    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))
    return payload["pfd"][0]["id"]
def check_access_token_expired(token):
    payload_b64 = token.split(".")[1]
    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))
    if int(payload["exp"])<time.time():
        return True
    else:
        return False