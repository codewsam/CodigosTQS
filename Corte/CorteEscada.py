# -*- coding: utf-8 -*-
import os
import json
import subprocess
from TQS import TQSUtil, TQSGeo


def pedir_dados_janela_windows():
    """Gera uma janela nativa do Windows independente do Python para coletar os dados."""
    caminho_script = os.path.dirname(os.path.abspath(__file__))
    hta_path = os.path.join(caminho_script, "dialogo_escada.hta")
    json_path = os.path.join(caminho_script, "dados_temp.json")
    img_path = os.path.join(caminho_script, "diagrama_escada.png")

    if os.path.exists(json_path):
        try:
            os.remove(json_path)
        except:
            pass

    json_js = json_path.replace('\\', '\\\\')
    img_html = "file:///" + img_path.replace('\\', '/')

    hta_content = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <meta http-equiv="x-ua-compatible" content="ie=edge" />
        <title>Dados da Escada - Plugin TQS</title>
        <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="EscadaTQS" BORDER="dialog" INNERBORDER="no" SCROLL="no" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
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
                background: linear-gradient(135deg, #0056b3 0%, #003d80 100%);
                color: #fff;
                padding: 12px 20px;
                display: flex;
                align-items: center;
                gap: 10px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.25);
            }}

            .topbar .icon {{
                width: 26px;
                height: 26px;
                background: rgba(255,255,255,0.15);
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 15px;
            }}

            .topbar h1 {{
                margin: 0;
                font-size: 15px;
                font-weight: 600;
                letter-spacing: 0.2px;
            }}

            .topbar p {{
                margin: 1px 0 0 0;
                font-size: 11px;
                color: #d7e6fb;
                font-weight: 400;
            }}

            .container {{
                display: flex;
                gap: 16px;
                padding: 16px 20px 20px 20px;
            }}

            .img-box {{
                background: #ffffff;
                padding: 10px;
                border: 1px solid #dbe1e8;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 1px 3px rgba(0,0,0,0.06);
            }}

            .img-box img {{ max-width: 420px; }}

            .form-box {{
                display: flex;
                flex-direction: column;
                gap: 10px;
                flex: 1;
                min-width: 300px;
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
                color: #0056b3;
                font-size: 12.5px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.4px;
                border-bottom: 1px solid #e7ebf0;
                padding-bottom: 6px;
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
            }}

            input, select {{
                width: 90px;
                padding: 4px 6px;
                text-align: right;
                border: 1px solid #c3cbd4;
                border-radius: 4px;
                background: #fbfcfd;
                transition: border-color 0.15s, box-shadow 0.15s;
            }}

            input:focus, select:focus {{
                outline: none;
                border-color: #0056b3;
                box-shadow: 0 0 0 2px rgba(0,86,179,0.15);
                background: #fff;
            }}

            select {{ text-align: left; width: 130px; }}

            input[type="checkbox"] {{
                width: auto;
                text-align: left;
                accent-color: #0056b3;
                transform: scale(1.1);
            }}

            .sec-opcional {{
                background: #f2f6fb;
                padding: 8px 10px;
                border-radius: 6px;
                border: 1px solid #d7e4f2;
                margin-top: 4px;
            }}

            .btns {{
                margin-top: 4px;
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                padding: 0 20px 18px 20px;
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
                transition: background 0.15s;
            }}

            button:hover {{ background: #e6e8eb; }}

            .btn-gerar {{
                background: linear-gradient(135deg, #0056b3 0%, #003d80 100%);
                color: #fff;
                border: none;
                font-weight: 600;
                box-shadow: 0 1px 3px rgba(0,86,179,0.35);
            }}

            .btn-gerar:hover {{ background: linear-gradient(135deg, #004494 0%, #00306b 100%); }}
        </style>
        <script>
            window.resizeTo(1200, 920);

            function toggleLances() {{
                var numLances = parseInt(document.getElementById('num_lances').value);
                var box2 = document.getElementById('box_lance2');
                var box3 = document.getElementById('box_lance3');
                var campoPat1 = document.getElementById('campo_pat1');

                if (numLances === 1) {{
                    box2.style.display = "none";
                    box3.style.display = "none";
                    campoPat1.style.display = "none";
                }} else if (numLances === 2) {{
                    box2.style.display = "block";
                    box3.style.display = "none";
                    campoPat1.style.display = "flex";
                }} else if (numLances === 3) {{
                    box2.style.display = "block";
                    box3.style.display = "block";
                    campoPat1.style.display = "flex";
                }}
            }}

            function togglePatamarPartida() {{
                var temPat = document.getElementById('tem_patamar_partida').checked;
                var box = document.getElementById('box_patamar_partida');
                if (box) {{
                    box.style.display = temPat ? "flex" : "none";
                }}
            }}

            function togglePatamarChegada() {{
                var temPat = document.getElementById('tem_patamar_chegada').checked;
                var box = document.getElementById('box_patamar_chegada');
                if (box) {{
                    box.style.display = temPat ? "flex" : "none";
                }}
            }}

            function toggleExtremos() {{
                var altExt = document.getElementById('alterar_extremos').checked;
                var box = document.getElementById('box_extremos');
                if (box) {{
                    box.style.display = altExt ? "block" : "none";
                }}
            }}

                                    function toggleVao() {{
                var temVao = document.getElementById('tem_vao_lances').checked;
                var box = document.getElementById('box_vao_lances');
                if (box) {{
                    box.style.display = temVao ? "flex" : "none";
                }}
            }}

            function togglePlanta() {{
                var temPlanta = document.getElementById('desenhar_planta').checked;
                var box = document.getElementById('box_opcoes_planta');
                if (box) {{
                    box.style.display = temPlanta ? "block" : "none";
                }}
                atualizarCamposPlanta();
            }}

            function atualizarCamposPlanta() {{
                var numLances = parseInt(document.getElementById('num_lances').value);
                var box1 = document.getElementById('box_planta_1lance');
                var boxMulti = document.getElementById('box_planta_multilance');
                var boxL3 = document.getElementById('box_planta_l3');
                if (box1 && boxMulti) {{
                    if (numLances === 1) {{
                        box1.style.display = "block";
                        boxMulti.style.display = "none";
                    }} else {{
                        box1.style.display = "none";
                        boxMulti.style.display = "block";
                        if (boxL3) {{
                            boxL3.style.display = (numLances === 3) ? "flex" : "none";
                        }}
                    }}
                }}
            }}

            function confirmar() {{
                try {{
                    var fso = new ActiveXObject("Scripting.FileSystemObject");
                    var file = fso.CreateTextFile("{json_js}", true, false);

                    var numLances = parseInt(document.getElementById('num_lances').value);
                    var n_deg1 = parseInt(document.getElementById('n_degraus_1').value);
                    var n_deg2 = numLances >= 2 ? parseInt(document.getElementById('n_degraus_2').value) : 0;
                    var n_deg3 = numLances === 3 ? parseInt(document.getElementById('n_degraus_3').value) : 0;
                    var temPatPartida = document.getElementById('tem_patamar_partida').checked;
                    var temPatChegada = document.getElementById('tem_patamar_chegada').checked;
                    var altExtremos = document.getElementById('alterar_extremos').checked;
                    var espGeral = parseFloat(document.getElementById('espelho').value.replace(',', '.'));

                    var dados = {{
                        "num_lances": numLances,
                        "piso": parseFloat(document.getElementById('piso').value.replace(',', '.')),
                        "espelho": espGeral,
                        "alterar_extremos": altExtremos,
                        "espelho_primeiro": altExtremos ? parseFloat(document.getElementById('espelho_primeiro').value.replace(',', '.')) : espGeral,
                        "espelho_ultimo": altExtremos ? parseFloat(document.getElementById('espelho_ultimo').value.replace(',', '.')) : espGeral,
                        "n_degraus_1": n_deg1,
                        "n_degraus_2": n_deg2,
                        "n_degraus_3": n_deg3,
                        "tem_patamar_partida": temPatPartida,
                        "patamar_partida": temPatPartida ? parseFloat(document.getElementById('patamar_partida').value.replace(',', '.')) : 0.0,
                        "patamar_intermediario_1": parseFloat(document.getElementById('patamar_int_1').value.replace(',', '.')),
                        "patamar_intermediario_2": parseFloat(document.getElementById('patamar_int_2').value.replace(',', '.')),
                        "tem_patamar_chegada": temPatChegada,
                        "patamar_chegada": temPatChegada ? parseFloat(document.getElementById('patamar_chegada').value.replace(',', '.')) : 0.0,
                        "espessura": parseFloat(document.getElementById('espessura').value.replace(',', '.')),
                        "viga_largura": parseFloat(document.getElementById('viga_largura').value.replace(',', '.')),
                        "viga_altura": parseFloat(document.getElementById('viga_altura').value.replace(',', '.')),
                        "desenhar_planta": document.getElementById('desenhar_planta') ? document.getElementById('desenhar_planta').checked : false,
                        "largura_lance_1": (numLances === 1) ? (parseFloat(document.getElementById('largura_escada_1').value.replace(',', '.')) || 100.0) : (parseFloat(document.getElementById('largura_lance_1').value.replace(',', '.')) || 120.0),
                        "largura_lance_2": (numLances >= 2) ? (parseFloat(document.getElementById('largura_lance_2').value.replace(',', '.')) || 105.5) : 0.0,
                        "largura_lance_3": (numLances === 3) ? (parseFloat(document.getElementById('largura_lance_3').value.replace(',', '.')) || 100.0) : 0.0,
                        "tem_vao_lances": document.getElementById('tem_vao_lances') ? document.getElementById('tem_vao_lances').checked : false,
                        "vao_lances": (numLances >= 2 && document.getElementById('tem_vao_lances') && document.getElementById('tem_vao_lances').checked) ? (parseFloat(document.getElementById('vao_lances').value.replace(',', '.')) || 10.0) : 0.0,
                    }};

                    file.Write(JSON.stringify(dados));
                    file.Close();
                    window.close();
                }} catch (e) {{
                    alert("Erro ao salvar dados: " + e.message);
                }}
            }}
        </script>
    </head>
    <body onload="toggleVao(); togglePlanta(); toggleLances(); togglePatamarPartida(); togglePatamarChegada(); toggleExtremos();">
        <div class="topbar">
            <div class="icon">📐</div>
            <div>
                <h1>Parâmetros da Escada</h1>
                <p>Plugin TQS &#9679 Ediglânthio Samuel Araújo Brandão &#9679 G3 Engenharia</p>
            </div>
        </div>

        <div class="container">
            <div class="img-box">
                <img src="{img_html}" alt="Diagrama da Escada" onerror="this.parentElement.innerHTML='<div style=\'color:#888; text-align:center; padding:40px;\'>Diagrama ilustrativo indisponível</div>'" />
            </div>

            <div class="form-box">
                <div class="card">
                    <h3>Configuração Geral</h3>
                    <div class="campo">
                        <label>Número de Lances:</label>
                        <select id="num_lances" onchange="toggleLances()">
                            <option value="1">1 Lance</option>
                            <option value="2" selected>2 Lances</option>
                            <option value="3">3 Lances</option>
                        </select>
                    </div>
                    <div class="campo"><label>Piso (cm):</label><input type="text" id="piso" value="28"></div>
                    <div class="campo"><label>Espelho Padrão (cm):</label><input type="text" id="espelho" value="17.9"></div>

                    <div class="campo" style="margin-top: 8px;">
                        <label>Alterar espelho do primeiro e último degrau?</label>
                        <input type="checkbox" id="alterar_extremos" onchange="toggleExtremos()">
                    </div>
                    <div id="box_extremos" class="sec-opcional" style="display:none;">
                        <div class="campo"><label>Espelho 1º degrau (cm):</label><input type="text" id="espelho_primeiro" value="17.9"></div>
                        <div class="campo"><label>Espelho último degrau (cm):</label><input type="text" id="espelho_ultimo" value="17.9"></div>
                    </div>
                </div>

                <div class="card">
                    <h3>Degraus por Lance</h3>
                    <div class="campo"><label>Degraus Lance 1:</label><input type="text" id="n_degraus_1" value="8"></div>

                    <div id="box_lance2" class="sec-opcional">
                        <div class="campo"><label>Degraus Lance 2:</label><input type="text" id="n_degraus_2" value="8"></div>
                    </div>

                    <div id="box_lance3" class="sec-opcional" style="display:none; margin-top: 6px;">
                        <div class="campo"><label>Degraus Lance 3:</label><input type="text" id="n_degraus_3" value="8"></div>
                        <div class="campo"><label>2º Patamar Intermediário (cm):</label><input type="text" id="patamar_int_2" value="120"></div>
                    </div>
                </div>

                <div class="card">
                    <h3>Patamares</h3>
                    <div class="campo">
                        <label>Tem patamar de partida?</label>
                        <input type="checkbox" id="tem_patamar_partida" checked onchange="togglePatamarPartida()">
                    </div>
                    <div class="campo" id="box_patamar_partida"><label>Patamar de Partida (cm):</label><input type="text" id="patamar_partida" value="150"></div>
                    <div class="campo" id="campo_pat1"><label>Patamar Intermediário (cm):</label><input type="text" id="patamar_int_1" value="120"></div>
                    <div class="campo">
                        <label>Tem patamar de chegada?</label>
                        <input type="checkbox" id="tem_patamar_chegada" checked onchange="togglePatamarChegada()">
                    </div>
                    <div class="campo" id="box_patamar_chegada"><label>Patamar de Chegada (cm):</label><input type="text" id="patamar_chegada" value="150"></div>
                </div>

                                <div class="card">
                    <h3>Planta da Escada</h3>
                    <div class="campo">
                        <label>Desenhar Planta da Escada?</label>
                        <input type="checkbox" id="desenhar_planta" checked onchange="togglePlanta()">
                    </div>

                    <div id="box_opcoes_planta" class="sec-opcional" style="margin-top: 6px;">
                        <div id="box_planta_1lance" style="display:none;">
                            <div class="campo"><label>Largura da Escada (cm):</label><input type="text" id="largura_escada_1" value="100"></div>
                        </div>

                        <div id="box_planta_multilance">
                            <div class="campo"><label>Largura Lance 1 (cm):</label><input type="text" id="largura_lance_1" value="120"></div>
                            <div class="campo"><label>Largura Lance 2 (cm):</label><input type="text" id="largura_lance_2" value="105.5"></div>
                            <div class="campo" id="box_planta_l3" style="display:none;"><label>Largura Lance 3 (cm):</label><input type="text" id="largura_lance_3" value="100"></div>
                            
                            <div class="campo" style="margin-top: 6px;">
                                <label>Tem vão entre lances?</label>
                                <input type="checkbox" id="tem_vao_lances" onchange="toggleVao()">
                            </div>
                            <div id="box_vao_lances" class="campo" style="display:none;">
                                <label>Vão entre lances (cm):</label>
                                <input type="text" id="vao_lances" value="10">
                            </div>
                        </div>
                    </div>
                </div>
                </div>

                <div class="card">
                    <h3>Laje e Vigas</h3>
                    <div class="campo"><label>Espessura (cm):</label><input type="text" id="espessura" value="15"></div>
                    <div class="campo"><label>Largura da Viga (cm):</label><input type="text" id="viga_largura" value="20"></div>
                    <div class="campo"><label>Altura da Viga (cm):</label><input type="text" id="viga_altura" value="40"></div>
                </div>
            </div>
        </div>
        <div class="btns">
            <button onclick="window.close()">Cancelar</button>
            <button class="btn-gerar" onclick="confirmar()">Gerar Escada</button>
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
# FUNÇÕES AUXILIARES DE GEOMETRIA
# ==============================================================================
def obter_fundo_lance(p1x, p1y, p2x, p2y, espessura):
    """Calcula a reta paralela da face inferior da laje inclinada."""
    xa1, ya1, xa2, ya2 = TQSGeo.ParallelLine(p1x, p1y, p2x, p2y, espessura)
    xb1, yb1, xb2, yb2 = TQSGeo.ParallelLine(p1x, p1y, p2x, p2y, -espessura)
    ym = (p1y + p2y) / 2.0

    if ((ya1 + ya2) / 2.0) < ym:
        return xa1, ya1, xa2, ya2
    return xb1, yb1, xb2, yb2


def calcular_x_no_y(x1, y1, x2, y2, y_alvo):
    """Calcula o X correspondente a um Y em uma reta (x1, y1) -> (x2, y2)."""
    if abs(y2 - y1) > 1e-9:
        t = (y_alvo - y1) / (y2 - y1)
        return x1 + t * (x2 - x1)
    return x1


def calcular_y_no_x(x1, y1, x2, y2, x_alvo):
    """Calcula o Y correspondente a um X em uma reta (x1, y1) -> (x2, y2)."""
    if abs(x2 - x1) > 1e-9:
        t = (x_alvo - x1) / (x2 - x1)
        return y1 + t * (y2 - y1)
    return y1


# ==============================================================================
# FUNÇÃO DE DESENHO DA GEOMETRIA NO TQS
# ==============================================================================
def desenhar_perfil_escada(dwg, x0, y0, dados):
    num_lances = dados.get("num_lances", 2)
    piso = float(dados["piso"])
    espelho = float(dados["espelho"])
    espessura = float(dados["espessura"])
    viga_largura = float(dados["viga_largura"])
    viga_altura = float(dados["viga_altura"])
    largura_escada = float(dados.get("largura_escada", 100.0))

    alterar_extremos = dados.get("alterar_extremos", False)
    if isinstance(alterar_extremos, str):
        alterar_extremos = (alterar_extremos.lower() in ["true", "1", "sim"])

    if alterar_extremos:
        espelho_primeiro = float(dados.get("espelho_primeiro", espelho))
        espelho_ultimo = float(dados.get("espelho_ultimo", espelho))
    else:
        espelho_primeiro = espelho
        espelho_ultimo = espelho

    tem_patamar_partida = dados.get("tem_patamar_partida", True)
    if isinstance(tem_patamar_partida, str):
        tem_patamar_partida = (tem_patamar_partida.lower() in ["true", "1", "sim"])

    tem_patamar_chegada = dados.get("tem_patamar_chegada", True)
    if isinstance(tem_patamar_chegada, str):
        tem_patamar_chegada = (tem_patamar_chegada.lower() in ["true", "1", "sim"])

    patamar_partida = float(dados.get("patamar_partida", 150))
    patamar_int_1 = float(dados.get("patamar_intermediario_1", 120))
    patamar_int_2 = float(dados.get("patamar_intermediario_2", 120))
    patamar_chegada = float(dados.get("patamar_chegada", 150))

    n1 = int(dados["n_degraus_1"])
    n2 = int(dados.get("n_degraus_2", 0))
    n3 = int(dados.get("n_degraus_3", 0))

    draw = dwg.draw

    # --------------------------------------------------------------------------
    # 1. LANCE 1 (NIVEL 241) - Apenas a parte de baixo (Viga Partida, Degraus e Fundo Lance 1)
    # --------------------------------------------------------------------------
    draw.level = 241
    draw.color = -1
    draw.style = -1

    if num_lances == 1:
        if n1 > 1:
            y_topo_l1 = y0 + espelho_primeiro + (n1 - 2) * espelho + espelho_ultimo
        else:
            y_topo_l1 = y0 + espelho_primeiro
    else:
        y_topo_l1 = y0 + espelho_primeiro + (n1 - 1) * espelho

    y_fundo_pat1 = y_topo_l1 - espessura

    # Degraus Lance 1
    x, y = x0, y0
    for i in range(n1):
        if num_lances > 1 and i == n1 - 1:
            if y < y_fundo_pat1:
                draw.Line(x, y, x, y_fundo_pat1)
            y = y_topo_l1
        else:
            if i == 0:
                h_esp = espelho_primeiro
            elif num_lances == 1 and i == n1 - 1:
                h_esp = espelho_ultimo
            else:
                h_esp = espelho

            draw.Line(x, y, x, y + h_esp)
            y += h_esp

        if i < n1 - 1:
            draw.Line(x, y, x + piso, y)
            x += piso

    x_inicio_l2 = x

    # Linha inclinada paralela de fundo do Lance 1
    p1x, p1y = x0 + piso, y0 + espelho_primeiro
    p2x, p2y = x0 + (n1 - 1) * piso, y0 + espelho_primeiro + (n1 - 2) * espelho if n1 > 1 else (p1x + piso, p1y + espelho)
    f1_x1, f1_y1, f1_x2, f1_y2 = obter_fundo_lance(p1x, p1y, p2x, p2y, espessura)

    if tem_patamar_partida:
        x_partida = x0 - patamar_partida
        y_partida = y0
        draw.Line(x_partida, y_partida, x0, y0)

        y_base_partida = y0 - espessura
        x_base_partida_fim = calcular_x_no_y(f1_x1, f1_y1, f1_x2, f1_y2, y_base_partida)
        draw.Line(x_partida, y_base_partida, x_base_partida_fim, y_base_partida)

        # Viga de Partida
        x_viga_s_ini = x_partida - viga_largura
        x_viga_s_meio = x_partida
        y_viga_s_topo = y0
        y_viga_s_base = y0 - viga_altura
        y_viga_s_corte = y0 - espessura

        draw.Line(x_viga_s_ini, y_viga_s_topo, x_viga_s_ini, y_viga_s_base)
        draw.Line(x_viga_s_ini, y_viga_s_base, x_viga_s_meio, y_viga_s_base)
        draw.Line(x_viga_s_meio, y_viga_s_base, x_viga_s_meio, y_viga_s_corte)
        draw.Line(x_viga_s_ini, y_viga_s_topo, x_partida, y_viga_s_topo)

        x_fundo_l1_ini = x_base_partida_fim
        y_fundo_l1_ini = y_base_partida
    else:
        x_viga_s_ini = x0 - viga_largura
        y_viga_s_topo = y0
        y_viga_s_base = y0 - viga_altura
        y_fundo_no_x0 = calcular_y_no_x(f1_x1, f1_y1, f1_x2, f1_y2, x0)

        draw.Line(x_viga_s_ini, y_viga_s_topo, x0, y_viga_s_topo)
        draw.Line(x_viga_s_ini, y_viga_s_topo, x_viga_s_ini, y_viga_s_base)
        draw.Line(x_viga_s_ini, y_viga_s_base, x0, y_viga_s_base)
        draw.Line(x0, y_viga_s_base, x0, y_fundo_no_x0)

        x_fundo_l1_ini = x0
        y_fundo_l1_ini = y_fundo_no_x0

    # Linha inclinada de fundo do Lance 1 (NIVEL 241)
    x_fundo_l1_fim = calcular_x_no_y(f1_x1, f1_y1, f1_x2, f1_y2, y_fundo_pat1)
    draw.Line(x_fundo_l1_ini, y_fundo_l1_ini, x_fundo_l1_fim, y_fundo_pat1)

    # Caso seja 1 lance apenas
    if num_lances == 1:
        x_fim_pat1 = x_inicio_l2 + (patamar_chegada if tem_patamar_chegada else 0.0)
        x_viga_p1_ext = x_fim_pat1 + viga_largura
        if tem_patamar_chegada:
            draw.Line(x_inicio_l2, y_topo_l1, x_fim_pat1, y_topo_l1)
            draw.Line(x_fundo_l1_fim, y_fundo_pat1, x_fim_pat1, y_fundo_pat1)
            draw.Line(x_fim_pat1, y_topo_l1, x_viga_p1_ext, y_topo_l1)
            draw.Line(x_viga_p1_ext, y_topo_l1, x_viga_p1_ext, y_topo_l1 - viga_altura)
            draw.Line(x_viga_p1_ext, y_topo_l1 - viga_altura, x_fim_pat1, y_topo_l1 - viga_altura)
            draw.Line(x_fim_pat1, y_topo_l1 - viga_altura, x_fim_pat1, y_fundo_pat1)
        else:
            y_fundo_no_xtopo = calcular_y_no_x(f1_x1, f1_y1, f1_x2, f1_y2, x_inicio_l2)
            draw.Line(x_inicio_l2, y_topo_l1, x_viga_p1_ext, y_topo_l1)
            draw.Line(x_viga_p1_ext, y_topo_l1, x_viga_c_ext, y_topo_l1 - viga_altura)
            draw.Line(x_viga_p1_ext, y_topo_l1 - viga_altura, x_inicio_l2, y_topo_l1 - viga_altura)
            draw.Line(x_inicio_l2, y_topo_l1 - viga_altura, x_inicio_l2, y_fundo_no_xtopo)
            draw.Line(x_fundo_l1_ini, y_fundo_l1_ini, x_inicio_l2, y_fundo_no_xtopo)
        return

    # --------------------------------------------------------------------------
    # 2. LANCE 2 (NIVEL 242) - Patamar Intermediario, Degraus Lance 2, Fundo e Chegada
    # --------------------------------------------------------------------------
    draw.level = 242
    draw.color = -1
    draw.style = -1

    # Patamar Intermediario 1 e Viga Direita (NIVEL 242)
    x_fim_pat1 = x_inicio_l2 + patamar_int_1
    x_viga_p1_ext = x_fim_pat1 + viga_largura

    draw.Line(x_inicio_l2, y_topo_l1, x_fim_pat1, y_topo_l1)
    draw.Line(x_fim_pat1, y_topo_l1, x_viga_p1_ext, y_topo_l1)
    draw.Line(x_viga_p1_ext, y_topo_l1, x_viga_p1_ext, y_topo_l1 - viga_altura)
    draw.Line(x_viga_p1_ext, y_topo_l1 - viga_altura, x_fim_pat1, y_topo_l1 - viga_altura)
    draw.Line(x_fim_pat1, y_topo_l1 - viga_altura, x_fim_pat1, y_fundo_pat1)

    x, y = x_inicio_l2, y_topo_l1
    if num_lances == 2:
        if n2 > 1:
            y_topo_l2 = y_topo_l1 + (n2 - 1) * espelho + espelho_ultimo
        else:
            y_topo_l2 = y_topo_l1 + (espelho_ultimo if n2 == 1 else 0)
    else:
        y_topo_l2 = y_topo_l1 + n2 * espelho

    y_fundo_pat2 = y_topo_l2 - espessura

    # Degraus Lance 2
    for i in range(n2):
        if num_lances == 3 and i == n2 - 1:
            if y < y_fundo_pat2:
                draw.Line(x, y, x, y_fundo_pat2)
            y = y_topo_l2
        else:
            if num_lances == 2 and i == n2 - 1:
                h_esp = espelho_ultimo
            else:
                h_esp = espelho

            draw.Line(x, y, x, y + h_esp)
            y += h_esp

        if i < n2 - 1:
            draw.Line(x, y, x - piso, y)
            x -= piso

    x_topo_l2 = x

    # Linha paralela de fundo do Lance 2
    p2_1x, p2_1y = x_inicio_l2 - piso, y_topo_l1 + espelho
    p2_2x, p2_2y = x_inicio_l2 - (n2 - 1) * piso, y_topo_l1 + (n2 - 1) * espelho if n2 > 1 else (p2_1x - piso, p2_1y + espelho)
    f2_x1, f2_y1, f2_x2, f2_y2 = obter_fundo_lance(p2_1x, p2_1y, p2_2x, p2_2y, espessura)

    # O Fundo do Lance 2 desce ate a cota de baixo do patamar (y_fundo_pat1)
    x_fundo_l2_no_pat1 = calcular_x_no_y(f2_x1, f2_y1, f2_x2, f2_y2, y_fundo_pat1)

    # Linha de BAIXO do patamar 1 (Nivel 242)
    draw.Line(x_fundo_l2_no_pat1, y_fundo_pat1, x_fim_pat1, y_fundo_pat1)

    # ==========================================================================
    # CASO 2 LANCES: Finaliza o Lance 2 no patamar de chegada superior a esquerda
    # ==========================================================================
    if num_lances == 2:
        if tem_patamar_chegada:
            x_fim_chegada = x_topo_l2 - patamar_chegada
            draw.Line(x_topo_l2, y_topo_l2, x_fim_chegada, y_topo_l2)

            y_fundo_chegada = y_topo_l2 - espessura
            x_fundo_l2_fim = calcular_x_no_y(f2_x1, f2_y1, f2_x2, f2_y2, y_fundo_chegada)

            draw.Line(x_fundo_l2_no_pat1, y_fundo_pat1, x_fundo_l2_fim, y_fundo_chegada)
            draw.Line(x_fundo_l2_fim, y_fundo_chegada, x_fim_chegada, y_fundo_chegada)

            # Viga de Chegada (Lado Esquerdo Superior)
            x_viga_c_ext = x_fim_chegada - viga_largura
            draw.Line(x_fim_chegada, y_topo_l2, x_viga_c_ext, y_topo_l2)
            draw.Line(x_viga_c_ext, y_topo_l2, x_viga_c_ext, y_topo_l2 - viga_altura)
            draw.Line(x_viga_c_ext, y_topo_l2 - viga_altura, x_fim_chegada, y_topo_l2 - viga_altura)
            draw.Line(x_fim_chegada, y_topo_l2 - viga_altura, x_fim_chegada, y_fundo_chegada)
        else:
            x_viga_c_ext = x_topo_l2 - viga_largura
            y_fundo_no_xtopo2 = calcular_y_no_x(f2_x1, f2_y1, f2_x2, f2_y2, x_topo_l2)

            draw.Line(x_topo_l2, y_topo_l2, x_viga_c_ext, y_topo_l2)
            draw.Line(x_viga_c_ext, y_topo_l2, x_viga_c_ext, y_topo_l2 - viga_altura)
            draw.Line(x_viga_c_ext, y_topo_l2 - viga_altura, x_topo_l2, y_topo_l2 - viga_altura)
            draw.Line(x_topo_l2, y_topo_l2 - viga_altura, x_topo_l2, y_fundo_no_xtopo2)
            draw.Line(x_fundo_l2_no_pat1, y_fundo_pat1, x_topo_l2, y_fundo_no_xtopo2)
        return

    # ==========================================================================
    # CASO 3 LANCES: 2º Patamar Intermediario (a esquerda) e Lance 3 (+X, +Y)
    # ==========================================================================
    x_inicio_l3 = x_topo_l2
    x, y = x_inicio_l3, y_topo_l2

    if n3 > 1:
        y_topo_l3 = y_topo_l2 + (n3 - 1) * espelho + espelho_ultimo
    else:
        y_topo_l3 = y_topo_l2 + (espelho_ultimo if n3 == 1 else 0)

    for i in range(n3):
        if i == n3 - 1:
            h_esp = espelho_ultimo
        else:
            h_esp = espelho

        draw.Line(x, y, x, y + h_esp)
        y += h_esp
        if i < n3 - 1:
            draw.Line(x, y, x + piso, y)
            x += piso

    x_topo_l3 = x

    p3_1x, p3_1y = x_inicio_l3 + piso, y_topo_l2 + espelho
    p3_2x, p3_2y = x_inicio_l3 + (n3 - 1) * piso, y_topo_l2 + (n3 - 1) * espelho if n3 > 1 else (p3_1x + piso, p3_1y + espelho)
    f3_x1, f3_y1, f3_x2, f3_y2 = obter_fundo_lance(p3_1x, p3_1y, p3_2x, p3_2y, espessura)

    x_fim_pat2 = x_inicio_l3 - patamar_int_2

    draw.Line(x_inicio_l3, y_topo_l2, x_fim_pat2, y_topo_l2)

    x_fundo_l2_fim = calcular_x_no_y(f2_x1, f2_y1, f2_x2, f2_y2, y_fundo_pat2)
    draw.Line(x_fundo_l2_no_pat1, y_fundo_pat1, x_fundo_l2_fim, y_fundo_pat2)

    x_fundo_l3_no_pat2 = calcular_x_no_y(f3_x1, f3_y1, f3_x2, f3_y2, y_fundo_pat2)
    draw.Line(x_fim_pat2, y_fundo_pat2, x_fundo_l3_no_pat2, y_fundo_pat2)

    x_viga_p2_ext = x_fim_pat2 - viga_largura
    draw.Line(x_fim_pat2, y_topo_l2, x_viga_p2_ext, y_topo_l2)
    draw.Line(x_viga_p2_ext, y_topo_l2, x_viga_p2_ext, y_topo_l2 - viga_altura)
    draw.Line(x_viga_p2_ext, y_topo_l2 - viga_altura, x_fim_pat2, y_topo_l2 - viga_altura)
    draw.Line(x_fim_pat2, y_topo_l2 - viga_altura, x_fim_pat2, y_fundo_pat2)

    # --------------------------------------------------------------------------
    # PATAMAR DE CHEGADA SUPERIOR (LADO DIREITO)
    # --------------------------------------------------------------------------
    if tem_patamar_chegada:
        x_fim_chegada = x_topo_l3 + patamar_chegada
        draw.Line(x_topo_l3, y_topo_l3, x_fim_chegada, y_topo_l3)

        y_fundo_chegada = y_topo_l3 - espessura
        x_fundo_l3_fim = calcular_x_no_y(f3_x1, f3_y1, f3_x2, f3_y2, y_fundo_chegada)

        draw.Line(x_fundo_l3_no_pat2, y_fundo_pat2, x_fundo_l3_fim, y_fundo_chegada)
        draw.Line(x_fundo_l3_fim, y_fundo_chegada, x_fim_chegada, y_fundo_chegada)

        x_viga_c_ext = x_fim_chegada + viga_largura
        draw.Line(x_fim_chegada, y_topo_l3, x_viga_c_ext, y_topo_l3)
        draw.Line(x_viga_c_ext, y_topo_l3, x_viga_c_ext, y_topo_l3 - viga_altura)
        draw.Line(x_viga_c_ext, y_topo_l3 - viga_altura, x_fim_chegada, y_topo_l3 - viga_altura)
        draw.Line(x_fim_chegada, y_topo_l3 - viga_altura, x_fim_chegada, y_fundo_chegada)
    else:
        x_viga_c_ext = x_topo_l3 + viga_largura
        y_fundo_no_xtopo3 = calcular_y_no_x(f3_x1, f3_y1, f3_x2, f3_y2, x_topo_l3)

        draw.Line(x_topo_l3, y_topo_l3, x_viga_c_ext, y_topo_l3)
        draw.Line(x_viga_c_ext, y_topo_l3, x_viga_c_ext, y_topo_l3 - viga_altura)
        draw.Line(x_viga_c_ext, y_topo_l3 - viga_altura, x_topo_l3, y_topo_l3 - viga_altura)
        draw.Line(x_topo_l3, y_topo_l3 - viga_altura, x_topo_l3, y_fundo_no_xtopo3)
        draw.Line(x_fundo_l3_no_pat2, y_fundo_pat2, x_topo_l3, y_fundo_no_xtopo3)


# ==============================================================================
# DESENHO DA PLANTA DA ESCADA
# ==============================================================================
def desenhar_planta_escada(dwg, x0, y0, dados):
    """Desenha a vista em planta (forma) da escada com cotas completas, vigas e anotacoes."""
    num_lances = dados.get("num_lances", 2)
    piso = float(dados["piso"])
    viga_largura = float(dados["viga_largura"])
    viga_altura = float(dados["viga_altura"])

    largura_l1 = float(dados.get("largura_lance_1", 120.0))
    largura_l2 = float(dados.get("largura_lance_2", 105.5))
    largura_l3 = float(dados.get("largura_lance_3", 100.0))
    vao_lances = float(dados.get("vao_lances", 0.0))

    tem_patamar_partida = dados.get("tem_patamar_partida", True)
    if isinstance(tem_patamar_partida, str):
        tem_patamar_partida = (tem_patamar_partida.lower() in ["true", "1", "sim"])

    tem_patamar_chegada = dados.get("tem_patamar_chegada", True)
    if isinstance(tem_patamar_chegada, str):
        tem_patamar_chegada = (tem_patamar_chegada.lower() in ["true", "1", "sim"])

    patamar_partida = float(dados.get("patamar_partida", 150))
    patamar_int_1 = float(dados.get("patamar_intermediario_1", 120))
    patamar_int_2 = float(dados.get("patamar_intermediario_2", 120))
    patamar_chegada = float(dados.get("patamar_chegada", 150))

    n1 = int(dados["n_degraus_1"])
    n2 = int(dados.get("n_degraus_2", 0))
    n3 = int(dados.get("n_degraus_3", 0))

    draw = dwg.draw
    draw.level = 242
    draw.color = -1
    draw.style = -1  # Verde para forma

    dist_offset = viga_altura + 290.0
    y_planta_top = y0 - dist_offset

    if num_lances == 1:
        # ======================================================================
        # PLANTA: 1 LANCE
        # ======================================================================
        y_min_int = y_planta_top - largura_l1
        y_max_int = y_planta_top
        y_min_ext = y_min_int - viga_largura
        y_max_ext = y_max_int + viga_largura

        x_deg_ini = x0
        x_deg_fim = x0 + (n1 - 1) * piso

        pat_esq = patamar_partida if tem_patamar_partida else 0.0
        pat_dir = patamar_chegada if tem_patamar_chegada else 0.0

        x_min_int = x_deg_ini - pat_esq
        x_min_ext = x_min_int - viga_largura
        x_max_int = x_deg_fim + pat_dir
        x_max_ext = x_max_int + viga_largura

        # Retangulo Externo (Caixa de Escada / Vigas)
        draw.Line(x_min_ext, y_min_ext, x_max_ext, y_min_ext)
        draw.Line(x_max_ext, y_min_ext, x_max_ext, y_max_ext)
        draw.Line(x_max_ext, y_max_ext, x_min_ext, y_max_ext)
        draw.Line(x_min_ext, y_max_ext, x_min_ext, y_min_ext)

        # Retangulo Interno
        draw.Line(x_min_int, y_min_int, x_max_int, y_min_int)
        draw.Line(x_max_int, y_min_int, x_max_int, y_max_int)
        draw.Line(x_max_int, y_max_int, x_min_int, y_max_int)
        draw.Line(x_min_int, y_max_int, x_min_int, y_min_int)

        # Linhas divisorias de patamares
        if tem_patamar_partida:
            draw.Line(x_deg_ini, y_min_int, x_deg_ini, y_max_int)
        if tem_patamar_chegada:
            draw.Line(x_deg_fim, y_min_int, x_deg_fim, y_max_int)

        # Degraus
        for i in range(1, n1 - 1):
            x_deg = x_deg_ini + i * piso
            draw.Line(x_deg, y_min_int, x_deg, y_max_int)

        # Numeracao dos degraus
        draw.color = 7  # Branco/Texto
        for i in range(n1 - 1):
            x_c = x_deg_ini + (i + 0.5) * piso
            y_c = y_min_int + largura_l1 / 2.0
            draw.Text(x_c - 4.0, y_c - 4.0, 8.0, 0.0, f"{i + 1:02d}")

        # Seta de fluxo
        draw.color = 4  # Azul / Ciano
        x_seta_start = x_deg_ini + piso * 0.5
        x_seta_end = x_deg_fim + (pat_dir * 0.5 if tem_patamar_chegada else 0.0)
        y_seta = y_min_int + largura_l1 / 2.0
        draw.Line(x_seta_start, y_seta, x_seta_end, y_seta)
        draw.Line(x_seta_end, y_seta, x_seta_end - 10.0, y_seta + 5.0)
        draw.Line(x_seta_end, y_seta, x_seta_end - 10.0, y_seta - 5.0)
        draw.Text(x_seta_start + 10.0, y_seta + 6.0, 8.0, 0.0, "DESCE")

        # COTAS
        y_cota_top1 = y_max_ext + 35.0
        y_cota_top2 = y_max_ext + 70.0

        # Cotas parciais
        dwg.dim.DimHorizontal(x_min_ext, y_max_ext, x_min_int, y_max_ext, x_min_ext, y_cota_top1)
        if tem_patamar_partida:
            dwg.dim.DimHorizontal(x_min_int, y_max_ext, x_deg_ini, y_max_ext, x_min_int, y_cota_top1)

        for i in range(n1 - 1):
            x_a = x_deg_ini + i * piso
            x_b = x_a + piso
            dwg.dim.DimHorizontal(x_a, y_max_ext, x_b, y_max_ext, x_a, y_cota_top1)

        if tem_patamar_chegada:
            dwg.dim.DimHorizontal(x_deg_fim, y_max_ext, x_max_int, y_max_ext, x_deg_fim, y_cota_top1)
        dwg.dim.DimHorizontal(x_max_int, y_max_ext, x_max_ext, y_max_ext, x_max_int, y_cota_top1)

        # Cota total horizontal
        dwg.dim.DimHorizontal(x_min_ext, y_max_ext, x_max_ext, y_max_ext, x_min_ext, y_cota_top2)

        # Cotas verticais (largura)
        x_cota_dir1 = x_max_ext + 35.0
        x_cota_dir2 = x_max_ext + 70.0
        dwg.dim.DimVertical(x_max_ext, y_min_ext, x_max_ext, y_min_int, x_cota_dir1, y_min_ext)
        dwg.dim.DimVertical(x_max_ext, y_min_int, x_max_ext, y_max_int, x_cota_dir1, y_min_int)
        dwg.dim.DimVertical(x_max_ext, y_max_int, x_max_ext, y_max_ext, x_cota_dir1, y_max_int)
        dwg.dim.DimVertical(x_max_ext, y_min_ext, x_max_ext, y_max_ext, x_cota_dir2, y_min_ext)

    elif num_lances == 2:
        # ======================================================================
        # PLANTA: 2 LANCES (Escada em U Simetrica com Vigas Envolventes)
        # ======================================================================
        largura_total = largura_l1 + vao_lances + largura_l2
        y_min_int = y_planta_top - largura_total
        y_max_int = y_planta_top
        y_min_ext = y_min_int - viga_largura
        y_max_ext = y_max_int + viga_largura

        y_l1_topo = y_min_int + largura_l1
        y_l2_base = y_l1_topo + vao_lances
        y_l2_topo = y_max_int

        # Degraus
        num_deg_flight = max(n1 - 1, n2 - 1)
        x_deg_ini = x0
        x_deg_fim = x0 + num_deg_flight * piso

        # Patamares
        pat_esq = max(patamar_partida if tem_patamar_partida else 0.0, patamar_chegada if tem_patamar_chegada else 0.0)
        pat_dir = patamar_int_1

        x_min_int = x_deg_ini - pat_esq
        x_min_ext = x_min_int - viga_largura

        x_max_int = x_deg_fim + pat_dir
        x_max_ext = x_max_int + viga_largura

        # ----------------------------------------------------------------------
        # 1. LINHAS DE FORMA (Nivel 242, Cor por nivel, Estilo -1)
        # ----------------------------------------------------------------------
        draw.level = 242
        draw.color = -1
        draw.style = -1

        # Retangulo Externo Completo (Vigas Perimetrais da Caixa de Escada)
        draw.Line(x_min_ext, y_min_ext, x_max_ext, y_min_ext)
        draw.Line(x_max_ext, y_min_ext, x_max_ext, y_max_ext)
        draw.Line(x_max_ext, y_max_ext, x_min_ext, y_max_ext)
        draw.Line(x_min_ext, y_max_ext, x_min_ext, y_min_ext)

        # Retangulo Interno Completo (Borda Interna das Vigas)
        draw.Line(x_min_int, y_min_int, x_max_int, y_min_int)
        draw.Line(x_max_int, y_min_int, x_max_int, y_max_int)
        draw.Line(x_max_int, y_max_int, x_min_int, y_max_int)
        draw.Line(x_min_int, y_max_int, x_min_int, y_min_int)

        # Divisorias verticais do Patamar Esquerdo (com os lances)
        draw.Line(x_deg_ini, y_min_int, x_deg_ini, y_l1_topo)
        draw.Line(x_deg_ini, y_l2_base, x_deg_ini, y_max_int)

        # Divisorias verticais do Patamar Direito (com os lances)
        draw.Line(x_deg_fim, y_min_int, x_deg_fim, y_l1_topo)
        draw.Line(x_deg_fim, y_l2_base, x_deg_fim, y_max_int)

        # Vao Central entre Lances
        draw.Line(x_deg_ini, y_l1_topo, x_deg_fim, y_l1_topo)
        if vao_lances > 0:
            draw.Line(x_deg_ini, y_l2_base, x_deg_fim, y_l2_base)
            draw.Line(x_deg_ini, y_l1_topo, x_deg_ini, y_l2_base)
            draw.Line(x_deg_fim, y_l1_topo, x_deg_fim, y_l2_base)

        # Degraus Lance 1 (Inferior)
        for i in range(1, n1 - 1):
            x_deg = x_deg_ini + i * piso
            draw.Line(x_deg, y_min_int, x_deg, y_l1_topo)

        # Degraus Lance 2 (Superior)
        for j in range(1, n2 - 1):
            x_deg = x_deg_ini + j * piso
            draw.Line(x_deg, y_l2_base, x_deg, y_max_int)

        # ----------------------------------------------------------------------
        # 2. NUMERACAO DOS DEGRAUS E TEXTOS
        # ----------------------------------------------------------------------
        draw.color = 7  # Branco/Texto

        # Numeracao Lance 1 (01, 02, 03... da esquerda para a direita)
        for i in range(n1 - 1):
            x_c = x_deg_ini + (i + 0.5) * piso
            y_c = y_min_int + largura_l1 / 2.0
            draw.Text(x_c - 4.0, y_c - 4.0, 8.0, 0.0, f"{i + 1:02d}")

        # Numeracao Lance 2 (15, 14, 13... da esquerda para a direita)
        for j in range(n2 - 1):
            x_c = x_deg_ini + (j + 0.5) * piso
            y_c = y_l2_base + largura_l2 / 2.0
            num_deg = (n1 + (n2 - 1) - 1) - j
            draw.Text(x_c - 4.0, y_c - 4.0, 8.0, 0.0, f"{num_deg:02d}")

        # Seta e Linha de Fluxo
        draw.color = 4  # Ciano/Azul
        y_m1 = y_min_int + largura_l1 / 2.0
        y_m2 = y_l2_base + largura_l2 / 2.0
        x_m_start = x_deg_ini + piso * 0.5
        x_m_pat = x_deg_fim + pat_dir * 0.5
        x_m_arr = x_min_int + (pat_esq * 0.5 if pat_esq > 0 else -20.0)

        draw.Line(x_m_start, y_m1, x_m_pat, y_m1)
        draw.Line(x_m_pat, y_m1, x_m_pat, y_m2)
        draw.Line(x_m_pat, y_m2, x_m_arr, y_m2)

        # Seta apontando para a esquerda na chegada
        draw.Line(x_m_arr, y_m2, x_m_arr + 12.0, y_m2 + 6.0)
        draw.Line(x_m_arr, y_m2, x_m_arr + 12.0, y_m2 - 6.0)

        # Texto DESCE
        draw.Text(x_deg_ini + piso * 0.8, y_m1 + 6.0, 8.0, 0.0, "DESCE")

        # ----------------------------------------------------------------------
        # 3. LINHAS DE COTA (dwg.dim)
        # ----------------------------------------------------------------------
        y_cota_top1 = y_max_ext + 35.0
        y_cota_top2 = y_max_ext + 70.0

        # Linha 1 de Cotas Superiores (Parciais)
        # Viga Esquerda
        dwg.dim.DimHorizontal(x_min_ext, y_max_ext, x_min_int, y_max_ext, x_min_ext, y_cota_top1)

        # Patamar Esquerdo
        if pat_esq > 0:
            dwg.dim.DimHorizontal(x_min_int, y_max_ext, x_deg_ini, y_max_ext, x_min_int, y_cota_top1)

        # Degraus
        for i in range(num_deg_flight):
            x_a = x_deg_ini + i * piso
            x_b = x_a + piso
            dwg.dim.DimHorizontal(x_a, y_max_ext, x_b, y_max_ext, x_a, y_cota_top1)

        # Patamar Direito (Intermediario 1)
        dwg.dim.DimHorizontal(x_deg_fim, y_max_ext, x_max_int, y_max_ext, x_deg_fim, y_cota_top1)

        # Viga Direita
        dwg.dim.DimHorizontal(x_max_int, y_max_ext, x_max_ext, y_max_ext, x_max_int, y_cota_top1)

        # Linha 2 de Cotas Superiores (Cota Total da Caixa da Escada)
        dwg.dim.DimHorizontal(x_min_ext, y_max_ext, x_max_ext, y_max_ext, x_min_ext, y_cota_top2)

        # Cotas Verticais a Direita
        x_cota_dir1 = x_max_ext + 35.0
        x_cota_dir2 = x_max_ext + 70.0

        # Viga Inferior
        dwg.dim.DimVertical(x_max_ext, y_min_ext, x_max_ext, y_min_int, x_cota_dir1, y_min_ext)

        # Lance 1
        dwg.dim.DimVertical(x_max_ext, y_min_int, x_max_ext, y_l1_topo, x_cota_dir1, y_min_int)

        # Vao entre Lances
        if vao_lances > 0:
            dwg.dim.DimVertical(x_max_ext, y_l1_topo, x_max_ext, y_l2_base, x_cota_dir1, y_l1_topo)

        # Lance 2
        dwg.dim.DimVertical(x_max_ext, y_l2_base, x_max_ext, y_max_int, x_cota_dir1, y_l2_base)

        # Viga Superior
        dwg.dim.DimVertical(x_max_ext, y_max_int, x_max_ext, y_max_ext, x_cota_dir1, y_max_int)

        # Cota Vertical Total
        dwg.dim.DimVertical(x_max_ext, y_min_ext, x_max_ext, y_max_ext, x_cota_dir2, y_min_ext)

    elif num_lances == 3:
        # ======================================================================
        # PLANTA: 3 LANCES
        # ======================================================================
        largura_total = largura_l1 + vao_lances + largura_l2 + vao_lances + largura_l3
        y_min_int = y_planta_top - largura_total
        y_max_int = y_planta_top
        y_min_ext = y_min_int - viga_largura
        y_max_ext = y_max_int + viga_largura

        x_deg_ini = x0
        num_deg_max = max(n1 - 1, n2 - 1, n3 - 1)
        x_deg_fim = x0 + num_deg_max * piso

        pat_esq = max(patamar_partida if tem_patamar_partida else 0.0, patamar_int_2)
        pat_dir = max(patamar_int_1, patamar_chegada if tem_patamar_chegada else 0.0)

        x_min_int = x_deg_ini - pat_esq
        x_min_ext = x_min_int - viga_largura
        x_max_int = x_deg_fim + pat_dir
        x_max_ext = x_max_int + viga_largura

        # Retangulo Externo
        draw.Line(x_min_ext, y_min_ext, x_max_ext, y_min_ext)
        draw.Line(x_max_ext, y_min_ext, x_max_ext, y_max_ext)
        draw.Line(x_max_ext, y_max_ext, x_min_ext, y_max_ext)
        draw.Line(x_min_ext, y_max_ext, x_min_ext, y_min_ext)

        # Retangulo Interno
        draw.Line(x_min_int, y_min_int, x_max_int, y_min_int)
        draw.Line(x_max_int, y_min_int, x_max_int, y_max_int)
        draw.Line(x_max_int, y_max_int, x_min_int, y_max_int)
        draw.Line(x_min_int, y_max_int, x_min_int, y_min_int)

        y_l1_topo = y_min_int + largura_l1
        y_l2_base = y_l1_topo + vao_lances
        y_l2_topo = y_l2_base + largura_l2
        y_l3_base = y_l2_topo + vao_lances

        draw.Line(x_deg_ini, y_min_int, x_deg_ini, y_l1_topo)
        draw.Line(x_deg_ini, y_l2_base, x_deg_ini, y_l2_topo)
        draw.Line(x_deg_ini, y_l3_base, x_deg_ini, y_max_int)

        draw.Line(x_deg_fim, y_min_int, x_deg_fim, y_l1_topo)
        draw.Line(x_deg_fim, y_l2_base, x_deg_fim, y_l2_topo)
        draw.Line(x_deg_fim, y_l3_base, x_deg_fim, y_max_int)

        for i in range(1, n1 - 1):
            x_deg = x_deg_ini + i * piso
            draw.Line(x_deg, y_min_int, x_deg, y_l1_topo)
        for j in range(1, n2 - 1):
            x_deg = x_deg_ini + j * piso
            draw.Line(x_deg, y_l2_base, x_deg, y_l2_topo)
        for k in range(1, n3 - 1):
            x_deg = x_deg_ini + k * piso
            draw.Line(x_deg, y_l3_base, x_deg, y_max_int)

        # COTAS
        y_cota_top1 = y_max_ext + 35.0
        y_cota_top2 = y_max_ext + 70.0

        dwg.dim.DimHorizontal(x_min_ext, y_max_ext, x_min_int, y_max_ext, x_min_ext, y_cota_top1)
        if pat_esq > 0:
            dwg.dim.DimHorizontal(x_min_int, y_max_ext, x_deg_ini, y_max_ext, x_min_int, y_cota_top1)
        for i in range(num_deg_max):
            x_a = x_deg_ini + i * piso
            x_b = x_a + piso
            dwg.dim.DimHorizontal(x_a, y_max_ext, x_b, y_max_ext, x_a, y_cota_top1)
        if pat_dir > 0:
            dwg.dim.DimHorizontal(x_deg_fim, y_max_ext, x_max_int, y_max_ext, x_deg_fim, y_cota_top1)
        dwg.dim.DimHorizontal(x_max_int, y_max_ext, x_max_ext, y_max_ext, x_max_int, y_cota_top1)

        dwg.dim.DimHorizontal(x_min_ext, y_max_ext, x_max_ext, y_max_ext, x_min_ext, y_cota_top2)

        x_cota_dir1 = x_max_ext + 35.0
        x_cota_dir2 = x_max_ext + 70.0
        dwg.dim.DimVertical(x_max_ext, y_min_ext, x_max_ext, y_min_int, x_cota_dir1, y_min_ext)
        dwg.dim.DimVertical(x_max_ext, y_min_int, x_max_ext, y_l1_topo, x_cota_dir1, y_min_int)
        if vao_lances > 0:
            dwg.dim.DimVertical(x_max_ext, y_l1_topo, x_max_ext, y_l2_base, x_cota_dir1, y_l1_topo)
        dwg.dim.DimVertical(x_max_ext, y_l2_base, x_max_ext, y_l2_topo, x_cota_dir1, y_l2_base)
        if vao_lances > 0:
            dwg.dim.DimVertical(x_max_ext, y_l2_topo, x_max_ext, y_l3_base, x_cota_dir1, y_l2_topo)
        dwg.dim.DimVertical(x_max_ext, y_l3_base, x_max_ext, y_max_int, x_cota_dir1, y_l3_base)
        dwg.dim.DimVertical(x_max_ext, y_max_int, x_max_ext, y_max_ext, x_cota_dir1, y_max_int)

        dwg.dim.DimVertical(x_max_ext, y_min_ext, x_max_ext, y_max_ext, x_cota_dir2, y_min_ext)



# ==============================================================================
# DESENHO DO CORTE DO 1º LANCE ISOLADO (EMBAIXO DA PLANTA)
# ==============================================================================

# ==============================================================================
# DESENHO DO SIMBOLO/TITULO DO CORTE (CORTE A-A / ESCALA)
# ==============================================================================
def desenhar_indicacao_corte(dwg, x_pos, y_pos, titulo="CORTE A-A", escala="ESCALA: 1/20"):
    """Desenha o rotulo padrao de corte com circulo duplo (niveis 243 e 255), titulo (245), linha e texto (243)."""
    draw = dwg.draw

    raio_ext = 13.5
    raio_int = 12.0
    xc = x_pos
    yc = y_pos

    # 1. Circulo Interno (Nivel 255)
    draw.level = 255
    draw.color = -1
    draw.style = -1
    draw.Circle(xc, yc, raio_int)

    # 2. Circulo Externo (Nivel 243)
    draw.level = 243
    draw.color = -1
    draw.style = -1
    draw.Circle(xc, yc, raio_ext)

    # 3. Linha divisoria que toca no circulo (Nivel 243)
    x_ini_linha = xc + raio_ext
    x_texto = xc + raio_ext + 10.0
    largura_linha = max(len(titulo) * 11.5, 115.0)
    x_fim_linha = x_texto + largura_linha

    draw.level = 243
    draw.color = -1
    draw.style = -1
    draw.Line(x_ini_linha, yc, x_fim_linha, yc)

    # 4. Titulo "CORTE A-A" (Nivel 245)
    draw.level = 245
    draw.color = -1
    draw.style = -1
    draw.Text(x_texto, yc + 3.0, 13.0, 0.0, titulo)

    # 5. Texto da Escala "ESCALA: 1/20" (Nivel 243)
    draw.level = 243
    draw.color = -1
    draw.style = -1
    draw.Text(x_texto, yc - 12.0, 8.5, 0.0, escala)

def desenhar_perfil_lance1_isolado(dwg, x0, y0, dados):
    """Desenha o corte do primeiro lance isolado (com patamar intermediario e viga superior a direita)."""
    piso = float(dados["piso"])
    espelho = float(dados["espelho"])
    espessura = float(dados["espessura"])
    viga_largura = float(dados["viga_largura"])
    viga_altura = float(dados["viga_altura"])

    alterar_extremos = dados.get("alterar_extremos", False)
    if isinstance(alterar_extremos, str):
        alterar_extremos = (alterar_extremos.lower() in ["true", "1", "sim"])

    espelho_primeiro = float(dados.get("espelho_primeiro", espelho)) if alterar_extremos else espelho

    tem_patamar_partida = dados.get("tem_patamar_partida", True)
    if isinstance(tem_patamar_partida, str):
        tem_patamar_partida = (tem_patamar_partida.lower() in ["true", "1", "sim"])

    patamar_partida = float(dados.get("patamar_partida", 150))
    patamar_int_1 = float(dados.get("patamar_intermediario_1", 120))
    n1 = int(dados["n_degraus_1"])

    draw = dwg.draw
    draw.level = 242
    draw.color = -1
    draw.style = -1

    # Altura do topo do Lance 1
    y_topo_l1 = y0 + espelho_primeiro + (n1 - 1) * espelho
    y_fundo_pat1 = y_topo_l1 - espessura

    # Degraus Lance 1
    x, y = x0, y0
    for i in range(n1):
        h_esp = espelho_primeiro if i == 0 else espelho
        draw.Line(x, y, x, y + h_esp)
        y += h_esp
        if i < n1 - 1:
            draw.Line(x, y, x + piso, y)
            x += piso

    x_fim_deg_l1 = x

    # Linha paralela de fundo do Lance 1
    p1x, p1y = x0 + piso, y0 + espelho_primeiro
    p2x, p2y = x0 + (n1 - 1) * piso, y0 + espelho_primeiro + (n1 - 2) * espelho if n1 > 1 else (p1x + piso, p1y + espelho)
    f1_x1, f1_y1, f1_x2, f1_y2 = obter_fundo_lance(p1x, p1y, p2x, p2y, espessura)

    # Patamar de Partida (Lado Esquerdo Inferior)
    if tem_patamar_partida:
        x_partida = x0 - patamar_partida
        y_partida = y0
        draw.Line(x_partida, y_partida, x0, y0)

        y_base_partida = y0 - espessura
        x_base_partida_fim = calcular_x_no_y(f1_x1, f1_y1, f1_x2, f1_y2, y_base_partida)
        draw.Line(x_partida, y_base_partida, x_base_partida_fim, y_base_partida)

        # Viga de Saida / Partida
        x_viga_s_ini = x_partida - viga_largura
        x_viga_s_meio = x_partida
        y_viga_s_topo = y0
        y_viga_s_base = y0 - viga_altura
        y_viga_s_corte = y0 - espessura

        draw.Line(x_viga_s_ini, y_viga_s_topo, x_viga_s_ini, y_viga_s_base)
        draw.Line(x_viga_s_ini, y_viga_s_base, x_viga_s_meio, y_viga_s_base)
        draw.Line(x_viga_s_meio, y_viga_s_base, x_viga_s_meio, y_viga_s_corte)
        draw.Line(x_viga_s_ini, y_viga_s_topo, x_partida, y_viga_s_topo)

        x_fundo_l1_ini = x_base_partida_fim
        y_fundo_l1_ini = y_base_partida
    else:
        x_viga_s_ini = x0 - viga_largura
        y_viga_s_topo = y0
        y_viga_s_base = y0 - viga_altura
        y_fundo_no_x0 = calcular_y_no_x(f1_x1, f1_y1, f1_x2, f1_y2, x0)

        draw.Line(x_viga_s_ini, y_viga_s_topo, x0, y_viga_s_topo)
        draw.Line(x_viga_s_ini, y_viga_s_topo, x_viga_s_ini, y_viga_s_base)
        draw.Line(x_viga_s_ini, y_viga_s_base, x0, y_viga_s_base)
        draw.Line(x0, y_viga_s_base, x0, y_fundo_no_x0)

        x_fundo_l1_ini = x0
        y_fundo_l1_ini = y_fundo_no_x0

    # Patamar Intermediario / Chegada do Lance 1 (Lado Direito Superior)
    x_fim_pat1 = x_fim_deg_l1 + patamar_int_1
    draw.Line(x_fim_deg_l1, y_topo_l1, x_fim_pat1, y_topo_l1)

    y_fundo_chegada = y_topo_l1 - espessura
    x_fundo_l1_fim = calcular_x_no_y(f1_x1, f1_y1, f1_x2, f1_y2, y_fundo_chegada)

    draw.Line(x_fundo_l1_ini, y_fundo_l1_ini, x_fundo_l1_fim, y_fundo_chegada)
    draw.Line(x_fundo_l1_fim, y_fundo_chegada, x_fim_pat1, y_fundo_chegada)

    # Viga de Apoio do Patamar Intermediario (Lado Direito Superior)
    x_viga_c_ext = x_fim_pat1 + viga_largura
    draw.Line(x_fim_pat1, y_topo_l1, x_viga_c_ext, y_topo_l1)
    draw.Line(x_viga_c_ext, y_topo_l1, x_viga_c_ext, y_topo_l1 - viga_altura)
    draw.Line(x_viga_c_ext, y_topo_l1 - viga_altura, x_fim_pat1, y_topo_l1 - viga_altura)
    draw.Line(x_fim_pat1, y_topo_l1 - viga_altura, x_fim_pat1, y_fundo_chegada)

    # Indicacao de corte abaixo do 1º lance
    x_rotulo = x0 - 40.0
    y_rotulo = (y0 - viga_altura) - 120.0
    desenhar_indicacao_corte(dwg, x_rotulo, y_rotulo, "CORTE A-A", "ESCALA: 1/20")


def meucmd(eag, tqsjan):
    """Funcao principal acionada pelo menu TQS."""
    dados = pedir_dados_janela_windows()

    if dados is None:
        TQSUtil.writef("Operacao cancelada pelo utilizador.")
        return

    icod, x0, y0 = eag.locate.GetPoint(tqsjan, "Clique no ponto inicial da escada")
    if icod == -1:
        TQSUtil.writef("Operacao cancelada.")
        return

    desenhar_perfil_escada(tqsjan.dwg, x0, y0, dados)
    if dados.get("desenhar_planta", True):
        desenhar_planta_escada(tqsjan.dwg, x0, y0, dados)

        # Se for escada de 2 lances, desenha tambem o corte do 1º lance isolado abaixo da planta
        if dados.get("num_lances", 2) == 2:
            largura_l1 = float(dados.get("largura_lance_1", 120.0))
            largura_l2 = float(dados.get("largura_lance_2", 105.5))
            vao_lances = float(dados.get("vao_lances", 0.0))
            largura_total = largura_l1 + vao_lances + largura_l2
            viga_largura = float(dados.get("viga_largura", 20.0))
            viga_altura = float(dados.get("viga_altura", 40.0))

            dist_offset = viga_altura + 190.0
            y_planta_top = y0 - dist_offset
            y_planta_bot = y_planta_top - largura_total
            y_min_ext = y_planta_bot - viga_largura

            n1 = int(dados["n_degraus_1"])
            espelho = float(dados["espelho"])
            alterar_extremos = dados.get("alterar_extremos", False)
            if isinstance(alterar_extremos, str):
                alterar_extremos = (alterar_extremos.lower() in ["true", "1", "sim"])
            espelho_primeiro = float(dados.get("espelho_primeiro", espelho)) if alterar_extremos else espelho
            altura_l1 = espelho_primeiro + (n1 - 1) * espelho

            # Folga abaixo da planta para o topo do 1º lance
            dist_offset_l1 = viga_altura + 140.0
            y0_lance1 = y_min_ext - dist_offset_l1 - altura_l1

            desenhar_perfil_lance1_isolado(tqsjan.dwg, x0, y0_lance1, dados)

    tqsjan.ZoomTotal()

    if dados.get("alterar_extremos"):
        TQSUtil.writef(
            "Escada (%d lance(s)) desenhada com sucesso! (Piso=%.1f cm, Espelho Geral=%.1f cm, 1º=%.1f cm, Ultimo=%.1f cm)"
            % (dados["num_lances"], dados["piso"], dados["espelho"], dados["espelho_primeiro"], dados["espelho_ultimo"])
        )
    else:
        TQSUtil.writef(
            "Escada (%d lance(s)) desenhada com sucesso! (Piso=%.1f cm, Espelho=%.1f cm)"
            % (dados["num_lances"], dados["piso"], dados["espelho"])
        )
