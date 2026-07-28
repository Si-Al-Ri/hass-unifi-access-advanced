"""Constants for the Unifi Access integration."""

DOMAIN = "unifi_access"


# Door entity types — controls which HA platform a door appears as. UA Hub Gate
# (UGT) doors can be exposed as a garage-door / gate cover instead of a lock.
DOOR_TYPE_LOCK = "lock"
DOOR_TYPE_GARAGE = "garage"
DOOR_TYPE_GATE = "gate"
DOOR_TYPES = [DOOR_TYPE_LOCK, DOOR_TYPE_GARAGE, DOOR_TYPE_GATE]

# Persistent storage for the per-door entity-type selection.
STORAGE_KEY = "unifi_access_entity_types"
STORAGE_VERSION = 1


DOORBELL_EVENT = "doorbell_press"
DOORBELL_START_EVENT = "unifi_access_doorbell_start"
DOORBELL_STOP_EVENT = "unifi_access_doorbell_stop"
ACCESS_ENTRY_EVENT = "unifi_access_entry"
ACCESS_EXIT_EVENT = "unifi_access_exit"
ACCESS_GENERIC_EVENT = "unifi_access_access"

# HA bus event fired when a guest pass is first used. Payload:
# {"visitor_id": <id>}. The guest-pass card subscribes to it to refresh.
EVENT_GUEST_ARRIVED = f"{DOMAIN}_guest_arrived"

# Valid (anti_spoofing_level, detect_distance) combinations accepted by the
# UniFi Access API (API ref 8.3). Any other pairing is silently ignored by the
# controller. These four map 1:1 to the Face Unlock slider in the UniFi UI,
# ordered from most sensitive to most secure.
ANTI_SPOOFING_COMBOS: dict[str, tuple[str, str]] = {
    "no_far": ("no", "far"),
    "no_medium": ("no", "medium"),
    "medium_near": ("medium", "near"),
    "high_near": ("high", "near"),
}

# Reverse lookup: (anti_spoofing_level, detect_distance) → combo option key.
ANTI_SPOOFING_OPTION_BY_PAIR: dict[tuple[str, str], str] = {
    pair: option for option, pair in ANTI_SPOOFING_COMBOS.items()
}

# Capability tokens (substring-matched against a device's `capabilities` array
# from /api/v1/developer/devices) that indicate the hardware actually supports
# a given access method. The settings endpoint returns some methods even when
# the hardware cannot use them (e.g. touch_pass on a UA-Intercom), so the
# capabilities array is the authoritative support signal. A method counts as
# supported when any token is found in any capability string.
ACCESS_METHOD_CAPABILITY_TOKENS: dict[str, tuple[str, ...]] = {
    "nfc": ("nfc",),
    "bt_button": ("mobile_unlock",),
    "bt_tap": ("mobile_unlock",),
    "pin_code": ("pin_code",),
    "wave": ("hand_wave",),
    "qr_code": ("qr_code",),
    "touch_pass": ("touch_pass",),
}
