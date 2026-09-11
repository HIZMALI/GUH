"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Bell,
  Box,
  Building2,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircuitBoard,
  Clock,
  Database,
  FlaskConical,
  FolderTree,
  Gauge,
  GitBranch,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Network,
  PanelTop,
  Play,
  Radio,
  RefreshCw,
  Search,
  Server,
  Shield,
  ShieldCheck,
  Thermometer,
  TriangleAlert,
  Wifi,
  WifiOff,
  X,
  Zap,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  api,
  ApiError,
  dateTime,
  measuredValue,
  number,
  qualityLabel,
  time,
} from "@/lib/api";
import type {
  Alarm,
  Event,
  Fleet,
  Notification,
  Panel,
  Registers,
  Scenario,
  Session,
  Severity,
} from "@/lib/types";
import { TrendChart } from "./charts";
import { Schematic } from "./schematic";

type View =
  | "overview"
  | "panels"
  | "alarms"
  | "events"
  | "scada"
  | "notifications"
  | "sources";
const statusNames: Record<Severity, string> = {
  NORMAL: "Normal",
  ATTENTION: "Dikkat",
  WARNING: "Uyarı",
  CRITICAL: "Kritik",
};
const statusColors: Record<Severity, string> = {
  NORMAL: "#48d8b0",
  ATTENTION: "#dcc16d",
  WARNING: "#f4a561",
  CRITICAL: "#fb7885",
};
const navigation: { id: View; label: string; icon: LucideIcon }[] = [
  { id: "overview", label: "Genel bakış", icon: LayoutDashboard },
  { id: "panels", label: "Pano envanteri", icon: PanelTop },
  { id: "alarms", label: "Alarm merkezi", icon: Bell },
  { id: "events", label: "Olay geçmişi", icon: Activity },
  { id: "scada", label: "SCADA / Modbus", icon: Network },
  { id: "notifications", label: "Bildirimler", icon: Radio },
  { id: "sources", label: "Sistem ve kaynaklar", icon: GitBranch },
];
const scenarioNames: Record<string, string> = {
  normal_operation: "Normal çalışma",
  gradual_overload: "Kademeli aşırı yük",
  thermal_hotspot: "Termal sıcak nokta",
  high_humidity: "Yüksek nem",
  loose_connection_signature: "Gevşek bağlantı imzası",
  pd_degradation: "PD kötüleşmesi",
  combined_thermal_pd: "Termal + PD birleşimi",
  arc_event: "Arc Guard olayı",
  sensor_failure: "Sensör arızası",
  communication_loss: "İletişim kaybı",
};
const sessionKey = "gridsentinel.session";
function Badge({ state }: { state: Severity }) {
  return (
    <span className={`badge ${state?.toLowerCase()}`}>
      <i />
      {statusNames[state] || state}
    </span>
  );
}
function Empty({
  title,
  detail,
  icon: Icon = Database,
}: {
  title: string;
  detail?: string;
  icon?: LucideIcon;
}) {
  return (
    <div className="empty">
      <Icon size={30} />
      <strong>{title}</strong>
      {detail && <p>{detail}</p>}
    </div>
  );
}
function SectionHeading({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children}
    </div>
  );
}
function Login({ onLogin }: { onLogin: (s: Session) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await api<Session>("/auth/login", undefined, {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
      sessionStorage.setItem(sessionKey, JSON.stringify(data));
      onLogin(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Oturum açılamadı");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <div className="login-showcase">
        <Brand />
        <div className="login-copy">
          <div className="eyebrow">
            <span className="live-dot" /> ŞİRKET İÇİ İZLEME PLATFORMU
          </div>
          <h1>
            Sinyalleri birleştirin.
            <br />
            <span>Riski erken görün.</span>
          </h1>
          <p>
            Elektriksel, termal ve PD belirtilerini aynı bağlamda değerlendirin.
            Her alarmın arkasındaki nedeni anlayın.
          </p>
          <div className="login-flow">
            <div>
              <CircuitBoard />
              <strong>Mevcut pano</strong>
              <span>MPR · Arc Guard · Retrofit</span>
            </div>
            <ArrowRight />
            <div>
              <Activity />
              <strong>GridSentinel</strong>
              <span>Açıklanabilir risk</span>
            </div>
            <ArrowRight />
            <div>
              <ShieldCheck />
              <strong>Operasyon</strong>
              <span>Erken uyarı ve karar desteği</span>
            </div>
          </div>
        </div>
        <div className="login-foot">
          <ShieldCheck size={16} /> On-premise mimari <span>•</span> Salt okunur
          cihaz entegrasyonu
        </div>
      </div>
      <div className="login-form-side">
        <div className="login-form">
          <span className="login-icon">
            <LockKeyhole size={25} />
          </span>
          <h2>Operasyon merkezine giriş</h2>
          <p>
            Yerel kurulumda oluşturulan kullanıcı bilgilerinizle devam edin.
          </p>
          <form onSubmit={submit}>
            <label htmlFor="username">Kullanıcı adı</label>
            <input
              id="username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Kullanıcı adınızı girin"
              required
              maxLength={80}
            />
            <label htmlFor="password">Parola</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Parolanızı girin"
              required
              maxLength={256}
            />
            {error && (
              <div className="inline-error" role="alert">
                <TriangleAlert size={16} />
                {error}
              </div>
            )}
            <button className="primary login-submit" disabled={busy}>
              {busy ? "Bağlanıyor…" : "Güvenli giriş yap"}
              <ArrowRight size={17} />
            </button>
          </form>
          <div className="demo-disclosure">
            <FlaskConical size={17} />
            <div>
              <strong>Hackathon · Sentetik demo</strong>
              <p>
                Gerçek saha bağlantısı yoktur. Bu uygulama bir koruma rölesi
                değildir.
              </p>
            </div>
          </div>
        </div>
        <span className="login-version">
          GRIDSENTINEL / LOCAL PLATFORM V1.0
        </span>
      </div>
    </main>
  );
}
function Brand() {
  return (
    <div className="brand">
      <span className="brand-symbol">
        <Zap size={23} fill="currentColor" />
      </span>
      <div>
        Grid<span>Sentinel</span>
        <small>ENERJİYİ İZLE. ÖNCEDEN GÖR.</small>
      </div>
    </div>
  );
}
export function Dashboard() {
  const [session, setSession] = useState<Session | null>(null),
    [initialized, setInitialized] = useState(false),
    [view, setView] = useState<View>("overview"),
    [selectedId, setSelectedId] = useState<string | null>(null);
  const [fleet, setFleet] = useState<Fleet | null>(null),
    [panel, setPanel] = useState<Panel | null>(null),
    [alarms, setAlarms] = useState<Alarm[]>([]),
    [events, setEvents] = useState<Event[]>([]),
    [notifications, setNotifications] = useState<Notification[]>([]),
    [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [error, setError] = useState(""),
    [resourceErrors, setResourceErrors] = useState<Record<string, string>>({}),
    [loading, setLoading] = useState(false),
    [refresh, setRefresh] = useState(0),
    [toast, setToast] = useState(""),
    [demoOpen, setDemoOpen] = useState(false),
    [mobileOpen, setMobileOpen] = useState(false);
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(sessionKey);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (
          parsed.access_token &&
          parsed.username &&
          ["viewer", "operator", "admin"].includes(parsed.role)
        )
          setSession(parsed);
      }
    } catch {
      sessionStorage.removeItem(sessionKey);
    }
    setInitialized(true);
  }, []);
  const logout = useCallback(() => {
    sessionStorage.removeItem(sessionKey);
    setSession(null);
    setFleet(null);
    setPanel(null);
    setAlarms([]);
    setEvents([]);
    setNotifications([]);
    setSelectedId(null);
    setError("");
  }, []);
  useEffect(() => {
    if (!session) return;
    const controller = new AbortController();
    let inFlight = false;
    setLoading(true);
    async function load() {
      if (inFlight) return;
      inFlight = true;
      try {
        const data = await api<Fleet>("/fleet", session!.access_token, {
          signal: controller.signal,
        });
        setFleet(data);
        setError("");
        const resources = [
          ["alarms", "/alarms", setAlarms],
          ["events", "/events", setEvents],
          ["notifications", "/notifications", setNotifications],
          ["scenarios", "/scenarios", setScenarios],
        ] as const;
        const results = await Promise.allSettled(
          resources.map(async ([key, path, set]) => {
            const data = await api<{ items: never[] }>(
              path,
              session!.access_token,
              { signal: controller.signal },
            );
            set(data.items);
            return key;
          }),
        );
        const failed: Record<string, string> = {};
        results.forEach((r, i) => {
          if (r.status === "rejected" && !controller.signal.aborted)
            failed[resources[i][0]] =
              r.reason instanceof Error ? r.reason.message : "Veri alınamadı";
        });
        setResourceErrors(failed);
      } catch (e) {
        if (controller.signal.aborted) return;
        if (e instanceof ApiError && e.status === 401) {
          logout();
          setToast("Oturum süresi doldu. Yeniden giriş yapın.");
        } else setError(e instanceof Error ? e.message : "API erişilemiyor");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
        inFlight = false;
      }
    }
    void load();
    const timer = setInterval(load, 5000);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [session, refresh, logout]);
  useEffect(() => {
    setPanel((current) => (current?.id === selectedId ? current : null));
    if (!session || !selectedId) return;
    const controller = new AbortController();
    let running = false;
    async function load() {
      if (running) return;
      running = true;
      try {
        const result = await api<Panel>(
          `/panels/${encodeURIComponent(selectedId!)}`,
          session!.access_token,
          { signal: controller.signal },
        );
        setPanel(result);
        setResourceErrors((prev) => ({ ...prev, panel: "" }));
      } catch (e) {
        if (!controller.signal.aborted)
          setResourceErrors((prev) => ({
            ...prev,
            panel: e instanceof Error ? e.message : "Pano verisi alınamadı",
          }));
      } finally {
        running = false;
      }
    }
    void load();
    const timer = setInterval(load, 4000);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [session, selectedId, refresh]);
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [view, selectedId]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 6500);
    return () => clearTimeout(timer);
  }, [toast]);
  function navigate(id: View) {
    setView(id);
    setSelectedId(null);
    setMobileOpen(false);
  }
  async function acknowledge(id: string) {
    if (!session) return;
    try {
      await api(
        `/alarms/${encodeURIComponent(id)}/acknowledge`,
        session.access_token,
        { method: "POST" },
      );
      setToast("Alarm onayı kaydedildi. İzleme devam ediyor.");
      setRefresh((r) => r + 1);
    } catch (e) {
      setToast(e instanceof Error ? e.message : "Alarm onaylanamadı");
    }
  }
  if (!initialized)
    return (
      <div className="boot-screen">
        <Brand />
        <span>Yerel çalışma alanı açılıyor…</span>
      </div>
    );
  if (!session)
    return (
      <>
        <Login onLogin={setSession} />
        {toast && (
          <div className="toast" role="status">
            {toast}
          </div>
        )}
      </>
    );
  const canOperate = session.role !== "viewer";
  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}>
        <Brand />
        <div className="workspace">
          <div className="workspace-icon">
            <Building2 size={18} />
          </div>
          <div>
            <strong>Grid Up / Demo</strong>
            <small>Yerel çalışma alanı</small>
          </div>
          <ChevronDown size={14} />
        </div>
        <div className="nav-section-label">OPERASYON</div>
        <nav>
          {navigation.map((item, i) => (
            <button
              key={item.id}
              className={`${view === item.id && !selectedId ? "active" : ""} ${i === 4 ? "nav-divider" : ""}`}
              onClick={() => navigate(item.id)}
            >
              <item.icon size={18} />
              <span>{item.label}</span>
              {item.id === "alarms" && !!fleet?.summary.open_alarms && (
                <b>{fleet.summary.open_alarms}</b>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="environment">
            <span className="live-dot" />
            <span>ON-PREMISE</span>
            <LockKeyhole size={12} />
          </div>
          <div className="sidebar-demo">
            <FlaskConical size={18} />
            <strong>Sentetik demo ortamı</strong>
            <p>
              Veriler simüle edilmiştir.
              <br />
              Fiziksel saha bağlantısı yoktur.
            </p>
          </div>
          <div className="user-profile">
            <span className="avatar">
              {session.username.slice(0, 2).toUpperCase()}
            </span>
            <div>
              <strong>{session.username}</strong>
              <small>
                {session.role === "admin"
                  ? "Yönetici"
                  : session.role === "operator"
                    ? "Operatör"
                    : "Görüntüleyici"}
              </small>
            </div>
            <button
              className="icon-button"
              onClick={logout}
              aria-label="Çıkış yap"
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <button
              className="mobile-menu icon-button"
              aria-label="Menüyü aç"
              onClick={() => setMobileOpen(!mobileOpen)}
            >
              <LayoutDashboard size={20} />
            </button>
            <span>Çalışma alanı</span>
            <ChevronRight size={13} />
            <strong>
              {selectedId
                ? "Pano detayı"
                : navigation.find((n) => n.id === view)?.label}
            </strong>
          </div>
          <div className="topbar-right">
            <span className={`connection ${error ? "disconnected" : ""}`}>
              <span className="live-dot" />
              {error
                ? "API bağlantısı kesildi"
                : fleet
                  ? "Yerel API bağlı"
                  : "Bağlantı kuruluyor"}
            </span>
            <span className="topbar-divider" />
            <span className="topbar-clock">
              <Clock size={13} />
              {fleet ? time(fleet.timestamp) : "—"}
            </span>
            <button
              className="icon-button"
              aria-label="Bildirimleri göster"
              onClick={() => navigate("notifications")}
            >
              <Bell size={18} />
              {notifications.length > 0 && <i className="notification-dot" />}
            </button>
          </div>
        </header>
        <main className="main-content">
          {error && (
            <div className="connection-alert" role="alert">
              <WifiOff size={19} />
              <div>
                <strong>Canlı güncelleme alınamıyor</strong>
                <p>
                  {error}{" "}
                  {fleet
                    ? "Ekrandaki son değerler güncel kabul edilmemelidir."
                    : ""}
                </p>
              </div>
              <button
                className="secondary"
                onClick={() => setRefresh((r) => r + 1)}
              >
                Yeniden dene
              </button>
            </div>
          )}
          {selectedId ? (
            <>
              <button
                className="back-button"
                onClick={() => {
                  setSelectedId(null);
                  setPanel(null);
                }}
              >
                <ArrowLeft size={15} /> Pano listesine dön
              </button>
              {resourceErrors.panel && (
                <div className="inline-error" role="alert">
                  {resourceErrors.panel}
                </div>
              )}
              {panel ? (
                <PanelDetail
                  panel={panel}
                  canOperate={canOperate}
                  acknowledge={acknowledge}
                  onDemo={() => setDemoOpen(true)}
                />
              ) : (
                <Empty
                  title="Pano telemetrisi yükleniyor"
                  detail={selectedId}
                />
              )}
            </>
          ) : (
            <>
              {(view === "overview" || view === "panels") && (
                <>
                  <SectionHeading
                    eyebrow="OPERASYON MERKEZİ"
                    title={
                      view === "overview"
                        ? "Filonun nabzı, tek ekranda."
                        : "Pano envanteri"
                    }
                    description="Elektriksel, termal ve PD sinyallerinden açıklanabilir erken uyarı."
                  >
                    <div className="heading-actions">
                      <button
                        className="secondary"
                        onClick={() => setRefresh((r) => r + 1)}
                        disabled={loading}
                      >
                        <RefreshCw
                          size={15}
                          className={loading ? "spin" : ""}
                        />{" "}
                        Yenile
                      </button>
                      <button
                        className="primary"
                        onClick={() => setDemoOpen(true)}
                        disabled={!canOperate}
                      >
                        <Play size={14} fill="currentColor" /> Senaryo başlat
                      </button>
                    </div>
                  </SectionHeading>
                  <div className="context-strip">
                    <span>
                      <FlaskConical size={14} /> SENTETİK DEMO
                    </span>
                    <p>
                      Tüm sahalar ve gözlemler simüledir. Kaynağa dayalı donanım
                      eşlemeleri kullanılır.
                    </p>
                    <span className="refresh-label">5 sn yenileme</span>
                  </div>
                  {fleet ? (
                    <FleetView
                      fleet={fleet}
                      events={events}
                      eventError={resourceErrors.events}
                      onPanel={setSelectedId}
                      onEvents={() => navigate("events")}
                      inventory={view === "panels"}
                    />
                  ) : (
                    <div className="card">
                      <Empty
                        title={
                          error
                            ? "Filo verisi alınamadı"
                            : "Telemetri bekleniyor"
                        }
                        detail="Yerel API ve simülatör erişilebilir olduğunda panolar burada görünecek."
                      />
                    </div>
                  )}
                </>
              )}
              {view === "alarms" && (
                <>
                  <SectionHeading
                    eyebrow="OPERASYON / ALARMLAR"
                    title="Alarm merkezi"
                    description="Önceliklendirin, nedeni inceleyin ve operatör onayını kaydedin."
                  />
                  <ResourceError error={resourceErrors.alarms} />
                  <AlarmList
                    alarms={alarms}
                    canOperate={canOperate}
                    acknowledge={acknowledge}
                    onPanel={setSelectedId}
                  />
                </>
              )}
              {view === "events" && (
                <>
                  <SectionHeading
                    eyebrow="OPERASYON / KAYITLAR"
                    title="Olay geçmişi"
                    description="Sentetik telemetri, durum geçişleri ve alarm yaşam döngüsü."
                  />
                  <ResourceError error={resourceErrors.events} />
                  <EventList events={events} onPanel={setSelectedId} />
                </>
              )}
              {view === "notifications" && (
                <>
                  <SectionHeading
                    eyebrow="ENTEGRASYON / BİLDİRİMLER"
                    title="Bildirim günlüğü"
                    description="Mock adaptör tarafından oluşturulan bildirim kayıtları."
                  />
                  <div className="context-strip">
                    <span>
                      <FlaskConical size={14} /> SİMÜLE EDİLDİ
                    </span>
                    <p>
                      SMS ve WhatsApp gönderilmez. Alıcılar demo hedefleridir.
                    </p>
                  </div>
                  <ResourceError error={resourceErrors.notifications} />
                  <div className="card table-card">
                    <div className="card-heading">
                      <h3>Bildirim kayıtları</h3>
                      <span>{notifications.length} kayıt</span>
                    </div>
                    {notifications.length ? (
                      <div className="table-scroll">
                        <table>
                          <thead>
                            <tr>
                              <th>KANAL / ALICI</th>
                              <th>BİLDİRİM</th>
                              <th>PANO</th>
                              <th>ZAMAN</th>
                              <th>DURUM</th>
                            </tr>
                          </thead>
                          <tbody>
                            {notifications.map((n) => (
                              <tr key={n.id}>
                                <td>
                                  <strong className="table-strong">
                                    {n.channel.toUpperCase()}
                                  </strong>
                                  <small>{n.recipient}</small>
                                </td>
                                <td className="message-cell">{n.message}</td>
                                <td>
                                  <button
                                    className="text-link"
                                    onClick={() => setSelectedId(n.panel_id)}
                                  >
                                    {n.panel_id}
                                  </button>
                                </td>
                                <td className="nowrap muted">
                                  {dateTime(n.timestamp)}
                                </td>
                                <td>
                                  <span className="small-tag cyan">
                                    Simüle edildi
                                  </span>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <Empty
                        title="Henüz bildirim yok"
                        detail="Yeni veya şiddeti artan alarm mock bildirim oluşturur."
                        icon={Radio}
                      />
                    )}
                  </div>
                </>
              )}
              {view === "scada" && (
                <ScadaView
                  token={session.access_token}
                  panels={fleet?.panels || []}
                />
              )}
              {view === "sources" && <SourcesView />}
            </>
          )}
          <footer className="main-footer">
            <span>
              <Shield size={12} /> Condition monitoring ve karar desteği ·
              Koruma rölesi değildir
            </span>
            <span>
              GridSentinel v1.0 <i /> On-premise
            </span>
          </footer>
        </main>
      </div>
      {demoOpen && (
        <DemoDialog
          token={session.access_token}
          panels={fleet?.panels || []}
          scenarios={scenarios}
          initialPanel={selectedId || undefined}
          onClose={() => setDemoOpen(false)}
          onSuccess={(message) => {
            setToast(message);
            setRefresh((r) => r + 1);
            setDemoOpen(false);
          }}
        />
      )}
      {toast && (
        <div className="toast" role="status">
          <CheckCheck size={18} />
          {toast}
          <button
            className="icon-button"
            aria-label="Bildirimi kapat"
            onClick={() => setToast("")}
          >
            <X size={15} />
          </button>
        </div>
      )}
    </div>
  );
}
function ResourceError({ error }: { error?: string }) {
  return error ? (
    <div className="inline-error" role="alert">
      <TriangleAlert size={16} />
      {error}
    </div>
  ) : null;
}

function FleetView({
  fleet,
  events,
  eventError,
  onPanel,
  onEvents,
  inventory,
}: {
  fleet: Fleet;
  events: Event[];
  eventError?: string;
  onPanel: (id: string) => void;
  onEvents: () => void;
  inventory: boolean;
}) {
  const [query, setQuery] = useState(""),
    [status, setStatus] = useState("all"),
    [region, setRegion] = useState("all"),
    [substation, setSubstation] = useState("all"),
    [transformer, setTransformer] = useState("all"),
    [sort, setSort] = useState("risk"),
    [limit, setLimit] = useState(12);
  const s = fleet.summary;
  const regions = [...new Set(fleet.panels.map((p) => p.region))];
  const substations = [
    ...new Set(
      fleet.panels
        .filter((p) => region === "all" || p.region === region)
        .map((p) => p.substation),
    ),
  ];
  const transformers = [
    ...new Set(
      fleet.panels
        .filter(
          (p) =>
            (region === "all" || p.region === region) &&
            (substation === "all" || p.substation === substation),
        )
        .map((p) => p.transformer),
    ),
  ];
  const filtered = useMemo(
    () =>
      fleet.panels
        .filter(
          (p) =>
            (status === "all" ||
              (status === "offline"
                ? !p.communication_ok
                : p.state === status)) &&
            (region === "all" || p.region === region) &&
            (substation === "all" || p.substation === substation) &&
            (transformer === "all" || p.transformer === transformer) &&
            `${p.name} ${p.id} ${p.device_id} ${p.substation}`
              .toLocaleLowerCase("tr-TR")
              .includes(query.toLocaleLowerCase("tr-TR")),
        )
        .sort((a, b) =>
          sort === "risk"
            ? b.risk_score - a.risk_score
            : sort === "health"
              ? a.health_score - b.health_score
              : a.name.localeCompare(b.name),
        ),
    [fleet.panels, status, region, substation, transformer, query, sort],
  );
  const risky = [...fleet.panels].sort(
    (a, b) => b.risk_score - a.risk_score,
  )[0];
  return (
    <>
      <div className="summary-grid">
        <Metric
          label="Toplam pano"
          value={s.total}
          icon={PanelTop}
          detail={`${regions.length} sanal bölge · ${s.total} modül`}
          color="cyan"
        />
        <Metric
          label="Normal çalışma"
          value={s.normal}
          icon={ShieldCheck}
          detail="Risk skoru 0–19"
          color="green"
        />
        <Metric
          label="İnceleme bekleyen"
          value={s.attention + s.warning}
          icon={Activity}
          detail={`${s.attention} dikkat · ${s.warning} uyarı`}
          color="amber"
        />
        <Metric
          label="Kritik durum"
          value={s.critical}
          icon={TriangleAlert}
          detail="Risk skoru 80–100"
          color="red"
        />
        <Metric
          label="Açık alarm"
          value={s.open_alarms}
          icon={Bell}
          detail={`${s.offline} iletişim problemi`}
          color="violet"
        />
      </div>
      {!inventory && (
        <div className="insights-row">
          <section className="card fleet-health">
            <div className="card-heading">
              <h3>Filo sağlık görünümü</h3>
              <span className="small-tag">ANLIK DAĞILIM</span>
            </div>
            <div className="health-overview">
              <div>
                <strong>
                  {number(s.fleet_health)}
                  <small>/ 100</small>
                </strong>
                <span>Ortalama sağlık skoru</span>
              </div>
              <div className="health-bars">
                <div className="segmented-bar">
                  {(
                    ["NORMAL", "ATTENTION", "WARNING", "CRITICAL"] as Severity[]
                  ).map((state) => {
                    const count = s[state.toLowerCase() as "normal"];
                    return count > 0 ? (
                      <span
                        key={state}
                        style={{ flex: count, background: statusColors[state] }}
                        title={`${statusNames[state]}: ${count}`}
                      />
                    ) : null;
                  })}
                </div>
                <div className="distribution-legend">
                  {(
                    ["NORMAL", "ATTENTION", "WARNING", "CRITICAL"] as Severity[]
                  ).map((state) => (
                    <button key={state} onClick={() => setStatus(state)}>
                      <i style={{ background: statusColors[state] }} />
                      {statusNames[state]}
                      <b>{s[state.toLowerCase() as "normal"]}</b>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>
          <section className="card priority-card">
            <div className="card-heading">
              <h3>
                <Activity size={15} /> Öncelikli izleme
              </h3>
              {risky && <Badge state={risky.state} />}
            </div>
            {risky ? (
              <>
                <div className="priority-main">
                  <div>
                    <strong>{risky.name}</strong>
                    <span>
                      {risky.substation} <i /> {risky.id}
                    </span>
                  </div>
                  <div
                    className="priority-score"
                    style={{ color: statusColors[risky.state] }}
                  >
                    {number(risky.risk_score)}
                    <small>risk</small>
                  </div>
                </div>
                <div className="priority-bottom">
                  <p>
                    {risky.explanation?.possible_cause ||
                      "Risk açıklaması bekleniyor."}
                  </p>
                  <button
                    aria-label={`${risky.name} detayını aç`}
                    onClick={() => onPanel(risky.id)}
                  >
                    <ArrowUpRight size={19} />
                  </button>
                </div>
              </>
            ) : (
              <p>Telemetri bekleniyor.</p>
            )}
          </section>
        </div>
      )}
      <div className={`fleet-layout ${inventory ? "inventory-layout" : ""}`}>
        <section className="card fleet-table">
          <div className="card-heading">
            <div className="title-with-count">
              <h3>Pano izleme</h3>
              <span>{fleet.panels.length}</span>
            </div>
            <span className="subtle-label">
              <span className="live-dot" /> SENTETİK TELEMETRİ
            </span>
          </div>
          <div className="fleet-toolbar">
            <label className="search-input">
              <Search size={16} />
              <input
                aria-label="Pano ara"
                placeholder="Pano, istasyon veya modül ara…"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setLimit(12);
                }}
              />
              {query && (
                <button
                  className="icon-button"
                  aria-label="Aramayı temizle"
                  onClick={() => setQuery("")}
                >
                  <X size={13} />
                </button>
              )}
            </label>
            <select
              aria-label="Risk sıralaması"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
              <option value="risk">Risk: yüksekten düşüğe</option>
              <option value="health">Sağlık: düşükten yükseğe</option>
              <option value="name">Pano adına göre</option>
            </select>
          </div>
          <div className="hierarchy-filters">
            <FolderTree size={14} />
            <select
              aria-label="Bölge filtresi"
              value={region}
              onChange={(e) => {
                setRegion(e.target.value);
                setSubstation("all");
                setTransformer("all");
              }}
            >
              <option value="all">Tüm bölgeler</option>
              {regions.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
            <ChevronRight size={12} />
            <select
              aria-label="İstasyon filtresi"
              value={substation}
              onChange={(e) => {
                setSubstation(e.target.value);
                setTransformer("all");
              }}
            >
              <option value="all">Tüm istasyonlar</option>
              {substations.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
            <ChevronRight size={12} />
            <select
              aria-label="Trafo filtresi"
              value={transformer}
              onChange={(e) => setTransformer(e.target.value)}
            >
              <option value="all">Tüm trafolar</option>
              {transformers.map((r) => (
                <option key={r}>{r}</option>
              ))}
            </select>
          </div>
          <div className="filter-tabs">
            {[
              { id: "all", name: "Tüm panolar", count: s.total },
              { id: "NORMAL", name: "Normal", count: s.normal },
              { id: "ATTENTION", name: "Dikkat", count: s.attention },
              { id: "WARNING", name: "Uyarı", count: s.warning },
              { id: "CRITICAL", name: "Kritik", count: s.critical },
              { id: "offline", name: "Çevrimdışı", count: s.offline },
            ].map((t) => (
              <button
                key={t.id}
                className={status === t.id ? "active" : ""}
                onClick={() => {
                  setStatus(t.id);
                  setLimit(12);
                }}
              >
                {t.name}
                <span>{t.count}</span>
              </button>
            ))}
          </div>
          {filtered.length ? (
            <div className="table-scroll">
              <table className="panel-table">
                <thead>
                  <tr>
                    <th>PANO / KONUM</th>
                    <th>DURUM</th>
                    <th>
                      RİSK <ArrowDown size={11} />
                    </th>
                    <th>SAĞLIK</th>
                    <th>SICAKLIK</th>
                    <th>İLETİŞİM</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {filtered.slice(0, limit).map((p) => (
                    <tr key={p.id} className="panel-row">
                      <td>
                        <button
                          className="panel-name"
                          onClick={() => onPanel(p.id)}
                        >
                          <span
                            className={`panel-symbol ${p.state.toLowerCase()}`}
                          >
                            <PanelTop size={18} />
                          </span>
                          <span>
                            <strong>{p.name}</strong>
                            <small>
                              {p.id} <i /> {p.substation}
                            </small>
                          </span>
                        </button>
                      </td>
                      <td>
                        <Badge state={p.state} />
                      </td>
                      <td>
                        <div className="risk-cell">
                          <strong style={{ color: statusColors[p.state] }}>
                            {number(p.risk_score)}
                          </strong>
                          <span>
                            <i
                              style={{
                                width: `${Math.min(100, Math.max(0, p.risk_score))}%`,
                                background: statusColors[p.state],
                              }}
                            />
                          </span>
                        </div>
                      </td>
                      <td>
                        <span className="numeric">
                          {number(p.health_score)}
                          <small> /100</small>
                        </span>
                      </td>
                      <td className="numeric">
                        {number(measuredValue(p, "temperature_c"), 1)}
                        <small> °C</small>
                      </td>
                      <td>
                        <span
                          className={`communication ${p.communication_ok ? "" : "offline"}`}
                        >
                          {p.communication_ok ? (
                            <Wifi size={13} />
                          ) : (
                            <WifiOff size={13} />
                          )}{" "}
                          {p.communication_ok ? "Bağlı" : "Kesinti"}
                        </span>
                        <small>{time(p.last_seen)}</small>
                      </td>
                      <td>
                        <button
                          className="icon-button"
                          aria-label={`${p.id} pano detayını aç`}
                          onClick={() => onPanel(p.id)}
                        >
                          <ChevronRight size={17} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty
              title="Eşleşen pano bulunamadı"
              detail="Arama veya filtre koşullarını değiştirin."
              icon={Search}
            />
          )}
          <div className="table-footer">
            <span>
              {filtered.length ? `1–${Math.min(limit, filtered.length)}` : "0"}{" "}
              / {filtered.length} pano <i /> Simüle filo
            </span>
            {filtered.length > limit ? (
              <button
                className="text-link"
                onClick={() => setLimit((l) => l + 20)}
              >
                Daha fazla göster <ChevronDown size={13} />
              </button>
            ) : (
              <span>Risk önceliğine göre izleyin</span>
            )}
          </div>
        </section>
        {!inventory && (
          <aside className="card recent-events">
            <div className="card-heading">
              <h3>Son olaylar</h3>
              <span className="event-count">{events.length}</span>
            </div>
            <ResourceError error={eventError} />
            {events.length ? (
              <div className="timeline">
                {events.slice(0, 5).map((e, i) => (
                  <button
                    key={e.id}
                    className="timeline-item"
                    onClick={() => onPanel(e.panel_id)}
                  >
                    <span
                      className={`timeline-marker ${/critical|arc/i.test(e.type + e.message) ? "critical" : i === 0 ? "highlight" : ""}`}
                    >
                      <Activity size={12} />
                    </span>
                    <span>
                      <small>{time(e.timestamp)}</small>
                      <strong>{e.message}</strong>
                      <em>
                        {e.panel_id} <ArrowUpRight size={11} />
                      </em>
                    </span>
                  </button>
                ))}
              </div>
            ) : (
              <Empty
                title="Henüz olay yok"
                detail="Durum geçişleri burada görünecek."
                icon={Activity}
              />
            )}
            <button className="view-all" onClick={onEvents}>
              Tüm olayları görüntüle <ArrowRight size={14} />
            </button>
            <div className="monitoring-note">
              <ShieldCheck size={19} />
              <strong>Her kararın bir açıklaması var.</strong>
              <p>
                Risk katkıları ve önerilen inceleme adımları pano detayında.
              </p>
            </div>
          </aside>
        )}
      </div>
    </>
  );
}
function Metric({
  label,
  value,
  icon: Icon,
  detail,
  color,
}: {
  label: string;
  value: number;
  icon: LucideIcon;
  detail: string;
  color: string;
}) {
  return (
    <div className={`metric-card ${color}`}>
      <div>
        <span>{label}</span>
        <Icon size={17} />
      </div>
      <strong>{number(value)}</strong>
      <p>
        <i />
        {detail}
      </p>
    </div>
  );
}

function PanelDetail({
  panel: p,
  canOperate,
  acknowledge,
  onDemo,
}: {
  panel: Panel;
  canOperate: boolean;
  acknowledge: (id: string) => Promise<void>;
  onDemo: () => void;
}) {
  const [tab, setTab] = useState("monitoring");
  const m = p.measurements;
  return (
    <>
      <SectionHeading
        eyebrow={`${p.region} / ${p.substation} / ${p.transformer}`}
        title={p.name}
        description={`${p.id} · ${p.device_id} · Son örnek ${time(p.last_seen)}`}
      >
        <div className="heading-actions">
          <Badge state={p.state} />
          <button className="primary" onClick={onDemo} disabled={!canOperate}>
            <Play size={14} /> Senaryo başlat
          </button>
        </div>
      </SectionHeading>
      <div className="context-strip">
        <span>
          <FlaskConical size={14} /> SENTETİK DEMO
        </span>
        <p>
          {p.source === "organizer_synthetic_replay"
            ? "L1: organizatör sentetik Excel tekrarı · Diğer kanallar: üretilmiş sentetik"
            : "Tüm gözlemler üretilmiş sentetik veri"}{" "}
          ·{" "}
          {scenarioNames[p.telemetry_scenario || p.scenario] ||
            p.telemetry_scenario ||
            p.scenario}
          {p.telemetry_scenario && p.telemetry_scenario !== p.scenario
            ? ` · Seçilen ${scenarioNames[p.scenario] || p.scenario} için yeni örnek bekleniyor`
            : ""}
        </p>
      </div>
      <div className="panel-summary">
        <div className="card score-card">
          <span>RİSK SKORU</span>
          <strong style={{ color: statusColors[p.state] }}>
            {number(p.risk_score)}
            <small>/100</small>
          </strong>
          <div className="score-track">
            <i
              style={{
                width: `${p.risk_score}%`,
                background: statusColors[p.state],
              }}
            />
          </div>
          <p>{statusNames[p.state]} · Açıklanabilir kural katkıları</p>
        </div>
        <div className="card score-card">
          <span>EKİPMAN SAĞLIĞI</span>
          <strong className="cyan-text">
            {number(p.health_score)}
            <small>/100</small>
          </strong>
          <div className="score-track">
            <i style={{ width: `${p.health_score}%`, background: "#43d5b4" }} />
          </div>
          <p>Risk ve veri kalitesiyle hesaplanan sağlık göstergesi</p>
        </div>
        <div className="card connectivity-card">
          <span>HABERLEŞME VE ARC GUARD</span>
          <div>
            <span>
              {p.communication_ok ? <Wifi size={16} /> : <WifiOff size={16} />}{" "}
              Edge Gateway
            </span>
            <b className={p.communication_ok ? "good-text" : "bad-text"}>
              {p.communication_ok ? "Bağlı" : "Kesinti"}
            </b>
          </div>
          <div>
            <span>
              <Shield size={16} /> TVOC-2 + COM
            </span>
            <b className={p.arc?.communication_ok ? "good-text" : "bad-text"}>
              {p.arc?.communication_ok ? "İletişim var" : "İletişim yok"}
            </b>
          </div>
          <p>
            {!p.arc?.communication_ok
              ? "Ark durumu bilinmiyor · iletişim yok"
              : p.arc?.event
                ? "Sentetik ark olayı kayıtlı"
                : "Aktif ark olayı bildirilmedi"}
          </p>
        </div>
      </div>
      <div className="detail-tabs">
        {[
          { id: "monitoring", name: "Pano ve izleme" },
          { id: "trends", name: "Ölçümler ve trendler" },
          { id: "alarms", name: `Alarmlar (${p.alarms?.length || 0})` },
          { id: "events", name: "Olay geçmişi" },
        ].map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? "active" : ""}
            onClick={() => setTab(t.id)}
          >
            {t.name}
          </button>
        ))}
      </div>
      {p.explanation?.data_quality?.length > 0 && (
        <div className="quality-alert">
          <TriangleAlert size={18} />
          <div>
            <strong>Veri kalitesi / kullanılabilirlik uyarısı</strong>
            <p>{p.explanation.data_quality.join(" · ")}</p>
          </div>
        </div>
      )}
      {tab === "monitoring" && (
        <div className="panel-detail-grid">
          <Schematic panel={p} />
          <div className="panel-analysis">
            <section className="card explanation-card">
              <div className="card-heading">
                <h3>
                  <Activity size={17} /> Riskin arkasındaki sinyaller
                </h3>
                <span className="small-tag">AÇIKLANABİLİR</span>
              </div>
              <div className="explanation-content">
                <span className="field-label">GÖZLENEN BELİRTİLER</span>
                {p.explanation.observed.length ? (
                  <ul>
                    {p.explanation.observed.map((o, i) => (
                      <li key={i}>
                        <span />
                        {o}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>Belirgin risk katkısı saptanmadı.</p>
                )}
                <div className="contributions">
                  {p.explanation.contributions.map((c, i) => (
                    <div key={i}>
                      <span title={c.detail}>
                        {c.rule}
                        <small>{c.detail}</small>
                      </span>
                      <strong>+{number(c.points)}</strong>
                    </div>
                  ))}
                </div>
                <span className="field-label">OLASI NEDEN</span>
                <p>{p.explanation.possible_cause}</p>
                <div className="recommendation">
                  <span>
                    <ShieldCheck size={16} /> Önerilen operatör aksiyonu
                  </span>
                  <p>{p.explanation.recommended_action}</p>
                </div>
                <div className="assumption-note">
                  Eşikler mühendislik demo varsayımlarıdır; koruma ayarı veya
                  doğruluk iddiası değildir.
                </div>
              </div>
            </section>
            <section
              className={`card arc-card ${p.arc?.event ? "arc-active" : ""}`}
            >
              <div className="card-heading">
                <h3>
                  <Shield size={16} /> ABB Arc Guard
                </h3>
                <span className={p.arc?.event ? "bad-text" : "muted"}>
                  {!p.arc?.communication_ok
                    ? "BİLİNMİYOR · İLETİŞİM YOK"
                    : p.arc?.event
                      ? "SENTETİK ARC EVENT"
                      : "OLAY YOK"}
                </span>
              </div>
              <dl>
                <div>
                  <dt>Dedektör</dt>
                  <dd>{p.arc?.detectors?.join(", ") || "—"}</dd>
                </div>
                <div>
                  <dt>Trip rölesi kaydı</dt>
                  <dd>{p.arc?.trip_relays?.join(", ") || "—"}</dd>
                </div>
                <div>
                  <dt>Olay zamanı</dt>
                  <dd>{dateTime(p.arc?.timestamp)}</dd>
                </div>
                <div>
                  <dt>Sistem state / aktif hata</dt>
                  <dd>
                    {p.arc?.communication_ok
                      ? (p.arc.system_state ?? "—")
                      : "Bilinmiyor"}{" "}
                    /{" "}
                    {p.arc?.communication_ok
                      ? p.arc.active_errors?.join(", ") || "Yok"
                      : "Bilinmiyor"}
                  </dd>
                </div>
              </dl>
              <p>Yalnızca olay kaydı okunur. Koruma ABB cihazının görevidir.</p>
            </section>
          </div>
        </div>
      )}
      {tab === "trends" && (
        <>
          <div className="measurement-grid">
            {[
              { key: "current_l1", name: "L1 akımı", unit: "A" },
              { key: "current_l2", name: "L2 akımı", unit: "A" },
              { key: "current_l3", name: "L3 akımı", unit: "A" },
              { key: "current_neutral", name: "Nötr akımı", unit: "A" },
              { key: "voltage_l1", name: "L1 gerilimi", unit: "V" },
              { key: "voltage_l2", name: "L2 gerilimi", unit: "V" },
              { key: "voltage_l3", name: "L3 gerilimi", unit: "V" },
              { key: "frequency_hz", name: "Frekans", unit: "Hz" },
              { key: "active_power_kw", name: "Aktif güç", unit: "kW" },
              { key: "reactive_power_kvar", name: "Reaktif güç", unit: "kVAr" },
              { key: "apparent_power_kva", name: "Görünür güç", unit: "kVA" },
              { key: "power_factor", name: "Güç faktörü", unit: "cos φ" },
              { key: "thd_current", name: "Akım THD", unit: "%" },
              { key: "thd_voltage", name: "Gerilim THD", unit: "%" },
              { key: "temperature_c", name: "Bağlantı sıcaklığı", unit: "°C" },
              {
                key: "ambient_temperature_c",
                name: "Ortam sıcaklığı",
                unit: "°C",
              },
              { key: "humidity_pct", name: "Bağıl nem", unit: "%" },
              { key: "pd_pulse_count", name: "PD darbe sayısı", unit: "darbe" },
              { key: "pd_peak", name: "PD tepe", unit: "a.u." },
              { key: "pd_rms", name: "PD RMS", unit: "a.u." },
              { key: "pd_activity_rate", name: "PD aktivite", unit: "darbe/s" },
              { key: "pd_baseline_ratio", name: "PD baz oranı", unit: "×" },
              { key: "battery_pct", name: "Sensör pili", unit: "%" },
            ].map((c) => (
              <div className="measurement" key={c.key}>
                <span>{c.name}</span>
                <strong>
                  {number(
                    measuredValue(p, c.key),
                    c.key === "power_factor" ? 3 : 1,
                  )}
                  <small>{c.unit}</small>
                </strong>
                <em
                  className={
                    p.quality?.[c.key] && p.quality[c.key] !== "good"
                      ? "bad-text"
                      : ""
                  }
                >
                  {m[c.key] === null || m[c.key] === undefined
                    ? "Eksik veri · Sentetik"
                    : qualityLabel(p, c.key) === "Sentetik"
                      ? "Sentetik"
                      : `${qualityLabel(p, c.key)} · Sentetik`}
                  {p.provenance?.[c.key] === "organizer_synthetic_replay" ||
                  (c.key === "current_l1" &&
                    p.source === "organizer_synthetic_replay")
                    ? " · Excel tekrarı"
                    : ""}
                </em>
              </div>
            ))}
          </div>
          <div className="trends-grid">
            <TrendChart
              history={p.history || []}
              title="Faz akımları"
              unit="A"
              channels={[
                { key: "current_l1", label: "L1", color: "#51e2c4" },
                { key: "current_l2", label: "L2", color: "#76aefb" },
                { key: "current_l3", label: "L3", color: "#c695ed" },
              ]}
            />
            <TrendChart
              history={p.history || []}
              title="Termal davranış"
              unit="°C"
              channels={[
                { key: "temperature_c", label: "Bağlantı", color: "#f5b16c" },
                {
                  key: "ambient_temperature_c",
                  label: "Ortam",
                  color: "#7393b6",
                },
              ]}
            />
            <TrendChart
              history={p.history || []}
              title="PD baz çizgisi oranı"
              unit="×"
              channels={[
                {
                  key: "pd_baseline_ratio",
                  label: "PD / baz",
                  color: "#c49df0",
                },
              ]}
            />
            <TrendChart
              history={p.history || []}
              title="Risk skoru"
              unit="/100"
              channels={[
                { key: "risk_score", label: "Risk", color: "#55daca" },
              ]}
            />
          </div>
        </>
      )}
      {tab === "alarms" && (
        <AlarmList
          alarms={p.alarms || []}
          canOperate={canOperate}
          acknowledge={acknowledge}
        />
      )}
      {tab === "events" && <EventList events={p.events || []} />}
    </>
  );
}

function AlarmList({
  alarms,
  canOperate,
  acknowledge,
  onPanel,
}: {
  alarms: Alarm[];
  canOperate: boolean;
  acknowledge: (id: string) => Promise<void>;
  onPanel?: (id: string) => void;
}) {
  const [filter, setFilter] = useState("open"),
    [pending, setPending] = useState<string | null>(null);
  const filtered = alarms.filter((a) =>
    filter === "all" || filter === "open"
      ? filter === "all" || a.status !== "resolved"
      : a.status === filter,
  );
  return (
    <div className="card table-card">
      <div className="card-heading">
        <h3>
          Alarm kayıtları <span className="muted">· {alarms.length}</span>
        </h3>
        <select
          aria-label="Alarm durum filtresi"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
        >
          <option value="open">Açık alarmlar</option>
          <option value="active">Aktif</option>
          <option value="acknowledged">Onaylanan</option>
          <option value="resolved">Çözülen</option>
          <option value="all">Tüm kayıtlar</option>
        </select>
      </div>
      {filtered.length ? (
        <div className="alarm-items">
          {filtered.map((a) => (
            <article className="alarm-item" key={a.id}>
              <span className={`alarm-symbol ${a.severity.toLowerCase()}`}>
                <TriangleAlert size={19} />
              </span>
              <div className="alarm-body">
                <div>
                  <strong>{a.title}</strong>
                  <Badge state={a.severity} />
                </div>
                <p>{a.message}</p>
                <small>
                  {onPanel ? (
                    <button
                      className="text-link"
                      onClick={() => onPanel(a.panel_id)}
                    >
                      {a.panel_name || a.panel_id}
                    </button>
                  ) : (
                    a.panel_id
                  )}
                  <i /> {dateTime(a.created_at)} <i />{" "}
                  {a.status === "active"
                    ? "Aktif"
                    : a.status === "acknowledged"
                      ? "Operatör onayı alındı"
                      : "Çözüldü"}
                </small>
              </div>
              {a.status === "active" && (
                <button
                  className="secondary acknowledge-button"
                  disabled={!canOperate || pending === a.id}
                  onClick={async () => {
                    setPending(a.id);
                    await acknowledge(a.id);
                    setPending(null);
                  }}
                >
                  <Check size={15} />
                  {pending === a.id ? "Kaydediliyor…" : "Alarmı onayla"}
                </button>
              )}
            </article>
          ))}
        </div>
      ) : (
        <Empty
          title="Bu görünümde alarm yok"
          detail="Durum filtresini değiştirebilir veya sentetik bir senaryo başlatabilirsiniz."
          icon={ShieldCheck}
        />
      )}
      <div className="table-footer">
        <span>Onay, alarmın görüldüğünü kaydeder. Cihaza komut göndermez.</span>
        {!canOperate && <span>Onay için operatör rolü gerekir.</span>}
      </div>
    </div>
  );
}
function EventList({
  events,
  onPanel,
}: {
  events: Event[];
  onPanel?: (id: string) => void;
}) {
  return (
    <div className="card table-card">
      <div className="card-heading">
        <h3>Olay akışı</h3>
        <span>{events.length} kayıt · UTC</span>
      </div>
      {events.length ? (
        <div className="event-list">
          {events.map((e) => (
            <div className="event-row" key={e.id}>
              <span className="event-row-icon">
                <Activity size={17} />
              </span>
              <div>
                <span className="small-tag">{e.type}</span>
                <p>{e.message}</p>
                <small>
                  {onPanel ? (
                    <button
                      className="text-link"
                      onClick={() => onPanel(e.panel_id)}
                    >
                      {e.panel_id}
                    </button>
                  ) : (
                    e.panel_id
                  )}
                </small>
              </div>
              <time>{dateTime(e.timestamp)}</time>
            </div>
          ))}
        </div>
      ) : (
        <Empty
          title="Olay geçmişi boş"
          detail="İlk telemetri ve durum geçişi sonrasında olaylar listelenecek."
          icon={Clock}
        />
      )}
    </div>
  );
}

function DemoDialog({
  token,
  panels,
  scenarios,
  initialPanel,
  onClose,
  onSuccess,
}: {
  token: string;
  panels: Panel[];
  scenarios: Scenario[];
  initialPanel?: string;
  onClose: () => void;
  onSuccess: (s: string) => void;
}) {
  const [panelId, setPanelId] = useState(initialPanel || panels[0]?.id || ""),
    [scenario, setScenario] = useState("combined_thermal_pd"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const selected = scenarios.find((s) => s.id === scenario);
  useEffect(() => {
    function key(e: KeyboardEvent) {
      if (e.key === "Escape" && !busy) onClose();
    }
    document.addEventListener("keydown", key);
    const before = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", key);
      document.body.style.overflow = before;
    };
  }, [onClose, busy]);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/demo/scenario", token, {
        method: "POST",
        body: JSON.stringify({ scenario, panel_id: panelId }),
      });
      onSuccess(
        `${scenarioNames[scenario] || scenario} senaryosu ${panelId} için seçildi. Simülatörün sonraki örneği bekleniyor.`,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Senaryo başlatılamadı");
      setBusy(false);
    }
  }
  return (
    <div
      className="modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget && !busy) onClose();
      }}
    >
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="demo-title"
        onKeyDown={(e) => {
          if (e.key === "Tab") {
            const items = Array.from(
              e.currentTarget.querySelectorAll<HTMLElement>(
                'button:not(:disabled),select,input,[tabindex="0"]',
              ),
            );
            const first = items[0],
              last = items[items.length - 1];
            if (e.shiftKey && document.activeElement === first) {
              e.preventDefault();
              last?.focus();
            } else if (!e.shiftKey && document.activeElement === last) {
              e.preventDefault();
              first?.focus();
            }
          }
        }}
      >
        <div className="modal-heading">
          <span className="login-icon">
            <FlaskConical size={21} />
          </span>
          <button
            className="icon-button"
            onClick={onClose}
            disabled={busy}
            aria-label="Senaryo penceresini kapat"
          >
            <X size={20} />
          </button>
        </div>
        <h2 id="demo-title">Bir sinyalle başlar.</h2>
        <p>
          Senaryoyu seçin; telemetri, risk, alarm ve Modbus kayıtlarının
          değişimini izleyin.
        </p>
        <form onSubmit={submit}>
          <label htmlFor="demo-panel">Hedef sanal pano</label>
          <select
            id="demo-panel"
            autoFocus
            value={panelId}
            onChange={(e) => setPanelId(e.target.value)}
            required
          >
            {!panels.length && <option value="">Pano verisi bekleniyor</option>}
            {panels.map((p) => (
              <option key={p.id} value={p.id}>
                {p.id} · {p.name}
              </option>
            ))}
          </select>
          <label htmlFor="demo-scenario">Demo senaryosu</label>
          <select
            id="demo-scenario"
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            required
          >
            {scenarios.length ? (
              scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {scenarioNames[s.id] || s.name}
                </option>
              ))
            ) : (
              <option value="">Senaryo listesi alınamadı</option>
            )}
          </select>
          {selected && (
            <div className="scenario-info">
              <div>
                <span>{selected.duration_steps} adım</span>
                <Badge state={selected.expected_state} />
              </div>
              <p>{selected.description}</p>
            </div>
          )}
          <div className="demo-disclosure">
            <FlaskConical size={16} />
            <p>
              Yalnızca sentetik simülatör seçimi değişir. Hızlandırılmış demo
              saati kullanılabilir; gerçek cihaza yazma yapılmaz.
            </p>
          </div>
          {error && (
            <div className="inline-error" role="alert">
              {error}
            </div>
          )}
          <button
            className="primary login-submit"
            disabled={busy || !panelId || !scenarios.length}
          >
            <Play size={15} />
            {busy ? "Senaryo seçiliyor…" : "Senaryoyu çalıştır"}
          </button>
        </form>
      </section>
    </div>
  );
}

function ScadaView({ token, panels }: { token: string; panels: Panel[] }) {
  const [panelId, setPanelId] = useState(panels[0]?.id || ""),
    [data, setData] = useState<Registers | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [refresh, setRefresh] = useState(0);
  useEffect(() => {
    if (!panelId && panels.length) setPanelId(panels[0].id);
  }, [panels, panelId]);
  useEffect(() => {
    setData(null);
    if (!panelId) return;
    const controller = new AbortController();
    setBusy(true);
    api<Registers>(
      `/scada/registers?panel_id=${encodeURIComponent(panelId)}`,
      token,
      { signal: controller.signal },
    )
      .then((r) => {
        setData(r);
        setError("");
      })
      .catch((e) => {
        if (!controller.signal.aborted)
          setError(e instanceof Error ? e.message : "Modbus okuması başarısız");
      })
      .finally(() => {
        if (!controller.signal.aborted) setBusy(false);
      });
    return () => controller.abort();
  }, [token, panelId, refresh]);
  return (
    <>
      <SectionHeading
        eyebrow="ENTEGRASYON / MODBUS MASTER"
        title="SCADA kayıtlarını okuyun."
        description="Yerel GridSentinel köprüsüne gerçek Modbus TCP master isteği."
      >
        <button
          className="primary"
          onClick={() => setRefresh((r) => r + 1)}
          disabled={busy || !panelId}
        >
          <RefreshCw size={15} className={busy ? "spin" : ""} />
          {busy ? "TCP okunuyor…" : "Register oku"}
        </button>
      </SectionHeading>
      <div className="context-strip">
        <span>
          <Network size={14} /> YEREL DEMO KÖPRÜSÜ
        </span>
        <p>
          GridSentinel özel register haritası · Gerçek ADM/GDZ SCADA bağlantısı
          yoktur.
        </p>
      </div>
      <div className="scada-flow card">
        <div>
          <Activity size={23} />
          <strong>Risk motoru</strong>
          <small>Sentetik pano sonuçları</small>
        </div>
        <ArrowRight size={20} />
        <div>
          <Server size={23} />
          <strong>Modbus TCP bridge</strong>
          <small>Salt okunur FC03 / FC04</small>
        </div>
        <ArrowRight size={20} />
        <div>
          <Network size={23} />
          <strong>Master okuması</strong>
          <small>API üzerinden gerçek TCP</small>
        </div>
      </div>
      <div className="card register-card">
        <div className="card-heading">
          <div>
            <h3>Holding registers</h3>
            <p>PDU sıfır tabanlı adres · uint16</p>
          </div>
          <select
            aria-label="SCADA hedef panosu"
            value={panelId}
            onChange={(e) => setPanelId(e.target.value)}
          >
            {panels.length ? (
              panels.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.id} · {p.name}
                </option>
              ))
            ) : (
              <option value="">Pano yok</option>
            )}
          </select>
        </div>
        <div className="register-status">
          <span className={data?.connected ? "good-text" : "bad-text"}>
            {data?.connected ? <Wifi size={15} /> : <WifiOff size={15} />}{" "}
            {busy
              ? "Okunuyor"
              : data?.connected
                ? "TCP okuması başarılı"
                : "Bağlantı doğrulanmadı"}
          </span>
          <span>
            Host <b>{data?.host || "—"}</b>
          </span>
          <span>
            Port <b>{data?.port ?? "—"}</b>
          </span>
          <span>
            Unit ID <b>{data?.unit_id ?? "—"}</b>
          </span>
          <span>{data ? time(data.timestamp) : "—"}</span>
        </div>
        <ResourceError error={error || data?.error} />
        {data?.connected && data.registers.length ? (
          <div className="table-scroll">
            <table className="register-table">
              <thead>
                <tr>
                  <th>PDU ADRESİ</th>
                  <th>REGISTER</th>
                  <th>DEĞER</th>
                  <th>BİRİM</th>
                  <th>ERİŞİM</th>
                </tr>
              </thead>
              <tbody>
                {data.registers.map((r) => (
                  <tr key={r.address}>
                    <td className="code-cell">
                      {String(r.address).padStart(4, "0")}
                      <small>
                        0x
                        {r.address.toString(16).padStart(4, "0").toUpperCase()}
                      </small>
                    </td>
                    <td className="code-cell">{r.name}</td>
                    <td className="register-value">{number(r.value)}</td>
                    <td>{r.unit || "—"}</td>
                    <td>
                      <span className="small-tag">
                        <LockKeyhole size={10} /> READ ONLY
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty
            title={
              busy
                ? "Modbus yanıtı bekleniyor"
                : "Register değeri gösterilemiyor"
            }
            detail="Bağlantı başarılı olmadan veritabanındaki değerler TCP okuması gibi sunulmaz."
            icon={Network}
          />
        )}
        <div className="table-footer">
          <span>
            Harita v1 · Adres 10–11: UNIX zaman damgası uint32 high/low
          </span>
          <span>Tek bridge en çok 247 unit ID</span>
        </div>
      </div>
    </>
  );
}
function SourcesView() {
  return (
    <>
      <SectionHeading
        eyebrow="MİMARİ / İZLENEBİLİRLİK"
        title="Verinin kaynağı açık."
        description="Kaynağa dayalı cihaz eşlemeleri, sentetik gözlemler ve saha tasarım önerileri."
      />
      <div className="source-cards">
        <section className="card">
          <span className="source-icon">
            <Database size={23} />
          </span>
          <h3>Organizatör verisi</h3>
          <strong>152 sentetik L1 örneği</strong>
          <p>
            İstenen Veriler.xlsx, Akım Sensörü A7:F158. 15 dakika göreli aralık,
            90–540 A, medyan 297 A. Tekrar oynatma L1 kaynağını korur.
          </p>
          <span className="small-tag">ORGANIZER_SYNTHETIC_REPLAY</span>
        </section>
        <section className="card">
          <span className="source-icon">
            <FlaskConical size={23} />
          </span>
          <h3>Üretilmiş kanallar</h3>
          <strong>10 açıklanabilir senaryo</strong>
          <p>
            L2/L3, gerilim, termal, nem, PD feature ve ark olayları simülatör
            tarafından üretilir. PD genlikleri a.u.; gerçek pC kalibrasyonu
            yoktur.
          </p>
          <span className="small-tag">GENERATED_SYNTHETIC</span>
        </section>
        <section className="card">
          <span className="source-icon">
            <CircuitBoard size={23} />
          </span>
          <h3>Donanım referansı</h3>
          <strong>Kaynak PDF eşlemeleri</strong>
          <p>
            TEDAŞ çizimi, MPR-53CS ve TVOC-2 COM belgeleri temel alınır. Modbus
            word order ve fiziksel montaj sahada doğrulanmamıştır.
          </p>
          <span className="small-tag">SOURCE-DERIVED</span>
        </section>
      </div>
      <section className="card architecture-card">
        <div className="card-heading">
          <h3>Uçtan uca şirket içi veri akışı</h3>
          <span className="small-tag cyan">PUBLIC CLOUD YOK</span>
        </div>
        <div className="architecture-layer">
          <span className="layer-label">SAHA KONSEPTİ / OT</span>
          <div className="architecture-nodes">
            <div>
              <CircuitBoard />
              <strong>Mevcut cihazlar</strong>
              <small>MPR-53CS · TVOC-2 + COM</small>
            </div>
            <div>
              <Thermometer />
              <strong>Retrofit sensörler</strong>
              <small>Kablosuz termal / nem önerisi</small>
            </div>
            <div>
              <Activity />
              <strong>HFCT + Acquisition</strong>
              <small>Geniş bant ön uç / PD feature</small>
            </div>
            <ArrowRight />
            <div className="accent-node">
              <Box />
              <strong>Edge Gateway</strong>
              <small>İzole RS485 · Ethernet</small>
            </div>
          </div>
        </div>
        <div className="network-boundary">
          <Shield size={15} /> OT / IT sınırı · Segmentasyon ve kontrollü erişim
          · Salt okunur izleme
        </div>
        <div className="architecture-layer">
          <span className="layer-label">YEREL MERKEZİ SUNUCU / IT</span>
          <div className="architecture-nodes">
            <div>
              <Radio />
              <strong>MQTT / Mosquitto</strong>
              <small>Kimlik doğrulanmış telemetri</small>
            </div>
            <ArrowRight />
            <div>
              <Database />
              <strong>FastAPI + PostgreSQL</strong>
              <small>Kalıcı kayıt / tekilleştirme</small>
            </div>
            <ArrowRight />
            <div className="accent-node">
              <Gauge />
              <strong>Risk ve alarm motoru</strong>
              <small>Kural + trend / açıklama</small>
            </div>
            <ArrowRight />
            <div>
              <LayoutDashboard />
              <strong>Operasyon + SCADA</strong>
              <small>Next.js · Modbus TCP · Mock</small>
            </div>
          </div>
        </div>
      </section>
      <section className="card source-reference">
        <div className="card-heading">
          <h3>Teknik referans ve sınırlar</h3>
          <ShieldCheck size={18} />
        </div>
        <dl>
          <div>
            <dt>Pano geometrisi</dt>
            <dd>
              TEDAŞ EK-II/14, basılı s.51: 1600 × 1500 × 450 mm, alt kablo
              boşluğu en az 400 mm. Ek sensör noktaları öneridir.
            </dd>
          </div>
          <div>
            <dt>MPR-53CS</dt>
            <dd>
              Register map 01.12.2019, s.1–2. Elektriksel ölçümler salt okunur;
              belgede belirsiz word order yapılandırılabilir.
            </dd>
          </div>
          <div>
            <dt>TVOC-2 + COM</dt>
            <dd>
              1SFC170017M0201 Rev D, s.20–27 ve 33. Trip, dedektör, diagnostic
              ve state okuması. Koruma fonksiyonu sertifikalı cihazda kalır.
            </dd>
          </div>
          <div>
            <dt>Kurulum yaklaşımı</dt>
            <dd>
              Kablosuz çevre sensörleri için RF doğrulaması; bara/CT/RS485
              bağlantısı ve HFCT montajı için kontrollü müdahale veya planlı
              kesinti değerlendirmesi gerekir.
            </dd>
          </div>
          <div>
            <dt>Risk değerlendirmesi</dt>
            <dd>
              0–19 normal, 20–44 dikkat, 45–79 uyarı, 80–100 kritik. Eşikler
              demo mühendislik varsayımıdır. Sahada doğruluk, RF kapsama ve pil
              ömrü doğrulanmamıştır.
            </dd>
          </div>
        </dl>
      </section>
    </>
  );
}
