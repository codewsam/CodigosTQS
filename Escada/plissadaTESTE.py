# -*- coding: utf-8 -*-
import os
import json
import math
import subprocess
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag


# ==============================================================================
# INTERFACE GRAFICA (HTA) COM OS DOIS BOTOES: ARMAR CORTE E ARMAR PLANTA
# ==============================================================================
def pedir_dados_armacao():
    """Abre a janela nativa para coletar parametros e escolher se arma Corte ou Planta."""
    caminho_script = os.path.dirname(os.path.abspath(__file__))
    hta_path = os.path.join(caminho_script, "dialogo_armacao.hta")
    json_path = os.path.join(caminho_script, "dados_armacao_temp.json")

    if os.path.exists(json_path):
        try:
            os.remove(json_path)
        except:
            pass

    json_js = json_path.replace('\\', '\\\\')

    hta_content = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <meta http-equiv="x-ua-compatible" content="ie=edge" />
        <title>Armacao da Escada - Plugin TQS</title>
        <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="ArmarEscada" BORDER="dialog" INNERBORDER="no" SCROLL="yes" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Tahoma, sans-serif;
                background: #eef1f5;
                margin: 0;
                padding: 0;
                font-size: 12px;
                color: #2b2f36;
            }}
            .topbar {{
                background: linear-gradient(135deg, #1b5e20 0%, #0d3810 100%);
                color: #fff;
                padding: 12px 18px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.25);
            }}
            .topbar h1 {{
                margin: 0;
                font-size: 15px;
                font-weight: 600;
            }}
            .topbar p {{
                margin: 2px 0 0 0;
                font-size: 11px;
                color: #c8e6c9;
            }}
            .container {{
                padding: 12px 18px;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }}
            .tabs {{
                display: flex;
                gap: 4px;
                border-bottom: 2px solid #c8d1dc;
                margin-bottom: 4px;
            }}
            .tab {{
                padding: 6px 14px;
                cursor: pointer;
                font-weight: 600;
                color: #556270;
                background: #e2e7ee;
                border-radius: 5px 5px 0 0;
                border: 1px solid #c8d1dc;
                border-bottom: none;
                font-size: 11.5px;
            }}
            .tab.active {{
                background: #ffffff;
                color: #1b5e20;
                border-top: 3px solid #1b5e20;
            }}
            .tab-content {{
                display: none;
                flex-direction: column;
                gap: 10px;
            }}
            .tab-content.active {{
                display: flex;
            }}
            .card {{
                background: #ffffff;
                border: 1px solid #dbe1e8;
                border-radius: 6px;
                padding: 10px 14px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
                display: flex;
                flex-direction: column;
                gap: 6px;
            }}
            .card h3 {{
                margin: 0 0 4px 0;
                color: #1b5e20;
                font-size: 11.5px;
                font-weight: 600;
                text-transform: uppercase;
                border-bottom: 1px solid #e7ebf0;
                padding-bottom: 3px;
            }}
            .card-blue h3 {{
                color: #0d47a1;
            }}
            .campo {{
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            label {{
                font-weight: 500;
                color: #45505c;
                font-size: 11.5px;
            }}
            input, select {{
                width: 95px;
                padding: 3px 6px;
                text-align: right;
                border: 1px solid #c3cbd4;
                border-radius: 4px;
                background: #fbfcfd;
                font-size: 11.5px;
            }}
            select {{ text-align: left; }}
            input:focus, select:focus {{
                outline: none;
                border-color: #1b5e20;
                box-shadow: 0 0 0 2px rgba(27,94,32,0.15);
                background: #fff;
            }}
            .btns {{
                display: flex;
                justify-content: flex-end;
                gap: 8px;
                margin-top: 6px;
                margin-bottom: 8px;
            }}
            button {{
                padding: 7px 14px;
                cursor: pointer;
                border: 1px solid #c3cbd4;
                border-radius: 5px;
                background: #f4f5f7;
                font-size: 11.5px;
                font-weight: 500;
            }}
            .btn-corte {{
                background: linear-gradient(135deg, #1b5e20 0%, #0d3810 100%);
                color: #fff;
                border: none;
                font-weight: 600;
            }}
            .btn-planta {{
                background: linear-gradient(135deg, #0d47a1 0%, #002171 100%);
                color: #fff;
                border: none;
                font-weight: 600;
            }}
            .card-purple h3 {{
                color: #6a1b9a;
            }}
            .btn-plissada {{
                background: linear-gradient(135deg, #6a1b9a 0%, #4a148c 100%);
                color: #fff;
                border: none;
                font-weight: 600;
            }}
        </style>
        <script>
            window.resizeTo(490, 560);

            function setTab(tabName) {{
                document.getElementById('tabCorte').className = (tabName == 'corte') ? 'tab active' : 'tab';
                document.getElementById('tabPlanta').className = (tabName == 'planta') ? 'tab active' : 'tab';
                document.getElementById('tabPlissada').className = (tabName == 'plissada') ? 'tab active' : 'tab';

                document.getElementById('contentCorte').className = (tabName == 'corte') ? 'tab-content active' : 'tab-content';
                document.getElementById('contentPlanta').className = (tabName == 'planta') ? 'tab-content active' : 'tab-content';
                document.getElementById('contentPlissada').className = (tabName == 'plissada') ? 'tab-content active' : 'tab-content';
                
                document.getElementById('btnCorte').style.display = (tabName == 'corte') ? 'inline-block' : 'none';
                document.getElementById('btnPlanta').style.display = (tabName == 'planta') ? 'inline-block' : 'none';
                document.getElementById('btnPlissada').style.display = (tabName == 'plissada') ? 'inline-block' : 'none';
            }}

            function confirmar(modoEscolhido) {{
                try {{
                    var fso = new ActiveXObject("Scripting.FileSystemObject");
                    var file = fso.CreateTextFile("{json_js}", true, false);

                    var dados = {{
                        "modo": modoEscolhido,

                        // Corte / Perfil
                        "bitola": parseFloat(document.getElementById('bitola').value.replace(',', '.')),
                        "espacamento": parseFloat(document.getElementById('espacamento').value.replace(',', '.')),
                        "quantidade": parseInt(document.getElementById('quantidade').value),
                        "cobrimento": parseFloat(document.getElementById('cobrimento').value.replace(',', '.')),
                        "espac_dist": parseFloat(document.getElementById('espac_dist').value.replace(',', '.')),

                        // Planta Baixa
                        "bitola_planta": parseFloat(document.getElementById('bitola_planta').value.replace(',', '.')),
                        "espacamento_planta": parseFloat(document.getElementById('espacamento_planta').value.replace(',', '.')),
                        "cobrimento_planta": parseFloat(document.getElementById('cobrimento_planta').value.replace(',', '.')),
                        "com_dobra_planta": parseInt(document.getElementById('com_dobra_planta').value),
                        "comp_dobra_planta": parseFloat(document.getElementById('comp_dobra_planta').value.replace(',', '.')),
                        "espelho_planta": parseFloat(document.getElementById('espelho_planta').value.replace(',', '.')),

                        // Escada Plissada (transpasse e tals: espessura e transpasse fixos em 15.0)
                        "bitola_plissada": parseFloat(document.getElementById('bitola_plissada').value.replace(',', '.')),
                        "espacamento_plissada": parseFloat(document.getElementById('espacamento_plissada').value.replace(',', '.')),
                        "multiplicador_plissada": parseInt(document.getElementById('multiplicador_plissada').value),
                        "cobrimento_plissada": parseFloat(document.getElementById('cobrimento_plissada').value.replace(',', '.')),
                        "espessura_plissada": 15.0,
                        "transpasse_plissada": 15.0
                    }};

                    file.Write(JSON.stringify(dados));
                    file.Close();
                    window.close();
                }} catch (e) {{
                    alert("Erro ao salvar: " + e.message);
                }}
            }}
        </script>
    </head>
    <body>
        <div class="topbar">
            <h1>Armacao da Escada</h1>
            <p>Plugin TQS &#9679 Ediglanthio Samuel Araujo Brandao &#9679 G3 Engenharia</p>
        </div>

        <div class="container">
            <div class="tabs">
                <div id="tabCorte" class="tab active" onclick="setTab('corte')">1. Corte / Perfil</div>
                <div id="tabPlanta" class="tab" onclick="setTab('planta')">2. Planta Baixa</div>
                <div id="tabPlissada" class="tab" onclick="setTab('plissada')">3. Escada Plissada</div>
            </div>

            <!-- CONTEUDO CORTE -->
            <div id="contentCorte" class="tab-content active">
                <div class="card">
                    <h3>Armadura Longitudinal (Corte)</h3>
                    <div class="campo">
                        <label>Bitola Principal:</label>
                        <select id="bitola">
                            <option value="5.0">5.0 mm</option>
                            <option value="6.3">6.3 mm</option>
                            <option value="8.0">8.0 mm</option>
                            <option value="10.0" selected>10.0 mm</option>
                            <option value="12.5">12.5 mm</option>
                            <option value="16.0">16.0 mm</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label>Espacamento Principal (cm):</label>
                        <input type="text" id="espacamento" value="15">
                    </div>
                    <div class="campo">
                        <label>Quantidade de Ferros:</label>
                        <input type="text" id="quantidade" value="8">
                    </div>
                    <div class="campo">
                        <label>Cobrimento (cm):</label>
                        <input type="text" id="cobrimento" value="2.5">
                    </div>
                    <div class="campo">
                        <label>Espacamento Distribuicao (cm):</label>
                        <input type="text" id="espac_dist" value="15">
                    </div>
                </div>
            </div>

            <!-- CONTEUDO PLANTA -->
            <div id="contentPlanta" class="tab-content">
                <div class="card card-blue">
                    <h3>Armadura da Planta Baixa</h3>
                    <div class="campo">
                        <label>Bitola:</label>
                        <select id="bitola_planta">
                            <option value="5.0">5.0 mm</option>
                            <option value="6.3">6.3 mm</option>
                            <option value="8.0" selected>8.0 mm</option>
                            <option value="10.0">10.0 mm</option>
                            <option value="12.5">12.5 mm</option>
                            <option value="16.0">16.0 mm</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label>Espacamento (cm):</label>
                        <input type="text" id="espacamento_planta" value="15">
                    </div>
                    <div class="campo">
                        <label>Cobrimento (cm):</label>
                        <input type="text" id="cobrimento_planta" value="2.5">
                    </div>
                    <div class="campo">
                        <label>Espelho do Degrau (cm):</label>
                        <input type="text" id="espelho_planta" value="17.5">
                    </div>
                    <div class="campo">
                        <label>Com Dobras nas Pontas:</label>
                        <select id="com_dobra_planta">
                            <option value="1" selected>Sim</option>
                            <option value="0">Nao</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label>Comprimento da Dobra (cm):</label>
                        <input type="text" id="comp_dobra_planta" value="15">
                    </div>
                </div>
            </div>

            <!-- CONTEUDO ESCADA PLISSADA -->
            <div id="contentPlissada" class="tab-content">
                <div class="card card-purple">
                    <h3>Armadura de Estribos (Escada Plissada)</h3>
                    <div class="campo">
                        <label>Bitola do Estribo:</label>
                        <select id="bitola_plissada">
                            <option value="5.0">5.0 mm</option>
                            <option value="6.3">6.3 mm</option>
                            <option value="8.0" selected>8.0 mm</option>
                            <option value="10.0">10.0 mm</option>
                            <option value="12.5">12.5 mm</option>
                            <option value="16.0">16.0 mm</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label>Espacamento (cm):</label>
                        <input type="text" id="espacamento_plissada" value="15">
                    </div>
                    <div class="campo">
                        <label>Multiplicador por Degrau (ex: 7x):</label>
                        <input type="text" id="multiplicador_plissada" value="7">
                    </div>
                    <div class="campo">
                        <label>Cobrimento (cm):</label>
                        <input type="text" id="cobrimento_plissada" value="2.5">
                    </div>
                </div>
            </div>

            <!-- TRES BOTOES DE ACAO CONFORME A ABA SELECIONADA -->
            <div class="btns">
                <button onclick="window.close()">Cancelar</button>
                <button id="btnCorte" class="btn-corte" onclick="confirmar('CORTE')">&#9658; Escada</button>
                <button id="btnPlanta" class="btn-planta" style="display: none;" onclick="confirmar('PLANTA')">&#9658; Planta Baixa</button>
                <button id="btnPlissada" class="btn-plissada" style="display: none;" onclick="confirmar('PLISSADA')">&#9658; Escada Plissada</button>
            </div>
        </div>
    </body>
    </html>
    """

    with open(hta_path, "w", encoding="utf-8-sig") as f:
        f.write(hta_content)

    subprocess.call(["mshta", hta_path])

    dados = None
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            dados = json.load(f)
        os.remove(json_path)

    if os.path.exists(hta_path):
        try:
            os.remove(hta_path)
        except:
            pass

    return dados


# ==============================================================================
# RECONHECIMENTO GEOMETRICO DO PERFIL DA ESCADA (CORTE) - SUPORTA 1 OU 2 LANCES
# ==============================================================================
def identificar_geometria_escada(linhas):
    """
    Analisa as linhas selecionadas e identifica os lances da escada em corte.
    Se houver 2 lances (escada de 2 lances), seleciona automaticamente o segundo lance (superior).
    """
    horizontais = []
    verticais = []
    inclinadas = []

    for (x1, y1), (x2, y2) in linhas:
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        if dx < 0.1:  # Vertical
            verticais.append((x1, min(y1, y2), max(y1, y2), dy))
        elif dy < 0.1:  # Horizontal
            horizontais.append((min(x1, x2), max(x1, x2), y1, dx))
        else:
            inclinadas.append(((min(x1, x2), y1 if x1 < x2 else y2), (max(x1, x2), y2 if x1 < x2 else y1)))

    if not verticais or not horizontais:
        return None

    # Filtrar espelhos dos degraus (verticais com altura tipica de espelho: 12 a 25 cm)
    espelhos = [v for v in verticais if 12.0 <= v[3] <= 25.0]
    if not espelhos:
        espelhos = [v for v in verticais if v[3] < 30.0]

    if len(espelhos) < 2:
        return None

    # Agrupar espelhos em cadeias continuas de degraus (lances)
    chains = []
    visited = set()
    for e in sorted(espelhos, key=lambda v: (v[1], v[0])):
        if (round(e[0], 1), round(e[1], 1)) in visited:
            continue
        chain = [e]
        curr = e
        while True:
            candidates = [
                c for c in espelhos 
                if (round(c[0], 1), round(c[1], 1)) not in visited
                and 10.0 <= (c[1] - curr[1]) <= 25.0
                and 18.0 <= abs(c[0] - curr[0]) <= 38.0
            ]
            if not candidates:
                break
            if len(chain) >= 2:
                prev_dx = chain[-1][0] - chain[-2][0]
                prev_dy = chain[-1][1] - chain[-2][1]
                candidates.sort(key=lambda c: (abs(c[0] - curr[0] - prev_dx), abs(c[1] - curr[1] - prev_dy)))
            else:
                candidates.sort(key=lambda c: abs(c[1] - curr[1] - curr[3]))
            next_step = candidates[0]
            chain.append(next_step)
            curr = next_step

        if len(chain) >= 2:
            for item in chain:
                visited.add((round(item[0], 1), round(item[1], 1)))
            chains.append(chain)

    if not chains:
        return None

    # Ordenar cadeias por cota vertical base (y_base)
    chains.sort(key=lambda c: c[0][1])

    # Se houver 2 ou mais lances, armar no segundo lance (lance superior) conforme solicitado
    if len(chains) >= 2:
        lance_selecionado = chains[-1]
        num_lance_msg = "Segundo Lance (Lance 2 - Superior)"
    else:
        lance_selecionado = chains[0]
        num_lance_msg = "Lance Unico"

    espelhos_lance = lance_selecionado
    n_degraus = len(espelhos_lance)

    # Determinar sentido de subida do lance
    dx_subida = espelhos_lance[1][0] - espelhos_lance[0][0] if len(espelhos_lance) > 1 else 1.0
    sentido = 'DIREITA' if dx_subida > 0 else 'ESQUERDA'

    x0 = espelhos_lance[0][0]
    y0 = espelhos_lance[0][1]
    x_topo = espelhos_lance[-1][0]
    y_topo = espelhos_lance[-1][2]

    # Piso e Espelho medios
    pisos_vals = [abs(espelhos_lance[i+1][0] - espelhos_lance[i][0]) for i in range(n_degraus - 1)]
    piso = (sum(pisos_vals) / len(pisos_vals)) if pisos_vals else 28.0
    espelho = sum(e[3] for e in espelhos_lance) / n_degraus

    # 4. Patamar de Partida
    patamar_partida = 0.0
    if sentido == 'DIREITA':
        cand_part = [h for h in horizontais if abs(h[2] - y0) < 2.5 and h[1] <= x0 + 1.0]
        if cand_part:
            patamar_partida = max(h[3] for h in cand_part)
        if patamar_partida < 30.0:
            patamar_partida = 120.0
    else:  # ESQUERDA (patamar de partida fica a direita)
        cand_part = [h for h in horizontais if abs(h[2] - y0) < 2.5 and h[0] >= x0 - 1.0]
        if cand_part:
            patamar_partida = max(h[3] for h in cand_part)
        if patamar_partida < 30.0:
            patamar_partida = 120.0

    # 5. Patamar de Chegada
    patamar_chegada = 0.0
    if sentido == 'DIREITA':
        cand_cheg = [h for h in horizontais if abs(h[2] - y_topo) < 2.5 and h[0] >= x_topo - 1.0]
        if cand_cheg:
            patamar_chegada = max(h[3] for h in cand_cheg)
        if patamar_chegada < 30.0:
            patamar_chegada = 120.0
    else:  # ESQUERDA (patamar de chegada fica a esquerda)
        cand_cheg = [h for h in horizontais if abs(h[2] - y_topo) < 2.5 and h[1] <= x_topo + 1.0]
        if cand_cheg:
            patamar_chegada = max(h[3] for h in cand_cheg)
        if patamar_chegada < 30.0:
            patamar_chegada = 120.0

    # 6. Espessura da Laje
    espessura = 15.0
    linha_fundo_inc = None
    if inclinadas:
        inclinadas.sort(key=lambda seg: math.hypot(seg[1][0] - seg[0][0], seg[1][1] - seg[0][1]), reverse=True)
        linha_fundo_inc = inclinadas[0]
        canto_x = (x0 + piso) if sentido == 'DIREITA' else (x0 - piso)
        canto_y = y0 + espelho
        try:
            espessura = TQSGeo.DistancePointLine(linha_fundo_inc[0][0], linha_fundo_inc[0][1], linha_fundo_inc[1][0], linha_fundo_inc[1][1], canto_x, canto_y)
        except:
            espessura = 15.0

    if espessura < 8.0 or espessura > 35.0:
        espessura = 15.0

    # 7. Vigas de apoio
    viga_largura = 20.0
    viga_altura = 40.0

    return {
        "num_lances": len(chains),
        "sentido": sentido,
        "x0": x0,
        "y0": y0,
        "n_degraus": n_degraus,
        "piso": piso,
        "espelho": espelho,
        "patamar_partida": patamar_partida,
        "patamar_chegada": patamar_chegada,
        "espessura": espessura,
        "viga_largura": viga_largura,
        "viga_altura": viga_altura,
        "x_topo": x_topo,
        "y_topo": y_topo,
        "linha_fundo_inc": linha_fundo_inc
    }


# ==============================================================================
# RECONHECIMENTO GEOMETRICO DA PLANTA BAIXA DA ESCADA
# ==============================================================================
def identificar_geometria_planta_escada(linhas, textos=None):
    """
    Analisa as linhas e textos selecionados para deduzir a geometria completa
    da escada em Planta Baixa (lances, degraus, patamares, parede/vao central).
    """
    if textos is None:
        textos = []

    horizontais = []
    verticais = []
    
    for (x1, y1), (x2, y2) in linhas:
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        length = math.hypot(dx, dy)
        if length < 2.0:
            continue
        if dx < 0.2:  # Linha Vertical
            verticais.append((x1, min(y1, y2), max(y1, y2), length))
        elif dy < 0.2:  # Linha Horizontal
            horizontais.append((min(x1, x2), max(x1, x2), y1, length))

    # CASO 1: Escada com orientacao HORIZONTAL (degraus sao linhas verticais com comp >= 45 cm)
    degraus_cands_v = [v for v in verticais if v[3] >= 45.0]
    
    # Agrupar linhas verticais por faixa de Y (lances diferentes)
    grupos_v = []
    for v in degraus_cands_v:
        x, ymin, ymax, l = v
        adicionado = False
        for g in grupos_v:
            g_ymin = sum(item[1] for item in g) / len(g)
            g_ymax = sum(item[2] for item in g) / len(g)
            if abs(ymin - g_ymin) < 25.0 and abs(ymax - g_ymax) < 25.0:
                g.append(v)
                adicionado = True
                break
        if not adicionado:
            grupos_v.append([v])

    lances_identificados = []
    for g in grupos_v:
        g.sort(key=lambda item: item[0])
        unicos = []
        for item in g:
            if not unicos or (item[0] - unicos[-1][0]) > 2.0:
                unicos.append(item)
        
        if len(unicos) >= 3:
            # Encontrar sequencia continua com espacamentos tipicos de piso (20 a 40 cm)
            subsequencias = []
            sub_atual = [unicos[0]]
            for i in range(len(unicos) - 1):
                dx = unicos[i+1][0] - unicos[i][0]
                if 20.0 <= dx <= 40.0:
                    sub_atual.append(unicos[i+1])
                else:
                    if len(sub_atual) >= 3:
                        subsequencias.append(sub_atual)
                    sub_atual = [unicos[i+1]]
            if len(sub_atual) >= 3:
                subsequencias.append(sub_atual)
            
            for degraus_finais in subsequencias:
                dxs = [degraus_finais[k+1][0] - degraus_finais[k][0] for k in range(len(degraus_finais)-1)]
                piso_med = sum(dxs) / len(dxs)
                largura_med = sum(d[3] for d in degraus_finais) / len(degraus_finais)
                ymin_med = sum(d[1] for d in degraus_finais) / len(degraus_finais)
                ymax_med = sum(d[2] for d in degraus_finais) / len(degraus_finais)
                lances_identificados.append({
                    'orientacao': 'HORIZONTAL',
                    'n_degraus': len(degraus_finais) - 1,
                    'n_linhas_degraus': len(degraus_finais),
                    'piso': round(piso_med, 1),
                    'largura': round(largura_med, 1),
                    'x_ini': degraus_finais[0][0],
                    'x_fim': degraus_finais[-1][0],
                    'y_base': round(ymin_med, 1),
                    'y_topo': round(ymax_med, 1),
                    'degraus_coords': [round(d[0], 1) for d in degraus_finais]
                })

    # CASO 2: Se nao achou na horizontal, tentar orientacao VERTICAL
    if not lances_identificados:
        degraus_cands_h = [h for h in horizontais if h[3] >= 45.0]
        grupos_h = []
        for h in degraus_cands_h:
            xmin, xmax, y, l = h
            adicionado = False
            for g in grupos_h:
                g_xmin = sum(item[0] for item in g) / len(g)
                g_xmax = sum(item[1] for item in g) / len(g)
                if abs(xmin - g_xmin) < 25.0 and abs(xmax - g_xmax) < 25.0:
                    g.append(h)
                    adicionado = True
                    break
            if not adicionado:
                grupos_h.append([h])

        for g in grupos_h:
            g.sort(key=lambda item: item[2])
            unicos = []
            for item in g:
                if not unicos or (item[2] - unicos[-1][2]) > 2.0:
                    unicos.append(item)
            if len(unicos) >= 3:
                subsequencias = []
                sub_atual = [unicos[0]]
                for i in range(len(unicos) - 1):
                    dy = unicos[i+1][2] - unicos[i][2]
                    if 20.0 <= dy <= 40.0:
                        sub_atual.append(unicos[i+1])
                    else:
                        if len(sub_atual) >= 3:
                            subsequencias.append(sub_atual)
                        sub_atual = [unicos[i+1]]
                if len(sub_atual) >= 3:
                    subsequencias.append(sub_atual)
                for degraus_finais in subsequencias:
                    dys = [degraus_finais[k+1][2] - degraus_finais[k][2] for k in range(len(degraus_finais)-1)]
                    piso_med = sum(dys) / len(dys)
                    largura_med = sum(d[3] for d in degraus_finais) / len(degraus_finais)
                    xmin_med = sum(d[0] for d in degraus_finais) / len(degraus_finais)
                    xmax_med = sum(d[1] for d in degraus_finais) / len(degraus_finais)
                    lances_identificados.append({
                        'orientacao': 'VERTICAL',
                        'n_degraus': len(degraus_finais) - 1,
                        'n_linhas_degraus': len(degraus_finais),
                        'piso': round(piso_med, 1),
                        'largura': round(largura_med, 1),
                        'y_ini': degraus_finais[0][2],
                        'y_fim': degraus_finais[-1][2],
                        'x_base': round(xmin_med, 1),
                        'x_topo': round(xmax_med, 1),
                        'degraus_coords': [round(d[2], 1) for d in degraus_finais]
                    })

    if not lances_identificados:
        return None

    # Ordenar e classificar lances
    if lances_identificados[0]['orientacao'] == 'HORIZONTAL':
        lances_identificados.sort(key=lambda l: l['y_base'])
        for idx, l in enumerate(lances_identificados):
            l['posicao'] = 'INFERIOR' if idx == 0 and len(lances_identificados) > 1 else ('SUPERIOR' if len(lances_identificados) > 1 else 'UNICO')
            l['indice'] = idx + 1
    else:
        lances_identificados.sort(key=lambda l: l['x_base'])
        for idx, l in enumerate(lances_identificados):
            l['posicao'] = 'ESQUERDO' if idx == 0 and len(lances_identificados) > 1 else ('DIREITO' if len(lances_identificados) > 1 else 'UNICO')
            l['indice'] = idx + 1

    elemento_central = None
    if len(lances_identificados) == 2 and lances_identificados[0]['orientacao'] == 'HORIZONTAL':
        l1 = lances_identificados[0]
        l2 = lances_identificados[1]
        gap = l2['y_base'] - l1['y_topo']
        
        tem_texto_alv = False
        for xt, yt, txt in textos:
            if any(w in txt.upper() for w in ['ALVENARIA', 'PAREDE', 'ALV']):
                tem_texto_alv = True
                break
        
        tipo_elem = 'PAREDE_ALVENARIA' if (tem_texto_alv or (7.0 <= gap <= 35.0)) else ('VAO_CENTRAL' if gap > 0 else 'NENHUM')
        
        elemento_central = {
            'tipo': tipo_elem,
            'espessura': round(gap, 1) if gap > 0 else 0.0,
            'y_base': l1['y_topo'],
            'y_topo': l2['y_base'],
            'x_ini': min(l1['x_ini'], l2['x_ini']),
            'x_fim': max(l1['x_fim'], l2['x_fim'])
        }

    patamar_esq = None
    patamar_dir = None
    if lances_identificados[0]['orientacao'] == 'HORIZONTAL':
        x_min_deg = min(l['x_ini'] for l in lances_identificados)
        x_max_deg = max(l['x_fim'] for l in lances_identificados)
        y_min_total = min(l['y_base'] for l in lances_identificados)
        y_max_total = max(l['y_topo'] for l in lances_identificados)
        
        # Patamar Esquerdo: detectar vao livre SEM a viga/parede
        vert_esq = [v for v in verticais if v[0] < x_min_deg - 5.0 and not (v[2] < y_min_total - 60.0 or v[1] > y_max_total + 60.0)]
        if vert_esq:
            xs_esq = sorted(list(set(round(v[0], 1) for v in vert_esq)))
            x_outer_esq = xs_esq[0]  # Linha vertical mais a esquerda (face externa)
            
            # Procurar face interna da viga (distante entre 10 e 35 cm da face externa)
            x_inner_esq = None
            for x_cand in xs_esq:
                if (10.0 <= x_cand - x_outer_esq <= 35.0) and (x_min_deg - x_cand >= 30.0):
                    x_inner_esq = x_cand
                    break
            
            # Se achou face interna, usa ela; senao desconta 20cm se for linha externa
            if x_inner_esq is not None:
                x_livre_esq = x_inner_esq
            else:
                tot = x_min_deg - x_outer_esq
                x_livre_esq = (x_outer_esq + 20.0) if tot > 60.0 else x_outer_esq

            comp_esq_livre = x_min_deg - x_livre_esq
            comp_esq_tot = x_min_deg - x_outer_esq
            if comp_esq_livre >= 25.0:
                patamar_esq = {
                    'existe': True,
                    'comprimento': round(comp_esq_livre, 1),
                    'comprimento_total': round(comp_esq_tot, 1),
                    'comprimento_livre': round(comp_esq_livre, 1),
                    'x_min': round(x_livre_esq, 1),
                    'x_min_livre': round(x_livre_esq, 1),
                    'x_min_externo': round(x_outer_esq, 1),
                    'x_max': round(x_min_deg, 1)
                }

        # Patamar Direito: detectar vao livre SEM a viga/parede
        vert_dir = [v for v in verticais if v[0] > x_max_deg + 5.0 and not (v[2] < y_min_total - 60.0 or v[1] > y_max_total + 60.0)]
        if vert_dir:
            xs_dir = sorted(list(set(round(v[0], 1) for v in vert_dir)), reverse=True)
            x_outer_dir = xs_dir[0]  # Linha vertical mais a direita (face externa)
            
            # Procurar face interna da viga (distante entre 10 e 35 cm da face externa)
            x_inner_dir = None
            for x_cand in xs_dir:
                if (10.0 <= x_outer_dir - x_cand <= 35.0) and (x_cand - x_max_deg >= 30.0):
                    x_inner_dir = x_cand
                    break
            
            if x_inner_dir is not None:
                x_livre_dir = x_inner_dir
            else:
                tot = x_outer_dir - x_max_deg
                x_livre_dir = (x_outer_dir - 20.0) if tot > 60.0 else x_outer_dir

            comp_dir_livre = x_livre_dir - x_max_deg
            comp_dir_tot = x_outer_dir - x_max_deg
            if comp_dir_livre >= 25.0:
                patamar_dir = {
                    'existe': True,
                    'comprimento': round(comp_dir_livre, 1),
                    'comprimento_total': round(comp_dir_tot, 1),
                    'comprimento_livre': round(comp_dir_livre, 1),
                    'x_min': round(x_max_deg, 1),
                    'x_min_livre': round(x_max_deg, 1),
                    'x_max': round(x_livre_dir, 1),
                    'x_max_livre': round(x_livre_dir, 1),
                    'x_max_externo': round(x_outer_dir, 1)
                }

    sentido_geral = None
    for xt, yt, txt in textos:
        txt_u = txt.upper()
        if 'DESCE' in txt_u:
            sentido_geral = 'DESCE'
        elif 'SOBE' in txt_u:
            sentido_geral = 'SOBE'

    # Identificar limites externos (vigas/paredes externas superior e inferior)
    y_min_total = min(l["y_base"] for l in lances_identificados)
    y_max_total = max(l["y_topo"] for l in lances_identificados)

    long_h = [h for h in horizontais if h[3] >= 100.0]
    if not long_h:
        long_h = horizontais

    if long_h:
        cands_y_min = [h[2] for h in long_h if h[2] <= y_min_total + 1.0]
        y_outer_min = min(cands_y_min) if cands_y_min else y_min_total - 20.0

        cands_y_max = [h[2] for h in long_h if h[2] >= y_max_total - 1.0]
        y_outer_max = max(cands_y_max) if cands_y_max else y_max_total + 20.0
    else:
        y_outer_min = y_min_total - 20.0
        y_outer_max = y_max_total + 20.0

    return {
        'tipo_vista': 'PLANTA_BAIXA',
        'orientacao': lances_identificados[0]['orientacao'],
        'num_lances': len(lances_identificados),
        'lances': lances_identificados,
        'elemento_central': elemento_central,
        'patamar_esquerdo': patamar_esq,
        'patamar_direito': patamar_dir,
        'y_base_externo': round(y_outer_min, 1),
        'y_topo_externo': round(y_outer_max, 1),
        'sentido': sentido_geral,
        'textos': textos
    }


# ==============================================================================
# RECONHECIMENTO GEOMETRICO DE ESCADA PLISSADA (CASCATA / ZIGUE-ZAGUE)
# ==============================================================================
def identificar_geometria_escada_plissada(linhas):
    """
    Analisa as linhas selecionadas e identifica os degraus em zigue-zague
    da escada plissada (pisos, espelhos, espessura da laje e patamares).
    Filtra rigorosamente apenas os espelhos de topo (face externa dos degraus).
    """
    horizontais = []
    verticais = []

    for (x1, y1), (x2, y2) in linhas:
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        length = math.hypot(dx, dy)
        if length < 2.0:
            continue
        if dx < 0.2:  # Vertical
            verticais.append((x1, min(y1, y2), max(y1, y2), dy))
        elif dy < 0.2:  # Horizontal
            horizontais.append((min(x1, x2), max(x1, x2), y1, dx))

    if not verticais or not horizontais:
        return None

    # Espelhos candidatos (verticais com altura típica de espelho entre 10 e 35 cm)
    espelhos_cands = [v for v in verticais if 10.0 <= v[3] <= 35.0]
    if len(espelhos_cands) < 2:
        return None

    # Filtrar exclusivamente espelhos superiores (se houver espelho inferior próximo em X com y_max menor, descartar o inferior)
    espelhos_topo = []
    for v in espelhos_cands:
        tem_superior = False
        for v_outro in espelhos_cands:
            if v_outro is not v and abs(v[0] - v_outro[0]) < 18.0 and (v_outro[2] - v[2]) > 5.0:
                tem_superior = True
                break
        if not tem_superior:
            espelhos_topo.append(v)

    if len(espelhos_topo) < 2:
        espelhos_topo = espelhos_cands

    # Montar cadeias contínuas de espelhos de topo
    chains = []
    visited = set()
    for e in sorted(espelhos_topo, key=lambda v: (v[1], v[0])):
        if (round(e[0], 1), round(e[1], 1)) in visited:
            continue
        chain = [e]
        curr = e
        while True:
            candidates = [
                c for c in espelhos_topo
                if (round(c[0], 1), round(c[1], 1)) not in visited
                and 8.0 <= (c[1] - curr[1]) <= 28.0
                and 16.0 <= abs(c[0] - curr[0]) <= 40.0
            ]
            if not candidates:
                break
            if len(chain) >= 2:
                prev_dx = chain[-1][0] - chain[-2][0]
                prev_dy = chain[-1][1] - chain[-2][1]
                candidates.sort(key=lambda c: (abs(c[0] - curr[0] - prev_dx), abs(c[1] - curr[1] - prev_dy)))
            else:
                candidates.sort(key=lambda c: abs(c[1] - curr[1] - curr[3]))
            next_step = candidates[0]
            chain.append(next_step)
            curr = next_step

        if len(chain) >= 2:
            for item in chain:
                visited.add((round(item[0], 1), round(item[1], 1)))
            chains.append(chain)

    if not chains:
        return None

    # Escolher a cadeia com maior número de degraus
    chains.sort(key=lambda c: len(c), reverse=True)
    espelhos_lance = chains[0]
    n_degraus = len(espelhos_lance)

    dx_subida = espelhos_lance[1][0] - espelhos_lance[0][0] if len(espelhos_lance) > 1 else 1.0
    sentido = 'DIREITA' if dx_subida > 0 else 'ESQUERDA'

    x0 = espelhos_lance[0][0]
    y0 = espelhos_lance[0][1]
    x_topo = espelhos_lance[-1][0]
    y_topo = espelhos_lance[-1][2]

    # Medias de piso e espelho
    pisos_vals = [abs(espelhos_lance[i+1][0] - espelhos_lance[i][0]) for i in range(n_degraus - 1)]
    piso = (sum(pisos_vals) / len(pisos_vals)) if pisos_vals else 28.0
    espelho = sum(e[3] for e in espelhos_lance) / n_degraus

    # Detectar espessura da laje plissada (distancia vertical entre o piso superior e o piso inferior)
    espessuras_detectadas = []
    for e_step in espelhos_lance:
        y_tread_top = e_step[2]
        cands_h = [h for h in horizontais if (h[2] < y_tread_top - 5.0) and (h[2] >= y_tread_top - 30.0)]
        for h in cands_h:
            dist = y_tread_top - h[2]
            if 8.0 <= dist <= 25.0:
                espessuras_detectadas.append(dist)

    if espessuras_detectadas:
        espessura_calc = sum(espessuras_detectadas) / len(espessuras_detectadas)
    else:
        espessura_calc = 12.0

    # Construir dados detalhados de cada degrau
    steps_data = []
    for i, e_step in enumerate(espelhos_lance):
        x_r = e_step[0]
        y_r_bot = e_step[1]
        y_r_top = e_step[2]
        steps_data.append({
            'indice': i,
            'x_riser': x_r,
            'y_riser_bot': y_r_bot,
            'y_riser_top': y_r_top,
            'altura_riser': e_step[3]
        })

    return {
        "tipo": "ESCADA_PLISSADA",
        "sentido": sentido,
        "n_degraus": n_degraus,
        "x0": x0,
        "y0": y0,
        "x_topo": x_topo,
        "y_topo": y_topo,
        "piso": round(piso, 1),
        "espelho": round(espelho, 1),
        "espessura": round(espessura_calc, 1),
        "espelhos": espelhos_lance,
        "steps": steps_data,
        "horizontais": horizontais,
        "verticais": verticais
    }


def obter_fundo_lance(p1x, p1y, p2x, p2y, espessura):
    """Calcula a reta paralela da face inferior da laje inclinada."""
    xa1, ya1, xa2, ya2 = TQSGeo.ParallelLine(p1x, p1y, p2x, p2y, espessura)
    xb1, yb1, xb2, yb2 = TQSGeo.ParallelLine(p1x, p1y, p2x, p2y, -espessura)
    ym = (p1y + p2y) / 2.0
    if ((ya1 + ya2) / 2.0) < ym:
        return xa1, ya1, xa2, ya2
    return xb1, yb1, xb2, yb2


def calcular_x_no_y(x1, y1, x2, y2, y_alvo):
    if abs(y2 - y1) > 1e-9:
        t = (y_alvo - y1) / (y2 - y1)
        return x1 + t * (x2 - x1)
    return x1


def calcular_y_no_x(x1, y1, x2, y2, x_alvo):
    if abs(x2 - x1) > 1e-9:
        t = (x_alvo - x1) / (x2 - x1)
        return y1 + t * (y2 - y1)
    return y1


# ==============================================================================
# FERROS DO PERFIL / CORTE DA ESCADA (N1, N2, N3, DISTRIBUICAO)
# ==============================================================================
def desenhar_ferro_principal_maior(dwg, geo, dados_ferros):
    """Calcula e desenha o ferro positivo principal no corte (suporta subida para Direita e Esquerda)."""
    sentido = geo.get("sentido", "DIREITA")
    x0 = geo["x0"]
    y0 = geo["y0"]
    n_deg = geo["n_degraus"]
    piso = geo["piso"]
    espelho = geo["espelho"]
    pat_part = geo["patamar_partida"]
    pat_cheg = geo["patamar_chegada"]
    espessura = geo["espessura"]
    viga_l = geo["viga_largura"]
    viga_h = geo["viga_altura"]
    x_topo = geo["x_topo"]
    y_topo = geo["y_topo"]

    cobr = float(dados_ferros.get("cobrimento_planta", dados_ferros.get("cobrimento", 2.5)))
    bitola = float(dados_ferros["bitola"])
    espac = float(dados_ferros["espacamento"])
    qtd = int(dados_ferros["quantidade"])

    ang = math.atan2(espelho, piso)
    cos_a = math.cos(ang)
    sin_a = math.sin(ang)
    dist_fundo = espessura - cobr

    if sentido == "DIREITA":
        p1x, p1y = x0 + piso, y0 + espelho
        p2x, p2y = x0 + (n_deg - 1) * piso, y0 + (n_deg - 1) * espelho
        f_x1, f_y1, f_x2, f_y2 = obter_fundo_lance(p1x, p1y, p2x, p2y, dist_fundo)

        x_viga_inf = (x0 - pat_part - viga_l) + cobr
        y_gancho_inf_base = y0 - viga_h + cobr

        y_topo_arm = y_topo - cobr
        pt_topo_x = calcular_x_no_y(f_x1, f_y1, f_x2, f_y2, y_topo_arm)

        x_viga_sup = x_topo + pat_cheg + viga_l - cobr
        y_gancho_sup_base = y_topo - viga_h + cobr

        if pat_part > 0:
            y_fundo_pat_part = y0 - espessura + cobr
            pt3_x = calcular_x_no_y(f_x1, f_y1, f_x2, f_y2, y_fundo_pat_part)

            pontos_ferro = [
                (x_viga_inf, y_gancho_inf_base),
                (x_viga_inf, y_fundo_pat_part),
                (pt3_x, y_fundo_pat_part),
                (pt_topo_x, y_topo_arm),
                (x_viga_sup, y_topo_arm),
                (x_viga_sup, y_gancho_sup_base)
            ]
        else:
            y_inc_inf = calcular_y_no_x(f_x1, f_y1, f_x2, f_y2, x_viga_inf)
            pontos_ferro = [
                (x_viga_inf, y_gancho_inf_base),
                (x_viga_inf, y_inc_inf),
                (pt_topo_x, y_topo_arm),
                (x_viga_sup, y_topo_arm),
                (x_viga_sup, y_gancho_sup_base)
            ]
    else:  # Subindo para a ESQUERDA (como na escada de 2 lances no lance superior)
        # Reta de referencia do fundo inclinado da laje
        fx_ref = (x0 - piso) - dist_fundo * sin_a
        fy_ref = (y0 + espelho) - dist_fundo * cos_a

        # Patamar de partida (a direita)
        x_viga_part = (x0 + pat_part + viga_l) - cobr
        y_fundo_pat_part = y0 - espessura + cobr
        y_gancho_part_base = y0 - viga_h + cobr

        # Transicao no patamar de partida (a direita)
        t_part = (y_fundo_pat_part - fy_ref) / sin_a
        x_kink_part = fx_ref - t_part * cos_a

        # Transicao no patamar superior (a esquerda)
        y_topo_arm = y_topo - cobr
        t_cheg = (y_topo_arm - fy_ref) / sin_a
        x_kink_cheg = fx_ref - t_cheg * cos_a

        # Viga de chegada no patamar superior (a esquerda)
        x_viga_cheg = (x_topo - pat_cheg - viga_l) + cobr
        y_gancho_cheg_base = y_topo - viga_h + cobr

        pontos_ferro = [
            (x_viga_part, y_gancho_part_base),
            (x_viga_part, y_fundo_pat_part),
            (x_kink_part, y_fundo_pat_part),
            (x_kink_cheg, y_topo_arm),
            (x_viga_cheg, y_topo_arm),
            (x_viga_cheg, y_gancho_cheg_base)
        ]

    try:
        rebar = TQSDwg.SmartRebar(dwg)
        rebar.type = TQSDwg.ICPFGN
        rebar.diameter = bitola
        rebar.spacing = espac
        rebar.quantity = qtd
        try:
            if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                f_mark = dwg.globalrebar.FreeMark()
                rebar.mark = f_mark if f_mark > 0 else 1
            else:
                rebar.mark = 1
        except:
            rebar.mark = 1

        for px, py in pontos_ferro:
            rebar.GenRebarPoint(px, py, 0.0, 0, 1, -1)

        # Inserir no Nivel 220, Cor por nivel (-1), Estilo por nivel (-1)
        rebar.RebarLine(0.0, 0.0, 0.0, 1.0, 0, 0, 0, 0, 220, -1, -1)
        is_dois_lances = (geo.get("num_lances", 1) >= 2) or (sentido == "ESQUERDA")
        dx_rebatido = 220.0 if is_dois_lances else 0.0
        dy_rebatido = -290.0 if is_dois_lances else -120.0
        rebar.RebarLine(dx_rebatido, dy_rebatido, 0.0, 1.0, 1, 1, 0, 0, 220, -1, -1)

    except Exception as e:
        TQSUtil.writef("Erro ao gerar SmartRebar N1: %s" % str(e))


def desenhar_ferro_no_superior(dwg, geo, dados_ferros):
    """Calcula e desenha o ferro negativo do no superior / patamar de chegada (N2)."""
    sentido = geo.get("sentido", "DIREITA")
    x0 = geo["x0"]
    y0 = geo["y0"]
    n_deg = geo["n_degraus"]
    piso = geo["piso"]
    espelho = geo["espelho"]
    pat_cheg = geo["patamar_chegada"]
    espessura = geo["espessura"]
    viga_l = geo["viga_largura"]
    viga_h = geo["viga_altura"]
    x_topo = geo["x_topo"]
    y_topo = geo["y_topo"]

    cobr = float(dados_ferros.get("cobrimento_planta", dados_ferros.get("cobrimento", 2.5)))
    bitola = float(dados_ferros["bitola"])
    espac = float(dados_ferros["espacamento"])
    qtd = int(dados_ferros["quantidade"])

    ang = math.atan2(espelho, piso)
    cos_a = math.cos(ang)
    sin_a = math.sin(ang)
    passo_diag = math.hypot(piso, espelho)
    comp_anc = min(140.0, max(90.0, 4.0 * passo_diag))
    y_fundo_pat_cheg = y_topo - espessura + cobr
    y_gancho_sup_base = y_topo - viga_h + cobr

    if sentido == "DIREITA":
        p2x = x0 + (n_deg - 1) * piso
        p2y = y0 + (n_deg - 1) * espelho
        ref_x = p2x + cobr * sin_a
        ref_y = p2y - cobr * cos_a

        x_kink = ref_x + (y_fundo_pat_cheg - ref_y) / math.tan(ang)
        y_kink = y_fundo_pat_cheg

        pt1_x = x_kink - comp_anc * cos_a
        pt1_y = y_kink - comp_anc * sin_a
        pt2_x = x_kink
        pt2_y = y_kink

        x_viga_sup = x_topo + pat_cheg + viga_l - cobr
        pt3_x = x_viga_sup
        pt3_y = y_fundo_pat_cheg
        pt4_x = x_viga_sup
        pt4_y = y_gancho_sup_base

        pontos_ferro_n2 = [
            (pt1_x, pt1_y),
            (pt2_x, pt2_y),
            (pt3_x, pt3_y),
            (pt4_x, pt4_y)
        ]
    else:  # Subindo para a ESQUERDA
        ref_x = x_topo + cobr * sin_a
        ref_y = (y_topo - espelho) - cobr * cos_a

        # Intersecao com cota do fundo do patamar superior
        x_kink = ref_x - (y_fundo_pat_cheg - ref_y) / math.tan(ang)
        y_kink = y_fundo_pat_cheg

        pt1_x = x_kink + comp_anc * cos_a
        pt1_y = y_kink - comp_anc * sin_a
        pt2_x = x_kink
        pt2_y = y_kink

        x_viga_cheg = (x_topo - pat_cheg - viga_l) + cobr
        pt3_x = x_viga_cheg
        pt3_y = y_fundo_pat_cheg
        pt4_x = x_viga_cheg
        pt4_y = y_gancho_sup_base

        pontos_ferro_n2 = [
            (pt1_x, pt1_y),
            (pt2_x, pt2_y),
            (pt3_x, pt3_y),
            (pt4_x, pt4_y)
        ]

    try:
        rebar2 = TQSDwg.SmartRebar(dwg)
        rebar2.type = TQSDwg.ICPFGN
        rebar2.diameter = bitola
        rebar2.spacing = espac
        rebar2.quantity = qtd
        try:
            if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                f_mark = dwg.globalrebar.FreeMark()
                rebar2.mark = f_mark if f_mark > 0 else 2
            else:
                rebar2.mark = 2
        except:
            rebar2.mark = 2

        for px, py in pontos_ferro_n2:
            rebar2.GenRebarPoint(px, py, 0.0, 0, 1, -1)

        # Inserir no Nivel 220, Cor por nivel (-1), Estilo por nivel (-1)
        rebar2.RebarLine(0.0, 0.0, 0.0, 1.0, 0, 0, 0, 0, 220, -1, -1)
        is_dois_lances = (geo.get("num_lances", 1) >= 2) or (sentido == "ESQUERDA")
        dx_rebatido = 220.0 if is_dois_lances else 0.0
        dy_rebatido = -330.0 if is_dois_lances else -160.0
        rebar2.RebarLine(dx_rebatido, dy_rebatido, 0.0, 1.0, 1, 1, 0, 0, 220, -1, -1)

    except Exception as e:
        TQSUtil.writef("Erro ao gerar SmartRebar N2: %s" % str(e))


def desenhar_ferro_bordo_patamar(dwg, geo, dados_ferros):
    """Calcula e desenha o ferro em L de reforco do bordo do patamar superior (N3)."""
    sentido = geo.get("sentido", "DIREITA")
    x0 = geo["x0"]
    y0 = geo["y0"]
    n_deg = geo["n_degraus"]
    piso = geo["piso"]
    espelho = geo["espelho"]
    pat_cheg = geo["patamar_chegada"]
    espessura = geo["espessura"]
    viga_l = geo["viga_largura"]
    viga_h = geo["viga_altura"]
    x_topo = geo["x_topo"]
    y_topo = geo["y_topo"]

    cobr = float(dados_ferros.get("cobrimento_planta", dados_ferros.get("cobrimento", 2.5)))
    bitola = float(dados_ferros["bitola"])
    espac = float(dados_ferros["espacamento"])
    qtd = int(dados_ferros["quantidade"])

    dist_fundo = espessura - cobr
    l_horiz = 60.0
    if pat_cheg > 0:
        l_horiz = min(pat_cheg - viga_l - cobr, 60.0)
        if l_horiz < 30.0:
            l_horiz = max(30.0, pat_cheg * 0.5)

    y_topo_arm = y_topo - cobr

    if sentido == "DIREITA":
        p1x, p1y = x0 + piso, y0 + espelho
        p2x, p2y = x0 + (n_deg - 1) * piso, y0 + (n_deg - 1) * espelho
        f_x1, f_y1, f_x2, f_y2 = obter_fundo_lance(p1x, p1y, p2x, p2y, dist_fundo)

        x_corner = x_topo + cobr
        if abs(f_x2 - f_x1) > 1e-9:
            t = (x_corner - f_x1) / (f_x2 - f_x1)
            y_bottom = f_y1 + t * (f_y2 - f_y1)
        else:
            y_bottom = y_topo_arm - 25.0

        pt1 = (x_corner, y_bottom)
        pt2 = (x_corner, y_topo_arm)
        pt3 = (x_corner + l_horiz, y_topo_arm)
        pontos_ferro_n3 = [pt1, pt2, pt3]
    else:  # Subindo para a ESQUERDA
        x_corner = x_topo - cobr
        y_bottom = y_topo_arm - 25.0

        pt1 = (x_corner, y_bottom)
        pt2 = (x_corner, y_topo_arm)
        pt3 = (x_corner - l_horiz, y_topo_arm)
        pontos_ferro_n3 = [pt1, pt2, pt3]

    try:
        rebar3 = TQSDwg.SmartRebar(dwg)
        rebar3.type = TQSDwg.ICPFGN
        rebar3.diameter = bitola
        rebar3.spacing = espac
        rebar3.quantity = qtd
        try:
            if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                f_mark = dwg.globalrebar.FreeMark()
                rebar3.mark = f_mark if f_mark > 0 else 3
            else:
                rebar3.mark = 3
        except:
            rebar3.mark = 3

        for px, py in pontos_ferro_n3:
            rebar3.GenRebarPoint(px, py, 0.0, 0, 1, -1)

        # Inserir no Nivel 220, Cor por nivel (-1), Estilo por nivel (-1)
        rebar3.RebarLine(0.0, 0.0, 0.0, 1.0, 0, 0, 0, 0, 220, -1, -1)
        is_dois_lances = (geo.get("num_lances", 1) >= 2) or (sentido == "ESQUERDA")
        dx_rebatido = 220.0 if is_dois_lances else 0.0
        dy_rebatido = -370.0 if is_dois_lances else -200.0
        rebar3.RebarLine(dx_rebatido, dy_rebatido, 0.0, 1.0, 1, 1, 0, 0, 220, -1, -1)

    except Exception as e:
        TQSUtil.writef("Erro ao gerar SmartRebar N3: %s" % str(e))


def desenhar_armadura_distribuicao(dwg, geo, dados_ferros):
    """Calcula e desenha as barras de distribuicao em corte ao longo dos ferros longitudinais."""
    sentido = geo.get("sentido", "DIREITA")
    x0 = geo["x0"]
    y0 = geo["y0"]
    n_deg = geo["n_degraus"]
    piso = geo["piso"]
    espelho = geo["espelho"]
    pat_part = geo["patamar_partida"]
    pat_cheg = geo["patamar_chegada"]
    espessura = geo["espessura"]
    viga_l = geo["viga_largura"]
    viga_h = geo["viga_altura"]
    x_topo = geo["x_topo"]
    y_topo = geo["y_topo"]

    cobr = float(dados_ferros.get("cobrimento_planta", dados_ferros.get("cobrimento", 2.5)))
    bitola_dist = 5.0
    espac_dist = float(dados_ferros.get("espac_dist", 15.0))
    if espac_dist <= 0:
        espac_dist = 15.0

    ang = math.atan2(espelho, piso)
    cos_a = math.cos(ang)
    sin_a = math.sin(ang)
    ux = cos_a if sentido == "DIREITA" else -cos_a
    uy = sin_a
    nx = -sin_a if sentido == "DIREITA" else -sin_a
    ny = cos_a

    dist_fundo = espessura - cobr
    y_topo_arm = y_topo - cobr
    y_fundo_pat_cheg = y_topo - espessura + cobr

    pontos_circulos = []
    r_circ = 1.0

    def adicionar_bolinha(cx, cy, d_min=5.5):
        for ex, ey in pontos_circulos:
            if math.hypot(cx - ex, cy - ey) < d_min:
                return False
        pontos_circulos.append((cx, cy))
        return True

    if sentido == "DIREITA":
        p1x, p1y = x0 + piso, y0 + espelho
        p2x, p2y = x0 + (n_deg - 1) * piso, y0 + (n_deg - 1) * espelho
        f_x1, f_y1, f_x2, f_y2 = obter_fundo_lance(p1x, p1y, p2x, p2y, dist_fundo)

        if pat_part >= 40.0:
            p_base_x = calcular_x_no_y(f_x1, f_y1, f_x2, f_y2, y0 - espessura + cobr)
            y_fundo_pat_part = y0 - espessura + cobr
            cy_part = y_fundo_pat_part + r_circ

            x = (x0 - pat_part) + espac_dist
            while x <= p_base_x - 2.0:
                adicionar_bolinha(x, cy_part)
                x += espac_dist
        else:
            p_base_x = x0

        x_corner = x_topo + cobr
        y_fundo_lance = calcular_y_no_x(f_x1, f_y1, f_x2, f_y2, x_corner)
        y_top_c = y_topo_arm - r_circ
        y_bot_c = y_fundo_lance + r_circ

        if y_top_c > y_bot_c + 10.0:
            dy_vert = (y_top_c - y_bot_c) / 3.0
            for i in range(4):
                adicionar_bolinha(x_corner + r_circ, y_top_c - i * dy_vert)
        else:
            adicionar_bolinha(x_corner + r_circ, y_top_c)
            adicionar_bolinha(x_corner + r_circ, y_top_c - 7.5)
            adicionar_bolinha(x_corner + r_circ, y_top_c - 15.0)

        if pat_cheg >= 40.0:
            cy_top = y_topo_arm - r_circ
            cy_bot = y_fundo_pat_cheg + r_circ
            x_lim_cheg = (x_topo + pat_cheg) - 10.0

            x = x_corner + espac_dist
            while x <= x_lim_cheg:
                adicionar_bolinha(x, cy_top)
                adicionar_bolinha(x, cy_bot)
                x += espac_dist

        p_base_y = calcular_y_no_x(f_x1, f_y1, f_x2, f_y2, p_base_x)
        pt_topo_x = calcular_x_no_y(f_x1, f_y1, f_x2, f_y2, y_topo_arm)
        pt_topo_y = y_topo_arm
        l_flight = math.hypot(pt_topo_x - p_base_x, pt_topo_y - p_base_y)

        s = espac_dist
        while s <= l_flight - 2.0:
            bx = p_base_x + s * ux
            by = p_base_y + s * uy
            cx_inf = bx + r_circ * nx
            cy_inf = by + r_circ * ny
            adicionar_bolinha(cx_inf, cy_inf)
            s += espac_dist

        ref_x = p2x + cobr * sin_a
        ref_y = p2y - cobr * cos_a
        x_kink = ref_x + (y_fundo_pat_cheg - ref_y) / math.tan(ang)
        y_kink = y_fundo_pat_cheg

        comp_anc = min(140.0, max(90.0, 4.0 * math.hypot(piso, espelho)))
        pt1_x = x_kink - comp_anc * cos_a
        pt1_y = y_kink - comp_anc * sin_a

        s = espac_dist
        while s <= comp_anc - 3.0:
            x = pt1_x + s * cos_a
            y = pt1_y + s * sin_a
            cx_sup = x - r_circ * nx
            cy_sup = y - r_circ * ny
            adicionar_bolinha(cx_sup, cy_sup)
            s += espac_dist

    else:  # Subindo para a ESQUERDA
        fx_ref = (x0 - piso) - dist_fundo * sin_a
        fy_ref = (y0 + espelho) - dist_fundo * cos_a

        # Patamar de partida (a direita) - somente em cima do ferro no fundo
        if pat_part >= 40.0:
            y_fundo_pat_part = y0 - espessura + cobr
            cy_part = y_fundo_pat_part + r_circ
            x = x0 + espac_dist
            x_lim_part = (x0 + pat_part) - 10.0
            while x <= x_lim_part:
                adicionar_bolinha(x, cy_part)
                x += espac_dist

        # Patamar de chegada (a esquerda)
        if pat_cheg >= 40.0:
            cy_top = y_topo_arm - r_circ
            cy_bot = y_fundo_pat_cheg + r_circ
            x_lim_cheg = (x_topo - pat_cheg) + 10.0
            x = x_topo - espac_dist
            while x >= x_lim_cheg:
                adicionar_bolinha(x, cy_top)
                adicionar_bolinha(x, cy_bot)
                x -= espac_dist

        # Lance inclinado (inferior / positivo) - Bolinhas em CIMA do ferro
        t_part = (y0 - espessura + cobr - fy_ref) / sin_a
        p_base_x = fx_ref - t_part * cos_a
        p_base_y = y0 - espessura + cobr

        t_cheg = (y_topo_arm - fy_ref) / sin_a
        pt_topo_x = fx_ref - t_cheg * cos_a
        pt_topo_y = y_topo_arm

        l_flight = math.hypot(pt_topo_x - p_base_x, pt_topo_y - p_base_y)
        s = espac_dist
        while s <= l_flight - 2.0:
            bx = p_base_x + s * ux
            by = p_base_y + s * uy
            cx_inf = bx + r_circ * sin_a
            cy_inf = by + r_circ * cos_a
            adicionar_bolinha(cx_inf, cy_inf)
            s += espac_dist

        # Lance inclinado (superior / negativo) - Bolinhas por BAIXO do ferro negativo
        ref_x = x_topo + cobr * sin_a
        ref_y = (y_topo - espelho) - cobr * cos_a
        x_kink = ref_x - (y_fundo_pat_cheg - ref_y) / math.tan(ang)
        y_kink = y_fundo_pat_cheg

        comp_anc = min(140.0, max(90.0, 4.0 * math.hypot(piso, espelho)))
        s = espac_dist
        while s <= comp_anc - 3.0:
            x = x_kink + s * cos_a
            y = y_kink - s * sin_a
            cx_sup = x - r_circ * sin_a
            cy_sup = y - r_circ * cos_a
            adicionar_bolinha(cx_sup, cy_sup)
            s += espac_dist

    draw = dwg.draw
    draw.level = 220
    draw.color = 1   # Vermelho
    draw.style = 0

    for cx, cy in pontos_circulos:
        draw.Circle(cx, cy, r_circ)

    # ferro que nn sei para que serve
    # total_pontos = len(pontos_circulos)
    # if total_pontos > 0:
    # try:
    # rebar_dist = TQSDwg.SmartRebar(dwg)
    # rebar_dist.type = TQSDwg.ICPFRT
    # rebar_dist.diameter = bitola_dist
    # rebar_dist.spacing = espac_dist
    # rebar_dist.quantity = total_pontos
    # try:
    # if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
    # f_mark = dwg.globalrebar.FreeMark()
    # rebar_dist.mark = f_mark if f_mark > 0 else 4
    # else:
    # rebar_dist.mark = 4
    # except:
    # rebar_dist.mark = 4
    #     # rebar_dist.straightBarMainLength = 100.0
    # dy_rebatido = -(viga_h + 155.0)
    # rebar_dist.RebarLine(x0, dy_rebatido, 0.0, 1.0, 1, 1, 0, 0, 220, -1, -1)
    #     # except Exception as e:
    # TQSUtil.writef("Erro ao gerar SmartRebar Distribuicao: %s" % str(e))


# ==============================================================================
# FERROS DA PLANTA BAIXA DA ESCADA (REBARS INTELIGENTES REAIS)
# ==============================================================================

def desenhar_ferros_tracejados_planta(dwg, geo_planta, dados_ferros):
    """
    Calcula e gera as armaduras dos Patamares e Lances na Planta Baixa.
    Nivel 220, Cor Azul Claro/Ciano (cor = 4).
    - Patamar Esquerdo: gera os dois ferros com dobras viradas para fora.
    - Patamar Direito: gera os dois ferros retos.
    - Lances: gera os ferros dentro dos limites dos lances com cobrimento bilateral e posicoes nao-colineares.
    """
    lances = geo_planta.get("lances", [])
    if not lances:
        return

    cobr = float(dados_ferros.get("cobrimento_planta", dados_ferros.get("cobrimento", 2.5)))
    bitola = float(dados_ferros.get("bitola_planta", dados_ferros.get("bitola_tracejados", 8.0)))
    espac = float(dados_ferros.get("espacamento_planta", dados_ferros.get("espac_tracejados", 15.0)))
    if espac <= 0:
        espac = 15.0

    tem_dobra = int(dados_ferros.get("com_dobra_planta", 1)) == 1
    comp_dobra = float(dados_ferros.get("comp_dobra_planta", 15.0)) if tem_dobra else 0.0

    # Limites internos da laje (face interna das vigas superior e inferior)
    y_base_laje = min(l["y_base"] for l in lances)
    y_topo_laje = max(l["y_topo"] for l in lances)

    # Barras dos patamares contidas na laje (respeitando cobrimento das vigas superior e inferior)
    y_ini_total = y_base_laje + cobr
    y_fim_total = y_topo_laje - cobr
    largura_total = y_fim_total - y_ini_total

    # 1. Armaduras no Patamar Esquerdo (ferros com dobras viradas para fora: ___|    |___)
    pat_esq = geo_planta.get("patamar_esquerdo")
    if pat_esq and pat_esq.get("existe"):
        comp_pat = pat_esq["comprimento"]
        qtd_esq = int(math.ceil(comp_pat / espac)) + 1
        
        x_p1 = pat_esq["x_min"] + comp_pat * 0.35
        x_p2 = pat_esq["x_min"] + comp_pat * 0.70

        # Barra 1 (esquerda): TRACEJADA com dobras apontando para a ESQUERDA (ipatas = 4)
        try:
            rebar_pat1 = TQSDwg.SmartRebar(dwg)
            rebar_pat1.type = TQSDwg.ICPFRT
            rebar_pat1.diameter = bitola
            rebar_pat1.spacing = espac
            rebar_pat1.quantity = qtd_esq
            try:
                if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                    f_mark = dwg.globalrebar.FreeMark()
                    rebar_pat1.mark = f_mark if f_mark > 0 else 15
                else:
                    rebar_pat1.mark = 15
            except:
                rebar_pat1.mark = 15

            rebar_pat1.straightBarMainLength = largura_total
            rebar_pat1.straightBarLeftLength = comp_dobra
            rebar_pat1.straightBarRightLength = comp_dobra

            ipatas_1 = 4 if tem_dobra else 0
            rebar_pat1.RebarLine(x_p1, y_ini_total, 90.0, 1.0, 1, 0, ipatas_1, 0, 220, 1, 4)
        except Exception as e:
            TQSUtil.writef("Erro ao gerar rebar patamar esquerdo 1: %s" % str(e))

        # Barra 2 (direita): CONTINUA com dobras apontando para a DIREITA (ipatas = 1)
        try:
            rebar_pat2 = TQSDwg.SmartRebar(dwg)
            rebar_pat2.type = TQSDwg.ICPFRT
            rebar_pat2.diameter = bitola
            rebar_pat2.spacing = espac
            rebar_pat2.quantity = qtd_esq
            try:
                if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                    f_mark = dwg.globalrebar.FreeMark()
                    rebar_pat2.mark = f_mark if f_mark > 0 else 16
                else:
                    rebar_pat2.mark = 16
            except:
                rebar_pat2.mark = 16

            rebar_pat2.straightBarMainLength = largura_total
            rebar_pat2.straightBarLeftLength = comp_dobra
            rebar_pat2.straightBarRightLength = comp_dobra

            ipatas_2 = 1 if tem_dobra else 0
            rebar_pat2.RebarLine(x_p2, y_ini_total, 90.0, 1.0, 1, 0, ipatas_2, 0, 220, 0, 4)
        except Exception as e:
            TQSUtil.writef("Erro ao gerar rebar patamar esquerdo 2: %s" % str(e))

    # 2. Armaduras no Patamar Direito (FERROS RETOS)
    pat_dir = geo_planta.get("patamar_direito")
    if pat_dir and pat_dir.get("existe"):
        comp_pat_d = pat_dir["comprimento"]
        qtd_dir = int(math.ceil(comp_pat_d / espac)) + 1
        
        x_pd1 = pat_dir["x_min"] + comp_pat_d * 0.35
        x_pd2 = pat_dir["x_min"] + comp_pat_d * 0.70

        # Barra 1 (reta): TRACEJADA
        try:
            rebar_pat_d1 = TQSDwg.SmartRebar(dwg)
            rebar_pat_d1.type = TQSDwg.ICPFRT
            rebar_pat_d1.diameter = bitola
            rebar_pat_d1.spacing = espac
            rebar_pat_d1.quantity = qtd_dir
            try:
                if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                    f_mark = dwg.globalrebar.FreeMark()
                    rebar_pat_d1.mark = f_mark if f_mark > 0 else 17
                else:
                    rebar_pat_d1.mark = 17
            except:
                rebar_pat_d1.mark = 17

            rebar_pat_d1.straightBarMainLength = largura_total
            rebar_pat_d1.straightBarLeftLength = 0.0
            rebar_pat_d1.straightBarRightLength = 0.0

            rebar_pat_d1.RebarLine(x_pd1, y_ini_total, 90.0, 1.0, 1, 0, 0, 0, 220, 1, 4)
        except Exception as e:
            TQSUtil.writef("Erro ao gerar rebar patamar direito 1: %s" % str(e))

        # Barra 2 (reta): CONTINUA / NORMAL
        try:
            rebar_pat_d2 = TQSDwg.SmartRebar(dwg)
            rebar_pat_d2.type = TQSDwg.ICPFRT
            rebar_pat_d2.diameter = bitola
            rebar_pat_d2.spacing = espac
            rebar_pat_d2.quantity = qtd_dir
            try:
                if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                    f_mark = dwg.globalrebar.FreeMark()
                    rebar_pat_d2.mark = f_mark if f_mark > 0 else 18
                else:
                    rebar_pat_d2.mark = 18
            except:
                rebar_pat_d2.mark = 18

            rebar_pat_d2.straightBarMainLength = largura_total
            rebar_pat_d2.straightBarLeftLength = 0.0
            rebar_pat_d2.straightBarRightLength = 0.0

            rebar_pat_d2.RebarLine(x_pd2, y_ini_total, 90.0, 1.0, 1, 0, 0, 0, 220, 0, 4)
        except Exception as e:
            TQSUtil.writef("Erro ao gerar rebar patamar direito 2: %s" % str(e))

    # 3. Armaduras nos Lances (Cobrimento bilateral total e Posicoes Nao-Colineares)
    espelho_padrao = float(dados_ferros.get("espelho_planta", 17.5))
    if espelho_padrao <= 0:
        espelho_padrao = 17.5

    for idx_l, l in enumerate(lances):
        if l.get("orientacao") == "VERTICAL":
            y_ini_l_raw = l.get("y_ini", 0.0)
            y_fim_l_raw = l.get("y_fim", 0.0)
            comp_horiz = abs(y_fim_l_raw - y_ini_l_raw)
        else:
            x_ini = l["x_ini"]
            x_fim = l["x_fim"]
            comp_horiz = abs(x_fim - x_ini)

        n_deg = l.get("n_degraus", 0)
        piso = l.get("piso", 28.0)
        if n_deg <= 0 and piso > 0:
            n_deg = int(round(comp_horiz / piso))

        n_espelhos = n_deg + 1 if n_deg > 0 else 1
        alt_vert = n_espelhos * espelho_padrao
        comp_inclinado = math.hypot(comp_horiz, alt_vert)

        # Quantidade de barras: n = ceil(L_inclinado / espac) + 1
        qtd_lance = int(math.ceil(comp_inclinado / espac)) + 1

        # Cobrimento rigoroso em ambas as pontas (fica fora da viga e fora da parede/vao central)
        y_ini_l = l["y_base"] + cobr
        y_fim_l = l["y_topo"] - cobr
        largura_l = y_fim_l - y_ini_l

        # POSICIONAMENTO X DESFASADO (NUNCA COLINEAR ENTRE OS LANCES)
        deg_coords = l.get("degraus_coords", [])
        n_pts_deg = len(deg_coords)
        
        if n_pts_deg >= 5:
            if idx_l == 0:
                # Lance 1 (Inferior): posicionado no 3º degrau (mais à esquerda)
                x_bar = (deg_coords[1] + deg_coords[2]) / 2.0
            elif idx_l == 1:
                # Lance 2 (Superior): posicionado no 5º ou 6º degrau (mais à direita, não-colinear)
                pos_deg = min(5, n_pts_deg - 2)
                x_bar = (deg_coords[pos_deg] + deg_coords[pos_deg + 1]) / 2.0
            else:
                pos_deg = min(3, n_pts_deg - 2)
                x_bar = (deg_coords[pos_deg] + deg_coords[pos_deg + 1]) / 2.0
        elif n_pts_deg >= 2:
            offset_x = (idx_l * 25.0) - 12.5
            x_bar = (deg_coords[0] + deg_coords[-1]) / 2.0 + offset_x
        else:
            offset_x = (idx_l * 30.0) - 15.0
            x_bar = (x_ini + x_fim) / 2.0 + offset_x

        try:
            rebar_l = TQSDwg.SmartRebar(dwg)
            rebar_l.type = TQSDwg.ICPFRT
            rebar_l.diameter = bitola
            rebar_l.spacing = espac
            rebar_l.quantity = qtd_lance
            try:
                if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                    f_mark = dwg.globalrebar.FreeMark()
                    rebar_l.mark = f_mark if f_mark > 0 else 3
                else:
                    rebar_l.mark = 3
            except:
                rebar_l.mark = 3

            rebar_l.straightBarMainLength = largura_l
            rebar_l.straightBarLeftLength = 0.0
            rebar_l.straightBarRightLength = 0.0

            # Nivel 220, Estilo CONTINUO (iestilo = 0), Cor Azul Claro / Ciano (4)
            rebar_l.RebarLine(x_bar, y_ini_l, 90.0, 1.0, 1, 0, 0, 0, 220, 0, 4)
        except Exception:
            pass


def desenhar_todos_ferros_planta(dwg, geo_planta, dados_ferros):
    """Gera o conjunto de ferros inteligentes na Planta Baixa da escada."""
    try:
        dwg.draw.level = 220
    except:
        pass
    desenhar_ferros_tracejados_planta(dwg, geo_planta, dados_ferros)


# ==============================================================================
# FERROS DA ESCADA PLISSADA (ESTRIBOS INTELIGENTES DOS DEGRAUS)
# ==============================================================================
def desenhar_estribos_escada_plissada(dwg, geo, dados_ferros):
    """
    Gera as armaduras inteligentes de estribos em escada plissada (cascata/zigue-zague)
    utilizando o tipo nativo TQSDwg.ICPSTR (permite alterar o formato pelo duplo clique no EAG).
    - P7: Estribo de partida (base)
    - P8: Estribos fechados horizontais nos pisos
    - P9: Estribos fechados verticais nos espelhos
    - P10: Estribo fechado horizontal na chegada (topo)
    """
    try:
        dwg.draw.level = 220
        dwg.draw.style = 0
        dwg.draw.color = 4
    except:
        pass

    sentido = geo.get("sentido", "DIREITA")
    n_deg = geo["n_degraus"]
    piso = geo["piso"]
    espelho = geo["espelho"]
    steps = geo["steps"]
    x0 = geo["x0"]
    y0 = geo["y0"]
    x_topo = geo["x_topo"]
    y_topo = geo["y_topo"]

    bitola = float(dados_ferros.get("bitola_plissada", 8.0))
    espac = float(dados_ferros.get("espacamento_plissada", 15.0))
    mult = int(dados_ferros.get("multiplicador_plissada", 7))
    cobr = float(dados_ferros.get("cobrimento_plissada", 2.5))
    # transpasse e tals: definicao da espessura da laje e transpasse da escada plissada (padrao 15.0 cm)
    espessura = float(dados_ferros.get("espessura_plissada", geo.get("espessura", 15.0)))
    transp = float(dados_ferros.get("transpasse_plissada", 15.0))

    if espac <= 0:
        espac = 15.0
    if mult <= 0:
        mult = 7

    # Dimensoes das secoes de concreto para cada posicao (alinhamento exato na casca do degrau)
    # Piso: estribo horizontal com transpasse no nó vertical
    sec_w8 = round(piso + (transp if transp > 0 else espessura), 1)
    sec_h8 = round(espessura, 1)

    # Espelho: estribo vertical com ancoragem no degrau inferior
    sec_w9 = round(espessura, 1)
    sec_h9 = round(espelho + (transp if transp > 0 else espessura), 1)

    # Partida: estribo de arranque
    sec_w7 = round(espessura, 1)
    sec_h7 = round(espelho + (transp if transp > 0 else espessura), 1)

    # Chegada: estribo de ancoragem no patamar superior
    sec_w10 = round(45.0 + 2.0 * cobr, 1)
    sec_h10 = round(espessura, 1)

    # --------------------------------------------------------------------------
    # 1. ESTRIBO DE PISO / HORIZONTAL (P8)
    # --------------------------------------------------------------------------
    qtd_p8 = max(1, n_deg - 1) * mult
    try:
        rebar8 = TQSDwg.SmartRebar(dwg)
        rebar8.type = TQSDwg.ICPSTR
        rebar8.diameter = bitola
        rebar8.spacing = espac
        rebar8.quantity = qtd_p8
        rebar8.cover = cobr
        rebar8.stirrupType = TQSDwg.ICPEFC
        rebar8.stirrupLegs = TQSDwg.ICPNR2
        rebar8.stirrupSectionWidth = sec_w8
        rebar8.stirrupSectionHeight = sec_h8
        rebar8.stirrupHookType = TQSDwg.ICPTPPATA45
        rebar8.stirrupHookLength = 8

        try:
            if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                f_mark = dwg.globalrebar.FreeMark()
                rebar8.mark = f_mark if f_mark > 0 else 8
            else:
                rebar8.mark = 8
        except:
            rebar8.mark = 8

        # Inserir linhas nos degraus reais (Nivel 220, Estilo Continuo 0, Cor Azul/Ciano 4)
        for s in steps[:-1]:
            if sentido == "DIREITA":
                x_ins = s['x_riser']
                y_ins = s['y_riser_top'] - sec_h8
            else:
                x_ins = s['x_riser'] - sec_w8
                y_ins = s['y_riser_top'] - sec_h8
            rebar8.RebarLine(x_ins, y_ins, 0.0, 1.0, 0, 0, 0, 0, 220, 0, 4)

        # Rebatido detalhado com identificacao e cotas (Piso: coluna direita, embaixo)
        x_reb8 = x0 + 130.0 if sentido == "DIREITA" else x0 - 130.0
        y_reb8 = y0 - 85.0
        rebar8.RebarLine(x_reb8, y_reb8, 0.0, 1.0, 1, 1, 1, 0, 220, -1, -1)
    except Exception as e:
        TQSUtil.writef("Erro ao gerar estribo P8: %s" % str(e))

    # --------------------------------------------------------------------------
    # 2. ESTRIBO DE ESPELHO / VERTICAL (P9)
    # --------------------------------------------------------------------------
    qtd_p9 = max(1, n_deg - 1) * mult
    try:
        rebar9 = TQSDwg.SmartRebar(dwg)
        rebar9.type = TQSDwg.ICPSTR
        rebar9.diameter = bitola
        rebar9.spacing = espac
        rebar9.quantity = qtd_p9
        rebar9.cover = cobr
        rebar9.stirrupType = TQSDwg.ICPEFC
        rebar9.stirrupLegs = TQSDwg.ICPNR2
        rebar9.stirrupSectionWidth = sec_w9
        rebar9.stirrupSectionHeight = sec_h9
        rebar9.stirrupHookType = TQSDwg.ICPTPPATA45
        rebar9.stirrupHookLength = 8

        try:
            if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                f_mark = dwg.globalrebar.FreeMark()
                rebar9.mark = f_mark if f_mark > 0 else 9
            else:
                rebar9.mark = 9
        except:
            rebar9.mark = 9

        # Inserir linhas nos espelhos reais (Nivel 220, Estilo Continuo 0, Cor Azul/Ciano 4)
        for s in steps[1:]:
            if sentido == "DIREITA":
                x_ins = s['x_riser']
                y_ins = s['y_riser_top'] - sec_h9
            else:
                x_ins = s['x_riser'] - sec_w9
                y_ins = s['y_riser_top'] - sec_h9
            rebar9.RebarLine(x_ins, y_ins, 0.0, 1.0, 0, 0, 0, 0, 220, 0, 4)

        # Rebatido detalhado com identificacao e cotas (Espelho: coluna direita, meio)
        x_reb9 = x0 + 140.0 if sentido == "DIREITA" else x0 - 140.0
        y_reb9 = y0 - 35.0
        rebar9.RebarLine(x_reb9, y_reb9, 0.0, 1.0, 1, 1, 1, 0, 220, -1, -1)
    except Exception as e:
        TQSUtil.writef("Erro ao gerar estribo P9: %s" % str(e))

    # --------------------------------------------------------------------------
    # 3. ESTRIBO DE PARTIDA / GANCHO EM U (P7)
    # --------------------------------------------------------------------------
    qtd_p7 = 3 * mult
    try:
        rebar7 = TQSDwg.SmartRebar(dwg)
        rebar7.type = TQSDwg.ICPSTR
        rebar7.diameter = bitola
        rebar7.spacing = espac
        rebar7.quantity = qtd_p7
        rebar7.cover = cobr
        rebar7.stirrupType = TQSDwg.ICPEFC
        rebar7.stirrupLegs = TQSDwg.ICPNR2
        rebar7.stirrupSectionWidth = sec_w7
        rebar7.stirrupSectionHeight = sec_h7
        rebar7.stirrupHookType = TQSDwg.ICPTPPATA45
        rebar7.stirrupHookLength = 8

        try:
            if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                f_mark = dwg.globalrebar.FreeMark()
                rebar7.mark = f_mark if f_mark > 0 else 7
            else:
                rebar7.mark = 7
        except:
            rebar7.mark = 7

        # Inserir linha na partida (Nivel 220, Estilo Continuo 0, Cor Azul/Ciano 4)
        if steps:
            s0 = steps[0]
            if sentido == "DIREITA":
                x_ins = s0['x_riser']
                y_ins = s0['y_riser_bot'] - sec_h7 + s0['altura_riser']
            else:
                x_ins = s0['x_riser'] - sec_w7
                y_ins = s0['y_riser_bot'] - sec_h7 + s0['altura_riser']
            rebar7.RebarLine(x_ins, y_ins, 0.0, 1.0, 0, 0, 0, 0, 220, 0, 4)

        # Rebatido detalhado com identificacao e cotas (Partida: coluna esquerda)
        x_reb7 = x0 + 60.0 if sentido == "DIREITA" else x0 - 60.0
        y_reb7 = y0 - 55.0
        rebar7.RebarLine(x_reb7, y_reb7, 0.0, 1.0, 1, 1, 1, 0, 220, -1, -1)
    except Exception as e:
        TQSUtil.writef("Erro ao gerar estribo P7: %s" % str(e))

    # --------------------------------------------------------------------------
    # 4. ESTRIBO DE CHEGADA / TOPO (P10)
    # --------------------------------------------------------------------------
    qtd_p10 = 4 * mult
    try:
        rebar10 = TQSDwg.SmartRebar(dwg)
        rebar10.type = TQSDwg.ICPSTR
        rebar10.diameter = bitola
        rebar10.spacing = espac
        rebar10.quantity = qtd_p10
        rebar10.cover = cobr
        rebar10.stirrupType = TQSDwg.ICPEFC
        rebar10.stirrupLegs = TQSDwg.ICPNR2
        rebar10.stirrupSectionWidth = sec_w10
        rebar10.stirrupSectionHeight = sec_h10
        rebar10.stirrupHookType = TQSDwg.ICPTPPATA45
        rebar10.stirrupHookLength = 8

        try:
            if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                f_mark = dwg.globalrebar.FreeMark()
                rebar10.mark = f_mark if f_mark > 0 else 10
            else:
                rebar10.mark = 10
        except:
            rebar10.mark = 10

        # Inserir linha na chegada (Nivel 220, Estilo Continuo 0, Cor Azul/Ciano 4)
        if steps:
            s_top = steps[-1]
            if sentido == "DIREITA":
                x_ins = s_top['x_riser']
                y_ins = s_top['y_riser_top'] - sec_h10
            else:
                x_ins = s_top['x_riser'] - sec_w10
                y_ins = s_top['y_riser_top'] - sec_h10
            rebar10.RebarLine(x_ins, y_ins, 0.0, 1.0, 0, 0, 0, 0, 220, 0, 4)

        # Rebatido detalhado com identificacao e cotas (Chegada: coluna direita, topo acima do P9)
        x_reb10 = x0 + 140.0 if sentido == "DIREITA" else x0 - 140.0
        y_reb10 = y0 + 20.0
        rebar10.RebarLine(x_reb10, y_reb10, 0.0, 1.0, 1, 1, 1, 0, 220, -1, -1)
    except Exception as e:
        TQSUtil.writef("Erro ao gerar estribo P10: %s" % str(e))


def desenhar_distribuicao_escada_plissada(dwg, geo, dados_ferros):
    """
    Desenha as armaduras de distribuicao (bolinhas vermelhas em corte) da escada plissada:
    1. 4 bolinhas nos nos quadrados de uniao dos estribos (cantos de cada degrau, partida e chegada).
    2. Bolinhas no ponto medio superior e inferior de cada estribo horizontal (pisos e chegada).
    """
    sentido = geo.get("sentido", "DIREITA")
    steps = geo.get("steps", [])
    if not steps:
        return

    piso = geo["piso"]
    espelho = geo["espelho"]

    cobr = float(dados_ferros.get("cobrimento_plissada", 2.5))
    espessura = float(dados_ferros.get("espessura_plissada", geo.get("espessura", 15.0)))
    transp = float(dados_ferros.get("transpasse_plissada", 15.0))

    sec_w8 = round(piso + (transp if transp > 0 else espessura), 1)
    sec_w10 = round(45.0 + 2.0 * cobr, 1)

    r_circ = 1.0
    pontos_circulos = []

    def adicionar_bolinha(cx, cy, d_min=2.0):
        for ex, ey in pontos_circulos:
            if math.hypot(cx - ex, cy - ey) < d_min:
                return False
        pontos_circulos.append((cx, cy))
        return True

    def adicionar_quadrado(x1, y1, x2, y2):
        xmin = min(x1, x2)
        xmax = max(x1, x2)
        ymin = min(y1, y2)
        ymax = max(y1, y2)
        adicionar_bolinha(xmin + cobr + r_circ, ymax - cobr - r_circ)
        adicionar_bolinha(xmax - cobr - r_circ, ymax - cobr - r_circ)
        adicionar_bolinha(xmin + cobr + r_circ, ymin + cobr + r_circ)
        adicionar_bolinha(xmax - cobr - r_circ, ymin + cobr + r_circ)

    if sentido == "DIREITA":
        # 1. Nos e pontos medios de cada degrau (P8 e P9)
        for i, s in enumerate(steps[:-1]):
            x_r = s['x_riser']
            y_top = s['y_riser_top']
            s_next = steps[i + 1]
            x_next = s_next['x_riser']

            # No do canto superior (uniao do espelho com o piso)
            adicionar_quadrado(x_r, y_top - espessura, x_r + espessura, y_top)

            # Ponto medio do estribo horizontal (em cima e em baixo)
            x_mid = x_r + sec_w8 / 2.0
            y_top_bar = y_top - cobr - r_circ
            y_bot_bar = y_top - espessura + cobr + r_circ
            adicionar_bolinha(x_mid, y_top_bar)
            adicionar_bolinha(x_mid, y_bot_bar)

            # No do canto reentrante (uniao do piso com o proximo espelho)
            adicionar_quadrado(x_next, y_top - espessura, x_next + espessura, y_top)

        # 2. Chegada / Topo (P10)
        s_top = steps[-1]
        x_top_r = s_top['x_riser']
        y_top_val = s_top['y_riser_top']
        # No da chegada com o ultimo espelho
        adicionar_quadrado(x_top_r, y_top_val - espessura, x_top_r + espessura, y_top_val)

        # Ponto medio do estribo horizontal de chegada P10
        x_mid10 = x_top_r + sec_w10 / 2.0
        y_top_bar10 = y_top_val - cobr - r_circ
        y_bot_bar10 = y_top_val - espessura + cobr + r_circ
        adicionar_bolinha(x_mid10, y_top_bar10)
        adicionar_bolinha(x_mid10, y_bot_bar10)

        # Extremidade direita do P10
        x_end10 = x_top_r + sec_w10 - cobr - r_circ
        adicionar_bolinha(x_end10, y_top_bar10)
        adicionar_bolinha(x_end10, y_bot_bar10)

    else:  # Subindo para a ESQUERDA
        # 1. Nos e pontos medios de cada degrau (P8 e P9)
        for i, s in enumerate(steps[:-1]):
            x_r = s['x_riser']
            y_top = s['y_riser_top']
            s_next = steps[i + 1]
            x_next = s_next['x_riser']

            # No do canto superior
            adicionar_quadrado(x_r - espessura, y_top - espessura, x_r, y_top)

            # Ponto medio do estribo horizontal
            x_mid = x_r - sec_w8 / 2.0
            y_top_bar = y_top - cobr - r_circ
            y_bot_bar = y_top - espessura + cobr + r_circ
            adicionar_bolinha(x_mid, y_top_bar)
            adicionar_bolinha(x_mid, y_bot_bar)

            # No do canto reentrante
            adicionar_quadrado(x_next - espessura, y_top - espessura, x_next, y_top)

        # 3. Chegada / Topo (P10)
        s_top = steps[-1]
        x_top_r = s_top['x_riser']
        y_top_val = s_top['y_riser_top']
        adicionar_quadrado(x_top_r - espessura, y_top_val - espessura, x_top_r, y_top_val)

        x_mid10 = x_top_r - sec_w10 / 2.0
        y_top_bar10 = y_top_val - cobr - r_circ
        y_bot_bar10 = y_top_val - espessura + cobr + r_circ
        adicionar_bolinha(x_mid10, y_top_bar10)
        adicionar_bolinha(x_mid10, y_bot_bar10)

        x_end10 = x_top_r - sec_w10 + cobr + r_circ
        adicionar_bolinha(x_end10, y_top_bar10)
        adicionar_bolinha(x_end10, y_bot_bar10)

    # Desenhar circulos vermelhos no nivel 220
    try:
        draw = dwg.draw
        draw.level = 220
        draw.color = 1   # Vermelho
        draw.style = 0

        for cx, cy in pontos_circulos:
            draw.Circle(cx, cy, r_circ)
    except Exception as e:
        TQSUtil.writef("Erro ao desenhar distribuicao plissada: %s" % str(e))


# ==============================================================================
# COMANDO PRINCIPAL UNIFICADO ACIONADO PELO MENU TQS ("2. Armar Escada")
# ==============================================================================
def meucmd(eag, tqsjan):
    """Funcao chamada pelo botao 'Armar Escada' no menu do TQS."""
    dados_ferros = pedir_dados_armacao()
    if dados_ferros is None:
        return

    modo = dados_ferros.get("modo", "CORTE")

    # ==========================================================================
    # FLUXO 1: SE O USUARIO CLICOU EM "ARMAR CORTE / ESCADA"
    # ==========================================================================
    if modo == "CORTE":
        addr, xs, ys, np, istat = eag.locate.Select(tqsjan, "Abra uma janela sobre o corte da escada", TQSEag.EAG_IJANEL)
        if istat != 0:
            return

        linhas = []
        eag.locate.BeginSelection(tqsjan)
        while True:
            h_elem = eag.locate.NextSelection(tqsjan)
            if h_elem is None:
                break
            tqsjan.dwg.iterator.SetPosition(h_elem)
            itipo = tqsjan.dwg.iterator.Next()
            if itipo == TQSDwg.DWGTYPE_LINE:
                x1 = tqsjan.dwg.iterator.x1
                y1 = tqsjan.dwg.iterator.y1
                x2 = tqsjan.dwg.iterator.x2
                y2 = tqsjan.dwg.iterator.y2
                linhas.append(((x1, y1), (x2, y2)))
            elif itipo == TQSDwg.DWGTYPE_POLYLINE:
                try:
                    npts = tqsjan.dwg.iterator.xySize
                    pts = [tqsjan.dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    for i in range(len(pts) - 1):
                        linhas.append(((pts[i][0], pts[i][1]), (pts[i+1][0], pts[i+1][1])))
                except Exception:
                    pass

        if not linhas:
            return

        geo_perfil = identificar_geometria_escada(linhas)
        if geo_perfil is None:
            return

        desenhar_ferro_principal_maior(tqsjan.dwg, geo_perfil, dados_ferros)
        desenhar_ferro_no_superior(tqsjan.dwg, geo_perfil, dados_ferros)
        desenhar_ferro_bordo_patamar(tqsjan.dwg, geo_perfil, dados_ferros)
        desenhar_armadura_distribuicao(tqsjan.dwg, geo_perfil, dados_ferros)
        tqsjan.Regen()
        return

    # ==========================================================================
    # FLUXO 2: SE O USUARIO CLICOU EM "ARMAR PLANTA BAIXA"
    # ==========================================================================
    elif modo == "PLANTA":
        addr, xs, ys, np, istat = eag.locate.Select(tqsjan, "Abra uma janela sobre a planta baixa da escada", TQSEag.EAG_IJANEL)
        if istat != 0:
            return

        linhas = []
        textos = []
        eag.locate.BeginSelection(tqsjan)
        while True:
            h_elem = eag.locate.NextSelection(tqsjan)
            if h_elem is None:
                break
            tqsjan.dwg.iterator.SetPosition(h_elem)
            itipo = tqsjan.dwg.iterator.Next()
            if itipo == TQSDwg.DWGTYPE_LINE:
                x1 = tqsjan.dwg.iterator.x1
                y1 = tqsjan.dwg.iterator.y1
                x2 = tqsjan.dwg.iterator.x2
                y2 = tqsjan.dwg.iterator.y2
                linhas.append(((x1, y1), (x2, y2)))
            elif itipo == TQSDwg.DWGTYPE_POLYLINE:
                try:
                    npts = tqsjan.dwg.iterator.xySize
                    pts = [tqsjan.dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    for i in range(len(pts) - 1):
                        linhas.append(((pts[i][0], pts[i][1]), (pts[i+1][0], pts[i+1][1])))
                except Exception:
                    pass
            elif itipo == TQSDwg.DWGTYPE_TEXT:
                try:
                    xt = tqsjan.dwg.iterator.x1
                    yt = tqsjan.dwg.iterator.y1
                    txt = tqsjan.dwg.iterator.text
                    textos.append((xt, yt, txt))
                except Exception:
                    pass

        if not linhas:
            return

        geo_planta = identificar_geometria_planta_escada(linhas, textos)
        if geo_planta is None:
            return

        desenhar_todos_ferros_planta(tqsjan.dwg, geo_planta, dados_ferros)
        tqsjan.Regen()
        return

    # ==========================================================================
    # FLUXO 3: SE O USUARIO CLICOU EM "ARMAR ESCADA PLISSADA"
    # ==========================================================================
    elif modo == "PLISSADA":
        addr, xs, ys, np, istat = eag.locate.Select(tqsjan, "Abra uma janela sobre o corte da escada plissada", TQSEag.EAG_IJANEL)
        if istat != 0:
            return

        linhas = []
        eag.locate.BeginSelection(tqsjan)
        while True:
            h_elem = eag.locate.NextSelection(tqsjan)
            if h_elem is None:
                break
            tqsjan.dwg.iterator.SetPosition(h_elem)
            itipo = tqsjan.dwg.iterator.Next()
            if itipo == TQSDwg.DWGTYPE_LINE:
                x1 = tqsjan.dwg.iterator.x1
                y1 = tqsjan.dwg.iterator.y1
                x2 = tqsjan.dwg.iterator.x2
                y2 = tqsjan.dwg.iterator.y2
                linhas.append(((x1, y1), (x2, y2)))
            elif itipo == TQSDwg.DWGTYPE_POLYLINE:
                try:
                    npts = tqsjan.dwg.iterator.xySize
                    pts = [tqsjan.dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    for i in range(len(pts) - 1):
                        linhas.append(((pts[i][0], pts[i][1]), (pts[i+1][0], pts[i+1][1])))
                except Exception:
                    pass

        if not linhas:
            return

        geo_plissada = identificar_geometria_escada_plissada(linhas)
        if geo_plissada is None:
            return

        desenhar_estribos_escada_plissada(tqsjan.dwg, geo_plissada, dados_ferros)
        desenhar_distribuicao_escada_plissada(tqsjan.dwg, geo_plissada, dados_ferros)
        tqsjan.Regen()
        return

