class Teste {
    valor : String;

    -- Erro 1: O método diz que retorna Int, mas retorna uma String
    retorna_errado() : String {
        "Isso é uma string, não um inteiro"
    };

    -- Erro 2: Uso de uma variável que não  no escopo
    calcular(x : Int) : Object {
        {
            valor <- y; 
            self;
        }
    };
};