export type KnowledgeFile = {
  id: string;
  name: string;
  status: "Nova" | "Editada" | "Lida";
  asset: string;
  date: string;
  confidence: number;
  priority: "Alta" | "Média" | "Baixa";
  content: string;
};

export const knowledgeFiles: KnowledgeFile[] = [
  {
    id: "k1",
    name: "Estrategia_SMC_Basica.md",
    status: "Lida",
    asset: "Metodologia",
    date: "2023-10-14",
    confidence: 95,
    priority: "Alta",
    content: "# Estratégia SMC Básica\n\n- Identificação de Order Blocks.\n- Mapeamento de Liquidez (Inducement).\n- Entradas no Fair Value Gap (FVG).\n\nO modelo tem 95% de confiança nas marcações de SMC.",
  },
  {
    id: "k2",
    name: "Analise_Volume_Wyckoff.md",
    status: "Editada",
    asset: "Contexto",
    date: "2023-11-02",
    confidence: 82,
    priority: "Média",
    content: "# Análise de Volume (Wyckoff)\n\n- Fases de Acumulação e Distribuição.\n- Identificação de Springs e Upthrusts.\n\nEditado recentemente para incluir novo padrão de absorção em M15.",
  },
  {
    id: "k3",
    name: "Logs_Stop_Loss_Novembro.md",
    status: "Nova",
    asset: "Memória",
    date: "2023-11-20",
    confidence: 65,
    priority: "Baixa",
    content: "# Aprendizados de Stop Loss (Nov)\n\n- O agente identificou falsos rompimentos em sessões asiáticas.\n- Sugestão: reduzir alavancagem em 50% após as 20h UTC.",
  },
];
