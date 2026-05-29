import re
import json

# --- ANALISADOR LÉXICO ---

def lexer_cool(caminho_arquivo):
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            codigo = f.read()
    except FileNotFoundError:
        print(f"Erro: O arquivo {caminho_arquivo} não foi encontrado.")
        return []

    token_patterns = [
        ('NEWLINE',  r'\n'),           
        ('COMMENT',  r'--.*|\(\*[\s\S]*?\*\)'), 
        ('KEYWORD',  r'\b(class|inherits|if|then|else|fi|let|in|inherits|main|Object|Int|String|Bool|IO|self)\b'),
        ('STRING',   r'".*?"'),
        ('NUMBER',   r'\d+'),
        ('ASSIGN',   r'<-'),
        ('LE',       r'<='), 
        ('ID',       r'[A-Za-z_][A-Za-z0-9_]*'),
        ('OP',       r'[+\-*/<>=~]'), 
        ('PUNCT',    r'[{}();:,.@]'),
        ('SKIP',     r'[ \t\r]+'),     
        ('MISMATCH', r'.'),            
    ]

    master_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_patterns)
    
    tokens_finais = []
    linha_atual = 1

    for mo in re.finditer(master_regex, codigo):
        kind = mo.lastgroup
        value = mo.group()
        
        if kind == 'NEWLINE':
            linha_atual += 1
        elif kind == 'SKIP':
            continue
        elif kind == 'COMMENT':
            linha_atual += value.count('\n')
            continue
        elif kind == 'MISMATCH':
            print(f'>>> ERRO LÉXICO: Caractere inválido "{value}" na linha {linha_atual}')
        else:
            tokens_finais.append({
                'tipo': kind,
                'valor': value,
                'linha': linha_atual
            })
            
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
        return {"tipo": "Programa", "corpo": classes}

    def parse_classe(self):
        self.comer('KEYWORD', 'class')
        nome = self.comer('ID')
        
        pai = 'Object'
        if self.atual() and self.atual()['valor'] == 'inherits':
            self.comer('KEYWORD', 'inherits')
            pai = self.comer('ID')['valor']
            
        self.comer('PUNCT', '{')
        features = []
        
        while self.atual() and self.atual()['valor'] != '}':
            features.append(self.parse_feature())
            
        self.comer('PUNCT', '}')
        self.comer('PUNCT', ';') 
        
        return {"tipo": "Classe", "nome": nome['valor'], "pai": pai, "features": features}

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
                linha_param = token_nome['linha'] # Captura a linha do parâmetro
                
                self.comer('PUNCT', ':')
                p_tipo = self.comer('ID')['valor']
                
                # Agora guardamos uma tupla de 3 elementos: (nome, tipo, linha)
                lista_de_parametros_capturados.append((p_nome, p_tipo, linha_param))
                
                if self.atual() and self.atual()['valor'] == ',':
                    self.comer('PUNCT', ',')
                    
            self.comer('PUNCT', ')')
            self.comer('PUNCT', ':')
            tipo_retorno = self.comer('ID') 
            self.comer('PUNCT', '{')
            corpo = self.parse_expressao()
            self.comer('PUNCT', '}')
            self.comer('PUNCT', ';') 
            
            return {
                "tipo": "Metodo", 
                "nome": id_nome['valor'], 
                "retorno": tipo_retorno['valor'],
                "parametros": lista_de_parametros_capturados,
                "corpo": corpo,
                "linha": linha_declaracao
            }
        
        # Caso contrário, é um ATRIBUTO
        else:
            self.comer('PUNCT', ':')
            tipo = self.comer('ID')
            if self.atual() and self.atual()['valor'] == '<-':
                self.comer('ASSIGN')
                self.pos += 1 
            
            self.comer('PUNCT', ';') 
            return {"tipo": "Atributo", "nome": id_nome['valor'], "dado": tipo['valor'], "linha": linha_declaracao}

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
            
        elif t['tipo'] in ['ID', 'KEYWORD']:
            var = self.comer(t['tipo']) 
            
            if self.atual() and self.atual()['valor'] == '=':
                raise SyntaxError(f"Erro na linha {t['linha']}: Você usou '=' para atribuição, mas em COOL usa-se '<-'")
            
            # Chamada de método: id( ... )
            if self.atual() and self.atual()['valor'] == '(':
                self.comer('PUNCT', '(')
                if self.atual() and self.atual()['tipo'] in ['STRING', 'ID', 'NUMBER']:
                    self.pos += 1
                self.comer('PUNCT', ')')
                no_retorno = {"tipo": "ChamadaMetodo", "nome": var['valor'], "linha": t['linha']}
                
            # Atribuição dinamicamente encadeada (id <- expressao)
            elif self.atual() and self.atual()['valor'] == '<-':
                self.comer('ASSIGN')
                expressao_direita = self.parse_expressao() 
                return {
                    "tipo": "Atribuicao", 
                    "nome": var['valor'], 
                    "direita": expressao_direita,
                    "linha": t['linha']
                }
            else:
                no_retorno = {"tipo": "Variavel", "nome": var['valor'], "linha": t['linha']}
                
            # --- SUPORTE A OPERAÇÕES MATEMÁTICAS/COMPARAÇÃO (Ex: n + n ou x < 10) ---
            if self.atual() and self.atual()['tipo'] in ['OP', 'LE']:
                operador = self.comer(self.atual()['tipo'])['valor']
                proxima_expr = self.parse_expressao() # Captura o lado direito recursivamente
                return {
                    "tipo": "OperacaoBinaria",
                    "esquerda": no_retorno,
                    "operador": operador,
                    "direita": proxima_expr,
                    "linha": t['linha']
                }
                
            return no_retorno
            
        elif t['tipo'] in ['STRING', 'NUMBER']:
            literal = self.comer(t['tipo'])
            no_retorno = {"tipo": t['tipo'], "valor": literal['valor'], "linha": literal['linha']}
            
            # Suporte a operações com números (Ex: 1 + 2)
            if self.atual() and self.atual()['tipo'] in ['OP', 'LE']:
                operador = self.comer(self.atual()['tipo'])['valor']
                proxima_expr = self.parse_expressao()
                return {
                    "tipo": "OperacaoBinaria",
                    "esquerda": no_retorno,
                    "operador": operador,
                    "direita": proxima_expr,
                    "linha": t['linha']
                }
            return no_retorno
            
        raise SyntaxError(f"Erro Sintático na linha {t['linha']}: Expressão inválida ou inesperada '{t['valor']}'")

    def parse_if(self):
        t = self.comer('KEYWORD', 'if')
        self.parse_condicao()
        self.comer('KEYWORD', 'then')
        self.parse_expressao()
        self.comer('KEYWORD', 'else')
        self.parse_expressao()
        self.comer('KEYWORD', 'fi')
        return {"tipo": "If", "linha": t['linha']}
        
    def parse_condicao(self):
        if self.atual()['tipo'] in ['ID', 'NUMBER']:
            self.pos += 1
        else:
            raise SyntaxError(f"Erro na linha {self.atual()['linha']}: Esperado ID ou NUMBER, mas veio {self.atual()['valor']}")
            
        self.comer('OP') 

        if self.atual()['tipo'] in ['ID', 'NUMBER']:
            self.pos += 1
        else:
            raise SyntaxError(f"Erro na linha {self.atual()['linha']}: Esperado ID ou NUMBER, mas veio {self.atual()['valor']}")

    def parse_let(self):
        t = self.comer('KEYWORD', 'let')
        while True:
            id_nome = self.comer('ID')
            self.comer('PUNCT', ':')
            tipo = self.comer('ID')
            
            if self.atual() and self.atual()['valor'] == '<-':
                self.comer('ASSIGN')
                self.parse_expressao() 
            
            if self.atual() and self.atual()['valor'] == ',':
                self.comer('PUNCT', ',')
            else:
                break
        
        self.comer('KEYWORD', 'in')
        corpo = self.parse_expressao()
        return {"tipo": "Let", "corpo": corpo, "linha": t['linha']}

    def parse_bloco(self):
        self.comer('PUNCT', '{')
        corpo = []
        
        while self.atual() and self.atual()['valor'] != '}':
            expr = self.parse_expressao()
            if expr:
                corpo.append(expr)
            self.comer('PUNCT', ';')
            
        self.comer('PUNCT', '}')
        return {"tipo": "Bloco", "expressoes": corpo}


# --- ANALISADOR SEMÂNTICO ---

class SemanticError(Exception):
    """Exceção customizada para erros semânticos."""
    pass

class AnalisadorSemantico:
    def __init__(self, ast):
        self.ast = ast
        self.escopos = []
        self.global_env = {}

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
        for escopo in reversed(self.escopos):
            if nome in escopo:
                return escopo[nome]
        raise SemanticError(f"Erro Semântico na linha {linha}: Variável '{nome}' não foi declarada antes do uso.")

    # --- TRAVESSIA E VALIDAÇÃO ---

    def analisar(self):
        if not self.ast or self.ast.get("tipo") != "Programa":
            return
        
        self._coletar_ambiente_global()
        
        for no_classe in self.ast["corpo"]:
            self._analisar_classe(no_classe)

    def _coletar_ambiente_global(self):
        for no_classe in self.ast["corpo"]:
            nome_classe = no_classe["nome"]
            pai = no_classe["pai"]
            
            if nome_classe in self.global_env:
                raise SemanticError(f"Erro Semântico: Classe '{nome_classe}' redefinida.")
                
            self.global_env[nome_classe] = {
                "pai": pai,
                "metodos": {},
                "atributos": {}
            }
            
            for feature in no_classe["features"]:
                if feature["tipo"] == "Metodo":
                    params = feature.get("parametros", []) 
                    self.global_env[nome_classe]["metodos"][feature["nome"]] = {
                        "retorno": feature["retorno"],
                        "params": params
                    }
                elif feature["tipo"] == "Atributo":
                    self.global_env[nome_classe]["atributos"][feature["nome"]] = feature["dado"]

    def _analisar_classe(self, no_classe):
        self.entrar_escopo()
        
        # Injeta o 'self' referenciando o tipo da própria classe atual
        self.declarar_variavel("self", no_classe["nome"], 0)
        
        nome_classe = no_classe["nome"]
        for tab_attr, tipo_attr in self.global_env[nome_classe]["atributos"].items():
            self.declarar_variavel(tab_attr, tipo_attr, 0)
            
        for feature in no_classe["features"]:
            if feature["tipo"] == "Metodo":
                self._analisar_metodo(nome_classe, feature)
                
        self.sair_escopo()

    def _analisar_metodo(self, nome_classe, no_metodo):
        self.entrar_escopo() # Escopo dos parâmetros do método
        
        params = no_metodo.get("parametros", [])
        # Desestruturando a nova tupla de 3 elementos (nome, tipo, linha)
        for p_nome, p_tipo, linha_param in params:
            self.declarar_variavel(p_nome, p_tipo, linha_param) # Passa a linha real!
            
        if "corpo" in no_metodo and no_metodo["corpo"] is not None:
            tipo_retornado_corpo = self._visitar_expressao(no_metodo["corpo"])
            
            tipo_esperado = no_metodo["retorno"]
            if tipo_esperado != "Object" and tipo_retornado_corpo != tipo_esperado:
                linha = no_metodo.get("linha", "desconhecida")
                raise SemanticError(
                    f"Erro Semântico na linha {linha} (método '{no_metodo['nome']}'): "
                    f"Tipo de retorno esperado '{tipo_esperado}', mas obteve '{tipo_retornado_corpo}'."
                )

        self.sair_escopo()

    def _visitar_expressao(self, no_expr):
        if not no_expr:
            return "Object"
            
        # Tratamento de nós terminais diretos mapeados por tokens
        if "tipo" in no_expr and "valor" in no_expr and "linha" in no_expr:
            tipo_token = no_expr["tipo"]
            if tipo_token == "NUMBER":
                return "Int"
            if tipo_token == "STRING":
                return "String"
            if tipo_token == "ID":
                return self.buscar_variavel(no_expr["valor"], no_expr["linha"])

        tipo_no = no_expr.get("tipo")
        linha_no = no_expr.get("linha", 0)

        if tipo_no == "Variavel":
            return self.buscar_variavel(no_expr["nome"], linha_no)

        # VALIDAÇÃO TOTALMENTE DINÂMICA DE ATRIBUIÇÃO
        elif tipo_no == "Atribuicao":
            tipo_esquerda = self.buscar_variavel(no_expr["nome"], linha_no)
            
            tipo_direita = "Object"
            if "direita" in no_expr:
                tipo_direita = self._visitar_expressao(no_expr["direita"]) # Avalia recursivamente o lado direito
            
            # CHAVE DA CORREÇÃO: Se ambos os tipos forem conhecidos e diferentes, temos uma quebra de sistema de tipos
            if tipo_esquerda != "Object" and tipo_direita != "Object" and tipo_esquerda != tipo_direita:
                raise SemanticError(
                    f"Erro Semântico na linha {linha_no}: Incompatibilidade de tipos (Type Mismatch). "
                    f"Não é possível atribuir o tipo '{tipo_direita}' à variável '{no_expr['nome']}' que foi declarada como '{tipo_esquerda}'."
                )
                
            return tipo_esquerda

        elif tipo_no == "Bloco":
            tipo_bloco = "Object"
            for expr in no_expr.get("expressoes", []):
                tipo_bloco = self._visitar_expressao(expr)
            return tipo_bloco 

        elif tipo_no == "If":
            return "Object"

        elif tipo_no == "Let":
            self.entrar_escopo()
            tipo_retorno_let = self._visitar_expressao(no_expr.get("corpo"))
            self.sair_escopo()
            return tipo_retorno_let

        elif tipo_no == "ChamadaMetodo":
            metodo_nome = no_expr["nome"]
            for classe, dados in self.global_env.items():
                if metodo_nome in dados["metodos"]:
                    return dados["metodos"][metodo_nome]["retorno"]
            
            if metodo_nome in ["out_string", "out_int", "in_string", "in_int"]:
                return "Object"
                
            raise SemanticError(f"Erro Semântico na linha {linha_no}: Chamada ao método '{metodo_nome}' não declarado.")
        
        elif tipo_no == "OperacaoBinaria":
            # Visita e valida recursivamente os dois lados da operação
            tipo_esq = self._visitar_expressao(no_expr["esquerda"])
            tipo_dir = self._visitar_expressao(no_expr["direita"])
            
            # Se for um operador matemático, idealmente ambos deveriam ser Int
            if no_expr["operador"] in ['+', '-', '*', '/']:
                if tipo_esq != "Int" or tipo_dir != "Int":
                    # Você pode optar por lançar um erro de tipos aqui no futuro se quiser!
                    pass
            return tipo_esq

        return "Object"


# --- EXECUÇÃO ATUALIZADA ---

arquivo = 'exemploerrado7.cl'
tokens = lexer_cool(arquivo)

if tokens:
    print(f"\n{'--- TABELA DE TOKENS (LÉXICO) ---':^35}")
    print(f"{'LINHA':<7} | {'TIPO':<10} | {'VALOR'}")
    print("-" * 35)
    for t in tokens:
        print(f"{t['linha']:<7} | {t['tipo']:<10} | {t['valor']}")
        
    try:
        # 1. Execução do Parser (Sintático)
        parser = ParserCool(tokens)
        ast = parser.parse_programa()
        print("\n" + "="*40)
        print("✓ SUCESSO SINTÁTICO: Árvore AST Gerada!")
        print("="*40)
        
        # 2. Execução do Analisador Semântico
        print("\nIniciando Análise Semântica...")
        semantic_analyzer = AnalisadorSemantico(ast)
        semantic_analyzer.analisar()
        
        print("="*40)
        print("✓ SUCESSO SEMÂNTICO: O código foi validado com sucesso!")
        print("="*40)
        
    except SyntaxError as e:
        print(f"\n✗ ERRO SINTÁTICO: {e}")
    except SemanticError as e:
        print(f"\n✗ ERRO SEMÂNTICO: {e}")
