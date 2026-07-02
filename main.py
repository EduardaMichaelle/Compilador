import re
import json
from ast_nodes import * # Importa todas as classes do arquivo ast_nodes.py
from bril_generator import BrilCodeGenerator

# --- ANALISADOR LÉXICO ---

class LexicalError(Exception):
    """Exceção customizada para erros léxicos."""
    pass

def lexer_cool(caminho_arquivo):
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            codigo = f.read()
    except FileNotFoundError:
        print(f"Erro: O arquivo {caminho_arquivo} não foi encontrado.")
        return []

    tokens_finais = []
    linha_atual = 1
    i = 0
    n = len(codigo)

    # Regex para os tokens simples (Palavras-chave agora aceitam variações de maiúsculas/minúsculas)
    # Nota: true/false começam obrigatoriamente com 't' e 'f' minúsculos, o resto pode variar.
    keyword_regex = re.compile(r'\b(class|inherits|if|then|else|fi|let|in|case|of|esac|new|isvoid|while|loop|pool|not)\b', re.IGNORECASE)
    type_regex = re.compile(r'\b(Object|Int|String|Bool|IO|Int)\b')
    bool_true = re.compile(r'\bt[rR][uU][eE]\b')
    bool_false = re.compile(r'\bf[aA][lL][sS][eE]\b')

    token_patterns = [
        ('ASSIGN',   r'<-'),
        ('LE',       r'<='),
        ('DARROW',   r'=>'), # Importante para o CASE do Cool
        ('NUMBER',   r'\d+'),
        ('OP',       r'[+\-*/<>=~]'), 
        ('PUNCT',    r'[{}();:,.@]'),
        ('ID',       r'[A-Za-z][A-Za-z0-9_]*'),
    ]
    
    master_regex = re.compile('|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_patterns))

    while i < n:
        # 1. Ignorar espaços em branco e atualizar linhas
        if codigo[i] == '\n':
            linha_atual += 1
            i += 1
            continue
        if codigo[i] in ' \t\r\v\f':
            i += 1
            continue

        # 2. Comentário de linha única (--)
        if codigo[i:i+2] == '--':
            while i < n and codigo[i] != '\n':
                i += 1
            continue

        # 3. Comentário em Bloco Aninhado (* *), tratando recursão de blocos
        if codigo[i:i+2] == '(*':
            nivel_comentario = 0
            linha_inicio_comentario = linha_atual # Guardamos a linha onde começou para o erro fazer sentido
            
            while i < n:
                if codigo[i:i+2] == '(*':
                    nivel_comentario += 1
                    i += 2
                elif codigo[i:i+2] == '*)':
                    nivel_comentario -= 1
                    i += 2
                    if nivel_comentario == 0:
                        break
                else:
                    if codigo[i] == '\n':
                        linha_atual += 1
                    i += 1
            
            # 🚨 A CORREÇÃO ESTÁ AQUI:
            if nivel_comentario > 0:
                raise LexicalError(
                    f"Erro inesperado em um comentário em bloco. "
                    f"Foi aberto na linha {linha_inicio_comentario}, mas nunca foi fechado."
                )
            continue

        # 4. Strings com suporte a caracteres de escape
        if codigo[i] == '"':
            inicio_string = i
            i += 1
            conteudo_string = ""
            while i < n and codigo[i] != '"':
                if codigo[i] == '\n':
                    # 🚨 Lança erro se quebrar a linha sem escapar a string
                    raise LexicalError(f"String constante não terminada na linha {linha_atual}")
                if codigo[i] == '\\': # Caractere de escape
                    i += 1
                    if i < n:
                        if codigo[i] == 'n': conteudo_string += '\n'
                        elif codigo[i] == 't': conteudo_string += '\t'
                        else: conteudo_string += codigo[i]
                else:
                    conteudo_string += codigo[i]
                i += 1
            
            if i >= n:
                # 🚨 Lança erro se o arquivo acabar e a string continuar aberta
                raise LexicalError(f"Fim de arquivo inesperado dentro de uma string constante na linha {linha_atual}")
                
            if i < n and codigo[i] == '"':
                i += 1 # consome a aspa de fechamento
                tokens_finais.append({'tipo': 'STRING', 'valor': conteudo_string, 'linha': linha_atual})
            continue

        # 5. Outros Matchings (Keywords, IDs, Operadores)
        match = master_regex.match(codigo, i)
        if match:
            kind = match.lastgroup
            value = match.group()
            
            # Refinar se o ID na verdade é uma KEYWORD ou BOOLEANO
            if kind == 'ID':
                if keyword_regex.match(value):
                    kind = 'KEYWORD'
                    value = value.lower() # 🚨 ATUALIZAÇÃO AQUI: Transforma 'Class' em 'class'
                elif bool_true.match(value) or bool_false.match(value):
                    kind = 'BOOL_CONST'
                elif type_regex.match(value) or value[0].isupper():
                    kind = 'TYPE_ID' # Em Cool, tipos começam com Letra Maiúscula
                    
            tokens_finais.append({'tipo': kind, 'valor': value, 'linha': linha_atual})
            i = match.end()
        else:
            # 🚨 MODIFICAÇÃO AQUI: Removemos o print/continuação e lançamos a exceção
            raise LexicalError(f"Caractere inválido '{codigo[i]}' na linha {linha_atual}")
            
    return tokens_finais


# --- ANALISADOR SINTÁTICO ---

class ParserCool:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def atual(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def comer(self, tipo_esperado, valor_esperado=None):
        token = self.atual()
        if not token:
            linha_erro = self.tokens[-1]['linha'] if self.tokens else "desconhecida"
            raise SyntaxError(f"Erro Sintático Próximo à linha {linha_erro}: Fim de arquivo inesperado (EOF).")

        tipo_token = token['tipo']
        valor_token = token['valor']

        if (tipo_token == tipo_esperado or 
           (tipo_esperado == 'ID' and tipo_token == 'KEYWORD') or
           (tipo_esperado == 'OP' and tipo_token == 'LE')) and \
           (valor_esperado is None or valor_token == valor_esperado):
            self.pos += 1
            return token
        else:
            esperado = valor_esperado if valor_esperado else tipo_esperado
            raise SyntaxError(f"Erro Sintático na linha {token['linha']}: Esperado '{esperado}', mas encontrou '{valor_token}'")
        
    def parse_programa(self):
        classes = []
        while self.atual() is not None:
            classes.append(self.parse_classe())
        return Programa(classes=classes)

    def parse_classe(self):
        self.comer('KEYWORD', 'class')
        nome = self.comer('TYPE_ID')
        
        pai = 'Object'
        if self.atual() and self.atual()['valor'] == 'inherits':
            self.comer('KEYWORD', 'inherits')
            pai = self.comer('TYPE_ID')['valor']
            
        self.comer('PUNCT', '{')
        features = []
        
        while self.atual() and self.atual()['valor'] != '}':
            features.append(self.parse_feature())
            
        self.comer('PUNCT', '}')
        self.comer('PUNCT', ';') 
        
        return Classe(linha=nome['linha'], nome=nome['valor'], pai=pai, features=features)

    def parse_feature(self):
        id_nome = self.comer('ID')
        linha_declaracao = id_nome['linha']
        
        # Se possui '(', trata-se de um MÉTODO
        if self.atual() and self.atual()['valor'] == '(':
            self.comer('PUNCT', '(')
            
            lista_de_parametros_capturados = []
            while self.atual() and self.atual()['valor'] != ')':
                token_nome = self.comer('ID')
                p_nome = token_nome['valor']
                linha_param = token_nome['linha']
                
                self.comer('PUNCT', ':')
                p_tipo = self.comer('TYPE_ID')['valor']
                
                lista_de_parametros_capturados.append((p_nome, p_tipo, linha_param))
                
                if self.atual() and self.atual()['valor'] == ',':
                    self.comer('PUNCT', ',')
                    
            self.comer('PUNCT', ')')
            self.comer('PUNCT', ':')
            tipo_retorno = self.comer('TYPE_ID') 
            self.comer('PUNCT', '{')
            corpo = self.parse_expressao()
            self.comer('PUNCT', '}')
            self.comer('PUNCT', ';') 
            
            return Metodo(
                linha=linha_declaracao,
                nome=id_nome['valor'],
                retorno=tipo_retorno['valor'],
                parametros=lista_de_parametros_capturados,
                corpo=corpo
            )
        
        # Caso contrário, é um ATRIBUTO
        else:
            self.comer('PUNCT', ':')
            tipo = self.comer('TYPE_ID')
            expressao_inicial = None
            
            if self.atual() and self.atual()['valor'] == '<-':
                self.comer('ASSIGN')                       
                expressao_inicial = self.parse_expressao() 
            
            self.comer('PUNCT', ';') 
            
            return Atributo(
                linha=linha_declaracao,
                nome=id_nome['valor'],
                dado=tipo['valor'],
                inicializacao=expressao_inicial
            )
            
    def parse_expressao(self):
        t = self.atual()
        if not t: 
            return None

        if t['valor'] == 'if':
            return self.parse_if()
        elif t['valor'] == 'let':
            return self.parse_let()
        elif t['valor'] == '{':
            return self.parse_bloco()
        elif t['valor'] == 'while':
            return self.parse_while()
        elif t['valor'] == 'case':
            return self.parse_case()
            
        elif t['valor'] == 'not':
            self.comer('KEYWORD', 'not') 
            expressao_negada = self.parse_expressao() 
            return NegacaoLogica(linha=t['linha'], expressao=expressao_negada)
            
        elif t['valor'] == 'isvoid':
            self.comer('KEYWORD', 'isvoid')
            expressao_interna = self.parse_expressao()
            return Isvoid(linha=t['linha'], expressao=expressao_interna)
            
        elif t['tipo'] == 'OP' and t['valor'] == '~':
            self.comer('OP', '~')
            expressao_negada = self.parse_expressao()
            return Negacao(linha=t['linha'], expressao=expressao_negada)
            
        elif t['tipo'] == 'PUNCT' and t['valor'] == '(':
            self.comer('PUNCT', '(')                    
            expressao_interna = self.parse_expressao()  
            self.comer('PUNCT', ')')                    
            
            while self.atual() and self.atual()['valor'] in ['.', '@']:
                tipo_despacho = self.comer(self.atual()['tipo'])['valor']
                
                classe_estatica = None
                if tipo_despacho == '@':
                    classe_estatica = self.comer('TYPE_ID')['valor']
                    self.comer('PUNCT', '.')
                    
                id_metodo = self.comer('ID')
                self.comer('PUNCT', '(')
                
                argumentos = []
                if self.atual() and self.atual()['valor'] != ')':
                    while True:
                        argumentos.append(self.parse_expressao())
                        if self.atual() and self.atual()['valor'] == ',':
                            self.comer('PUNCT', ',')
                        else:
                            break
                            
                self.comer('PUNCT', ')')
                
                expressao_interna = ChamadaMetodoObjeto(
                    linha=t['linha'],
                    objeto=expressao_interna,
                    classe_estatica=classe_estatica,
                    metodo=id_metodo['valor'],
                    argumentos=argumentos
                )
                
            if self.atual() and self.atual()['tipo'] in ['OP', 'LE']:
                operador = self.comer(self.atual()['tipo'])['valor']
                proxima_expr = self.parse_expressao()
                return OperacaoBinaria(
                    linha=t['linha'],
                    esquerda=expressao_interna,
                    operador=operador,
                    direita=proxima_expr
                )
                
            return expressao_interna
            
        elif t['valor'] == 'new':
            return self.parse_new()
            
        elif t['tipo'] in ['ID', 'KEYWORD', 'TYPE_ID']:
            var = self.comer(t['tipo']) 
            
            # 1. Chamada de método local
            if self.atual() and self.atual()['valor'] == '(':
                self.comer('PUNCT', '(')
                
                argumentos = []
                if self.atual() and self.atual()['valor'] != ')':
                    while True:
                        argumentos.append(self.parse_expressao())
                        if self.atual() and self.atual()['valor'] == ',':
                            self.comer('PUNCT', ',')
                        else:
                            break
                            
                self.comer('PUNCT', ')')
                no_retorno = ChamadaMetodo(linha=t['linha'], nome=var['valor'], argumentos=argumentos)
                
            # 2. Atribuição (id <- expressao)
            elif self.atual() and self.atual()['valor'] == '<-':
                self.comer('ASSIGN')
                expressao_direita = self.parse_expressao() 
                return Atribuicao(linha=t['linha'], nome=var['valor'], direita=expressao_direita)
                
            # 3. Variável simples
            else:
                no_retorno = Variavel(linha=t['linha'], nome=var['valor'])
                
            # 4. Encadeamento de chamadas (. ou @)
            while self.atual() and self.atual()['valor'] in ['.', '@']:
                tipo_estatico = None
                tipo_despacho = self.comer(self.atual()['tipo'])['valor']
                
                if tipo_despacho == '@':
                    tipo_estatico = self.comer('TYPE_ID')['valor']
                    self.comer('PUNCT', '.')
                
                id_metodo = self.comer('ID')
                self.comer('PUNCT', '(')
                
                argumentos = []
                if self.atual() and self.atual()['valor'] != ')':
                    while True:
                        argumentos.append(self.parse_expressao())
                        if self.atual() and self.atual()['valor'] == ',':
                            self.comer('PUNCT', ',')
                        else:
                            break
                            
                self.comer('PUNCT', ')')
                no_retorno = ChamadaMetodoObjeto(
                    linha=t['linha'],
                    objeto=no_retorno,
                    classe_estatica=tipo_estatico,
                    metodo=id_metodo['valor'],
                    argumentos=argumentos
                )
            
            if self.atual() and self.atual()['tipo'] in ['OP', 'LE']:
                operador = self.comer(self.atual()['tipo'])['valor']
                proxima_expr = self.parse_expressao()
                return OperacaoBinaria(
                    linha=t['linha'],
                    esquerda=no_retorno,
                    operador=operador,
                    direita=proxima_expr
                )
                
            return no_retorno
            
        elif t['tipo'] in ['STRING', 'NUMBER', 'BOOL_CONST']:
            literal = self.comer(t['tipo'])
            
            # Mapeia dinamicamente para o nó correto da nossa AST
            if t['tipo'] == 'NUMBER':
                no_retorno = IntConst(linha=literal['linha'], valor=literal['valor'])
            elif t['tipo'] == 'STRING':
                no_retorno = StrConst(linha=literal['linha'], valor=literal['valor'])
            else:
                no_retorno = BoolConst(linha=literal['linha'], valor=literal['valor'])
            
            while self.atual() and self.atual()['valor'] == '.':
                self.comer('PUNCT', '.') 
                id_metodo = self.comer('ID') 
                self.comer('PUNCT', '(') 
                
                argumentos = []
                if self.atual() and self.atual()['valor'] != ')':
                    while True:
                        argumentos.append(self.parse_expressao())
                        if self.atual() and self.atual()['valor'] == ',':
                            self.comer('PUNCT', ',')
                        else:
                            break
                            
                self.comer('PUNCT', ')') 
                no_retorno = ChamadaMetodoObjeto(
                    linha=t['linha'],
                    objeto=no_retorno,
                    metodo=id_metodo['valor'],
                    argumentos=argumentos
                )
            
            if self.atual() and self.atual()['tipo'] in ['OP', 'LE']:
                operador = self.comer(self.atual()['tipo'])['valor']
                proxima_expr = self.parse_expressao()
                return OperacaoBinaria(
                    linha=t['linha'],
                    esquerda=no_retorno,
                    operador=operador,
                    direita=proxima_expr
                )
                
            return no_retorno
            
        raise SyntaxError(f"Erro Sintático na linha {t['linha']}: Expressão inválida ou inesperada '{t['valor']}'")

    def parse_if(self):
        t = self.comer('KEYWORD', 'if')
        condicao = self.parse_expressao()
        self.comer('KEYWORD', 'then')
        corpo_then = self.parse_expressao()
        self.comer('KEYWORD', 'else')
        corpo_else = self.parse_expressao()
        self.comer('KEYWORD', 'fi')
        
        # Instancia a classe If
        no_retorno = If(
            linha=t['linha'],
            condicao=condicao,
            then_expr=corpo_then,
            else_expr=corpo_else
        )
        
        if self.atual() and self.atual()['tipo'] in ['OP', 'LE']:
            operador = self.comer(self.atual()['tipo'])['valor']
            proxima_expr = self.parse_expressao()
            return OperacaoBinaria(
                linha=t['linha'],
                esquerda=no_retorno,
                operador=operador,
                direita=proxima_expr
            )
            
        return no_retorno
        
    def parse_while(self):
        t = self.comer('KEYWORD', 'while')   
        condicao = self.parse_expressao()   
        self.comer('KEYWORD', 'loop')       
        corpo = self.parse_expressao()      
        self.comer('KEYWORD', 'pool')       
        
        return While(
            linha=t['linha'],
            condicao=condicao,
            corpo=corpo
        )
        
    def parse_new(self):
        t = self.comer('KEYWORD', 'new')
        tipo = self.comer('TYPE_ID')
        
        no_retorno = Instanciacao(linha=tipo['linha'], classe=tipo['valor'])
        
        while self.atual() and self.atual()['valor'] == '.':
            self.comer('PUNCT', '.')          
            id_metodo = self.comer('ID')      
            self.comer('PUNCT', '(')          
            
            argumentos = []
            if self.atual() and self.atual()['valor'] != ')':
                while True:
                    argumentos.append(self.parse_expressao())
                    if self.atual() and self.atual()['valor'] == ',':
                        self.comer('PUNCT', ',')
                    else:
                        break
                        
            self.comer('PUNCT', ')')          
            
            no_retorno = ChamadaMetodoObjeto(
                linha=t['linha'],
                objeto=no_retorno,
                metodo=id_metodo['valor'],
                argumentos=argumentos
            )
            
        return no_retorno
        

    def parse_let(self):
        t = self.comer('KEYWORD', 'let')
        declaracoes = []  
        
        while True:
            id_nome = self.comer('ID')
            self.comer('PUNCT', ':')
            tipo = self.comer('TYPE_ID')
            
            expressao_inicial = None
            if self.atual() and self.atual()['valor'] == '<-':
                self.comer('ASSIGN')
                expressao_inicial = self.parse_expressao() 
                
            declaracoes.append({
                "nome": id_nome['valor'],
                "tipo": tipo['valor'],
                "inicializacao": expressao_inicial
            })
            
            if self.atual() and self.atual()['valor'] == ',':
                self.comer('PUNCT', ',')
            else:
                break
                
        self.comer('KEYWORD', 'in')
        corpo = self.parse_expressao()
        
        return Let(
            linha=t['linha'],
            declaracoes=declaracoes,
            corpo=corpo
        )
        
    def parse_case(self):
        t = self.comer('KEYWORD', 'case')
        expressao_principal = self.parse_expressao() 
        self.comer('KEYWORD', 'of')
        
        ramos = []
        while self.atual() and self.atual()['valor'] != 'esac':
            id_ramo = self.comer('ID')       
            self.comer('PUNCT', ':')
            tipo_ramo = self.comer('TYPE_ID') 
            self.comer('DARROW', '=>')       
            expr_ramo = self.parse_expressao() 
            self.comer('PUNCT', ';')          
            
            ramos.append({
                "id": id_ramo['valor'],
                "tipo": tipo_ramo['valor'],
                "expressao": expr_ramo
            })
            
        self.comer('KEYWORD', 'esac') 
        return Case(
            linha=t['linha'],
            expressao=expressao_principal,
            ramos=ramos
        )

    def parse_bloco(self):
        self.comer('PUNCT', '{')
        corpo = []
        
        while self.atual() and self.atual()['valor'] != '}':
            expr = self.parse_expressao()
            if expr:
                corpo.append(expr)
            self.comer('PUNCT', ';')
            
        self.comer('PUNCT', '}')
        return Bloco(expressoes=corpo)


# --- ANALISADOR SEMÂNTICO ---

class SemanticError(Exception):
    """Exceção customizada para erros semânticos."""
    pass

class AnalisadorSemantico:
    def __init__(self, ast):
        self.ast = ast
        self.escopos = []
        # === POPULANDO O GLOBAL_ENV COM AS CLASSES NATIVAS ===
        self.global_env = {
            "Object": {
                "pai": None,
                "atributos": {},
                "metodos": {
                    "abort": {"retorno": "Object", "parametros": []},
                    "type_name": {"retorno": "String", "parametros": []},
                    "copy": {"retorno": "SELF_TYPE", "parametros": []}
                }
            },
            "IO": {
                "pai": "Object",
                "atributos": {},
                "metodos": {
                    "out_string": {"retorno": "SELF_TYPE", "parametros": [("x", "String")]},
                    "out_int": {"retorno": "SELF_TYPE", "parametros": [("x", "Int")]},
                    "in_string": {"retorno": "String", "parametros": []},
                    "in_int": {"retorno": "Int", "parametros": []}
                }
            },
            "Int": {"pai": "Object", "atributos": {}, "metodos": {}},
            "Bool": {"pai": "Object", "atributos": {}, "metodos": {}},
            "String": {
                "pai": "Object", 
                "atributos": {}, 
                "metodos": {
                    "length": {"retorno": "Int", "parametros": []},
                    "concat": {"retorno": "String", "parametros": [("s", "String")]},
                    "substr": {"retorno": "String", "parametros": [("i", "Int"), ("l", "Int")]}
                }
            }
        }
        
        self.classe_atual = None

    # --- GERENCIAMENTO DE ESCOPO ---
    
    def entrar_escopo(self):
        self.escopos.append({})

    def sair_escopo(self):
        if self.escopos:
            self.escopos.pop()

    def declarar_variavel(self, nome, tipo, linha):
        escopo_atual = self.escopos[-1]
        if nome in escopo_atual:
            raise SemanticError(f"Erro Semântico na linha {linha}: Redeclaração do identificador '{nome}' no mesmo escopo.")
        escopo_atual[nome] = tipo

    def buscar_variavel(self, nome, linha):
        if nome == "self":
            return self.classe_atual if self.classe_atual else "Object"

        for escopo in reversed(self.escopos):
            if nome in escopo:
                return escopo[nome]
                
        if self.classe_atual and self.classe_atual in self.global_env:
            atributos = self.global_env[self.classe_atual].get("atributos", {})
            if nome in atributos:
                return atributos[nome]
                
        foco = self.global_env.get(self.classe_atual, {}).get("pai") if self.classe_atual else None
        while foco is not None:
            if foco in self.global_env:
                atributos_pai = self.global_env[foco].get("atributos", {})
                if nome in atributos_pai:
                    return atributos_pai[nome]
            foco = self.global_env.get(foco, {}).get("pai")

        return "Object"
        
    def e_subtipo(self, tipo_derivado, tipo_base):
        if tipo_base == "SELF_TYPE":
            return tipo_derivado in ["SELF_TYPE", self.classe_atual]
            
        if tipo_derivado == "SELF_TYPE":
            tipo_derivado = self.classe_atual

        if tipo_derivado == tipo_base or tipo_base == "Object":
            return True
            
        foco = tipo_derivado
        while foco is not None:
            if foco == tipo_base:
                return True
            foco = self.global_env.get(foco, {}).get("pai")
            
        return False
        
    def menor_ancestral_comum(self, tipo_a, tipo_b):
        if tipo_a == tipo_b:
            return tipo_a
        if tipo_a == "SELF_TYPE":
            tipo_a = self.classe_atual
        if tipo_b == "SELF_TYPE":
            tipo_b = self.classe_atual

        caminho_a = []
        foco = tipo_a
        while foco is not None:
            caminho_a.append(foco)
            foco = self.global_env.get(foco, {}).get("pai")
        if "Object" not in caminho_a:
            caminho_a.append("Object")

        foco = tipo_b
        while foco is not None:
            if foco in caminho_a:
                return foco
            foco = self.global_env.get(foco, {}).get("pai")

        return "Object"

    # --- TRAVESSIA E VALIDAÇÃO ---

    def analisar(self):
        # CORREÇÃO AQUI: Verificação direta usando isinstance
        if not self.ast or not isinstance(self.ast, Programa):
            return
        
        self._coletar_ambiente_global()
        
        for no_classe in self.ast.classes:
            self._analisar_classe(no_classe)

    def _coletar_ambiente_global(self):
        for no_classe in self.ast.classes:
            nome_classe = no_classe.nome
            pai = no_classe.pai
            
            if nome_classe in self.global_env:
                raise SemanticError(f"Erro Semântico: Classe '{nome_classe}' redefinida.")
                
            self.global_env[nome_classe] = {
                "pai": pai,
                "metodos": {},
                "atributos": {}
            }
            
            for feature in no_classe.features:
                if isinstance(feature, Metodo):
                    params = feature.parametros 
                    self.global_env[nome_classe]["metodos"][feature.nome] = {
                        "retorno": feature.retorno,
                        "params": params
                    }
                elif isinstance(feature, Atributo):
                    self.global_env[nome_classe]["atributos"][feature.nome] = feature.dado

    def _analisar_classe(self, no_classe):
        self.entrar_escopo()
        self.classe_atual = no_classe.nome
        
        self.declarar_variavel("self", no_classe.nome, 0)
        
        nome_classe = no_classe.nome
        for tab_attr, tipo_attr in self.global_env[nome_classe]["atributos"].items():
            self.declarar_variavel(tab_attr, tipo_attr, 0)
            
        for feature in no_classe.features:
            if isinstance(feature, Metodo):
                self._analisar_metodo(nome_classe, feature)
                
        self.sair_escopo()

    def _analisar_metodo(self, nome_classe, no_metodo):
        self.entrar_escopo() 
        
        params = no_metodo.parametros
        for p_nome, p_tipo, linha_param in params:
            self.declarar_variavel(p_nome, p_tipo, linha_param) 
            
        if no_metodo.corpo is not None:
            tipo_retornado_corpo = self._visitar_expressao(no_metodo.corpo)
            tipo_esperado = no_metodo.retorno
            metodo_nome = no_metodo.nome
            
            if not self.e_subtipo(tipo_retornado_corpo, tipo_esperado):
                linha = no_metodo.linha
                raise SemanticError(
                    f"Erro Semântico na linha {linha} (método '{metodo_nome}'): "
                    f"Tipo de retorno esperado '{tipo_esperado}', mas obteve '{tipo_retornado_corpo}' (não compatível)."
                )

        self.sair_escopo()

    def _visitar_expressao(self, no_expr):
        if not no_expr:
            return "Object"
            
        linha_no = getattr(no_expr, 'linha', 0)

        # Usando isinstance de forma limpa para mapear cada classe da AST
        if isinstance(no_expr, IntConst):
            return "Int"
            
        elif isinstance(no_expr, StrConst):
            return "String"
            
        elif isinstance(no_expr, BoolConst):
            return "Bool"
            
        elif isinstance(no_expr, Variavel):
            return self.buscar_variavel(no_expr.nome, linha_no)

        elif isinstance(no_expr, Instanciacao):
            return no_expr.classe

        elif isinstance(no_expr, Atribuicao):
            tipo_esquerda = self.buscar_variavel(no_expr.nome, linha_no)
            tipo_direita = self._visitar_expressao(no_expr.direita)
            
            if not self.e_subtipo(tipo_direita, tipo_esquerda):
                raise SemanticError(
                    f"Erro Semântico na linha {linha_no}: Incompatibilidade de tipos. "
                    f"Não é possível atribuir '{tipo_direita}' à variável '{no_expr.nome}' ({tipo_esquerda})."
                )
            return tipo_esquerda
            
        elif isinstance(no_expr, Negacao):
            tipo_expr = self._visitar_expressao(no_expr.expressao)
            if tipo_expr != "Int":
                raise SemanticError(f"Erro Semântico na linha {linha_no}: O operador '~' só se aplica a 'Int'.")
            return "Int"

        elif isinstance(no_expr, Bloco):
            if not no_expr.expressoes:
                return "Object"
            tipo_final = "Object"
            for expr in no_expr.expressoes:
                tipo_final = self._visitar_expressao(expr)
            return tipo_final

        elif isinstance(no_expr, If):
            self._visitar_expressao(no_expr.condicao)
            tipo_then = self._visitar_expressao(no_expr.then_expr)
            tipo_else = self._visitar_expressao(no_expr.else_expr)
            return self.menor_ancestral_comum(tipo_then, tipo_else)
            
        elif isinstance(no_expr, While):
            self._visitar_expressao(no_expr.condicao)
            self._visitar_expressao(no_expr.corpo)
            return "Object"    

        elif isinstance(no_expr, Let):
            self.entrar_escopo()
            for dec in no_expr.declaracoes:
                nome_var = dec["nome"]
                tipo_declarado = dec["tipo"]
                if dec.get("inicializacao"):
                    tipo_ini = self._visitar_expressao(dec["inicializacao"])
                    if not self.e_subtipo(tipo_ini, tipo_declarado):
                        raise SemanticError(f"Erro Semântico na linha {linha_no}: Inicialização do let inválida.")
                self.declarar_variavel(nome_var, tipo_declarado, linha_no)
                
            resultado = self._visitar_expressao(no_expr.corpo)
            self.sair_escopo()
            return resultado

        elif isinstance(no_expr, ChamadaMetodo):
            metodo_nome = no_expr.nome
            def _buscar_metodo_na_hierarquia(classe_nome, met_nome):
                foco = classe_nome
                while foco is not None:
                    if foco in self.global_env and met_nome in self.global_env[foco]["metodos"]:
                        return self.global_env[foco]["metodos"][met_nome]
                    foco = self.global_env.get(foco, {}).get("pai")
                return None

            assinatura_metodo = _buscar_metodo_na_hierarquia(self.classe_atual, metodo_nome)
            if assinatura_metodo:
                return assinatura_metodo["retorno"]
                
            raise SemanticError(f"Erro Semântico na linha {linha_no}: Método '{metodo_nome}' não declarado.")
        
        elif isinstance(no_expr, ChamadaMetodoObjeto):
            tipo_objeto = self._visitar_expressao(no_expr.objeto)
            metodo_nome = no_expr.metodo
            classe_alvo = no_expr.classe_estatica or tipo_objeto
            
            if classe_alvo == "SELF_TYPE":
                classe_alvo = self.classe_atual

            foco = classe_alvo
            while foco is not None:
                if foco in self.global_env and metodo_nome in self.global_env[foco]["metodos"]:
                    retorno_metodo = self.global_env[foco]["metodos"][metodo_nome]["retorno"]
                    if retorno_metodo == "SELF_TYPE":
                        return tipo_objeto
                    return retorno_metodo
                foco = self.global_env.get(foco, {}).get("pai")
                
            if metodo_nome in ["out_string", "out_int", "in_string", "in_int"]:
                return "Object"
            return "Object"

        elif isinstance(no_expr, OperacaoBinaria):
            tipo_esq = self._visitar_expressao(no_expr.esquerda)
            tipo_dir = self._visitar_expressao(no_expr.direita)
            if no_expr.operador in ['+', '-', '*', '/']:
                if tipo_esq != "Int" or tipo_dir != "Int":
                    raise SemanticError(f"Erro Semântico na linha {linha_no}: Operação matemática exige inteiros.")
                return "Int"
            # Operadores de comparação (<, <=, =) retornam Bool no Cool
            return "Bool"
            
        elif isinstance(no_expr, Case):
            self._visitar_expressao(no_expr.expressao)
            tipos_ramos = []
            for ramo in no_expr.ramos:
                self.entrar_escopo()
                self.declarar_variavel(ramo["id"], ramo["tipo"], linha_no)
                tipo_ramo = self._visitar_expressao(ramo["expressao"])
                tipos_ramos.append(tipo_ramo)
                self.sair_escopo()
            
            tipo_final = tipos_ramos[0]
            for t in tipos_ramos[1:]:
                tipo_final = self.menor_ancestral_comum(tipo_final, t)
            return tipo_final
            
        elif isinstance(no_expr, NegacaoLogica):
            self._visitar_expressao(no_expr.expressao)
            return "Bool"

        print(f"DEBUG: Nó não tratado identificado: {type(no_expr).__name__}")
        return "Object"


# --- EXECUÇÃO ATUALIZADA ---

arquivo = 'exemplo.cl'

try:
    # 1. Execução do Analisador Léxico
    tokens = lexer_cool(arquivo)
    
    if tokens:
        print(f"\n{'--- TABELA DE TOKENS (LÉXICO) ---':^35}")
        print(f"{'LINHA':<7} | {'TIPO':<10} | {'VALOR'}")
        print("-" * 35)
        for t in tokens:
            print(f"{t['linha']:<7} | {t['tipo']:<10} | {t['valor']}")
            
        # 2. Execução do Parser (Sintático)
        parser = ParserCool(tokens)
        ast = parser.parse_programa()
        print("\n" + "="*40)
        print("✓ SUCESSO SINTÁTICO: Árvore AST Gerada!")
        print("="*40)
        
        # 3. Execução do Analisador Semântico
        print("\nIniciando Análise Semântica...")
        semantic_analyzer = AnalisadorSemantico(ast)
        semantic_analyzer.analisar()
        
        print("="*40)
        print("✓ SUCESSO SEMÂNTICO: O código foi validado com sucesso!")
        print("="*40)
        
        # 🚀 4. NOVO: GERAÇÃO DE CÓDIGO BRIL
        print("\nIniciando Geração de Código Bril...")
        gerador_bril = BrilCodeGenerator()
        codigo_final_bril = gerador_bril.gerar(ast)
        
        print("\n" + "-"*15 + " CÓDIGO BRIL GERADO " + "-"*15)
        print(codigo_final_bril)
        print("-" * 50)
        
        # Opcional: Se quiser salvar direto num arquivo .bril para usar o bril2json depois:
        with open("resultado.bril", "w", encoding="utf-8") as f:
            f.write(codigo_final_bril)
        print("✓ Arquivo 'resultado.bril' salvo com sucesso!")

except LexicalError as e:
    print(f"\n✗ ERRO LÉXICO: {e}")
except SyntaxError as e:
    print(f"\n✗ ERRO SINTÁTICO: {e}")
except SemanticError as e:
    print(f"\n✗ ERRO SEMÂNTICO: {e}")