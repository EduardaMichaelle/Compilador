import re

def lexer_simples(codigo):
    # Regex que separa palavras, números e símbolos
    tokens = re.findall(r'[A-Za-z_][A-Za-z0-9_]*|\d+|".*?"|<-|<=|[+\-*/<>=~{}();:,.@]',codigo)
    for token in tokens:
        print(token)

# Lê o arquivo
with open('exemplo.cl', 'r', encoding='utf-8') as f:
    codigo = f.read()

# Executa
lexer_simples(codigo)