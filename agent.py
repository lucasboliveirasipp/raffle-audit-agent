"""
Arquivo principal do sistema de auditoria de sorteios
Interface Streamlit + Integração com LangGraph
"""
import streamlit as st
import tempfile
import os
from uuid import uuid4
from typing import Dict, Any, Tuple
from .graph import audit_graph
from feedback_local import update_feedback
from feedback_local import log_interaction


def generate_interaction_ids() -> Tuple[str, str]:
    """
    Gera IDs únicos para thread_id e response_id usando UUID4
    
    Returns:
        Tuple[str, str]: (thread_id, response_id)
    """
    thread_id = str(uuid.uuid4())
    response_id = str(uuid.uuid4())
    return thread_id, response_id

def save_uploaded_file(uploaded_file) -> str:
    """
    Salva arquivo uploaded do Streamlit em arquivo temporário
    
    Args:
        uploaded_file: Arquivo do st.file_uploader
        
    Returns:
        Caminho do arquivo temporário
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        return tmp_file.name


def save_report_to_file(report: str, excel_data) -> str:
    """
    Salva relatório em arquivo PDF
    
    Args:
        report: Conteúdo do relatório
        excel_data: Dados da planilha (pode ser dict ou list de dicts)
    
    Returns:
        Nome do arquivo salvo
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor
    import re
    
    # Lidar com múltiplos sorteios (lista) ou sorteio único (dict)
    if isinstance(excel_data, list) and len(excel_data) > 0:
        # Usar o primeiro sorteio para o nome do arquivo
        numero_susep = excel_data[0].get("numero_susep", "MULTIPLOS")
        if len(excel_data) > 1:
            numero_susep = f"{numero_susep}_e_{len(excel_data)-1}_outros"
    elif isinstance(excel_data, dict):
        numero_susep = excel_data.get("numero_susep", "UNICO")
    else:
        numero_susep = "AUDITORIA"
    
    # Limpar caracteres especiais do nome do arquivo
    numero_susep_clean = str(numero_susep).replace("/", "_").replace(" ", "_")
    filename = f"relatorio_auditoria_{numero_susep_clean}.pdf"
    
    # Criar documento PDF
    doc = SimpleDocTemplate(filename, pagesize=A4, topMargin=0.8*inch, bottomMargin=0.8*inch)
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=HexColor('#1f77b4'),
        spaceAfter=12,
        alignment=1  # Center
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=HexColor('#333333'),
        spaceAfter=8
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    # Converter markdown para elementos PDF
    content = []
    lines = report.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            content.append(Spacer(1, 6))
            continue
            
        # Títulos principais (# )
        if line.startswith('# '):
            text = line[2:].strip()
            content.append(Paragraph(text, title_style))
            content.append(Spacer(1, 12))
            
        # Subtítulos (## )
        elif line.startswith('## '):
            text = line[3:].strip()
            content.append(Paragraph(text, heading_style))
            content.append(Spacer(1, 8))
            
        # Subtítulos menores (### )
        elif line.startswith('### '):
            text = line[4:].strip()
            content.append(Paragraph(f"<b>{text}</b>", normal_style))
            content.append(Spacer(1, 6))
            
        # Texto normal
        else:
            # Converter markdown básico para HTML
            text = line
            text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)  # **bold**
            text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)      # *italic*
            text = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', text)  # `code`
            
            if text:
                content.append(Paragraph(text, normal_style))
    
    # Gerar PDF
    doc.build(content)
    
    return filename

AGENT_NAME = "auditoria_sorteios"

def initialize_chat_state():
    """Inicializa os estados necessários no 'st.session_state'"""
    if f"{AGENT_NAME}_thread_id" not in st.session_state:
        st.session_state[f"{AGENT_NAME}_thread_id"] = str(uuid4())
    if "response_id" not in st.session_state:
        st.session_state['response_id'] = str(uuid4())

def reset_chat_state():
    """Reseta o estado do chat e gera um novo thread_id"""
    st.session_state[f"{AGENT_NAME}_chat_history"] = []
    st.session_state[f"{AGENT_NAME}_thread_id"] = str(uuid4())

def build_page(is_authenticated: bool):
    """
    Função principal - Constrói a página de auditoria
    Entry point para integração com projeto maior
    
    Args:
        is_authenticated: Se o usuário está autenticado
    """
    if not is_authenticated:
        st.error("Você não está autenticado. Por favor, faça login para acessar esta página.")
        return
    
    # Configuração da página
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 1rem;
        }
        .sub-header {
            font-size: 1.2rem;
            color: #666;
            text-align: center;
            margin-bottom: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<h1 class="main-header">📊 Auditoria de Sorteios</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Sistema de Auditoria de Títulos de Capitalização - Modalidade Tradicional</p>',
        unsafe_allow_html=True
    )
    
    # Informações sobre o sistema
    with st.expander("ℹ️ Sobre o Sistema"):
        st.markdown("""
        ### Objetivo
        Auditar sorteios de Títulos de Capitalização verificando conformidade com as 
        Condições Gerais (CG) do produto.
        
        ### Arquivos Necessários
        
        1. **📊 Planilha Excel** - Dados dos sorteios com campos obrigatórios
        2. **📄 PDF Condições Gerais** - Documento SUSEP oficial
        3. **🎲 PDF Loteria Federal** - Resultado oficial do sorteio
        
        ### Processo de Auditoria
        
        ✅ Validação de datas e periodicidade  
        ✅ Verificação da combinação sorteada  
        ✅ Análise de multiplicadores  
        ✅ Identificação de divergências  
        ✅ Geração de relatório técnico
        """)
    
    # Campos obrigatórios
    with st.expander("📋 Campos Obrigatórios da Planilha Excel"):
        st.markdown("""
        A planilha Excel deve conter as seguintes colunas:
        
        | Campo | Descrição | Formato |
        |-------|-----------|---------|
        | **DATA SORTEIO PREVISTA** | Data em que ocorreu o sorteio | AAAA-MM-DD (ISO 8601) |
        | **SERIE** | Série do título | Texto |
        | **TITULO** | Número do título | Numérico |
        | **DATA INICIO VIGENCIA** | Data de início de vigência | AAAA-MM-DD (ISO 8601) |
        | **COMBINACAO SORTEADA** | Combinação registrada | Numérico |
        | **PLANO** | Identificação do plano | Texto |
        | **NOME DO PLANO SUSEP** | Código SUSEP do produto | Texto |
        | **MULTIPLICADOR** | Multiplicador aplicado | Numérico |
        
        ⚠️ **Importante:** Todas as datas devem estar no formato ISO 8601 (AAAA-MM-DD)
        """)
    
    # Códigos SUSEP disponíveis
    with st.expander("🏦 Condições Gerais Disponíveis no Sistema"):
        from .tools import get_available_susep_codes
        available_codes = get_available_susep_codes()
        
        if available_codes:
            # Organizar códigos por tipo (PM, PU, etc.)
            pm_codes = [code for code in available_codes if code.startswith('PM')]
            pu_codes = [code for code in available_codes if code.startswith('PU')]
            other_codes = [code for code in available_codes if not code.startswith(('PM', 'PU'))]
            
            st.markdown(f"""
            Este sistema possui **{len(available_codes)} código(s) SUSEP** cadastrado(s) no banco de dados.
            
            **⚠️ Importante:** Apenas sorteios com estes códigos SUSEP na coluna "NOME DO PLANO SUSEP" podem ser auditados.
            """)
            
            if pm_codes:
                st.markdown("### 📅 PM - Pagamento Mensal")
                for code in pm_codes:
                    st.markdown(f"- `{code}`")
            
            if pu_codes:
                st.markdown("### 💰 PU - Pagamento Único")
                for code in pu_codes:
                    st.markdown(f"- `{code}`")
            
            if other_codes:
                st.markdown("### 📋 Outros Planos")
                for code in other_codes:
                    st.markdown(f"- `{code}`")
        else:
            st.error("❌ **Erro:** Nenhuma Condição Geral encontrada no banco de dados. Verifique a configuração do sistema.")
    
    st.markdown("---")
    
    # Seção de Upload
    st.markdown("## 📁 Upload de Arquivos")
    
    col1, col2 = st.columns(2)
    
    excel_file = None
    lottery_file = None
    
    with col1:
        st.markdown("### 📊 Planilha Excel")
        excel_file = st.file_uploader(
            "Dados dos Sorteios (com código SUSEP)",
            type=['xlsx', 'xls'],
            key='excel_uploader',
            help="Planilha com dados do sorteio e código SUSEP"
        )
        if excel_file:
            st.success(f"✅ {excel_file.name}")
    
    with col2:
        st.markdown("### 🎲 Loteria Federal")
        lottery_file = st.file_uploader(
            "Resultado (PDF)",
            type=['pdf'],
            key='lottery_uploader',
            help="PDF com resultado oficial"
        )
        if lottery_file:
            st.success(f"✅ {lottery_file.name}")
    
    st.info("ℹ️ As Condições Gerais serão buscadas automaticamente pelo código SUSEP da planilha")
    
    st.markdown("---")
    
    # Botão de auditoria
    all_files_uploaded = excel_file and lottery_file
    
    if not all_files_uploaded:
        st.warning("⚠️ Por favor, faça upload de todos os arquivos necessários antes de iniciar a auditoria.")
    
    if st.button("🚀 Iniciar Auditoria", type="primary", use_container_width=True, disabled=not all_files_uploaded):
        
        st.markdown("---")
        st.markdown("## 🔄 Processamento da Auditoria")
        
        # Salvar arquivos temporariamente
        excel_path = save_uploaded_file(excel_file)
        lottery_path = save_uploaded_file(lottery_file)
        
        # Criar estado inicial para o grafo (suporta múltiplos sorteios com CGs diferentes)
        initial_state = {
            "excel_path": excel_path,
            "lottery_path": lottery_path,
            "excel_data": [],  # Lista de sorteios
            "total_draws": 0,
            "current_draw_index": 0,
            "cg_contents": [],  # Lista de CGs (uma por sorteio)
            "lottery_content": "",
            "lottery_prizes": {},
            "cg_rules_list": [],  # Lista de regras (uma por sorteio)
            "date_analyses": [],  # Lista de análises
            "combination_analyses": [],
            "multiplier_analyses": [],
            "final_report": "",
            "errors": [],
            "success": True
        }
        
        try:
            # Executar o grafo LangGraph
            final_state = audit_graph.invoke(initial_state)
            initialize_chat_state()
            # Log da interação
            log_interaction(
                agent_name=AGENT_NAME,   
                thread_id=st.session_state[f"{AGENT_NAME}_thread_id"], 
                response_id=st.session_state["response_id"],
                user_question="Auditoria de sorteios",
                chatbot_response=final_state.get('final_report','')
            )
            print(st.session_state['response_id'])
            print(st.session_state[f"{AGENT_NAME}_thread_id"])
            # Exibir resultado
            st.markdown("---")
            st.markdown("## 📊 Resultado da Auditoria")
            
            total_analyzed = final_state.get('total_draws', 0)
            st.info(f"📈 Total de sorteios analisados: **{total_analyzed}**")
            
            if final_state.get('success', False):
                st.success("✅ Auditoria Concluída com Sucesso")
            else:
                st.error("❌ Auditoria Concluída com Erros")
                if final_state.get('errors'):
                    st.error(f"Erros: {', '.join(final_state['errors'])}")
            
            # Relatório principal
            if final_state.get('final_report'):
                st.markdown("### 📄 Relatório Consolidado de Auditoria")
                st.markdown(final_state['final_report'])
                
                
                # Detalhes expandíveis por sorteio
                with st.expander("🔍 Detalhes das Análises por Sorteio"):
                    
                    # Mostrar análises de cada sorteio
                    for i in range(total_analyzed):
                        draw_data = final_state.get('excel_data', [])[i] if i < len(final_state.get('excel_data', [])) else {}
                        codigo_susep = draw_data.get('numero_susep', 'N/A')
                        
                        st.markdown(f"### Sorteio {i + 1}/{total_analyzed} (SUSEP: {codigo_susep})")
                        
                        if i < len(final_state.get('cg_rules_list', [])):
                            st.markdown("#### 📋 Regras das Condições Gerais")
                            st.markdown(final_state['cg_rules_list'][i])
                        
                        if i < len(final_state.get('date_analyses', [])):
                            st.markdown("#### 📅 Análise de Data")
                            st.markdown(final_state['date_analyses'][i])
                        
                        if i < len(final_state.get('combination_analyses', [])):
                            st.markdown("#### 🎲 Análise de Combinação")
                            st.markdown(final_state['combination_analyses'][i])
                        
                        if i < len(final_state.get('multiplier_analyses', [])):
                            st.markdown("#### ✖️ Análise de Multiplicador")
                            st.markdown(final_state['multiplier_analyses'][i])
                        
                        if i < total_analyzed - 1:
                            st.divider()
                
                # Download do relatório
                filename = save_report_to_file(
                    final_state['final_report'],
                    final_state.get('excel_data', {})
                )
            
                with open(filename, "rb") as file:
                    st.download_button(
                        label="📥 Download Relatório (PDF)",
                        data=file.read(),
                        file_name=filename,
                        mime="application/pdf"
                    )
            
                
            print(st.session_state['response_id'])
            print(st.session_state[f"{AGENT_NAME}_thread_id"])
                          
        
    
        finally:
            # Limpar arquivos temporários
            for path in [excel_path, lottery_path]:
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                except:
                    pass
        update_feedback(
                agent_name=AGENT_NAME,
                thread_id=st.session_state[f"{AGENT_NAME}_thread_id"], 
                response_id=st.session_state["response_id"],
                )    
    