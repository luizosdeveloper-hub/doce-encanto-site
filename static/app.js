const $ = selector => document.querySelector(selector);
const money = cents => (cents / 100).toLocaleString('pt-BR', {style:'currency', currency:'BRL'});
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let products = [], cart = {};
const statuses = ['Recebido', 'Em preparo', 'Saiu para entrega', 'Entregue', 'Cancelado'];
async function request(path, options) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.erro || 'Não foi possível concluir a operação.');
  return data;
}
function renderProducts() {
  $('#products').innerHTML = products.map((p,i) => `<article class="product"><div class="product-art"><img src="/product-${p.id}.png" alt="Cupcake ${escapeHTML(p.nome)}" loading="lazy" width="1024" height="1024"><span class="product-tag">ARTESANAL</span></div><div class="product-body"><h3>${escapeHTML(p.nome)}</h3><p>${escapeHTML(p.descricao)}</p><div class="product-bottom"><strong>${money(p.preco_centavos)}</strong><button class="add" data-add="${p.id}">+ Adicionar</button></div></div></article>`).join('');
}
function renderCart() {
  const selected = products.filter(p => cart[p.id]);
  $('#cart-count').textContent = Object.values(cart).reduce((a,b) => a+b, 0);
  $('#cart-total').textContent = money(selected.reduce((sum,p) => sum + p.preco_centavos * cart[p.id], 0));
  $('#cart-items').innerHTML = selected.length ? selected.map(p => `<div class="cart-row"><span><strong>${escapeHTML(p.nome)}</strong><br>${money(p.preco_centavos)} cada</span><div class="quantity"><button type="button" data-minus="${p.id}" aria-label="Remover uma unidade de ${escapeHTML(p.nome)}">−</button><span>${cart[p.id]}</span><button type="button" data-plus="${p.id}" aria-label="Adicionar uma unidade de ${escapeHTML(p.nome)}">+</button></div><strong>${money(p.preco_centavos * cart[p.id])}</strong></div>`).join('') : '<p class="empty">Sua sacola está vazia. Escolha um cupcake no cardápio.</p>';
}
document.addEventListener('click', event => {
  const add = event.target.closest('[data-add], [data-plus]');
  const minus = event.target.closest('[data-minus]');
  if (add) { const id = add.dataset.add || add.dataset.plus; cart[id] = Math.min(30, (cart[id] || 0) + 1); renderCart(); }
  if (minus) { const id = minus.dataset.minus; cart[id]--; if (!cart[id]) delete cart[id]; renderCart(); }
  const close = event.target.closest('[data-close]'); if(close) document.getElementById(close.dataset.close).close();
});
$('#open-cart').addEventListener('click', () => { $('#order-message').replaceChildren(); $('#order-message').className='message'; renderCart(); $('#cart-dialog').showModal(); });
$('#open-orders').addEventListener('click', () => { $('#orders-dialog').showModal(); loadOrders(); });
$('#open-tracking').addEventListener('click', () => { $('#tracking-result').textContent=''; $('#tracking-dialog').showModal(); });
$('#tracking-form').addEventListener('submit', async event => {
  event.preventDefault(); const result = $('#tracking-result'); result.textContent = 'Consultando...';
  try {
    const data = Object.fromEntries(new FormData(event.target));
    const order = await request('/api/acompanhar', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
    const stages = [
      ['Recebido', 'Seu pedido foi registrado pela loja.'],
      ['Em preparo', 'A loja está preparando seus cupcakes.'],
      ['Saiu para entrega', 'A loja marcou a saída para entrega.'],
      ['Entregue', 'A loja marcou o pedido como entregue.']
    ];
    const current = stages.findIndex(([name]) => name === order.status);
    result.innerHTML = `<section class="tracking-card"><h3>Pedido #${escapeHTML(order.id)}</h3><p>Total: ${money(order.total_centavos)}</p>${order.status === 'Cancelado' ? '<p class="cancelled">Este pedido foi cancelado pela loja.</p>' : `<ol class="tracking-stages">${stages.map(([name,detail], index) => `<li class="${index <= current ? 'reached' : ''}" ${index === current ? 'aria-current="step"' : ''}><strong>${name}${index === current ? ' · Agora' : ''}</strong><span>${detail}</span></li>`).join('')}</ol>`}<p class="success-note">Entrega simulada. Consulte novamente para atualizar o andamento; não enviamos notificações externas.</p></section>`;
  } catch(error) { result.textContent = error.message; }
});
$('#order-form').addEventListener('submit', async event => {
  event.preventDefault(); const message = $('#order-message');
  message.className = 'message';
  if (!Object.keys(cart).length) { message.textContent = 'Adicione um produto à sacola.'; return; }
  const button = event.target.querySelector('button[type=submit]'); button.disabled = true; message.textContent = 'Registrando pedido...';
  try {
    const fields = Object.fromEntries(new FormData(event.target));
    fields.itens = Object.entries(cart).map(([id,quantidade]) => ({id:Number(id), quantidade}));
    const order = await request('/api/pedidos', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(fields)});
    cart = {}; renderCart(); event.target.reset(); message.className = 'message order-success';
    message.innerHTML = `<div class="success-heading"><span class="success-check" aria-hidden="true">✓</span><div><span class="eyebrow">TUDO CERTO!</span><h3>Seu pedido foi recebido</h3></div></div><p>Guarde os dados abaixo para acompanhar seu momento doce.</p><dl class="order-summary"><div><dt>Pedido</dt><dd>#${escapeHTML(order.id)}</dd></div><div><dt>Total</dt><dd>${money(order.total_centavos)}</dd></div></dl><div class="tracking-code"><span>Código de acompanhamento</span><code>${escapeHTML(order.codigo_acesso)}</code><button type="button" class="copy-code">Copiar código</button></div><p class="success-note">Pagamento e entrega simulados neste protótipo.</p>`;
    message.querySelector('.copy-code').addEventListener('click', async e => {
      try { await navigator.clipboard.writeText(order.codigo_acesso); e.target.textContent = 'Código copiado ✓'; }
      catch { e.target.textContent = 'Selecione o código acima para copiar'; }
    });
    message.scrollIntoView({block:'nearest',behavior:'smooth'});
  } catch (error) { message.textContent = error.message; } finally { button.disabled = false; }
});
async function loadOrders() {
  const list = $('#orders-list'); list.textContent = 'Carregando pedidos...';
  try {
    const orders = await request('/api/pedidos');
    list.innerHTML = orders.length ? orders.map(o => `<article class="order"><strong>Pedido #${o.id} · ${money(o.total_centavos)}</strong><p>${escapeHTML(o.nome)} · ${escapeHTML(o.telefone)}</p><p>${escapeHTML(o.endereco)}</p><p>${o.itens.map(i => `${i.quantidade}× ${escapeHTML(i.nome_produto)}`).join(', ')}</p><p>Pagamento: ${escapeHTML(o.pagamento)} (simulado)</p><label>Andamento<select data-order="${o.id}">${statuses.map(s => `<option ${s===o.status?'selected':''}>${escapeHTML(s)}</option>`).join('')}</select></label></article>`).join('') : '<p class="empty">Ainda não há pedidos registrados.</p>';
  } catch(error) { list.textContent = error.message; }
}
$('#orders-list').addEventListener('change', async event => {
  if (!event.target.matches('[data-order]')) return;
  try { await request(`/api/pedidos/${event.target.dataset.order}`, {method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:event.target.value})}); }
  catch(error) { alert(error.message); loadOrders(); }
});
request('/api/produtos').then(data => { products = data; renderProducts(); renderCart(); }).catch(() => { $('#products').textContent = 'Não foi possível carregar o cardápio. Verifique se o servidor está em execução.'; });
