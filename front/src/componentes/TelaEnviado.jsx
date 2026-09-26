import { CheckCircle2, CloudOff } from "lucide-react";
import { NIVEL, hora } from "../textos";

export default function TelaEnviado({ ficha, onNovo }) {
  const enviada = ficha.status === "enviada";
  const nivel = NIVEL[ficha.cor];
  return (
    <>
      <main className="flex flex-1 flex-col items-center justify-center gap-5 overflow-y-auto p-6 text-center">
        <div className={`animate-subir grid size-24 place-items-center rounded-full ${enviada ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>
          {enviada ? <CheckCircle2 className="size-14" /> : <CloudOff className="size-14" />}
        </div>
        <div>
          <h2 className="text-[26px] font-bold tracking-tight">{enviada ? "Ficha enviada" : "Ficha guardada"}</h2>
          <p className="mt-2 text-suave">
            {enviada
              ? ficha.em_casa
                ? "A unidade foi avisada. Lembre da revisita em 24 a 48 horas."
                : `${ficha.destino_nome} já recebeu a ficha.`
              : "Está sem sinal. A ficha fica guardada no celular e vai sozinha quando o sinal voltar."}
          </p>
        </div>
        <div className="w-full rounded-3xl bg-white p-4 text-left shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <span className={`rounded-full px-3 py-1 text-sm font-bold ${nivel.fundo} ${nivel.texto}`}>{nivel.nome}</span>
            <span className="text-sm text-suave">Ficha nº {ficha.id}</span>
          </div>
          <p className="mt-3 font-semibold">{ficha.em_casa ? "Fica em casa" : ficha.destino_nome}</p>
          {ficha.chegada_prevista && <p className="text-roxo-700">Chegada prevista às {hora(ficha.chegada_prevista)}</p>}
        </div>
      </main>
      <footer className="border-t border-linha bg-white p-4 pb-[max(16px,env(safe-area-inset-bottom))]">
        <button type="button" onClick={onNovo}
          className="flex h-14 w-full items-center justify-center rounded-2xl bg-roxo-600 text-[19px] font-bold text-white shadow-lg shadow-roxo-600/25 active:bg-roxo-800">
          Novo atendimento
        </button>
      </footer>
    </>
  );
}
