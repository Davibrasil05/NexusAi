import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import Topo from "./componentes/Topo";
import TelaInicio from "./componentes/TelaInicio";
import TelaConversa from "./componentes/TelaConversa";
import TelaResultado from "./componentes/TelaResultado";
import TelaEnviado from "./componentes/TelaEnviado";
import PainelUnidade from "./componentes/PainelUnidade";
import { RaciocinioGaveta, RaciocinioLateral } from "./componentes/Raciocinio";

// A comunidade do ACS quase nunca muda: lembra a última (só neste aparelho).
const lerComunidade = () => {
  try { return localStorage.getItem("comunidade") || ""; } catch { return ""; }
};
const INICIO = { comunidade: "", idade: "", foto: null };

function useRota() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const f = () => setHash(window.location.hash);
    window.addEventListener("hashchange", f);
    return () => window.removeEventListener("hashchange", f);
  }, []);
  return hash;
}

export default function App() {
  const rota = useRota();
  const [config, setConfig] = useState(null);
  const [sinal, setSinal] = useState({ ligado: false, na_fila: 0 });
  const [tela, setTela] = useState("inicio"); // inicio | conversa | resultado | enviado
  const [dados, setDados] = useState(() => ({ ...INICIO, comunidade: lerComunidade() }));
  const [caso, setCaso] = useState(null);
  const [ficha, setFicha] = useState(null);
  const [pendente, setPendente] = useState(null);
  const [ocupado, setOcupado] = useState(false);
  const [gaveta, setGaveta] = useState(false);
  const [aviso, setAviso] = useState(null);

  const avisar = useCallback((msg) => {
    setAviso(msg);
    setTimeout(() => setAviso(null), 3500);
  }, []);

  useEffect(() => {
    api.config().then(setConfig).catch(() => avisar("Não encontrei o servidor do agente. Ele está ligado?"));
    api.sinal().then(setSinal).catch(() => {});
  }, [avisar]);

  if (rota === "#/painel") return <PainelUnidade unidades={config?.unidades ?? []} />;

  async function trocarSinal() {
    try {
      const r = await api.mudarSinal(!sinal.ligado);
      setSinal({ ligado: r.ligado, na_fila: r.na_fila });
      // A tela "Ficha guardada" está aberta e o sinal voltou: busca a ficha já enviada (com a chegada prevista).
      if (r.ligado && ficha?.status === "na_fila") {
        const enviada = (await api.fichas()).find((f) => f.id === ficha.id);
        if (enviada) setFicha(enviada);
      }
      avisar(r.ligado
        ? r.enviadas_agora ? `Sinal voltou: ${r.enviadas_agora} ficha(s) enviada(s)` : "Com sinal"
        : "Sem sinal: as fichas ficam guardadas no celular");
    } catch (e) {
      avisar(e.message);
    }
  }

  async function comecar() {
    setOcupado(true);
    try {
      const idade = dados.idade === "" ? null : Number(dados.idade);
      try { localStorage.setItem("comunidade", dados.comunidade.trim()); } catch { /* sem armazenamento: tudo bem */ }
      let novo = await api.abrirCaso(dados.comunidade.trim(), idade);
      if (dados.foto) novo = await api.foto(novo.id, dados.foto).catch(() => novo);
      setCaso(novo);
      setTela("conversa");
    } catch (e) {
      avisar(e.message);
    } finally {
      setOcupado(false);
    }
  }

  async function enviar(texto) {
    setPendente(texto);
    setOcupado(true);
    try {
      const atualizado = await api.responder(caso.id, texto);
      setCaso(atualizado);
      if (atualizado.status !== "coletando") setTela("resultado");
    } catch (e) {
      avisar(`Não consegui falar com o agente: ${e.message}`);
    } finally {
      setPendente(null);
      setOcupado(false);
    }
  }

  async function confirmar() {
    setOcupado(true);
    try {
      const r = await api.confirmar(caso.id);
      setCaso(r.caso);
      setFicha(r.ficha);
      setTela("enviado");
      api.sinal().then(setSinal).catch(() => {});
    } catch (e) {
      avisar(e.message);
    } finally {
      setOcupado(false);
    }
  }

  function recomecar(perguntar = true) {
    if (perguntar && !confirm("Cancelar este atendimento?")) return;
    setCaso(null);
    setFicha(null);
    setDados({ ...INICIO, comunidade: dados.comunidade });
    setTela("inicio");
  }

  const subtitulo = {
    inicio: "Mancha roxa (hematoma) · funciona sem internet",
    conversa: `${dados.comunidade}${dados.idade !== "" ? ` · ${dados.idade} anos` : ""}`,
    resultado: "Resultado da triagem",
    enviado: "Ficha do atendimento",
  }[tela];

  return (
    <div className="lg:grid lg:min-h-dvh lg:grid-cols-[minmax(380px,430px)_minmax(360px,520px)] lg:justify-center lg:gap-7 lg:p-6">
      <div className="mx-auto flex h-dvh max-w-[480px] flex-col bg-fundo lg:h-[calc(100dvh-48px)] lg:w-full lg:overflow-hidden lg:rounded-[2.2rem] lg:border-[10px] lg:border-tinta lg:shadow-2xl lg:shadow-roxo-900/25">
        <Topo
          subtitulo={subtitulo}
          sinal={sinal}
          onSinal={trocarSinal}
          onVoltar={tela === "conversa" || tela === "resultado" ? () => recomecar() : undefined}
        />
        {tela === "inicio" && (
          <TelaInicio comunidades={config?.comunidades ?? []} dados={dados} setDados={setDados}
            onComecar={comecar} ocupado={ocupado} onErro={avisar} />
        )}
        {tela === "conversa" && caso && (
          <TelaConversa caso={caso} pendente={pendente} pensando={ocupado} onEnviar={enviar}
            onAbrirRaciocinio={() => setGaveta(true)} />
        )}
        {tela === "resultado" && caso && (
          <TelaResultado caso={caso} ocupado={ocupado} onConfirmar={confirmar}
            onCancelar={() => recomecar()} onAbrirRaciocinio={() => setGaveta(true)} />
        )}
        {tela === "enviado" && ficha && <TelaEnviado ficha={ficha} onNovo={() => recomecar(false)} />}
      </div>

      <RaciocinioLateral passos={caso?.passos ?? []} />
      <RaciocinioGaveta aberta={gaveta} onFechar={() => setGaveta(false)} passos={caso?.passos ?? []} />

      {aviso && (
        <div role="alert"
          className="animate-subir fixed inset-x-4 bottom-28 z-40 mx-auto max-w-md rounded-2xl bg-tinta px-4 py-3.5 text-base text-white shadow-xl">
          {aviso}
        </div>
      )}
    </div>
  );
}
