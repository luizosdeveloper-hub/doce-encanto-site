# Doce Encanto

Site de uma cupcakeria com catálogo, sacola, registro de pedidos, acompanhamento por código e painel da loja. Interface responsiva em HTML, CSS e JavaScript, servidor Python e banco SQLite.

## Executar

Requer Python 3.10 ou superior. Não é necessário instalar bibliotecas externas.

```sh
python app.py
```

No Windows, também é possível abrir `iniciar.bat`. Acesse http://127.0.0.1:8000 e mantenha o servidor em execução. O banco `cupcake.db` é criado automaticamente e não é versionado.

## Usar

1. Selecione cupcakes e abra a sacola.
2. Preencha os dados com informações fictícias e confirme o pedido.
3. Guarde o número e o código de acompanhamento.
4. Altere o andamento em **Pedidos da loja** e consulte em **Acompanhar pedido**.

Pagamentos e entregas são simulados. O painel não possui autenticação. Este é um protótipo para demonstração; uso público exige controle de acesso e proteção de dados.

## Estrutura

```text
app.py          Servidor, rotas e regras de pedidos
schema.sql      Estrutura do banco SQLite
static/         HTML, CSS, JavaScript e imagens
iniciar.bat     Inicialização no Windows
```

As imagens dos cupcakes são ilustrativas e foram geradas por inteligência artificial.
