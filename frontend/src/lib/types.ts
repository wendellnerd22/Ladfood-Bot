// Interfaces espelham os modelos Pydantic em backend/models/schemas.py e as
// respostas da API LAD v1. Mantenha os dois lados em sincronia na mesma edição.

export interface Store {
  id: string;
  nome: string;
  token: string;
  demo: boolean;
  bot_prompt: string;
  conexao_ok: boolean;
  conexao_msg: string;
  created_at: string;
}

export interface StoreCreate {
  nome: string;
  token: string;
  demo: boolean;
  bot_prompt: string;
}

export interface ConnectionResult {
  ok: boolean;
  mensagem: string;
  nome_loja: string | null;
  aberta_agora: boolean | null;
}

export interface ToolTrace {
  name: string;
  ok: boolean;
  resumo: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  store_id: string;
  role: string;
  text: string;
  tools: ToolTrace[];
  created_at: string;
}

export interface ChatResponse {
  reply: string;
  tools: ToolTrace[];
  order_uuid: string | null;
}

export interface OrderRecord {
  id: string;
  store_id: string;
  session_id: string;
  cliente_nome: string;
  cliente_telefone: string;
  tipo: string;
  status_codigo: string;
  status_descricao: string;
  valor_total: number;
  data_pedido: string;
  demo: boolean;
  payload: Record<string, unknown>;
  created_at: string;
}

// ---- respostas cruas da API LAD v1 (proxy do backend) ----
export interface LojaHorario {
  diaDaSemana: number;
  diaDaSemanaLabel: string;
  abre: string;
  fecha: string;
}

export interface LojaInfo {
  id: number;
  nome: string;
  telefone: string | null;
  endereco: string | null;
  abertaAgora: boolean;
  horarios: LojaHorario[];
  pedidoMinimo: number;
  entregaDisponivel: boolean;
  retiradaDisponivel: boolean;
  formasPagamento: string[];
  mensagemRetirada: string | null;
  moeda: string;
}

export interface CardapioOpcao {
  id: number;
  nome: string;
  preco: number;
}

export interface CardapioGrupo {
  id: number;
  nome: string;
  minimo: number;
  maximo: number;
  regraPreco: string;
  opcoes: CardapioOpcao[];
}

export interface CardapioTamanho {
  id: number;
  nome: string;
  preco: number;
}

export interface CardapioProduto {
  id: number;
  nome: string;
  descricao: string | null;
  preco: number;
  precoOriginal: number | null;
  imagemUrl: string | null;
  tamanhos: CardapioTamanho[];
  gruposOpcionais: CardapioGrupo[];
}

export interface CardapioCategoria {
  id: number;
  nome: string;
  produtos: CardapioProduto[];
}

export interface Cardapio {
  idLoja: number;
  nomeLoja: string;
  lojaAbertaAgora: boolean;
  categorias: CardapioCategoria[];
  avisos: string[];
}

export const STATUS_LAD: Record<string, { label: string; className: string }> = {
  E: { label: "Pendente", className: "bg-[#3B2505] text-[#FDE68A] border-[#D97706]" },
  A: { label: "Autorizado", className: "bg-[#063047] text-[#BAE6FD] border-[#0284C7]" },
  V: { label: "Em preparo", className: "bg-[#371A45] text-[#F5D0FE] border-[#9333EA]" },
  X: { label: "Saiu p/ entrega", className: "bg-[#064E3B] text-[#A7F3D0] border-[#059669]" },
  D: { label: "Entregue", className: "bg-[#065F46] text-[#D1FAE5] border-[#10B981]" },
  P: { label: "Aguardando pagamento", className: "bg-[#451A03] text-[#FED7AA] border-[#EA580C]" },
  C: { label: "Cancelado", className: "bg-[#450A0A] text-[#FECACA] border-[#DC2626]" },
  R: { label: "Rejeitado", className: "bg-[#3F1515] text-[#FEE2E2] border-[#B91C1C]" },
};

export const brl = (v: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v || 0);
