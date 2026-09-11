"use client";
import {
  Activity,
  CheckCheck,
  Clock,
  FlaskConical,
  Shield,
  Workflow,
} from "lucide-react";
import { dateTime, number } from "@/lib/api";
import type { Action, EarlyWarning, Panel, Severity } from "@/lib/types";

export const ruleLabels: Record<string, string> = {
  baseline: "Referans çalışma",
  temperature: "Termal yükseliş",
  humidity: "Yüksek nem",
  pd_activity: "PD aktivitesi",
  load: "Yük seviyesi",
  phase_imbalance: "Faz dengesizliği",
  frequency: "Frekans sapması",
  current_thd: "Akım harmonikleri",
  thermal_trend: "Sıcaklık artış eğilimi",
  thermal_load_correlation: "Yük-sıcaklık uyumsuzluğu",
  thermal_pd_correlation: "Termal + PD korelasyonu",
  availability: "Veri kullanılabilirliği",
  arc_event: "ABB ark olayı",
};
const states: Record<Severity, string> = {
  NORMAL: "Normal",
  ATTENTION: "Dikkat",
  WARNING: "Uyarı",
  CRITICAL: "Kritik",
};
export function RunSelector({
  panel,
  scope,
  onScope,
  canOperate,
  busy,
  onQuickRun,
}: {
  panel: Panel;
  scope: "current" | "all";
  onScope: (scope: "current" | "all") => void;
  canOperate: boolean;
  busy: boolean;
  onQuickRun: (scenario: "combined_thermal_pd" | "arc_event") => void;
}) {
  return (
    <section className="run-bar" aria-label="Demo çalışma kapsamı">
      <div className="scope-segments">
        <button
          className={scope === "current" ? "active" : ""}
          aria-pressed={scope === "current"}
          onClick={() => onScope("current")}
        >
          Bu demo çalışması
        </button>
        <button
          className={scope === "all" ? "active" : ""}
          aria-pressed={scope === "all"}
          onClick={() => onScope("all")}
        >
          Tüm geçmiş
        </button>
      </div>
      <div className="run-meta">
        <span>
          <Clock size={13} />
          {dateTime(panel.scenario_started_at)}
        </span>
        <span>
          Çalışma <b>{panel.scenario_revision ?? "—"}</b>
        </span>
        <span>
          Adım <b>{panel.demo_step ?? "—"}</b>
        </span>
        {panel.focused_demo && (
          <span className="focus-cadence">
            <FlaskConical size={13} />
            {number(panel.focus_interval_seconds, 1)} sn / sentetik adım
          </span>
        )}
      </div>
      <div className="quick-demos" aria-label="Odaklı demo başlat">
        <button
          className="secondary"
          disabled={!canOperate || busy}
          onClick={() => onQuickRun("combined_thermal_pd")}
        >
          <FlaskConical size={14} /> Termal + PD demosu
        </button>
        <button
          className="secondary"
          disabled={!canOperate || busy}
          onClick={() => onQuickRun("arc_event")}
        >
          <Activity size={14} /> Ark demosu
        </button>
        <small>
          Sunum hedefi: termal + PD ≈60–75 sn; ark ≈15–20 sn. Ölçülmüş süre veya
          saha garantisi değildir.
        </small>
      </div>
      <p>
        {scope === "current"
          ? "Grafik, alarm ve olaylar yalnız seçili çalışmaya aittir."
          : "Tüm çalışmaların korunmuş kayıtları. Grafik başlangıçta son 120 ölçümü gösterir."}{" "}
        Hızlandırılmış demo adımları gerçek saha erken uyarı süresi değildir.
      </p>
    </section>
  );
}
export function EarlyWarningTimeline({
  data,
  runId,
}: {
  data?: EarlyWarning;
  runId?: string;
}) {
  return (
    <section
      className="card early-warning-card"
      aria-label="Erken uyarı kanıtı"
      data-run-id={runId}
    >
      <div className="card-heading">
        <h3>
          <Activity size={16} /> Erken uyarı zaman çizgisi
        </h3>
        <span className="small-tag">BU DEMO ÇALIŞMASI</span>
      </div>
      {data?.transitions.length ? (
        <>
          <ol className="warning-timeline">
            {data.transitions.map((transition, index) => (
              <li
                key={`${transition.step}-${transition.state}-${index}`}
                className={transition.state.toLowerCase()}
              >
                <span className="transition-dot" />
                <strong>{states[transition.state]}</strong>
                <span>Adım {transition.step}</span>
                <small>
                  Risk {number(transition.risk_score)} ·{" "}
                  {dateTime(transition.timestamp)}
                </small>
              </li>
            ))}
          </ol>
          <div
            className={`lead-time ${data.status === "demonstrated" ? "demonstrated" : ""}`}
          >
            <CheckCheck size={17} />
            <div>
              <strong>
                {data.status === "demonstrated" && data.lead_steps !== null
                  ? `Erken uyarı: kritik seviyeden ${data.lead_steps} sentetik demo adımı önce`
                  : data.message}
              </strong>
              <p>
                Bu fark senaryo adımlarından hesaplanır; sahada dakika/saat
                cinsinden lead-time veya arıza tahmini doğrulanmış değildir.
              </p>
            </div>
          </div>
        </>
      ) : (
        <div className="run-empty">
          <Clock size={19} />
          <span>
            {data?.message || "Yeni çalışmanın ilk durum geçişi bekleniyor."}
          </span>
        </div>
      )}
    </section>
  );
}
const actionStatus: Record<string, string> = {
  simulated: "Simüle edildi",
  recorded: "Kaydedildi",
  active: "Aktif",
  triggered: "Tetiklendi",
  recommended: "Operatör önerisi",
  pending: "Bekleniyor",
  monitoring: "İzleniyor",
  enabled: "Etkin",
  not_applicable: "Kapsam dışı",
  completed: "Tamamlandı",
  available: "Hazır",
  published: "Kayda alındı",
  eligible: "Simülasyon politikası hazır",
  deduplicated: "Önceki kayıt korundu",
  external: "Bağımsız koruma işlevi",
};
export function ActionCard({
  actions,
  pending,
}: {
  actions?: Action[];
  pending: boolean;
}) {
  return (
    <section className="card action-card">
      <div className="card-heading">
        <h3>
          <Workflow size={16} /> Tetiklenen otomatik aksiyonlar
        </h3>
        <span className="small-tag">POLİTİKA</span>
      </div>
      {pending ? (
        <div className="run-empty">
          <Clock size={18} />
          <span>Bu çalışma için ölçüm bekleniyor.</span>
        </div>
      ) : actions?.length ? (
        <div className="action-list">
          {actions.map((action, index) => (
            <article key={`${action.type}-${action.channel}-${index}`}>
              <span
                className={`action-dot ${action.status === "simulated" ? "simulated" : ""}`}
              >
                <CheckCheck size={14} />
              </span>
              <div>
                <div className="action-title">
                  <strong>{action.description}</strong>
                  <span
                    className={
                      action.status === "simulated"
                        ? "simulation-badge"
                        : "small-tag"
                    }
                  >
                    {actionStatus[action.status] || action.status}
                  </span>
                </div>
                <p>
                  {action.automatic
                    ? "Otomatik politika"
                    : "Operatör değerlendirmesi"}
                  {action.channel ? ` · ${action.channel.toUpperCase()}` : ""} ·{" "}
                  {(
                    {
                      ARC_EVENT: "Ark olayı",
                      COMMUNICATION_LOSS: "İletişim kaybı",
                    } as Record<string, string>
                  )[action.trigger] ||
                    states[action.trigger as Severity] ||
                    ruleLabels[action.trigger] ||
                    action.trigger}
                </p>
                {action.safety_boundary && (
                  <small>{action.safety_boundary}</small>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="run-empty">
          <Activity size={18} />
          <span>Bu çalışma için aksiyon kaydı bulunmuyor.</span>
        </div>
      )}
      <div className="source-note">
        <Shield size={13} /> Koruma komutu yok. Trip ve reset, GridSentinel
        tarafından gönderilmez.
      </div>
    </section>
  );
}
