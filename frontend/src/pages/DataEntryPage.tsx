import { useEffect, useState, type FormEvent } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Card } from "@/components/Card";
import { Field, Input, Select, Button } from "@/components/Field";
import { ErrorState, Spinner } from "@/components/Spinner";
import {
  ApiError,
  type Asset,
  type PositionFull,
  getAssets,
  getPositions,
  createAsset,
  createPosition,
  deleteAsset,
  deletePosition,
  runIngestion,
} from "@/lib/api";
import { formatCurrency, formatNumber } from "@/lib/format";

type Feedback = { kind: "ok" | "error"; text: string } | null;

const ASSET_CLASSES = ["cedear", "equity", "etf", "bond", "fx", "crypto"];

export function DataEntryPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [positions, setPositions] = useState<PositionFull[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Feedback>(null);

  async function reload() {
    setLoading(true);
    try {
      const [a, p] = await Promise.all([getAssets(), getPositions()]);
      setAssets(a);
      setPositions(p);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error al cargar");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  function notify(kind: "ok" | "error", text: string) {
    setFeedback({ kind, text });
    window.setTimeout(() => setFeedback(null), 4000);
  }

  function describe(e: unknown): string {
    return e instanceof ApiError ? e.message : "Ocurrió un error";
  }

  return (
    <div>
      <PageHeader
        title="Ingreso de datos"
        question="¿Cómo cargo y edito posiciones, transacciones y fuentes?"
      />

      {feedback && (
        <div
          className={`mb-4 rounded-control border px-4 py-2.5 text-sm ${
            feedback.kind === "ok"
              ? "border-gain/40 bg-gain/10 text-gain"
              : "border-loss/40 bg-loss/10 text-loss"
          }`}
        >
          {feedback.text}
        </div>
      )}

      {error && (
        <Card className="mb-5">
          <ErrorState message={error} />
        </Card>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <AssetForm
          assetClasses={ASSET_CLASSES}
          onCreate={async (body) => {
            try {
              await createAsset(body);
              notify("ok", `Activo ${body.ticker.toUpperCase()} creado.`);
              await reload();
            } catch (e) {
              notify("error", describe(e));
            }
          }}
        />

        <PositionForm
          assets={assets}
          onCreate={async (body) => {
            try {
              await createPosition(body);
              notify("ok", `Posición en ${body.ticker} creada.`);
              await reload();
            } catch (e) {
              notify("error", describe(e));
            }
          }}
        />
      </div>

      <Card title="Ingestión" subtitle="Forzar la ingesta de una fuente" className="mt-5">
        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="ghost"
            onClick={async () => {
              try {
                const r = await runIngestion("prices");
                notify("ok", r.message);
                await reload();
              } catch (e) {
                notify("error", describe(e));
              }
            }}
          >
            Forzar ingestión de precios
          </Button>
          <span className="text-xs text-secondary">
            Fuente mock determinística (sin red). Noticias y transcripciones:
            próximamente.
          </span>
        </div>
      </Card>

      {loading ? (
        <Card className="mt-5">
          <Spinner />
        </Card>
      ) : (
        <div className="mt-5 grid grid-cols-1 gap-5 lg:grid-cols-2">
          <Card title="Activos" subtitle={`${assets.length} en cartera`}>
            <ListTable
              empty="Sin activos"
              rows={assets.map((a) => ({
                id: a.id,
                cells: [a.ticker, a.name, a.asset_class, a.currency],
                onDelete: async () => {
                  try {
                    await deleteAsset(a.id);
                    notify("ok", `Activo ${a.ticker} eliminado.`);
                    await reload();
                  } catch (e) {
                    notify("error", describe(e));
                  }
                },
              }))}
              headers={["Ticker", "Nombre", "Clase", "Moneda", ""]}
            />
          </Card>

          <Card title="Posiciones" subtitle={`${positions.length} abiertas`}>
            <ListTable
              empty="Sin posiciones"
              headers={["Ticker", "Cantidad", "Costo prom.", "", ""]}
              rows={positions.map((p) => ({
                id: p.id,
                cells: [
                  p.ticker,
                  formatNumber(p.quantity, 0),
                  formatCurrency(p.avg_cost),
                  "",
                ],
                onDelete: async () => {
                  try {
                    await deletePosition(p.id);
                    notify("ok", "Posición eliminada.");
                    await reload();
                  } catch (e) {
                    notify("error", describe(e));
                  }
                },
              }))}
            />
          </Card>
        </div>
      )}
    </div>
  );
}

// --- Sub-components -----------------------------------------------------------

function AssetForm({
  assetClasses,
  onCreate,
}: {
  assetClasses: string[];
  onCreate: (body: Asset & Record<string, string>) => Promise<void>;
}) {
  const [form, setForm] = useState({
    ticker: "",
    name: "",
    asset_class: assetClasses[0],
    sector: "",
    country: "",
    currency: "USD",
  });
  const [busy, setBusy] = useState(false);

  function set(key: string, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    await onCreate(form as unknown as Asset & Record<string, string>);
    setBusy(false);
    setForm({ ...form, ticker: "", name: "", sector: "", country: "" });
  }

  return (
    <Card title="Nuevo activo" subtitle="Alta de un instrumento">
      <form onSubmit={submit} className="grid grid-cols-2 gap-3">
        <Field label="Ticker">
          <Input
            required
            value={form.ticker}
            onChange={(e) => set("ticker", e.target.value)}
            placeholder="AAPL"
          />
        </Field>
        <Field label="Nombre">
          <Input
            required
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            placeholder="Apple Inc."
          />
        </Field>
        <Field label="Clase">
          <Select
            value={form.asset_class}
            onChange={(e) => set("asset_class", e.target.value)}
          >
            {assetClasses.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Moneda">
          <Input
            value={form.currency}
            onChange={(e) => set("currency", e.target.value)}
            placeholder="USD"
          />
        </Field>
        <Field label="Sector">
          <Input
            value={form.sector}
            onChange={(e) => set("sector", e.target.value)}
            placeholder="Technology"
          />
        </Field>
        <Field label="País">
          <Input
            value={form.country}
            onChange={(e) => set("country", e.target.value)}
            placeholder="USA"
          />
        </Field>
        <div className="col-span-2 mt-1">
          <Button type="submit" disabled={busy}>
            {busy ? "Guardando…" : "Crear activo"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function PositionForm({
  assets,
  onCreate,
}: {
  assets: Asset[];
  onCreate: (body: {
    ticker: string;
    quantity: number;
    avg_cost: number;
  }) => Promise<void>;
}) {
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [avgCost, setAvgCost] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    await onCreate({
      ticker: ticker || assets[0]?.ticker || "",
      quantity: Number(quantity),
      avg_cost: Number(avgCost),
    });
    setBusy(false);
    setQuantity("");
    setAvgCost("");
  }

  return (
    <Card title="Nueva posición" subtitle="Abrir una tenencia">
      <form onSubmit={submit} className="grid grid-cols-2 gap-3">
        <Field label="Activo">
          <Select value={ticker} onChange={(e) => setTicker(e.target.value)}>
            {assets.length === 0 && <option value="">Sin activos</option>}
            {assets.map((a) => (
              <option key={a.id} value={a.ticker}>
                {a.ticker}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Cantidad">
          <Input
            required
            type="number"
            step="any"
            min="0"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="10"
          />
        </Field>
        <Field label="Costo promedio">
          <Input
            required
            type="number"
            step="any"
            min="0"
            value={avgCost}
            onChange={(e) => setAvgCost(e.target.value)}
            placeholder="150.00"
          />
        </Field>
        <div className="col-span-2 mt-1">
          <Button type="submit" disabled={busy || assets.length === 0}>
            {busy ? "Guardando…" : "Crear posición"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function ListTable({
  headers,
  rows,
  empty,
}: {
  headers: string[];
  rows: { id: number; cells: string[]; onDelete: () => void }[];
  empty: string;
}) {
  if (rows.length === 0) {
    return <p className="py-6 text-sm text-secondary">{empty}</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-separator text-xs uppercase tracking-wide text-secondary">
            {headers.map((h, i) => (
              <th key={i} className="px-2 py-2 text-left font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-b border-separator/50">
              {r.cells.map((c, i) => (
                <td
                  key={i}
                  className={`px-2 py-2.5 ${i === 0 ? "font-medium text-primary" : "tabnum text-secondary"}`}
                >
                  {c}
                </td>
              ))}
              <td className="px-2 py-2.5 text-right">
                <Button variant="danger" onClick={r.onDelete}>
                  Eliminar
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
