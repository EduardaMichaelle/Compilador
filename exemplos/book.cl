Class Book inherits IO {
    title : Int;
    author : Int;

    initBook(title_p : Int, author_p : Int) : Book {
        {
            title <- title_p;
            author <- author_p;
            self;
        }
    };

    print() : Book {
        {
            out_int(title);
            out_int(author);
            self;
        }
    };
};

Class Article inherits Book {
    per_title : Int;

    initArticle(title_p : Int, author_p : Int,
        per_title_p : Int) : Article {
        {
            initBook(title_p, author_p);
            per_title <- per_title_p;
            self;
        }
    };

    print() : Book {
        {
            self@Book.print();
            out_int(per_title);
            self;
        }
    };
};

Class Main {

    main() : Object {
        (let a_book : Book <-
            (new Article).initArticle(100, 7, 10)
        in
            {
               a_book.print();
            }
        )
    };
};
