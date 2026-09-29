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
# INTERFACE GRÁFICA (HTA) - BITOLA E TRANSPASSE
# ==============================================================================
def pedir_dados_laje():
    """Abre janela para parâmetros da armação da faixa."""
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
        <title>Armação de Faixa - G3 Plugins</title>
        <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="ArmarFaixa" BORDER="dialog" INNERBORDER="no" SCROLL="no" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
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
                padding: 14px 18px 8px 18px;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }}
            .card {{
                background: #ffffff;
                border: 1px solid #e1bee7;
                border-radius: 8px;
                padding: 14px 16px;
                box-shadow: 0 1px 3px rgba(106,27,154,0.06);
            }}
            .card h3 {{
                margin: 0 0 12px 0;
                color: #4a148c;
                font-size: 12px;
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
                margin-bottom: 10px;
            }}
            .campo:last-child {{ margin-bottom: 0; }}
            label {{
                font-weight: 500;
                color: #42394d;
                font-size: 12.5px;
            }}
            input, select {{
                width: 140px;
                padding: 5px 8px;
                text-align: right;
                border: 1px solid #ceb3db;
                border-radius: 4px;
                background: #fdfbfe;
                font-size: 12.5px;
            }}
            select {{ text-align: left; width: 150px; }}
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
                padding: 8px 18px 14px 18px;
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

            function atualizarTranspasse() {{
                var bit = document.getElementById('bitola').value;
                if (tabelaTranspasse[bit]) {{
                    document.getElementById('transpasse').value = tabelaTranspasse[bit];
                }}
            }}

            function initDialog() {{
                try {{
                    window.resizeTo(450, 360);
                    window.moveTo((screen.availWidth - 450) / 2, (screen.availHeight - 360) / 2);
                }} catch(e) {{}}
                atualizarTranspasse();
            }}

            function confirmar() {{
                try {{
                    var bit = parseFloat(document.getElementById('bitola').value) || 16.0;
                    var trans = parseFloat(document.getElementById('transpasse').value.replace(',', '.')) || (tabelaTranspasse[bit] || 90.0);

                    var fso = new ActiveXObject("Scripting.FileSystemObject");
                    var a = fso.CreateTextFile("{json_js}", true);

                    var jsonStr = '{{' +
                        '"bitola":' + bit +
                        ',"transpasse":' + trans +
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
                <h1>Armação de Faixa de Laje</h1>
                <p>Plugin TQS &#9679 G3 Engenharia</p>
            </div>
        </div>

        <div class="container">
            <div class="card">
                <h3>Parâmetros da Faixa</h3>
                <div class="campo">
                    <label>Bitola da Barra (&Phi; mm):</label>
                    <select id="bitola" onchange="atualizarTranspasse()">
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
                    <input type="text" id="transpasse" value="90">
                </div>
            </div>

            <div class="info-box">
                💡 <b>Armação de Faixa:</b> Arraste uma janela sobre a faixa de cubetas. O plugin gera os trechos de até 11.80m, as retas verticais com setas e as cotas de transpasse.
            </div>
        </div>

        <div class="btns">
            <button onclick="window.close()">Cancelar</button>
            <button class="btn-gerar" onclick="confirmar()">Selecionar Faixa no EAG</button>
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
# COTAGEM DE TRANSPASSE (ESCALA EM CENTÍMETROS)
# ==============================================================================
def desenhar_cota_transpasse(draw, x_ini, x_fim, y_barra, dist_t):
    """
    Desenha a cota de transpasse elegante e proporcional no DWG.
    """
    y_cota = y_barra + 7.0
    draw.level = 220
    draw.color = 1  # Linha de cota em vermelho
    draw.style = 0

    # Linha horizontal de cota
    draw.Line(x_ini, y_cota, x_fim, y_cota)

    # Linhas de chamada verticais
    draw.Line(x_ini, y_barra - 1.0, x_ini, y_cota + 2.0)
    draw.Line(x_fim, y_barra - 1.0, x_fim, y_cota + 2.0)

    # Ticks inclinados a 45 graus
    tick = 2.0
    draw.Line(x_ini - tick, y_cota - tick, x_ini + tick, y_cota + tick)
    draw.Line(x_fim - tick, y_cota - tick, x_fim + tick, y_cota + tick)

    # Texto da cota (Amarelo, altura proporcional 8.5cm)
    draw.color = 2  # Amarelo
    txt_val = f"{int(round(dist_t))}"
    tam_txt = 8.5
    larg_txt = len(txt_val) * (tam_txt * 0.72)
    xm = (x_ini + x_fim) / 2.0
    draw.Text(xm - larg_txt / 2.0, y_cota + 2.0, tam_txt, 0.0, txt_val)


# ==============================================================================
# GERAÇÃO DA FAIXA: TRECHOS HORIZONTAIS DE 11.80m E RETAS VERTICAIS
# ==============================================================================
def processar_faixa_laje(dwg, linhas_coletadas, todos_xs, todos_ys, dados):
    """
    Gera a armadura horizontal para a faixa selecionada:
    - Identifica as nervuras em Y pelo vão selecionado (ou pelas linhas das cubetas).
    - Divide a extensão X em trechos comerciais de até 11.80m com transpasse.
    - Gera para cada trecho a sua barra horizontal, a sua reta vertical com setas (ex: 12x1) e a cota no transpasse.
    """
    draw = dwg.draw

    bitola = float(dados.get("bitola", 16.0))
    transpasse_cm = float(dados.get("transpasse", TABELA_TRANSPASSE.get(bitola, 90.0)))
    comp_max_barra = 1180.0  # Comprimento máximo comercial da barra (11.80m)

    x1_faixa = min(todos_xs)
    x2_faixa = max(todos_xs)
    y1_faixa = min(todos_ys)
    y2_faixa = max(todos_ys)

    largura_total = x2_faixa - x1_faixa
    altura_total = y2_faixa - y1_faixa

    if largura_total <= 5.0 or altura_total <= 5.0:
        return

    # 1. Identificar as linhas horizontais de cubetas dentro da seleção
    linhas_h = []
    for lx1, ly1, lx2, ly2 in linhas_coletadas:
        if abs(ly1 - ly2) <= 1.5 and abs(lx2 - lx1) >= 15.0:
            linhas_h.append((lx1, ly1, lx2, ly2))

    # 2. Identificar os eixos Y das nervuras
    niveis_y = []
    for lx1, ly1, lx2, ly2 in linhas_h:
        ym_l = (ly1 + ly2) / 2.0
        if not any(abs(ny - ym_l) <= 2.0 for ny in niveis_y):
            niveis_y.append(ym_l)
    niveis_y.sort()

    nervuras_y = []
    for i in range(len(niveis_y) - 1):
        dist = niveis_y[i + 1] - niveis_y[i]
        # Distância correspondente à largura da nervura (5 a 28 cm)
        if 5.0 <= dist <= 28.0:
            nervuras_y.append((niveis_y[i] + niveis_y[i + 1]) / 2.0)

    # Se não identificou pares explícitos de linhas, distribui pelo módulo padrão (65cm)
    if len(nervuras_y) < 1:
        modulo = 65.0
        num_n = max(int(round(altura_total / modulo)), 1)
        passo = altura_total / float(num_n)
        for i in range(num_n):
            nervuras_y.append(y1_faixa + (i + 0.5) * passo)

    nervuras_y.sort()
    num_nervuras = len(nervuras_y)

    y_min_n = min(nervuras_y)
    y_max_n = max(nervuras_y)
    y_mid_n = nervuras_y[num_nervuras // 2]

    # 3. Particionar a extensão horizontal X em trechos comerciais de até 11.80m
    trechos_x = []
    x_curr = x1_faixa
    idx_t = 0

    while x_curr < x2_faixa:
        x_fim_t = min(x_curr + comp_max_barra, x2_faixa)
        trechos_x.append((x_curr, x_fim_t, idx_t))

        if x_fim_t >= x2_faixa:
            break
        x_curr = x_fim_t - transpasse_cm
        idx_t += 1

    # 4. Desenhar para cada trecho: Barra, Reta Vertical de Distribuição e Cota
    pos_num = 1

    for i_t, (xa_t, xb_t, idx_trecho) in enumerate(trechos_x):
        comp_trecho = xb_t - xa_t
        xm_trecho = (xa_t + xb_t) / 2.0

        # Alternar o Y da barra nas emendas para que fiquem paralelas (de lado)
        off_y = 3.5 if (idx_trecho % 2 == 1) else 0.0
        y_barra = y_mid_n + off_y

        # A) Desenhar a barra horizontal
        draw.level = 220
        draw.color = 3  # Verde (Armadura)
        draw.style = 0
        draw.Line(xa_t, y_barra, xb_t, y_barra)

        # B) Cota de transpasse se for trecho subsequente
        if i_t > 0:
            x_trans_ini = xa_t
            x_trans_fim = trechos_x[i_t - 1][1]
            dist_t = x_trans_fim - x_trans_ini
            if dist_t > 1.0:
                desenhar_cota_transpasse(draw, x_trans_ini, x_trans_fim, y_barra, dist_t)

        # C) Reta vertical de distribuição com setas cobrindo as nervuras da faixa
        if num_nervuras > 1:
            draw.level = 220
            draw.color = 3  # Verde
            draw.style = 1  # Tracejado
            draw.Line(xm_trecho, y_min_n, xm_trecho, y_max_n)

            # Setas nas extremidades da reta vertical
            raio_seta = 4.0
            draw.style = 0
            draw.Line(xm_trecho, y_min_n, xm_trecho - raio_seta, y_min_n + raio_seta * 1.5)
            draw.Line(xm_trecho, y_min_n, xm_trecho + raio_seta, y_min_n + raio_seta * 1.5)
            draw.Line(xm_trecho, y_max_n, xm_trecho - raio_seta, y_max_n - raio_seta * 1.5)
            draw.Line(xm_trecho, y_max_n, xm_trecho + raio_seta, y_max_n - raio_seta * 1.5)

        # D) Texto de chamada do ferro (Amarelo)
        draw.level = 220
        draw.color = 2  # Amarelo
        draw.style = 0
        bitola_str = f"{bitola:g}"
        comp_int = int(round(comp_trecho))
        pos_str = f"P{pos_num}"

        if num_nervuras > 1:
            prefixo = f"{num_nervuras}x1"
        else:
            prefixo = "1"

        txt_chamada = f"{prefixo} {pos_str} %% {bitola_str} C/NERV C={comp_int}"
        tam_txt = 8.5
        larg_txt = len(txt_chamada) * (tam_txt * 0.72)

        # Posicionado 12cm abaixo da barra para clareza
        draw.Text(xm_trecho - larg_txt / 2.0, y_barra - 12.0, tam_txt, 0.0, txt_chamada)

        pos_num += 1


# ==============================================================================
# ENTRY POINT PRINCIPAL NO TQS EAG
# ==============================================================================
def meucmd(eag, tqsjan):
    """Comando acionado pelo menu TQS na aba G3 Plugins."""
    try:
        dados = pedir_dados_laje()
        if dados is None:
            return

        addr, xs, ys, np, istat = eag.locate.Select(
            tqsjan,
            "Selecione por janela a faixa de cubetas a ser armada",
            TQSEag.EAG_IJANEL
        )
        if istat != 0:
            return

        linhas_coletadas = []
        todos_xs = []
        todos_ys = []

        # 1. Coletar linhas e polilinhas das cubetas englobadas
        try:
            eag.locate.BeginSelection(tqsjan)
            while True:
                h_elem = eag.locate.NextSelection(tqsjan)
                if h_elem is None:
                    break
                tqsjan.dwg.iterator.SetPosition(h_elem)
                itipo = tqsjan.dwg.iterator.Next()

                if itipo == TQSDwg.DWGTYPE_LINE:
                    lx1 = tqsjan.dwg.iterator.x1
                    ly1 = tqsjan.dwg.iterator.y1
                    lx2 = tqsjan.dwg.iterator.x2
                    ly2 = tqsjan.dwg.iterator.y2
                    linhas_coletadas.append((lx1, ly1, lx2, ly2))
                    todos_xs.extend([lx1, lx2])
                    todos_ys.extend([ly1, ly2])

                elif itipo == TQSDwg.DWGTYPE_POLYLINE:
                    try:
                        npts = tqsjan.dwg.iterator.xySize
                        pts = [tqsjan.dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                        for i in range(len(pts)):
                            p_a = pts[i]
                            p_b = pts[(i + 1) % len(pts)]
                            linhas_coletadas.append((p_a[0], p_a[1], p_b[0], p_b[1]))
                            todos_xs.append(p_a[0])
                            todos_ys.append(p_a[1])
                    except Exception:
                        pass
                elif itipo == TQSDwg.DWGTYPE_INSERT:
                    todos_xs.append(tqsjan.dwg.iterator.x1)
                    todos_ys.append(tqsjan.dwg.iterator.y1)
        except Exception:
            pass

        # 2. Coordenadas dos cantos da janela de seleção
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

        processar_faixa_laje(tqsjan.dwg, linhas_coletadas, todos_xs, todos_ys, dados)
        tqsjan.Regen()

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except:
            pass
