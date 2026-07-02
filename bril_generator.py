from ast_nodes import *

class BrilCodeGenerator:
    def __init__(self):
        self.codigo_bril = []      # Guarda as linhas de código geradas
        self.contador_temp = 0     # Gerador de variáveis temporárias (v0, v1, v2...)
        self.contador_rotulo = 0   # Contador para rótulos únicos (labels)
        self.variaveis_locais = {} # Tabela de símbolos de geração de código
        self.classe_atual = ""

    def gerar_temp(self) -> str:
        """Gera um nome de variável temporária única."""
        nome = f"v{self.contador_temp}"
        self.contador_temp += 1
        return nome

    def gerar_rotulo(self, nome_base: str) -> str:
        """Gera um nome de rótulo único baseado em um nome base."""
        rotulo = f"{nome_base}{self.contador_rotulo}"
        self.contador_rotulo += 1
        return rotulo

    def emitir(self, linha_comando: str):
        """Adiciona uma linha de instrução Bril com a indentação correta."""
        self.codigo_bril.append(f"  {linha_comando}")

    def emitir_rotulo(self, rotulo: str):
        """Adiciona um rótulo (label) sem indentação."""
        self.codigo_bril.append(f"{rotulo}:")

    def gerar(self, ast_raiz) -> str:
        """Método principal que inicia a geração de código a partir da raiz."""
        if isinstance(ast_raiz, Programa):
            for no_classe in ast_raiz.classes:
                self.visitar_classe(no_classe)
        return "\n".join(self.codigo_bril)

    def visitar_classe(self, no_classe: Classe):
        self.classe_atual = no_classe.nome
        self.variaveis_locais = {}
        
        # Guarda os atributos para uso posterior se for a classe Main
        if no_classe.nome == "Main":
            self.atributos_main_pendentes = [f for f in no_classe.features if isinstance(f, Atributo)]

        # Mapeia os atributos na tabela de símbolos
        for feature in no_classe.features:
            if isinstance(feature, Atributo):
                self.variaveis_locais[feature.nome] = feature.nome

        # Visita os métodos
        for feature in no_classe.features:
            if isinstance(feature, Metodo):
                self.visitar_metodo(no_classe.nome, feature)

    def visitar_metodo(self, nome_classe: str, no_metodo: Metodo):
        if nome_classe == "Main" and no_metodo.nome == "main":
            self.codigo_bril.append("@main {")
            
            # 💡 CORREÇÃO AQUI: Extrair e visitar a expressão real de inicialização do atributo
            if hasattr(self, 'atributos_main_pendentes'):
                for no_atrib in self.atributos_main_pendentes:
                    if hasattr(no_atrib, 'inicializacao') and no_atrib.inicializacao is not None:
                        # Em vez de visitar o nó do Atributo inteiro, visitamos a EXPRESSÃO dentro dele!
                        reg_ini = self.visitar_expressao(no_atrib.inicializacao)
                        
                        # E se o atributo tiver um nome, salvamos o resultado dele na variável correspondente
                        if reg_ini and hasattr(no_atrib, 'nome'):
                            self.emitir(f"{no_atrib.nome}: int = id {reg_ini};")
        else:
            self.codigo_bril.append(f"@{nome_classe}_{no_metodo.nome} {{")

        # Registra os parâmetros do método no ambiente local
        params = no_metodo.parametros if hasattr(no_metodo, 'parametros') else []
        for p in params:
            if isinstance(p, tuple) and len(p) > 0:
                self.variaveis_locais[p[0]] = p[0]
            elif hasattr(p, 'nome'):
                self.variaveis_locais[p.nome] = p.nome

        reg_final = self.visitar_expressao(no_metodo.corpo)
        
        if reg_final and reg_final.strip():
            self.emitir(f"ret {reg_final};")
        else:
            self.emitir("ret;")
            
        self.codigo_bril.append("}\n")

    def visitar_expressao(self, no_expr) -> str:
        if no_expr is None:
            return ""

        if isinstance(no_expr, IntConst):
            tmp = self.gerar_temp()
            self.emitir(f"{tmp}: int = const {no_expr.valor};")
            return tmp

        elif isinstance(no_expr, StrConst):
            tmp = self.gerar_temp()
            valor_limpo = no_expr.valor.replace('\n', '\\n')
            self.emitir(f"{tmp}: string = const \"{valor_limpo}\";")
            return tmp

        elif isinstance(no_expr, BoolConst):
            tmp = self.gerar_temp()
            val = "true" if no_expr.valor else "false"
            self.emitir(f"{tmp}: bool = const {val};")
            return tmp

        elif isinstance(no_expr, Variavel):
            if no_expr.nome in self.variaveis_locais:
                return self.variaveis_locais[no_expr.nome]
            # Fallback seguro para evitar "id ;"
            tmp = self.gerar_temp()
            self.emitir(f"{tmp}: int = const 0;")
            return tmp

        elif isinstance(no_expr, Atribuicao):
            reg_dir = self.visitar_expressao(no_expr.direita)
            if not reg_dir or not reg_dir.strip():
                reg_dir = self.gerar_temp()
                self.emitir(f"{reg_dir}: int = const 0;")
                
            if no_expr.nome not in self.variaveis_locais:
                self.variaveis_locais[no_expr.nome] = no_expr.nome
                
            reg_destino = self.variaveis_locais[no_expr.nome]
            self.emitir(f"{reg_destino}: int = id {reg_dir};")
            return reg_destino

        elif isinstance(no_expr, Bloco):
            ultimo_reg = ""
            for expr in no_expr.expressoes:
                ultimo_reg = self.visitar_expressao(expr)
            if not ultimo_reg:
                ultimo_reg = self.gerar_temp()
                self.emitir(f"{ultimo_reg}: int = const 0;")
            return ultimo_reg

        elif isinstance(no_expr, Let):
            escopo_anterior = self.variaveis_locais.copy()
            for dec in no_expr.declaracoes:
                nome_var = dec["nome"]
                if dec.get("inicializacao"):
                    reg_ini = self.visitar_expressao(dec["inicializacao"])
                else:
                    reg_ini = self.gerar_temp()
                    padrao = "0" if dec["tipo"] == "Int" else '""'
                    self.emitir(f"{reg_ini}: int = const {padrao};")
                
                self.variaveis_locais[nome_var] = nome_var
                self.emitir(f"{nome_var}: int = id {reg_ini};")
            
            reg_corpo = self.visitar_expressao(no_expr.corpo)
            self.variaveis_locais = escopo_anterior
            return reg_corpo

        elif isinstance(no_expr, If):
            reg_condicao = self.visitar_expressao(no_expr.condicao)
            if not reg_condicao:
                reg_condicao = self.gerar_temp()
                self.emitir(f"{reg_condicao}: bool = const false;")
                
            lbl_then = self.gerar_rotulo("then")
            lbl_else = self.gerar_rotulo("else")
            lbl_fim = self.gerar_rotulo("fim_if")
            
            reg_resultado = self.gerar_temp()
            self.emitir(f"{reg_resultado}: int = const 0;") 
            self.emitir(f"br {reg_condicao} {lbl_then} {lbl_else};")
            
            self.emitir_rotulo(lbl_then)
            reg_then = self.visitar_expressao(no_expr.then_expr)
            if reg_then:
                self.emitir(f"{reg_resultado}: int = id {reg_then};")
            self.emitir(f"jmp {lbl_fim};")
            
            self.emitir_rotulo(lbl_else)
            reg_else = self.visitar_expressao(no_expr.else_expr)
            if reg_else:
                self.emitir(f"{reg_resultado}: int = id {reg_else};")
            self.emitir(f"jmp {lbl_fim};")
            
            self.emitir_rotulo(lbl_fim)
            return reg_resultado

        elif isinstance(no_expr, While):
            lbl_teste = self.gerar_rotulo("while_teste")
            lbl_corpo = self.gerar_rotulo("while_corpo")
            lbl_fim = self.gerar_rotulo("while_fim")
            
            self.emitir_rotulo(lbl_teste)
            reg_condicao = self.visitar_expressao(no_expr.condicao)
            if not reg_condicao:
                reg_condicao = self.gerar_temp()
                self.emitir(f"{reg_condicao}: bool = const false;")
                
            self.emitir(f"br {reg_condicao} {lbl_corpo} {lbl_fim};")
            
            self.emitir_rotulo(lbl_corpo)
            self.visitar_expressao(no_expr.corpo)
            self.emitir(f"jmp {lbl_teste};")
            
            self.emitir_rotulo(lbl_fim)
            tmp_void = self.gerar_temp()
            self.emitir(f"{tmp_void}: int = const 0;")
            return tmp_void

        elif isinstance(no_expr, ChamadaMetodo) or isinstance(no_expr, ChamadaMetodoObjeto):
            regs_args = []
            argumentos = no_expr.argumentos if hasattr(no_expr, 'argumentos') else []
            for arg in argumentos:
                reg_arg = self.visitar_expressao(arg)
                if reg_arg:
                    regs_args.append(reg_arg)
            
            metodo = no_expr.metodo if hasattr(no_expr, 'metodo') else no_expr.nome
            
            if metodo in ["out_string", "out_int"]:
                args_str = " ".join(regs_args)
                if args_str.strip():
                    self.emitir(f"print {args_str};")
                return ""
            
            tmp = self.gerar_temp()
            args_str = " ".join(regs_args)
            # Vincula dinamicamente ao escopo da classe atual para evitar chamadas soltas
            self.emitir(f"{tmp}: int = call @{self.classe_atual}_{metodo} {args_str};")
            return tmp

        elif isinstance(no_expr, OperacaoBinaria):
            reg_esq = self.visitar_expressao(no_expr.esquerda)
            reg_dir = self.visitar_expressao(no_expr.direita)
            
            if not reg_esq:
                reg_esq = self.gerar_temp()
                self.emitir(f"{reg_esq}: int = const 0;")
            if not reg_dir:
                reg_dir = self.gerar_temp()
                self.emitir(f"{reg_dir}: int = const 0;")
                
            tmp = self.gerar_temp()
            traducao_ops = {'+': 'add', '-': 'sub', '*': 'mul', '/': 'div', '<': 'lt', '<=': 'le', '=': 'eq'}
            op_bril = traducao_ops.get(no_expr.operador, 'add')
            tipo_destino = "bool" if no_expr.operador in ['<', '<=', '='] else "int"
            
            self.emitir(f"{tmp}: {tipo_destino} = {op_bril} {reg_esq} {reg_dir};")
            return tmp

        return ""