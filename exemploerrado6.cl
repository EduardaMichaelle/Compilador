class Execucao {
    valor : Int <- 42;

    processar() : Object {
        {
            -- ERRO PRINCIPAL: Chamada a um método que não existe
            -- O método 'calcular_raiz' não foi definido nesta classe nem em Object
            calcular_raiz(valor); 
        }
    };
};