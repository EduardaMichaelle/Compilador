class Matematica {
    -- ERRO PRINCIPAL: Redeclaração de parâmetro no mesmo escopo
    somar_duplicado(x : Int, x : Int) : Int {
        {
            x + x;
        }
    };
};
