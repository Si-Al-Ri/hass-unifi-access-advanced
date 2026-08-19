/*
 * UniFi Access — Last Access card
 * Bundled with the hass-unifi-access integration and auto-registered.
 * Lovelace type: custom:unifi-access-last-access-card
 *
 * Shows the most recent access events (who / direction / method / reader /
 * result / when), merged across all doors and sorted newest first. Fed by the
 * integration's last-access sensors and their `events` history. Expanding an
 * event shows the snapshot the reader captured, if the door has a camera;
 * clicking the thumbnail opens it full size.
 *
 * The UI follows Home Assistant's language (hass.locale.language) — de, en,
 * it, nl and zh-Hans are bundled; unknown languages fall back to English.
 *
 * YAML config:
 *   type: custom:unifi-access-last-access-card
 *   max_logs: 4          # how many events to list (default 5)
 *   entities:            # optional — restrict to specific sensors
 *     - sensor.haustuer_letzter_zutritt
 */

// ---- translations ------------------------------------------------------
const I18N = {
  de: {
    header: "UniFi Access · Letzter Zutritt",
    loading: "Lädt…",
    empty: "Noch keine Zutritte aufgezeichnet. (WebSocket-Modus erforderlich.)",
    doorbell_event: "Jemand hat geklingelt",
    dir_entry: "Zutritt",
    dir_exit: "Verlassen",
    m_nfc: "NFC-Tag",
    m_face: "Gesichtserkennung",
    m_pin: "PIN-Nummer",
    m_qr: "QR-Code",
    m_mobiletap: "Mobiles Tippen",
    m_mobilebutton: "Mobile Taste",
    m_touchpass: "Touch Pass",
    m_wave: "Handbewegung",
    denied_inline: "· abgewiesen",
    d_time: "Uhrzeit",
    d_who: "Wer",
    d_direction: "Richtung",
    d_method: "Methode",
    d_reader: "Reader",
    d_door: "Tür",
    d_result: "Ergebnis",
    d_picture: "Bild",
    res_granted: "Gewährt",
    res_denied: "Abgewiesen",
    ago_now: "gerade eben",
    ago_min: "vor {n} min",
    ago_hour: "vor {n} h",
    ago_day: "vor {n} d",
  },
  en: {
    header: "UniFi Access · Last Access",
    loading: "Loading…",
    empty: "No accesses recorded yet. (WebSocket mode required.)",
    doorbell_event: "Someone rang the doorbell",
    dir_entry: "Entry",
    dir_exit: "Exit",
    m_nfc: "NFC tag",
    m_face: "Face recognition",
    m_pin: "PIN code",
    m_qr: "QR code",
    m_mobiletap: "Mobile tap",
    m_mobilebutton: "Mobile button",
    m_touchpass: "Touch Pass",
    m_wave: "Hand wave",
    denied_inline: "· denied",
    d_time: "Time",
    d_who: "Who",
    d_direction: "Direction",
    d_method: "Method",
    d_reader: "Reader",
    d_door: "Door",
    d_result: "Result",
    d_picture: "Picture",
    res_granted: "Granted",
    res_denied: "Denied",
    ago_now: "just now",
    ago_min: "{n} min ago",
    ago_hour: "{n} h ago",
    ago_day: "{n} d ago",
  },
  it: {
    header: "UniFi Access · Ultimo accesso",
    loading: "Caricamento…",
    empty: "Nessun accesso registrato. (Richiede la modalità WebSocket.)",
    doorbell_event: "Qualcuno ha suonato il campanello",
    dir_entry: "Ingresso",
    dir_exit: "Uscita",
    m_nfc: "Tag NFC",
    m_face: "Riconoscimento facciale",
    m_pin: "Codice PIN",
    m_qr: "Codice QR",
    m_mobiletap: "Tocco mobile",
    m_mobilebutton: "Pulsante mobile",
    m_touchpass: "Touch Pass",
    m_wave: "Gesto della mano",
    denied_inline: "· negato",
    d_time: "Ora",
    d_who: "Chi",
    d_direction: "Direzione",
    d_method: "Metodo",
    d_reader: "Lettore",
    d_door: "Porta",
    d_result: "Esito",
    d_picture: "Immagine",
    res_granted: "Consentito",
    res_denied: "Negato",
    ago_now: "proprio ora",
    ago_min: "{n} min fa",
    ago_hour: "{n} h fa",
    ago_day: "{n} g fa",
  },
  nl: {
    header: "UniFi Access · Laatste toegang",
    loading: "Laden…",
    empty: "Nog geen toegangen geregistreerd. (WebSocket-modus vereist.)",
    doorbell_event: "Iemand heeft aangebeld",
    dir_entry: "Toegang",
    dir_exit: "Vertrek",
    m_nfc: "NFC-tag",
    m_face: "Gezichtsherkenning",
    m_pin: "Pincode",
    m_qr: "QR-code",
    m_mobiletap: "Mobiel tikken",
    m_mobilebutton: "Mobiele knop",
    m_touchpass: "Touch Pass",
    m_wave: "Handgebaar",
    denied_inline: "· geweigerd",
    d_time: "Tijd",
    d_who: "Wie",
    d_direction: "Richting",
    d_method: "Methode",
    d_reader: "Lezer",
    d_door: "Deur",
    d_result: "Resultaat",
    d_picture: "Afbeelding",
    res_granted: "Toegestaan",
    res_denied: "Geweigerd",
    ago_now: "zojuist",
    ago_min: "{n} min geleden",
    ago_hour: "{n} u geleden",
    ago_day: "{n} d geleden",
  },
  "zh-Hans": {
    header: "UniFi Access · 最近门禁",
    loading: "加载中…",
    empty: "尚未记录门禁事件。（需要 WebSocket 模式。）",
    doorbell_event: "有人按了门铃",
    dir_entry: "进入",
    dir_exit: "离开",
    m_nfc: "NFC 标签",
    m_face: "人脸识别",
    m_pin: "PIN 码",
    m_qr: "二维码",
    m_mobiletap: "移动轻触",
    m_mobilebutton: "移动按钮",
    m_touchpass: "Touch Pass",
    m_wave: "挥手",
    denied_inline: "· 已拒绝",
    d_time: "时间",
    d_who: "人员",
    d_direction: "方向",
    d_method: "方式",
    d_reader: "读卡器",
    d_door: "门",
    d_result: "结果",
    d_picture: "图片",
    res_granted: "已允许",
    res_denied: "已拒绝",
    ago_now: "刚刚",
    ago_min: "{n} 分钟前",
    ago_hour: "{n} 小时前",
    ago_day: "{n} 天前",
  },
};

const GENERIC_METHOD_ICON =
  "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 15h-2v-2h2Zm0-4h-2V7h2Z";

const DIRECTIONS = {
  entry: { k: "dir_entry", cls: "in", arrow: "M5 12h14M13 6l6 6-6 6" },
  exit: { k: "dir_exit", cls: "out", arrow: "M19 12H5M11 6l-6 6 6 6" },
};

// Maps raw method / credential codes to a translation key + an icon path.
const METHODS = {
  NFC: { k: "m_nfc", icon: "M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2Zm-9 11H7a2 2 0 0 1 0-4h2V9H7a4 4 0 0 0 0 8h4Zm6 0h-2a4 4 0 0 0 0-8h-4v2h4a2 2 0 0 1 0 4h2Z" },
  FACE: { k: "m_face", icon: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm-3 7a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Zm6 0a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Zm-6.5 6h7a3.5 3.5 0 0 1-7 0Z" },
  FACEUNLOCK: { k: "m_face", icon: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm-3 7a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Zm6 0a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Zm-6.5 6h7a3.5 3.5 0 0 1-7 0Z" },
  IDENTITYFACEUNLOCK: { k: "m_face", icon: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm-3 7a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Zm6 0a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3Zm-6.5 6h7a3.5 3.5 0 0 1-7 0Z" },
  PIN: { k: "m_pin", icon: "M3 5h18v4H3Zm0 6h18v4H3Zm0 6h12v2H3Z" },
  PINCODE: { k: "m_pin", icon: "M3 5h18v4H3Zm0 6h18v4H3Zm0 6h12v2H3Z" },
  QR: { k: "m_qr", icon: "M3 3h8v8H3Zm2 2v4h4V5Zm8-2h8v8h-8Zm2 2v4h4V5ZM3 13h8v8H3Zm2 2v4h4v-4Zm8-2h3v3h-3Zm5 0h3v3h-3Zm-5 5h3v3h-3Zm5 0h3v3h-3Z" },
  QRCODE: { k: "m_qr", icon: "M3 3h8v8H3Zm2 2v4h4V5Zm8-2h8v8h-8Zm2 2v4h4V5ZM3 13h8v8H3Zm2 2v4h4v-4Zm8-2h3v3h-3Zm5 0h3v3h-3Zm-5 5h3v3h-3Zm5 0h3v3h-3Z" },
  MOBILETAP: { k: "m_mobiletap", icon: "M17 1H7a2 2 0 0 0-2 2v18a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3a2 2 0 0 0-2-2Zm0 18H7V5h10Z" },
  BTTAP: { k: "m_mobiletap", icon: "M17 1H7a2 2 0 0 0-2 2v18a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3a2 2 0 0 0-2-2Zm0 18H7V5h10Z" },
  MOBILEBUTTON: { k: "m_mobilebutton", icon: "M17 1H7a2 2 0 0 0-2 2v18a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3a2 2 0 0 0-2-2Zm-5 20a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Z" },
  BTBUTTON: { k: "m_mobilebutton", icon: "M17 1H7a2 2 0 0 0-2 2v18a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3a2 2 0 0 0-2-2Zm-5 20a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3Z" },
  TOUCHPASS: { k: "m_touchpass", icon: "M9 11.2V7a3 3 0 0 1 6 0v4.2a5 5 0 1 1-6 0ZM12 5a2 2 0 0 0-2 2v4h4V7a2 2 0 0 0-2-2Z" },
  WAVE: { k: "m_wave", icon: "M9 11V4a1.5 1.5 0 0 1 3 0v6V3a1.5 1.5 0 0 1 3 0v7V5a1.5 1.5 0 0 1 3 0v9a7 7 0 0 1-7 7 7 7 0 0 1-6.3-3.9L4 14a1.6 1.6 0 0 1 2.4-2L9 14Z" },
  HANDWAVE: { k: "m_wave", icon: "M9 11V4a1.5 1.5 0 0 1 3 0v6V3a1.5 1.5 0 0 1 3 0v7V5a1.5 1.5 0 0 1 3 0v9a7 7 0 0 1-7 7 7 7 0 0 1-6.3-3.9L4 14a1.6 1.6 0 0 1 2.4-2L9 14Z" },
};

const ICON = {
  time: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 11h-2V6h2Zm0 0 4.5 2.7-1 1.6L11 14Z",
  who: "M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0 2c-4 0-9 2-9 6v2h18v-2c0-4-5-6-9-6Z",
  reader: "M4 2h16a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Zm2 4v4h12V6Zm0 8h6v4H6Z",
  door: "M5 3h11a2 2 0 0 1 2 2v16h3v2H3v-2h2Zm9 8a1 1 0 1 0 0 2 1 1 0 0 0 0-2Z",
  result: "M9 16.2 4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4Z",
  picture:
    "M21 19V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2ZM8.5 13.5l2.5 3 3.5-4.5 4.5 6H5Z",
};

// Endpoint serving the stored capture images. Requests are authenticated with
// a signed path obtained from Home Assistant, valid for SIGN_TTL seconds and
// renewed SIGN_RENEW seconds before it runs out.
const CAPTURE_URL = "/api/unifi_access/capture/";
const SIGN_TTL = 3600;
const SIGN_RENEW = 300;

// Trailing localized sensor-name fragments stripped to derive the door name.
const SENSOR_NAME_RE =
  /\s*(letzter zutritt|last access|ultimo accesso|laatste toegang|最近门禁)$/i;

class UnifiAccessLastAccessCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._built = false;
    this._expanded = new Set();
    this._lang = "en";
    // Live state overrides fed by an explicit state_changed subscription —
    // this guarantees updates even if the dashboard never pushes a fresh
    // `hass` object to the card.
    this._live = {};
    this._sub = false;
    this._unsub = null;
    // Incremented on every disconnect so a subscription that resolves after
    // the card is gone can be recognised and dropped instead of leaking.
    this._gen = 0;
    // capture id → { url, until }, so re-rendering does not re-sign.
    this._urls = {};
  }

  setConfig(config) {
    this._config = config || {};
    this._maxLogs = Math.max(1, parseInt(this._config.max_logs, 10) || 5);
  }

  set hass(hass) {
    this._hass = hass;
    this._lang = this._resolveLang(hass);
    if (!this._built) this._build();
    if (!this._sub) this._subscribe();
    this._renderIfChanged();
  }

  get hass() {
    return this._hass;
  }

  connectedCallback() {
    if (!this._sub) this._subscribe();
    // Keeps relative timestamps ("vor 3 min") fresh.
    if (this._tick) clearInterval(this._tick);
    this._tick = setInterval(() => {
      if (this._hass) this._render();
    }, 30000);
  }

  disconnectedCallback() {
    this._gen += 1;
    this._closeLightbox();
    if (this._tick) clearInterval(this._tick);
    this._tick = null;
    if (typeof this._unsub === "function") this._dropSubscription(this._unsub);
    this._unsub = null;
    this._sub = false;
  }

  // Unsubscribing returns a promise that rejects once the connection is gone;
  // swallow it so a closed connection does not surface as an unhandled error.
  _dropSubscription(unsub) {
    try {
      const result = unsub();
      if (result && typeof result.then === "function") result.catch(() => {});
    } catch (err) {
      /* connection already closed */
    }
  }

  // ---- i18n -------------------------------------------------------------

  _resolveLang(hass) {
    const raw = String(
      (hass && hass.locale && hass.locale.language) ||
        (hass && hass.language) ||
        "en",
    );
    if (I18N[raw]) return raw;
    const base = raw.split("-")[0];
    return I18N[base] ? base : "en";
  }

  _t(key, vars) {
    const dict = I18N[this._lang] || I18N.en;
    let s = dict[key] !== undefined ? dict[key] : I18N.en[key];
    if (s === undefined) return key;
    if (vars) {
      for (const k of Object.keys(vars)) s = s.replace(`{${k}}`, vars[k]);
    }
    return s;
  }

  // ---- live updates -----------------------------------------------------

  // Subscribe directly to state_changed so a door event re-renders the card
  // immediately, independent of the dashboard's hass-push timing.
  _subscribe() {
    if (this._sub || !this._hass || !this._hass.connection) return;
    this._sub = true;
    const gen = this._gen;
    this._hass.connection
      .subscribeEvents((ev) => this._onStateEvent(ev), "state_changed")
      .then((unsub) => {
        // The card was disconnected while subscribing — drop it right away,
        // otherwise it would stay active with nothing holding its handle.
        if (gen !== this._gen) {
          this._dropSubscription(unsub);
          return;
        }
        this._unsub = unsub;
      })
      .catch(() => {
        if (gen === this._gen) this._sub = false;
      });
  }

  _onStateEvent(ev) {
    const ns = ev && ev.data && ev.data.new_state;
    if (!ns || typeof ns.entity_id !== "string") return;
    if (!ns.entity_id.startsWith("sensor.")) return;
    if (!this._isLastAccess(ns)) return;
    this._live[ns.entity_id] = ns;
    this._renderIfChanged();
  }

  _isLastAccess(state) {
    const cfg = this._config && this._config.entities;
    if (Array.isArray(cfg) && cfg.length) return cfg.includes(state.entity_id);
    const a = state.attributes || {};
    if (Array.isArray(a.events)) return true;
    if (a.actor !== undefined && a.direction !== undefined) return true;
    return SENSOR_NAME_RE.test(String(a.friendly_name || ""));
  }

  // Merge the dashboard's states with any fresher live overrides.
  _states() {
    return Object.assign({}, (this._hass && this._hass.states) || {}, this._live);
  }

  _renderIfChanged() {
    const sig = this._signature();
    if (sig !== this._sig) {
      this._sig = sig;
      this._render();
    }
  }

  // Compact fingerprint of every last-access sensor's current state.
  // Uses last_updated (not last_changed) and the first event's time so that
  // an attribute-only update (doorbell ring → events array gets a new entry
  // but sensor.state stays the same) still triggers a re-render.
  _signature() {
    if (!this._hass) return "";
    const states = this._states();
    return (
      this._lang +
      "|" +
      this._entities()
        .map((id) => {
          const st = states[id];
          if (!st) return `${id}:none`;
          const ev = st.attributes && st.attributes.events;
          const n = Array.isArray(ev) ? ev.length : 0;
          const firstTime = (Array.isArray(ev) && ev[0] && ev[0].time) || "";
          return `${id}:${st.state}:${st.last_updated}:${n}:${firstTime}`;
        })
        .join("|")
    );
  }

  getCardSize() {
    return 2 + this._maxLogs;
  }

  static getStubConfig() {
    return { max_logs: 5 };
  }

  // ---- data -------------------------------------------------------------

  _entities() {
    if (Array.isArray(this._config.entities) && this._config.entities.length) {
      return this._config.entities;
    }
    const states = this._states();
    return Object.keys(states).filter(
      (id) => id.startsWith("sensor.") && this._isLastAccess(states[id]),
    );
  }

  // Merge every sensor's events into one list, newest first. Uses the
  // sensor's `events` history when available; otherwise falls back to the
  // single most-recent access carried in the flat state attributes (e.g. a
  // sensor restored from an older integration version).
  _events() {
    const states = this._states();
    const out = [];
    this._entities().forEach((id) => {
      const st = states[id];
      if (!st) return;
      const a = st.attributes || {};
      const door = a.door_name || this._stripName(a.friendly_name);
      const list = Array.isArray(a.events) ? a.events : [];

      if (list.length) {
        list.forEach((e, i) => {
          out.push({
            uid: `${id}#${e.time || i}`,
            time: e.time || st.state,
            actor: e.actor || "—",
            method: e.method || "",
            direction: e.direction || "",
            result: e.result || "",
            reader: e.reader || "",
            door: e.door_name || door,
            kind: e.kind || "",
            capture: e.capture_id || "",
          });
        });
      } else if (
        st.state &&
        !["unknown", "unavailable", ""].includes(st.state) &&
        (a.actor !== undefined || a.direction !== undefined)
      ) {
        out.push({
          uid: `${id}#${st.state}`,
          time: st.state,
          actor: a.actor || "—",
          method: a.method || "",
          direction: a.direction || "",
          result: a.result || "",
          reader: a.reader || "",
          door,
          kind: a.kind || "",
          capture: a.capture_id || "",
        });
      }
    });
    out.sort((x, y) => new Date(y.time) - new Date(x.time));
    return out.slice(0, this._maxLogs);
  }

  // ---- build (once) -----------------------------------------------------

  _build() {
    this._built = true;
    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 0; }
        .head {
          display:flex; align-items:center; gap:10px;
          padding:16px 18px 12px; font-size:18px; font-weight:500;
        }
        .head svg { width:22px; height:22px; fill: var(--primary-color); }
        .section { padding: 2px 14px 14px; }
        .muted { color: var(--secondary-text-color); font-size: 13px; padding: 14px 4px; text-align:center; }

        .ev { border-radius:12px; margin-top:8px; background: var(--secondary-background-color); }
        .ev:first-child { margin-top:2px; }
        .row { display:flex; align-items:center; gap:12px; padding:11px 12px; cursor:pointer; }
        .av {
          width:38px; height:38px; border-radius:10px; flex:0 0 auto;
          display:flex; align-items:center; justify-content:center;
          color:#fff; font-size:14px; font-weight:600;
        }
        .info { flex:1; min-width:0; }
        .info b {
          font-size:14px; font-weight:500; display:block;
          white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
        }
        .info .sub {
          font-size:12px; color: var(--secondary-text-color);
          white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
        }
        .meta { display:flex; flex-direction:column; align-items:flex-end; gap:5px; flex:0 0 auto; }
        .when { font-size:11.5px; color: var(--secondary-text-color); white-space:nowrap; }
        .dir {
          display:inline-flex; align-items:center; gap:4px;
          font-size:11px; font-weight:600; padding:3px 9px; border-radius:20px;
        }
        .dir svg { width:13px; height:13px; fill:none; stroke:currentColor;
          stroke-width:2.4; stroke-linecap:round; stroke-linejoin:round; }
        .dir.in  { background: rgba(67,160,71,.20); color:#66bb6a; }
        .dir.out { background: rgba(3,169,244,.18); color:#4fc3f7; }
        .dir.unknown { background: var(--divider-color); color: var(--secondary-text-color); }
        .denied { color:#ef5350 !important; }
        .denied-dot { color:#ef5350; font-weight:600; }
        .av.doorbell { background:#ffa726; }
        .av.doorbell svg { width:22px; height:22px; fill:#fff; }

        /* ---- expanded detail ---- */
        .detail { padding:4px 14px 12px; border-top:1px solid var(--divider-color); }
        .drow {
          display:flex; align-items:center; gap:10px;
          padding:9px 2px; border-bottom:1px solid var(--divider-color);
        }
        .drow:last-child { border-bottom:none; }
        .drow svg { width:18px; height:18px; fill: var(--secondary-text-color); flex:0 0 auto; }
        .dk { font-size:12px; color: var(--secondary-text-color); width:78px; flex:0 0 auto; }
        .dv { font-size:13.5px; color: var(--primary-text-color); font-weight:500; flex:1;
          text-align:right; word-break:break-word; }
        .dv.ok { color:#66bb6a; }
        .dv.no { color:#ef5350; }
        .thumb {
          width:72px; height:54px; object-fit:cover; border-radius:6px;
          display:block; margin-left:auto; cursor:zoom-in;
          background: var(--divider-color);
        }

        /* ---- full-size image overlay ---- */
        .lightbox {
          display:none; position:fixed; inset:0; z-index:9;
          background:rgba(0,0,0,.88); align-items:center; justify-content:center;
          cursor:zoom-out; padding:16px;
        }
        .lightbox.open { display:flex; }
        .lightbox img {
          max-width:96vw; max-height:92vh; border-radius:10px;
          box-shadow:0 8px 40px rgba(0,0,0,.6);
        }
      </style>
      <ha-card>
        <div class="head">
          <svg viewBox="0 0 24 24"><path d="M13 3a9 9 0 0 0-9 9H1l4 4 4-4H6a7 7 0 1 1 2 4.9l-1.5 1.5A9 9 0 1 0 13 3Zm-1 5v5l4.2 2.5 1-1.6L13.5 12V8Z"/></svg>
          <span id="head-text"></span>
        </div>
        <div class="section"><div id="list" class="muted"></div></div>
      </ha-card>
      <div class="lightbox" id="lightbox"><img alt=""></div>
    `;
    this._list = this.shadowRoot.getElementById("list");
    this._headText = this.shadowRoot.getElementById("head-text");
    this._lightbox = this.shadowRoot.getElementById("lightbox");
    this._lightbox.addEventListener("click", () => this._closeLightbox());
  }

  // ---- render -----------------------------------------------------------

  _render() {
    if (!this._list) return;
    this._headText.textContent = this._t("header");
    const events = this._events();
    this._pruneUrls(events);
    if (!events.length) {
      this._list.className = "muted";
      this._list.textContent = this._t("empty");
      return;
    }
    this._list.className = "";
    this._list.innerHTML = "";
    events.forEach((e) => this._list.appendChild(this._renderEvent(e)));
  }

  _renderEvent(e) {
    if (e.kind === "doorbell") return this._renderDoorbell(e);
    const denied = e.result !== "" && !this._granted(e.result);
    const dir = this._dir(e.direction);
    const subParts = [e.door, e.reader, this._method(e.method).label].filter(
      Boolean,
    );

    const wrap = document.createElement("div");
    wrap.className = "ev";

    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <div class="av" style="background:${this._color(e.actor)}">
        ${this._initials(e.actor)}
      </div>
      <div class="info">
        <b>${this._esc(e.actor)}${
          denied
            ? ` <span class="denied-dot">${this._esc(
                this._t("denied_inline"),
              )}</span>`
            : ""
        }</b>
        <div class="sub">${this._esc(subParts.join(" · ")) || "—"}</div>
      </div>
      <div class="meta">
        <span class="dir ${dir.cls}${denied ? " denied" : ""}">
          <svg viewBox="0 0 24 24"><path d="${dir.arrow}"/></svg>
          ${this._esc(dir.label)}
        </span>
        <span class="when">${this._esc(this._ago(e.time))}</span>
      </div>`;
    row.addEventListener("click", () => {
      if (this._expanded.has(e.uid)) this._expanded.delete(e.uid);
      else this._expanded.add(e.uid);
      this._render();
    });
    wrap.appendChild(row);

    if (this._expanded.has(e.uid)) {
      wrap.appendChild(this._renderDetail(e, dir));
    }
    return wrap;
  }

  // Doorbell rings don't have an actor / direction / method / result, so they
  // get a simpler row: bell-icon avatar, "Jemand hat geklingelt", door, time.
  _renderDoorbell(e) {
    const wrap = document.createElement("div");
    wrap.className = "ev";

    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <div class="av doorbell">
        <svg viewBox="0 0 24 24"><path d="M12 22a2 2 0 0 0 2-2h-4a2 2 0 0 0 2 2Zm6-6V11a6 6 0 0 0-5-5.9V4a1 1 0 0 0-2 0v1.1A6 6 0 0 0 6 11v5l-2 2v1h16v-1l-2-2Z"/></svg>
      </div>
      <div class="info">
        <b>${this._esc(this._t("doorbell_event"))}</b>
        <div class="sub">${this._esc(e.door || "—")}</div>
      </div>
      <div class="meta">
        <span class="when">${this._esc(this._ago(e.time))}</span>
      </div>`;
    row.addEventListener("click", () => {
      if (this._expanded.has(e.uid)) this._expanded.delete(e.uid);
      else this._expanded.add(e.uid);
      this._render();
    });
    wrap.appendChild(row);

    if (this._expanded.has(e.uid)) {
      const rows = [
        { icon: ICON.time, k: this._t("d_time"), v: this._fullTime(e.time) },
        { icon: ICON.door, k: this._t("d_door"), v: e.door || "—" },
      ];
      const det = document.createElement("div");
      det.className = "detail";
      det.innerHTML = rows
        .map(
          (r) => `
          <div class="drow">
            <svg viewBox="0 0 24 24"><path d="${r.icon}"/></svg>
            <span class="dk">${this._esc(r.k)}</span>
            <span class="dv">${this._esc(r.v)}</span>
          </div>`,
        )
        .join("");
      this._appendPicture(det, e.capture);
      wrap.appendChild(det);
    }
    return wrap;
  }

  // ---- capture images ---------------------------------------------------

  // Append a "picture" row carrying the event's snapshot. The row removes
  // itself when no image is stored for the event — the controller publishes
  // the snapshot a moment after the event, and doors without a camera never
  // publish one at all.
  _appendPicture(detail, captureId) {
    if (!captureId) return;
    const row = document.createElement("div");
    row.className = "drow";
    row.innerHTML = `
      <svg viewBox="0 0 24 24"><path d="${ICON.picture}"/></svg>
      <span class="dk">${this._esc(this._t("d_picture"))}</span>
      <span class="dv"><img class="thumb" alt=""></span>`;
    const img = row.querySelector("img");
    img.addEventListener("error", () => row.remove());
    img.addEventListener("click", (ev) => {
      ev.stopPropagation();
      this._openLightbox(img.src);
    });
    detail.appendChild(row);
    this._imageUrl(captureId).then((url) => {
      if (url) img.src = url;
      else row.remove();
    });
  }

  // Drop cached URLs for events that are no longer listed, bounding the cache
  // to the entries the card can currently show.
  _pruneUrls(events) {
    const listed = new Set(events.map((e) => e.capture).filter(Boolean));
    for (const captureId of Object.keys(this._urls)) {
      if (!listed.has(captureId)) delete this._urls[captureId];
    }
  }

  // Home Assistant signs the endpoint path so the browser can load the image
  // in a plain <img> tag, which cannot send an authorization header. The
  // signature is re-issued shortly before it expires, so a dashboard left
  // open for a long time keeps showing images.
  async _imageUrl(captureId) {
    const cached = this._urls[captureId];
    if (cached && cached.until > Date.now()) return cached.url;
    if (!this._hass || !this._hass.callWS) return "";
    try {
      const res = await this._hass.callWS({
        type: "auth/sign_path",
        path: CAPTURE_URL + encodeURIComponent(captureId),
        expires: SIGN_TTL,
      });
      this._urls[captureId] = {
        url: res.path,
        until: Date.now() + (SIGN_TTL - SIGN_RENEW) * 1000,
      };
      return res.path;
    } catch (err) {
      return "";
    }
  }

  _openLightbox(src) {
    if (!this._lightbox || !src) return;
    this._lightbox.querySelector("img").src = src;
    this._lightbox.classList.add("open");
  }

  _closeLightbox() {
    if (this._lightbox) this._lightbox.classList.remove("open");
  }

  _renderDetail(e, dir) {
    const m = this._method(e.method);
    const granted = this._granted(e.result);
    const rows = [
      { icon: ICON.time, k: this._t("d_time"), v: this._fullTime(e.time) },
      { icon: ICON.who, k: this._t("d_who"), v: e.actor || "—" },
      { icon: dir.arrow, k: this._t("d_direction"), v: dir.label, stroke: true },
      { icon: m.icon, k: this._t("d_method"), v: m.label || "—" },
      { icon: ICON.reader, k: this._t("d_reader"), v: e.reader || "—" },
      { icon: ICON.door, k: this._t("d_door"), v: e.door || "—" },
      {
        icon: ICON.result,
        k: this._t("d_result"),
        v: e.result
          ? granted
            ? this._t("res_granted")
            : this._t("res_denied")
          : "—",
        cls: e.result ? (granted ? "ok" : "no") : "",
      },
    ];
    const det = document.createElement("div");
    det.className = "detail";
    det.innerHTML = rows
      .map(
        (r) => `
        <div class="drow">
          <svg viewBox="0 0 24 24"${
            r.stroke
              ? ' fill="none" stroke="currentColor" stroke-width="2.4"' +
                ' stroke-linecap="round" stroke-linejoin="round"'
              : ""
          }><path d="${r.icon}"/></svg>
          <span class="dk">${this._esc(r.k)}</span>
          <span class="dv ${r.cls || ""}">${this._esc(r.v)}</span>
        </div>`,
      )
      .join("");
    this._appendPicture(det, e.capture);
    return det;
  }

  // ---- humanizing helpers ----------------------------------------------

  _dir(direction) {
    const x = DIRECTIONS[String(direction || "").toLowerCase()];
    if (x) return { label: this._t(x.k), cls: x.cls, arrow: x.arrow };
    return {
      label: this._t("dir_entry"),
      cls: "unknown",
      arrow: "M12 5v14M5 12h14",
    };
  }

  _method(raw) {
    const code = String(raw || "")
      .toUpperCase()
      .replace(/[^A-Z]/g, "");
    const m = METHODS[code];
    if (m) return { icon: m.icon, label: this._t(m.k) };
    return { icon: GENERIC_METHOD_ICON, label: raw ? String(raw) : "" };
  }

  _granted(result) {
    return /access|grant|erfolg|ok|allow/i.test(String(result));
  }

  _stripName(fn) {
    return String(fn || "").replace(SENSOR_NAME_RE, "") || "—";
  }

  _ago(iso) {
    const then = new Date(iso).getTime();
    if (isNaN(then)) return "";
    const diff = Math.max(0, Date.now() - then);
    const m = Math.floor(diff / 60000);
    if (m < 1) return this._t("ago_now");
    if (m < 60) return this._t("ago_min", { n: m });
    const h = Math.floor(m / 60);
    if (h < 24) return this._t("ago_hour", { n: h });
    const d = Math.floor(h / 24);
    if (d < 7) return this._t("ago_day", { n: d });
    return new Date(then).toLocaleDateString();
  }

  _fullTime(iso) {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleString();
  }

  _initials(name) {
    const parts = String(name || "?")
      .trim()
      .split(/\s+/)
      .slice(0, 2);
    return parts.map((w) => w[0] || "").join("").toUpperCase() || "?";
  }

  _color(name) {
    let h = 0;
    for (const ch of String(name || "")) h = (h * 31 + ch.charCodeAt(0)) % 360;
    return `hsl(${h},42%,46%)`;
  }

  _esc(s) {
    return String(s).replace(/[&<>"]/g, (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c],
    );
  }
}

if (!customElements.get("unifi-access-last-access-card")) {
  customElements.define("unifi-access-last-access-card", UnifiAccessLastAccessCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "unifi-access-last-access-card")) {
  window.customCards.push({
    type: "unifi-access-last-access-card",
    name: "UniFi Access Last Access",
    description:
      "Shows recent accesses — who, direction, method, reader.",
  });
}
