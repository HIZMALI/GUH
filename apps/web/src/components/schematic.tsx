"use client";
import { useState } from "react";
import { CircleDot, Info } from "lucide-react";
import { measuredValue, number, qualityLabel } from "@/lib/api";
import type { Panel } from "@/lib/types";
const points = [
  {
    id: "thermal",
    label: "T1 · Bağlantı sıcaklığı",
    x: 235,
    y: 129,
    short: "T1",
    kind: "Önerilen retrofit sensör",
    text: "Üst giriş / CT bağlantı bölgesinin termal izlenmesi. Fiziksel montaj ve elektriksel açıklıklar mühendislik değerlendirmesi gerektirir.",
    key: "temperature_c",
    unit: "°C",
  },
  {
    id: "arc",
    label: "A1 · Arc Guard izleme",
    x: 375,
    y: 82,
    short: "A1",
    kind: "Mevcut cihazdan okuma konsepti",
    text: "TVOC-2 + COM üzerinden salt okunur olay ve diagnostic bilgisi. Optik dedektör bölgesi şematik öneridir. Koruma fonksiyonu ABB cihazında kalır.",
    key: "",
    unit: "",
  },
  {
    id: "mpr",
    label: "E1 · MPR-53CS",
    x: 430,
    y: 246,
    short: "E1",
    kind: "Mevcut ölçü bölgesi",
    text: "Sağ ölçü ve yardımcı devreler alanı. RS485/Modbus üzerinden faz akımları, gerilim ve elektriksel parametrelerin okunması.",
    key: "current_l1",
    unit: "A · L1",
  },
  {
    id: "humidity",
    label: "H1 · Sıcaklık ve nem",
    x: 92,
    y: 335,
    short: "H1",
    kind: "Önerilen kablosuz sensör",
    text: "Alt kablo bölgesinde ortam izleme önerisi. Metal pano içi RF kapsama ve sensör konumu sahada doğrulanmalıdır.",
    key: "humidity_pct",
    unit: "% RH",
  },
  {
    id: "pd",
    label: "P1 · HFCT / PD",
    x: 275,
    y: 364,
    short: "P1",
    kind: "Önerilen acquisition zinciri",
    text: "Uygun toprak bağlantısında HFCT → geniş bant analog ön uç → acquisition → türetilmiş feature. Demo genliği arbitrary unit; pC ölçümü değildir.",
    key: "pd_baseline_ratio",
    unit: "× baz çizgi",
  },
  {
    id: "edge",
    label: "G1 · Edge Gateway",
    x: 441,
    y: 357,
    short: "G1",
    kind: "Önerilen saha modülü",
    text: "Yardımcı bölgeye yerel ağ geçidi önerisi. İzole RS485, kablosuz sensör alıcısı ve Ethernet; hiçbir cihaza açma/reset komutu gönderilmez.",
    key: "",
    unit: "",
  },
];
export function Schematic({ panel }: { panel: Panel }) {
  const [active, setActive] = useState("thermal");
  const selected = points.find((p) => p.id === active)!;
  return (
    <section className="card schematic-card">
      <div className="card-heading">
        <div>
          <h3>Pano izleme şeması</h3>
          <p>1600 kVA · Dahili tip AG dağıtım panosu</p>
        </div>
        <span className="small-tag">YERLEŞİM ÖNERİSİ</span>
      </div>
      <div className="schematic-surface">
        <svg
          viewBox="0 0 530 450"
          aria-label="TEDAŞ EK-II/14 kaynak çizimine dayalı pano şeması"
          role="img"
        >
          <defs>
            <pattern
              id="panelGrid"
              width="20"
              height="20"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M20 0H0V20"
                fill="none"
                stroke="#1b2b3b"
                strokeWidth=".5"
              />
            </pattern>
          </defs>
          <rect width="530" height="450" fill="url(#panelGrid)" />
          <path d="M52 28H482 M52 24V32 M482 24V32" stroke="#65798c" />
          <text x="268" y="20" textAnchor="middle" fill="#7d93a6" fontSize="10">
            1600 mm (+100 / −0)
          </text>
          <path d="M27 49V403M23 49H31M23 403H31" stroke="#65798c" />
          <text
            transform="translate(18 240) rotate(-90)"
            fill="#7d93a6"
            fontSize="10"
          >
            1500 mm (+100 / −0)
          </text>
          <rect
            x="50"
            y="49"
            width="432"
            height="354"
            rx="3"
            fill="#101c28"
            stroke="#697d8e"
            strokeWidth="2"
          />
          <rect
            x="59"
            y="58"
            width="414"
            height="336"
            fill="none"
            stroke="#334b60"
          />
          <path
            d="M59 163H473M59 180H473M400 180V394M59 307H400"
            stroke="#637789"
            strokeWidth="1.5"
          />
          <path d="M115 58V163M129 58V163" stroke="#334b60" />
          {[203, 238, 273].map((x, i) => (
            <g key={x}>
              <rect
                x={x}
                y="39"
                width="11"
                height="119"
                fill="#9c8057"
                opacity=".6"
              />
              <rect
                x={x - 6}
                y="116"
                width="23"
                height="17"
                rx="2"
                fill="#172b3a"
                stroke="#8298a8"
              />
              <circle cx={x + 5} cy="124" r="3" fill="#aec1cd" />
              <text
                x={x + 5}
                y="76"
                textAnchor="middle"
                fontSize="8"
                fill="#d3c2a8"
              >
                L{i + 1}
              </text>
            </g>
          ))}
          <rect
            x="72"
            y="82"
            width="32"
            height="36"
            fill="#233546"
            stroke="#4f6578"
          />
          <text x="88" y="131" textAnchor="middle" fill="#7c91a3" fontSize="7">
            Sabit
          </text>
          <text x="88" y="141" textAnchor="middle" fill="#7c91a3" fontSize="7">
            komp.
          </text>
          <text x="185" y="96" fill="#7c91a3" fontSize="8">
            GİRİŞ / CT
          </text>
          <rect
            x="399"
            y="122"
            width="59"
            height="26"
            rx="2"
            fill="#233546"
            stroke="#4f6578"
          />
          <text x="428" y="139" textAnchor="middle" fill="#9ab0c2" fontSize="8">
            YARDIMCI
          </text>
          {Array.from({ length: 12 }, (_, i) => (
            <g key={i}>
              <rect
                x={66 + i * 27}
                y="190"
                width="19"
                height="104"
                fill="#1b3041"
                stroke="#5e7485"
              />
              {[198, 230, 262].map((y) => (
                <g key={y}>
                  <rect
                    x={71 + i * 27}
                    y={y}
                    width="9"
                    height="22"
                    rx="1"
                    fill="#536878"
                  />
                  <path d={`M${75 + i * 27} ${y + 4}v14`} stroke="#a3b1ba" />
                </g>
              ))}
              <text
                x={75 + i * 27}
                y="304"
                textAnchor="middle"
                fontSize="6"
                fill="#7e95a5"
              >
                {i < 10 ? `F${i + 1}` : "Y"}
              </text>
            </g>
          ))}
          <rect
            x="414"
            y="199"
            width="46"
            height="60"
            rx="2"
            fill="#1b3041"
            stroke="#698398"
          />
          <rect x="420" y="207" width="34" height="22" rx="2" fill="#283f4c" />
          <text x="437" y="220" textAnchor="middle" fill="#53dbba" fontSize="8">
            MPR
          </text>
          <path d="M418 269H458M418 279H458M418 289H458" stroke="#637789" />
          <rect
            x="412"
            y="323"
            width="50"
            height="54"
            rx="3"
            fill="#1b3041"
            stroke="#4fc4b7"
            strokeDasharray="4 3"
          />
          <text x="438" y="339" textAnchor="middle" fill="#9bc9c5" fontSize="7">
            EDGE
          </text>
          <text x="225" y="332" textAnchor="middle" fill="#7c91a3" fontSize="9">
            KABLO BAĞLANTI BÖLGESİ
          </text>
          <path d="M370 319V386M366 319H374M366 386H374" stroke="#65798c" />
          <text
            transform="translate(382 375) rotate(-90)"
            fill="#7d93a6"
            fontSize="8"
          >
            en az 400 mm
          </text>
          {[122, 153, 184, 215, 246, 277, 308].map((x) => (
            <path
              key={x}
              d={`M${x} 307V349q0 12 10 12V394`}
              fill="none"
              stroke="#465d70"
              strokeWidth="2"
            />
          ))}
          {points.map((p) => (
            <g
              key={p.id}
              role="button"
              tabIndex={0}
              aria-label={p.label}
              onClick={() => setActive(p.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setActive(p.id);
                }
              }}
              className="sensor-point"
            >
              <circle
                cx={p.x}
                cy={p.y}
                r="18"
                fill={active === p.id ? "#2dd8ba22" : "#0e1e2d"}
                stroke={active === p.id ? "#62f1ce" : "#37999c"}
                strokeWidth={active === p.id ? 2 : 1}
              />
              <circle
                cx={p.x}
                cy={p.y}
                r="23"
                fill="none"
                stroke={active === p.id ? "#38c4aa55" : "transparent"}
              />
              <text
                x={p.x}
                y={p.y + 4}
                textAnchor="middle"
                fill="#69e9cf"
                fontSize="10"
                fontWeight="700"
              >
                {p.short}
              </text>
            </g>
          ))}
          <text x="266" y="426" textAnchor="middle" fill="#71889c" fontSize="9">
            Derinlik 450 mm (+50 / −0) · Şema ölçekli değildir
          </text>
        </svg>
      </div>
      <div className="sensor-tabs">
        {points.map((p) => (
          <button
            key={p.id}
            className={active === p.id ? "active" : ""}
            onClick={() => setActive(p.id)}
          >
            {p.short}
          </button>
        ))}
      </div>
      <div className="sensor-description">
        <CircleDot size={19} />
        <div>
          <div className="sensor-title">
            <strong>{selected.label}</strong>
            <span>
              {selected.id === "edge"
                ? panel.communication_ok
                  ? "Gateway bağlı"
                  : "Gateway iletişimi yok"
                : selected.key
                  ? `${number(measuredValue(panel, selected.key), 1)} ${selected.unit} · ${qualityLabel(panel, selected.key)}`
                  : !panel.arc?.communication_ok
                    ? "Bilinmiyor · iletişim yok"
                    : panel.arc?.event
                      ? "Sentetik olay var"
                      : "Olay yok"}
            </span>
          </div>
          <small>{selected.kind}</small>
          <p>{selected.text}</p>
        </div>
      </div>
      <div className="source-note">
        <Info size={13} /> Kaynak: TEDAŞ EK-II/14, basılı s.51. Ek sensörler
        öneridir.
      </div>
    </section>
  );
}
