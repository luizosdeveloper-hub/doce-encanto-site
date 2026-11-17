"""Servidor local do protótipo Cupcake Gourmet, usando apenas a biblioteca padrão."""
import json
import os
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('CUPCAKE_DB', ROOT / 'cupcake.db'))
STATUSES = ('Recebido', 'Em preparo', 'Saiu para entrega', 'Entregue', 'Cancelado')

class Connection(sqlite3.Connection):
    def __exit__(self, exc_type, exc, traceback):
        try:
            return super().__exit__(exc_type, exc, traceback)
        finally:
            self.close()

def connect():
    db = sqlite3.connect(DB, timeout=10, factory=Connection)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys = ON')
    return db

def init_db():
    with connect() as db:
        db.executescript((ROOT / 'schema.sql').read_text(encoding='utf-8'))
        if 'codigo_acesso' not in {row['name'] for row in db.execute('PRAGMA table_info(pedidos)')}:
            db.execute('ALTER TABLE pedidos ADD COLUMN codigo_acesso TEXT')
        if not db.execute('SELECT 1 FROM produtos LIMIT 1').fetchone():
            db.executemany('INSERT INTO produtos (nome, descricao, preco_centavos, emoji) VALUES (?, ?, ?, ?)', [
                ('Chocolate intenso', 'Massa de chocolate e cobertura cremosa.', 1400, '🍫'),
                ('Baunilha & frutas', 'Baunilha delicada com toque de frutas vermelhas.', 1500, '🍓'),
                ('Doce de leite', 'Massa fofinha e cobertura de doce de leite.', 1500, '🍯'),
                ('Red velvet', 'Cacau suave com cobertura de cream cheese.', 1600, '❤️'),
                ('Limão', 'Um toque cítrico com cobertura leve.', 1400, '🍋'),
                ('Cookies & cream', 'Chocolate, baunilha e pedacinhos crocantes.', 1600, '🍪'),
            ])

def create_order(data):
    if not isinstance(data, dict):
        raise ValueError('Dados do pedido inválidos.')
    name = str(data.get('nome', '')).strip()
    phone = str(data.get('telefone', '')).strip()
    if any(key in data for key in ('rua', 'numero', 'bairro', 'complemento')):
        limits = {'rua': (2, 100), 'numero': (1, 12), 'bairro': (2, 60), 'complemento': (0, 50)}
        parts = {}
        for key, (minimum, maximum) in limits.items():
            value = data.get(key, '')
            if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
                raise ValueError('Confira rua, número, bairro e complemento do endereço.')
            parts[key] = value.strip()
        address = f"{parts['rua']}, {parts['numero']} - {parts['bairro']}"
        if parts['complemento']:
            address += f" - {parts['complemento']}"
    else:
        address = str(data.get('endereco', '')).strip()
    payment = data.get('pagamento')
    items = data.get('itens')
    if not (2 <= len(name) <= 100 and 8 <= len(phone) <= 25 and 8 <= len(address) <= 250):
        raise ValueError('Informe nome, telefone e endereço completos.')
    if payment not in ('Pix', 'Cartão na entrega'):
        raise ValueError('Selecione uma forma de pagamento válida.')
    if not isinstance(items, list) or not 1 <= len(items) <= 20:
        raise ValueError('Adicione ao menos um produto ao carrinho.')
    quantities = {}
    for item in items:
        if not isinstance(item, dict) or type(item.get('id')) is not int or type(item.get('quantidade')) is not int or not 1 <= item['quantidade'] <= 30:
            raise ValueError('Produto ou quantidade inválida.')
        quantities[item['id']] = quantities.get(item['id'], 0) + item['quantidade']
        if quantities[item['id']] > 30:
            raise ValueError('O limite é de 30 unidades por produto.')
    with connect() as db:
        products = []
        for product_id, qty in quantities.items():
            product = db.execute('SELECT * FROM produtos WHERE id = ? AND ativo = 1', (product_id,)).fetchone()
            if not product:
                raise ValueError('Um produto selecionado não está disponível.')
            products.append((product, qty))
        total = sum(p['preco_centavos'] * qty for p, qty in products)
        code = secrets.token_hex(8)
        cursor = db.execute('INSERT INTO pedidos (nome, telefone, endereco, pagamento, total_centavos, codigo_acesso) VALUES (?, ?, ?, ?, ?, ?)', (name, phone, address, payment, total, code))
        order_id = cursor.lastrowid
        db.executemany('INSERT INTO itens_pedido (pedido_id, produto_id, nome_produto, preco_centavos, quantidade) VALUES (?, ?, ?, ?, ?)', [(order_id, p['id'], p['nome'], p['preco_centavos'], qty) for p, qty in products])
        return {'id': order_id, 'total_centavos': total, 'status': 'Recebido', 'codigo_acesso': code}

class Handler(BaseHTTPRequestHandler):
    def json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status); self.send_header('Content-Type', 'application/json; charset=utf-8'); self.send_header('Content-Length', str(len(body))); self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(body)

    def read_json(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 1 or length > 20000: raise ValueError()
            return json.loads(self.rfile.read(length).decode('utf-8'))
        except (ValueError, UnicodeError):
            raise ValueError('Dados JSON inválidos.')

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/produtos':
            with connect() as db:
                self.json_response([dict(row) for row in db.execute('SELECT id, nome, descricao, preco_centavos, emoji FROM produtos WHERE ativo = 1 ORDER BY id')])
        elif path == '/api/pedidos':
            with connect() as db:
                orders = [dict(row) for row in db.execute('SELECT id, nome, telefone, endereco, pagamento, total_centavos, status, criado_em FROM pedidos ORDER BY id DESC LIMIT 100')]
                for order in orders:
                    order['itens'] = [dict(row) for row in db.execute('SELECT nome_produto, quantidade, preco_centavos FROM itens_pedido WHERE pedido_id = ?', (order['id'],))]
                self.json_response(orders)
        else:
            files = {'/': ('index.html', 'text/html; charset=utf-8'), '/style.css': ('style.css', 'text/css; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'), '/cupcakes.png': ('cupcakes.png', 'image/png')}
            files.update({f'/product-{i}.png': (f'product-{i}.png', 'image/png') for i in range(1, 7)})
            if path not in files: return self.json_response({'erro': 'Página não encontrada.'}, 404)
            name, kind = files[path]; body = (ROOT / 'static' / name).read_bytes()
            self.send_response(200); self.send_header('Content-Type', kind); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        try:
            if urlparse(self.path).path == '/api/acompanhar':
                data = self.read_json()
                if not isinstance(data, dict): raise ValueError('Dados inválidos.')
                order_id, code = str(data.get('id', '')), data.get('codigo', '')
                if not order_id.isdigit() or not isinstance(code, str) or not code.isascii() or len(code) != 16: raise ValueError('Informe número e código do pedido.')
                with connect() as db:
                    row = db.execute('SELECT id, status, total_centavos, criado_em, codigo_acesso FROM pedidos WHERE id = ?', (int(order_id),)).fetchone()
                    if not row or not row['codigo_acesso'] or not secrets.compare_digest(row['codigo_acesso'], code): return self.json_response({'erro': 'Pedido ou código não encontrado.'}, 404)
                    return self.json_response({k: row[k] for k in ('id', 'status', 'total_centavos', 'criado_em')})
            if urlparse(self.path).path != '/api/pedidos': return self.json_response({'erro': 'Rota não encontrada.'}, 404)
            self.json_response(create_order(self.read_json()), 201)
        except ValueError as exc:
            self.json_response({'erro': str(exc)}, 400)

    def do_PATCH(self):
        try:
            parts = urlparse(self.path).path.strip('/').split('/')
            if len(parts) != 3 or parts[:2] != ['api', 'pedidos'] or not parts[2].isdigit(): return self.json_response({'erro': 'Rota não encontrada.'}, 404)
            data = self.read_json(); status = data.get('status') if isinstance(data, dict) else None
            if status not in STATUSES: raise ValueError('Status inválido.')
            with connect() as db:
                cursor = db.execute('UPDATE pedidos SET status = ? WHERE id = ?', (status, int(parts[2])))
                if not cursor.rowcount: return self.json_response({'erro': 'Pedido não encontrado.'}, 404)
            self.json_response({'ok': True})
        except ValueError as exc:
            self.json_response({'erro': str(exc)}, 400)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('CUPCAKE_PORT', '8000'))
    host = os.environ.get('CUPCAKE_HOST', '127.0.0.1')
    print(f'Cupcake Gourmet: http://{host}:{port} (Ctrl+C para encerrar)', flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
