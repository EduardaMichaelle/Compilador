class Cadastro {
    identificador : Int;

    configurar_id() : Object {
        {
            -- ERRO PRINCIPAL: Incompatibilidade de tipos (Type Mismatch)
            -- 'identificador' é do tipo Int, mas está recebendo uma constante do tipo String
            identificador <- "ID_999"; 
        }
    };
};