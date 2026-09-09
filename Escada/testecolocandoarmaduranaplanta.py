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
        </style>
        <script>
            window.resizeTo(470, 620);

            function setTab(tabName) {{
                document.getElementById('tabCorte').className = (tabName == 'corte') ? 'tab active' : 'tab';
                document.getElementById('tabPlanta').className = (tabName == 'planta') ? 'tab active' : 'tab';
                document.getElementById('contentCorte').className = (tabName == 'corte') ? 'tab-content active' : 'tab-content';
                document.getElementById('contentPlanta').className = (tabName == 'planta') ? 'tab-content active' : 'tab-content';
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

                        // Planta Baixa - Ligacao Alvenaria (P2)
                        "bitola_lig_alv": parseFloat(document.getElementById('bitola_lig_alv').value.replace(',', '.')),
                        "espac_lig_alv": parseFloat(document.getElementById('espac_lig_alv').value.replace(',', '.')),
                        "dobra_lance_alv": parseFloat(document.getElementById('dobra_lance_alv').value.replace(',', '.')),
                        "dobra_parede_alv": parseFloat(document.getElementById('dobra_parede_alv').value.replace(',', '.')),
                        "gancho_alv": parseFloat(document.getElementById('gancho_alv').value.replace(',', '.')),

                        // Planta Baixa - Longitudinal Alvenaria (P9)
                        "qtd_long_alv": parseInt(document.getElementById('qtd_long_alv').value),
                        "bitola_long_alv": parseFloat(document.getElementById('bitola_long_alv').value.replace(',', '.')),

                        // Planta Baixa - Ferros Tracejados
                        "bitola_tracejados": parseFloat(document.getElementById('bitola_tracejados').value.replace(',', '.')),
                        "espac_tracejados": parseFloat(document.getElementById('espac_tracejados').value.replace(',', '.'))
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
            <p>Plugin TQS &#9679 Escolha a opcao: Armar Corte ou Armar Planta</p>
        </div>

        <div class="container">
            <div class="tabs">
                <div id="tabCorte" class="tab active" onclick="setTab('corte')">1. Corte / Perfil</div>
                <div id="tabPlanta" class="tab" onclick="setTab('planta')">2. Planta Baixa</div>
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
                            <option value="10.0">10.0 mm</option>
                            <option value="12.5" selected>12.5 mm</option>
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
                    <h3>Ligacao Escada-Alvenaria (P2 - Continuo Azul)</h3>
                    <div class="campo">
                        <label>Bitola:</label>
                        <select id="bitola_lig_alv">
                            <option value="5.0">5.0 mm</option>
                            <option value="6.3">6.3 mm</option>
                            <option value="8.0" selected>8.0 mm</option>
                            <option value="10.0">10.0 mm</option>
                            <option value="12.5">12.5 mm</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label>Espacamento (cm):</label>
                        <input type="text" id="espac_lig_alv" value="15">
                    </div>
                    <div class="campo">
                        <label>Trecho no Lance (cm):</label>
                        <input type="text" id="dobra_lance_alv" value="50">
                    </div>
                    <div class="campo">
                        <label>Descida na Parede (cm):</label>
                        <input type="text" id="dobra_parede_alv" value="20">
                    </div>
                    <div class="campo">
                        <label>Gancho no Fundo (cm):</label>
                        <input type="text" id="gancho_alv" value="11">
                    </div>
                </div>

                <div class="card card-blue">
                    <h3>Longitudinal Alvenaria (P9 - Continuo Verde)</h3>
                    <div class="campo">
                        <label>Quantidade de Barras:</label>
                        <input type="text" id="qtd_long_alv" value="2">
                    </div>
                    <div class="campo">
                        <label>Bitola:</label>
                        <select id="bitola_long_alv">
                            <option value="5.0">5.0 mm</option>
                            <option value="6.3" selected>6.3 mm</option>
                            <option value="8.0">8.0 mm</option>
                            <option value="10.0">10.0 mm</option>
                        </select>
                    </div>
                </div>

                <div class="card card-blue">
                    <h3>Patamares e Lances (Tracejados Branco)</h3>
                    <div class="campo">
                        <label>Bitola Tracejados:</label>
                        <select id="bitola_tracejados">
                            <option value="5.0">5.0 mm</option>
                            <option value="6.3" selected>6.3 mm</option>
                            <option value="8.0">8.0 mm</option>
                            <option value="10.0">10.0 mm</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label>Espacamento (cm):</label>
                        <input type="text" id="espac_tracejados" value="15">
                    </div>
                </div>
            </div>

            <!-- DOIS BOTOES DE ACAO LADO A LADO -->
            <div class="btns">
                <button onclick="window.close()">Cancelar</button>
                <button class="btn-corte" onclick="confirmar('CORTE')">&#9658; Escada </button>
                <button class="btn-planta" onclick="confirmar('PLANTA')">&#9658; Planta Baixa</button>
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
# RECONHECIMENTO GEOMETRICO DO PERFIL DA ESCADA (CORTE)
# ==============================================================================
def identificar_geometria_escada(linhas):
    """Analisa as linhas selecionadas e deduz todas as dimensoes da escada em Perfil/Corte."""
    horizontais = []
    verticais = []
    inclinadas = []

    for (x1, y1), (x2, y2) in linhas:
        if abs(x1 - x2) < 0.1:  # Vertical
            verticais.append((x1, min(y1, y2), max(y1, y2), abs(y2 - y1)))
        elif abs(y1 - y2) < 0.1:  # Horizontal
            horizontais.append((min(x1, x2), max(x1, x2), y1, abs(x2 - x1)))
        else:
            inclinadas.append(((min(x1, x2), y1 if x1 < x2 else y2), (max(x1, x2), y2 if x1 < x2 else y1)))

    if not verticais or not horizontais:
        return None

    # Filtrar espelhos dos degraus (verticais com altura tipica de degrau: 14 a 22 cm)
    espelhos = [v for v in verticais if 14.0 <= v[3] <= 22.0]
    espelhos.sort(key=lambda v: (v[0], v[1]))

    if not espelhos:
        espelhos = [v for v in verticais if v[3] < 30.0]
        espelhos.sort(key=lambda v: (v[0], v[1]))

    if len(espelhos) < 2:
        return None

    # 1. Ponto Inicial (x0, y0)
    x0 = espelhos[0][0]
    y0 = espelhos[0][1]

    # 2. Numero de degraus
    n_degraus = len(espelhos)

    # 3. Piso e Espelho medios
    pisos_vals = []
    for i in range(len(espelhos) - 1):
        dx = espelhos[i+1][0] - espelhos[i][0]
        if dx > 5.0:
            pisos_vals.append(dx)

    piso = (sum(pisos_vals) / len(pisos_vals)) if pisos_vals else 28.0
    espelho = sum(e[3] for e in espelhos) / len(espelhos)

    # 4. Patamar de Partida (horizontal que termina em x0 no nivel y0)
    patamar_partida = 0.0
    for h in horizontais:
        if abs(h[1] - x0) < 0.5 and abs(h[2] - y0) < 0.5:
            if h[3] >= 40.0:
                patamar_partida = h[3]
            break

    # 5. Patamar de Chegada (horizontal que comeca no topo da escada)
    x_topo = espelhos[-1][0]
    y_topo = espelhos[-1][2]
    patamar_chegada = 0.0
    for h in horizontais:
        if abs(h[0] - x_topo) < 0.5 and abs(h[2] - y_topo) < 0.5:
            if h[3] >= 40.0:
                patamar_chegada = h[3]
            break

    # 6. Espessura da Laje (distancia da linha inclinada ao canto interno)
    espessura = 15.0
    linha_fundo_inc = None
    if inclinadas:
        inclinadas.sort(key=lambda seg: math.hypot(seg[1][0] - seg[0][0], seg[1][1] - seg[0][1]), reverse=True)
        linha_fundo_inc = inclinadas[0]
        canto_x = x0 + piso
        canto_y = y0 + espelho
        espessura = TQSGeo.DistancePointLine(linha_fundo_inc[0][0], linha_fundo_inc[0][1], linha_fundo_inc[1][0], linha_fundo_inc[1][1], canto_x, canto_y)

    # 7. Largura e Altura das Vigas de apoio
    viga_largura = 20.0
    viga_altura = 40.0

    # Viga de partida (face vertical mais a esquerda)
    x_lim_esq = x0 - patamar_partida
    vert_esq = [v for v in verticais if v[0] <= x_lim_esq + 0.1]
    if vert_esq:
        vert_esq.sort(key=lambda v: v[0])
        viga_largura = max(x_lim_esq - vert_esq[0][0], 20.0)
        viga_altura = max(vert_esq[0][3], 40.0)

    # Viga de chegada (face vertical mais a direita)
    x_lim_dir = x_topo + patamar_chegada
    vert_dir = [v for v in verticais if v[0] >= x_lim_dir - 0.1]
    if vert_dir:
        vert_dir.sort(key=lambda v: v[0], reverse=True)
        viga_largura = max(vert_dir[0][0] - x_lim_dir, 20.0)
        viga_altura = max(vert_dir[0][3], 40.0)

    return {
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

    # CASO 2: Se nao achou na horizontal, tentar orientacao VERTICAL (degraus horizontais com comp >= 45 cm)
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

    # Identificar Elemento Central (entre lances se houver 2 lances na horizontal)
    elemento_central = None
    if len(lances_identificados) == 2 and lances_identificados[0]['orientacao'] == 'HORIZONTAL':
        l1 = lances_identificados[0]  # inferior
        l2 = lances_identificados[1]  # superior
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

    # Identificar Patamares (se horizontal)
    patamar_esq = None
    patamar_dir = None
    if lances_identificados[0]['orientacao'] == 'HORIZONTAL':
        x_min_deg = min(l['x_ini'] for l in lances_identificados)
        x_max_deg = max(l['x_fim'] for l in lances_identificados)
        y_min_total = min(l['y_base'] for l in lances_identificados)
        y_max_total = max(l['y_topo'] for l in lances_identificados)
        
        vert_esq = [v for v in verticais if v[0] < x_min_deg - 5.0 and not (v[2] < y_min_total - 60.0 or v[1] > y_max_total + 60.0)]
        if vert_esq:
            vert_esq.sort(key=lambda v: v[0])
            x_pat_esq = vert_esq[0][0]
            comp_esq = x_min_deg - x_pat_esq
            if comp_esq >= 30.0:
                patamar_esq = {
                    'existe': True,
                    'comprimento': round(comp_esq, 1),
                    'x_min': round(x_pat_esq, 1),
                    'x_max': round(x_min_deg, 1)
                }

        vert_dir = [v for v in verticais if v[0] > x_max_deg + 5.0 and not (v[2] < y_min_total - 60.0 or v[1] > y_max_total + 60.0)]
        if vert_dir:
            vert_dir.sort(key=lambda v: v[0], reverse=True)
            x_pat_dir = vert_dir[0][0]
            comp_dir = x_pat_dir - x_max_deg
            if comp_dir >= 30.0:
                patamar_dir = {
                    'existe': True,
                    'comprimento': round(comp_dir, 1),
                    'x_min': round(x_max_deg, 1),
                    'x_max': round(x_pat_dir, 1)
                }

    sentido_geral = None
    for xt, yt, txt in textos:
        txt_u = txt.upper()
        if 'DESCE' in txt_u:
            sentido_geral = 'DESCE'
        elif 'SOBE' in txt_u:
            sentido_geral = 'SOBE'

    return {
        'tipo_vista': 'PLANTA_BAIXA',
        'orientacao': lances_identificados[0]['orientacao'],
        'num_lances': len(lances_identificados),
        'lances': lances_identificados,
        'elemento_central': elemento_central,
        'patamar_esquerdo': patamar_esq,
        'patamar_direito': patamar_dir,
        'sentido': sentido_geral,
        'textos': textos
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
    """Calcula e desenha o ferro positivo principal no corte."""
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

    cobr = float(dados_ferros.get("cobrimento", 2.5))
    bitola = float(dados_ferros["bitola"])
    espac = float(dados_ferros["espacamento"])
    qtd = int(dados_ferros["quantidade"])

    p1x, p1y = x0 + piso, y0 + espelho
    p2x, p2y = x0 + (n_deg - 1) * piso, y0 + (n_deg - 1) * espelho
    dist_fundo = espessura - cobr
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

        rebar.RebarLine(0.0, 0.0, 0.0, 1.0, 0, 0, 0, 0, 220, -1, 4)
        dy_rebatido = -(viga_h + 35.0)
        rebar.RebarLine(0.0, dy_rebatido, 0.0, 1.0, 1, 1, 0, 0, 220, -1, 4)

    except Exception as e:
        TQSUtil.writef("Erro ao gerar SmartRebar N1: %s" % str(e))


def desenhar_ferro_no_superior(dwg, geo, dados_ferros):
    """Calcula e desenha o ferro negativo do no superior / patamar de chegada (N2)."""
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

    cobr = float(dados_ferros.get("cobrimento", 2.5))
    bitola = float(dados_ferros["bitola"])
    espac = float(dados_ferros["espacamento"])
    qtd = int(dados_ferros["quantidade"])

    ang = math.atan2(espelho, piso)
    cos_a = math.cos(ang)
    sin_a = math.sin(ang)

    p2x = x0 + (n_deg - 1) * piso
    p2y = y0 + (n_deg - 1) * espelho

    ref_x = p2x + cobr * sin_a
    ref_y = p2y - cobr * cos_a

    y_fundo_pat_cheg = y_topo - espessura + cobr
    x_kink = ref_x + (y_fundo_pat_cheg - ref_y) / math.tan(ang)
    y_kink = y_fundo_pat_cheg

    passo_diag = math.hypot(piso, espelho)
    comp_anc = min(140.0, max(90.0, 4.0 * passo_diag))
    pt1_x = x_kink - comp_anc * cos_a
    pt1_y = y_kink - comp_anc * sin_a

    pt2_x = x_kink
    pt2_y = y_kink

    x_viga_sup = x_topo + pat_cheg + viga_l - cobr
    pt3_x = x_viga_sup
    pt3_y = y_fundo_pat_cheg

    y_gancho_sup_base = y_topo - viga_h + cobr
    pt4_x = x_viga_sup
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

        rebar2.RebarLine(0.0, 0.0, 0.0, 1.0, 0, 0, 0, 0, 220, -1, 4)
        dy_rebatido = -(viga_h + 75.0)
        rebar2.RebarLine(0.0, dy_rebatido, 0.0, 1.0, 1, 1, 0, 0, 220, -1, 4)

    except Exception as e:
        TQSUtil.writef("Erro ao gerar SmartRebar N2: %s" % str(e))


def desenhar_ferro_bordo_patamar(dwg, geo, dados_ferros):
    """Calcula e desenha o ferro em L de reforco do bordo do patamar superior (N3)."""
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

    cobr = float(dados_ferros.get("cobrimento", 2.5))
    bitola = float(dados_ferros["bitola"])
    espac = float(dados_ferros["espacamento"])
    qtd = int(dados_ferros["quantidade"])

    p1x, p1y = x0 + piso, y0 + espelho
    p2x, p2y = x0 + (n_deg - 1) * piso, y0 + (n_deg - 1) * espelho
    dist_fundo = espessura - cobr
    f_x1, f_y1, f_x2, f_y2 = obter_fundo_lance(p1x, p1y, p2x, p2y, dist_fundo)

    x_corner = x_topo + cobr
    y_topo_arm = y_topo - cobr

    if abs(f_x2 - f_x1) > 1e-9:
        t = (x_corner - f_x1) / (f_x2 - f_x1)
        y_bottom = f_y1 + t * (f_y2 - f_y1)
    else:
        y_bottom = y_topo_arm - 25.0

    l_horiz = 60.0
    if pat_cheg > 0:
        l_horiz = min(pat_cheg - viga_l - cobr, 60.0)
        if l_horiz < 30.0:
            l_horiz = max(30.0, pat_cheg * 0.5)

    pt1 = (x_corner, y_bottom)
    pt2 = (x_corner, y_topo_arm)
    pt3 = (x_corner + l_horiz, y_topo_arm)

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

        rebar3.RebarLine(0.0, 0.0, 0.0, 1.0, 0, 0, 0, 0, 220, -1, 4)
        dy_rebatido = -(viga_h + 115.0)
        rebar3.RebarLine(0.0, dy_rebatido, 0.0, 1.0, 1, 1, 0, 0, 220, -1, 4)

    except Exception as e:
        TQSUtil.writef("Erro ao gerar SmartRebar N3: %s" % str(e))


def desenhar_armadura_distribuicao(dwg, geo, dados_ferros):
    """Calcula e desenha as barras de distribuicao em corte ao longo dos ferros longitudinais."""
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

    cobr = float(dados_ferros.get("cobrimento", 2.5))
    bitola_dist = 5.0
    espac_dist = float(dados_ferros.get("espac_dist", 15.0))
    if espac_dist <= 0:
        espac_dist = 15.0

    ang = math.atan2(espelho, piso)
    cos_a = math.cos(ang)
    sin_a = math.sin(ang)
    ux, uy = cos_a, sin_a
    nx, ny = -sin_a, cos_a

    p1x, p1y = x0 + piso, y0 + espelho
    p2x, p2y = x0 + (n_deg - 1) * piso, y0 + (n_deg - 1) * espelho
    dist_fundo = espessura - cobr
    f_x1, f_y1, f_x2, f_y2 = obter_fundo_lance(p1x, p1y, p2x, p2y, dist_fundo)

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

    passo_diag = math.hypot(piso, espelho)
    comp_anc = min(140.0, max(90.0, 4.0 * passo_diag))
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

    draw = dwg.draw
    draw.level = 220
    draw.color = 1
    draw.style = 0

    for cx, cy in pontos_circulos:
        draw.Circle(cx, cy, r_circ)

    total_pontos = len(pontos_circulos)
    if total_pontos > 0:
        try:
            rebar_dist = TQSDwg.SmartRebar(dwg)
            rebar_dist.type = TQSDwg.ICPFRT
            rebar_dist.diameter = bitola_dist
            rebar_dist.spacing = espac_dist
            rebar_dist.quantity = total_pontos
            try:
                if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                    f_mark = dwg.globalrebar.FreeMark()
                    rebar_dist.mark = f_mark if f_mark > 0 else 4
                else:
                    rebar_dist.mark = 4
            except:
                rebar_dist.mark = 4

            rebar_dist.straightBarMainLength = 100.0
            dy_rebatido = -(viga_h + 155.0)
            rebar_dist.RebarLine(x0, dy_rebatido, 0.0, 1.0, 1, 1, 0, 0, 220, -1, 1)

        except Exception as e:
            TQSUtil.writef("Erro ao gerar SmartRebar Distribuicao: %s" % str(e))


# ==============================================================================
# FERROS DA PLANTA BAIXA DA ESCADA (REBARS INTELIGENTES REAIS)
# ==============================================================================

def desenhar_ferro_ligacao_alvenaria_planta(dwg, geo_planta, dados_ferros):
    """
    Calcula e gera o Ferro Inteligente de Ligacao com a Alvenaria (P2 - Gancho 50, 20, 11).
    LINHA CONTINUA (iestilo=0), COR AZUL (cor=5), COM FAIXA DE DISTRIBUICAO (17 BARRAS).
    """
    lances = geo_planta.get("lances", [])
    if not lances:
        return

    # Escolher o lance superior (ou o lance que tem a parede na base)
    lance_alvo = None
    for l in lances:
        if l.get("posicao") in ["SUPERIOR", "UNICO"]:
            lance_alvo = l
            break
    if lance_alvo is None:
        lance_alvo = lances[0]

    bitola = float(dados_ferros.get("bitola_lig_alv", 8.0))
    espac = float(dados_ferros.get("espac_lig_alv", 15.0))
    d_lance = float(dados_ferros.get("dobra_lance_alv", 50.0))
    d_parede = float(dados_ferros.get("dobra_parede_alv", 20.0))
    d_gancho = float(dados_ferros.get("gancho_alv", 11.0))

    x_ini = lance_alvo["x_ini"]
    x_fim = lance_alvo["x_fim"]
    y_base_lance = lance_alvo["y_base"]  # Face superior da parede de alvenaria

    # Calculo automatico da quantidade de ferros pela extensao da faixa: ceil(L/e) + 1
    comp_faixa = abs(x_fim - x_ini)
    qtd = int(math.ceil(comp_faixa / espac)) + 1

    # Ponto X intermediario no lance para desenhar a barra representativa (ex: degrau 5/6)
    degraus_x = lance_alvo.get("degraus_coords", [])
    if len(degraus_x) >= 5:
        x_bar = degraus_x[len(degraus_x) // 2 + 1]
    else:
        x_bar = (x_ini + x_fim) / 2.0

    # Vertices do ferro em formato gancho:
    p1 = (x_bar, y_base_lance + d_lance)
    p2 = (x_bar, y_base_lance)
    p3 = (x_bar, y_base_lance - d_parede)
    p4 = (x_bar - d_gancho, y_base_lance - d_parede)

    pontos_ferro = [p1, p2, p3, p4]

    try:
        rebar = TQSDwg.SmartRebar(dwg)
        rebar.type = TQSDwg.ICPFGN
        rebar.diameter = bitola
        rebar.spacing = espac
        rebar.quantity = qtd
        try:
            if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                f_mark = dwg.globalrebar.FreeMark()
                rebar.mark = f_mark if f_mark > 0 else 2
            else:
                rebar.mark = 2
        except:
            rebar.mark = 2

        for px, py in pontos_ferro:
            rebar.GenRebarPoint(px, py, 0.0, 0, 1, -1)

        # Inserir Linha do Ferro na Planta (Nivel 220, Linha Continua iestilo=0, Cor 5 - Azul)
        rebar.RebarLine(0.0, 0.0, 0.0, 1.0, 1, 1, 0, 0, 220, 0, 5)

        # Desenhar a Faixa de Distribuicao (Colchete Azul e Seta do Fluxo)
        draw = dwg.draw
        draw.level = 220
        draw.color = 5   # Azul
        draw.style = 0   # Continuo
        y_bracket = y_base_lance + d_lance + 18.0
        draw.Line(x_ini, y_bracket - 12.0, x_ini, y_bracket)
        draw.Line(x_ini, y_bracket, x_fim, y_bracket)
        draw.Line(x_fim, y_bracket, x_fim, y_bracket - 12.0)
        # Seta apontando no sentido do fluxo (esquerda)
        draw.Line(x_ini, y_bracket, x_ini + 12.0, y_bracket + 6.0)
        draw.Line(x_ini, y_bracket, x_ini + 12.0, y_bracket - 6.0)

        TQSUtil.writef("Ferro de ligacao da alvenaria (P2) gerado: %d barras de dia %.1f mm (Cor Azul, Continua)" % (qtd, bitola))

    except Exception as e:
        TQSUtil.writef("Erro ao gerar SmartRebar de ligacao alvenaria: %s" % str(e))


def desenhar_ferro_longitudinal_alvenaria_planta(dwg, geo_planta, dados_ferros):
    """
    Calcula e gera o Ferro Reto Longitudinal da Alvenaria (P9 - 2 barras).
    LINHA CONTINUA (iestilo=0), COR VERDE (cor=3).
    """
    elem_central = geo_planta.get("elemento_central")
    lances = geo_planta.get("lances", [])
    if not lances:
        return

    bitola = float(dados_ferros.get("bitola_long_alv", 6.3))
    qtd = int(dados_ferros.get("qtd_long_alv", 2))

    x_ini = min(l["x_ini"] for l in lances)
    x_fim = max(l["x_fim"] for l in lances)

    if elem_central and elem_central.get("y_base") is not None:
        y_center = (elem_central["y_base"] + elem_central["y_topo"]) / 2.0
    else:
        y_center = lances[0]["y_topo"]

    comp_barra = abs(x_fim - x_ini)

    try:
        rebar_long = TQSDwg.SmartRebar(dwg)
        rebar_long.type = TQSDwg.ICPFRT
        rebar_long.diameter = bitola
        rebar_long.spacing = 0.0  # Nao distribuido
        rebar_long.quantity = qtd
        try:
            if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                f_mark = dwg.globalrebar.FreeMark()
                rebar_long.mark = f_mark if f_mark > 0 else 9
            else:
                rebar_long.mark = 9
        except:
            rebar_long.mark = 9

        rebar_long.straightBarMainLength = comp_barra
        rebar_long.leaderLine = 1
        rebar_long.leaderLineDistance = 15.0

        # Inserir Linha do Ferro Reto na Alvenaria (Nivel 220, Linha Continua iestilo=0, Cor 3 - Verde)
        rebar_long.RebarLine(x_ini, y_center, 0.0, 1.0, 1, 0, 0, 0, 220, 0, 3)

        # Linha de chamada para o texto
        draw = dwg.draw
        draw.level = 220
        draw.color = 3   # Verde
        draw.style = 0   # Continuo
        x_pt_call = x_ini + 35.0
        draw.Line(x_pt_call, y_center, x_pt_call - 25.0, y_center - 30.0)

        TQSUtil.writef("Ferro longitudinal da alvenaria (P9) gerado: %d barras de dia %.1f mm (Cor Verde, Continua)" % (qtd, bitola))

    except Exception as e:
        TQSUtil.writef("Erro ao gerar SmartRebar longitudinal alvenaria: %s" % str(e))


def desenhar_ferros_tracejados_planta(dwg, geo_planta, dados_ferros):
    """
    Calcula e gera as armaduras tracejadas (iestilo = 1) nos Patamares e nos Lances da escada.
    LINHA TRACEJADA (iestilo=1), COR BRANCA/PADRAO (cor=7), COM GANCHOS NAS PONTAS.
    """
    lances = geo_planta.get("lances", [])
    if not lances:
        return

    cobr = float(dados_ferros.get("cobrimento", 2.5))
    bitola = float(dados_ferros.get("bitola_tracejados", 6.3))
    espac = float(dados_ferros.get("espac_tracejados", 15.0))
    if espac <= 0:
        espac = 15.0

    y_min_total = min(l["y_base"] for l in lances)
    y_max_total = max(l["y_topo"] for l in lances)
    largura_total = (y_max_total - y_min_total) - 2.0 * cobr

    # 1. Armaduras Tracejadas no Patamar Esquerdo
    pat_esq = geo_planta.get("patamar_esquerdo")
    if pat_esq and pat_esq.get("existe"):
        comp_pat = pat_esq["comprimento"]
        qtd_esq = int(math.ceil(comp_pat / espac)) + 1
        
        x_p1 = pat_esq["x_min"] + comp_pat * 0.35
        x_p2 = pat_esq["x_min"] + comp_pat * 0.70

        for x_ins in [x_p1, x_p2]:
            try:
                rebar_pat = TQSDwg.SmartRebar(dwg)
                rebar_pat.type = TQSDwg.ICPFRT
                rebar_pat.diameter = bitola
                rebar_pat.spacing = espac
                rebar_pat.quantity = qtd_esq
                try:
                    if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                        f_mark = dwg.globalrebar.FreeMark()
                        rebar_pat.mark = f_mark if f_mark > 0 else 15
                    else:
                        rebar_pat.mark = 15
                except:
                    rebar_pat.mark = 15

                rebar_pat.straightBarMainLength = largura_total
                rebar_pat.straightBarLeftLength = 15.0
                rebar_pat.straightBarRightLength = 15.0

                # Linha TRACEJADA (iestilo = 1) no nivel 220, cor 7 (branco)
                rebar_pat.RebarLine(x_ins, y_min_total + cobr, 90.0, 1.0, 1, 1, 1, 0, 220, 1, 7)
            except Exception as e:
                TQSUtil.writef("Erro ao gerar rebar tracejado patamar esquerdo: %s" % str(e))

    # 2. Armaduras Tracejadas no Patamar Direito
    pat_dir = geo_planta.get("patamar_direito")
    if pat_dir and pat_dir.get("existe"):
        comp_pat_d = pat_dir["comprimento"]
        qtd_dir = int(math.ceil(comp_pat_d / espac)) + 1
        
        x_pd1 = pat_dir["x_min"] + comp_pat_d * 0.35
        x_pd2 = pat_dir["x_min"] + comp_pat_d * 0.70

        for x_ins in [x_pd1, x_pd2]:
            try:
                rebar_pat_d = TQSDwg.SmartRebar(dwg)
                rebar_pat_d.type = TQSDwg.ICPFRT
                rebar_pat_d.diameter = bitola
                rebar_pat_d.spacing = espac
                rebar_pat_d.quantity = qtd_dir
                try:
                    if hasattr(dwg, 'globalrebar') and hasattr(dwg.globalrebar, 'FreeMark'):
                        f_mark = dwg.globalrebar.FreeMark()
                        rebar_pat_d.mark = f_mark if f_mark > 0 else 16
                    else:
                        rebar_pat_d.mark = 16
                except:
                    rebar_pat_d.mark = 16

                rebar_pat_d.straightBarMainLength = largura_total
                rebar_pat_d.straightBarLeftLength = 15.0
                rebar_pat_d.straightBarRightLength = 15.0

                # Linha TRACEJADA (iestilo = 1) no nivel 220, cor 7 (branco)
                rebar_pat_d.RebarLine(x_ins, y_min_total + cobr, 90.0, 1.0, 1, 1, 1, 0, 220, 1, 7)
            except Exception as e:
                TQSUtil.writef("Erro ao gerar rebar tracejado patamar direito: %s" % str(e))

    # 3. Armadura Tracejada no Lance (ex: degrau 04)
    for l in lances:
        x_ini = l["x_ini"]
        x_fim = l["x_fim"]
        y_b = l["y_base"]
        y_t = l["y_topo"]
        comp_lance = abs(x_fim - x_ini)
        qtd_lance = int(math.ceil(comp_lance / espac)) + 1
        largura_l = (y_t - y_b) - 2.0 * cobr

        deg_coords = l.get("degraus_coords", [])
        if len(deg_coords) >= 4:
            x_bar = deg_coords[3]
        else:
            x_bar = (x_ini + x_fim) / 2.0

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
            rebar_l.straightBarLeftLength = 15.0
            rebar_l.straightBarRightLength = 15.0

            # Linha TRACEJADA (iestilo = 1) no nivel 220, cor 7 (branco)
            rebar_l.RebarLine(x_bar, y_b + cobr, 90.0, 1.0, 1, 1, 1, 0, 220, 1, 7)
        except Exception as e:
            TQSUtil.writef("Erro ao gerar rebar tracejado no lance: %s" % str(e))

    TQSUtil.writef("Armaduras tracejadas dos patamares e lances geradas com sucesso (Estilo Tracejado, Cor Branca)!")


def desenhar_todos_ferros_planta(dwg, geo_planta, dados_ferros):
    """Gera o conjunto completo de ferros inteligentes na Planta Baixa da escada."""
    desenhar_ferro_ligacao_alvenaria_planta(dwg, geo_planta, dados_ferros)
    desenhar_ferro_longitudinal_alvenaria_planta(dwg, geo_planta, dados_ferros)
    desenhar_ferros_tracejados_planta(dwg, geo_planta, dados_ferros)


# ==============================================================================
# COMANDO PRINCIPAL UNIFICADO ACIONADO PELO MENU TQS ("2. Armar Escada")
# ==============================================================================
def meucmd(eag, tqsjan):
    """Funcao chamada pelo botao 'Armar Escada' no menu do TQS."""
    # 1. Coletar dados da armadura e escolha do modo (Corte ou Planta)
    dados_ferros = pedir_dados_armacao()
    if dados_ferros is None:
        TQSUtil.writef("Operacao cancelada.")
        return

    modo = dados_ferros.get("modo", "CORTE")

    # ==========================================================================
    # FLUXO 1: SE O USUARIO CLICOU EM "ARMAR CORTE"
    # ==========================================================================
    if modo == "CORTE":
        TQSUtil.writef("Selecione o Corte/Perfil da escada abrindo uma janela sobre ele:")
        addr, xs, ys, np, istat = eag.locate.Select(tqsjan, "Abra uma janela sobre o corte da escada", TQSEag.EAG_IJANEL)
        if istat != 0:
            TQSUtil.writef("Nenhum elemento selecionado.")
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
            TQSUtil.writef("Nenhuma linha encontrada na selecao.")
            return

        geo_perfil = identificar_geometria_escada(linhas)
        if geo_perfil is None:
            TQSUtil.writef("Nao foi possivel identificar o perfil da escada.")
            return

        desenhar_ferro_principal_maior(tqsjan.dwg, geo_perfil, dados_ferros)
        desenhar_ferro_no_superior(tqsjan.dwg, geo_perfil, dados_ferros)
        desenhar_ferro_bordo_patamar(tqsjan.dwg, geo_perfil, dados_ferros)
        desenhar_armadura_distribuicao(tqsjan.dwg, geo_perfil, dados_ferros)
        tqsjan.Regen()

        TQSUtil.writef("Armadura completa do Corte da escada gerada com sucesso!")
        return

    # ==========================================================================
    # FLUXO 2: SE O USUARIO CLICOU EM "ARMAR PLANTA BAIXA"
    # ==========================================================================
    elif modo == "PLANTA":
        TQSUtil.writef("Selecione a Planta Baixa da escada abrindo uma janela sobre ela:")
        addr, xs, ys, np, istat = eag.locate.Select(tqsjan, "Abra uma janela sobre a planta baixa da escada", TQSEag.EAG_IJANEL)
        if istat != 0:
            TQSUtil.writef("Nenhum elemento selecionado.")
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
            TQSUtil.writef("Nenhuma linha encontrada na selecao.")
            return

        geo_planta = identificar_geometria_planta_escada(linhas, textos)
        if geo_planta is None:
            TQSUtil.writef("Nao foi possivel identificar a Planta Baixa da escada.")
            return

        TQSUtil.writef("============================================================")
        TQSUtil.writef("PLANTA BAIXA DA ESCADA RECONHECIDA COM SUCESSO!")
        TQSUtil.writef("Orientacao: %s | Lances detectados: %d" % (geo_planta["orientacao"], geo_planta["num_lances"]))
        for l in geo_planta["lances"]:
            if geo_planta["orientacao"] == "HORIZONTAL":
                TQSUtil.writef("  Lance %d (%s): %d degraus, Piso = %.1f cm, Largura = %.1f cm" % 
                               (l["indice"], l["posicao"], l["n_degraus"], l["piso"], l["largura"]))
            else:
                TQSUtil.writef("  Lance %d (%s): %d degraus, Piso = %.1f cm, Largura = %.1f cm" % 
                               (l["indice"], l["posicao"], l["n_degraus"], l["piso"], l["largura"]))

        if geo_planta.get("elemento_central"):
            ec = geo_planta["elemento_central"]
            TQSUtil.writef("  Elemento Central: %s (Espessura = %.1f cm)" % (ec["tipo"], ec["espessura"]))
        if geo_planta.get("patamar_esquerdo"):
            TQSUtil.writef("  Patamar Esquerdo: %.1f cm" % geo_planta["patamar_esquerdo"]["comprimento"])
        if geo_planta.get("patamar_direito"):
            TQSUtil.writef("  Patamar Direito: %.1f cm" % geo_planta["patamar_direito"]["comprimento"])
        TQSUtil.writef("============================================================")

        # Gerar os Ferros Inteligentes Reais na Planta Baixa
        desenhar_todos_ferros_planta(tqsjan.dwg, geo_planta, dados_ferros)
        tqsjan.Regen()

        TQSUtil.writef("Armadura completa da Planta Baixa gerada com sucesso!")
