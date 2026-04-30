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
        ('LE',       r'<='), # Operador Menor ou Igual
        ('ID',       r'[A-Za-z_][A-Za-z0-9_]*'),
        ('OP',       r'[+\-*/<>=~]'), # Outros operadores
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
            raise SyntaxError(f"Erro Sintático: Fim de arquivo inesperado.")

        tipo_token = token['tipo']
        valor_token = token['valor']

        # Ajuste para aceitar ID/KEYWORD e OP/LE
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

# Arvore 
    def parse_classe(self):
        self.comer('KEYWORD', 'class')
        nome = self.comer('ID')
        pai = None
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
        
        if self.atual() and self.atual()['valor'] == '(':
            self.comer('PUNCT', '(')
            while self.atual() and self.atual()['valor'] != ')':
                self.comer('ID')
                self.comer('PUNCT', ':')
                self.comer('ID')
                if self.atual() and self.atual()['valor'] == ',':
                    self.comer('PUNCT', ',')
            self.comer('PUNCT', ')')
            self.comer('PUNCT', ':')
            tipo_retorno = self.comer('ID') 
            self.comer('PUNCT', '{')
            corpo = self.parse_expressao()
            self.comer('PUNCT', '}')
            self.comer('PUNCT', ';')
            return {"tipo": "Metodo", "nome": id_nome['valor'], "retorno": tipo_retorno['valor']}
        
        else:
            self.comer('PUNCT', ':')
            tipo = self.comer('ID')
            if self.atual() and self.atual()['valor'] == '<-':
                self.comer('ASSIGN')
                self.pos += 1 
            
            if self.atual() and self.atual()['valor'] == ';':
                self.comer('PUNCT', ';')
            elif self.atual() and self.atual()['valor'] == ',':
                self.comer('PUNCT', ',')
                
            return {"tipo": "Atributo", "nome": id_nome['valor'], "dado": tipo['valor']}

    def parse_expressao(self):
        t = self.atual()
        if not t: return None

        if t['valor'] == 'if':
            return self.parse_if()
        elif t['valor'] == 'let':
            return self.parse_let()
        elif t['valor'] == '{':
            return self.parse_bloco()
        elif t['tipo'] == 'ID':
            var = self.comer('ID')
            
            # --- ADIÇÃO: VERIFICA ERRO DE ATRIBUIÇÃO '=' NO LUGAR DE '<-' ---
            if self.atual() and self.atual()['valor'] == '=':
                raise SyntaxError(f"Erro na linha {t['linha']}: Você usou '=' para atribuição, mas em COOL usa-se '<-'")
            
            if self.atual() and self.atual()['valor'] == '(':
                self.comer('PUNCT', '(')
                if self.atual() and self.atual()['tipo'] in ['STRING', 'ID']:
                    self.pos += 1
                self.comer('PUNCT', ')')
                return {"tipo": "ChamadaMetodo", "nome": var['valor']}
            elif self.atual() and self.atual()['valor'] == '<-':
                self.comer('ASSIGN')
                self.parse_expressao() # Tenta ler o que vem depois da atribuição
                return {"tipo": "Atribuicao", "nome": var['valor']}
            return {"tipo": "Variavel", "nome": var['valor']}
            
        return self.comer(t['tipo'])
        
    # Fim Arvore

    def parse_if(self):
        self.comer('KEYWORD', 'if')
        self.parse_condicao()
        self.comer('KEYWORD', 'then')
        self.parse_expressao()
        self.comer('KEYWORD', 'else')
        self.parse_expressao()
        self.comer('KEYWORD', 'fi')
        return {"tipo": "If"}
        
    def parse_condicao(self):
        # Aceita ID ou NUMBER no lado esquerdo
        if self.atual()['tipo'] in ['ID', 'NUMBER']:
            self.pos += 1
        else:
            raise SyntaxError(f"Erro na linha {self.atual()['linha']}: Esperado ID ou NUMBER, mas veio {self.atual()['valor']}")
            
        self.comer('OP') # Aceita <, >, <=, etc (ajustado no comer)

        # Aceita ID ou NUMBER no lado direito
        if self.atual()['tipo'] in ['ID', 'NUMBER']:
            self.pos += 1
        else:
            raise SyntaxError(f"Erro na linha {self.atual()['linha']}: Esperado ID ou NUMBER, mas veio {self.atual()['valor']}")

    def parse_let(self):
        self.comer('KEYWORD', 'let')
        while self.atual() and self.atual()['valor'] != 'in':
            self.parse_feature()
        self.comer('KEYWORD', 'in')
        return {"tipo": "Let", "corpo": self.parse_expressao()}

    def parse_bloco(self):
        self.comer('PUNCT', '{')
        while self.atual() and self.atual()['valor'] != '}':
            self.parse_expressao()
            if self.atual() and self.atual()['valor'] == ';':
                self.comer('PUNCT', ';')
        self.comer('PUNCT', '}')
        return {"tipo": "Bloco"}

# --- EXECUÇÃO ---

arquivo = 'exemplo.cl'
tokens = lexer_cool(arquivo)

if tokens:
    print(f"\n{'--- TABELA DE TOKENS (LÉXICO) ---':^35}")
    print(f"{'LINHA':<7} | {'TIPO':<10} | {'VALOR'}")
    print("-" * 35)
    for t in tokens:
        print(f"{t['linha']:<7} | {t['tipo']:<10} | {t['valor']}")

    try:
        parser = ParserCool(tokens)
        ast = parser.parse_programa()
        print("\n" + "="*40)
        print("✓ SUCESSO: O código é sintaticamente correto!")
        print("="*40)
        print("\nÁrvore de Sintaxe Abstrata (AST) Gerada:")
        print(json.dumps(ast, indent=2, ensure_ascii=False))
    except SyntaxError as e:
        print(f"\n✗ {e}")
