"""
Construção do grafo LangGraph para auditoria de sorteios
"""
from langgraph.graph import StateGraph, END
from .nodes import (
    AuditState,
    load_files_node,
    extract_rules_node,
    analyze_date_node,
    analyze_combination_node,
    analyze_multiplier_node,
    generate_report_node
)


def should_continue(state: AuditState) -> str:
    """
    Função condicional para decidir se deve continuar o fluxo
    """
    if not state.get("success", True):
        return "end"
    
    if state.get("errors") and len(state["errors"]) > 0:
        return "end"
    
    return "continue"


def should_process_next_draw(state: AuditState) -> str:
    """
    Decide se deve processar mais um sorteio ou gerar relatório final.
    Chamada após analyze_multiplier_node que incrementa current_draw_index.
    """
    current_index = state.get("current_draw_index", 0)
    total_draws = state.get("total_draws", 0)
    
    # Se ainda há sorteios para processar, volta para analyze_date
    if current_index < total_draws:
        return "next_draw"
    
    # Se todos foram processados, vai para relatório
    return "generate_report"


def create_audit_graph():
    """
    Cria e compila o grafo de auditoria com loop para múltiplos sorteios.
    Cada sorteio pode ter código SUSEP diferente e CG diferente.
    
    Fluxo:
    1. load_files -> Carrega todos os arquivos e lista de sorteios
    2. LOOP por cada sorteio:
       - extract_rules -> Busca e extrai regras da CG específica (por SUSEP)
       - analyze_date -> Analisa data do sorteio atual
       - analyze_combination -> Analisa combinação do sorteio atual
       - analyze_multiplier -> Analisa multiplicador do sorteio atual
       - Volta para extract_rules se houver mais sorteios
    3. generate_report -> Gera relatório consolidado com todos os sorteios
    """
    
    # Criar o grafo com o estado tipado
    workflow = StateGraph(AuditState)
    
    # Adicionar nós
    workflow.add_node("load_files", load_files_node)
    workflow.add_node("extract_rules", extract_rules_node)
    workflow.add_node("analyze_date", analyze_date_node)
    workflow.add_node("analyze_combination", analyze_combination_node)
    workflow.add_node("analyze_multiplier", analyze_multiplier_node)
    workflow.add_node("generate_report", generate_report_node)
    
    # Definir ponto de entrada
    workflow.set_entry_point("load_files")
    
    # Definir fluxo com verificação de erros após carregar arquivos
    workflow.add_conditional_edges(
        "load_files",
        should_continue,
        {
            "continue": "extract_rules",
            "end": END
        }
    )
    
    # Após extrair regras, vai para análise de data do mesmo sorteio
    workflow.add_edge("extract_rules", "analyze_date")
    
    # Fluxo linear dentro de cada sorteio
    workflow.add_edge("analyze_date", "analyze_combination")
    workflow.add_edge("analyze_combination", "analyze_multiplier")
    
    # Após multiplicador, decide: próximo sorteio OU relatório final
    workflow.add_conditional_edges(
        "analyze_multiplier",
        should_process_next_draw,
        {
            "next_draw": "extract_rules",  # Loop de volta para buscar próxima CG
            "generate_report": "generate_report"  # Finalizar
        }
    )
    
    # Fim após relatório
    workflow.add_edge("generate_report", END)
    
    # Compilar o grafo
    app = workflow.compile()
    
    return app


# Instância global do grafo compilado
audit_graph = create_audit_graph()
