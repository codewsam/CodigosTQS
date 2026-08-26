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
            window.resizeTo(1000, 720);

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
                        "viga_altura": parseFloat(document.getElementById('viga_altura').value.replace(',', '.'))
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
    <body onload="toggleLances(); togglePatamarPartida(); togglePatamarChegada(); toggleExtremos();">
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
    draw.level = 241
    draw.color = 3

    # --------------------------------------------------------------------------
    # 1. LANCE 1 (Sobe para a Direita: +X, +Y)
    # --------------------------------------------------------------------------
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
            # O último espelho sobe apenas até a face de baixo do patamar 1
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

    # Linha paralela de fundo do Lance 1 (referenciada aos cantos reentrantes)
    p1x, p1y = x0 + piso, y0 + espelho_primeiro
    p2x, p2y = x0 + (n1 - 1) * piso, y0 + espelho_primeiro + (n1 - 2) * espelho if n1 > 1 else (p1x + piso, p1y + espelho)
    f1_x1, f1_y1, f1_x2, f1_y2 = obter_fundo_lance(p1x, p1y, p2x, p2y, espessura)

    if tem_patamar_partida:
        x_partida = x0 - patamar_partida
        y_partida = y0
        draw.Line(x_partida, y_partida, x0, y0)  # Topo patamar de partida

        # Interseção do fundo do Lance 1 com a horizontal inferior de partida
        y_base_partida = y0 - espessura
        x_base_partida_fim = calcular_x_no_y(f1_x1, f1_y1, f1_x2, f1_y2, y_base_partida)
        draw.Line(x_partida, y_base_partida, x_base_partida_fim, y_base_partida)

        # Viga de Saída / Partida (Lado Esquerdo Inferior)
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
        # Viga de Partida Direta no 1º Degrau (Sem Patamar)
        x_viga_s_ini = x0 - viga_largura
        y_viga_s_topo = y0
        y_viga_s_base = y0 - viga_altura

        # Ponto onde o fundo inclinado do lance 1 encontra x0 (face direita da viga)
        y_fundo_no_x0 = calcular_y_no_x(f1_x1, f1_y1, f1_x2, f1_y2, x0)

        # Topo da viga
        draw.Line(x_viga_s_ini, y_viga_s_topo, x0, y_viga_s_topo)
        # Face esquerda da viga
        draw.Line(x_viga_s_ini, y_viga_s_topo, x_viga_s_ini, y_viga_s_base)
        # Fundo da viga
        draw.Line(x_viga_s_ini, y_viga_s_base, x0, y_viga_s_base)
        # Face direita da viga (apenas da base até o encontro com o fundo da escada)
        draw.Line(x0, y_viga_s_base, x0, y_fundo_no_x0)

        x_fundo_l1_ini = x0
        y_fundo_l1_ini = y_fundo_no_x0

    # ==========================================================================
    # CASO 1 LANCE
    # ==========================================================================
    if num_lances == 1:
        if tem_patamar_chegada:
            x_fim_chegada = x_inicio_l2 + patamar_chegada
            draw.Line(x_inicio_l2, y_topo_l1, x_fim_chegada, y_topo_l1)

            y_fundo_chegada = y_topo_l1 - espessura
            x_fundo_l1_fim = calcular_x_no_y(f1_x1, f1_y1, f1_x2, f1_y2, y_fundo_chegada)

            draw.Line(x_fundo_l1_ini, y_fundo_l1_ini, x_fundo_l1_fim, y_fundo_chegada)
            draw.Line(x_fundo_l1_fim, y_fundo_chegada, x_fim_chegada, y_fundo_chegada)

            # Viga de Chegada (Lado Direito Superior)
            x_viga_c_ext = x_fim_chegada + viga_largura
            draw.Line(x_fim_chegada, y_topo_l1, x_viga_c_ext, y_topo_l1)
            draw.Line(x_viga_c_ext, y_topo_l1, x_viga_c_ext, y_topo_l1 - viga_altura)
            draw.Line(x_viga_c_ext, y_topo_l1 - viga_altura, x_fim_chegada, y_topo_l1 - viga_altura)
            draw.Line(x_fim_chegada, y_topo_l1 - viga_altura, x_fim_chegada, y_fundo_chegada)
        else:
            # Viga de Chegada Direta no Último Degrau (Sem Patamar)
            x_viga_c_ext = x_inicio_l2 + viga_largura
            y_fundo_no_xtopo = calcular_y_no_x(f1_x1, f1_y1, f1_x2, f1_y2, x_inicio_l2)

            # Topo da viga
            draw.Line(x_inicio_l2, y_topo_l1, x_viga_c_ext, y_topo_l1)
            # Face direita da viga
            draw.Line(x_viga_c_ext, y_topo_l1, x_viga_c_ext, y_topo_l1 - viga_altura)
            # Fundo da viga
            draw.Line(x_viga_c_ext, y_topo_l1 - viga_altura, x_inicio_l2, y_topo_l1 - viga_altura)
            # Face esquerda da viga (do fundo da viga até o fundo inclinado do lance 1)
            draw.Line(x_inicio_l2, y_topo_l1 - viga_altura, x_inicio_l2, y_fundo_no_xtopo)

            # Fundo do Lance 1 vai até x_inicio_l2
            draw.Line(x_fundo_l1_ini, y_fundo_l1_ini, x_inicio_l2, y_fundo_no_xtopo)
        return

    # --------------------------------------------------------------------------
    # 2. LANCE 2 (Sobe para a Esquerda: -X, +Y)
    # --------------------------------------------------------------------------
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
            # O último espelho sobe apenas até a face de baixo do patamar 2
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

    # --------------------------------------------------------------------------
    # 1º PATAMAR INTERMEDIÁRIO (À DIREITA)
    # --------------------------------------------------------------------------
    x_fim_pat1 = x_inicio_l2 + patamar_int_1

    # Topo do Patamar 1 (do primeiro espelho do Lance 2 até a viga da direita)
    draw.Line(x_inicio_l2, y_topo_l1, x_fim_pat1, y_topo_l1)

    # Fundo do Lance 1 encontra a linha de baixo do patamar 1
    x_fundo_l1_fim = calcular_x_no_y(f1_x1, f1_y1, f1_x2, f1_y2, y_fundo_pat1)
    draw.Line(x_fundo_l1_ini, y_fundo_l1_ini, x_fundo_l1_fim, y_fundo_pat1)

    # O Fundo do Lance 2 desce até a cota de baixo do patamar (y_fundo_pat1)
    x_fundo_l2_no_pat1 = calcular_x_no_y(f2_x1, f2_y1, f2_x2, f2_y2, y_fundo_pat1)

    # Linha de BAIXO do patamar 1: vai desde o encontro com o fundo do Lance 2 até a viga da direita
    draw.Line(x_fundo_l2_no_pat1, y_fundo_pat1, x_fim_pat1, y_fundo_pat1)

    # Viga do 1º Patamar Intermediário (Lado Direito)
    x_viga_p1_ext = x_fim_pat1 + viga_largura
    draw.Line(x_fim_pat1, y_topo_l1, x_viga_p1_ext, y_topo_l1)
    draw.Line(x_viga_p1_ext, y_topo_l1, x_viga_p1_ext, y_topo_l1 - viga_altura)
    draw.Line(x_viga_p1_ext, y_topo_l1 - viga_altura, x_fim_pat1, y_topo_l1 - viga_altura)
    draw.Line(x_fim_pat1, y_topo_l1 - viga_altura, x_fim_pat1, y_fundo_pat1)

    # ==========================================================================
    # CASO 2 LANCES: Finaliza o Lance 2 no patamar de chegada superior à esquerda
    # ==========================================================================
    if num_lances == 2:
        if tem_patamar_chegada:
            x_fim_chegada = x_topo_l2 - patamar_chegada
            draw.Line(x_topo_l2, y_topo_l2, x_fim_chegada, y_topo_l2)

            y_fundo_chegada = y_topo_l2 - espessura
            x_fundo_l2_fim = calcular_x_no_y(f2_x1, f2_y1, f2_x2, f2_y2, y_fundo_chegada)

            # Fundo do Lance 2 vai desde a cota de baixo do patamar 1 até a chegada superior
            draw.Line(x_fundo_l2_no_pat1, y_fundo_pat1, x_fundo_l2_fim, y_fundo_chegada)
            draw.Line(x_fundo_l2_fim, y_fundo_chegada, x_fim_chegada, y_fundo_chegada)

            # Viga de Chegada (Lado Esquerdo Superior)
            x_viga_c_ext = x_fim_chegada - viga_largura
            draw.Line(x_fim_chegada, y_topo_l2, x_viga_c_ext, y_topo_l2)
            draw.Line(x_viga_c_ext, y_topo_l2, x_viga_c_ext, y_topo_l2 - viga_altura)
            draw.Line(x_viga_c_ext, y_topo_l2 - viga_altura, x_fim_chegada, y_topo_l2 - viga_altura)
            draw.Line(x_fim_chegada, y_topo_l2 - viga_altura, x_fim_chegada, y_fundo_chegada)
        else:
            # Viga de Chegada Direta no Último Degrau (Sem Patamar)
            x_viga_c_ext = x_topo_l2 - viga_largura
            y_fundo_no_xtopo2 = calcular_y_no_x(f2_x1, f2_y1, f2_x2, f2_y2, x_topo_l2)

            # Topo da viga
            draw.Line(x_topo_l2, y_topo_l2, x_viga_c_ext, y_topo_l2)
            # Face esquerda da viga
            draw.Line(x_viga_c_ext, y_topo_l2, x_viga_c_ext, y_topo_l2 - viga_altura)
            # Fundo da viga
            draw.Line(x_viga_c_ext, y_topo_l2 - viga_altura, x_topo_l2, y_topo_l2 - viga_altura)
            # Face direita da viga (do fundo da viga até o fundo inclinado do lance 2)
            draw.Line(x_topo_l2, y_topo_l2 - viga_altura, x_topo_l2, y_fundo_no_xtopo2)

            # Fundo do Lance 2 vai desde o patamar 1 até x_topo_l2
            draw.Line(x_fundo_l2_no_pat1, y_fundo_pat1, x_topo_l2, y_fundo_no_xtopo2)
        return

    # ==========================================================================
    # CASO 3 LANCES: 2º Patamar Intermediário (à esquerda) e Lance 3 (+X, +Y)
    # ==========================================================================
    x_inicio_l3 = x_topo_l2
    x, y = x_inicio_l3, y_topo_l2

    if n3 > 1:
        y_topo_l3 = y_topo_l2 + (n3 - 1) * espelho + espelho_ultimo
    else:
        y_topo_l3 = y_topo_l2 + (espelho_ultimo if n3 == 1 else 0)

    # Degraus Lance 3 (Sobe para a Direita a partir de x_inicio_l3, y_topo_l2)
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

    # Linha paralela de fundo do Lance 3
    p3_1x, p3_1y = x_inicio_l3 + piso, y_topo_l2 + espelho
    p3_2x, p3_2y = x_inicio_l3 + (n3 - 1) * piso, y_topo_l2 + (n3 - 1) * espelho if n3 > 1 else (p3_1x + piso, p3_1y + espelho)
    f3_x1, f3_y1, f3_x2, f3_y2 = obter_fundo_lance(p3_1x, p3_1y, p3_2x, p3_2y, espessura)

    # --------------------------------------------------------------------------
    # 2º PATAMAR INTERMEDIÁRIO (À ESQUERDA)
    # --------------------------------------------------------------------------
    x_fim_pat2 = x_inicio_l3 - patamar_int_2

    # Topo do Patamar 2 (do primeiro espelho do Lance 3 até a viga da esquerda)
    draw.Line(x_inicio_l3, y_topo_l2, x_fim_pat2, y_topo_l2)

    # Fundo do Lance 2 encontra a linha de baixo do patamar 2
    x_fundo_l2_fim = calcular_x_no_y(f2_x1, f2_y1, f2_x2, f2_y2, y_fundo_pat2)
    draw.Line(x_fundo_l2_no_pat1, y_fundo_pat1, x_fundo_l2_fim, y_fundo_pat2)

    # O Fundo do Lance 3 desce até a cota de baixo do patamar 2 (y_fundo_pat2)
    x_fundo_l3_no_pat2 = calcular_x_no_y(f3_x1, f3_y1, f3_x2, f3_y2, y_fundo_pat2)

    # Linha de BAIXO do patamar 2: vai desde a viga até o fundo do Lance 3
    draw.Line(x_fim_pat2, y_fundo_pat2, x_fundo_l3_no_pat2, y_fundo_pat2)

    # Viga do 2º Patamar Intermediário (Lado Esquerdo)
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

        # Fundo do Lance 3 vai desde o patamar 2 até a chegada superior
        y_fundo_chegada = y_topo_l3 - espessura
        x_fundo_l3_fim = calcular_x_no_y(f3_x1, f3_y1, f3_x2, f3_y2, y_fundo_chegada)

        draw.Line(x_fundo_l3_no_pat2, y_fundo_pat2, x_fundo_l3_fim, y_fundo_chegada)
        draw.Line(x_fundo_l3_fim, y_fundo_chegada, x_fim_chegada, y_fundo_chegada)

        # Viga de Chegada Superior (Lado Direito)
        x_viga_c_ext = x_fim_chegada + viga_largura
        draw.Line(x_fim_chegada, y_topo_l3, x_viga_c_ext, y_topo_l3)
        draw.Line(x_viga_c_ext, y_topo_l3, x_viga_c_ext, y_topo_l3 - viga_altura)
        draw.Line(x_viga_c_ext, y_topo_l3 - viga_altura, x_fim_chegada, y_topo_l3 - viga_altura)
        draw.Line(x_fim_chegada, y_topo_l3 - viga_altura, x_fim_chegada, y_fundo_chegada)
    else:
        # Viga de Chegada Direta no Último Degrau (Sem Patamar)
        x_viga_c_ext = x_topo_l3 + viga_largura
        y_fundo_no_xtopo3 = calcular_y_no_x(f3_x1, f3_y1, f3_x2, f3_y2, x_topo_l3)

        # Topo da viga
        draw.Line(x_topo_l3, y_topo_l3, x_viga_c_ext, y_topo_l3)
        # Face direita da viga
        draw.Line(x_viga_c_ext, y_topo_l3, x_viga_c_ext, y_topo_l3 - viga_altura)
        # Fundo da viga
        draw.Line(x_viga_c_ext, y_topo_l3 - viga_altura, x_topo_l3, y_topo_l3 - viga_altura)
        # Face esquerda da viga (do fundo da viga até o fundo inclinado do lance 3)
        draw.Line(x_topo_l3, y_topo_l3 - viga_altura, x_topo_l3, y_fundo_no_xtopo3)

        # Fundo do Lance 3 vai desde o patamar 2 até x_topo_l3
        draw.Line(x_fundo_l3_no_pat2, y_fundo_pat2, x_topo_l3, y_fundo_no_xtopo3)


# ==============================================================================
# COMANDO PRINCIPAL EXECUTADO PELO TQS
# ==============================================================================
def meucmd(eag, tqsjan):
    """Função principal acionada pelo menu TQS."""
    dados = pedir_dados_janela_windows()

    if dados is None:
        TQSUtil.writef("Operação cancelada pelo utilizador.")
        return

    icod, x0, y0 = eag.locate.GetPoint(tqsjan, "Clique no ponto inicial da escada")
    if icod == -1:
        TQSUtil.writef("Operação cancelada.")
        return

    desenhar_perfil_escada(tqsjan.dwg, x0, y0, dados)
    tqsjan.ZoomTotal()

    if dados.get("alterar_extremos"):
        TQSUtil.writef(
            "Escada (%d lance(s)) desenhada com sucesso! (Piso=%.1f cm, Espelho Geral=%.1f cm, 1º=%.1f cm, Último=%.1f cm)"
            % (dados["num_lances"], dados["piso"], dados["espelho"], dados["espelho_primeiro"], dados["espelho_ultimo"])
        )
    else:
        TQSUtil.writef(
            "Escada (%d lance(s)) desenhada com sucesso! (Piso=%.1f cm, Espelho=%.1f cm)"
            % (dados["num_lances"], dados["piso"], dados["espelho"])
        )
