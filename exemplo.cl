(* 
   Este é um comentário de bloco.
   O compilador deve ignorar tudo isso aqui.
   Pode ter inclusive palavras-chave como class ou if aqui dentro 
   que não devem ser transformadas em tokens!
*)

class Cliente {
    nome : String;
    id : Int;

    -- Comentário de linha única: define a inicialização
    init(n : String, i : Int) : Cliente {
        {
            nome <- n;
            id <- i;
            self;
        }
    };
};

class Main inherits IO {
    contagem : Int <- 0;

    main() : Object {
        let msg : String <- "Olá, mundo!\n" in {
            out_string(msg); -- Imprime a saudação
            
            if contagem <= 10 then
                out_string("Contagem baixa\n")
            else
                out_string("Contagem alta\n")
            fi;
        }
    };
};