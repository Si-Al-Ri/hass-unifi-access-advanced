/*
 * UniFi Access — Guest Pass card
 * Bundled with the hass-unifi-access integration and auto-registered.
 * Lovelace type: custom:unifi-access-guest-card
 *
 * The UI follows Home Assistant's language (hass.locale.language) — de, en,
 * it, nl and zh-Hans are bundled; unknown languages fall back to English.
 */

const DOMAIN = "unifi_access";

// ---- translations ------------------------------------------------------
const I18N = {
  de: {
    header: "UniFi Access · Gastzugänge",
    loading: "Lädt…",
    empty: "Noch keine Gastzugänge.",
    error_prefix: "Fehler: ",
    new_pass: "+ Neuer Gastzugang",
    f_name_label: "Name des Gasts",
    f_name_ph: "Max Mustermann",
    f_doors: "Türen (mind. eine)",
    all_doors: "Alle Türen",
    f_from: "Gültig ab",
    f_until: "Gültig bis",
    f_cred_label: "Zugangsart (mind. eine)",
    cred_pin: "PIN-Code",
    cred_qr: "QR-Code",
    btn_cancel: "Abbrechen",
    btn_create: "Erstellen",
    btn_extend: "Verlängern",
    ct_inactive: "Zugangsdaten nur bei aktivem Pass verfügbar",
    act_extend: "Verlängern",
    act_revoke: "Widerrufen",
    act_delete: "Löschen",
    confirm_delete: "Gastzugang „{name}“ endgültig löschen? Dies kann nicht rückgängig gemacht werden.",
    delete_failed: "Löschen fehlgeschlagen: ",
    until_prefix: "bis ",
    arrived_prefix: "Angekommen ",
    confirm_revoke: "Gastzugang „{name}“ widerrufen?",
    revoke_failed: "Widerrufen fehlgeschlagen: ",
    err_period: "Bitte Zeitraum angeben.",
    err_order: "„Gültig bis“ muss nach „Gültig ab“ liegen.",
    err_name: "Bitte einen Namen eingeben.",
    err_cred: "Bitte mindestens eine Zugangsart wählen.",
    err_door: "Bitte mindestens eine Tür wählen.",
    status_active: "Aktiv",
    status_expired: "Abgelaufen",
    status_revoked: "Widerrufen",
  },
  en: {
    header: "UniFi Access · Guest Passes",
    loading: "Loading…",
    empty: "No guest passes yet.",
    error_prefix: "Error: ",
    new_pass: "+ New guest pass",
    f_name_label: "Guest name",
    f_name_ph: "Jane Doe",
    f_doors: "Doors (at least one)",
    all_doors: "All doors",
    f_from: "Valid from",
    f_until: "Valid until",
    f_cred_label: "Access type (at least one)",
    cred_pin: "PIN code",
    cred_qr: "QR code",
    btn_cancel: "Cancel",
    btn_create: "Create",
    btn_extend: "Extend",
    ct_inactive: "Credentials are only available while the pass is active",
    act_extend: "Extend",
    act_revoke: "Revoke",
    act_delete: "Delete",
    confirm_delete: "Permanently delete guest pass “{name}”? This cannot be undone.",
    delete_failed: "Delete failed: ",
    until_prefix: "until ",
    arrived_prefix: "Arrived ",
    confirm_revoke: "Revoke guest pass “{name}”?",
    revoke_failed: "Revoke failed: ",
    err_period: "Please specify a time period.",
    err_order: "“Valid until” must be after “Valid from”.",
    err_name: "Please enter a name.",
    err_cred: "Please choose at least one access type.",
    err_door: "Please choose at least one door.",
    status_active: "Active",
    status_expired: "Expired",
    status_revoked: "Revoked",
  },
  it: {
    header: "UniFi Access · Pass ospiti",
    loading: "Caricamento…",
    empty: "Nessun pass ospite.",
    error_prefix: "Errore: ",
    new_pass: "+ Nuovo pass ospite",
    f_name_label: "Nome dell'ospite",
    f_name_ph: "Mario Rossi",
    f_doors: "Porte (almeno una)",
    all_doors: "Tutte le porte",
    f_from: "Valido dal",
    f_until: "Valido fino al",
    f_cred_label: "Tipo di accesso (almeno uno)",
    cred_pin: "Codice PIN",
    cred_qr: "Codice QR",
    btn_cancel: "Annulla",
    btn_create: "Crea",
    btn_extend: "Estendi",
    ct_inactive: "Le credenziali sono disponibili solo quando il pass è attivo",
    act_extend: "Estendi",
    act_revoke: "Revoca",
    act_delete: "Elimina",
    confirm_delete: "Eliminare definitivamente il pass ospite “{name}”? L'operazione non è reversibile.",
    delete_failed: "Eliminazione non riuscita: ",
    until_prefix: "fino al ",
    arrived_prefix: "Arrivato il ",
    confirm_revoke: "Revocare il pass ospite “{name}”?",
    revoke_failed: "Revoca non riuscita: ",
    err_period: "Specificare un periodo di tempo.",
    err_order: "“Valido fino al” deve essere successivo a “Valido dal”.",
    err_name: "Inserire un nome.",
    err_cred: "Scegliere almeno un tipo di accesso.",
    err_door: "Scegliere almeno una porta.",
    status_active: "Attivo",
    status_expired: "Scaduto",
    status_revoked: "Revocato",
  },
  nl: {
    header: "UniFi Access · Gastpassen",
    loading: "Laden…",
    empty: "Nog geen gastpassen.",
    error_prefix: "Fout: ",
    new_pass: "+ Nieuwe gastpas",
    f_name_label: "Naam van de gast",
    f_name_ph: "Jan Jansen",
    f_doors: "Deuren (minstens één)",
    all_doors: "Alle deuren",
    f_from: "Geldig vanaf",
    f_until: "Geldig tot",
    f_cred_label: "Toegangstype (minstens één)",
    cred_pin: "Pincode",
    cred_qr: "QR-code",
    btn_cancel: "Annuleren",
    btn_create: "Aanmaken",
    btn_extend: "Verlengen",
    ct_inactive: "Inloggegevens zijn alleen beschikbaar zolang de pas actief is",
    act_extend: "Verlengen",
    act_revoke: "Intrekken",
    act_delete: "Verwijderen",
    confirm_delete: "Gastpas “{name}” definitief verwijderen? Dit kan niet ongedaan worden gemaakt.",
    delete_failed: "Verwijderen mislukt: ",
    until_prefix: "tot ",
    arrived_prefix: "Aangekomen ",
    confirm_revoke: "Gastpas “{name}” intrekken?",
    revoke_failed: "Intrekken mislukt: ",
    err_period: "Geef een tijdsperiode op.",
    err_order: "“Geldig tot” moet na “Geldig vanaf” liggen.",
    err_name: "Voer een naam in.",
    err_cred: "Kies minstens één toegangstype.",
    err_door: "Kies minstens één deur.",
    status_active: "Actief",
    status_expired: "Verlopen",
    status_revoked: "Ingetrokken",
  },
  "zh-Hans": {
    header: "UniFi Access · 访客通行证",
    loading: "加载中…",
    empty: "暂无访客通行证。",
    error_prefix: "错误：",
    new_pass: "+ 新建访客通行证",
    f_name_label: "访客姓名",
    f_name_ph: "张三",
    f_doors: "门（至少一扇）",
    all_doors: "所有门",
    f_from: "生效时间",
    f_until: "失效时间",
    f_cred_label: "访问方式（至少一种）",
    cred_pin: "PIN 码",
    cred_qr: "二维码",
    btn_cancel: "取消",
    btn_create: "创建",
    btn_extend: "延长",
    ct_inactive: "仅在通行证有效期内可查看凭据",
    act_extend: "延长",
    act_revoke: "撤销",
    act_delete: "删除",
    confirm_delete: "确定要永久删除访客通行证“{name}”吗？此操作无法撤销。",
    delete_failed: "删除失败：",
    until_prefix: "至 ",
    arrived_prefix: "已到达 ",
    confirm_revoke: "撤销访客通行证“{name}”？",
    revoke_failed: "撤销失败：",
    err_period: "请指定时间段。",
    err_order: "“失效时间”必须晚于“生效时间”。",
    err_name: "请输入姓名。",
    err_cred: "请至少选择一种访问方式。",
    err_door: "请至少选择一扇门。",
    status_active: "有效",
    status_expired: "已过期",
    status_revoked: "已撤销",
  },
};

// Maps a pass status to its translation key and colour class. The badge shows
// three states (active / expired / revoked); upcoming and arrived both map to
// active.
const STATUS = {
  upcoming: { key: "status_active", cls: "active" },
  arrived: { key: "status_active", cls: "active" },
  expired: { key: "status_expired", cls: "expired" },
  revoked: { key: "status_revoked", cls: "revoked" },
};

class UnifiAccessGuestCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._built = false;
    this._loaded = false;
    this._busy = false;
    this._lang = "en";
    this._doors = [];
    this._passes = [];
    this._error = null;
    this._mode = "create"; // "create" | "extend"
    this._extendId = null;
    this._creds = new Set(["pin"]);
    this._selDoors = new Set();
    this._expanded = new Set();
    // Subscription handle for the `unifi_access_guest_arrived` HA bus event.
    this._sub = false;
    this._unsub = null;
  }

  setConfig(config) {
    this._config = config || {};
  }

  set hass(hass) {
    this._hass = hass;
    this._lang = this._resolveLang(hass);
    if (!this._built) this._build();
    if (!this._sub) this._subscribe();
    if (!this._loaded) {
      this._loaded = true;
      this._loadData();
    }
  }

  getCardSize() {
    return 6;
  }

  static getStubConfig() {
    return {};
  }

  // ---- live refresh -----------------------------------------------------
  // The card's data comes from the list_guest_passes action (not entity
  // states), so it cannot subscribe to state_changed like the last-access
  // card. Instead it re-fetches on (re)connect, when the tab becomes visible
  // again, and on a periodic poll — so externally-made changes (new/expired/
  // revoked passes, status transitions) appear without a manual reload.

  connectedCallback() {
    if (this._loaded) this._refresh();
    if (!this._sub) this._subscribe();
    this._poll = setInterval(() => this._refresh(), 60000);
    this._onVisible = () => {
      if (document.visibilityState === "visible") this._refresh();
    };
    document.addEventListener("visibilitychange", this._onVisible);
  }

  disconnectedCallback() {
    if (this._poll) clearInterval(this._poll);
    this._poll = null;
    if (this._onVisible) {
      document.removeEventListener("visibilitychange", this._onVisible);
    }
    this._onVisible = null;
    if (typeof this._unsub === "function") this._unsub();
    this._unsub = null;
    this._sub = false;
  }

  // Subscribe to the `unifi_access_guest_arrived` HA bus event so the card
  // refreshes when a guest pass is first used, without waiting for the poll.
  _subscribe() {
    if (this._sub || !this._hass || !this._hass.connection) return;
    this._sub = true;
    this._hass.connection
      .subscribeEvents(() => this._refresh(), "unifi_access_guest_arrived")
      .then((unsub) => {
        this._unsub = unsub;
      })
      .catch(() => {
        this._sub = false;
      });
  }

  _refresh() {
    // Skip while a service call runs or the form is open — a reload would
    // discard in-progress form input and the door selection.
    if (!this._hass || this._busy) return;
    if (this._el && !this._el.form.classList.contains("hidden")) return;
    this._loadData();
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

  // ---- service helpers --------------------------------------------------

  async _call(service, data, withResponse) {
    const res = await this._hass.callService(
      DOMAIN,
      service,
      data || {},
      undefined,
      false,
      !!withResponse,
    );
    return res ? res.response : undefined;
  }

  async _loadData() {
    if (this._loadingData) return;
    this._loadingData = true;
    try {
      const resp = await this._call("list_guest_passes", {}, true);
      this._doors = (resp && resp.doors) || [];
      this._passes = (resp && resp.passes) || [];
      this._error = null;
    } catch (err) {
      this._error = err && err.message ? err.message : String(err);
    } finally {
      this._loadingData = false;
    }
    // The form (incl. the door selection) may have opened while the fetch was
    // in flight — don't rebuild the door list underneath it.
    if (this._el && this._el.form.classList.contains("hidden")) {
      this._fillDoors();
    }
    this._renderList();
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
        .section { padding: 4px 14px 14px; }
        .divider { height:1px; background: var(--divider-color); }
        .muted { color: var(--secondary-text-color); font-size: 13px; padding: 10px 4px; }
        .err { color: var(--error-color); font-size: 13px; padding: 8px 4px; }

        /* ---- pass list ---- */
        .pass { border-radius:12px; margin-top:8px; background: var(--secondary-background-color); }
        .pass:first-child { margin-top:2px; }
        .phead {
          display:flex; align-items:center; gap:11px; padding:10px 12px; cursor:pointer;
        }
        .av {
          width:34px; height:34px; border-radius:9px; flex:0 0 auto;
          display:flex; align-items:center; justify-content:center;
          color:#fff; font-size:13px; font-weight:600;
        }
        .pinfo { flex:1; min-width:0; }
        .pinfo b { font-size:14px; font-weight:500; display:block;
          white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .pinfo span { font-size:12px; color: var(--secondary-text-color); }
        .badge {
          font-size:11px; padding:3px 9px; border-radius:20px; white-space:nowrap; font-weight:600;
        }
        .badge.active   { background: rgba(3,169,244,.18); color:#4fc3f7; }
        .badge.expired  { background: var(--divider-color); color: var(--secondary-text-color); }
        .badge.revoked  { background: rgba(255,167,38,.18); color:#ffa726; }
        .pdetail { padding:4px 14px 14px; border-top:1px solid var(--divider-color); text-align:center; }
        .ct { font-size:11px; text-transform:uppercase; letter-spacing:.5px;
          color: var(--secondary-text-color); margin:12px 0 6px; }
        .pin {
          font-family: ui-monospace, Menlo, Consolas, monospace;
          font-size:30px; font-weight:600; letter-spacing:6px;
          padding:12px; border-radius:9px; background: var(--card-background-color);
          color: var(--primary-text-color);
        }
        .pdetail img { width:170px; height:170px; border-radius:9px; background:#fff; padding:8px; }
        .actions { display:flex; gap:8px; }
        .lnk {
          background:none; border:none; cursor:pointer; font-family:inherit;
          color: var(--primary-color); font-size:13px; padding:6px 4px;
        }
        .lnk.danger { color: var(--error-color); }
        .lnk:hover { text-decoration:underline; }

        /* ---- form ---- */
        .toggle {
          width:100%; margin-top:10px; padding:12px; border-radius:11px;
          border:1px dashed var(--primary-color); color: var(--primary-color);
          background:none; cursor:pointer; font-size:14px; font-family:inherit;
        }
        .form { margin-top:8px; }
        .field { margin-bottom:12px; }
        .field label { display:block; font-size:12px; color: var(--secondary-text-color); margin-bottom:5px; }
        .field input, .field select {
          width:100%; box-sizing:border-box; padding:10px 11px; font-size:14px; font-family:inherit;
          border:1px solid var(--divider-color); border-radius:9px;
          background: var(--card-background-color); color: var(--primary-text-color);
        }
        .row { display:flex; gap:10px; }
        .row .field { flex:1; }
        .doorlist {
          display:flex; flex-direction:column;
          border:1px solid var(--divider-color); border-radius:9px; overflow:hidden;
        }
        .dchk {
          display:flex; align-items:center; gap:10px; padding:9px 11px;
          cursor:pointer; font-size:13.5px; color: var(--primary-text-color);
        }
        .dchk:hover { background: var(--card-background-color); }
        .dchk input { width:17px; height:17px; margin:0; accent-color: var(--primary-color); }
        .dchk.dall { font-weight:600; border-bottom:1px solid var(--divider-color); }
        .seg { display:flex; gap:8px; }
        .seg button {
          flex:1; padding:10px; border-radius:9px; font-size:13px; cursor:pointer; font-family:inherit;
          border:1px solid var(--divider-color); background: var(--card-background-color);
          color: var(--secondary-text-color);
        }
        .seg button.on { background: var(--primary-color); color:#fff; border-color: var(--primary-color); }
        .formact { display:flex; gap:10px; margin-top:4px; }
        .btn {
          flex:1; padding:12px; border-radius:10px; font-size:14px; font-weight:500;
          cursor:pointer; font-family:inherit; border:none;
        }
        .btn.primary { background: var(--primary-color); color:#fff; }
        .btn.ghost { background:none; border:1px solid var(--divider-color); color: var(--primary-text-color); }
        .btn[disabled] { opacity:.5; cursor:default; }
        .ferr { color: var(--error-color); font-size:12.5px; margin-bottom:8px; }
        .hidden { display:none !important; }
      </style>
      <ha-card>
        <div class="head">
          <svg viewBox="0 0 24 24"><path d="M12 1 3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4Z"/></svg>
          ${this._esc(this._t("header"))}
        </div>
        <div class="section">
          <div id="list" class="muted">${this._esc(this._t("loading"))}</div>
          <button id="toggle" class="toggle">${this._esc(this._t("new_pass"))}</button>
          <div id="form" class="form hidden">
            <div class="field">
              <label>${this._esc(this._t("f_name_label"))}</label>
              <input id="f-name" type="text" placeholder="${this._esc(this._t("f_name_ph"))}" />
            </div>
            <div class="field" id="f-doorwrap">
              <label>${this._esc(this._t("f_doors"))}</label>
              <div id="f-doors" class="doorlist"></div>
            </div>
            <div class="row">
              <div class="field"><label>${this._esc(this._t("f_from"))}</label>
                <input id="f-from" type="datetime-local" /></div>
              <div class="field"><label>${this._esc(this._t("f_until"))}</label>
                <input id="f-until" type="datetime-local" /></div>
            </div>
            <div class="field" id="f-credwrap">
              <label>${this._esc(this._t("f_cred_label"))}</label>
              <div class="seg">
                <button id="c-pin" type="button">${this._esc(this._t("cred_pin"))}</button>
                <button id="c-qr" type="button">${this._esc(this._t("cred_qr"))}</button>
              </div>
            </div>
            <div id="f-err" class="ferr hidden"></div>
            <div class="formact">
              <button id="f-cancel" class="btn ghost">${this._esc(this._t("btn_cancel"))}</button>
              <button id="f-submit" class="btn primary">${this._esc(this._t("btn_create"))}</button>
            </div>
          </div>
        </div>
      </ha-card>
    `;
    const $ = (id) => this.shadowRoot.getElementById(id);
    this._el = {
      list: $("list"), toggle: $("toggle"), form: $("form"),
      name: $("f-name"), doorwrap: $("f-doorwrap"), doors: $("f-doors"),
      from: $("f-from"), until: $("f-until"), credwrap: $("f-credwrap"),
      cPin: $("c-pin"), cQr: $("c-qr"), err: $("f-err"),
      submit: $("f-submit"), cancel: $("f-cancel"),
    };
    this._el.toggle.addEventListener("click", () => this._startCreate());
    this._el.cancel.addEventListener("click", () => this._hideForm());
    this._el.submit.addEventListener("click", () => this._submit());
    this._el.cPin.addEventListener("click", () => this._toggleCred("pin"));
    this._el.cQr.addEventListener("click", () => this._toggleCred("qr"));
  }

  // ---- form helpers -----------------------------------------------------

  _toggleCred(c) {
    if (this._creds.has(c)) this._creds.delete(c);
    else this._creds.add(c);
    this._el.cPin.classList.toggle("on", this._creds.has("pin"));
    this._el.cQr.classList.toggle("on", this._creds.has("qr"));
  }

  // Render the door checkbox list (an "All doors" master toggle + one row
  // per door), reflecting the current selection.
  _fillDoors() {
    if (!this._el) return;
    const total = this._doors.length;
    const allOn = total > 0 && this._selDoors.size === total;
    let html = `
      <label class="dchk dall">
        <input type="checkbox" id="d-all" ${allOn ? "checked" : ""} />
        <span>${this._esc(this._t("all_doors"))}</span>
      </label>`;
    html += this._doors
      .map(
        (d) => `
      <label class="dchk">
        <input type="checkbox" data-door="${this._esc(d.id)}" ${
          this._selDoors.has(d.id) ? "checked" : ""
        } />
        <span>${this._esc(d.name)}</span>
      </label>`,
      )
      .join("");
    this._el.doors.innerHTML = html;

    this._el.doors.querySelectorAll("input[data-door]").forEach((cb) => {
      cb.addEventListener("change", () => {
        if (cb.checked) this._selDoors.add(cb.dataset.door);
        else this._selDoors.delete(cb.dataset.door);
        const all = this.shadowRoot.getElementById("d-all");
        if (all) {
          all.checked =
            this._doors.length > 0 &&
            this._selDoors.size === this._doors.length;
        }
      });
    });
    const allCb = this.shadowRoot.getElementById("d-all");
    if (allCb) {
      allCb.addEventListener("change", () => {
        this._selDoors = new Set(
          allCb.checked ? this._doors.map((d) => d.id) : [],
        );
        this._fillDoors();
      });
    }
  }

  _fmtInput(date) {
    const p = (n) => String(n).padStart(2, "0");
    return `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())}`
      + `T${p(date.getHours())}:${p(date.getMinutes())}`;
  }

  _defaultTimes() {
    const now = new Date();
    const later = new Date(now.getTime() + 2 * 3600 * 1000);
    this._el.from.value = this._fmtInput(now);
    this._el.until.value = this._fmtInput(later);
  }

  _startCreate() {
    this._mode = "create";
    this._extendId = null;
    this._el.name.value = "";
    this._el.name.disabled = false;
    this._el.doorwrap.classList.remove("hidden");
    this._selDoors = new Set();
    this._fillDoors();
    this._el.credwrap.classList.remove("hidden");
    this._creds = new Set(["pin"]);
    this._el.cPin.classList.add("on");
    this._el.cQr.classList.remove("on");
    this._defaultTimes();
    this._el.submit.textContent = this._t("btn_create");
    this._showForm();
  }

  _startExtend(pass) {
    this._mode = "extend";
    this._extendId = pass.visitor_id;
    this._el.name.value = pass.name || "";
    this._el.name.disabled = true;
    // Doors cannot be changed on extend — the visitor keeps its resources.
    this._el.doorwrap.classList.add("hidden");
    this._el.credwrap.classList.add("hidden");
    this._defaultTimes();
    this._el.submit.textContent = this._t("btn_extend");
    this._showForm();
  }

  _showForm() {
    this._el.err.classList.add("hidden");
    this._el.form.classList.remove("hidden");
    this._el.toggle.classList.add("hidden");
  }

  _hideForm() {
    this._el.form.classList.add("hidden");
    this._el.toggle.classList.remove("hidden");
  }

  _formError(msg) {
    this._el.err.textContent = msg;
    this._el.err.classList.remove("hidden");
  }

  async _submit() {
    if (this._busy) return;
    const from = this._el.from.value;
    const until = this._el.until.value;
    if (!from || !until) return this._formError(this._t("err_period"));
    if (until <= from) return this._formError(this._t("err_order"));

    let data;
    let service;
    if (this._mode === "extend") {
      service = "extend_guest_pass";
      data = { visitor_id: this._extendId, valid_from: from, valid_until: until };
    } else {
      const name = this._el.name.value.trim();
      if (!name) return this._formError(this._t("err_name"));
      if (!this._selDoors.size) return this._formError(this._t("err_door"));
      if (!this._creds.size) return this._formError(this._t("err_cred"));
      service = "create_guest_pass";
      data = {
        name,
        door_id: [...this._selDoors],
        valid_from: from,
        valid_until: until,
        credentials: [...this._creds],
      };
    }

    this._busy = true;
    this._el.submit.disabled = true;
    this._el.err.classList.add("hidden");
    try {
      const result = await this._call(service, data, true);
      if (result && result.visitor_id) this._expanded.add(result.visitor_id);
      this._hideForm();
      await this._loadData();
    } catch (err) {
      this._formError(err && err.message ? err.message : String(err));
    } finally {
      this._busy = false;
      this._el.submit.disabled = false;
    }
  }

  async _revoke(pass) {
    if (this._busy) return;
    if (!confirm(this._t("confirm_revoke", { name: pass.name }))) return;
    this._busy = true;
    try {
      await this._call("revoke_guest_pass", { visitor_id: pass.visitor_id });
      await this._loadData();
    } catch (err) {
      alert(
        this._t("revoke_failed") + (err && err.message ? err.message : err),
      );
    } finally {
      this._busy = false;
    }
  }

  async _delete(pass) {
    if (this._busy) return;
    if (!confirm(this._t("confirm_delete", { name: pass.name }))) return;
    this._busy = true;
    try {
      await this._call("delete_guest_pass", { visitor_id: pass.visitor_id });
      this._expanded.delete(pass.visitor_id);
      await this._loadData();
    } catch (err) {
      alert(
        this._t("delete_failed") + (err && err.message ? err.message : err),
      );
    } finally {
      this._busy = false;
    }
  }

  // ---- list rendering ---------------------------------------------------

  _renderList() {
    if (!this._el) return;
    const list = this._el.list;
    if (this._error) {
      list.className = "err";
      list.textContent = this._t("error_prefix") + this._error;
      return;
    }
    if (!this._passes.length) {
      list.className = "muted";
      list.textContent = this._t("empty");
      return;
    }
    list.className = "";
    list.innerHTML = "";
    this._passes.forEach((p) => list.appendChild(this._renderPass(p)));
  }

  _renderPass(p) {
    const st = STATUS[p.status] || STATUS.expired;
    const expanded = this._expanded.has(p.visitor_id);
    const until = new Date((p.valid_until || 0) * 1000).toLocaleString();
    const creds = (p.credentials || [])
      .map((c) => (c === "qr" ? "QR" : "PIN"))
      .join(" + ");

    // Show "Angekommen <time>" in green only while the pass is active
    // (arrived) or expired; otherwise show the validity end time.
    const showArrived =
      p.arrived_at && (p.status === "arrived" || p.status === "expired");
    let tail;
    if (showArrived) {
      const arrived = new Date(p.arrived_at * 1000).toLocaleString();
      tail =
        `<span style="color:#66bb6a">` +
        `${this._esc(this._t("arrived_prefix"))}${this._esc(arrived)}` +
        `</span>`;
    } else {
      tail = `${this._esc(this._t("until_prefix"))}${this._esc(until)}`;
    }

    const wrap = document.createElement("div");
    wrap.className = "pass";

    const head = document.createElement("div");
    head.className = "phead";
    head.innerHTML = `
      <div class="av" style="background:${this._color(p.name)}">${this._initials(p.name)}</div>
      <div class="pinfo">
        <b>${this._esc(p.name || "—")}</b>
        <span>${this._esc(p.door_name || "")} · ${creds} · ${tail}</span>
      </div>
      <span class="badge ${st.cls}">${this._esc(this._t(st.key))}</span>`;
    head.addEventListener("click", () => {
      if (expanded) this._expanded.delete(p.visitor_id);
      else this._expanded.add(p.visitor_id);
      this._renderList();
    });
    wrap.appendChild(head);

    if (expanded) {
      const det = document.createElement("div");
      det.className = "pdetail";
      let inner = "";
      if (p.pin) {
        inner += `<div class="ct">${this._esc(this._t("cred_pin"))}</div><div class="pin">${this._esc(p.pin)}</div>`;
      }
      if (p.qr_image) {
        inner += `<div class="ct">${this._esc(this._t("cred_qr"))}</div><div><img src="${p.qr_image}" alt="QR"/></div>`;
      }
      if (!p.pin && !p.qr_image) {
        inner += `<div class="ct">${this._esc(this._t("ct_inactive"))}</div>`;
      }
      det.innerHTML = inner;
      const act = document.createElement("div");
      act.className = "actions";
      act.style.cssText = "justify-content:center;margin-top:12px";
      const ext = document.createElement("button");
      ext.className = "lnk";
      ext.textContent = this._t("act_extend");
      ext.addEventListener("click", () => this._startExtend(p));
      const rev = document.createElement("button");
      rev.className = "lnk danger";
      rev.textContent = this._t("act_revoke");
      rev.addEventListener("click", () => this._revoke(p));
      const del = document.createElement("button");
      del.className = "lnk danger";
      del.textContent = this._t("act_delete");
      del.addEventListener("click", () => this._delete(p));
      act.appendChild(ext);
      act.appendChild(rev);
      act.appendChild(del);
      det.appendChild(act);
      wrap.appendChild(det);
    }
    return wrap;
  }

  // ---- small helpers ----------------------------------------------------

  _initials(name) {
    const parts = String(name || "?").trim().split(/\s+/).slice(0, 2);
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

if (!customElements.get("unifi-access-guest-card")) {
  customElements.define("unifi-access-guest-card", UnifiAccessGuestCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "unifi-access-guest-card")) {
  window.customCards.push({
    type: "unifi-access-guest-card",
    name: "UniFi Access Guest Pass",
    description: "Create and manage time-limited guest passes (PIN/QR).",
  });
}
