import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { PASSOS, QUEM } from "../textos";

function Legenda() {
  return (
    <div className="mb-3 flex flex-wrap gap-1.5">
      {Object.values(QUEM).map((q) => (
        <span key={q.nome} className={`rounded-full px-2.5 py-0.5 text-xs font-bold text-white ${q.tag}`}>
          {q.nome}
        </span>
      ))}
    </div>
  );
}

function ListaPassos({ passos }) {
  const fim = useRef(null);
  useEffect(() => {
    fim.current?.scrollIntoView({ block: "nearest" });
  }, [passos.length]);

  if (!passos.length) return <p className="py-6 text-center text-suave">Os passos aparecem aqui durante o atendimento.</p>;
  return (
    <ol className="grid gap-2.5">
      {passos.map((p) => {
        const q = QUEM[p.quem] ?? QUEM.codigo;
        return (
          <li key={p.n} className={`animate-subir rounded-r-xl border-l-4 bg-fundo px-3 py-2.5 ${q.borda}`}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="flex-1 text-[15px] font-semibold">{PASSOS[p.ferramenta] ?? p.ferramenta}</span>
              {p.ms > 0 && <span className="text-xs text-suave">{(p.ms / 1000).toFixed(1)} s</span>}
              <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold text-white ${q.tag}`}>{q.nome}</span>
            </div>
            {(p.entrada != null || p.saida != null) && (
              <details className="mt-1 text-xs">
                <summary className="cursor-pointer text-suave">detalhes</summary>
                <pre className="mt-1.5 max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-lg bg-white p-2">
                  {JSON.stringify({ entrada: p.entrada ?? undefined, saida: p.saida ?? undefined }, null, 2)}
                </pre>
              </details>
            )}
          </li>
        );
      })}
      <li ref={fim} aria-hidden="true" className="h-px" />
    </ol>
  );
}

// Computador: painel fixo ao lado do "celular". Celular: gaveta que sobe de baixo.
export function RaciocinioLateral({ passos }) {
  return (
    <aside
      aria-label="Painel de raciocínio"
      className="sticky top-6 hidden max-h-[calc(100dvh-48px)] self-start overflow-auto rounded-3xl bg-white p-5 shadow-sm lg:block"
    >
      <h2 className="text-xl font-bold tracking-tight">Como o agente decidiu</h2>
      <p className="mb-3 text-[15px] text-suave">Cada passo, na ordem. Toque em "detalhes" para ver entrada e saída.</p>
      <Legenda />
      <ListaPassos passos={passos} />
    </aside>
  );
}

export function RaciocinioGaveta({ aberta, onFechar, passos }) {
  if (!aberta) return null;
  return (
    <div className="fixed inset-0 z-30 lg:hidden" role="dialog" aria-modal="true" aria-label="Como o agente decidiu">
      <button type="button" aria-label="Fechar" onClick={onFechar} className="absolute inset-0 bg-black/45" />
      <div className="animate-subir absolute inset-x-0 bottom-0 max-h-[82dvh] overflow-auto rounded-t-3xl bg-white px-4 pb-[max(20px,env(safe-area-inset-bottom))] pt-2.5">
        <div className="mx-auto mb-3 h-1.5 w-11 rounded-full bg-linha" />
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-xl font-bold">Como o agente decidiu</h2>
          <button type="button" onClick={onFechar} aria-label="Fechar" className="grid size-11 place-items-center rounded-full bg-fundo">
            <X className="size-5" />
          </button>
        </div>
        <Legenda />
        <ListaPassos passos={passos} />
      </div>
    </div>
  );
}
