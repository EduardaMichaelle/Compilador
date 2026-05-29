class Matematica {
    -- ERRO PRINCIPAL: Redeclaração de parâmetro no mesmo escopo
    -- O parâmetro 'n' está sendo declarado duas vezes na assinatura do método
    somar_duplicado(x : Int, x : Int) : Int {
        {
            x + x;
        }
    };
};