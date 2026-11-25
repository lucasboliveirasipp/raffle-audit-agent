"""
Prompts do sistema para o agente de auditoria
"""

SYSTEM_PROMPT = """# Persona: Analista de Auditoria de Títulos de Capitalização

Você é um Analista de Auditoria especializado em sorteios de Títulos de Capitalização (modalidade tradicional). 
Seu perfil é técnico, meticuloso e comprometido com a conformidade dos sorteios conforme as regras estabelecidas 
nas Condições Gerais (CG) do produto.

## Suas Responsabilidades:

1. **Verificar Datas**: Confirmar se a data do sorteio está de acordo com a periodicidade exigida nas CG
2. **Validar Extração**: Comparar números da Loteria Federal com a combinação sorteada registrada
3. **Analisar Multiplicadores**: Verificar se o multiplicador aplicado está correto para o ano de vigência
4. **Documentar Divergências**: Registrar qualquer não-conformidade com evidências e explicações técnicas

## Princípios:

- O documento SUSEP (Condições Gerais) é a fonte mais fidedigna e tem precedência absoluta
- Todas as datas seguem o formato ISO 8601 (AAAA-MM-DD)
- Toda divergência deve ser justificada tecnicamente com base nas regras das CG
- A extração da Loteria Federal é composta pelos 5 últimos dígitos de cada prêmio, lidos do final para o começo

## Fontes de Dados:

1. Planilha Excel dos sorteios
2. Resultado da Loteria Federal
3. Documento SUSEP das Condições Gerais (CG)

Seja rigoroso, preciso e sempre fundamente suas conclusões em evidências documentais.
"""

AUDIT_INSTRUCTIONS = """# Instruções para Auditoria de Sorteio

## Etapas da Auditoria:

### 1. Verificação da Data do Sorteio
- Confirme se houve extração válida da Loteria Federal na data informada
- Identifique o dia da semana da data do sorteio
- Valide se a data está de acordo com a periodicidade exata exigida nas CG
- Exemplo: se as CG exigem "primeiro sábado de junho e dezembro", verifique se é exatamente isso
- Classifique como "Periodicidade Inválida" caso não esteja prevista nas CG

### 2. Análise do Resultado da Loteria Federal
- Extraia os 5 últimos dígitos de cada prêmio da Loteria Federal
- Os dígitos devem ser lidos do final para o começo
- Exemplo: Prêmio 003920 → extrair 03920

### 3. Consulta das Condições Gerais (CG)
- Identifique as seções sobre:
  * Periodicidade dos sorteios
  * Regras de formação da combinação sorteada
  * Tipo de extração permitido
  * Multiplicadores por ano de vigência
- Use APENAS o conteúdo do PDF fornecido - não use regras genéricas

### 4. Validação da Combinação Sorteada
- Verifique se a combinação registrada está estruturada conforme as regras das CG
- Identifique qual tipo de extração foi aplicada (ex: unidade simples de cima para baixo)
- Verifique o exemplo dado nas próprias CG para entender a regra
- Valide se essa regra está explicitamente permitida nas CG

### 5. Verificação do Multiplicador
- Determine o ano de vigência comparando a data do sorteio com o início de vigência
- Confirme se o multiplicador aplicado condiz com o previsto nas CG para aquele ano

### 6. Registro de Divergências
Para cada incompatibilidade encontrada:
- Descreva a natureza da divergência
- Explique tecnicamente a origem do erro
- Indique o impacto (ex: valor pago incorretamente, combinação inválida)
- Sugira a correção esperada
- Apresente evidências documentais (trechos da CG, números da Loteria, datas)

## Formato de Saída Esperado:

**Produto:** [Nome do Produto]
**Código SUSEP:** [XXXXXXX]
**Data do Sorteio:** [DD/MM/AAAA]
**Dia da Semana:** [Sábado/Outro] - Justificativa
**Periodicidade Válida para o Produto?:** [Sim/Não] - Justificativa
**Tipo de Extração Utilizada:** [Ex: Unidade de Cima p/ Baixo]
**Tipo Permitido na CG?:** [Sim/Não] - Justificativa
**Combinação Sorteada está de acordo?:** [Sim/Não] - Justificativa
**Multiplicador Aplicado Corretamente?:** [Sim/Não] - Justificativa

### Divergências Encontradas:
[Se houver]
- **Descrição detalhada**
- **Causa e explicação técnica**
- **Referência documental**
- **Correção recomendada**
"""

VALIDATION_PROMPT = """Baseado nos dados fornecidos:

**Planilha Excel:**
{excel_data}

**Resultado da Loteria Federal:**
{lottery_result}

**Condições Gerais (CG):**
{cg_content}

Execute uma auditoria completa seguindo todas as instruções e forneça um relatório detalhado 
identificando conformidades e divergências.
"""

EXTRACT_CG_RULES_PROMPT = """Analise o documento das Condições Gerais e extraia as seguintes informações:

1. **Periodicidade dos sorteios**: Em quais datas/dias os sorteios devem ocorrer?
2. **Regra de formação da combinação**: Como deve ser construída a combinação sorteada a partir da Loteria Federal?
3. **Tipos de extração permitidos**: Quais métodos de leitura são válidos?
4. **Multiplicadores**: Quais multiplicadores se aplicam a cada ano de vigência?

Documento CG:
{cg_content}

Seja específico e cite os trechos relevantes do documento.
"""

ERROR_MISSING_FILES = """⚠️ **Arquivos Faltando**

Para iniciar a auditoria, é necessário fornecer:

1. ✅ **Planilha Excel** contendo os campos obrigatórios:
   - DATA DO SORTEIO
   - SÉRIE
   - TITULO
   - INICIO DE VIGÊNCIA
   - COMBINAÇÃO SORTEADA
   - PLANO
   - NOME DO PLANO SUSEP
   - MULTIPLICADOR

2. ✅ **PDF das Condições Gerais (CG)** - baseado no código SUSEP da planilha

3. ✅ **PDF do Resultado da Loteria Federal** - referente à data do sorteio

Por favor, faça o upload de todos os arquivos necessários.
"""

ERROR_INVALID_EXCEL = """⚠️ **Planilha Excel Inválida**

A planilha fornecida não contém todos os campos obrigatórios.

**Campos esperados:**
- DATA DO SORTEIO
- SÉRIE
- TITULO
- INICIO DE VIGÊNCIA
- COMBINAÇÃO SORTEADA
- PLANO
- NOME DO PLANO SUSEP
- MULTIPLICADOR

**Campos encontrados:**
{found_fields}

**Campos faltando:**
{missing_fields}

Por favor, corrija a planilha e faça upload novamente.
"""


# ====================
# Prompts específicos para cada nó
# ====================

ANALYZE_DATE_PROMPT = """Analise a data do sorteio com base nas regras das Condições Gerais.

**Contexto da Data:**
{date_context}

**Regras das CG:**
{cg_rules}

Responda:
1. A data do sorteio está de acordo com a periodicidade prevista nas CG?
2. O dia da semana está correto?
3. Há alguma divergência? Se sim, explique tecnicamente.

Forneça uma análise detalhada.
"""

ANALYZE_COMBINATION_PROMPT = """Analise a combinação sorteada comparando com os resultados da Loteria Federal.

**Contexto da Combinação:**
{combination_context}

**Regras das CG:**
{cg_rules}

Responda:
1. A combinação registrada está correta de acordo com a Loteria Federal?
2. O método de extração utilizado está de acordo com as CG?
3. Há alguma divergência? Se sim, explique tecnicamente.

Forneça uma análise detalhada.
"""

ANALYZE_MULTIPLIER_PROMPT = """Analise o multiplicador aplicado ao sorteio.

**Contexto do Multiplicador:**
{multiplier_context}

**Regras das CG:**
{cg_rules}

Responda:
1. O multiplicador aplicado está de acordo com o previsto nas CG?
2. O ano de vigência foi calculado corretamente?
3. Há alguma divergência? Se sim, explique tecnicamente.

Forneça uma análise detalhada.
"""

GENERATE_REPORT_PROMPT = """Gere um relatório consolidado de auditoria com base em todas as análises realizadas.

**Análises Completas:**
{full_context}

**Dados da Planilha:**
{excel_data}

Forneça um relatório técnico no seguinte formato:

# RELATÓRIO DE AUDITORIA - SORTEIO DE TÍTULO DE CAPITALIZAÇÃO

## Identificação
- **Produto:** [Nome do Produto]
- **Código SUSEP:** [Número]
- **Data do Sorteio:** [Data]
- **Série:** [Série]
- **Título:** [Número do Título]

## Resumo Executivo
[Resumo das principais conclusões: conforme ou não conforme]

## Análises Detalhadas

### 1. Periodicidade do Sorteio
[Análise da data]

### 2. Combinação Sorteada
[Análise da combinação]

### 3. Multiplicador
[Análise do multiplicador]

## Divergências Encontradas
[Lista de divergências, se houver]

## Conclusão Final
[Parecer final: CONFORME ou NÃO CONFORME]

## Recomendações
[Se houver divergências, liste as correções necessárias]
"""
