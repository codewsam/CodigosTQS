# -*- coding: utf-8 -*-
import os
import json
import math
import subprocess
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag


# ==============================================================================
# INTERFACE GRAFICA (HTA) - APENAS BITOLA, ESPACAMENTO E QUANTIDADE
# ==============================================================================
def pedir_dados_armacao():
    """Abre a janela nativa para coletar bitola, espacamento e quantidade."""
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
        <title>Armação da Escada - Plugin TQS</title>
        <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="ArmarEscada" BORDER="dialog" INNERBORDER="no" SCROLL="no" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Tahoma, sans-serif;
                background: #eef1f5;
                margin: 0;
                padding: 0;
                font-size: 13px;
                color: #2b2f36;
            }}
            .topbar {{
                background: linear-gradient(135deg, #1b5e20 0%, #0d3810 100%);
                color: #fff;
                padding: 14px 20px;
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
                padding: 20px;
            }}
            .card {{
                background: #ffffff;
                border: 1px solid #dbe1e8;
                border-radius: 8px;
                padding: 16px 20px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
                display: flex;
                flex-direction: column;
                gap: 12px;
            }}
            .card h3 {{
                margin: 0 0 8px 0;
                color: #1b5e20;
                font-size: 12.5px;
                font-weight: 600;
                text-transform: uppercase;
                border-bottom: 1px solid #e7ebf0;
                padding-bottom: 6px;
            }}
            .campo {{
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            label {{
                font-weight: 500;
                color: #45505c;
            }}
            input, select {{
                width: 110px;
                padding: 5px 8px;
                text-align: right;
                border: 1px solid #c3cbd4;
                border-radius: 4px;
                background: #fbfcfd;
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
                gap: 10px;
                margin-top: 16px;
            }}
            button {{
                padding: 8px 22px;
                cursor: pointer;
                border: 1px solid #c3cbd4;
                border-radius: 5px;
                background: #f4f5f7;
                font-size: 12.5px;
                font-weight: 500;
            }}
            .btn-gerar {{
                background: linear-gradient(135deg, #1b5e20 0%, #0d3810 100%);
                color: #fff;
                border: none;
                font-weight: 600;
            }}
        </style>
        <script>
            window.resizeTo(420, 360);

            function confirmar() {{
                try {{
                    var fso = new ActiveXObject("Scripting.FileSystemObject");
                    var file = fso.CreateTextFile("{json_js}", true, false);

                    var dados = {{
                        "bitola": parseFloat(document.getElementById('bitola').value.replace(',', '.')),
                        "espacamento": parseFloat(document.getElementById('espacamento').value.replace(',', '.')),
                        "quantidade": parseInt(document.getElementById('quantidade').value)
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
            <h1>Armação da Escada</h1>
            <p>Plugin TQS &#9679 Dados de Armadura</p>
        </div>

        <div class="container">
            <div class="card">
                <h3>Parâmetros dos Ferros</h3>
                
                <div class="campo">
                    <label>Bitola:</label>
                    <select id="bitola">
                        <option value="5.0">Ø 5.0 mm</option>
                        <option value="6.3">Ø 6.3 mm</option>
                        <option value="8.0">Ø 8.0 mm</option>
                        <option value="10.0">Ø 10.0 mm</option>
                        <option value="12.5" selected>Ø 12.5 mm</option>
                        <option value="16.0">Ø 16.0 mm</option>
                    </select>
                </div>

                <div class="campo">
                    <label>Espaçamento (cm):</label>
                    <input type="text" id="espacamento" value="15">
                </div>

                <div class="campo">
                    <label>Quantidade:</label>
                    <input type="text" id="quantidade" value="8">
                </div>
            </div>

            <div class="btns">
                <button onclick="window.close()">Cancelar</button>
                <button class="btn-gerar" onclick="confirmar()">Avançar</button>
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
# RECONHECIMENTO GEOMETRICO DA ESCADA SELECIONADA
# ==============================================================================
def identificar_geometria_escada(linhas):
    """Analisa as linhas selecionadas e deduz todas as dimensoes da escada."""
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

    # Filtrar espelhos dos degraus (verticais com altura típica de degrau: 14 a 22 cm)
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

    # 3. Piso e Espelho médios
    pisos_vals = []
    for i in range(len(espelhos) - 1):
        dx = espelhos[i+1][0] - espelhos[i][0]
        if dx > 5.0:
            pisos_vals.append(dx)

    piso = (sum(pisos_vals) / len(pisos_vals)) if pisos_vals else 28.0
    espelho = sum(e[3] for e in espelhos) / len(espelhos)

    # 4. Patamar de Partida (horizontal que termina em x0 no nível y0)
    patamar_partida = 0.0
    for h in horizontais:
        if abs(h[1] - x0) < 0.5 and abs(h[2] - y0) < 0.5:
            patamar_partida = h[3]
            break

    # 5. Patamar de Chegada (horizontal que começa no topo da escada)
    x_topo = espelhos[-1][0]
    y_topo = espelhos[-1][2]
    patamar_chegada = 0.0
    for h in horizontais:
        if abs(h[0] - x_topo) < 0.5 and abs(h[2] - y_topo) < 0.5:
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

    # Viga de partida (face vertical mais à esquerda)
    x_lim_esq = x0 - patamar_partida
    vert_esq = [v for v in verticais if v[0] <= x_lim_esq + 0.1]
    if vert_esq:
        vert_esq.sort(key=lambda v: v[0])
        viga_largura = max(x_lim_esq - vert_esq[0][0], 20.0)
        viga_altura = max(vert_esq[0][3], 40.0)

    # Viga de chegada (face vertical mais à direita)
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


# ==============================================================================
# DESENHO DO FERRO PRINCIPAL MAIOR (N1)
# ==============================================================================
def desenhar_ferro_principal_maior(dwg, geo, dados_ferros):
    """Calcula e desenha o ferro positivo principal."""
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

    cobr = 2.5  # Cobrimento padrão (2.5 cm)
    bitola = float(dados_ferros["bitola"])
    espac = float(dados_ferros["espacamento"])
    qtd = int(dados_ferros["quantidade"])

    # 1. Reta inclinada do fundo do lance com cobrimento
    p1x, p1y = x0 + piso, y0 + espelho
    p2x, p2y = x0 + (n_deg - 1) * piso, y0 + (n_deg - 1) * espelho
    dist_fundo = espessura - cobr
    f_x1, f_y1, f_x2, f_y2 = obter_fundo_lance(p1x, p1y, p2x, p2y, dist_fundo)

    # --------------------------------------------------------------------------
    # PONTOS DO FERRO:
    # --------------------------------------------------------------------------
    # Ponto 1: Ponta inferior do gancho no lado direito da viga inferior (onde o usuario desenhou em vermelho)
    x_gancho_esq = (x0 - pat_part) - cobr
    y_fundo_pat_part = y0 - espessura + cobr
    y_gancho_inf_base = y0 - viga_h + cobr

    pt1_x = x_gancho_esq
    pt1_y = y_gancho_inf_base

    # Ponto 2: Canto no encontro da face direita da viga com o fundo do patamar
    pt2_x = x_gancho_esq
    pt2_y = y_fundo_pat_part

    # Ponto 3: Encontro do fundo horizontal do patamar com o fundo inclinado
    pt3_x = calcular_x_no_y(f_x1, f_y1, f_x2, f_y2, y_fundo_pat_part)
    pt3_y = y_fundo_pat_part

    # Ponto 4: O ferro sobe pelo fundo inclinado e vai até o TOPO do patamar de chegada
    y_topo_arm = y_topo - cobr
    pt4_x = calcular_x_no_y(f_x1, f_y1, f_x2, f_y2, y_topo_arm)
    pt4_y = y_topo_arm

    # Ponto 5: Canto superior do L invertido na viga de chegada à direita
    x_viga_sup = x_topo + pat_cheg + viga_l - cobr
    pt5_x = x_viga_sup
    pt5_y = y_topo_arm

    # Ponto 6: Ponta inferior do gancho descendo na viga de chegada (L invertido)
    y_gancho_sup_base = y_topo - viga_h + cobr
    pt6_x = x_viga_sup
    pt6_y = y_gancho_sup_base

    pontos_ferro = [
        (pt1_x, pt1_y),
        (pt2_x, pt2_y),
        (pt3_x, pt3_y),
        (pt4_x, pt4_y),
        (pt5_x, pt5_y),
        (pt6_x, pt6_y)
    ]

    # --- Desenho Gráfico no Desenho (Nível 241, Cor 4 - Ciano/Azul Claro) ---
    draw = dwg.draw
    draw.level = 241
    draw.color = 4   # Ciano / Azul Claro
    draw.style = 0   # Linha Contínua

    for i in range(len(pontos_ferro) - 1):
        pa = pontos_ferro[i]
        pb = pontos_ferro[i + 1]
        draw.Line(pa[0], pa[1], pb[0], pb[1])

    # --- Criar Objeto SmartRebar do TQS ---
    try:
        rebar = TQSDwg.SmartRebar(dwg)
        rebar.type = TQSDwg.ICPFGN
        rebar.diameter = bitola
        rebar.spacing = espac
        rebar.quantity = qtd
        rebar.mark = 1

        for px, py in pontos_ferro:
            rebar.GenRebarPoint(px, py, 0.0, 0, 1, -1)

        # Inserir no DWG
        rebar.RebarLine(0.0, 0.0, 0.0, 1.0, 0, 0, 0, 0, 241, -1, 4)
    except Exception as e:
        pass


# ==============================================================================
# COMANDO PRINCIPAL ACIONADO PELO MENU TQS
# ==============================================================================
def meucmd(eag, tqsjan):
    """Funcao chamada pelo botao 'Armar Escada'."""
    # 1. Coletar dados da armadura (apenas bitola, espacamento e quantidade)
    dados_ferros = pedir_dados_armacao()
    if dados_ferros is None:
        TQSUtil.writef("Operacao cancelada.")
        return

    # 2. Selecionar a escada
    TQSUtil.writef("Selecione a escada abrindo uma janela sobre ela...")
    addr, xs, ys, np, istat = eag.locate.Select(tqsjan, "Abra uma janela sobre a escada", TQSEag.EAG_IJANEL)
    if istat != 0:
        TQSUtil.writef("Nenhum elemento selecionado.")
        return

    # 3. Ler elementos
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

    if not linhas:
        TQSUtil.writef("Nenhuma linha encontrada na selecao.")
        return

    # 4. Reconhecer a geometria
    geo = identificar_geometria_escada(linhas)
    if geo is None:
        TQSUtil.writef("Nao foi possivel identificar o perfil da escada.")
        return

    # 5. Desenhar o ferro principal maior
    desenhar_ferro_principal_maior(tqsjan.dwg, geo, dados_ferros)
    tqsjan.Regen()

    TQSUtil.writef("Ferro principal maior gerado com sucesso!")
