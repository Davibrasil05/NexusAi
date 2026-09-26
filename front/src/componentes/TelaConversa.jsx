import { useEffect, useRef, useState } from "react";
import { Bot, ListTree, SendHorizontal } from "lucide-react";
import { respostasRapidas } from "../textos";

function Pensando() {
  const [demorou, setDemorou] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setDemorou(true), 5000);
    return () => clearTimeout(t);
  }, []);
  return (
    <div className="flex items-center gap-2.5 text-suave">
      <span className="flex gap-1.5">
        {[0, 150, 300].map((d) => (
          <i key={d} className="size-2 animate-pulo rounded-full bg-roxo-600" style={{ animationDelay: `${d}ms` }} />
        ))}
      </span>
      {demorou ? "Preparando a orientação…" : "Analisando a resposta…"}
    </div>
  );
}

function Balao({ autor, atual, children }) {
  if (autor === "acs") {
    return (
      <div className="animate-subir max-w-[86%] self-end rounded-3xl rounded-br-md bg-roxo-600 px-4 py-3 text-white shadow-sm">
        {children}
      </div>
    );
  }
  return (
    <div className="animate-subir flex max-w-[92%] items-end gap-2 self-start">
      <div className="grid size-9 shrink-0 place-items-center rounded-full bg-roxo-100 text-roxo-700">
        <Bot className="size-5" />
      </div>
      <div className={`rounded-3xl rounded-bl-md bg-white px-4 py-3 shadow-sm ${atual ? "font-semibold ring-2 ring-roxo-600" : ""}`}>
        {children}
      </div>
    </div>
  );
}

export default function TelaConversa({ caso, pendente, pensando, onEnviar, onAbrirRaciocinio }) {
  const [texto, setTexto] = useState("");
  const fim = useRef(null);
  const historico = caso?.historico ?? [];
  const ultimaDoAgente = historico.findLastIndex((m) => m.autor === "agente");
  const chips = pensando ? [] : respostasRapidas(caso?.campo_perguntado);

  useEffect(() => {
    fim.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [historico.length, pensando]);

  function enviar(valor) {
    const t = valor.trim();
    if (!t || pensando) return;
    setTexto("");
    onEnviar(t);
  }

  return (
    <>
      <main className="flex flex-1 flex-col gap-3 overflow-y-auto p-4" aria-live="polite">
        {historico.map((m, i) => (
          <Balao key={i} autor={m.autor} atual={i === ultimaDoAgente && !pensando}>
            {m.texto}
          </Balao>
        ))}
        {pendente && <Balao autor="acs">{pendente}</Balao>}
        {pensando && (
          <Balao autor="agente">
            <Pensando />
          </Balao>
        )}
        <div ref={fim} />
      </main>

      <footer className="space-y-3 border-t border-linha bg-white p-3 pb-[max(12px,env(safe-area-inset-bottom))]">
        {chips.length > 0 && (
          <p className="px-1 text-sm font-semibold text-suave">Toque na resposta:</p>
        )}
        {chips.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {chips.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => enviar(c)}
                className="min-h-13 flex-auto rounded-2xl border-2 border-roxo-600 bg-roxo-50 px-4 py-2.5 text-lg font-bold text-roxo-800 transition active:bg-roxo-600 active:text-white"
              >
                {c}
              </button>
            ))}
          </div>
        )}
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            enviar(texto);
          }}
        >
          <label htmlFor="texto" className="sr-only">Resposta do ACS</label>
          <input
            id="texto"
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
            disabled={pensando}
            autoComplete="off"
            enterKeyHint="send"
            placeholder={chips.length ? "Ou escreva com suas palavras…" : "Escreva a resposta…"}
            className="h-14 min-w-0 flex-1 rounded-2xl border-2 border-linha bg-fundo px-4 outline-none focus:border-roxo-600 focus:bg-white focus:ring-4 focus:ring-roxo-100 disabled:opacity-60"
          />
          <button
            type="submit"
            aria-label="Enviar"
            disabled={pensando || !texto.trim()}
            className="grid size-14 shrink-0 place-items-center rounded-2xl bg-roxo-600 text-white active:bg-roxo-800 disabled:bg-roxo-200"
          >
            <SendHorizontal className="size-6" />
          </button>
        </form>
        <button type="button" onClick={onAbrirRaciocinio}
          className="flex min-h-11 w-full items-center justify-center gap-2 text-[15px] font-semibold text-roxo-700 lg:hidden">
          <ListTree className="size-4" /> Ver como o assistente está decidindo
        </button>
      </footer>
    </>
  );
}
