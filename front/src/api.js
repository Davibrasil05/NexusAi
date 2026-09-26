// Mesma origem da API (o build é servido pela FastAPI em /web/). No dev, o Vite repassa /api.
async function chamar(caminho, { metodo = "GET", corpo } = {}) {
  const resp = await fetch(caminho, {
    method: metodo,
    headers: corpo ? { "Content-Type": "application/json" } : undefined,
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  const dados = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(dados.detail || `Erro ${resp.status}`);
  return dados;
}

export const api = {
  config: () => chamar("/api/config"),
  abrirCaso: (comunidade, idade) => chamar("/api/casos", { metodo: "POST", corpo: { comunidade, idade } }),
  responder: (id, texto) => chamar(`/api/casos/${id}/mensagens`, { metodo: "POST", corpo: { texto } }),
  foto: (id, imagem) => chamar(`/api/casos/${id}/foto`, { metodo: "POST", corpo: { imagem } }),
  confirmar: (id) => chamar(`/api/casos/${id}/confirmar`, { metodo: "POST" }),
  sinal: () => chamar("/api/sinal"),
  mudarSinal: (ligado) => chamar("/api/sinal", { metodo: "POST", corpo: { ligado } }),
  fichas: (unidade) => chamar(`/api/fichas?status=enviada${unidade ? `&unidade=${unidade}` : ""}`),
  reiniciar: () => chamar("/api/reiniciar", { metodo: "POST" }),
};

// Reduz a foto no próprio celular (máx. 1280 px, JPEG) antes de enviar.
export function reduzirFoto(arquivo, lado = 1280) {
  return new Promise((ok, erro) => {
    const img = new Image();
    img.onload = () => {
      const escala = Math.min(1, lado / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(img.width * escala);
      canvas.height = Math.round(img.height * escala);
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(img.src);
      ok(canvas.toDataURL("image/jpeg", 0.8));
    };
    img.onerror = () => erro(new Error("Não consegui abrir a foto"));
    img.src = URL.createObjectURL(arquivo);
  });
}
