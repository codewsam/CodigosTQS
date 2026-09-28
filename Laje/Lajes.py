# -*- coding: utf-8 -*-
import os
import json
import math
import subprocess
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag


# ==============================================================================
# TABELA PADRÃO DE TRANSPASSE POR BITOLA (Norma / Prática G3)
# ==============================================================================
TABELA_TRANSPASSE = {
    6.3: 40.0,
    8.0: 50.0,
    10.0: 60.0,
    12.5: 70.0,
    16.0: 90.0,
    20.0: 110.0
}


# ==============================================================================
# INTERFACE GRÁFICA (HTA) COM ABAS: ARMADURA POSITIVA E NEGATIVA (TEMA ROXO)
# ==============================================================================
def pedir_dados_laje():
    """Abre janela interativa com 2 setores (Positiva e Negativa) em tema roxo."""
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
        <title>Armação de Laje Nervurada - G3 Plugins</title>
        <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="ArmarLaje" BORDER="dialog" INNERBORDER="no" SCROLL="no" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Tahoma, sans-serif;
                background: #f7f4fa;
                margin: 0;
                padding: 0;
                font-size: 12.5px;
                color: #2b2736;
            }}
            .topbar {{
                background: linear-gradient(135deg, #6a1b9a 0%, #38006b 100%);
                color: #fff;
                padding: 12px 18px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.25);
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            .topbar .icon {{
                width: 32px;
                height: 32px;
                background: rgba(255,255,255,0.18);
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 17px;
            }}
            .topbar h1 {{
                margin: 0;
                font-size: 15px;
                font-weight: 600;
                letter-spacing: 0.2px;
            }}
            .topbar p {{
                margin: 2px 0 0 0;
                font-size: 11px;
                color: #e1bee7;
            }}
            .container {{
                padding: 12px 18px 8px 18px;
            }}
            .tabs {{
                display: flex;
                gap: 6px;
                border-bottom: 2px solid #ceb3db;
                margin-bottom: 12px;
            }}
            .tab {{
                padding: 7px 16px;
                cursor: pointer;
                font-weight: 600;
                color: #6a1b9a;
                background: #ede3f2;
                border-radius: 6px 6px 0 0;
                border: 1px solid #ceb3db;
                border-bottom: none;
                font-size: 12px;
                transition: all 0.15s ease;
            }}
            .tab:hover {{ background: #f3e5f5; }}
            .tab.active {{
                background: #ffffff;
                color: #38006b;
                border-top: 3px solid #6a1b9a;
                border-bottom: 2px solid #ffffff;
                margin-bottom: -2px;
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
                border: 1px solid #e1bee7;
                border-radius: 8px;
                padding: 12px 16px;
                box-shadow: 0 1px 3px rgba(106,27,154,0.06);
            }}
            .card h3 {{
                margin: 0 0 10px 0;
                color: #4a148c;
                font-size: 11.5px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.4px;
                border-bottom: 1px solid #f3e5f5;
                padding-bottom: 5px;
            }}
            .campo {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }}
            .campo:last-child {{ margin-bottom: 0; }}
            label {{
                font-weight: 500;
                color: #42394d;
                font-size: 12px;
            }}
            input, select {{
                width: 130px;
                padding: 4px 8px;
                text-align: right;
                border: 1px solid #ceb3db;
                border-radius: 4px;
                background: #fdfbfe;
                font-size: 12px;
            }}
            select {{ text-align: left; width: 140px; }}
            input:focus, select:focus {{
                outline: none;
                border-color: #6a1b9a;
                box-shadow: 0 0 0 2px rgba(106,27,154,0.18);
                background: #fff;
            }}
            .info-box {{
                background: #f3e5f5;
                border: 1px solid #e1bee7;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 11px;
                color: #4a148c;
                line-height: 1.4;
            }}
            .btns {{
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                padding: 4px 18px 14px 18px;
            }}
            button {{
                padding: 8px 18px;
                cursor: pointer;
                border: 1px solid #ceb3db;
                border-radius: 5px;
                background: #f7f3fa;
                font-size: 12px;
                font-weight: 500;
                color: #4a148c;
            }}
            button:hover {{ background: #ece0f2; }}
            .btn-gerar {{
                background: linear-gradient(135deg, #6a1b9a 0%, #4a148c 100%);
                color: #fff;
                border: none;
                font-weight: 600;
                box-shadow: 0 1px 4px rgba(106,27,154,0.35);
            }}
            .btn-gerar:hover {{ background: linear-gradient(135deg, #5c1687 0%, #3b0e70 100%); }}
        </style>
        <script type="text/javascript">
            var tabelaTranspasse = {{
                "6.3": 40,
                "8.0": 50,
                "10.0": 60,
                "12.5": 70,
                "16.0": 90,
                "20.0": 110
            }};

            var setorAtual = "POSITIVA";

            function trocarAba(setor) {{
                setorAtual = setor;
                document.getElementById('tab-positiva').className = (setor == 'POSITIVA') ? 'tab active' : 'tab';
                document.getElementById('tab-negativa').className = (setor == 'NEGATIVA') ? 'tab active' : 'tab';
                document.getElementById('conteudo-positiva').className = (setor == 'POSITIVA') ? 'tab-content active' : 'tab-content';
                document.getElementById('conteudo-negativa').className = (setor == 'NEGATIVA') ? 'tab-content active' : 'tab-content';
            }}

            function atualizarTranspassePos() {{
                var bit = document.getElementById('pos_bitola').value;
                if (tabelaTranspasse[bit]) {{
                    document.getElementById('pos_transpasse').value = tabelaTranspasse[bit];
                }}
            }}

            function atualizarTranspasseNeg() {{
                var bit = document.getElementById('neg_bitola').value;
                if (tabelaTranspasse[bit]) {{
                    document.getElementById('neg_transpasse').value = tabelaTranspasse[bit];
                }}
            }}

            function initDialog() {{
                try {{
                    window.resizeTo(500, 430);
                    window.moveTo((screen.availWidth - 500) / 2, (screen.availHeight - 430) / 2);
                }} catch(e) {{}}
                atualizarTranspassePos();
                atualizarTranspasseNeg();
            }}

            function confirmar() {{
                try {{
                    var dados = {{
                        "setor": setorAtual
                    }};

                    if (setorAtual == "POSITIVA") {{
                        var bit = parseFloat(document.getElementById('pos_bitola').value) || 16.0;
                        var trans = parseFloat(document.getElementById('pos_transpasse').value.replace(',', '.')) || (tabelaTranspasse[bit] || 90.0);
                        var dir = document.getElementById('pos_direcao').value;
                        var qtd_nerv = parseInt(document.getElementById('pos_qtd_nerv').value) || 1;
                        var pos_texto = document.getElementById('pos_id').value || "P89";

                        dados.bitola = bit;
                        dados.transpasse = trans;
                        dados.direcao = dir;
                        dados.qtd_nerv = qtd_nerv;
                        dados.pos_id = pos_texto;
                    }} else {{
                        var bit = parseFloat(document.getElementById('neg_bitola').value) || 10.0;
                        var trans = parseFloat(document.getElementById('neg_transpasse').value.replace(',', '.')) || (tabelaTranspasse[bit] || 60.0);
                        var dir = document.getElementById('neg_direcao').value;
                        var dobra = parseFloat(document.getElementById('neg_dobra').value.replace(',', '.')) || 0.0;
                        var pos_texto = document.getElementById('neg_id').value || "N1";

                        dados.bitola = bit;
                        dados.transpasse = trans;
                        dados.direcao = dir;
                        dados.dobra = dobra;
                        dados.pos_id = pos_texto;
                    }}

                    var fso = new ActiveXObject("Scripting.FileSystemObject");
                    var a = fso.CreateTextFile("{json_js}", true);

                    var jsonStr = '{{"setor":"' + dados.setor + '"' +
                                  ',"bitola":' + dados.bitola + 
                                  ',"transpasse":' + dados.transpasse +
                                  ',"direcao":"' + dados.direcao + '"' +
                                  ',"pos_id":"' + dados.pos_id + '"' +
                                  (dados.qtd_nerv ? ',"qtd_nerv":' + dados.qtd_nerv : '') +
                                  (dados.dobra !== undefined ? ',"dobra":' + dados.dobra : '') +
                                  '}}';

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
                <p>Plugin TQS &#9679 G3 Engenharia</p>
            </div>
        </div>

        <div class="container">
            <div class="tabs">
                <div id="tab-positiva" class="tab active" onclick="trocarAba('POSITIVA')">Armadura Positiva (Fundo)</div>
                <div id="tab-negativa" class="tab" onclick="trocarAba('NEGATIVA')">Armadura Negativa (Topo / Apoios)</div>
            </div>

            <!-- ABA 1: ARMADURA POSITIVA -->
            <div id="conteudo-positiva" class="tab-content active">
                <div class="card">
                    <h3>Parâmetros da Armadura Positiva</h3>
                    <div class="campo">
                        <label>Direção da Barra:</label>
                        <select id="pos_direcao">
                            <option value="HORIZONTAL" selected>Horizontal (Direção X)</option>
                            <option value="VERTICAL">Vertical (Direção Y)</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label>Bitola da Barra (&Phi; mm):</label>
                        <select id="pos_bitola" onchange="atualizarTranspassePos()">
                            <option value="6.3">&Phi; 6.3 mm</option>
                            <option value="8.0">&Phi; 8.0 mm</option>
                            <option value="10.0">&Phi; 10.0 mm</option>
                            <option value="12.5">&Phi; 12.5 mm</option>
                            <option value="16.0" selected>&Phi; 16.0 mm</option>
                            <option value="20.0">&Phi; 20.0 mm</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label>Transpasse entre Barras (cm):</label>
                        <input type="text" id="pos_transpasse" value="90">
                    </div>
                    <div class="campo">
                        <label>Barras por Nervura:</label>
                        <select id="pos_qtd_nerv">
                            <option value="1" selected>1 barra / nervura</option>
                            <option value="2">2 barras / nervura</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label>Identificação / Posição:</label>
                        <input type="text" id="pos_id" value="P89">
                    </div>
                </div>

                <div class="info-box">
                    💡 <b>Armadura Positiva:</b> Fica no fundo das nervuras. Arraste uma janela no EAG sobre a extensão das nervuras para gerar as barras com emendas automáticas de 12m.
                </div>
            </div>

            <!-- ABA 2: ARMADURA NEGATIVA -->
            <div id="conteudo-negativa" class="tab-content">
                <div class="card">
                    <h3>Parâmetros da Armadura Negativa</h3>
                    <div class="campo">
                        <label>Direção da Barra:</label>
                        <select id="neg_direcao">
                            <option value="HORIZONTAL" selected>Horizontal (Direção X)</option>
                            <option value="VERTICAL">Vertical (Direção Y)</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label>Bitola da Barra (&Phi; mm):</label>
                        <select id="neg_bitola" onchange="atualizarTranspasseNeg()">
                            <option value="6.3">&Phi; 6.3 mm</option>
                            <option value="8.0">&Phi; 8.0 mm</option>
                            <option value="10.0" selected>&Phi; 10.0 mm</option>
                            <option value="12.5">&Phi; 12.5 mm</option>
                            <option value="16.0">&Phi; 16.0 mm</option>
                            <option value="20.0">&Phi; 20.0 mm</option>
                        </select>
                    </div>
                    <div class="campo">
                        <label>Transpasse entre Barras (cm):</label>
                        <input type="text" id="neg_transpasse" value="60">
                    </div>
                    <div class="campo">
                        <label>Dobra / Gancho nas Pontas (cm):</label>
                        <input type="text" id="neg_dobra" value="15">
                    </div>
                    <div class="campo">
                        <label>Identificação / Posição:</label>
                        <input type="text" id="neg_id" value="N1">
                    </div>
                </div>

                <div class="info-box">
                    💡 <b>Armadura Negativa:</b> Fica na face superior sobre apoios e vigas para combater tração superior. Arraste uma janela sobre a região de ancoragem/viga.
                </div>
            </div>
        </div>

        <div class="btns">
            <button onclick="window.close()">Cancelar</button>
            <button class="btn-gerar" onclick="confirmar()">Arrastar Janela no EAG</button>
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
# GERAÇÃO DAS BARRAS (POSITIVAS E NEGATIVAS - HORIZONTAL OU VERTICAL)
# ==============================================================================
def processar_armadura(dwg, xs, ys, dados):
    """
    Identifica a geometria e gera as armaduras positivas ou negativas no EAG.
    """
    draw = dwg.draw

    x1 = min(xs)
    x2 = max(xs)
    y1 = min(ys)
    y2 = max(ys)

    largura_total = x2 - x1
    altura_total = y2 - y1

    if largura_total <= 1.0 and altura_total <= 1.0:
        return

    setor = dados.get("setor", "POSITIVA")
    direcao = dados.get("direcao", "HORIZONTAL").upper()
    bitola = float(dados.get("bitola", 16.0 if setor == "POSITIVA" else 10.0))
    transpasse_cm = float(dados.get("transpasse", TABELA_TRANSPASSE.get(bitola, 90.0)))
    pos_id = str(dados.get("pos_id", "P89" if setor == "POSITIVA" else "N1"))
    comp_max_barra = 1200.0  # 12 metros em cm

    modulo_nervura = 65.0

    # --------------------------------------------------------------------------
    # CASO 1: DIREÇÃO HORIZONTAL (Barras correm em X, distribuição em Y)
    # --------------------------------------------------------------------------
    if direcao == "HORIZONTAL":
        comp_total = largura_total
        ym = (y1 + y2) / 2.0
        xm = (x1 + x2) / 2.0

        if altura_total > 10.0:
            num_nervuras = max(int(round(altura_total / modulo_nervura)), 1)
        else:
            num_nervuras = 1

        qtd_nerv = int(dados.get("qtd_nerv", 1))
        dobra = float(dados.get("dobra", 0.0)) if setor == "NEGATIVA" else 0.0

        # Nível e cor (Positiva = Nível 220 Verde, Negativa = Nível 220/230)
        draw.level = 220
        draw.color = 3  # Verde
        draw.style = 0

        # 1. Traçar as barras horizontais com transpasse se > 12m
        if comp_total <= comp_max_barra:
            draw.Line(x1, ym, x2, ym)
            if dobra > 0.0:
                draw.Line(x1, ym, x1, ym - dobra)
                draw.Line(x2, ym, x2, ym - dobra)
        else:
            comp_util = comp_max_barra - transpasse_cm
            x_atual = x1
            idx_b = 0

            while x_atual < x2:
                x_fim_b = min(x_atual + comp_max_barra, x2)
                off_y = 3.0 if (idx_b % 2 == 1) else 0.0

                draw.Line(x_atual, ym + off_y, x_fim_b, ym + off_y)

                if idx_b == 0 and dobra > 0.0:
                    draw.Line(x_atual, ym + off_y, x_atual, ym + off_y - dobra)
                if x_fim_b >= x2 and dobra > 0.0:
                    draw.Line(x_fim_b, ym + off_y, x_fim_b, ym + off_y - dobra)

                if x_fim_b >= x2:
                    break
                x_atual += comp_util
                idx_b += 1

        # 2. Linha de distribuição vertical com setas
        if altura_total > 20.0:
            draw.level = 220
            draw.color = 3  # Verde
            draw.style = 1  # Tracejado
            x_dist = xm
            draw.Line(x_dist, y1, x_dist, y2)

            # Setas
            raio_seta = 6.0
            draw.style = 0
            draw.Line(x_dist, y1, x_dist - raio_seta, y1 + raio_seta * 1.8)
            draw.Line(x_dist, y1, x_dist + raio_seta, y1 + raio_seta * 1.8)
            draw.Line(x_dist, y2, x_dist - raio_seta, y2 - raio_seta * 1.8)
            draw.Line(x_dist, y2, x_dist + raio_seta, y2 - raio_seta * 1.8)

        # 3. Texto de chamada (Amarelo)
        draw.level = 220
        draw.color = 2  # Amarelo
        bitola_str = f"{bitola:g}"
        comp_real = int(round(comp_total + 2 * dobra))

        if setor == "POSITIVA":
            prefixo = f"{num_nervuras}x{qtd_nerv}" if qtd_nerv > 1 else f"{num_nervuras}x1"
            txt_chamada = f"{prefixo} {pos_id} %% {bitola_str} C/NERV C={comp_real}"
        else:
            txt_chamada = f"{num_nervuras} {pos_id} %% {bitola_str} C/NERV C={comp_real}"

        larg_txt = len(txt_chamada) * (8.0 * 0.75)
        draw.Text(xm - larg_txt / 2.0, ym + 6.0, 8.5, 0.0, txt_chamada)

    # --------------------------------------------------------------------------
    # CASO 2: DIREÇÃO VERTICAL (Barras correm em Y, distribuição em X)
    # --------------------------------------------------------------------------
    else:
        comp_total = altura_total
        xm = (x1 + x2) / 2.0
        ym = (y1 + y2) / 2.0

        if largura_total > 10.0:
            num_nervuras = max(int(round(largura_total / modulo_nervura)), 1)
        else:
            num_nervuras = 1

        qtd_nerv = int(dados.get("qtd_nerv", 1))
        dobra = float(dados.get("dobra", 0.0)) if setor == "NEGATIVA" else 0.0

        draw.level = 220
        draw.color = 3  # Verde
        draw.style = 0

        # 1. Traçar as barras verticais com transpasse se > 12m
        if comp_total <= comp_max_barra:
            draw.Line(xm, y1, xm, y2)
            if dobra > 0.0:
                draw.Line(xm, y1, xm - dobra, y1)
                draw.Line(xm, y2, xm - dobra, y2)
        else:
            comp_util = comp_max_barra - transpasse_cm
            y_atual = y1
            idx_b = 0

            while y_atual < y2:
                y_fim_b = min(y_atual + comp_max_barra, y2)
                off_x = 3.0 if (idx_b % 2 == 1) else 0.0

                draw.Line(xm + off_x, y_atual, xm + off_x, y_fim_b)

                if idx_b == 0 and dobra > 0.0:
                    draw.Line(xm + off_x, y_atual, xm + off_x - dobra, y_atual)
                if y_fim_b >= y2 and dobra > 0.0:
                    draw.Line(xm + off_x, y_fim_b, xm + off_x - dobra, y_fim_b)

                if y_fim_b >= y2:
                    break
                y_atual += comp_util
                idx_b += 1

        # 2. Linha de distribuição horizontal com setas
        if largura_total > 20.0:
            draw.level = 220
            draw.color = 3  # Verde
            draw.style = 1  # Tracejado
            y_dist = ym
            draw.Line(x1, y_dist, x2, y_dist)

            # Setas
            raio_seta = 6.0
            draw.style = 0
            draw.Line(x1, y_dist, x1 + raio_seta * 1.8, y_dist - raio_seta)
            draw.Line(x1, y_dist, x1 + raio_seta * 1.8, y_dist + raio_seta)
            draw.Line(x2, y_dist, x2 - raio_seta * 1.8, y_dist - raio_seta)
            draw.Line(x2, y_dist, x2 - raio_seta * 1.8, y_dist + raio_seta)

        # 3. Texto de chamada (Amarelo, 90 graus para vertical)
        draw.level = 220
        draw.color = 2  # Amarelo
        bitola_str = f"{bitola:g}"
        comp_real = int(round(comp_total + 2 * dobra))

        if setor == "POSITIVA":
            prefixo = f"{num_nervuras}x{qtd_nerv}" if qtd_nerv > 1 else f"{num_nervuras}x1"
            txt_chamada = f"{prefixo} {pos_id} %% {bitola_str} C/NERV C={comp_real}"
        else:
            txt_chamada = f"{num_nervuras} {pos_id} %% {bitola_str} C/NERV C={comp_real}"

        larg_txt = len(txt_chamada) * (8.0 * 0.75)
        draw.Text(xm + 6.0, ym - larg_txt / 2.0, 8.5, 90.0, txt_chamada)


# ==============================================================================
# ENTRY POINT PRINCIPAL NO TQS EAG
# ==============================================================================
def meucmd(eag, tqsjan):
    """Comando acionado pelo menu TQS na aba G3 Plugins."""
    try:
        dados = pedir_dados_laje()
        if dados is None:
            return

        # O usuário arrasta uma janela cobrindo a região desejada
        setor = dados.get("setor", "POSITIVA")
        msg_prompt = (
            "Arraste uma janela sobre as nervuras (Armadura Positiva)"
            if setor == "POSITIVA"
            else "Arraste uma janela sobre o apoio/viga (Armadura Negativa)"
        )

        addr, xs, ys, np, istat = eag.locate.Select(
            tqsjan,
            msg_prompt,
            TQSEag.EAG_IJANEL
        )
        if istat != 0:
            return

        todos_xs = []
        todos_ys = []

        # 1. Coletar os elementos englobados pela janela
        try:
            eag.locate.BeginSelection(tqsjan)
            while True:
                h_elem = eag.locate.NextSelection(tqsjan)
                if h_elem is None:
                    break
                tqsjan.dwg.iterator.SetPosition(h_elem)
                itipo = tqsjan.dwg.iterator.Next()
                if itipo == TQSDwg.DWGTYPE_LINE:
                    todos_xs.extend([tqsjan.dwg.iterator.x1, tqsjan.dwg.iterator.x2])
                    todos_ys.extend([tqsjan.dwg.iterator.y1, tqsjan.dwg.iterator.y2])
                elif itipo == TQSDwg.DWGTYPE_POLYLINE:
                    try:
                        npts = tqsjan.dwg.iterator.xySize
                        pts = [tqsjan.dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                        for pt in pts:
                            todos_xs.append(pt[0])
                            todos_ys.append(pt[1])
                    except Exception:
                        pass
                elif itipo == TQSDwg.DWGTYPE_INSERT:
                    todos_xs.append(tqsjan.dwg.iterator.x1)
                    todos_ys.append(tqsjan.dwg.iterator.y1)
        except Exception:
            pass

        # 2. Caso xs e ys retornem coordenadas de pontos ou valores diretos
        if xs is not None:
            if isinstance(xs, (list, tuple)):
                for x in xs:
                    if x is not None:
                        try:
                            fx = float(x)
                            if not math.isnan(fx):
                                todos_xs.append(fx)
                        except:
                            pass
            else:
                try:
                    fx = float(xs)
                    if not math.isnan(fx):
                        todos_xs.append(fx)
                except:
                    pass

        if ys is not None:
            if isinstance(ys, (list, tuple)):
                for y in ys:
                    if y is not None:
                        try:
                            fy = float(y)
                            if not math.isnan(fy):
                                todos_ys.append(fy)
                        except:
                            pass
            else:
                try:
                    fy = float(ys)
                    if not math.isnan(fy):
                        todos_ys.append(fy)
                except:
                    pass

        if not todos_xs or not todos_ys:
            return

        processar_armadura(tqsjan.dwg, todos_xs, todos_ys, dados)
        tqsjan.Regen()

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except:
            pass
