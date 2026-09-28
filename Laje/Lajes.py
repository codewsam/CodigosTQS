# -*- coding: utf-8 -*-
import os
import json
import math
import subprocess
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag


# ==============================================================================
# INTERFACE GRÁFICA (HTA) - PARÂMETROS DE ARMAÇÃO DA LAJE NERVURADA
# ==============================================================================
def pedir_dados_laje():
    """Abre a janela nativa para coletar parâmetros da armação das nervuras da laje."""
    caminho_script = os.path.dirname(os.path.abspath(__file__))
    hta_path = os.path.join(caminho_script, "dialogo_laje.hta")
    json_path = os.path.join(caminho_script, "dados_laje_temp.json")

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
        <title>Armadura de Laje Nervurada - G3 Plugins</title>
        <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="ArmarLaje" BORDER="dialog" INNERBORDER="no" SCROLL="no" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Tahoma, sans-serif;
                background: #eef1f5;
                margin: 0;
                padding: 0;
                font-size: 12.5px;
                color: #2b2f36;
            }}
            .topbar {{
                background: linear-gradient(135deg, #0d3b66 0%, #001e3d 100%);
                color: #fff;
                padding: 12px 18px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.25);
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .topbar .icon {{
                width: 28px;
                height: 28px;
                background: rgba(255,255,255,0.15);
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
            }}
            .topbar h1 {{
                margin: 0;
                font-size: 15px;
                font-weight: 600;
            }}
            .topbar p {{
                margin: 2px 0 0 0;
                font-size: 11px;
                color: #b8d4f0;
            }}
            .container {{
                padding: 14px 18px 10px 18px;
                display: flex;
                gap: 14px;
            }}
            .col-form {{
                flex: 1;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }}
            .card {{
                background: #ffffff;
                border: 1px solid #dbe1e8;
                border-radius: 8px;
                padding: 10px 14px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            }}
            .card h3 {{
                margin: 0 0 8px 0;
                color: #0d3b66;
                font-size: 12.5px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.3px;
                border-bottom: 1px solid #e7ebf0;
                padding-bottom: 5px;
            }}
            .campo {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 6px;
            }}
            .campo:last-child {{ margin-bottom: 0; }}
            label {{
                font-weight: 500;
                color: #45505c;
                font-size: 12px;
            }}
            input, select {{
                width: 100px;
                padding: 4px 6px;
                text-align: right;
                border: 1px solid #c3cbd4;
                border-radius: 4px;
                background: #fbfcfd;
                font-size: 12px;
            }}
            select {{ text-align: left; width: 140px; }}
            input:focus, select:focus {{
                outline: none;
                border-color: #0d3b66;
                box-shadow: 0 0 0 2px rgba(13,59,102,0.15);
                background: #fff;
            }}
            input[type="checkbox"] {{
                width: auto;
                transform: scale(1.1);
            }}
            .info-box {{
                background: #e8f1fa;
                border: 1px solid #c2daf2;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 11.5px;
                color: #1a4971;
                margin-top: 4px;
            }}
            .btns {{
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                padding: 0 18px 14px 18px;
            }}
            button {{
                padding: 7px 18px;
                cursor: pointer;
                border: 1px solid #c3cbd4;
                border-radius: 5px;
                background: #f4f5f7;
                font-size: 12.5px;
                font-weight: 500;
                color: #45505c;
            }}
            button:hover {{ background: #e6e8eb; }}
            .btn-gerar {{
                background: linear-gradient(135deg, #0d3b66 0%, #001e3d 100%);
                color: #fff;
                border: none;
                font-weight: 600;
                box-shadow: 0 1px 3px rgba(13,59,102,0.35);
            }}
            .btn-gerar:hover {{ background: linear-gradient(135deg, #082642 0%, #001326 100%); }}
        </style>
        <script type="text/javascript">
            function initDialog() {{
                try {{
                    window.resizeTo(780, 560);
                    window.moveTo((screen.availWidth - 780) / 2, (screen.availHeight - 560) / 2);
                }} catch(e) {{}}
            }}

            function confirmar() {{
                try {{
                    var dados = {{
                        "direcao": document.getElementById('direcao').value,
                        "modulo_nervura": parseFloat(document.getElementById('modulo_nervura').value.replace(',', '.')) || 65.0,
                        "largura_nervura": parseFloat(document.getElementById('largura_nervura').value.replace(',', '.')) || 10.0,
                        "bitola": parseFloat(document.getElementById('bitola').value) || 10.0,
                        "qtd_barras": parseInt(document.getElementById('qtd_barras').value) || 1,
                        "tipo_gancho": document.getElementById('tipo_gancho').value,
                        "comprimento_gancho": parseFloat(document.getElementById('comprimento_gancho').value.replace(',', '.')) || 15.0,
                        "cobrimento": parseFloat(document.getElementById('cobrimento').value.replace(',', '.')) || 2.5,
                        "posicao_inicial": parseInt(document.getElementById('posicao_inicial').value) || 1,
                        "desenhar_chamada": document.getElementById('desenhar_chamada').checked
                    }};

                    var fso = new ActiveXObject("Scripting.FileSystemObject");
                    var a = fso.CreateTextFile("{json_js}", true);

                    var jsonStr = '{{"direcao":"' + dados.direcao + '"' +
                                  ',"modulo_nervura":' + dados.modulo_nervura + 
                                  ',"largura_nervura":' + dados.largura_nervura + 
                                  ',"bitola":' + dados.bitola + 
                                  ',"qtd_barras":' + dados.qtd_barras + 
                                  ',"tipo_gancho":"' + dados.tipo_gancho + '"' + 
                                  ',"comprimento_gancho":' + dados.comprimento_gancho + 
                                  ',"cobrimento":' + dados.cobrimento + 
                                  ',"posicao_inicial":' + dados.posicao_inicial + 
                                  ',"desenhar_chamada":' + dados.desenhar_chamada + '}}';

                    a.WriteLine(jsonStr);
                    a.Close();
                    window.close();
                }} catch (e) {{
                    alert("Erro ao salvar dados: " + e.message);
                }}
            }}
        </script>
    </head>
    <body onload="initDialog();">
        <div class="topbar">
            <div class="icon">▦</div>
            <div>
                <h1>Armação de Laje Nervurada</h1>
                <p>Plugin TQS &#9679 Ediglânthio Samuel Araújo Brandão &#9679 G3 Engenharia</p>
            </div>
        </div>

        <div class="container">
            <div class="col-form">
                <div class="card">
                    <h3>Disposição das Nervuras</h3>
                    <div class="campo">
                        <label>Direção da Armadura:</label>
                        <select id="direcao">
                            <option value="XY" selected>Eixos X e Y (Ambas)</option>
                            <option value="X">Apenas Eixo X (Horizontal)</option>
                            <option value="Y">Apenas Eixo Y (Vertical)</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label>Espaçamento entre Eixos (cm):</label>
                        <input type="text" id="modulo_nervura" value="65">
                    </div>
                    <div class="campo">
                        <label>Largura da Nervura (cm):</label>
                        <input type="text" id="largura_nervura" value="10">
                    </div>
                </div>

                <div class="card">
                    <h3>Armadura Positiva</h3>
                    <div class="campo">
                        <label>Bitola da Barra (&Phi; mm):</label>
                        <select id="bitola">
                            <option value="6.3">&Phi; 6.3 mm</option>
                            <option value="8.0">&Phi; 8.0 mm</option>
                            <option value="10.0" selected>&Phi; 10.0 mm</option>
                            <option value="12.5">&Phi; 12.5 mm</option>
                            <option value="16.0">&Phi; 16.0 mm</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label>Barras por Nervura:</label>
                        <select id="qtd_barras">
                            <option value="1" selected>1 Barra</option>
                            <option value="2">2 Barras</option>
                        </select>
                    </div>
                </div>
            </div>

            <div class="col-form">
                <div class="card">
                    <h3>Ancoragens e Extremidades</h3>
                    <div class="campo">
                        <label>Tipo de Dobra / Gancho:</label>
                        <select id="tipo_gancho">
                            <option value="90" selected>Gancho a 90&deg;</option>
                            <option value="135">Gancho a 135&deg;</option>
                            <option value="RETO">Reta (Sem Gancho)</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label>Comprimento Gancho (cm):</label>
                        <input type="text" id="comprimento_gancho" value="15">
                    </div>
                    <div class="campo">
                        <label>Cobrimento da Ponta (cm):</label>
                        <input type="text" id="cobrimento" value="2.5">
                    </div>
                </div>

                <div class="card">
                    <h3>Identificação no Desenho</h3>
                    <div class="campo">
                        <label>Posição Inicial (N):</label>
                        <input type="text" id="posicao_inicial" value="1">
                    </div>
                    <div class="campo" style="margin-top: 6px;">
                        <label>Desenhar linha de chamada?</label>
                        <input type="checkbox" id="desenhar_chamada" checked>
                    </div>
                </div>

                <div class="info-box">
                    💡 <b>Como funciona:</b> Ao clicar em Avançar, você selecionará 2 cantos no EAG para definir o alinhamento da região das cubetas.
                </div>
            </div>
        </div>

        <div class="btns">
            <button onclick="window.close()">Cancelar</button>
            <button class="btn-gerar" onclick="confirmar()">Selecionar Região no EAG</button>
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
# FUNÇÃO PARA DESENHAR OS FERROS DAS NERVURAS NA REGIÃO SELECIONADA
# ==============================================================================
def armar_regiao_laje(dwg, p1, p2, dados):
    """
    Gera as barras de armadura positiva nas nervuras entre p1 e p2.
    """
    x1, y1 = min(p1[0], p2[0]), min(p1[1], p2[1])
    x2, y2 = max(p1[0], p2[0]), max(p1[1], p2[1])

    direcao = dados.get("direcao", "XY").upper()
    modulo = float(dados.get("modulo_nervura", 65.0))
    bitola = float(dados.get("bitola", 10.0))
    cobrimento = float(dados.get("cobrimento", 2.5))
    tipo_gancho = str(dados.get("tipo_gancho", "90"))
    comp_gancho = float(dados.get("comprimento_gancho", 15.0))
    desenhar_chamada = bool(dados.get("desenhar_chamada", True))
    pos_ini = int(dados.get("posicao_inicial", 1))

    draw = dwg.draw

    # Nível do ferro no TQS (Nível 220 = Linha que representa o ferro)
    draw.level = 220
    draw.color = 3   # Verde (Cor padrão de armadura positiva no TQS)
    draw.style = 0

    largura_total = x2 - x1
    altura_total = y2 - y1

    pos_atual = pos_ini

    # --------------------------------------------------------------------------
    # 1. FERROS HORIZONTAIS (EIXO X)
    # --------------------------------------------------------------------------
    if direcao in ["XY", "X"]:
        num_nervuras_y = int(altura_total / modulo)
        if num_nervuras_y <= 0:
            num_nervuras_y = 1

        sobra_y = altura_total - (num_nervuras_y * modulo)
        y_offset_ini = y1 + (modulo / 2.0) + (sobra_y / 2.0)

        x_ini_ferro = x1 + cobrimento
        x_fim_ferro = x2 - cobrimento

        for i in range(num_nervuras_y):
            y_nerv = y_offset_ini + i * modulo
            if y_nerv > y2:
                break

            # Linha longitudinal principal do ferro
            draw.Line(x_ini_ferro, y_nerv, x_fim_ferro, y_nerv)

            # Ganchos de ancoragem nas pontas
            if tipo_gancho == "90":
                draw.Line(x_ini_ferro, y_nerv, x_ini_ferro, y_nerv + comp_gancho)
                draw.Line(x_fim_ferro, y_nerv, x_fim_ferro, y_nerv + comp_gancho)
            elif tipo_gancho == "135":
                diag = comp_gancho * 0.7071
                draw.Line(x_ini_ferro, y_nerv, x_ini_ferro + diag, y_nerv + diag)
                draw.Line(x_fim_ferro, y_nerv, x_fim_ferro - diag, y_nerv + diag)

            # Texto de chamada do ferro (se habilitado)
            if desenhar_chamada and i == int(num_nervuras_y / 2):
                draw.level = 220
                draw.color = 7  # Branco/Texto
                txt_ferro = f"N{pos_atual} 1 %%{bitola:.1f} c/{modulo:.0f}"
                draw.Text((x_ini_ferro + x_fim_ferro) / 2.0 - 25.0, y_nerv + 6.0, 7.0, 0.0, txt_ferro)
                draw.color = 3

        pos_atual += 1

    # --------------------------------------------------------------------------
    # 2. FERROS VERTICAIS (EIXO Y)
    # --------------------------------------------------------------------------
    if direcao in ["XY", "Y"]:
        num_nervuras_x = int(largura_total / modulo)
        if num_nervuras_x <= 0:
            num_nervuras_x = 1

        sobra_x = largura_total - (num_nervuras_x * modulo)
        x_offset_ini = x1 + (modulo / 2.0) + (sobra_x / 2.0)

        y_ini_ferro = y1 + cobrimento
        y_fim_ferro = y2 - cobrimento

        for j in range(num_nervuras_x):
            x_nerv = x_offset_ini + j * modulo
            if x_nerv > x2:
                break

            # Linha longitudinal vertical do ferro
            draw.Line(x_nerv, y_ini_ferro, x_nerv, y_fim_ferro)

            # Ganchos de ancoragem nas pontas
            if tipo_gancho == "90":
                draw.Line(x_nerv, y_ini_ferro, x_nerv + comp_gancho, y_ini_ferro)
                draw.Line(x_nerv, y_fim_ferro, x_nerv + comp_gancho, y_fim_ferro)
            elif tipo_gancho == "135":
                diag = comp_gancho * 0.7071
                draw.Line(x_nerv, y_ini_ferro, x_nerv + diag, y_ini_ferro + diag)
                draw.Line(x_nerv, y_fim_ferro, x_nerv + diag, y_fim_ferro - diag)

            # Texto de chamada do ferro vertical (se habilitado)
            if desenhar_chamada and j == int(num_nervuras_x / 2):
                draw.level = 220
                draw.color = 7  # Branco/Texto
                txt_ferro = f"N{pos_atual} 1 %%{bitola:.1f} c/{modulo:.0f}"
                draw.Text(x_nerv + 6.0, (y_ini_ferro + y_fim_ferro) / 2.0, 7.0, 90.0, txt_ferro)
                draw.color = 3


# ==============================================================================
# ENTRY POINT PRINCIPAL DO COMANDO NO TQS EAG
# ==============================================================================
def meucmd(eag, tqsjan):
    """Funcao chamada pelo menu TQS para armar a laje nervurada."""
    dados = pedir_dados_laje()
    if dados is None:
        return

    # Solicita a selecao dos dois pontos do retangulo da regiao das nervuras
    icod1, x1, y1 = eag.locate.GetPoint(tqsjan, "Clique no 1º canto da região da laje (ex: inferior esquerdo)")
    if icod1 == -1:
        return

    icod2, x2, y2 = eag.locate.GetPoint(tqsjan, "Clique no 2º canto oposto da região da laje")
    if icod2 == -1:
        return

    armar_regiao_laje(tqsjan.dwg, (x1, y1), (x2, y2), dados)

    tqsjan.ZoomTotal()
    tqsjan.Regen()
