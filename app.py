import os
import re
import secrets
from functools import wraps
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.io as pio

from flask import Flask, render_template, request, redirect, url_for, session
from classes.corporation import Corporation
from classes.client import Client
from classes.broker import Broker
from classes.trade import Trade
from classes.userlogin import Userlogin


app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'g53-projeto-chave-secreta-2025')

@app.template_filter('moeda')
def moeda_filter(value):
    return f"{value:,.2f} €".replace(',', 'X').replace('.', ',').replace('X', '.')

db_path = os.path.join(os.path.dirname(__file__), 'data/business.db')
Corporation.read(db_path)
Broker.read(db_path)
Client.read(db_path)
Trade.read(db_path)
Userlogin.read(db_path)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('user_login'))
        return f(*args, **kwargs)
    return decorated


def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('user_login'))
            if session.get('usergroup') not in roles:
                return redirect(url_for('user_login'))
            return f(*args, **kwargs)
        return decorated
    return decorator

@app.route('/')
def home():
    return redirect(url_for('index'))

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/user_login')
def user_login():
    return render_template('login.html', user='', password='', resul='')

@app.route('/chklogin', methods=['POST'])
def chklogin():
    user = request.form.get('user', '').strip()
    password = request.form.get('password', '')

    result = Userlogin.chk_password(user, password)
    if result != 'Valid':
        return render_template('login.html', user=user, password='', resul='Credenciais inválidas. Tente novamente.')

    user_id = Userlogin.user_id
    u = Userlogin.obj[user_id]

    session['user_id'] = u.id
    session['username'] = u.user
    session['usergroup'] = u.usergroup
    session['entity_id'] = u.entity_id

    if u.usergroup == 'admin':
        return redirect(url_for('admin'))
    elif u.usergroup == 'corp':
        if u.entity_id == 0:
            return redirect(url_for('select_entity', tipo='corp'))
        return redirect(url_for('corporation_dashboard', id=u.entity_id))
    elif u.usergroup == 'broker':
        if u.entity_id == 0:
            return redirect(url_for('select_entity', tipo='broker'))
        return redirect(url_for('broker_dashboard', id=u.entity_id))
    elif u.usergroup == 'client':
        if u.entity_id == 0:
            return redirect(url_for('select_entity', tipo='client'))
        return redirect(url_for('cliente_dashboard', id=u.entity_id))
    else:
        return redirect(url_for('index'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('user_login'))


@app.route('/select/<tipo>')
@login_required
def select_entity(tipo):
    usergroup = session.get('usergroup')
    if usergroup not in ('corp', 'broker', 'client') or session.get('entity_id') != 0:
        return redirect(url_for('user_login'))

    if tipo == 'corp':
        entidades = sorted(
            [{'id': c.id, 'name': c.name} for c in Corporation.obj.values()],
            key=lambda x: x['name'].lower()
        )
        label = 'Corporação'
    elif tipo == 'broker':
        entidades = sorted(
            [{'id': b.id, 'name': b.name} for b in Broker.obj.values()],
            key=lambda x: x['name'].lower()
        )
        label = 'Corretor'
    elif tipo == 'client':
        entidades = sorted(
            [{'id': c.id, 'name': c.name} for c in Client.obj.values()],
            key=lambda x: x['name'].lower()
        )
        label = 'Cliente'
    else:
        return redirect(url_for('user_login'))

    return render_template('select_entity.html', tipo=label, tipo_key=tipo, entidades=entidades)


@app.route('/select/go', methods=['POST'])
@login_required
def select_entity_post():
    if session.get('entity_id') != 0:
        return redirect(url_for('user_login'))

    tipo = request.form.get('tipo')
    entity_id = int(request.form.get('entity_id', 0))

    if tipo == 'corp':
        return redirect(url_for('corporation_dashboard', id=entity_id))
    elif tipo == 'broker':
        return redirect(url_for('broker_dashboard', id=entity_id))
    elif tipo == 'client':
        return redirect(url_for('cliente_dashboard', id=entity_id))
    return redirect(url_for('user_login'))


SUPERVISOR_CODE = 'PCII_supervisor'
ADMIN_CODE = 'PCII_admin'


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html', erro='')

    def err(msg):
        return render_template('register.html', erro=msg)

    role = request.form.get('role', '').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    confirm = request.form.get('confirm', '').strip()
    access_code = request.form.get('access_code', '').strip()

    if not role or not username or not password:
        return err('Preenche todos os campos obrigatórios.')
    if password != confirm:
        return err('As passwords não coincidem.')
    if len(password) < 6:
        return err('A password deve ter pelo menos 6 caracteres.')
    if Userlogin.get_user_id(username) != 0:
        return err('Este nome de utilizador já existe.')

    if role == 'admin':
        if access_code != ADMIN_CODE:
            return err('Código de administrador inválido.')
        usergroup = 'admin'
        entity_id = 0
    elif role in ('corp', 'broker', 'client_sup'):
        if access_code != SUPERVISOR_CODE:
            return err('Código de supervisão inválido.')
        usergroup = 'client' if role == 'client_sup' else role
        entity_id = 0
    elif role == 'client':
        name = request.form.get('name', '').strip()
        address = request.form.get('address', '').strip()
        if not name or not address:
            return err('Nome e morada são obrigatórios para conta de cliente.')
        new_client_id = max(Client.lst) + 1 if Client.lst else 1
        Client(new_client_id, name, address)
        Client.insert(new_client_id)
        usergroup = 'client'
        entity_id = new_client_id
    else:
        return err('Tipo de conta inválido.')

    new_user_id = max(Userlogin.lst) + 1 if Userlogin.lst else 1
    hashed = Userlogin.set_password(password)
    Userlogin(new_user_id, username, usergroup, hashed, entity_id)
    Userlogin.insert(new_user_id)

    session['user_id'] = new_user_id
    session['username'] = username
    session['usergroup'] = usergroup
    session['entity_id'] = entity_id

    if usergroup == 'admin':
        return redirect(url_for('admin'))
    elif usergroup == 'corp':
        return redirect(url_for('select_entity', tipo='corp'))
    elif usergroup == 'broker':
        return redirect(url_for('select_entity', tipo='broker'))
    elif usergroup == 'client' and entity_id == 0:
        return redirect(url_for('select_entity', tipo='client'))
    else:
        return redirect(url_for('cliente_dashboard', id=entity_id))

@app.route('/admin')
@require_role('admin')
def admin():
    corps = sorted((Corporation.obj[id] for id in Corporation.lst), key=lambda c: c.name.lower())
    brokers = sorted((Broker.obj[id] for id in dict.fromkeys(Broker.lst)), key=lambda b: b.name.lower())
    clients = sorted((Client.obj[id] for id in Client.lst), key=lambda c: c.name.lower())

    mapping = {'high': 'ALTO', 'medium': 'MÉDIO', 'low': 'BAIXO'}
    for corp in corps:
        corp.risk_profile = ''
        if getattr(corp, 'comments', None):
            m = re.search(r'Risk\s*profile\s*:\s*(High|Medium|Low)', corp.comments, re.IGNORECASE)
            if m:
                corp.risk_profile = mapping.get(m.group(1).lower(), '')

    for b in brokers:
        b_trades = [Trade.obj[t_id] for t_id in Trade.lst if Trade.obj[t_id].broker_id == b.id]
        b.num_trades = len(b_trades)
        b.num_clients = len({t.client_id for t in b_trades})
        b.avg_ticket = sum(t.amount for t in b_trades) / len(b_trades) if b_trades else 0

    for cl in clients:
        c_trades = [t for t in Trade.obj.values() if t.client_id == cl.id]
        cl.num_trades = len(c_trades)
        cl.capital_investido = sum(t.amount for t in c_trades) if c_trades else 0

    return render_template('admin.html', 
                           lista_corps=corps, 
                           lista_brokers=brokers, 
                           lista_clients=clients)

@app.route('/admin/corporation/add', methods=['POST'])
@require_role('admin')
def admin_add_corporation():
    name = (request.form.get('name') or '').strip()
    comments = (request.form.get('comments') or '').strip()

    if not name:
        return "Nome da corporação é obrigatório.", 400

    new_id = max(Corporation.lst) + 1 if Corporation.lst else 1
    Corporation(new_id, name, comments)
    Corporation.insert(new_id)
    return redirect(url_for('admin'))

@app.route('/admin/corporation/remove', methods=['POST'])
@require_role('admin')
def admin_remove_corporation():
    corp_id = request.form.get('corp_id')
    if not corp_id:
        return "Corporação inválida.", 400

    corp_id = int(corp_id)
    if corp_id not in Corporation.obj:
        return "Corporação não encontrada.", 404

    broker_ids = [bid for bid in list(Broker.lst) if Broker.obj[bid].corporation_id == corp_id]
    for bid in broker_ids:
        trade_ids = [tid for tid in list(Trade.lst) if Trade.obj[tid].broker_id == bid]
        for tid in trade_ids:
            Trade.lst.remove(tid)
            del Trade.obj[tid]
        Trade.sqlexe(f"DELETE FROM Trade WHERE broker_id={bid}")
        Broker.lst.remove(bid)
        del Broker.obj[bid]
    Broker.sqlexe(f"DELETE FROM Broker WHERE corporation_id={corp_id}")

    Corporation.remove(corp_id)
    return redirect(url_for('admin'))

@app.route('/admin/broker/add', methods=['POST'])
@require_role('admin')
def admin_add_broker():
    name = (request.form.get('name') or '').strip()
    license_number = request.form.get('license_number')
    corporation_id = request.form.get('corporation_id')

    if not name or not corporation_id:
        return "Dados do broker incompletos.", 400

    corp_id = int(corporation_id)
    new_id = max(Broker.lst) + 1 if Broker.lst else 1

    novo_broker = Broker(new_id, name, license_number, corp_id)
    
    if new_id not in Broker.lst:
        Broker.lst.append(new_id)
    Broker.obj[new_id] = novo_broker

    Broker.insert(new_id)

    return redirect(url_for('admin'))

@app.route('/admin/broker/remove', methods=['POST'])
@require_role('admin')
def admin_remove_broker():
    broker_id = request.form.get('broker_id')
    if not broker_id:
        return "Broker inválido.", 400

    broker_id = int(broker_id)
    if broker_id not in Broker.obj:
        return "Broker não encontrado.", 404

    trade_ids = [tid for tid in list(Trade.lst) if Trade.obj[tid].broker_id == broker_id]
    for tid in trade_ids:
        Trade.lst.remove(tid)
        del Trade.obj[tid]
    Trade.sqlexe(f"DELETE FROM Trade WHERE broker_id={broker_id}")

    Broker.remove(broker_id)
    return redirect(url_for('admin'))

@app.route('/admin/client/add', methods=['POST'])
@require_role('admin')
def admin_add_client():
    name = (request.form.get('name') or '').strip()
    address = (request.form.get('address') or '').strip()

    if not name or not address:
        return "Dados do cliente incompletos.", 400

    new_id = max(Client.lst) + 1 if Client.lst else 1
    Client(new_id, name, address)
    Client.insert(new_id)
    return redirect(url_for('admin'))

@app.route('/admin/client/remove', methods=['POST'])
@require_role('admin')
def admin_remove_client():
    client_id = request.form.get('client_id')
    if not client_id:
        return "Cliente inválido.", 400

    client_id = int(client_id)
    if client_id not in Client.obj:
        return "Cliente não encontrado.", 404

    trade_ids = [tid for tid in list(Trade.lst) if Trade.obj[tid].client_id == client_id]
    for tid in trade_ids:
        Trade.lst.remove(tid)
        del Trade.obj[tid]
    Trade.sqlexe(f"DELETE FROM Trade WHERE client_id={client_id}")

    Client.remove(client_id)
    return redirect(url_for('admin'))

@app.route('/corporation/<int:id>/dashboard')
@login_required
def corporation_dashboard(id):
    ug = session.get('usergroup')
    eid = session.get('entity_id')
    if ug != 'admin' and not (ug == 'corp' and (eid == 0 or eid == id)):
        return redirect(url_for('user_login'))
    if id not in Corporation.obj:
        return "Erro: Corporação não encontrada!", 404
    
    corp = Corporation.obj[id]
    corp_brokers = [Broker.obj[b_id] for b_id in dict.fromkeys(Broker.lst) if Broker.obj[b_id].corporation_id == id]
    
    broker_stats = []
    total_trades_list = []
    
    for b in corp_brokers:
        b_trades = [Trade.obj[t_id] for t_id in Trade.lst if Trade.obj[t_id].broker_id == b.id]
        
        if not b_trades:
            broker_stats.append({'obj': b, 'aum': 0, 'num_clients': 0, 'clients': [], 'risk_status': 'N/A', 'risk_color': '#95a5a6'})
            continue

        df_b = pd.DataFrame([{'client_id': t.client_id, 'amount': t.amount} for t in b_trades])
        b_aum = df_b['amount'].sum()
        max_conc_pct = (df_b.groupby('client_id')['amount'].sum().max() / b_aum) * 100
        
        if max_conc_pct > 10:
            status, color = 'ALTO', '#e74c3c'
        elif max_conc_pct > 7.5:
            status, color = 'MÉDIO', '#f1c40f'
        else:
            status, color = 'BAIXO', '#27ae60'
            
        clientes_info = []
        for c_id, group in df_b.groupby('client_id'):
            c_name = Client.obj[c_id].name if c_id in Client.obj else f"Cliente {c_id}"
            clientes_info.append({'name': c_name, 'amount': group['amount'].sum()})
        clientes_info = sorted(clientes_info, key=lambda x: x['amount'], reverse=True)
            
        broker_stats.append({
            'obj': b,
            'aum': b_aum,
            'num_clients': df_b['client_id'].nunique(),
            'clients': clientes_info,
            'risk_status': status,
            'risk_color': color
        })
        total_trades_list.extend([t.amount for t in b_trades])

    total_aum = sum(total_trades_list)
    avg_ticket = sum(total_trades_list) / len(total_trades_list) if total_trades_list else 0
    
    risk_series = pd.Series([s['risk_status'] for s in broker_stats])
    pct_alto = (risk_series == 'ALTO').mean() * 100
    
    if pct_alto > 30:
        corp_risk = {'nivel': 'CRÍTICO', 'cor': '#c0392b', 'msg': 'ALERTA: Mais de 30% da equipa está em risco de concentração!'}
    elif pct_alto > 10 or (risk_series == 'MÉDIO').sum() > (len(corp_brokers)/2):
        corp_risk = {'nivel': 'ATENÇÃO', 'cor': '#d35400', 'msg': 'Exposição moderada. Recomenda-se diversificar carteiras.'}
    else:
        corp_risk = {'nivel': 'ESTÁVEL', 'cor': '#27ae60', 'msg': 'A estrutura de brokers está saudável e diversificada.'}

    df_plot = pd.DataFrame([{'Corretor': s['obj'].name, 'AUM': s['aum']} for s in broker_stats if s['aum'] > 0])
    if not df_plot.empty:
        fig = px.pie(df_plot, values='AUM', names='Corretor', title='Distribuição de Volume por Corretor', hole=0.4)
        fig.update_layout(separators=',.')
        fig.update_traces(hovertemplate='%{label}<br>Volume: %{value:,.2f} €<extra></extra>')
        graph_html = pio.to_html(fig, full_html=False)
    else:
        graph_html = "<p class='text-muted'>Nenhum dado de volume disponível para gerar o gráfico.</p>"

    return render_template('corporation_dashboard.html',
                           corp=corp,
                           aum=total_aum,
                           avg_ticket=avg_ticket,
                           num_brokers=len(corp_brokers),
                           risk=corp_risk,
                           graph_html=graph_html,
                           brokers=broker_stats)

@app.route('/corporation/close_account', methods=['POST'])
@require_role('corp', 'admin')
def close_corporation_account():
    corp_id = request.form.get('corp_id')
    if not corp_id:
        return "Corporação inválida.", 400

    corp_id = int(corp_id)
    if corp_id not in Corporation.obj:
        return "Corporação não encontrada.", 404

    # 1. Encontrar todos os brokers associados a esta corporação
    broker_ids = [bid for bid in list(Broker.lst) if Broker.obj[bid].corporation_id == corp_id]
    
    for bid in broker_ids:
        # 2. Encontrar e apagar todas as transações associadas a cada broker
        trade_ids = [tid for tid in list(Trade.lst) if Trade.obj[tid].broker_id == bid]
        for tid in trade_ids:
            Trade.lst.remove(tid)
            del Trade.obj[tid]
        Trade.sqlexe(f"DELETE FROM Trade WHERE broker_id={bid}")
        
        # 3. Apagar o broker
        Broker.lst.remove(bid)
        del Broker.obj[bid]
    
    # Executa a limpeza final de brokers na BD para esta corporação
    Broker.sqlexe(f"DELETE FROM Broker WHERE corporation_id={corp_id}")

    # 4. Finalmente, apagar a Corporação e redirecionar para a página inicial
    Corporation.remove(corp_id)
    session.clear()
    return redirect(url_for('index'))

@app.route('/broker/<int:id>/dashboard')
@login_required
def broker_dashboard(id):
    ug = session.get('usergroup')
    eid = session.get('entity_id')
    if ug != 'admin' and not (ug == 'broker' and (eid == 0 or eid == id)):
        return redirect(url_for('user_login'))
    if id not in Broker.obj:
        return "Erro: Broker não encontrado!", 404
    
    broker = Broker.obj[id]
    empresa = Corporation.obj[broker.corporation_id].name if broker.corporation_id in Corporation.obj else "Independente"
    
    trades_list = []
    clientes_dict = {}
    
    for t in Trade.obj.values():
        if t.broker_id == id:
            c_name = Client.obj[t.client_id].name if t.client_id in Client.obj else f"Cliente {t.client_id}"
            trade_info = {
                'id': t.id,
                'client_name': c_name,
                'amount': t.amount,
                'date': t.date,
                'trade_name': t.name
            }
            trades_list.append(trade_info)
            
            if t.client_id not in clientes_dict:
                clientes_dict[t.client_id] = {'name': c_name, 'total': 0, 'trades': []}
            clientes_dict[t.client_id]['total'] += t.amount
            clientes_dict[t.client_id]['trades'].append(trade_info)
            
    df = pd.DataFrame(trades_list)
    lista_clientes = sorted(clientes_dict.values(), key=lambda x: x['total'], reverse=True)
    
    clientes_atuais_ids = set(clientes_dict.keys())

    clientes_atuais = sorted(
        [{'id': cid, 'name': Client.obj[cid].name, 'total': clientes_dict[cid]['total']}
         for cid in clientes_atuais_ids if cid in Client.obj],
        key=lambda c: c['name'].lower()
    )
    
    clientes_disponiveis = [Client.obj[cid] for cid in Client.lst if cid not in clientes_atuais_ids and cid in Client.obj]
    clientes_disponiveis = sorted(clientes_disponiveis, key=lambda c: c.name.lower())

    if df.empty:
        todos_globais = sorted([Client.obj[cid] for cid in Client.lst if cid in Client.obj], key=lambda c: c.name.lower())
        return render_template('broker_dashboard.html', broker=broker, empresa=empresa, total_investido=0, ticket_medio=0, num_clientes=0, risco={'nivel': 'N/A', 'cor': '#95a5a6', 'msg': 'Sem dados suficientes.'}, graph_html=None, negocios=[], lista_clientes=[], clientes_atuais=[], clientes_disponiveis=todos_globais)

    
    total_aum = df['amount'].sum()
    ticket_medio = df['amount'].mean()
    num_clientes = df['client_name'].nunique()
    df_clientes = df.groupby('client_name')['amount'].sum().reset_index()
    maior_fatia = df_clientes['amount'].max()
    percentagem_maior_cliente = (maior_fatia/total_aum)*100
    nome_maior_cliente = df_clientes.loc[df_clientes['amount'].idxmax(),'client_name']
    
    if percentagem_maior_cliente > 10:
        risco = {'nivel': 'ALTO', 'cor': '#e74c3c', 'msg': f'Cuidado! {nome_maior_cliente} detém {percentagem_maior_cliente:.1f}% da carteira.'}
    elif percentagem_maior_cliente > 7.5:
        risco = {'nivel': 'MÉDIO', 'cor': '#f1c40f', 'msg': 'Dependência moderada de um único cliente.'}
    else:
        risco = {'nivel': 'BAIXO', 'cor': '#27ae60', 'msg': 'Carteira bem diversificada.'}
        
    fig = px.bar(df_clientes.sort_values('amount', ascending=True).tail(5),
                 x='amount', y='client_name', orientation='h',
                 title='Top 5 Clientes por Volume',
                 labels={'amount': 'Volume(€)', 'client_name': 'Cliente'},
                 color='amount', color_continuous_scale='Blues')
    fig.update_layout(separators=',.')
    fig.update_traces(hovertemplate='%{y}<br>Volume: %{x:,.2f} €<extra></extra>')
    fig.update_xaxes(tickformat=',.2f')
    graph_html = pio.to_html(fig, full_html=False)
    
    return render_template('broker_dashboard.html',
                           broker=broker,
                           empresa=empresa,
                           total_investido=total_aum,
                           ticket_medio=ticket_medio,
                           num_clientes=num_clientes,
                           risco=risco,
                           graph_html=graph_html,
                           negocios=trades_list,
                           lista_clientes=lista_clientes,
                           clientes_atuais=clientes_atuais,        
                           clientes_disponiveis=clientes_disponiveis)

@app.route('/broker/close_account', methods=['POST'])
@require_role('broker', 'admin')
def broker_close_account():
    broker_id = int(request.form.get('broker_id'))
    
    if broker_id not in Broker.obj:
        return "Broker não encontrado.", 404
        
    broker_name = Broker.obj[broker_id].name
    data_atual = datetime.now().strftime("%Y-%m-%d")
    
    saldos_clientes = {}
    for t in Trade.obj.values():
        if t.broker_id == broker_id:
            saldos_clientes[t.client_id] = saldos_clientes.get(t.client_id, 0.0) + t.amount
            
    for client_id, saldo in saldos_clientes.items():
        if saldo > 0:
            new_id = max(Trade.lst) + 1 if Trade.lst else 1
            Trade(new_id, broker_id, client_id, f"Liquidação por Encerramento de {broker_name}", data_atual, -saldo)
            query = f"INSERT INTO Trade (id, broker_id, client_id, name, date, amount) " \
                    f"VALUES ({new_id}, {broker_id}, {client_id}, 'Liquidação por Encerramento de {broker_name}', '{data_atual}', {-saldo})"
            Trade.sqlexe(query)
            
    trade_ids = [tid for tid in list(Trade.lst) if Trade.obj[tid].broker_id == broker_id]
    for tid in trade_ids:
        Trade.lst.remove(tid)
        del Trade.obj[tid]
    Trade.sqlexe(f"DELETE FROM Trade WHERE broker_id={broker_id}")

    if broker_id in Broker.lst:
        Broker.lst.remove(broker_id)
    if broker_id in Broker.obj:
        del Broker.obj[broker_id]

    Broker.sqlexe(f"DELETE FROM Broker WHERE id={broker_id}")
    session.clear()
    return redirect(url_for('index'))

@app.route('/broker/manage_client', methods=['POST'])
@require_role('broker', 'admin')
def manage_client():
    broker_id = int(request.form.get('broker_id'))
    client_id = int(request.form.get('client_id'))
    action = request.form.get('action_type')
    data_atual = datetime.now().strftime("%Y-%m-%d")

    if action == 'adicionar':
        # Criação de um trade dummy de 0€ para forçar a associação no portfolio
        new_id = max(Trade.lst) + 1 if Trade.lst else 1
        Trade(new_id, broker_id, client_id, "Entrada na Carteira", data_atual, 0.0)
        query = f"INSERT INTO Trade (id, broker_id, client_id, name, date, amount) VALUES ({new_id}, {broker_id}, {client_id}, 'Entrada na Carteira', '{data_atual}', 0.0)"
        Trade.sqlexe(query)
        
    elif action == 'remover':
        # Removemos todos os "trades" em memória
        trades_to_remove = [t_id for t_id, t in Trade.obj.items() if t.broker_id == broker_id and t.client_id == client_id]
        for t_id in trades_to_remove:
            if t_id in Trade.obj:
                del Trade.obj[t_id]
            if t_id in Trade.lst:
                Trade.lst.remove(t_id)
        # Apagamos da DB
        Trade.sqlexe(f"DELETE FROM Trade WHERE broker_id={broker_id} AND client_id={client_id}")

    return redirect(url_for('broker_dashboard', id=broker_id))


@app.route('/cliente/<int:id>/dashboard')
@login_required
def cliente_dashboard(id):
    ug = session.get('usergroup')
    eid = session.get('entity_id')
    if ug != 'admin' and not (ug == 'client' and (eid == 0 or eid == id)):
        return redirect(url_for('user_login'))
    if id not in Client.obj:
        return "Erro: Cliente não encontrado!", 404

    cliente = Client.obj[id]
    
    saldos = {}  # Mapeamento de broker_id -> saldo acumulado
    brokers_associados_ids = set()
    trades_data = []

    trades_data = []
    for t in Trade.obj.values():
        if t.client_id == id:
            brokers_associados_ids.add(t.broker_id)
            saldos[t.broker_id] = saldos.get(t.broker_id, 0.0) + t.amount

            b_name = Broker.obj[t.broker_id].name if t.broker_id in Broker.obj else "Removido do sistema"
            trades_data.append({
                'id': t.id,
                'broker_name': b_name, 
                'client_id': t.client_id, 
                'amount': t.amount,
                'name': t.name,
                'date': t.date
            })
    brokers_adicionar = [Broker.obj[bid] for bid in brokers_associados_ids if bid in Broker.obj]
    brokers_adicionar = sorted(brokers_adicionar, key=lambda b: b.name.lower())

    brokers_levantar = [Broker.obj[bid] for bid, saldo in saldos.items() if saldo > 0 and bid in Broker.obj]
    brokers_levantar = sorted(brokers_levantar, key=lambda b: b.name.lower())

    df_all = pd.DataFrame(trades_data)
    total_investido = df_all['amount'].sum() if not df_all.empty else 0
    total_negocios = len(df_all)
    
    if not df_all.empty:
        df_grouped = df_all.groupby('broker_name')['amount'].sum().reset_index()
        df_grouped = df_grouped[df_grouped['amount'] > 0]
        
        if not df_grouped.empty:
            fig = px.pie(df_grouped, values='amount', names='broker_name',
                         title='Distribuição de Investimento por Corretor',
                         hole=0.4,
                         color_discrete_sequence=px.colors.sequential.RdBu)
            fig.update_layout(separators=',.')
            fig.update_traces(hovertemplate='%{label}<br>Investimento: %{value:,.2f} €<extra></extra>')
            graph_html = pio.to_html(fig, full_html=False)
        else:
            graph_html = "<p style='text-align:center; color:#7f8c8d;'>Sem investimentos ativos no momento.</p>"
    else:
        graph_html = "<p style='text-align:center; color:#7f8c8d;'>Sem investimentos ativos no momento.</p>"
    
    return render_template('cliente_dashboard.html', 
                           cliente=cliente, 
                           brokers_adicionar=brokers_adicionar,
                           brokers_levantar=brokers_levantar,
                           saldos_brokers=saldos,
                           negocios=df_all.to_dict('records') if not df_all.empty else [],
                           total_investido=total_investido,
                           total_negocios=total_negocios,
                           graph_html=graph_html)
    
@app.route('/cliente/close_account', methods=['POST'])
@require_role('client', 'admin')
def close_account():
    client_id = int(request.form.get('client_id'))
    
    if client_id not in Client.obj:
        return "Cliente não encontrado.", 404
        
    data_atual = datetime.now().strftime("%Y-%m-%d")
    
    # Calcular saldo total por broker para fazer a liquidação (Abordagem B)
    saldos = {}
    for t in Trade.obj.values():
        if t.client_id == client_id:
            saldos[t.broker_id] = saldos.get(t.broker_id, 0.0) + t.amount
            
    # Registar uma trade de "Levantamento Total" (Liquidação) onde o saldo for positivo
    for broker_id, saldo in saldos.items():
        if saldo > 0:
            new_id = max(Trade.lst) + 1 if Trade.lst else 1
            # Inserir montante negativo para zerar a conta
            Trade(new_id, broker_id, client_id, "Liquidação de Encerramento", data_atual, -saldo)
            query = f"INSERT INTO Trade (id, broker_id, client_id, name, date, amount) VALUES ({new_id}, {broker_id}, {client_id}, 'Liquidação de Encerramento', '{data_atual}', {-saldo})"
            Trade.sqlexe(query)
            
    # Remover o cliente do sistema (mantendo o histórico das trades)
    if client_id in Client.lst:
        Client.lst.remove(client_id)
    if client_id in Client.obj:
        del Client.obj[client_id]
        
    Client.sqlexe(f"DELETE FROM Client WHERE id={client_id}")
    session.clear()
    return redirect(url_for('index'))

@app.route('/trade/new', methods=['POST'])
@require_role('client', 'admin')
def new_trade():
    client_id = int(request.form.get('client_id'))
    broker_id = int(request.form.get('broker_id'))
    amount = float(request.form.get('amount'))
    tipo = request.form.get('tipo')
    data_atual = datetime.now().strftime("%Y-%m-%d")
        
    if tipo == 'investir':
        trade_name = "Novo Investimento"
        amount = abs(amount)
    else:
        saldo_neste_broker = sum(t.amount for t in Trade.obj.values() if t.client_id == client_id and t.broker_id == broker_id)
        if amount > saldo_neste_broker:
            return f"<h1>Operação Recusada!</h1><p>Tentou levantar {amount}€, mas o seu saldo no Broker selecionado é de apenas {saldo_neste_broker}€.</p><a href='/cliente/{client_id}/dashboard'>Voltar à Dashboard</a>", 400
        trade_name = "Levantamento"
        amount = -abs(amount)
        
    new_id = max(Trade.lst) + 1 if Trade.lst else 1
    Trade(new_id, broker_id, client_id, trade_name, data_atual, amount)
    query = f"INSERT INTO Trade (id, broker_id, client_id, name, date, amount) VALUES ({new_id}, {broker_id}, {client_id}, '{trade_name}', '{data_atual}', {amount})"
    Trade.sqlexe(query)
    return redirect(url_for('cliente_dashboard', id=client_id))

@app.route('/stats')
def stats():
    all_trades = list(Trade.obj.values())
    total_trades = len(all_trades)
    total_aum = sum(t.amount for t in all_trades)

    corp_volumes = {}
    for t in all_trades:
        broker = Broker.obj.get(t.broker_id)
        if broker:
            corp = Corporation.obj.get(broker.corporation_id)
            if corp:
                corp_volumes[corp.name] = corp_volumes.get(corp.name, 0) + t.amount

    df_corp = pd.DataFrame(list(corp_volumes.items()), columns=['Corporação', 'Volume'])
    df_corp = df_corp.sort_values('Volume', ascending=True).tail(10)
    fig_corp = px.bar(df_corp, x='Volume', y='Corporação', orientation='h',
        title='Top 10 Corporações por Volume',
        color='Volume', color_continuous_scale='Blues')
    fig_corp.update_layout(separators=',.')
    fig_corp.update_traces(hovertemplate='%{y}<br>Volume: %{x:,.2f} €<extra></extra>')
    fig_corp.update_xaxes(tickformat=',.2f')
    graph_corp = pio.to_html(fig_corp, full_html=False)

    broker_volumes = {}
    for t in all_trades:
        broker = Broker.obj.get(t.broker_id)
        if broker:
            broker_volumes[broker.name] = broker_volumes.get(broker.name, 0) + t.amount

    df_broker = pd.DataFrame(list(broker_volumes.items()), columns=['Corretor', 'Volume'])
    df_broker = df_broker.sort_values('Volume', ascending=True).tail(5)
    fig_broker = px.bar(df_broker, x='Volume', y='Corretor', orientation='h',
                        title='Top 5 Corretores por Volume',
                        color='Volume', color_continuous_scale='Blues')
    fig_broker.update_layout(separators=',.')
    fig_broker.update_traces(hovertemplate='%{y}<br>Volume: %{x:,.2f} €<extra></extra>')
    fig_broker.update_xaxes(tickformat=',.2f')
    graph_broker = pio.to_html(fig_broker, full_html=False)

    return render_template('stats.html',
                           total_trades=total_trades,
                           total_aum=total_aum,
                           num_clients=len(Client.lst),
                           num_brokers=len(Broker.lst),
                           num_corps=len(Corporation.lst),
                           graph_corp=graph_corp,
                           graph_broker=graph_broker)

if __name__ == '__main__':
    app.run(debug=True, port=5001)