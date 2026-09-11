"use client";
import { useMemo, useState } from "react";
import {
  ArrowRight,
  Box,
  Calculator,
  Check,
  CircuitBoard,
  Database,
  FlaskConical,
  Layers3,
  LockKeyhole,
  Network,
  Radio,
  Shield,
  Thermometer,
  Wrench,
} from "lucide-react";
import { number, dateTime } from "@/lib/api";
import {
  calculateTco,
  componentKeys,
  parseCost,
  type TcoInput,
} from "@/lib/tco";
import proof from "@/data/scale-proof.json";

const tierRows = [
  {
    name: "Mevcut ekipman",
    core: "MPR + varsa TVOC-COM verisi",
    thermal: "CORE ekipmanını kullanır",
    pd: "THERMAL ekipmanını kullanır",
  },
  {
    name: "Yeni donanım",
    core: "Edge + izole arayüz + temel ortam düğümü",
    thermal: "Seçilen bağlantılarda kablosuz yüzey sıcaklığı",
    pd: "Uygun HFCT + acquisition / feature katmanı",
  },
  {
    name: "Kurulum yaklaşımı",
    core: "Dış erişim A/B; yeni iç besleme C",
    thermal: "Canlı bağlantıya sensör montajı C",
    pd: "HFCT/toprak bağlantısı C",
  },
  {
    name: "Bakım ve kablolama",
    core: "Mevcut Modbus yolu + LAN; ortam düğümü bakımı",
    thermal: "Yeni sensör kablosu azalır; erişime göre pil bakımı",
    pd: "Koaksiyel / LAN ve uzman acquisition bakımı",
  },
  {
    name: "Göreli karmaşıklık",
    core: "Temel izleme kapsamı",
    thermal: "Seçilmiş noktalarda ek izleme",
    pd: "Uzmanlık ve kalibrasyon gerektiren katman",
  },
  {
    name: "Hedef kullanım",
    core: "Yaygın temel görünürlük",
    thermal: "Termal riski yüksek bağlantılar",
    pd: "PD incelemesi gerekçelendirilen kritik varlıklar",
  },
];
const installation = [
  [
    "Mevcut MPR gateway verisi",
    "A/B",
    "Güvenli mevcut ağ erişimi ve onaylı commissioning",
  ],
  [
    "Mevcut TVOC-COM okuması",
    "B",
    "Koruma iletişimini etkilemeyen onaylı veri paylaşımı",
  ],
  [
    "Yeni TVOC donanımı / COM",
    "C",
    "Yetkili protection ekibiyle planlı kesinti",
  ],
  [
    "Bağlantıda yüzey sıcaklığı sensörü",
    "C",
    "Canlı bağlantıya fiziksel erişim / izolasyon",
  ],
  [
    "TH-A / H1 ortam düğümü",
    "A/B/C",
    "Sağ yardımcı hacmin güvenli erişim koşuluna bağlı",
  ],
  [
    "Yeni iç PSU / HFCT montajı",
    "C",
    "Yeni güç veya uygun toprak bağlantısına müdahale",
  ],
  [
    "Dış / duvar tipi gateway",
    "A/B",
    "Mevcut onaylı besleme ve güvenli dış erişim",
  ],
];
const costLabels: Record<string, string> = {
  gateway: "Gateway",
  isolated_interfaces: "İzole arayüzler",
  sensors: "Sensörler",
  installation: "Kurulum",
  commissioning: "Devreye alma",
  planned_outage: "Varsa planlı kesinti maliyeti",
  optional_pd: "Opsiyonel PD katmanı",
  shared_server: "Ortak sunucu · filonun tamamı",
  maintenance_annual: "Yıllık bakım · pano başına",
  battery_annual: "Yıllık pil değişimi · pano başına",
};
const benefitLabels: Record<string, string> = {
  outage_hour_cost: "Kesinti saat maliyeti",
  maintenance_visit_cost: "Saha ziyareti maliyeti",
  avoided_hours: "Varsayılan kaçınılan saat / yıl / pano",
  avoided_visits: "Varsayılan kaçınılan ziyaret / yıl / pano",
};
const blank: TcoInput = Object.fromEntries(
  [
    ...componentKeys,
    "panel_count",
    "period_years",
    "currency",
    ...Object.keys(benefitLabels),
  ].map((key) => [key, ""]),
);

export function DeploymentView() {
  const [tab, setTab] = useState<"overview" | "installation" | "cost">(
    "overview",
  );
  const total = proof.cases.reduce((sum, item) => sum + item.committed, 0),
    expected = proof.cases.reduce((sum, item) => sum + item.expected, 0);
  return (
    <>
      <div className="section-heading">
        <div>
          <div className="eyebrow">YAYGINLAŞTIRMA / ÇÖZÜM DEĞERİ</div>
          <h1>Mevcut yatırımı koruyarak büyüyün.</h1>
          <p>
            Retrofit yaklaşımı, erişime göre kurulum ve ihtiyaca göre izleme
            kapsamı.
          </p>
        </div>
        <span className="small-tag cyan">
          <LockKeyhole size={12} /> ON-PREMISE
        </span>
      </div>
      <div className="context-strip">
        <span>
          <FlaskConical size={14} /> KONSEPT + ÖLÇÜLMÜŞ YAZILIM DEMOSU
        </span>
        <p>
          Fiziksel saha kurulumu, fiyat teklifi, gerçek tasarruf veya ürün
          sertifikasyonu iddiası yoktur.
        </p>
      </div>
      <div className="detail-tabs deployment-tabs">
        <button
          className={tab === "overview" ? "active" : ""}
          onClick={() => setTab("overview")}
        >
          Kapsam ve ölçek
        </button>
        <button
          className={tab === "installation" ? "active" : ""}
          onClick={() => setTab("installation")}
        >
          Kurulum / A–B–C
        </button>
        <button
          className={tab === "cost" ? "active" : ""}
          onClick={() => setTab("cost")}
        >
          Maliyet modeli
        </button>
      </div>
      {tab === "overview" && (
        <>
          <div className="value-pillars">
            <section className="card">
              <CircuitBoard size={22} />
              <h3>Mevcut cihazdan veri</h3>
              <p>
                MPR ölçümleri ve varsa TVOC-COM olayları yeniden ölçülmeden
                ortak izleme katmanına alınır.
              </p>
            </section>
            <section className="card">
              <Radio size={22} />
              <h3>Uygun noktada kablosuz</h3>
              <p>
                Yeni ortam/yüzey sensörlerinde kablolamayı azaltma hedefi. Metal
                pano RF kapsaması sahada ölçülür.
              </p>
            </section>
            <section className="card">
              <Shield size={22} />
              <h3>Koruma bağımsız kalır</h3>
              <p>
                Kural, trend ve veri kalitesiyle açıklanabilir karar desteği.
                ABB protection işlevine kontrol yolu yoktur.
              </p>
            </section>
          </div>
          <section className="card tier-comparison">
            <div className="card-heading">
              <h3>
                <Layers3 size={17} /> İhtiyaca göre üç dağıtım seviyesi
              </h3>
              <span className="small-tag">TEKLİF GEREKTİRİR</span>
            </div>
            <div className="tier-intro">
              <div />
              <div>
                <span>01</span>
                <h2>CORE</h2>
                <p>Temel görünürlük</p>
              </div>
              <div>
                <span>02</span>
                <h2>THERMAL</h2>
                <p>Bağlantı sıcaklığı odağı</p>
              </div>
              <div>
                <span>03</span>
                <h2>ADVANCED PD</h2>
                <p>Uzman acquisition katmanı</p>
              </div>
            </div>
            <div className="table-scroll">
              <table className="tier-table">
                <thead>
                  <tr>
                    <th>KAPSAM</th>
                    <th>CORE</th>
                    <th>THERMAL</th>
                    <th>ADVANCED PD</th>
                  </tr>
                </thead>
                <tbody>
                  {tierRows.map((row) => (
                    <tr key={row.name}>
                      <th>{row.name}</th>
                      <td>{row.core}</td>
                      <td>{row.thermal}</td>
                      <td>{row.pd}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="source-note">
              Her seviyede donanım, kurulum, bakım ve varsa acquisition için
              güncel teklif/saha keşfi gerekir. Pil ömrü ve fiyat
              varsayılmamıştır.
            </div>
          </section>
          <section className="card scale-proof">
            <div className="card-heading">
              <div>
                <h3>
                  <Database size={17} /> Ölçülmüş merkezi ölçek
                </h3>
                <p>
                  {proof.source_label} · {dateTime(proof.measured_at)}
                </p>
              </div>
              <span className="small-tag">
                {proof.version.toUpperCase()} KANITI
              </span>
            </div>
            <div className="scale-headline">
              <strong>
                {number(total)}
                <span> / {number(expected)}</span>
              </strong>
              <div>
                <h3>PostgreSQL kalıcı kayıt</h3>
                <p>
                  {proof.cases.filter((item) => item.passed).length} /{" "}
                  {proof.cases.length} HTTP ve MQTT test vakası başarılı
                </p>
              </div>
              <span className="simulation-badge">TÜM GÖZLEMLER SENTETİK</span>
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>PANO</th>
                    <th>TAŞIMA</th>
                    <th>COMMIT / BEKLENEN</th>
                    <th>FRAME / SN</th>
                    <th>FİLO API P95</th>
                  </tr>
                </thead>
                <tbody>
                  {proof.cases.map((item) => (
                    <tr key={`${item.panels}-${item.transport}`}>
                      <td>{item.panels}</td>
                      <td>{item.transport}</td>
                      <td className="good-text">
                        {number(item.committed)} / {number(item.expected)}
                      </td>
                      <td>{number(item.frames_per_second, 2)}</td>
                      <td>{number(item.api_p95_ms, 1)} ms</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="scale-boundary">
              <FlaskConical size={17} />
              <p>
                {proof.limitation}{" "}
                <span>
                  {proof.environment} · Kaynak: {proof.source_path}
                </span>
              </p>
            </div>
            <div className="scale-architecture">
              {[
                "Panel / Edge",
                "MQTT",
                "Ingestion",
                "PostgreSQL + risk",
                "UI + SCADA bankları",
              ].map((item, index) => (
                <div key={item}>
                  {index > 0 && <ArrowRight size={14} />}
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </section>
          <div className="deployment-bottom">
            <section className="card">
              <div className="card-heading">
                <h3>Teknik fark nerede?</h3>
              </div>
              <ul className="value-list">
                {[
                  "Mevcut MPR/TVOC yatırımının yeniden kullanılması",
                  "Elektriksel, termal ve PD sinyallerinin birlikte değerlendirilmesi",
                  "Skorun kural katkıları ve operatör aksiyonuyla açıklanması",
                  "Eksik / eski / geçersiz veriyle sağlıklı görünmeme",
                  "Şirket içinde saklama, salt okunur SCADA bankları",
                  "Kaynak, üretilmiş veri ve saha tasarımının açık ayrımı",
                ].map((item) => (
                  <li key={item}>
                    <Check size={14} />
                    {item}
                  </li>
                ))}
              </ul>
            </section>
            <section className="card validation-boundary">
              <div className="card-heading">
                <h3>Saha doğrulaması bekleyenler</h3>
              </div>
              <p>
                RF kapsama, pil ömrü, montaj/izolasyon koordinasyonu,
                düşük-yüksek sıcaklık, yoğun manyetik alan/EMC, gerçek RTU cihaz
                ayarları ve kalibre PD acquisition.
              </p>
              <span>
                <Shield size={17} /> Kablosuz veya tak-çalıştır tasarım,
                enerjili ekipmana dokunma izni değildir.
              </span>
              <p>
                Fayda; merkezi görünürlük ve bakım planlama potansiyelidir.
                Gerçek tasarruf oranı veya önlenmiş kesinti süresi ölçülmedi.
              </p>
            </section>
          </div>
        </>
      )}
      {tab === "installation" && (
        <>
          <div className="installation-classes">
            <section className="card">
              <b>A</b>
              <h3>Güvenli dış erişim</h3>
              <p>
                Canlı kısımlara yaklaşmadan, mevcut güvenli erişim üzerinden.
                Enerji kesmeden uygulanabilirliği saha sahibi belirler.
              </p>
            </section>
            <section className="card">
              <b>B</b>
              <h3>Kontrollü müdahale</h3>
              <p>
                Onaylı commissioning veya monitoring iletişimi müdahalesi.
                Elektriksel risk gerektirirse sınıf C'ye yükselir.
              </p>
            </section>
            <section className="card">
              <b>C</b>
              <h3>Planlı kesinti</h3>
              <p>
                İzolasyon, yetkili saha prosedürü ve koruma ekipmanının
                bağımsızlığını koruyan kontrollü kurulum.
              </p>
            </section>
          </div>
          <section className="card table-card installation-table">
            <div className="card-heading">
              <h3>
                <Wrench size={17} /> Bileşene göre erişim sınıfı
              </h3>
              <span className="small-tag">SAHA KEŞFİ GEREKİR</span>
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>BİLEŞEN</th>
                    <th>SINIF</th>
                    <th>KOŞUL / GEREKÇE</th>
                  </tr>
                </thead>
                <tbody>
                  {installation.map(([component, level, condition]) => (
                    <tr key={component}>
                      <td>{component}</td>
                      <td>
                        <span
                          className={`installation-class ${level === "C" ? "outage" : ""}`}
                        >
                          {level}
                        </span>
                      </td>
                      <td>{condition}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="scale-boundary">
              <Shield size={19} />
              <p>
                Wireless = canlı çalışma izni değildir. Yeni PSU, HFCT ve canlı
                bağlantıya yüzey sensörü kurulumu planlı kesinti gerektiren
                konseptlerdir. Süre, montaj uygunluğu ve nihai sınıf saha
                keşfiyle belirlenir.
              </p>
            </div>
          </section>
          <div className="context-strip">
            <span>
              <Thermometer size={15} /> TH-A / H1
            </span>
            <p>
              Sağ yardımcı hacimde temsil edici hava noktası. Alt kablo/toprak
              alanında PD-A / P1 kalır. Kaynak: docs/hardware/panel-placement.md
              ve TEDAŞ EK-II/14.
            </p>
          </div>
        </>
      )}
      {tab === "cost" && <TcoCalculator />}
    </>
  );
}

function TcoCalculator() {
  const [inputs, setInputs] = useState<TcoInput>({ ...blank });
  const result = useMemo(() => calculateTco(inputs), [inputs]);
  const update = (key: string, value: string) =>
    setInputs((previous) => ({ ...previous, [key]: value }));
  const field = (key: string, label: string, min = 0) => (
    <label key={key} className="cost-field">
      <span>{label}</span>
      <input
        aria-label={label}
        type="number"
        min={min}
        step={key === "panel_count" ? 1 : "any"}
        inputMode="decimal"
        value={inputs[key]}
        onChange={(event) => update(key, event.target.value)}
        placeholder="Kendi değerinizi girin"
        aria-invalid={
          inputs[key] !== "" &&
          (parseCost(inputs[key]) === null ||
            (key === "panel_count" &&
              (Number(inputs[key]) < 1 ||
                !Number.isInteger(Number(inputs[key])))) ||
            (key === "period_years" && Number(inputs[key]) <= 0))
        }
      />
    </label>
  );
  return (
    <>
      <div className="tco-disclosure">
        <Calculator size={22} />
        <div>
          <h3>Sizin girdilerinizle varsayımsal maliyet</h3>
          <p>
            Hazır fiyat veya tasarruf varsayımı yoktur. Eksik alanlar sıfır
            sayılmaz. Kapsam dışı bir maliyet için açıkça 0 girin. Girdiler
            tarayıcı belleğinde kalır.
          </p>
        </div>
        <button className="secondary" onClick={() => setInputs({ ...blank })}>
          Girdileri temizle
        </button>
      </div>
      <div className="tco-layout">
        <section className="card">
          <div className="card-heading">
            <h3>
              <Box size={17} /> Teklif ve planlama girdileri
            </h3>
            <span className="small-tag">KULLANICI GİRDİSİ</span>
          </div>
          <form
            onSubmit={(event) => event.preventDefault()}
            className="tco-form"
          >
            <div className="cost-grid">
              <label className="cost-field">
                <span>Para birimi</span>
                <input
                  aria-label="Para birimi"
                  value={inputs.currency}
                  maxLength={12}
                  onChange={(event) => update("currency", event.target.value)}
                  placeholder="Kendi para biriminiz"
                />
              </label>
              {field("panel_count", "Pano sayısı", 1)}
              {field("period_years", "Değerlendirme dönemi (yıl)", 0.01)}
            </div>
            <p className="cost-group-label">
              Bir defalık bedeller pano başınadır. Ortak sunucu bedeli filonun
              tamamına aittir.
            </p>
            <div className="cost-grid">
              {componentKeys.map((key) => field(key, costLabels[key]))}
            </div>
            <p className="cost-group-label">
              İsteğe bağlı fayda varsayımları · Yıllık, pano başına. Bunlar saha
              sonucu değildir.
            </p>
            <div className="cost-grid">
              {Object.entries(benefitLabels).map(([key, label]) =>
                field(key, label),
              )}
            </div>
          </form>
        </section>
        <aside className="card tco-result">
          <div className="card-heading">
            <h3>Parametrik TCO</h3>
            <span className="small-tag">TAHMİN</span>
          </div>
          {result.ready ? (
            <div className="cost-results" data-testid="tco-results">
              <span>
                {number(result.count)} pano · {number(result.years, 1)} yıl ·
                Kullanıcı girdisi
              </span>
              <div>
                <small>Pano başına dönem TCO</small>
                <strong data-testid="tco-per-panel">
                  {number(result.perPanelTotal, 2)} <em>{inputs.currency}</em>
                </strong>
              </div>
              <div>
                <small>Filo toplam TCO</small>
                <strong data-testid="tco-fleet-total">
                  {number(result.fleetTotal, 2)} <em>{inputs.currency}</em>
                </strong>
              </div>
              <dl>
                <div>
                  <dt>Pano başına ilk yatırım</dt>
                  <dd>
                    {number(result.perPanelInitial, 2)} {inputs.currency}
                  </dd>
                </div>
                <div>
                  <dt>Pano başına yıllık bakım + pil</dt>
                  <dd>
                    {number(result.perPanelAnnual, 2)} {inputs.currency}
                  </dd>
                </div>
              </dl>
              <div className="payback-output">
                <h4>İsteğe bağlı varsayımsal fayda</h4>
                {result.annualNet === null ? (
                  <p>
                    Fayda alanları eksik: tasarruf veya geri ödeme hesaplanmadı.
                  </p>
                ) : (
                  <>
                    <p>
                      Yıllık net varsayımsal fayda:{" "}
                      {number(result.annualNet, 2)} {inputs.currency} / pano.
                    </p>
                    <strong>
                      {result.paybackYears === null
                        ? "Pozitif net fayda yok; geri ödeme hesaplanmaz."
                        : `Basit varsayımsal geri ödeme: ${number(result.paybackYears, 2)} yıl`}
                    </strong>
                  </>
                )}
                <small>
                  Finansman, iskonto ve vergi dahil değildir. Gerçek saha
                  getirisi iddiası değildir.
                </small>
              </div>
            </div>
          ) : (
            <div className="cost-incomplete" data-testid="tco-incomplete">
              <Calculator size={27} />
              <strong>Hesaplama için girdiler bekleniyor</strong>
              <p>
                Para birimi, en az 1 tam sayı pano, pozitif dönem ve tüm maliyet
                bileşenlerini girin. Negatif veya geçersiz değerler kullanılmaz.
              </p>
              <span>
                TCO — <br />
                Geri ödeme —
              </span>
            </div>
          )}
          <div className="cost-formula">
            <strong>Hesabın dayanağı</strong>
            <p>
              Pano TCO = gateway + izole arayüz + sensör + kurulum + devreye
              alma + varsa kesinti + opsiyonel PD + ortak sunucu / pano sayısı +
              yıl × (yıllık bakım + yıllık pil).
            </p>
            <p>
              Net yıllık varsayımsal fayda = kaçınılan saat × saat maliyeti +
              kaçınılan ziyaret × ziyaret maliyeti − yıllık bakım − yıllık pil.
              Basit geri ödeme = ilk yatırım / pozitif net yıllık fayda.
            </p>
          </div>
        </aside>
      </div>
      <div className="context-strip">
        <span>
          <Network size={15} /> MALİYETİN YAPISI
        </span>
        <p>
          Mevcut ekipmanı kullanma, seçilmiş noktalarda sensör ekleme ve ortak
          on-premise altyapı yatırımını paylaşma yaklaşımıdır; gerçek TL/USD
          fiyatı veya tasarruf yüzdesi verilmez.
        </p>
      </div>
    </>
  );
}
