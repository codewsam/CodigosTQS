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
        <meta http-equiv="x-ua-compatible" content="ie=edge" />
        <title>Dados da Escada - Plugin TQS</title>
        <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="EscadaTQS" BORDER="dialog" INNERBORDER="no" SCROLL="no" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #f0f0f0; margin: 15px 20px; font-size: 13px; }}
            .container {{ display: flex; gap: 20px; }}
            .img-box {{ background: white; padding: 10px; border: 1px solid #ccc; border-radius: 5px; display:flex; align-items:center; justify-content:center; }}
            .img-box img {{ max-width: 430px; }}
            .form-box {{ display: flex; flex-direction: column; gap: 5px; flex: 1; }}
            h3 {{ margin: 0 0 6px 0; color: #333; font-size: 15px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }}
            .campo {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px; }}
            label {{ font-weight: 500; color: #444; }}
            input, select {{ width: 85px; padding: 3px; text-align: right; border: 1px solid #aaa; border-radius: 3px; }}
            select {{ text-align: left; }}
            .sec-opcional {{ background: #e8eef7; padding: 5px 8px; border-radius: 4px; border: 1px solid #c5d6eb; margin-top: 3px; }}
            .btns {{ margin-top: 10px; display: flex; justify-content: flex-end; gap: 10px; }}
            button {{ padding: 6px 15px; cursor: pointer; border: 1px solid #999; border-radius: 3px; background: #e1e1e1; }}
            button:hover {{ background: #d1d1d1; }}
            .btn-gerar {{ background: #0056b3; color: white; border: none; font-weight: bold; }}
            .btn-gerar:hover {{ background: #004494; }}
        </style>
        <script>
            window.resizeTo(980, 580);

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

            function confirmar() {{
                try {{
                    var fso = new ActiveXObject("Scripting.FileSystemObject");
                    var file = fso.CreateTextFile("{json_js}", true, false);

                    var numLances = parseInt(document.getElementById('num_lances').value);
                    var n_deg1 = parseInt(document.getElementById('n_degraus_1').value);
                    var n_deg2 = numLances >= 2 ? parseInt(document.getElementById('n_degraus_2').value) : 0;
                    var n_deg3 = numLances === 3 ? parseInt(document.getElementById('n_degraus_3').value) : 0;

                    var dados = {{
                        "num_lances": numLances,
                        "piso": parseFloat(document.getElementById('piso').value.replace(',', '.')),
                        "espelho": parseFloat(document.getElementById('espelho').value.replace(',', '.')),
                        "n_degraus_1": n_deg1,
                        "n_degraus_2": n_deg2,
                        "n_degraus_3": n_deg3,
                        "patamar_partida": parseFloat(document.getElementById('patamar_partida').value.replace(',', '.')),
                        "patamar_intermediario_1": parseFloat(document.getElementById('patamar_int_1').value.replace(',', '.')),
                        "patamar_intermediario_2": parseFloat(document.getElementById('patamar_int_2').value.replace(',', '.')),
                        "patamar_chegada": parseFloat(document.getElementById('patamar_chegada').value.replace(',', '.')),
                        "espessura": parseFloat(document.getElementById('espessura').value.replace(',', '.')),
                        "viga_largura": parseFloat(document.getElementById('viga_largura').value.replace(',', '.')),
                        "viga_altura": parseFloat(document.getElementById('viga_altura').value.replace(',', '.'))
                    }};

                    file.Write(JSON.stringify(dados));
                    file.Close();
                    window.close();
                }} catch (e) {{
                    alert("Erro ao gravar os dados: " + e.message);
                }}
            }}
        </script>
    </head>
    <body onload="toggleLances()">
        <div class="container">
            <div class="img-box">
                <img src="{img_html}" alt="Diagrama" onerror="this.style.display='none';">
            </div>
            <div class="form-box">
                <h3>Dados da Escada</h3>

                <div class="campo">
                    <label>Quantidade de Lances:</label>
                    <select id="num_lances" onchange="toggleLances()">
                        <option value="1">1 Lance</option>
                        <option value="2" selected>2 Lances</option>
                        <option value="3">3 Lances</option>
                    </select>
                </div>

                <div class="campo"><label>Passo / Largura (cm):</label><input type="text" id="piso" value="29"></div>
                <div class="campo"><label>Espelho / Altura (cm):</label><input type="text" id="espelho" value="17.9"></div>
                <div class="campo"><label>Degraus Lance 1:</label><input type="text" id="n_degraus_1" value="8"></div>

                <div id="box_lance2" class="sec-opcional">
                    <div class="campo"><label>Degraus Lance 2:</label><input type="text" id="n_degraus_2" value="8"></div>
                </div>

                <div id="box_lance3" class="sec-opcional" style="display:none;">
                    <div class="campo"><label>Degraus Lance 3:</label><input type="text" id="n_degraus_3" value="8"></div>
                    <div class="campo"><label>Segundo Patamar meio. (cm):</label><input type="text" id="patamar_int_2" value="120"></div>
                </div>

                <div class="campo"><label>Patamar partida (cm):</label><input type="text" id="patamar_partida" value="150"></div>
                <div class="campo" id="campo_pat1"><label>Patamar meio. (cm):</label><input type="text" id="patamar_int_1" value="120"></div>
                <div class="campo"><label>Patamar chegada (cm):</label><input type="text" id="patamar_chegada" value="150"></div>
                <div class="campo"><label>Espessura laje (cm):</label><input type="text" id="espessura" value="15"></div>
                <div class="campo"><label>Largura viga (cm):</label><input type="text" id="viga_largura" value="20"></div>
                <div class="campo"><label>Altura viga (cm):</label><input type="text" id="viga_altura" value="40"></div>

                <div class="btns">
                    <button onclick="window.close()">Cancelar</button>
                    <button class="btn-gerar" onclick="confirmar()">Gerar Escada</button>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    with open(hta_path, "w", encoding="utf-8") as f:
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


# ==============================================================================
# FUNÇÃO DE DESENHO DA GEOMETRIA NO TQS
# ==============================================================================
def desenhar_perfil_escada(dwg, x0, y0, dados):
    num_lances = dados.get("num_lances", 2)
    piso = dados["piso"]
    espelho = dados["espelho"]
    espessura = dados["espessura"]
    viga_largura = dados["viga_largura"]
    viga_altura = dados["viga_altura"]

    patamar_partida = dados["patamar_partida"]
    patamar_int_1 = dados.get("patamar_intermediario_1", 120)
    patamar_int_2 = dados.get("patamar_intermediario_2", 120)
    patamar_chegada = dados["patamar_chegada"]

    n1 = int(dados["n_degraus_1"])
    n2 = int(dados.get("n_degraus_2", 0))
    n3 = int(dados.get("n_degraus_3", 0))

    draw = dwg.draw
    draw.level = 241
    draw.color = 3

    # --------------------------------------------------------------------------
    # 1. LANCE 1 (Sobe para a Direita: +X, +Y)
    # --------------------------------------------------------------------------
    x_partida = x0 - patamar_partida
    y_partida = y0
    draw.Line(x_partida, y_partida, x0, y0)  # Topo patamar de partida

    y_topo_l1 = y0 + n1 * espelho
    y_fundo_pat1 = y_topo_l1 - espessura

    # Degraus Lance 1
    x, y = x0, y0
    for i in range(n1):
        if num_lances > 1 and i == n1 - 1:
            # O último espelho sobe apenas até a face de baixo do patamar 1 (sem entrar no concreto)
            if y < y_fundo_pat1:
                draw.Line(x, y, x, y_fundo_pat1)
            y = y_topo_l1
        else:
            draw.Line(x, y, x, y + espelho)
            y += espelho

        if i < n1 - 1:
            draw.Line(x, y, x + piso, y)
            x += piso

    x_inicio_l2 = x

    # Linha paralela de fundo do Lance 1
    p1x, p1y = x0 + piso, y0 + espelho
    p2x, p2y = x0 + (n1 - 1) * piso, y0 + (n1 - 1) * espelho if n1 > 1 else (p1x + piso, p1y + espelho)
    f1_x1, f1_y1, f1_x2, f1_y2 = obter_fundo_lance(p1x, p1y, p2x, p2y, espessura)

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
    draw.Line(x_viga_s_ini, y_viga_s_topo, x0, y_viga_s_topo)

    # ==========================================================================
    # CASO 1 LANCE
    # ==========================================================================
    if num_lances == 1:
        x_fim_chegada = x_inicio_l2 + patamar_chegada
        draw.Line(x_inicio_l2, y_topo_l1, x_fim_chegada, y_topo_l1)

        y_fundo_chegada = y_topo_l1 - espessura
        x_fundo_l1_fim = calcular_x_no_y(f1_x1, f1_y1, f1_x2, f1_y2, y_fundo_chegada)

        draw.Line(x_base_partida_fim, y_base_partida, x_fundo_l1_fim, y_fundo_chegada)
        draw.Line(x_fundo_l1_fim, y_fundo_chegada, x_fim_chegada, y_fundo_chegada)

        # Viga de Chegada (Lado Direito Superior)
        x_viga_c_ext = x_fim_chegada + viga_largura
        draw.Line(x_fim_chegada, y_topo_l1, x_viga_c_ext, y_topo_l1)
        draw.Line(x_viga_c_ext, y_topo_l1, x_viga_c_ext, y_topo_l1 - viga_altura)
        draw.Line(x_viga_c_ext, y_topo_l1 - viga_altura, x_fim_chegada, y_topo_l1 - viga_altura)
        draw.Line(x_fim_chegada, y_topo_l1 - viga_altura, x_fim_chegada, y_fundo_chegada)
        return

    # --------------------------------------------------------------------------
    # 2. LANCE 2 (Sobe para a Esquerda: -X, +Y)
    # --------------------------------------------------------------------------
    x, y = x_inicio_l2, y_topo_l1
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
            draw.Line(x, y, x, y + espelho)
            y += espelho

        if i < n2 - 1:
            draw.Line(x, y, x - piso, y)
            x -= piso

    x_topo_l2 = x

    # Linha paralela de fundo do Lance 2
    p2_1x, p2_1y = x_inicio_l2 - piso, y_topo_l1 + espelho
    p2_2x, p2_2y = x_inicio_l2 - (n2 - 1) * piso, y_topo_l1 + (n2 - 1) * espelho if n2 > 1 else (p2_1x - piso,
                                                                                                 p2_1y + espelho)
    f2_x1, f2_y1, f2_x2, f2_y2 = obter_fundo_lance(p2_1x, p2_1y, p2_2x, p2_2y, espessura)

    # --------------------------------------------------------------------------
    # 1º PATAMAR INTERMEDIÁRIO (À DIREITA)
    # --------------------------------------------------------------------------
    x_fim_pat1 = x_inicio_l2 + patamar_int_1

    # Topo do Patamar 1 (do primeiro espelho do Lance 2 até a viga da direita)
    draw.Line(x_inicio_l2, y_topo_l1, x_fim_pat1, y_topo_l1)

    # Fundo do Lance 1 encontra a linha de baixo do patamar 1
    x_fundo_l1_fim = calcular_x_no_y(f1_x1, f1_y1, f1_x2, f1_y2, y_fundo_pat1)
    draw.Line(x_base_partida_fim, y_base_partida, x_fundo_l1_fim, y_fundo_pat1)

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
        return

    # ==========================================================================
    # CASO 3 LANCES: 2º Patamar Intermediário (à esquerda) e Lance 3 (+X, +Y)
    # ==========================================================================
    x_inicio_l3 = x_topo_l2
    x, y = x_inicio_l3, y_topo_l2

    # Degraus Lance 3 (Sobe para a Direita a partir de x_inicio_l3, y_topo_l2)
    for i in range(n3):
        draw.Line(x, y, x, y + espelho)
        y += espelho
        if i < n3 - 1:
            draw.Line(x, y, x + piso, y)
            x += piso

    x_topo_l3 = x
    y_topo_l3 = y_topo_l2 + n3 * espelho

    # Linha paralela de fundo do Lance 3
    p3_1x, p3_1y = x_inicio_l3 + piso, y_topo_l2 + espelho
    p3_2x, p3_2y = x_inicio_l3 + (n3 - 1) * piso, y_topo_l2 + (n3 - 1) * espelho if n3 > 1 else (p3_1x + piso,
                                                                                                 p3_1y + espelho)
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

    TQSUtil.writef(
        "Escada (%d lance(s)) desenhada com sucesso! (Piso=%.1f cm, Espelho=%.1f cm)"
        % (dados["num_lances"], dados["piso"], dados["espelho"])
    )
