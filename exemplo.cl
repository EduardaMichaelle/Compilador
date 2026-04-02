class Main inherits IO {
  main(): Object {
    let x: Int <- 10, y: Int <- 20 in {
      if x < y then
        out_string("x é menor\n")
      else
        out_string("x é maior\n")
      fi;
    };
  };
};