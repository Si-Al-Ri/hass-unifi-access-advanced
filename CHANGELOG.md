# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_Nothing yet._

---

# Fork releases

Releases of this fork ([Si-Al-Ri/hass-unifi-access-advanced](https://github.com/Si-Al-Ri/hass-unifi-access-advanced)).

## [3.2.5] - 2026-08-19

### Fixed
- **The Face Anti-Spoofing level is no longer lost on restart.** While Face
  Unlock is disabled the controller reports a placeholder rather than the
  configured value, which was adopted on every start and showed up as the
  highest setting. The configured level is now stored and restored, and it is
  only taken from the controller while Face Unlock is enabled — so it also
  keeps working when Face Unlock is switched off nightly by an automation.
  Re-enabling Face Unlock now writes the level that was actually configured
  instead of the placeholder.
- **The temporary-lock-rule interval no longer resets to 10 minutes** on every
  restart; the restored value was read but never applied.
- **The door-lock-rule select no longer breaks under a scheduled rule.** The
  controller reports rule types that cannot be selected (`schedule`,
  `lock_now`); these were missing from the option list, so the current state was
  rejected as invalid. The active one is now listed, and `schedule` was added to
  all six translations.
- Entity removal when a door's entity type changes no longer starts a coroutine
  that is never awaited, which left the entity in place.
- The config flow no longer builds the SSL context on the event loop.
- Snapshot images that no event claims are released instead of being held for
  the lifetime of the integration.
- A guest pass whose QR code cannot be downloaded is now rolled back like a
  failed credential assignment, and the rollback deletes the unusable visitor
  outright instead of leaving a cancelled entry behind.
- Both dashboard cards no longer leak an event subscription when they are
  removed while subscribing, and the last-access card bounds its cache of
  signed image URLs to the entries it currently shows.
- Garage/gate covers track their trigger rate limit on a monotonic clock, so a
  clock change cannot disable or block it, and the debounce task is handed to
  Home Assistant instead of being started detached.

## [3.2.4] - 2026-08-13

### Added
- **Camera snapshots in the last-access card.** Readers and intercoms with a
  camera capture a snapshot at the moment of the event; expanding an entry shows
  it as a *Picture* row, and clicking the thumbnail opens it full size. Works for
  granted accesses, denied attempts and doorbell rings alike.
  - Kept as a ring buffer of the 25 most recent events **per door**, matching the
    sensor's history length, so every entry the card can display still has its
    image at any `max_logs` value. No new configuration option.
  - Images are stored as files under `.storage/` and referenced from the event by
    id only, keeping image data out of the recorder database. They survive a
    restart and are deleted with the integration.
  - Served through an authenticated endpoint — unlike `config/www/`, snapshots
    are not reachable without a Home Assistant login.

### Changed
- The three door-thumbnail code paths were merged into a single helper.

### Fixed
- An unusable thumbnail timestamp reported by the controller can no longer
  interrupt the websocket connection.

## [3.2.3] - 2026-08-03

### Added
- **Delete guest passes permanently**, so expired and revoked passes no longer
  pile up: a *Delete* button in the guest pass card (with confirmation) and a new
  `unifi_access.delete_guest_pass` action. Removes the visitor from UniFi Access
  itself, not just from Home Assistant.
  *Revoke* still disables the credentials while keeping the pass reactivatable;
  *delete* cannot be undone.

## [3.2.2] - 2026-07-31

### Changed
- `trigger_doorbell` offers a **device picker**: choose the door or reader from a
  dropdown instead of looking up UniFi IDs. Selecting several devices rings each
  of them; the existing `door_id` / `device_id` fields keep working.
  Supersedes 3.2.1, which used a service target that Home Assistant does not
  allow to be filtered by integration.

## [3.2.1] - 2026-07-31

### Changed
- First attempt at device-picker support for `trigger_doorbell` (superseded by
  3.2.2).

## [3.2.0] - 2026-07-31

### Added
- **New action `unifi_access.trigger_doorbell`** — makes an intercom or reader
  ring from Home Assistant. Targets a door (preferring an intercom when a door
  has several readers) or a specific device, with optional `room_name` to call a
  directory entry and `cancel` to stop a ringing doorbell.
  Requires UniFi Access 4.0.10 or later and an API token with `edit:device`.

## [3.1.1] - 2026-07-29

### Fixed
- **Guest passes:** reactivating or extending a pass that had already ended now
  re-assigns its PIN/QR credentials, so they work at the door again. Previously
  only the validity window was reopened while the controller had already removed
  the credentials. If the stored plaintext PIN is no longer available, a new PIN
  is generated and shown; credentials of a still-active pass are left unchanged.

## [3.1.0] - 2026-07-29

First tagged release of the **advanced** fork, branched from upstream 3.0.8.

### Added
- **Per-reader access-method switches** — Face Unlock, NFC, PIN, QR, Mobile
  Button, Mobile Tap, Hand Wave and Touch Pass, capability-gated per reader.
- **Face Anti-Spoofing** and **PIN Keypad Layout** selects.
- **Time-limited guest passes** (PIN/QR, single or multi-door) with a bundled
  Lovelace card.
- **Last Access** sensor with a bundled Lovelace card; doorbell rings appear as
  their own entries.
- **Garage door / gate (UGT)** cover mode with a per-door entity-type select.
- Doorbell entities fire the standard `ring` event while keeping the legacy
  start/stop events.

### Changed
- Guest card: the green arrival time is shown only while a pass is *active* or
  *expired*; revoked and reactivated passes show the validity end time again.
- Declared `http` and `frontend` as `after_dependencies`, required for the
  bundled cards.
- Documented all advanced features in the README.

---

# Upstream history

Releases of the original [imhotep/hass-unifi-access](https://github.com/imhotep/hass-unifi-access),
kept for reference. This fork branched from upstream **3.0.8**; upstream releases
between 1.3.2 and 3.0.8 are not documented here — see the upstream repository.

## [Unreleased upstream at the time of the fork]

### Added
- Full Unicode support for device names with special characters (ö, ä, ü, etc.)
- Support for Unifi Access G3 Intercom (UA-G3-Intercom)
- Unicode NFC normalization for consistent door name handling
- Fixed doorbell event detection for devices with special character names

### Fixed
- Unicode door name matching issues that prevented doorbell events from being detected
- WebSocket event matching for devices with German umlauts and other special characters

### Changed
- Improved international character support for German, French, and other languages

## [1.3.2] - 2024-10-21

### Changed
- Testing new event behavior
- Documentation updates

## [1.3.1] - 2024-10-21

### Changed
- Updated manifest version
- Documentation improvements

## [1.3.0] - 2024-09-15

### Added
- Door entry/exit result information in event attributes
- Device door association improvements

### Changed
- Updated async entry types for better compatibility

## [1.2.9] - 2024-08-12

### Added
- Better error handling for thumbnails
- Stale entity removal functionality

### Fixed
- Polling issues
- Thumbnail retrieval errors

## [1.2.8] - 2024-07-28

### Fixed
- DPS (Door Position Sensor) handling improvements
- Lock rule logic corrections
- Issues with UA-ULTRA devices (#96)

### Changed
- Version bumping process

## [1.2.7] - 2024-06-15

### Added
- Thumbnail support for door events
- Support for additional hub types
- Updated documentation links

### Changed
- Improved datetime handling
- Better hub compatibility

## [1.2.6] - 2024-05-20

### Added
- Interface device filtering (ignore interface devices)

### Fixed
- Restored missing credential provider functionality
- Small compatibility improvements

## [1.2.5] - 2024-04-18

### Added
- Chinese (Simplified) translation support

### Changed
- Updated manifest version

## [1.2.4] - 2024-03-25

### Added
- Basic support for UA-Intercom devices
- Credential Provider information for access.logs.add events
- Improved logging functionality

### Changed
- Updated README with new device support

## [1.2.3] - 2024-02-28

### Added
- Support for UAH-DOOR device type
- Default handler for unknown hub types
- Better error messages for unsupported devices

### Fixed
- Issue templates updated
- Documentation type corrections

## [1.2.2] - 2024-02-15

### Added
- Support for multiple doors on single update messages
- German (de) translation
- Italian (it) translation
- Dutch (nl) translation

### Changed
- Improved multi-door handling logic
- Code comments and documentation

## [1.2.1] - 2024-01-20

### Added
- Translation support infrastructure
- Multiple language files

## [1.2.0] - 2024-01-10

### Added
- Evacuation and lockdown functionality
- Temporary lock rules support
- Support for UGT (Unifi Gate Hub) devices
- Support for UAH-Ent (Enterprise) devices
- Support for UA-ULTRA devices
- GitHub Actions workflow
- Translation keys system

### Fixed
- Coordinator performance improvements
- Door lock rule support detection
- KeyError exception handling

### Changed
- Manifest file organization (alphabetical sorting)
- Documentation updates

## [1.1.6] - 2023-11-15

### Changed
- Version number update

## [1.1.5] - 2023-11-10

### Changed
- Updated manifest version
- Updated requests and websocket-client library versions

### Added
- Hardware doorbell support
- Instant updates via WebSocket
- Configuration cleanup

## [1.1.4] - 2023-10-25

### Added
- Support for OPEN door events
- Code refactoring for better maintainability

## [1.1.3] - 2023-10-15

### Added
- Event system implementation
- Access and doorbell press events
- Event metadata (door_name, door_id, type, authentication, actor)

### Fixed
- Potential threading issues
- Unused variable cleanup

### Changed
- README documentation improvements

## [1.1.2] - 2023-09-28

### Fixed
- Doorbell press variable assignment issues

## [1.1.1] - 2023-09-20

### Added
- Automatic WebSocket reconnection on connection close
- 5-second retry interval for reconnections

### Fixed
- Connection stability improvements

## [1.1.0] - 2023-09-10

### Added
- WebSocket support for real-time updates
- Doorbell status as boolean sensor
- String localization support

### Changed
- Moved from polling to WebSocket-based updates
- Improved real-time responsiveness

## [1.0.3] - 2023-08-25

### Fixed
- Only add doors when `is_bind_hub` is True
- Improved hub binding logic

## [1.0.2] - 2023-08-15

### Added
- Support for custom ports in configuration

## [1.0.1] - 2023-08-10

### Added
- SSL certificate verification option
- Configurable SSL handling

### Changed
- README documentation updates

## [1.0.0] - 2023-08-01

### Added
- Initial release
- Basic Unifi Access integration
- Door lock/unlock functionality
- Door position sensors
- Configuration flow setup
- Support for UAH (Unifi Access Hub)
- HACS integration
- Basic documentation

### Features
- Door control via Home Assistant interface
- Door position monitoring
- API token-based authentication
- SSL certificate handling options

---

## Legend

- **Added** - New features
- **Changed** - Changes in existing functionality  
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Vulnerability fixes