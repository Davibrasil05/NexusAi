import {
  AlertTriangle, BookOpen, Home, ListTree, Ship, ShieldAlert, Siren, TriangleAlert, Clock,
} from "lucide-react";
import { CAMPOS, NIVEL, minutos } from "../textos";

const ICONE_NIVEL = { vermelho: Siren, laranja: AlertTriangle, amarelo: Clock, verde: Home };

// Troca "[id]" por um numerozinho que aponta para o trecho do protocolo.
function FalaComCitacoes({ fala, trechos }) {
  const ordem = trechos.map((t) => t.id);
  const partes = fala.split(/\[([\w-]+)\]/g);
  return (
    <p className="text-[19px] leading-relaxed">
      {partes.map((p, i) =>
        i % 2 === 1 ? (
          <sup key={i} className="ml-0.5 font-bold text-roxo-600">{ordem.indexOf(p) + 1 || "?"}</sup>
        ) : (
          <span key={i}>{p}</span>
        ),
      )}
    </p>
  );
}

function Trechos({ trechos, abertos }) {
  return (
    <details open={abertos} className="group mt-4 border-t border-linha pt-1">
      <summary className="flex min-h-12 cursor-pointer list-none items-center gap-2 font-bold text-roxo-700">
        <BookOpen className="size-5" />
        {abertos ? "Trechos do protocolo" : `Ver trechos do protocolo (${trechos.length})`}
      </summary>
      <ol className="divide-y divide-linha">
        {trechos.map((t, i) => (
          <li key={t.id} className="py-3 text-base">
            <span className="mr-1 font-extrabold text-roxo-600">{i + 1}.</span>
            {t.texto}
            <span className="mt-1.5 flex flex-wrap items-center gap-2 text-sm text-suave">
              {t.fonte_titulo}
              {t.pagina ? `, p. ${t.pagina}` : ""}
              {!t.conferido && (
                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-800" title="O texto ainda não foi conferido no PDF original">a conferir no PDF</span>
              )}
            </span>
          </li>
        ))}
      </ol>
    </details>
  );
}

// "Precisa de X: Unidade, 2h de barco. A mais próxima (...) não tem X." -> mostra só o porquê.
function ExplicacaoDestino({ texto }) {
  const [precisa, resto = ""] = texto.split(": ");
  const porque = resto.split(". ").slice(1).join(". ");
  return (
    <div className="mt-2 space-y-1 text-base text-suave">
      <p>{precisa}.</p>
      {porque && <p className="rounded-xl bg-fundo px-3 py-2 text-[15px]">{porque}</p>}
    </div>
  );
}

function Orientacao({ orientacao }) {
  if (!orientacao || orientacao.status === "sem_protocolo") {
    return (
      <div className="flex gap-3 rounded-2xl bg-amber-50 p-4 text-amber-900">
        <TriangleAlert className="size-6 shrink-0" />
        <p className="text-base"><b>Sem protocolo para essa situação.</b> Contate a unidade de saúde para orientação.</p>
      </div>
    );
  }
  if (orientacao.status === "so_trechos") {
    return (
      <>
        <div className="flex gap-3 rounded-2xl bg-amber-50 p-4 text-amber-900">
          <ShieldAlert className="size-6 shrink-0" />
          <p className="text-base">{orientacao.problemas_verificador?.some((p) => p.startsWith("frase sem fonte"))
            ? "O resumo da IA tinha uma frase sem fonte no protocolo. Por segurança, mostramos o texto original."
            : "Mostrando o texto original do protocolo, sem resumo da IA."}</p>
        </div>
        <Trechos trechos={orientacao.trechos} abertos />
      </>
    );
  }
  return (
    <>
      <FalaComCitacoes fala={orientacao.fala} trechos={orientacao.trechos} />
      <Trechos trechos={orientacao.trechos} />
    </>
  );
}

export default function TelaResultado({ caso, ocupado, onConfirmar, onCancelar, onAbrirRaciocinio }) {
  const cls = caso.classificacao;
  const nivel = NIVEL[cls.cor];
  const Icone = ICONE_NIVEL[cls.cor];
  const destino = caso.destino;

  return (
    <>
      <main className="flex-1 space-y-4 overflow-y-auto p-4">
        <section className={`animate-subir rounded-3xl p-5 shadow-lg ${nivel.fundo} ${nivel.texto}`} aria-live="polite">
          <div className="flex items-center gap-3">
            <div className="grid size-14 place-items-center rounded-2xl bg-white/20">
              <Icone className="size-8" strokeWidth={2.4} />
            </div>
            <div>
              <p className="text-3xl font-extrabold tracking-tight">{nivel.nome}</p>
              <p className="text-lg font-bold opacity-95">{nivel.acao}</p>
            </div>
          </div>
          <ul className="mt-3 list-disc space-y-1 pl-5 text-base opacity-95">
            {cls.motivos.map((m) => <li key={m}>{m}</li>)}
          </ul>
        </section>

        {caso.assumidos?.length > 0 && (
          <div className="flex gap-3 rounded-2xl bg-amber-50 p-4 text-base text-amber-900">
            <ShieldAlert className="size-6 shrink-0" />
            <p>Sem resposta clara sobre <b>{caso.assumidos.map((c) => CAMPOS[c] ?? c).join(", ")}</b>. Por segurança, o agente considerou que sim.</p>
          </div>
        )}

        <section className="rounded-3xl bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-suave">Para onde ir</h2>
          {destino?.em_casa ? (
            <div className="flex items-start gap-4">
              <div className="grid size-13 shrink-0 place-items-center rounded-2xl bg-green-50 text-green-700"><Home className="size-7" /></div>
              <div>
                <p className="text-xl font-bold">Fica em casa</p>
                <p className="mt-1 text-base text-suave">{destino.explicacao}</p>
              </div>
            </div>
          ) : destino ? (
            <div className="flex items-start gap-4">
              <div className="grid size-13 shrink-0 place-items-center rounded-2xl bg-roxo-50 text-roxo-700"><Ship className="size-7" /></div>
              <div className="min-w-0">
                <p className="text-xl font-bold leading-snug">{destino.nome}</p>
                <p className="mt-0.5 text-lg font-bold text-roxo-700">{minutos(destino.tempo_barco_min)} de barco</p>
                <ExplicacaoDestino texto={destino.explicacao} />
              </div>
            </div>
          ) : (
            <p className="text-base text-suave">Esta comunidade ainda não tem a tabela de distâncias. Contate a unidade de referência.</p>
          )}
        </section>

        <section className="rounded-3xl bg-white p-5 shadow-sm">
          <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-suave">O que fazer agora</h2>
          <Orientacao orientacao={caso.orientacao} />
        </section>

        <button type="button" onClick={onAbrirRaciocinio}
          className="flex min-h-11 w-full items-center justify-center gap-2 text-[15px] font-semibold text-roxo-700 lg:hidden">
          <ListTree className="size-4" /> Ver como o assistente decidiu
        </button>
        <p className="px-2 text-center text-sm text-suave">O assistente ajuda na decisão. A palavra final é sempre do ACS.</p>
      </main>

      <footer className="space-y-2.5 border-t border-linha bg-white p-4 pb-[max(16px,env(safe-area-inset-bottom))]">
        <button type="button" onClick={onConfirmar} disabled={ocupado}
          className="flex h-14 w-full items-center justify-center rounded-2xl bg-roxo-600 text-[19px] font-bold text-white shadow-lg shadow-roxo-600/25 active:bg-roxo-800 disabled:bg-roxo-200">
          {ocupado ? "Salvando…" : "Confirmar e enviar ficha"}
        </button>
        <button type="button" onClick={onCancelar}
          className="flex h-12 w-full items-center justify-center rounded-2xl font-bold text-roxo-700 active:bg-roxo-50">
          Cancelar atendimento
        </button>
      </footer>
    </>
  );
}
