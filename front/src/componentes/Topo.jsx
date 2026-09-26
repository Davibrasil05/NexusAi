import { ChevronLeft, Wifi, WifiOff } from "lucide-react";

export default function Topo({ titulo = "Triagem ACS", subtitulo, onVoltar, sinal, onSinal }) {
  return (
    <header className="sticky top-0 z-10 flex items-center gap-3 bg-roxo-600 px-4 pb-4 pt-[max(14px,env(safe-area-inset-top))] text-white">
      {onVoltar && (
        <button
          type="button"
          onClick={onVoltar}
          aria-label="Voltar ao início"
          className="grid size-11 shrink-0 place-items-center rounded-full bg-white/15 active:bg-white/25"
        >
          <ChevronLeft className="size-6" strokeWidth={2.5} />
        </button>
      )}
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-xl font-bold tracking-tight">{titulo}</h1>
        {subtitulo && <p className="truncate text-sm text-white/80">{subtitulo}</p>}
      </div>
      {sinal && (
        <button
          type="button"
          onClick={onSinal}
          aria-live="polite"
          aria-label={sinal.ligado ? "Com sinal. Toque para desligar" : "Sem sinal. Toque para ligar"}
          className={`flex h-11 shrink-0 items-center gap-2 rounded-full px-3.5 text-sm font-semibold transition ${
            sinal.ligado ? "bg-white text-green-700" : "bg-white/15 text-white"
          }`}
        >
          {sinal.ligado ? <Wifi className="size-5" /> : <WifiOff className="size-5" />}
          {sinal.ligado ? "Com sinal" : "Sem sinal"}
          {sinal.na_fila > 0 && (
            <span className="rounded-full bg-amber-400 px-2 text-xs font-bold text-amber-950">{sinal.na_fila}</span>
          )}
        </button>
      )}
    </header>
  );
}
