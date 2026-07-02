from dataclasses import dataclass, field
from typing import List, Optional, Any

# Nó base do qual todos os outros herdarão para garantir que guardamos a linha para relatórios de erro
@dataclass
class ASTNode:
    linha: int = 0

# --- ESTRUTURA DO PROGRAMA ---

@dataclass
class Programa(ASTNode):
    classes: List['Classe'] = field(default_factory=list)

@dataclass
class Classe(ASTNode):
    nome: str = ""
    pai: str = "Object"
    features: List[Any] = field(default_factory=list)

@dataclass
class Metodo(ASTNode):
    nome: str = ""
    retorno: str = ""
    parametros: List[tuple] = field(default_factory=list) # Lista de tuplas (nome, tipo, linha)
    corpo: Any = None

@dataclass
class Atributo(ASTNode):
    nome: str = ""
    dado: str = ""
    inicializacao: Optional[Any] = None

# --- EXPRESSÕES ---

@dataclass
class IntConst(ASTNode):
    valor: str = ""  # Mantido como str do lexer ou convertido para int

@dataclass
class StrConst(ASTNode):
    valor: str = ""

@dataclass
class BoolConst(ASTNode):
    valor: str = ""  # 'true' ou 'false'

@dataclass
class Variavel(ASTNode):
    nome: str = ""

@dataclass
class Atribuicao(ASTNode):
    nome: str = ""
    direita: Any = None

@dataclass
class OperacaoBinaria(ASTNode):
    esquerda: Any = None
    operador: str = ""
    direita: Any = None

@dataclass
class If(ASTNode):
    condicao: Any = None
    then_expr: Any = None
    else_expr: Any = None

@dataclass
class While(ASTNode):
    condicao: Any = None
    corpo: Any = None

@dataclass
class Bloco(ASTNode):
    expressoes: List[Any] = field(default_factory=list)

@dataclass
class Let(ASTNode):
    declaracoes: List[dict] = field(default_factory=list) # Cada dict: {"nome": str, "tipo": str, "inicializacao": Any}
    corpo: Any = None

@dataclass
class Case(ASTNode):
    expressao: Any = None
    ramos: List[dict] = field(default_factory=list) # Cada dict: {"id": str, "tipo": str, "expressao": Any}

@dataclass
class Instanciacao(ASTNode): # O "new" do Cool
    classe: str = ""

@dataclass
class Negacao(ASTNode): # O operador '~' do Cool
    expressao: Any = None

@dataclass
class NegacaoLogica(ASTNode): # O 'not' do Cool
    expressao: Any = None

@dataclass
class Isvoid(ASTNode):
    expressao: Any = None

@dataclass
class ChamadaMetodo(ASTNode): # Chamada local implicitamente no self: id(args)
    nome: str = ""
    argumentos: List[Any] = field(default_factory=list)

@dataclass
class ChamadaMetodoObjeto(ASTNode): # Chamada explícita: obj.metodo(args) ou obj@Classe.metodo(args)
    objeto: Any = None
    classe_estatica: Optional[str] = None
    metodo: str = ""
    argumentos: List[Any] = field(default_factory=list)