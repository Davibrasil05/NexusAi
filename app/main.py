"""API do agente (FastAPI). Rodar:

    .venv/bin/uvicorn app.main:app --port 8000
    LLM_PROVEDOR=ollama .venv/bin/uvicorn app.main:app --port 8000

Contrato das rotas para o front: API.md.
As rotas são 'def' (não async): a chamada ao modelo bloqueia e roda no threadpool do FastAPI.
"""
import base64
import binascii
import re
import threading

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import fichas
from app.agente import Agente, CasoEncerrado
from app.config import FOTOS, WEB
from app.llm import criar_llm
from app.modelos import Caso, EstadoSinal, NovaFoto, NovaMensagem, NovoCaso
from app.unidades import carregar as carregar_unidades
from app.unidades import comunidades

MAX_FOTO_BYTES = 5 * 1024 * 1024
RE_DATA_URL = re.compile(r"^data:image/(jpeg|jpg|png|webp);base64,(.+)$", re.DOTALL)

app = FastAPI(title="Triagem de hematoma – ACS")
# Liberado para o front rodar em outro servidor local durante o desenvolvimento.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

llm = criar_llm()
agente = Agente(llm)
casos: dict[str, Caso] = {}
_trava_casos: dict[str, threading.Lock] = {}


def _caso(caso_id: str) -> Caso:
    if caso_id not in casos:
        raise HTTPException(404, f"caso {caso_id} não existe")
    return casos[caso_id]


# ---------- configuração ----------

@app.get("/api/config")
def config():
    unidades = [{"id": u["id"], "nome": u["nome"]} for u in carregar_unidades()["unidades"]]
    return {"llm": llm.nome, "comunidades": comunidades(), "unidades": unidades, "sinal": fichas.sinal_ligado()}


# ---------- caso (tela do ACS) ----------

@app.post("/api/casos", response_model=Caso)
def abrir_caso(dados: NovoCaso):
    if dados.comunidade not in comunidades():
        raise HTTPException(422, f"comunidade desconhecida; use uma de {comunidades()}")
    caso = agente.novo_caso(dados.comunidade, dados.idade)
    casos[caso.id] = caso
    _trava_casos[caso.id] = threading.Lock()
    return caso


@app.get("/api/casos/{caso_id}", response_model=Caso)
def ver_caso(caso_id: str):
    return _caso(caso_id)


@app.post("/api/casos/{caso_id}/mensagens", response_model=Caso)
def responder(caso_id: str, msg: NovaMensagem):
    caso = _caso(caso_id)
    with _trava_casos[caso_id]:  # evita duas respostas ao mesmo tempo no mesmo caso (duplo clique)
        try:
            return agente.responder(caso, msg.texto)
        except CasoEncerrado as e:
            raise HTTPException(409, str(e))


@app.post("/api/casos/{caso_id}/foto", response_model=Caso)
def anexar_foto(caso_id: str, foto: NovaFoto):
    caso = _caso(caso_id)
    m = RE_DATA_URL.match(foto.imagem)
    if not m:
        raise HTTPException(422, "envie um data URL: data:image/jpeg|png|webp;base64,...")
    try:
        conteudo = base64.b64decode(m.group(2), validate=True)
    except binascii.Error:
        raise HTTPException(422, "base64 inválido")
    if len(conteudo) > MAX_FOTO_BYTES:
        raise HTTPException(413, "foto maior que 5 MB")
    ext = "jpg" if m.group(1) in ("jpeg", "jpg") else m.group(1)
    (FOTOS / f"{caso.id}.{ext}").write_bytes(conteudo)
    caso.foto = f"/fotos/{caso.id}.{ext}"
    caso.registrar("anexar_foto", "pessoa", saida=caso.foto)
    return caso


@app.post("/api/casos/{caso_id}/confirmar")
def confirmar(caso_id: str):
    """O ACS revisou e confirma: gera a ficha e põe na fila (ou envia, se houver sinal)."""
    caso = _caso(caso_id)
    if caso.status == "coletando":
        raise HTTPException(409, "a coleta ainda não terminou")
    if caso.status == "confirmado":
        raise HTTPException(409, f"caso já confirmado (ficha {caso.ficha_id})")
    caso.registrar("confirmar", "pessoa")
    ficha = fichas.gerar_ficha(caso)
    caso.ficha_id, caso.status = ficha["id"], "confirmado"
    caso.registrar("gerar_ficha", "codigo", saida={"ficha": ficha["id"], "status": ficha["status"]})
    return {"caso": caso, "ficha": ficha}


# ---------- sinal e fila ----------

@app.get("/api/sinal")
def ver_sinal():
    return {"ligado": fichas.sinal_ligado(), "na_fila": len(fichas.listar("na_fila"))}


@app.post("/api/sinal")
def mudar_sinal(estado: EstadoSinal):
    enviadas = fichas.definir_sinal(estado.ligado)
    return {"ligado": estado.ligado, "enviadas_agora": enviadas, "na_fila": len(fichas.listar("na_fila"))}


# ---------- painel da unidade ----------

@app.get("/api/fichas")
def listar_fichas(status: str | None = None, unidade: str | None = None):
    """Painel da unidade: GET /api/fichas?status=enviada (&unidade=<id> para filtrar o destino)."""
    lista = fichas.listar(status)
    if unidade:
        lista = [f for f in lista if f["destino_id"] == unidade]
    return lista


@app.post("/api/reiniciar")
def reiniciar():
    """Zera casos, fichas e sinal (para recomeçar a demo)."""
    casos.clear()
    _trava_casos.clear()
    fichas.limpar()
    fichas.definir_sinal(False)
    for f in FOTOS.iterdir():
        if f.name != ".gitkeep":
            f.unlink()
    return {"ok": True}


# ---------- arquivos ----------

FOTOS.mkdir(parents=True, exist_ok=True)
app.mount("/fotos", StaticFiles(directory=FOTOS), name="fotos")
if WEB.exists():
    app.mount("/web", StaticFiles(directory=WEB, html=True), name="web")

    @app.get("/", include_in_schema=False)
    def inicio():
        return RedirectResponse("/web/")
