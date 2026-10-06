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
                    window.resizeTo(450, 480);
                    window.moveTo((screen.availWidth - 450) / 2, (screen.availHeight - 480) / 2);
                }} catch(e) {{}}
                atualizarTranspasse();
            }}

            function confirmar() {{
                try {{
                    var bit = parseFloat(document.getElementById('bitola').value) || 16.0;
                    var trans = parseFloat(document.getElementById('transpasse').value.replace(',', '.')) || (tabelaTranspasse[bit] || 90.0);
                    var modulo = parseFloat(document.getElementById('modulo').value.replace(',', '.')) || 65.0;
                    var dobra = parseFloat(document.getElementById('dobra').value.replace(',', '.')) || 15.0;

                    var fso = new ActiveXObject("Scripting.FileSystemObject");
                    var a = fso.CreateTextFile("{json_js}", true);

                    var jsonStr = '{{' +
                        '"bitola":' + bit +
                        ',"transpasse":' + trans +
                        ',"modulo":' + modulo +
                        ',"dobra":' + dobra +
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
            <div class="card">
                <h3>Parâmetros do Ferro</h3>
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
                <div class="campo">
                    <label>Comprimento da Dobra (cm):</label>
                    <input type="text" id="dobra" value="15">
                </div>
                <div class="campo">
                    <label>Módulo da Nervura (cm):</label>
                    <input type="text" id="modulo" value="65">
                </div>
            </div>

            <div class="info-box">
                💡 <b>Como usar:</b> Após confirmar, clique em 2 pontos no desenho para definir
                a reta vertical (extensão das nervuras). O plugin conta automaticamente quantas
                nervuras cabem e coloca o ferro horizontal com o texto correto.
            </div>
        </div>

        <div class="btns">
            <button onclick="window.close()">Cancelar</button>
            <button class="btn-gerar" onclick="confirmar()">Definir Pontos no EAG</button>
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
# DETECTAR CANAIS REAIS DE NERVURA (IGNORANDO MACIÇOS E CAPITÉIS)
# ==============================================================================
def detectar_canais_reais_entre_pontos(dwg, y_min, y_max, x_reta, modulo=65.0):
    """
    Varre o desenho e encontra APENAS as nervuras reais (espaços entre 5cm e 24cm
    entre fileiras de cubetas), ignorando totalmente as regiões maciças de pilares/capitéis.
    """
    from collections import Counter

    y_horiz = []
    linhas_201_horiz = []

    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break

            nivel = getattr(dwg.iterator, "level", 0)

            # Nível 201 (Borda/Viga)
            if nivel == 201:
                if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                    lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                    lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                    if abs(ly1 - ly2) <= 5.0 and abs(lx2 - lx1) >= 5.0:
                        linhas_201_horiz.append((ly1 + ly2) / 2.0)
                elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                    try:
                        npts = dwg.iterator.xySize
                        pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                        for i in range(len(pts)):
                            p_a = pts[i]
                            p_b = pts[(i + 1) % len(pts)]
                            if abs(p_a[1] - p_b[1]) <= 5.0 and abs(p_b[0] - p_a[0]) >= 5.0:
                                linhas_201_horiz.append((p_a[1] + p_b[1]) / 2.0)
                    except Exception:
                        pass
                continue

            if nivel >= 220:
                continue

            # Linhas horizontais de cubeta
            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                dy = abs(ly2 - ly1)
                dx = abs(lx2 - lx1)
                ym = (ly1 + ly2) / 2.0

                if dy <= 3.0 and dx >= 8.0:
                    if (y_min - 20.0) <= ym <= (y_max + 20.0):
                        y_horiz.append(round(ym, 1))

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    for i in range(len(pts)):
                        p_a = pts[i]
                        p_b = pts[(i + 1) % len(pts)]
                        dy = abs(p_b[1] - p_a[1])
                        dx = abs(p_b[0] - p_a[0])
                        ym = (p_a[1] + p_b[1]) / 2.0
                        if dy <= 3.0 and dx >= 8.0:
                            if (y_min - 20.0) <= ym <= (y_max + 20.0):
                                y_horiz.append(round(ym, 1))
                except Exception:
                    pass
    except Exception:
        pass

    if not y_horiz:
        # Fallback modular
        extensao = abs(y_max - y_min)
        qtd = max(int(round(extensao / modulo)), 1)
        return [], qtd

    # Agrupar níveis horizontais com tolerância de 3cm
    contagem = Counter(y_horiz)
    niveis_unicos = sorted(contagem.keys())

    picos_y = []
    for y in niveis_unicos:
        qtd = contagem[y]
        if not picos_y or abs(y - picos_y[-1]['y']) > 3.0:
            picos_y.append({'y': y, 'qtd': qtd})
        else:
            tot = picos_y[-1]['qtd'] + qtd
            picos_y[-1]['y'] = (picos_y[-1]['y'] * picos_y[-1]['qtd'] + y * qtd) / tot
            picos_y[-1]['qtd'] = tot

    niveis = sorted([p['y'] for p in picos_y if p['qtd'] >= 1])

    # ── IDENTIFICAR APENAS OS VÃOS REAIS DE NERVURA ENTRE CUBETAS (5cm a 24cm) ──
    # Espaços maiores que 24cm (como maciços de pilares, aberturas e capitéis) são descartados
    canais_reais = []
    for i in range(len(niveis) - 1):
        gap = niveis[i + 1] - niveis[i]
        if 5.0 <= gap <= 24.0:
            canal_meio = (niveis[i] + niveis[i + 1]) / 2.0
            if y_min - 10.0 <= canal_meio <= y_max + 10.0:
                canais_reais.append(canal_meio)

    canais_reais = sorted(list(set(round(c, 1) for c in canais_reais)))
    qtd_final = max(len(canais_reais), 1)

    return canais_reais, qtd_final


# ==============================================================================
# ENCONTRAR LIMITES X A PARTIR DO NÍVEL 228 (LINHA BRANCA) E NÍVEL 201 (BORDO)
# ==============================================================================
def coletar_linhas_borda_dwg(dwg):
    """
    Varre o desenho em busca de linhas/polilinhas de contorno no Nível 228 (linha branca de borda)
    e Nível 201 (vigas/contorno da laje), separando horizontais e verticais.
    """
    linhas_borda_horiz = []
    linhas_borda_vert = []
    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break
            nivel = getattr(dwg.iterator, "level", 0)
            if nivel not in (228, 201):
                continue

            eh_228 = (nivel == 228)

            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                lx1 = dwg.iterator.x1
                ly1 = dwg.iterator.y1
                lx2 = dwg.iterator.x2
                ly2 = dwg.iterator.y2
                if abs(ly1 - ly2) <= 5.0 and abs(lx2 - lx1) >= 5.0:
                    linhas_borda_horiz.append((min(lx1, lx2), (ly1 + ly2) / 2.0, max(lx1, lx2), eh_228))
                elif abs(lx1 - lx2) <= 5.0 and abs(ly1 - ly2) >= 5.0:
                    linhas_borda_vert.append(((lx1 + lx2) / 2.0, min(ly1, ly2), max(ly1, ly2), eh_228))

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    for i in range(len(pts)):
                        p_a = pts[i]
                        p_b = pts[(i + 1) % len(pts)]
                        if abs(p_a[1] - p_b[1]) <= 5.0 and abs(p_b[0] - p_a[0]) >= 5.0:
                            linhas_borda_horiz.append((min(p_a[0], p_b[0]), (p_a[1] + p_b[1]) / 2.0, max(p_a[0], p_b[0]), eh_228))
                        elif abs(p_a[0] - p_b[0]) <= 5.0 and abs(p_b[1] - p_a[1]) >= 5.0:
                            linhas_borda_vert.append(((p_a[0] + p_b[0]) / 2.0, min(p_a[1], p_b[1]), max(p_a[1], p_b[1]), eh_228))
                except Exception:
                    pass
    except Exception:
        pass

    return linhas_borda_horiz, linhas_borda_vert


def encontrar_limites_x_bordas(dwg, y_min_band, y_max_band, x_ponto, canais_reais=None):
    """
    Determina os limites externos X (borda esquerda e borda direita) da laje
    para toda a faixa vertical [y_min_band, y_max_band], priorizando a linha branca
    do Nível 228 onde os ferros laterais devem parar.
    Garante que nenhuma barra da faixa ultrapasse a borda em qualquer uma das nervuras.
    """
    linhas_borda_horiz, linhas_borda_vert = coletar_linhas_borda_dwg(dwg)

    # Definir pontos Y de amostragem na faixa (todas as nervuras reais ou passos regulares)
    if canais_reais and len(canais_reais) > 0:
        pontos_y = [y for y in canais_reais if (y_min_band - 5.0) <= y <= (y_max_band + 5.0)]
        if not pontos_y:
            pontos_y = list(canais_reais)
    else:
        num_passos = max(int(round(abs(y_max_band - y_min_band) / 20.0)), 1)
        pontos_y = [y_min_band + i * (y_max_band - y_min_band) / float(num_passos) for i in range(num_passos + 1)]

    # Coletar todas as entidades de cubetas (nível < 220) na faixa vertical
    cubetas_segmentos = []
    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break
            nivel = getattr(dwg.iterator, "level", 0)
            if nivel >= 220:
                continue

            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                ymin_seg = min(ly1, ly2)
                ymax_seg = max(ly1, ly2)
                if ymax_seg >= (y_min_band - 30.0) and ymin_seg <= (y_max_band + 30.0):
                    if abs(lx2 - lx1) >= 8.0:
                        cubetas_segmentos.append((min(lx1, lx2), max(lx1, lx2), ymin_seg, ymax_seg))

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    if pts:
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        ymin_poly = min(ys)
                        ymax_poly = max(ys)
                        if ymax_poly >= (y_min_band - 30.0) and ymin_poly <= (y_max_band + 30.0):
                            cubetas_segmentos.append((min(xs), max(xs), ymin_poly, ymax_poly))
                except Exception:
                    pass
    except Exception:
        pass

    limites_esq = []
    limites_dir = []

    for y_amostra in pontos_y:
        # Cubetas cobrindo este Y específico
        xs_neste_y = []
        for xmin_c, xmax_c, ymin_c, ymax_c in cubetas_segmentos:
            if (ymin_c - 20.0) <= y_amostra <= (ymax_c + 20.0):
                xs_neste_y.extend([xmin_c, xmax_c])

        # Linhas verticais de borda cobrindo este Y específico
        linhas_vert_y = []
        for x_lim, y_a, y_b, eh_228 in linhas_borda_vert:
            if (min(y_a, y_b) - 40.0) <= y_amostra <= (max(y_a, y_b) + 40.0):
                linhas_vert_y.append((x_lim, eh_228))

        if xs_neste_y:
            x_cub_min = min(xs_neste_y)
            x_cub_max = max(xs_neste_y)

            # Borda esquerda
            cands_esq_228 = [x for x, eh_228 in linhas_vert_y if eh_228 and x <= x_cub_min + 30.0]
            cands_esq_todos = [x for x, eh_228 in linhas_vert_y if x <= x_cub_min + 30.0]
            if cands_esq_228:
                limites_esq.append(max(cands_esq_228))
            elif cands_esq_todos:
                limites_esq.append(max(cands_esq_todos))
            else:
                limites_esq.append(x_cub_min - 15.0)

            # Borda direita
            cands_dir_228 = [x for x, eh_228 in linhas_vert_y if eh_228 and x >= x_cub_max - 30.0]
            cands_dir_todos = [x for x, eh_228 in linhas_vert_y if x >= x_cub_max - 30.0]
            if cands_dir_228:
                limites_dir.append(min(cands_dir_228))
            elif cands_dir_todos:
                limites_dir.append(min(cands_dir_todos))
            else:
                limites_dir.append(x_cub_max + 15.0)
        elif linhas_vert_y:
            cands_228 = [x for x, eh_228 in linhas_vert_y if eh_228]
            if cands_228:
                esq = [x for x in cands_228 if x < x_ponto]
                dir = [x for x in cands_228 if x > x_ponto]
                if esq:
                    limites_esq.append(max(esq))
                if dir:
                    limites_dir.append(min(dir))
            else:
                esq = [x for x, _ in linhas_vert_y if x < x_ponto]
                dir = [x for x, _ in linhas_vert_y if x > x_ponto]
                if esq:
                    limites_esq.append(max(esq))
                if dir:
                    limites_dir.append(min(dir))

    # O limite da faixa inteira deve ser o mais restritivo (nenhuma barra sai para fora)
    x_left = max(limites_esq) if limites_esq else None
    x_right = min(limites_dir) if limites_dir else None

    return x_left, x_right


def coletar_obstaculos_e_vazios(dwg):
    """
    Varre o desenho em busca de obstáculos e aberturas:
    1. Elementos no Nível 237 (rosa)
    2. Linhas e polilinhas diagonais formando o 'X' dos espaços vazios / furos / shafts
    3. Linhas e caixas vermelhas (cor 1) que delimitam aberturas
    Retorna lista de dicionários com limites: [{'xmin': ..., 'xmax': ..., 'ymin': ..., 'ymax': ...}, ...]
    """
    obstaculos = []
    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break
            nivel = getattr(dwg.iterator, "level", 0)
            cor = getattr(dwg.iterator, "color", 0)

            # 1. Elementos rosa no Nível 237
            if nivel == 237:
                if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                    lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                    lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                    obstaculos.append({
                        'xmin': min(lx1, lx2),
                        'xmax': max(lx1, lx2),
                        'ymin': min(ly1, ly2),
                        'ymax': max(ly1, ly2)
                    })
                elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                    try:
                        npts = dwg.iterator.xySize
                        pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                        if pts:
                            xs = [p[0] for p in pts]
                            ys = [p[1] for p in pts]
                            obstaculos.append({
                                'xmin': min(xs),
                                'xmax': max(xs),
                                'ymin': min(ys),
                                'ymax': max(ys)
                            })
                    except Exception:
                        pass
                continue

            # 2. Linhas diagonais com 'X' (vazios / aberturas) e contornos vermelhos
            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                dx = abs(lx2 - lx1)
                dy = abs(ly2 - ly1)
                if dx >= 15.0 and dy >= 15.0:
                    # Linha diagonal de 'X'
                    obstaculos.append({
                        'xmin': min(lx1, lx2),
                        'xmax': max(lx1, lx2),
                        'ymin': min(ly1, ly2),
                        'ymax': max(ly1, ly2)
                    })
                elif cor == 1 and (dx >= 15.0 or dy >= 15.0):
                    # Contorno vermelho de abertura
                    obstaculos.append({
                        'xmin': min(lx1, lx2),
                        'xmax': max(lx1, lx2),
                        'ymin': min(ly1, ly2),
                        'ymax': max(ly1, ly2)
                    })

            # 3. Polilinhas com segmentos diagonais ou caixas vermelhas de abertura
            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    if pts:
                        tem_diag = False
                        for i in range(len(pts) - 1):
                            p_a = pts[i]
                            p_b = pts[i + 1]
                            if abs(p_b[0] - p_a[0]) >= 15.0 and abs(p_b[1] - p_a[1]) >= 15.0:
                                tem_diag = True
                                break
                        if tem_diag or cor == 1:
                            xs = [p[0] for p in pts]
                            ys = [p[1] for p in pts]
                            obstaculos.append({
                                'xmin': min(xs),
                                'xmax': max(xs),
                                'ymin': min(ys),
                                'ymax': max(ys)
                            })
                except Exception:
                    pass
    except Exception:
        pass

    return obstaculos


def coletar_obstaculos_nivel_237(dwg):
    """Mantido por compatibilidade: redireciona para coletar_obstaculos_e_vazios."""
    return coletar_obstaculos_e_vazios(dwg)


def encontrar_limites_x_rib(dwg, y_rib, x_ponto, cobrimento_237=2.5):
    """
    Determina os limites X (borda esquerda e direita) da armadura para uma nervura na cota y_rib:
    1. Busca os limites no Nível 228 (linha branca de borda) e Nível 201 na vizinhança de y_rib.
    2. Aplica cobrimento de 2.5cm nas dobras das bordas (recuo para dentro da laje).
    3. Se houver elemento no Nível 237 (rosa) ou VAZIO com 'X' cobrindo a cota y_rib (+/- 12cm):
       - Para antes dele com cobrimento de 2.5cm (x_obs_min - 2.5 à direita ou x_obs_max + 2.5 à esquerda).
    Retorna: (x_left, x_right, parou_237_esq, parou_237_dir)
    """
    x_left_borda, x_right_borda = encontrar_limites_x_bordas(dwg, y_rib - 15.0, y_rib + 15.0, x_ponto)

    cobrimento_val = float(cobrimento_237)

    if x_left_borda is not None:
        x_left = x_left_borda + cobrimento_val
    else:
        x_left = x_ponto - 500.0

    if x_right_borda is not None:
        x_right = x_right_borda - cobrimento_val
    else:
        x_right = x_ponto + 500.0

    parou_237_esq = False
    parou_237_dir = False

    obstaculos = coletar_obstaculos_e_vazios(dwg)
    if obstaculos:
        obst_na_nervura = [
            obs for obs in obstaculos
            if obs['ymin'] <= (y_rib + 12.0) and obs['ymax'] >= (y_rib - 12.0)
        ]

        obs_dir = [obs['xmin'] for obs in obst_na_nervura if obs['xmin'] > x_ponto]
        if obs_dir:
            x_obs_dir = min(obs_dir)
            x_novo_dir = x_obs_dir - cobrimento_val
            if x_novo_dir < x_right:
                x_right = x_novo_dir
                parou_237_dir = True

        obs_esq = [obs['xmax'] for obs in obst_na_nervura if obs['xmax'] < x_ponto]
        if obs_esq:
            x_obs_esq = max(obs_esq)
            x_novo_esq = x_obs_esq + cobrimento_val
            if x_novo_esq > x_left:
                x_left = x_novo_esq
                parou_237_esq = True

    return x_left, x_right, parou_237_esq, parou_237_dir


def encontrar_limites_x_com_nivel_237(dwg, y_min_band, y_max_band, x_ponto, cobrimento_237=2.5, canais_reais=None):
    """
    Determina os limites X (borda esquerda e direita) da armadura para TODA a faixa vertical [y_min_band, y_max_band].
    """
    x_left_borda, x_right_borda = encontrar_limites_x_bordas(dwg, y_min_band, y_max_band, x_ponto, canais_reais)

    cobrimento_val = float(cobrimento_237)

    if x_left_borda is not None:
        x_left = x_left_borda + cobrimento_val
    else:
        x_left = x_ponto - 500.0

    if x_right_borda is not None:
        x_right = x_right_borda - cobrimento_val
    else:
        x_right = x_ponto + 500.0

    parou_237_esq = False
    parou_237_dir = False

    obstaculos = coletar_obstaculos_e_vazios(dwg)
    if obstaculos:
        obst_na_faixa = [
            obs for obs in obstaculos
            if obs['ymin'] <= (y_max_band + 5.0) and obs['ymax'] >= (y_min_band - 5.0)
        ]

        obs_dir = [obs['xmin'] for obs in obst_na_faixa if obs['xmin'] > x_ponto]
        if obs_dir:
            x_obs_dir = min(obs_dir)
            x_novo_dir = x_obs_dir - cobrimento_val
            if x_novo_dir < x_right:
                x_right = x_novo_dir
                parou_237_dir = True

        obs_esq = [obs['xmax'] for obs in obst_na_faixa if obs['xmax'] < x_ponto]
        if obs_esq:
            x_obs_esq = max(obs_esq)
            x_novo_esq = x_obs_esq + cobrimento_val
            if x_novo_esq > x_left:
                x_left = x_novo_esq
                parou_237_esq = True

    return x_left, x_right, parou_237_esq, parou_237_dir


# ==============================================================================
# GERAÇÃO DO FERRO HORIZONTAL COM RETA VERTICAL E CONTAGEM
# ==============================================================================
def processar_ferro_por_2pontos(dwg, x1, y1, x2, y2, dados):
    """
    A partir dos 2 pontos selecionados pelo usuário:
    1. Usa o X dos pontos como posição da reta vertical.
    2. Usa o Y dos pontos como extensão vertical.
    3. Detecta os canais reais de nervura (ignorando maciços de pilares).
    4. Agrupa nervuras contíguas com a mesma geometria (permite que nervuras livres continuem
       e nervuras com obstáculo parem no Nível 237 rosa com cobrimento 2.5cm).
    5. Divide em trechos comerciais com transpasse e desenha armadura, chamada e distribuição.
    """
    draw = dwg.draw

    bitola = float(dados.get("bitola", 16.0))
    transpasse_cm = float(dados.get("transpasse", TABELA_TRANSPASSE.get(bitola, 90.0)))
    comp_dobra = float(dados.get("dobra", 15.0))
    comp_max_barra = 1180.0  # 11.80m
    modulo = float(dados.get("modulo", 65.0))

    # ── Os 2 pontos definem a reta vertical ──
    x_reta = (x1 + x2) / 2.0
    y_p1 = min(y1, y2)
    y_p2 = max(y1, y2)

    extensao_vertical = y_p2 - y_p1
    if extensao_vertical < 10.0:
        return

    # ── Detectar canais reais (espaços vazios entre cubetas) ──
    canais_reais, total_nervuras = detectar_canais_reais_entre_pontos(dwg, y_p1, y_p2, x_reta, modulo)

    # ── Identificar grupos contíguos de nervuras com mesma geometria/obstáculos ──
    grupos = []
    if canais_reais:
        grupo_atual = None
        for y_rib in canais_reais:
            x_l, x_r, p_esq, p_dir = encontrar_limites_x_rib(dwg, y_rib, x_reta, cobrimento_237=2.5)
            if grupo_atual is None:
                grupo_atual = {
                    'ribs': [y_rib],
                    'x_left': x_l,
                    'x_right': x_r,
                    'parou_esq': p_esq,
                    'parou_dir': p_dir
                }
            else:
                mesmo_x_esq = (abs(x_l - grupo_atual['x_left']) <= 3.0)
                mesmo_x_dir = (abs(x_r - grupo_atual['x_right']) <= 3.0)
                mesmo_p_esq = (p_esq == grupo_atual['parou_esq'])
                mesmo_p_dir = (p_dir == grupo_atual['parou_dir'])
                if mesmo_x_esq and mesmo_x_dir and mesmo_p_esq and mesmo_p_dir:
                    grupo_atual['ribs'].append(y_rib)
                else:
                    grupos.append(grupo_atual)
                    grupo_atual = {
                        'ribs': [y_rib],
                        'x_left': x_l,
                        'x_right': x_r,
                        'parou_esq': p_esq,
                        'parou_dir': p_dir
                    }
        if grupo_atual:
            grupos.append(grupo_atual)
    else:
        x_l, x_r, p_esq, p_dir = encontrar_limites_x_rib(dwg, (y_p1 + y_p2) / 2.0, x_reta, cobrimento_237=2.5)
        grupos.append({
            'ribs': [(y_p1 + y_p2) / 2.0],
            'x_left': x_l,
            'x_right': x_r,
            'parou_esq': p_esq,
            'parou_dir': p_dir
        })

    # ── Desenhar cada grupo homogêneo ──
    pos_num = 1

    for g_idx, grupo in enumerate(grupos):
        qtd_nervuras_g = len(grupo['ribs'])

        if qtd_nervuras_g > 1:
            y_min_g = min(grupo['ribs'])
            y_max_g = max(grupo['ribs'])
            y_barra = grupo['ribs'][-2] if len(grupo['ribs']) >= 2 else grupo['ribs'][0]
        else:
            y_barra = grupo['ribs'][0]
            y_min_g = y_barra - (modulo / 2.0)
            y_max_g = y_barra + (modulo / 2.0)

        # Se for único grupo, manter exatamente os pontos clicados
        if len(grupos) == 1:
            y_min_g = y_p1
            y_max_g = y_p2
        else:
            if g_idx == 0:
                y_min_g = min(y_min_g, y_p1)
            if g_idx == len(grupos) - 1:
                y_max_g = max(y_max_g, y_p2)

        x_ini_ferro = grupo['x_left']
        x_fim_ferro = grupo['x_right']

        # Dobras nas pontas (se parou no Nível 237 é barra reta sem dobra)
        dobra_esq_efetiva = 0.0 if grupo['parou_esq'] else comp_dobra
        dobra_dir_efetiva = 0.0 if grupo['parou_dir'] else comp_dobra

        # ── Dividir em trechos comerciais (≤ 11.80m) com transpasse ──
        trechos_x = []
        x_curr = x_ini_ferro
        idx_t = 0

        while x_curr < x_fim_ferro:
            x_fim_t = min(x_curr + comp_max_barra, x_fim_ferro)
            trechos_x.append((x_curr, x_fim_t, idx_t))

            if x_fim_t >= x_fim_ferro:
                break
            x_curr = x_fim_t - transpasse_cm
            idx_t += 1

        # ── Desenhar cada trecho do grupo ──
        for i_t, (xa_t, xb_t, idx_trecho) in enumerate(trechos_x):
            comp_trecho = xb_t - xa_t
            xm_trecho = (xa_t + xb_t) / 2.0

            off_y = 0.0
            if len(trechos_x) > 1:
                off_y = 1.5 if (idx_trecho % 2 == 1) else -1.5

            y_ferro = y_barra + off_y

            eh_ponta_esq = (i_t == 0)
            eh_ponta_dir = (i_t == len(trechos_x) - 1)

            # ── SMARTREBAR NATIVO CONECTADO COM QUANTIDADE EXATA ──
            usou_smart = False
            try:
                sr = TQSDwg.SmartRebar(dwg)
                sr.type = getattr(TQSDwg, "ICPFRT", 1)
                sr.diameter = float(bitola)
                sr.mark = int(pos_num)
                sr.quantity = int(qtd_nervuras_g)
                sr.spacing = float(modulo)
                sr.ribbed = 1
                sr.showRibbed = 1
                sr.straightBarMainLength = float(comp_trecho)
                sr.straightBarLeftLength = float(dobra_esq_efetiva if eh_ponta_esq else 0.0)
                sr.straightBarRightLength = float(dobra_dir_efetiva if eh_ponta_dir else 0.0)
                sr.straightBarTextPosition = 2
                sr.straightBarZone = getattr(TQSDwg, "ICPPOS", 0)

                # Associar a faixa de distribuição conectada no 1º trecho
                if i_t == 0 and qtd_nervuras_g > 1:
                    comp_faixa = abs(y_max_g - y_min_g)
                    esp_faixa = (comp_faixa / float(qtd_nervuras_g)) if qtd_nervuras_g > 0 else float(modulo)
                    sr.RebarDistrAdd(
                        getattr(TQSDwg, "ICPESP", 2),
                        90.0,
                        x_reta, y_min_g,
                        x_reta, y_max_g,
                        x_reta, (y_min_g + y_max_g) / 2.0,
                        0, 0, 0, 0, 0,
                        getattr(TQSDwg, "ICPCENTR_CENTRAD", 0),
                        getattr(TQSDwg, "ICPQUEBR_SEMQUEBRA", 0),
                        "", 0, 0, 1, 0, 0,
                        float(esp_faixa), 1.0
                    )

                sr.RebarLine(xa_t, y_ferro, 0.0, 1.0, 1, 0, 1, 0, 220, 0, 3)
                usou_smart = True
            except Exception:
                usou_smart = False

            # ── FALLBACK CAD DIRETO SE NECESSÁRIO ──
            if not usou_smart:
                # A) Barra horizontal
                draw.level = 220
                draw.color = 3  # Verde (Armadura)
                draw.style = 0  # Contínuo
                draw.Line(xa_t, y_ferro, xb_t, y_ferro)

                # Dobras nas extremidades da laje
                if eh_ponta_esq and dobra_esq_efetiva > 0:
                    draw.Line(xa_t, y_ferro, xa_t, y_ferro - dobra_esq_efetiva)

                if eh_ponta_dir and dobra_dir_efetiva > 0:
                    draw.Line(xb_t, y_ferro, xb_t, y_ferro - dobra_dir_efetiva)

                # C) Reta vertical com setas (linha contínua verde)
                if i_t == 0 and qtd_nervuras_g > 1:
                    draw.level = 220
                    draw.color = 3  # Verde
                    draw.style = 0  # Linha Contínua Sólida
                    draw.Line(x_reta, y_min_g, x_reta, y_max_g)

                    larg_seta = 8.0
                    alt_seta = 12.0
                    draw.Line(x_reta - larg_seta, y_min_g, x_reta + larg_seta, y_min_g)
                    draw.Line(x_reta, y_min_g, x_reta - (larg_seta * 0.7), y_min_g + alt_seta)
                    draw.Line(x_reta, y_min_g, x_reta + (larg_seta * 0.7), y_min_g + alt_seta)

                    draw.Line(x_reta - larg_seta, y_max_g, x_reta + larg_seta, y_max_g)
                    draw.Line(x_reta, y_max_g, x_reta - (larg_seta * 0.7), y_max_g - alt_seta)
                    draw.Line(x_reta, y_max_g, x_reta + (larg_seta * 0.7), y_max_g - alt_seta)

                # D) Texto de chamada do ferro (Amarelo)
                draw.level = 220
                draw.color = 2  # Amarelo
                draw.style = 0
                bitola_str = f"{bitola:g}"
                comp_total_barra = comp_trecho + (dobra_esq_efetiva if eh_ponta_esq else 0.0) + (dobra_dir_efetiva if eh_ponta_dir else 0.0)
                comp_int = int(round(comp_total_barra))
                pos_str = f"P{pos_num}"

                if qtd_nervuras_g > 1:
                    prefixo = f"{qtd_nervuras_g}x1"
                else:
                    prefixo = "1"

                txt_chamada = f"{prefixo} {pos_str} %% {bitola_str} C/NERV C={comp_int}"
                tam_txt = 8.5
                larg_txt = len(txt_chamada) * (tam_txt * 0.72)
                draw.Text(xm_trecho - larg_txt / 2.0, y_ferro - 12.0, tam_txt, 0.0, txt_chamada)

            # E) Texto com o valor da dobra nas extremidades
            draw.level = 220
            draw.color = 2  # Amarelo
            draw.style = 0
            if eh_ponta_esq and dobra_esq_efetiva > 0:
                txt_d_esq = f"{int(round(dobra_esq_efetiva))}"
                draw.Text(xa_t - 7.5, y_ferro - (dobra_esq_efetiva / 2.0) - 2.0, 6.5, 0.0, txt_d_esq)

            if eh_ponta_dir and dobra_dir_efetiva > 0:
                txt_d_dir = f"{int(round(dobra_dir_efetiva))}"
                draw.Text(xb_t + 2.5, y_ferro - (dobra_dir_efetiva / 2.0) - 2.0, 6.5, 0.0, txt_d_dir)

            # B) Cota de transpasse se for trecho posterior
            if i_t > 0:
                x_trans_ini = xa_t
                x_trans_fim = trechos_x[i_t - 1][1]
                dist_t = x_trans_fim - x_trans_ini
                if dist_t > 1.0:
                    desenhar_cota_transpasse(draw, x_trans_ini, x_trans_fim, y_ferro, dist_t)

            pos_num += 1


# ==============================================================================
# ENTRY POINT PRINCIPAL NO TQS EAG (MODO CONTÍNUO MULTI-FAIXAS)
# ==============================================================================
def meucmd(eag, tqsjan):
    """
    Comando acionado pelo menu TQS na aba G3 Plugins.

    Fluxo Contínuo / Múltiplas Faixas:
    1. Abre janela HTA para parâmetros (bitola, transpasse, módulo) uma única vez.
    2. Em loop contínuo:
       - Pede o 1º ponto (ou <Enter>/<Esc> para finalizar).
       - Pede o 2º ponto (com linha elástica).
       - Desenha o ferro horizontal e a linha vertical conectada.
       - Atualiza a tela (Regen) e já pede a próxima faixa.
    """
    try:
        # 1. Parâmetros via HTA (apenas uma vez para todas as faixas)
        dados = pedir_dados_laje()
        if dados is None:
            return

        faixa_idx = 1
        while True:
            # 2. Primeiro ponto da faixa (ou <Esc> para encerrar)
            prompt1 = f"Clique o 1º ponto da {faixa_idx}ª faixa (ou <Esc> para encerrar):"
            icod1, x1, y1 = eag.locate.GetPoint(tqsjan, prompt1)
            if icod1 != 1:
                break

            # 3. Segundo ponto da faixa com linha elástica (ou <Esc> para cancelar esta faixa)
            prompt2 = f"Clique o 2º ponto da {faixa_idx}ª faixa (ou <Esc> para cancelar):"
            icod2, x2, y2 = eag.locate.GetSecondPoint(
                tqsjan, x1, y1,
                TQSEag.EAG_RUBLINEAR,
                TQSEag.EAG_RUBRET_NAOPREEN,
                prompt2
            )
            if icod2 != 1:
                break

            # 4. Processar e desenhar a faixa imediatamente
            processar_ferro_por_2pontos(tqsjan.dwg, x1, y1, x2, y2, dados)
            tqsjan.Regen()

            faixa_idx += 1

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except:
            pass
