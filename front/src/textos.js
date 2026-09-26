// Tudo o que é texto fixo ou mapeamento de nomes técnicos -> linguagem do ACS.

export const NIVEL = {
  vermelho: { nome: "Emergência", acao: "Encaminhar agora", fundo: "bg-red-700", texto: "text-white", faixa: "bg-red-700", cor: "text-red-700" },
  laranja: { nome: "Muito urgente", acao: "Encaminhar com prioridade", fundo: "bg-orange-600", texto: "text-white", faixa: "bg-orange-600", cor: "text-orange-700" },
  amarelo: { nome: "Urgente", acao: "Levar à unidade de saúde", fundo: "bg-amber-400", texto: "text-amber-950", faixa: "bg-amber-400", cor: "text-amber-700" },
  verde: { nome: "Pouco urgente", acao: "Pode cuidar em casa", fundo: "bg-green-700", texto: "text-white", faixa: "bg-green-700", cor: "text-green-700" },
};

const SIM_NAO = ["Sim", "Não", "Não sei"];
const CHIPS = {
  pancada: ["Teve pancada ou queda", "Apareceu sozinha"],
  local: ["Cabeça", "Peito", "Barriga", "Braço", "Perna"],
  mecanismo: ["Queda de altura", "Acidente de barco", "Acidente de moto", "Pancada leve"],
};
export const respostasRapidas = (campo) => (campo ? CHIPS[campo] ?? SIM_NAO : []);

export const CAMPOS = {
  pancada: "se teve pancada",
  local: "local do roxo",
  mecanismo: "como foi a pancada",
  sinais_cabeca: "vômito, sono ou confusão",
  dor_forte_ou_falta_ar: "dor forte ou falta de ar",
  deformidade: "braço/perna torto ou frio",
  mexe_apoia: "se mexe e apoia",
  crescendo_ou_sangrando: "roxo crescendo ou sangrando",
  febre: "febre",
  sangramento_mucosa: "sangramento na gengiva, nariz ou urina",
  petequias: "pontinhos vermelhos",
  picada_cobra: "picada de cobra",
  cansaco_palidez: "cansaço ou palidez",
  anticoagulante: "remédio que afina o sangue",
};

export const QUEM = {
  llm: { nome: "IA local", borda: "border-roxo-600", tag: "bg-roxo-600" },
  codigo: { nome: "Regra", borda: "border-cyan-700", tag: "bg-cyan-700" },
  rag: { nome: "Protocolo", borda: "border-green-700", tag: "bg-green-700" },
  guardrail: { nome: "Proteção", borda: "border-amber-600", tag: "bg-amber-600" },
  pessoa: { nome: "ACS", borda: "border-stone-500", tag: "bg-stone-500" },
};

export const PASSOS = {
  abrir_caso: "ACS abriu o atendimento",
  pergunta_padrao: "Pergunta padrão",
  perguntar: "Escolheu como perguntar",
  atualizar_caso: "Entendeu a resposta",
  validar_json: "Resposta do modelo recusada",
  validar_campos: "Valor inválido descartado",
  fallback_palavras: "Plano B: palavras-chave",
  complemento_palavras: "Completou por palavras-chave",
  conflito_pancada: "Dúvida sobre pancada: pergunta de novo",
  nao_baixa_risco: "Bloqueou baixar o risco",
  rede_seguranca: "Rede de segurança achou alerta",
  pior_cenario: "Assumiu o pior cenário",
  avaliar_risco: "Avaliou o risco",
  buscar_unidades: "Escolheu o destino",
  buscar_protocolo: "Buscou no protocolo",
  escrever_orientacao: "Escreveu a orientação",
  verificador: "Conferiu a orientação",
  anexar_foto: "Foto anexada",
  confirmar: "ACS confirmou",
  gerar_ficha: "Gerou a ficha",
};

export const minutos = (m) => {
  if (m == null) return "";
  const h = Math.floor(m / 60);
  const r = m % 60;
  if (!h) return `${r} min`;
  return r ? `${h}h${String(r).padStart(2, "0")}` : `${h}h`;
};

export const hora = (iso) =>
  iso ? new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "";
