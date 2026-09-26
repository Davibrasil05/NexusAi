"""gerar_ficha + fila offline (SQLite local).

Sem sinal, a ficha fica 'na_fila' no aparelho do ACS. Ao ligar o sinal, tudo o que está na fila
vai para 'enviada' e aparece no painel da unidade. O SINAL É SIMULADO (botão); o modelo é real.
"""
import json
import sqlite3
import threading
from datetime import datetime, timedelta

from app.config import DADOS
from app.modelos import Caso

BANCO = DADOS / "fichas.db"
_trava = threading.Lock()
_sinal = {"ligado": False}

_con = sqlite3.connect(BANCO, check_same_thread=False)
_con.row_factory = sqlite3.Row
_con.execute("""
CREATE TABLE IF NOT EXISTS fichas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caso_id TEXT UNIQUE NOT NULL,
    criada_em TEXT NOT NULL,
    status TEXT NOT NULL,          -- na_fila | enviada
    enviada_em TEXT,
    cor TEXT NOT NULL,
    tempo_barco_min INTEGER,
    dados TEXT NOT NULL            -- JSON com o resumo do caso
)""")
_con.commit()


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _linha(r: sqlite3.Row) -> dict:
    f = {k: r[k] for k in ("id", "caso_id", "criada_em", "status", "enviada_em", "cor", "tempo_barco_min")}
    f.update(json.loads(r["dados"]))
    f["chegada_prevista"] = None
    if r["enviada_em"] and r["tempo_barco_min"] is not None:
        f["chegada_prevista"] = (datetime.fromisoformat(r["enviada_em"])
                                 + timedelta(minutes=r["tempo_barco_min"])).isoformat(timespec="minutes")
    return f


def gerar_ficha(caso: Caso) -> dict:
    cls, dest, ori = caso.classificacao, caso.destino, caso.orientacao
    dados = {
        "idade": caso.idade,
        "comunidade": caso.comunidade,
        "motivos": cls.motivos,
        "assumidos": caso.assumidos,
        "campos": caso.campos.model_dump(exclude_none=True),
        "em_casa": bool(dest and dest.em_casa),
        "destino_id": dest.unidade_id if dest else None,
        "destino_nome": dest.nome if dest else None,
        "destino_explicacao": dest.explicacao if dest else None,
        "orientacao_status": ori.status if ori else None,
        "foto": caso.foto,
    }
    status = "enviada" if _sinal["ligado"] else "na_fila"
    with _trava:
        cur = _con.execute(
            "INSERT INTO fichas (caso_id, criada_em, status, enviada_em, cor, tempo_barco_min, dados) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (caso.id, _agora(), status, _agora() if status == "enviada" else None, cls.cor,
             dest.tempo_barco_min if dest else None, json.dumps(dados, ensure_ascii=False)))
        _con.commit()
        return _linha(_con.execute("SELECT * FROM fichas WHERE id = ?", (cur.lastrowid,)).fetchone())


def listar(status: str | None = None) -> list[dict]:
    ordem = "CASE cor WHEN 'vermelho' THEN 0 WHEN 'laranja' THEN 1 WHEN 'amarelo' THEN 2 ELSE 3 END, criada_em DESC"
    with _trava:
        if status:
            linhas = _con.execute(f"SELECT * FROM fichas WHERE status = ? ORDER BY {ordem}", (status,)).fetchall()
        else:
            linhas = _con.execute(f"SELECT * FROM fichas ORDER BY {ordem}").fetchall()
    return [_linha(r) for r in linhas]


def sinal_ligado() -> bool:
    return _sinal["ligado"]


def definir_sinal(ligado: bool) -> int:
    """Liga/desliga o sinal. Ao ligar, envia a fila. Devolve quantas fichas foram enviadas agora."""
    _sinal["ligado"] = ligado
    if not ligado:
        return 0
    with _trava:
        cur = _con.execute("UPDATE fichas SET status = 'enviada', enviada_em = ? WHERE status = 'na_fila'", (_agora(),))
        _con.commit()
        return cur.rowcount


def limpar() -> None:
    """Apaga todas as fichas (para recomeçar a demo)."""
    with _trava:
        _con.execute("DELETE FROM fichas")
        _con.commit()
