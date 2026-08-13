"""Storage and delivery of door capture images.

Readers and intercoms with a camera publish a snapshot a moment after an
access, a denied access or a doorbell ring. Those snapshots are kept as a
per-door ring buffer on disk and served to the Lovelace card through an
authenticated endpoint, so the recorder database never holds image data.
"""

from __future__ import annotations

from http import HTTPStatus
import logging
from pathlib import Path
import re
import shutil
import time

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Sub-directory of the Home Assistant configuration folder holding the images.
_CAPTURE_DIR = f".storage/{DOMAIN}_captures"

# Images kept per door. Matches the last-access sensor's history length, so
# every event the card is able to display still has its image available.
CAPTURES_PER_DOOR = 25

# Capture ids are ``<door>__<sequence>``; the door part is sanitized to the
# characters below, which also makes the id safe to use as a file name and
# rules out path traversal through the HTTP endpoint.
_ID_RE = re.compile(r"^(?P<door>[A-Za-z0-9_-]+)__(?P<seq>\d+)$")
_UNSAFE_RE = re.compile(r"[^A-Za-z0-9_-]")

_STORE_KEY = f"{DOMAIN}_capture_store"
_VIEW_KEY = f"{DOMAIN}_capture_view"


def _sequence_of(capture_id: str) -> int:
    """Return the sequence number encoded in a capture id (0 if malformed)."""
    match = _ID_RE.match(capture_id)
    return int(match["seq"]) if match else 0


class CaptureStore:
    """Per-door ring buffer of capture images backed by the file system.

    Each image is one ``<capture_id>.jpg`` file. A door never keeps more than
    ``CAPTURES_PER_DOOR`` files: saving a new image deletes that door's oldest
    ones beyond the limit, bounding the space used regardless of runtime.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the store."""
        self._hass = hass
        self._dir = Path(hass.config.path(_CAPTURE_DIR))
        # Capture ids per door, oldest first.
        self._index: dict[str, list[str]] = {}
        self._last_sequence: dict[str, int] = {}

    async def async_load(self) -> None:
        """Rebuild the index from the images already on disk."""
        self._index = await self._hass.async_add_executor_job(self._scan)
        self._last_sequence = {
            door: _sequence_of(ids[-1]) for door, ids in self._index.items() if ids
        }

    def new_id(self, door_id: str) -> str:
        """Return a capture id reserved for the next image of a door.

        The sequence is the current time in milliseconds, forced to strictly
        increase per door so ids stay unique and sortable by age.
        """
        door = _UNSAFE_RE.sub("-", door_id)
        sequence = max(int(time.time() * 1000), self._last_sequence.get(door, 0) + 1)
        self._last_sequence[door] = sequence
        return f"{door}__{sequence}"

    async def async_save(self, capture_id: str, image: bytes) -> None:
        """Store an image and drop the door's images beyond the limit."""
        match = _ID_RE.match(capture_id)
        if match is None or not image:
            return

        ids = self._index.setdefault(match["door"], [])
        ids.append(capture_id)
        expired = ids[:-CAPTURES_PER_DOOR]
        del ids[:-CAPTURES_PER_DOOR]

        try:
            await self._hass.async_add_executor_job(
                self._write, capture_id, image, expired
            )
        except OSError as err:
            _LOGGER.debug("Could not store capture %s: %s", capture_id, err)
            if capture_id in ids:
                ids.remove(capture_id)

    async def async_get(self, capture_id: str) -> bytes | None:
        """Return a stored image, or None when it is unknown."""
        if _ID_RE.match(capture_id) is None:
            return None
        return await self._hass.async_add_executor_job(self._read, capture_id)

    async def async_clear(self) -> None:
        """Delete every stored image."""
        self._index = {}
        self._last_sequence = {}
        await self._hass.async_add_executor_job(self._delete_all)

    def _delete_all(self) -> None:
        """Remove the capture directory and everything in it."""
        shutil.rmtree(self._dir, ignore_errors=True)

    def _scan(self) -> dict[str, list[str]]:
        """Return the capture ids present on disk, per door and oldest first."""
        index: dict[str, list[str]] = {}
        if not self._dir.is_dir():
            return index
        for path in self._dir.glob("*.jpg"):
            match = _ID_RE.match(path.stem)
            if match is not None:
                index.setdefault(match["door"], []).append(path.stem)
        for ids in index.values():
            ids.sort(key=_sequence_of)
        return index

    def _write(self, capture_id: str, image: bytes, expired: list[str]) -> None:
        """Write one image and unlink the expired ones."""
        self._dir.mkdir(parents=True, exist_ok=True)
        (self._dir / f"{capture_id}.jpg").write_bytes(image)
        for stale in expired:
            (self._dir / f"{stale}.jpg").unlink(missing_ok=True)

    def _read(self, capture_id: str) -> bytes | None:
        """Read one image, or return None when the file is missing."""
        try:
            return (self._dir / f"{capture_id}.jpg").read_bytes()
        except OSError:
            return None


class UnifiAccessCaptureView(HomeAssistantView):
    """Serve stored capture images to the last-access card."""

    url = f"/api/{DOMAIN}/capture/{{capture_id}}"
    name = f"api:{DOMAIN}:capture"
    requires_auth = True

    def __init__(self, store: CaptureStore) -> None:
        """Initialize the view."""
        self._store = store

    async def get(self, request: web.Request, capture_id: str) -> web.Response:
        """Return the requested image, or 404 when it is not stored."""
        image = await self._store.async_get(capture_id)
        if image is None:
            return web.Response(status=HTTPStatus.NOT_FOUND)
        return web.Response(
            body=image,
            content_type="image/jpeg",
            headers={"Cache-Control": "private, max-age=3600"},
        )


async def async_setup_captures(hass: HomeAssistant) -> CaptureStore:
    """Return the shared capture store, registering its endpoint once."""
    store: CaptureStore | None = hass.data.get(_STORE_KEY)
    if store is None:
        store = CaptureStore(hass)
        await store.async_load()
        hass.data[_STORE_KEY] = store
    if not hass.data.get(_VIEW_KEY):
        hass.http.register_view(UnifiAccessCaptureView(store))
        hass.data[_VIEW_KEY] = True
    return store


async def async_remove_captures(hass: HomeAssistant) -> None:
    """Delete all stored images (called when the integration is removed)."""
    store: CaptureStore | None = hass.data.get(_STORE_KEY)
    if store is not None:
        await store.async_clear()
