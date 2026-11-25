"""
Nós do fluxo de auditoria para LangGraph
Cada nó é uma função que recebe o state e retorna um dict com atualizações
"""
import streamlit as st
from typing import Dict, Any, TypedDict
from .config import llm
from .tools import (
    load_all_files,
    parse_date,
    get_weekday_name,
    calculate_vigency_year,
    extract_digits_from_prizes,
    compare_combinations
)
from .prompts import (
    SYSTEM_PROMPT,
    EXTRACT_CG_RULES_PROMPT,
    ANALYZE_DATE_PROMPT,
    ANALYZE_COMBINATION_PROMPT,
    ANALYZE_MULTIPLIER_PROMPT,
    GENERATE_REPORT_PROMPT
)


class AuditState(TypedDict):
    """Estado do processo de auditoria - suporta múltiplos sorteios com CGs diferentes"""
    # Inputs
    excel_path: str
    lottery_path: str
    
    # Dados extraídos
    excel_data: list[Dict[str, Any]]  # Lista de sorteios
    total_draws: int  # Número total de sorteios
    current_draw_index: int  # Índice do sorteio sendo processado (0-based)
    cg_contents: list[str]  # Lista de CGs (uma por sorteio, pode ter SUSEP diferente)
    lottery_content: str
    lottery_prizes: Dict[str, str]
    
    # Análises (uma por sorteio)
    cg_rules_list: list[str]  # Lista de regras extraídas (uma por sorteio)
    date_analyses: list[str]  # Uma análise por sorteio
    combination_analyses: list[str]  # Uma análise por sorteio
    multiplier_analyses: list[str]  # Uma análise por sorteio
    
    # Output
    final_report: str
    errors: list
    success: bool





def load_files_node(state: AuditState) -> Dict[str, Any]:
    """
    Nó 1: Carregar Excel, Loteria e buscar CG do banco.
    Carrega TODOS os sorteios do Excel de uma vez.
    """
    st.info("📂 Carregando arquivos...")
    
    with st.spinner("Processando arquivos..."):
        result = load_all_files(
            state["excel_path"],
            state["lottery_path"]
        )
    
    if not result["success"]:
        st.error(f"❌ Erro ao carregar arquivos: {', '.join(result['errors'])}")
        return {
            "errors": result["errors"],
            "success": False
        }
    
    # Exibir informação sobre sorteios
    total_draws = result["total_draws"]
    
    # Verificar quantos códigos SUSEP únicos existem
    susep_codes = set(draw.get("numero_susep") for draw in result["excel_data"])
    
    st.success(f"✅ Arquivos carregados | {total_draws} sorteio(s) | {len(susep_codes)} código(s) SUSEP único(s)")
    
    return {
        "excel_data": result["excel_data"],
        "total_draws": result["total_draws"],
        "current_draw_index": 0,  # Começar no primeiro sorteio
        "cg_contents": [],  # Será preenchido durante extract_rules
        "lottery_content": result["lottery_content"],
        "lottery_prizes": result["lottery_prizes"],
        "cg_rules_list": [],  # Inicializar lista vazia
        "date_analyses": [],
        "combination_analyses": [],
        "multiplier_analyses": [],
        "errors": [],
        "success": True
    }


def extract_rules_node(state: AuditState) -> Dict[str, Any]:
    """
    Nó 2: Extrair regras das Condições Gerais do sorteio ATUAL.
    Busca a CG específica para o código SUSEP do sorteio atual.
    """
    current_index = state["current_draw_index"]
    total = state["total_draws"]
    current_draw = state["excel_data"][current_index]
    codigo_susep = current_draw.get("numero_susep")
    
    st.info(f"📋 Extraindo regras das CG [{current_index + 1}/{total}] - SUSEP: {codigo_susep}...")
    
    with st.spinner(f"Buscando CG e analisando com Azure OpenAI..."):
        # Buscar CG do banco de dados para este sorteio específico
        from .tools import get_cg_by_susep
        
        cg_content = get_cg_by_susep(codigo_susep)
        
        if not cg_content:
            error_msg = f"CG não encontrada para código SUSEP {codigo_susep} (sorteio {current_index + 1})"
            st.error(f"❌ {error_msg}")
            return {
                "errors": state.get("errors", []) + [error_msg],
                "success": False
            }
        
        # Adicionar CG à lista
        cg_contents = state.get("cg_contents", []).copy()
        cg_contents.append(cg_content)
        
        # Extrair regras com LLM
        prompt = EXTRACT_CG_RULES_PROMPT.format(
            cg_content=cg_content[:10000]  # Limitar tamanho
        )
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        response = llm.invoke(messages)
        cg_rules = response.content
        
        # Adicionar regras à lista
        cg_rules_list = state.get("cg_rules_list", []).copy()
        cg_rules_list.append(cg_rules)
    
    st.success(f"✅ Regras extraídas das CG [{current_index + 1}/{total}] - SUSEP: {codigo_susep}")
    
    return {
        "cg_contents": cg_contents,
        "cg_rules_list": cg_rules_list
    }


def analyze_date_node(state: AuditState) -> Dict[str, Any]:
    """
    Nó 3: Analisar data do sorteio ATUAL (um por vez, sequencial).
    """
    current_index = state["current_draw_index"]
    total = state["total_draws"]
    current_draw = state["excel_data"][current_index]
    
    st.info(f"📅 Analisando data do sorteio [{current_index + 1}/{total}]...")
    
    with st.spinner(f"Verificando periodicidade do sorteio {current_index + 1}..."):
        excel_data = current_draw  # Processar apenas o sorteio atual
        
        # Parsear datas
        draw_date = parse_date(excel_data["data_sorteio"])
        start_date = parse_date(excel_data["inicio_vigencia"])
        
        if not draw_date or not start_date:
            return {
                "date_analysis": "❌ Erro: Não foi possível parsear as datas",
                "errors": state.get("errors", []) + ["Erro ao parsear datas"]
            }
        
        # Calcular informações
        weekday = get_weekday_name(draw_date)
        vigency_year = calculate_vigency_year(draw_date, start_date)
        
        # Preparar contexto para LLM
        date_context = f"""
        Data do Sorteio: {draw_date.strftime('%Y-%m-%d')} ({weekday})
        Início de Vigência: {start_date.strftime('%Y-%m-%d')}
        Ano de Vigência: {vigency_year}º ano
        """
        
        # Consultar LLM usando as regras específicas deste sorteio
        # Usar as regras do sorteio atual
        current_cg_rules = state["cg_rules_list"][current_index] if current_index < len(state["cg_rules_list"]) else ""
        
        prompt = ANALYZE_DATE_PROMPT.format(
            date_context=date_context,
            cg_rules=current_cg_rules
        )
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        response = llm.invoke(messages)
        date_analysis = response.content
    
    st.success(f"✅ Análise de data concluída [{current_index + 1}/{total}]")
    
    # Adicionar análise à lista
    date_analyses = state.get("date_analyses", []).copy()
    date_analyses.append(date_analysis)
    
    return {
        "date_analyses": date_analyses
    }


def analyze_combination_node(state: AuditState) -> Dict[str, Any]:
    """
    Nó 4: Analisar combinação sorteada do sorteio ATUAL (um por vez).
    """
    current_index = state["current_draw_index"]
    total = state["total_draws"]
    current_draw = state["excel_data"][current_index]
    
    st.info(f"🎲 Analisando combinação sorteada [{current_index + 1}/{total}]...")
    
    with st.spinner(f"Verificando combinação do sorteio {current_index + 1}..."):
        excel_data = current_draw
        lottery_prizes = state["lottery_prizes"]
        
        # Extrair combinação registrada
        registered_combination = excel_data["combinacao_sorteada"]
        
        # Calcular combinação a partir da loteria
        calculated_combination = extract_digits_from_prizes(lottery_prizes, method="top_to_bottom")
        
        # Comparar
        matches = compare_combinations(registered_combination, calculated_combination)
        
        # Preparar contexto
        combination_context = f"""
        Combinação Registrada: {registered_combination}
        Combinação Calculada (Loteria Federal): {calculated_combination}
        Prêmios da Loteria: {lottery_prizes}
        Match: {'✅ SIM' if matches else '❌ NÃO'}
        """
        
        # Consultar LLM usando as regras específicas deste sorteio
        # Usar as regras do sorteio atual
        current_cg_rules = state["cg_rules_list"][current_index] if current_index < len(state["cg_rules_list"]) else ""
        
        prompt = ANALYZE_COMBINATION_PROMPT.format(
            combination_context=combination_context,
            cg_rules=current_cg_rules
        )
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        response = llm.invoke(messages)
        combination_analysis = response.content
    
    st.success(f"✅ Análise de combinação concluída [{current_index + 1}/{total}]")
    
    # Adicionar análise à lista
    combination_analyses = state.get("combination_analyses", []).copy()
    combination_analyses.append(combination_analysis)
    
    return {
        "combination_analyses": combination_analyses
    }


def analyze_multiplier_node(state: AuditState) -> Dict[str, Any]:
    """
    Nó 5: Analisar multiplicador do sorteio ATUAL (um por vez).
    """
    current_index = state["current_draw_index"]
    total = state["total_draws"]
    current_draw = state["excel_data"][current_index]
    
    st.info(f"✖️ Analisando multiplicador [{current_index + 1}/{total}]...")
    
    with st.spinner(f"Verificando multiplicador do sorteio {current_index + 1}..."):
        excel_data = current_draw
        
        multiplier = excel_data["multiplicador"]
        
        # Preparar contexto
        multiplier_context = f"""
        Multiplicador Registrado: {multiplier}
        Plano: {excel_data["plano"]}
        Número SUSEP: {excel_data["numero_susep"]}
        """
        
        # Consultar LLM usando as regras específicas deste sorteio
        # Usar as regras do sorteio atual
        current_cg_rules = state["cg_rules_list"][current_index] if current_index < len(state["cg_rules_list"]) else ""
        
        prompt = ANALYZE_MULTIPLIER_PROMPT.format(
            multiplier_context=multiplier_context,
            cg_rules=current_cg_rules
        )
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        response = llm.invoke(messages)
        multiplier_analysis = response.content
    
    st.success(f"✅ Análise de multiplicador concluída [{current_index + 1}/{total}]")
    
    # Adicionar análise à lista
    multiplier_analyses = state.get("multiplier_analyses", []).copy()
    multiplier_analyses.append(multiplier_analysis)
    
    # Avançar para próximo sorteio
    next_index = current_index + 1
    
    return {
        "multiplier_analyses": multiplier_analyses,
        "current_draw_index": next_index
    }


def generate_report_node(state: AuditState) -> Dict[str, Any]:
    """
    Nó 6: Gerar relatório final consolidado com TODOS os sorteios analisados.
    """
    st.info("📊 Gerando relatório final consolidado...")
    
    total_draws = state["total_draws"]
    
    with st.spinner(f"Consolidando {total_draws} análise(s)..."):
        # Preparar contexto consolidado com TODAS as análises
        analyses_by_draw = []
        
        for i in range(total_draws):
            draw_data = state["excel_data"][i]
            cg_rules = state["cg_rules_list"][i] if i < len(state["cg_rules_list"]) else "N/A"
            date_analysis = state["date_analyses"][i] if i < len(state["date_analyses"]) else "N/A"
            combination_analysis = state["combination_analyses"][i] if i < len(state["combination_analyses"]) else "N/A"
            multiplier_analysis = state["multiplier_analyses"][i] if i < len(state["multiplier_analyses"]) else "N/A"
            
            analysis_section = f"""
### Sorteio {i + 1}/{total_draws}
**Dados:**
- Data: {draw_data.get('data_sorteio')}
- Série: {draw_data.get('serie')}
- Título: {draw_data.get('titulo')}
- Código SUSEP: {draw_data.get('numero_susep')}
- Combinação: {draw_data.get('combinacao_sorteada')}
- Multiplicador: {draw_data.get('multiplicador')}

**Regras das Condições Gerais (SUSEP: {draw_data.get('numero_susep')}):**
{cg_rules}

**Análise de Data:**
{date_analysis}

**Análise de Combinação:**
{combination_analysis}

**Análise de Multiplicador:**
{multiplier_analysis}

---
"""
            analyses_by_draw.append(analysis_section)
        
        full_context = f"""
## Análises por Sorteio ({total_draws} sorteio(s))

{''.join(analyses_by_draw)}
"""
        
        # Gerar relatório final
        prompt = GENERATE_REPORT_PROMPT.format(
            full_context=full_context,
            excel_data=f"{total_draws} sorteio(s) analisados"
        )
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        response = llm.invoke(messages)
        final_report = response.content
    
    st.success(f"✅ Relatório consolidado gerado com sucesso! ({total_draws} sorteio(s))")
    
    return {
        "final_report": final_report,
        "success": True
    }
