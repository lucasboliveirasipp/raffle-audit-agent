"""
Ferramentas para processamento de arquivos e extração de dados
Todas as funções são puras (sem classes)
"""
import pandas as pd
import PyPDF2
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from .database import get_db_session, close_db_session, CondicoesGerais, init_db, get_db_path


# ====================
# Database Operations
# ====================

def get_cg_by_susep(codigo_susep: str) -> Optional[str]:
    """
    Busca Condições Gerais por código SUSEP no banco de dados usando SQLAlchemy
    
    Args:
        codigo_susep: Código SUSEP do produto
        
    Returns:
        Texto completo das CG ou None se não encontrado
    """
    import os
    
    try:
        # Verificar se o código SUSEP é válido
        if not codigo_susep or codigo_susep == "nan" or str(codigo_susep).lower() == "nan":
            raise Exception(f"Código SUSEP inválido: '{codigo_susep}'. Verifique se a planilha tem valores válidos na coluna 'NOME DO PLANO SUSEP'")
        
        # Verificar se o arquivo do banco existe
        db_path = get_db_path()
        if not os.path.exists(db_path):
            raise Exception(f"Arquivo do banco de dados não encontrado: {db_path}")
        
        # Inicializar banco (criar tabelas se não existirem)
        init_db()
        
        # Criar sessão
        session = get_db_session()
        
        try:
            # Buscar o registro
            record = session.query(CondicoesGerais).filter(
                CondicoesGerais.plano_susep == str(codigo_susep)
            ).first()
            
            if record:
                return record.texto_completo
            
            # Se não encontrou, vamos listar os códigos disponíveis para debug
            available_codes = session.query(CondicoesGerais.plano_susep).limit(10).all()
            available_codes = [code[0] for code in available_codes]
            
            raise Exception(f"Código SUSEP '{codigo_susep}' não encontrado. Códigos disponíveis: {available_codes}")
            
        finally:
            close_db_session(session)
        
    except Exception as e:
        raise Exception(f"Erro ao buscar CG no banco: {str(e)}")


def get_available_susep_codes() -> List[str]:
    """
    Busca todos os códigos SUSEP disponíveis no banco de dados usando SQLAlchemy
    
    Returns:
        Lista com todos os códigos SUSEP disponíveis
    """
    import os
    
    try:
        db_path = get_db_path()
        if not os.path.exists(db_path):
            return []
        
        # Inicializar banco (criar tabelas se não existirem)
        init_db()
        
        # Criar sessão
        session = get_db_session()
        
        try:
            # Buscar todos os códigos SUSEP ordenados
            results = session.query(CondicoesGerais.plano_susep).order_by(CondicoesGerais.plano_susep).all()
            return [row[0] for row in results]
            
        finally:
            close_db_session(session)
        
    except Exception:
        return []


# ====================
# Excel Processing
# ====================

def read_excel(file_path: str) -> Tuple[pd.DataFrame, List[str]]:
    """
    Lê planilha Excel
    
    Args:
        file_path: Caminho do arquivo Excel
        
    Returns:
        Tuple[DataFrame, List[str]]: (dataframe, lista de erros vazia)
    """
    try:
        df = pd.read_excel(file_path)
        
        # Normalizar nomes das colunas (remover espaços extras)
        df.columns = df.columns.str.strip()
        
        return df, []
        
    except Exception as e:
        raise Exception(f"Erro ao ler planilha Excel: {str(e)}")


def extract_draw_data(df: pd.DataFrame, row_index: int = 0) -> Dict[str, Any]:
    """
    Extrai dados de um sorteio específico da planilha
    
    Args:
        df: DataFrame com dados dos sorteios
        row_index: Índice da linha a ser extraída
        
    Returns:
        Dict com dados do sorteio
    """
    row = df.iloc[row_index]
    
    # Função auxiliar para normalizar valores (remover espaços extras e tratar NaN)
    def normalize_value(value):
        # Verificar se é NaN ou None
        if pd.isna(value) or value is None:
            return None
        if isinstance(value, str):
            return value.strip() if value.strip() else None
        return value
    
    return {
        "data_sorteio": normalize_value(row.get("DATA SORTEIO PREVISTA")),
        "serie": normalize_value(row.get("SERIE")),
        "titulo": normalize_value(row.get("TITULO")),
        "inicio_vigencia": normalize_value(row.get("DATA INICIO VIGENCIA")),
        "combinacao_sorteada": normalize_value(row.get("COMBINACAO SORTEADA")),
        "plano": normalize_value(row.get("PLANO")),
        "numero_susep": normalize_value(row.get("NOME DO PLANO SUSEP")),
        "multiplicador": normalize_value(row.get("MULTIPLICADOR"))
    }


def format_excel_data(draw_data: Dict[str, Any]) -> str:
    """Formata dados da planilha para apresentação"""
    return f"""
**Dados da Planilha:**
- Data do Sorteio: {draw_data.get('data_sorteio')}
- Série: {draw_data.get('serie')}
- Título: {draw_data.get('titulo')}
- Início de Vigência: {draw_data.get('inicio_vigencia')}
- Combinação Sorteada: {draw_data.get('combinacao_sorteada')}
- Plano: {draw_data.get('plano')}
- Número SUSEP: {draw_data.get('numero_susep')}
- Multiplicador: {draw_data.get('multiplicador')}
"""


def extract_text_from_pdf(file_path: str) -> str:
    """Extrai texto de um arquivo PDF"""
    try:
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        
        return text.strip()
        
    except Exception as e:
        raise Exception(f"Erro ao ler PDF: {str(e)}")


def extract_lottery_numbers(lottery_text: str) -> Dict[str, str]:
    """Extrai números dos prêmios da Loteria Federal"""
    prizes = {}
    
    pattern = r'(\d+)[ºª°]\s*(?:prêmio|premio|Prêmio|Premio)[\s:]*(\d{5,6})'
    matches = re.findall(pattern, lottery_text, re.IGNORECASE)
    
    for match in matches:
        prize_number = match[0]
        full_number = match[1]
        last_five = full_number[-5:]
        prizes[f"{prize_number}º Prêmio"] = last_five
    
    return prizes


def parse_date(date_value: Any) -> Optional[datetime]:
    """Converte valor de data para datetime (formato ISO 8601)"""
    if pd.isna(date_value):
        return None
    
    if isinstance(date_value, datetime):
        return date_value
    
    if isinstance(date_value, pd.Timestamp):
        return date_value.to_pydatetime()
    
    try:
        return datetime.strptime(str(date_value), "%Y-%m-%d")
    except:
        try:
            return datetime.strptime(str(date_value), "%d/%m/%Y")
        except:
            return None


def get_weekday_name(date: datetime, language: str = "pt") -> str:
    """Retorna nome do dia da semana"""
    weekdays_pt = [
        "Segunda-feira", "Terça-feira", "Quarta-feira", 
        "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"
    ]
    return weekdays_pt[date.weekday()]


def is_first_saturday(date: datetime) -> bool:
    """Verifica se a data é o primeiro sábado do mês"""
    if date.weekday() != 5:
        return False
    return 1 <= date.day <= 7


def is_nth_weekday_of_month(date: datetime, weekday: int, nth: int) -> bool:
    """Verifica se a data corresponde ao n-ésimo dia da semana do mês"""
    if date.weekday() != weekday:
        return False
    
    count = 0
    for day in range(1, date.day + 1):
        test_date = date.replace(day=day)
        if test_date.weekday() == weekday:
            count += 1
    
    return count == nth


def calculate_vigency_year(draw_date: datetime, start_date: datetime) -> int:
    """Calcula o ano de vigência do título"""
    if draw_date < start_date:
        return 0
    
    years_diff = draw_date.year - start_date.year
    
    if (draw_date.month, draw_date.day) < (start_date.month, start_date.day):
        years_diff -= 1
    
    return years_diff + 1


def extract_digits_from_prizes(prizes: Dict[str, str], method: str = "top_to_bottom") -> str:
    """Extrai combinação a partir dos prêmios da loteria"""
    sorted_prizes = sorted(prizes.items(), key=lambda x: int(x[0].split('º')[0]))
    
    if method == "top_to_bottom":
        combination = ""
        for _, number in sorted_prizes:
            combination += number[-1]
        return combination
    
    elif method == "bottom_to_top":
        combination = ""
        for _, number in reversed(sorted_prizes):
            combination += number[-1]
        return combination
    
    return ""


def compare_combinations(registered: str, calculated: str) -> bool:
    """Compara combinação registrada com a calculada"""
    reg_clean = str(registered).replace(" ", "").replace("-", "").strip()
    calc_clean = str(calculated).replace(" ", "").replace("-", "").strip()
    
    return reg_clean == calc_clean


def load_all_files(excel_path: str, lottery_path: str) -> Dict[str, Any]:
    """
    Carrega arquivos e busca CG do banco de dados.
    Processa TODAS as linhas do Excel, cada uma representando um sorteio.
    
    Args:
        excel_path: Caminho da planilha Excel
        lottery_path: Caminho do PDF da Loteria Federal
        
    Returns:
        Dict com todos os dados extraídos:
        - excel_data: Lista de dicts, um para cada sorteio
        - total_draws: Número total de sorteios
        - cg_content: Texto das CG (pode variar se houver múltiplos SUSEP)
        - lottery_content: Texto da Loteria Federal
        - lottery_prizes: Dict com prêmios extraídos
    """
    result = {
        "success": True,
        "errors": [],
        "excel_data": [],  # Lista de sorteios
        "total_draws": 0,
        "cg_content": None,
        "lottery_content": None,
        "lottery_prizes": None
    }
    
    try:
        # Carregar Excel
        df, _ = read_excel(excel_path)
        total_rows = len(df)
        result["total_draws"] = total_rows
        
        # Extrair dados de TODAS as linhas (cada linha = 1 sorteio)
        all_draws = []
        skipped_rows = []
        
        for row_index in range(total_rows):
            draw_data = extract_draw_data(df, row_index)
            
            # Verificar se a linha tem código SUSEP válido
            numero_susep = draw_data.get("numero_susep")
            if not numero_susep or numero_susep == "nan" or str(numero_susep).lower() == "nan":
                skipped_rows.append(row_index + 1)  # +1 para número da linha no Excel
                continue
                
            all_draws.append(draw_data)
        
        # Atualizar total de sorteios válidos
        result["total_draws"] = len(all_draws)
        result["excel_data"] = all_draws
        
        # Informar sobre linhas ignoradas
        if skipped_rows:
            print(f"⚠️ Linhas ignoradas (sem código SUSEP válido): {skipped_rows}")
        
        # Verificar se há pelo menos um sorteio válido
        if len(all_draws) == 0:
            result["success"] = False
            result["errors"].append("Nenhum sorteio com código SUSEP válido encontrado na planilha")
            return result
        
        # NÃO buscar CG aqui - cada sorteio buscará sua própria CG
        # (cada linha pode ter código SUSEP diferente)
        result["cg_content"] = None  # Será buscado individualmente por sorteio
        
        # Carregar Loteria Federal
        lottery_text = extract_text_from_pdf(lottery_path)
        result["lottery_content"] = lottery_text
        result["lottery_prizes"] = extract_lottery_numbers(lottery_text)
        
    except Exception as e:
        result["success"] = False
        result["errors"].append(str(e))
    
    return result