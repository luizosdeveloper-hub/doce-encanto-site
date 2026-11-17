PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS produtos (
 id INTEGER PRIMARY KEY, nome TEXT NOT NULL, descricao TEXT NOT NULL,
 preco_centavos INTEGER NOT NULL CHECK(preco_centavos >= 0), emoji TEXT NOT NULL,
 ativo INTEGER NOT NULL DEFAULT 1 CHECK(ativo IN (0,1))
);
CREATE TABLE IF NOT EXISTS pedidos (
 id INTEGER PRIMARY KEY, nome TEXT NOT NULL, telefone TEXT NOT NULL, endereco TEXT NOT NULL,
 pagamento TEXT NOT NULL CHECK(pagamento IN ('Pix','Cartão na entrega')),
 total_centavos INTEGER NOT NULL CHECK(total_centavos >= 0),
 status TEXT NOT NULL DEFAULT 'Recebido' CHECK(status IN ('Recebido','Em preparo','Saiu para entrega','Entregue','Cancelado')),
 criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, codigo_acesso TEXT
);
CREATE TABLE IF NOT EXISTS itens_pedido (
 id INTEGER PRIMARY KEY, pedido_id INTEGER NOT NULL REFERENCES pedidos(id), produto_id INTEGER NOT NULL REFERENCES produtos(id),
 nome_produto TEXT NOT NULL, preco_centavos INTEGER NOT NULL CHECK(preco_centavos >= 0), quantidade INTEGER NOT NULL CHECK(quantidade > 0)
);
