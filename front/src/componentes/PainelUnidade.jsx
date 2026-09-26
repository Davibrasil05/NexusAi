import { useEffect, useState } from "react";
import { Home, Inbox, RotateCcw, Ship } from "lucide-react";
import { api } from "../api";
import { NIVEL, hora, minutos } from "../textos";
import Topo from "./Topo";

function Ficha({ f }) {
  const nivel = NIVEL[f.cor];
  return (
    <article className="animate-subir flex overflow-hidden rounded-3xl bg-white shadow-sm">
      <div className={`w-2.5 shrink-0 ${nivel.faixa}`} />
      <div className="min-w-0 flex-1 p-4">
        <div className="flex items-start justify-between gap-3">
          <span className={`rounded-full px-3 py-1 text-sm font-bold ${nivel.fundo} ${nivel.texto}`}>{nivel.nome}</span>
          {f.chegada_prevista ? (
            <span className="text-right">
              <span className="block text-xs text-suave">chega às</span>
              <span className="text-xl font-extrabold text-roxo-700">{hora(f.chegada_prevista)}</span>
            </span>
          ) : (
            <span className="text-sm font-semibold text-green-700">em casa</span>
          )}
        </div>
        {f.foto && <img src={f.foto} alt="Foto do hematoma" className="float-right ml-3 mt-3 size-16 rounded-xl object-cover" />}
        <p className="mt-3 font-semibold">
          {f.idade != null ? `${f.idade} anos · ` : ""}{f.comunidade}
        </p>
        <p className="mt-1 text-[15px] text-suave">{f.motivos.join("; ")}</p>
        <p className="mt-2 flex items-center gap-1.5 text-sm text-suave">
          {f.em_casa ? <Home className="size-4" /> : <Ship className="size-4" />}
          {f.em_casa ? "Revisita do ACS" : `${f.destino_nome} · ${minutos(f.tempo_barco_min)} de barco`}
          <span className="ml-auto">nº {f.id}</span>
        </p>
      </div>
    </article>
  );
}

export default function PainelUnidade({ unidades }) {
  const [unidade, setUnidade] = useState("");
  const [fichas, setFichas] = useState([]);
  const [erro, setErro] = useState(false);

  useEffect(() => {
    let vivo = true;
    const buscar = () =>
      api.fichas(unidade).then((f) => vivo && (setFichas(f), setErro(false))).catch(() => vivo && setErro(true));
    buscar();
    const t = setInterval(buscar, 2000);
    return () => {
      vivo = false;
      clearInterval(t);
    };
  }, [unidade]);

  async function reiniciar() {
    if (!confirm("Apagar todas as fichas e recomeçar a demonstração?")) return;
    await api.reiniciar();
    setFichas([]);
  }

  return (
    <div className="min-h-dvh">
      <Topo titulo="Painel da unidade" subtitulo="Fichas recebidas dos ACS · atualiza sozinho" />
      <main className="mx-auto max-w-5xl space-y-4 p-4">
        <label className="block">
          <span className="mb-2 block font-bold">Unidade</span>
          <select value={unidade} onChange={(e) => setUnidade(e.target.value)}
            className="h-14 w-full rounded-2xl border-2 border-linha bg-white px-4 font-semibold outline-none focus:border-roxo-600">
            <option value="">Todas as unidades</option>
            {unidades.map((u) => <option key={u.id} value={u.id}>{u.nome}</option>)}
          </select>
        </label>

        {erro && <p className="rounded-2xl bg-amber-50 p-4 text-amber-900">Sem conexão com o servidor. Tentando de novo…</p>}

        {fichas.length === 0 ? (
          <div className="rounded-3xl bg-white p-10 text-center text-suave shadow-sm">
            <Inbox className="mx-auto mb-3 size-12 text-roxo-300" />
            <p className="font-semibold text-tinta">Nenhuma ficha recebida</p>
            <p>As fichas aparecem aqui quando o ACS tiver sinal.</p>
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2">
            {fichas.map((f) => <Ficha key={f.id} f={f} />)}
          </div>
        )}

        <button type="button" onClick={reiniciar}
          className="mx-auto flex min-h-11 items-center gap-2 px-4 text-sm font-semibold text-suave">
          <RotateCcw className="size-4" /> Reiniciar demonstração
        </button>
      </main>
    </div>
  );
}
