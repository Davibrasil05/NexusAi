import { useRef } from "react";
import { Camera, MapPin, Minus, Plus, Stethoscope, Trash2 } from "lucide-react";
import { reduzirFoto } from "../api";

export default function TelaInicio({ comunidades, dados, setDados, onComecar, ocupado, onErro }) {
  const inputFoto = useRef(null);
  const { comunidade, idade, foto } = dados;
  // Sugere as comunidades cadastradas enquanto o ACS digita (sem acento e sem maiúscula).
  const chave = (t) => t.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
  const digitado = chave(comunidade);
  const sugestoes = comunidades.filter((c) => chave(c) !== digitado && (!digitado || chave(c).includes(digitado)));
  const mudarIdade = (d) => setDados({ ...dados, idade: Math.max(0, Math.min(120, (Number(idade) || 0) + d)) });

  async function escolherFoto(e) {
    const arq = e.target.files?.[0];
    e.target.value = "";
    if (!arq) return;
    try {
      setDados({ ...dados, foto: await reduzirFoto(arq) });
    } catch (err) {
      onErro(err.message);
    }
  }

  return (
    <>
      <main className="flex-1 space-y-4 overflow-y-auto p-4">
        <section className="animate-subir rounded-3xl bg-gradient-to-br from-roxo-600 to-roxo-800 p-5 text-white shadow-lg shadow-roxo-900/20">
          <div className="mb-3 grid size-12 place-items-center rounded-2xl bg-white/15">
            <Stethoscope className="size-7" />
          </div>
          <h2 className="text-[26px] font-bold leading-tight tracking-tight">Novo atendimento</h2>
          <p className="mt-1 text-white/85">Conte o que aconteceu com a pessoa. O assistente faz algumas perguntas e mostra a gravidade, para onde levar e o que fazer.</p>
        </section>

        <section className="rounded-3xl bg-white p-5 shadow-sm">
          <label htmlFor="comunidade" className="mb-3 block font-bold">Comunidade da pessoa atendida</label>
          <div className="relative">
            <MapPin className="pointer-events-none absolute left-4 top-1/2 size-5 -translate-y-1/2 text-suave" />
            <input
              id="comunidade"
              type="text"
              autoComplete="off"
              enterKeyHint="done"
              placeholder="Escreva o nome da comunidade"
              value={comunidade}
              onChange={(e) => setDados({ ...dados, comunidade: e.target.value })}
              className="h-14 w-full rounded-2xl border-2 border-linha bg-white pl-12 pr-4 font-semibold outline-none placeholder:font-normal focus:border-roxo-600 focus:ring-4 focus:ring-roxo-100"
            />
          </div>
          {sugestoes.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {sugestoes.map((c) => (
                <button key={c} type="button" onClick={() => setDados({ ...dados, comunidade: c })}
                  className="min-h-11 rounded-full border-2 border-roxo-200 bg-roxo-50 px-4 text-[15px] font-semibold text-roxo-800 active:bg-roxo-100">
                  {c}
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-3xl bg-white p-5 shadow-sm">
          <label htmlFor="idade" className="mb-3 block font-bold">
            Idade <span className="font-normal text-suave">(se souber)</span>
          </label>
          <div className="flex items-center gap-3">
            <button type="button" aria-label="Diminuir idade" onClick={() => mudarIdade(-1)}
              className="grid size-14 place-items-center rounded-full border-2 border-roxo-200 text-roxo-700 active:bg-roxo-50">
              <Minus className="size-6" strokeWidth={3} />
            </button>
            <input
              id="idade"
              type="number"
              inputMode="numeric"
              min="0"
              max="120"
              placeholder="—"
              value={idade}
              onChange={(e) => setDados({ ...dados, idade: e.target.value })}
              className="h-14 w-28 rounded-2xl border-2 border-linha text-center text-2xl font-bold outline-none focus:border-roxo-600 focus:ring-4 focus:ring-roxo-100"
            />
            <button type="button" aria-label="Aumentar idade" onClick={() => mudarIdade(1)}
              className="grid size-14 place-items-center rounded-full border-2 border-roxo-200 text-roxo-700 active:bg-roxo-50">
              <Plus className="size-6" strokeWidth={3} />
            </button>
            <span className="text-suave">anos</span>
          </div>
        </section>

        <section className="rounded-3xl bg-white p-5 shadow-sm">
          <p className="mb-3 font-bold">
            Foto da mancha <span className="font-normal text-suave">(opcional)</span>
          </p>
          {foto ? (
            <div className="flex items-center gap-4">
              <img src={foto} alt="Foto da mancha roxa" className="size-20 rounded-2xl object-cover" />
              <button type="button" onClick={() => setDados({ ...dados, foto: null })}
                className="flex min-h-12 items-center gap-2 font-semibold text-roxo-700">
                <Trash2 className="size-5" /> Remover foto
              </button>
            </div>
          ) : (
            <button type="button" onClick={() => inputFoto.current.click()}
              className="flex min-h-14 w-full items-center justify-center gap-2.5 rounded-2xl border-2 border-dashed border-roxo-300 bg-roxo-50 font-bold text-roxo-700 active:bg-roxo-100">
              <Camera className="size-6" /> Tirar foto
            </button>
          )}
          <input ref={inputFoto} type="file" accept="image/*" capture="environment" onChange={escolherFoto} className="hidden" />
        </section>
      </main>

      <footer className="border-t border-linha bg-white p-4 pb-[max(16px,env(safe-area-inset-bottom))]">
        <button
          type="button"
          disabled={comunidade.trim().length < 2 || ocupado}
          onClick={onComecar}
          className="flex h-14 w-full items-center justify-center rounded-2xl bg-roxo-600 text-[19px] font-bold text-white shadow-lg shadow-roxo-600/25 transition active:bg-roxo-800 disabled:bg-roxo-200 disabled:shadow-none"
        >
          {ocupado ? "Abrindo…" : comunidade.trim().length >= 2 ? "Começar triagem" : "Escreva a comunidade"}
        </button>
      </footer>
    </>
  );
}
