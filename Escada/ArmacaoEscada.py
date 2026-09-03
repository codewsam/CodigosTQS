# -*- coding: utf-8 -*-
import os
import json
import math
import subprocess
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag


# ==============================================================================
# INTERFACE GRAFICA (HTA) PARA ENTRADA DOS DADOS DE ARMACAO
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
                        <option value="10.0" selected>Ø 10.0 mm</option>
                        <option value="12.5">Ø 12.5 mm</option>
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
        # Classificar por tipo de segmento
        if abs(x1 - x2) < 0.1:  # Vertical
            verticais.append((x1, min(y1, y2), max(y1, y2), abs(y2 - y1)))
        elif abs(y1 - y2) < 0.1:  # Horizontal
            horizontais.append((min(x1, x2), max(x1, x2), y1, abs(x2 - x1)))
        else:
            inclinadas.append(((min(x1, x2), y1 if x1 < x2 else y2), (max(x1, x2), y2 if x1 < x2 else y1)))

    if not verticais or not horizontais:
        return None

    # Filtrar os espelhos dos degraus (verticais com altura típica de degrau: 14 a 22 cm)
    espelhos = [v for v in verticais if 14.0 <= v[3] <= 22.0]
    espelhos.sort(key=lambda v: (v[0], v[1]))

    if not espelhos:
        # Tentar sem filtro rígido de altura caso tenha espelhos menores/maiores
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
    if inclinadas:
        p_inc = inclinadas[0]
        # Pega o canto interno do primeiro piso (x0 + piso, y0 + espelho)
        canto_x = x0 + piso
        canto_y = y0 + espelho
        espessura = TQSGeo.DistancePointLine(p_inc[0][0], p_inc[0][1], p_inc[1][0], p_inc[1][1], canto_x, canto_y)

    return {
        "x0": round(x0, 2),
        "y0": round(y0, 2),
        "n_degraus": n_degraus,
        "piso": round(piso, 1),
        "espelho": round(espelho, 1),
        "patamar_partida": round(patamar_partida, 1),
        "patamar_chegada": round(patamar_chegada, 1),
        "espessura": round(espessura, 1),
        "qtd_linhas_lidas": len(linhas)
    }


# ==============================================================================
# COMANDO PRINCIPAL ACIONADO PELO MENU TQS
# ==============================================================================
def meucmd(eag, tqsjan):
    """Funcao chamada pelo botao 'Armar Escada'."""
    # 1. Abrir a janela para coletar dados dos ferros
    dados_ferros = pedir_dados_armacao()
    if dados_ferros is None:
        TQSUtil.writef("Operacao cancelada.")
        return

    # 2. Pedir para o usuario selecionar a escada por janela
    TQSUtil.writef("Selecione a escada abrindo uma janela sobre ela...")
    addr, xs, ys, np, istat = eag.locate.Select(tqsjan, "Abra uma janela sobre a escada", TQSEag.EAG_IJANEL)
    if istat != 0:
        TQSUtil.writef("Nenhum elemento selecionado.")
        return

    # 3. Ler todos os elementos selecionados
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

    # 4. Executar o reconhecimento geometrico
    geo = identificar_geometria_escada(linhas)
    if geo is None:
        TQSUtil.writef("Nao foi possivel identificar o perfil da escada nas %d linhas selecionadas." % len(linhas))
        return

    # 5. Exibir o resultado da identificacao no console TQS
    TQSUtil.writef("==================================================")
    TQSUtil.writef("   RECONHECIMENTO DA ESCADA CONCLUIDO COM SUCESSO")
    TQSUtil.writef("==================================================")
    TQSUtil.writef("Linhas lidas na selecao: %d" % geo["qtd_linhas_lidas"])
    TQSUtil.writef("Ponto Inicial (x0, y0) : (%.1f, %.1f) cm" % (geo["x0"], geo["y0"]))
    TQSUtil.writef("Numero de Degraus      : %d" % geo["n_degraus"])
    TQSUtil.writef("Piso                   : %.1f cm" % geo["piso"])
    TQSUtil.writef("Espelho                : %.1f cm" % geo["espelho"])
    TQSUtil.writef("Patamar de Partida     : %.1f cm" % geo["patamar_partida"])
    TQSUtil.writef("Patamar de Chegada     : %.1f cm" % geo["patamar_chegada"])
    TQSUtil.writef("Espessura da Laje      : %.1f cm" % geo["espessura"])
    TQSUtil.writef("--------------------------------------------------")
    TQSUtil.writef("Ferros configurados: Bitola Ø%.1f mm | Espaçamento c/%.1f cm | Qtd: %d"
                   % (dados_ferros["bitola"], dados_ferros["espacamento"], dados_ferros["quantidade"]))
    TQSUtil.writef("==================================================")
