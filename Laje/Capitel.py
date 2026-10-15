# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - ARMAÇÃO DE CAPITEL (TQS EAG)
================================================================================
Este módulo implementa o detalhamento de armaduras para capitéis em lajes
nervuradas e maciças no TQS EAG.
================================================================================
"""
import os
import json
import math
import subprocess
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag


def pedir_dados_capitel():
    """Abre janela nativa HTA para configuração dos parâmetros do capitel."""
    caminho_script = os.path.dirname(os.path.abspath(__file__))
    hta_path = os.path.join(caminho_script, "dialogo_capitel.hta")
    json_path = os.path.join(caminho_script, "dados_capitel_temp.json")

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
        <title>Armação de Capitel - G3 Plugins</title>
        <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="ArmarCapitel" BORDER="dialog" INNERBORDER="no" SCROLL="no" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
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
                background: linear-gradient(135deg, #0d47a1 0%, #1976d2 100%);
                color: #ffffff;
                padding: 12px 18px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.25);
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .topbar h1 {{
                font-size: 15px;
                margin: 0;
                font-weight: 700;
                letter-spacing: 0.3px;
                color: #ffffff;
            }}
            .topbar p {{
                margin: 2px 0 0 0;
                font-size: 11px;
                color: #bbdefb;
                font-weight: 500;
            }}
            .container {{
                padding: 14px 18px 10px 18px;
            }}
            .card {{
                background: #ffffff;
                border: 1px solid #bbdefb;
                border-radius: 6px;
                padding: 14px;
                margin-bottom: 12px;
                box-shadow: 0 1px 4px rgba(13,71,161,0.08);
            }}
            .card h3 {{
                font-size: 12px;
                margin: 0 0 12px 0;
                color: #0d47a1;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                border-bottom: 1px solid #e3f2fd;
                padding-bottom: 6px;
                font-weight: 700;
            }}
            .campo {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }}
            .campo label {{
                font-weight: 500;
                color: #424242;
            }}
            .campo input[type="text"], .campo select {{
                width: 140px;
                padding: 5px 8px;
                border: 1px solid #90caf9;
                border-radius: 4px;
                font-size: 12px;
                text-align: right;
                background: #ffffff;
                color: #0d47a1;
                font-weight: 600;
            }}
            .campo input[type="text"]:focus, .campo select:focus {{
                border-color: #1976d2;
                outline: none;
                box-shadow: 0 0 5px rgba(25,118,210,0.35);
            }}
            .info-box {{
                background: #e3f2fd;
                border-left: 3px solid #1976d2;
                padding: 8px 12px;
                font-size: 11px;
                color: #0d47a1;
                border-radius: 0 4px 4px 0;
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
                border: 1px solid #bbdefb;
                border-radius: 5px;
                background: #fff;
                font-size: 12px;
                font-weight: 600;
                color: #0d47a1;
            }}
            button:hover {{ background: #e3f2fd; }}
            .btn-gerar {{
                background: linear-gradient(135deg, #1976d2 0%, #0d47a1 100%);
                color: #ffffff;
                border: none;
                font-weight: 700;
                box-shadow: 0 2px 4px rgba(13,71,161,0.35);
            }}
            .btn-gerar:hover {{
                background: linear-gradient(135deg, #1565c0 0%, #0a3880 100%);
                color: #ffffff;
            }}
        </style>
        <script language="javascript">
            window.onload = function() {{
                window.resizeTo(450, 520);
                window.moveTo((screen.width - 450) / 2, (screen.height - 520) / 2);
            }};

            function confirmar() {{
                var espacamentoVal = parseFloat(document.getElementById("espacamento").value.replace(',', '.')) || 15.0;
                var dobraVal = parseFloat(document.getElementById("dobra").value.replace(',', '.')) || 20.0;
                var dados = {{
                    bitola: parseFloat(document.getElementById("bitola").value),
                    espacamento: espacamentoVal,
                    dobra: dobraVal,
                    direcao: document.getElementById("direcao").value,
                    adicionar_mais_um: document.getElementById("adicionar_mais_um").checked
                }};

                try {{
                    var fso = new ActiveXObject("Scripting.FileSystemObject");
                    var a = fso.CreateTextFile("{json_js}", true);
                    a.WriteLine(JSON.stringify(dados));
                    a.Close();
                }} catch (e) {{
                    alert("Erro ao salvar dados: " + e.message);
                }}

                window.close();
            }}
        </script>
    </head>
    <body>
        <div class="topbar">
            <div style="font-size:20px;"></div>
            <div>
                <h1>Armação de Capitel</h1>
                <p>G3 Plugins - Ediglânthio Samuel Araújo Brandão - TQS</p>
            </div>
        </div>

        <div class="container">
            <div class="card">
                <h3>Parâmetros da Armadura</h3>
                <div class="campo">
                    <label>Direção do Ferro:</label>
                    <select id="direcao">
                        <option value="horizontal" selected>Horizontal</option>
                        <option value="vertical">Vertical</option>
                    </select>
                </div>
                <div class="campo">
                    <label>Bitola dos Ferros:</label>
                    <select id="bitola">
                        <option value="6.3">Ø 6.3 mm</option>
                        <option value="8.0">Ø 8.0 mm</option>
                        <option value="10.0" selected>Ø 10.0 mm</option>
                        <option value="12.5">Ø 12.5 mm</option>
                        <option value="16.0">Ø 16.0 mm</option>
                        <option value="20.0">Ø 20.0 mm</option>
                    </select>
                </div>
                <div class="campo">
                    <label>Espaçamento (cm):</label>
                    <input type="text" id="espacamento" value="15">
                </div>
                <div class="campo">
                    <label>Tamanho da Dobra (cm):</label>
                    <input type="text" id="dobra" value="20">
                </div>
                <div class="campo" style="margin-top:10px; padding-top:8px; border-top:1px dashed #90caf9;">
                    <label style="color:#0d47a1; font-weight:600;">Adicionar +1 barra:</label>
                    <input type="checkbox" id="adicionar_mais_um" checked style="width:18px; height:18px; cursor:pointer;">
                </div>
            </div>

            <div class="info-box">
                💡 <b>Instrução:</b> Após confirmar, arraste uma janela (retângulo por 2 pontos) cobrindo a laje ou os capitéis desejados. O plugin identifica os pilares e as cubetas ao redor para armar os capitéis com a quantidade e bitola selecionadas.
            </div>
        </div>

        <div class="btns">
            <button onclick="window.close()">Cancelar</button>
            <button class="btn-gerar" onclick="confirmar()">Armar Capitéis</button>
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
# CONSTANTES
# ==============================================================================
COMP_DOBRA = 20.0          # Dobra nas pontas do ferro (cm)
COBRIMENTO = 2.5           # Cobrimento nas pontas (cm)
COR_PILAR = 1              # Cor vermelha (pilares)
MODULO_CUBETA = 65.0


def _iter_segmentos(dwg):
    """Gera (nivel, cor, x1, y1, x2, y2) para todas as linhas e segmentos de polilinha."""
    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break
            nivel = getattr(dwg.iterator, "level", 0)
            cor = getattr(dwg.iterator, "color", -1)
            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                yield (nivel, cor, dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2)
            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    for i in range(len(pts) - 1):
                        yield (nivel, cor, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
                    if len(pts) >= 3 and (abs(pts[0][0] - pts[-1][0]) > 0.1 or abs(pts[0][1] - pts[-1][1]) > 0.1):
                        yield (nivel, cor, pts[-1][0], pts[-1][1], pts[0][0], pts[0][1])
                except Exception:
                    pass
    except Exception:
        return


def coletar_geometria(dwg, janela=None):
    """
    Varre o desenho e separa:
    - segmentos e polilinhas de pilar (Nível 227 ou cor vermelha, comp <= 300cm)
    - faces de cubeta verticais e horizontais (linhas curtas, nível < 220, exceto 201/227/228/237)
    Se 'janela' (xmin, ymin, xmax, ymax) for fornecida, filtra os elementos na região com margem.
    """
    seg_pilar = []
    pilares_prontos = []
    faces_v = []   # (x, y_lo, y_hi)
    faces_h = []   # (y, x_lo, x_hi)
    comp_max_face = 1.6 * MODULO_CUBETA

    margem = 600.0
    if janela:
        xmin_g = janela[0] - margem
        ymin_g = janela[1] - margem
        xmax_g = janela[2] + margem
        ymax_g = janela[3] + margem
    else:
        xmin_g = ymin_g = -1e9
        xmax_g = ymax_g = 1e9

    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break
            nivel = getattr(dwg.iterator, "level", 0)
            cor = getattr(dwg.iterator, "color", -1)

            # Ignora armaduras desenhadas (nível >= 220), MAS mantém o Nível 227 (pilares/estruturas vermelhas)
            if nivel >= 220 and nivel != 227:
                continue

            eh_pilar = (nivel == 227) or (cor == COR_PILAR) or (cor in (-1, 0, 1) and nivel == 201)

            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                xa, ya = dwg.iterator.x1, dwg.iterator.y1
                xb, yb = dwg.iterator.x2, dwg.iterator.y2
                x_min_s, x_max_s = min(xa, xb), max(xa, xb)
                y_min_s, y_max_s = min(ya, yb), max(ya, yb)

                if x_max_s < xmin_g or x_min_s > xmax_g or y_max_s < ymin_g or y_min_s > ymax_g:
                    continue

                comp_seg = math.hypot(xb - xa, yb - ya)

                # Pilar no Nível 227 ou vermelho
                if eh_pilar and nivel not in (228, 237):
                    if 8.0 <= comp_seg <= 300.0:
                        seg_pilar.append((x_min_s, y_min_s, x_max_s, y_max_s))
                        continue

                # Cubetas
                if nivel in (201, 227, 228, 237):
                    continue

                if abs(xa - xb) <= 5.0 and 8.0 <= abs(yb - ya) <= comp_max_face:
                    faces_v.append(((xa + xb) / 2.0, y_min_s, y_max_s))
                elif abs(ya - yb) <= 5.0 and 8.0 <= abs(xb - xa) <= comp_max_face:
                    faces_h.append(((ya + yb) / 2.0, x_min_s, x_max_s))

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    if not pts:
                        continue

                    # Polilinha fechada de pilar no Nível 227 ou vermelho
                    if eh_pilar and nivel not in (228, 237) and len(pts) >= 4:
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        lx = max(xs) - min(xs)
                        ly = max(ys) - min(ys)
                        if 8.0 <= lx <= 300.0 and 8.0 <= ly <= 300.0:
                            pilares_prontos.append((min(xs), min(ys), max(xs), max(ys)))

                    # Segmentos individuais
                    segs = []
                    for i in range(len(pts) - 1):
                        segs.append((pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]))
                    if len(pts) >= 3 and (abs(pts[0][0] - pts[-1][0]) > 0.1 or abs(pts[0][1] - pts[-1][1]) > 0.1):
                        segs.append((pts[-1][0], pts[-1][1], pts[0][0], pts[0][1]))

                    for xa, ya, xb, yb in segs:
                        x_min_s, x_max_s = min(xa, xb), max(xa, xb)
                        y_min_s, y_max_s = min(ya, yb), max(ya, yb)

                        if x_max_s < xmin_g or x_min_s > xmax_g or y_max_s < ymin_g or y_min_s > ymax_g:
                            continue

                        comp_seg = math.hypot(xb - xa, yb - ya)

                        if eh_pilar and nivel not in (228, 237):
                            if 8.0 <= comp_seg <= 300.0:
                                seg_pilar.append((x_min_s, y_min_s, x_max_s, y_max_s))
                                continue

                        if nivel in (201, 227, 228, 237):
                            continue

                        if abs(xa - xb) <= 5.0 and 8.0 <= abs(yb - ya) <= comp_max_face:
                            faces_v.append(((xa + xb) / 2.0, y_min_s, y_max_s))
                        elif abs(ya - yb) <= 5.0 and 8.0 <= abs(xb - xa) <= comp_max_face:
                            faces_h.append(((ya + yb) / 2.0, x_min_s, x_max_s))
                except Exception:
                    pass
    except Exception:
        pass

    return seg_pilar, pilares_prontos, faces_v, faces_h


def agrupar_pilares(seg_pilar, pilares_prontos=None, tol=6.0):
    """Une segmentos vermelhos conectados em retângulos (bounding boxes) de pilares."""
    caixas = []
    if pilares_prontos:
        for p in pilares_prontos:
            caixas.append(list(p))

    for s in seg_pilar:
        caixa = list(s)
        mudou = True
        while mudou:
            mudou = False
            for c in caixas[:]:
                if (caixa[0] - tol <= c[2] and c[0] - tol <= caixa[2] and
                        caixa[1] - tol <= c[3] and c[1] - tol <= caixa[3]):
                    caixa = [min(caixa[0], c[0]), min(caixa[1], c[1]),
                             max(caixa[2], c[2]), max(caixa[3], c[3])]
                    caixas.remove(c)
                    mudou = True
        caixas.append(caixa)

    pilares = []
    for c in caixas:
        lx, ly = c[2] - c[0], c[3] - c[1]
        if 8.0 <= lx <= 300.0 and 8.0 <= ly <= 300.0:
            pilares.append(tuple(c))
    return pilares


def limites_capitel(pilar, faces_v, faces_h):
    """
    A partir do pilar, procura a face de cubeta mais próxima em cada direção.
    A região livre entre elas é o capitel. Refina 2x usando a faixa já encontrada.
    """
    x_lo, y_lo, x_hi, y_hi = pilar
    alcance = 600.0
    xl, xr, yb, yt = x_lo, x_hi, y_lo, y_hi
    faixa_x = (x_lo - 20.0, x_hi + 20.0)
    faixa_y = (y_lo - 20.0, y_hi + 20.0)

    for _ in range(2):
        dir_ = [x for x, a, b in faces_v if x > x_hi + 1.0 and x - x_hi <= alcance and a < faixa_y[1] and b > faixa_y[0]]
        esq_ = [x for x, a, b in faces_v if x < x_lo - 1.0 and x_lo - x <= alcance and a < faixa_y[1] and b > faixa_y[0]]
        sup_ = [y for y, a, b in faces_h if y > y_hi + 1.0 and y - y_hi <= alcance and a < faixa_x[1] and b > faixa_x[0]]
        inf_ = [y for y, a, b in faces_h if y < y_lo - 1.0 and y_lo - y <= alcance and a < faixa_x[1] and b > faixa_x[0]]

        xr = min(dir_) if dir_ else x_hi
        xl = max(esq_) if esq_ else x_lo
        yt = min(sup_) if sup_ else y_hi
        yb = max(inf_) if inf_ else y_lo

        # Faixa interna (com folga) para a próxima iteração
        faixa_x = (xl + 5.0, xr - 5.0)
        faixa_y = (yb + 5.0, yt - 5.0)

    return xl, yb, xr, yt


def desenhar_ferro_capitel(dwg, capitel, dados, marca):
    """
    Coloca o ferro do capitel com a linha de distribuição conectada:
    - horizontal: ferro na direção X com dobras para cima, distribuição vertical atravessando o capitel.
    - vertical:   ferro na direção Y com dobras para a direita, distribuição horizontal atravessando o capitel.
    Quantidade = distância do capitel / espaçamento (+1 se marcado).
    """
    draw = dwg.draw
    bitola = float(dados.get("bitola", 10.0))
    espac = float(dados.get("espacamento", 15.0))
    comp_dobra = float(dados.get("dobra", COMP_DOBRA))
    mais_um = bool(dados.get("adicionar_mais_um", True))
    horizontal = (dados.get("direcao", "horizontal") == "horizontal")

    xl, yb, xr, yt = capitel
    larg, alt = xr - xl, yt - yb

    if horizontal:
        comp_reto = larg - 2.0 * COBRIMENTO
        dist_distr = alt
    else:
        comp_reto = alt - 2.0 * COBRIMENTO
        dist_distr = larg

    if comp_reto < 10.0 or dist_distr < 10.0:
        return 0, 0

    qtd = int(math.ceil(dist_distr / espac - 1e-6)) if espac > 0 else 1
    if mais_um:
        qtd += 1
    qtd = max(qtd, 1)

    comp_total = int(round(comp_reto + 2.0 * comp_dobra))

    # Posições de referência
    if horizontal:
        x_ferro = xl + COBRIMENTO
        # O ferro fica no terço superior do capitel (acima do pilar)
        y_ferro = yt - 0.20 * alt
        # A linha de distribuição vertical cruza o ferro e cobre todo o capitel
        x_distr = xl + 0.35 * larg
        p1 = (x_distr, yb)
        p2 = (x_distr, yt)
        angulo = 0.0
        ang_distr = 90.0
    else:
        x_ferro = xl + 0.20 * larg
        y_ferro = yb + COBRIMENTO
        y_distr = yb + 0.35 * alt
        p1 = (xl, y_distr)
        p2 = (xr, y_distr)
        angulo = 90.0
        ang_distr = 0.0

    try:
        draw.level = 220
        sr = TQSDwg.SmartRebar(dwg)
        sr.type = getattr(TQSDwg, "ICPFRT", 1)
        sr.diameter = bitola
        sr.mark = int(marca)
        sr.quantity = int(qtd)
        sr.spacing = float(espac)
        sr.ribbed = 0
        sr.showRibbed = 0
        sr.straightBarMainLength = float(comp_reto)
        sr.straightBarLeftLength = comp_dobra
        sr.straightBarRightLength = comp_dobra
        sr.straightBarTextPosition = 2
        sr.straightBarZone = getattr(TQSDwg, "ICPPOS", 0)
        sr.RebarDistrAdd(
            getattr(TQSDwg, "ICPESP", 2),
            ang_distr,
            p1[0], p1[1],
            p2[0], p2[1],
            (p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0,
            0, 0, 0, 0, 0,
            getattr(TQSDwg, "ICPCENTR_CENTRAD", 0),
            getattr(TQSDwg, "ICPQUEBR_SEMQUEBRA", 0),
            "", 0, 0, 1, 0, 0,
            float(espac), 1.0
        )
        try:
            sr.RebarDistrQuantity(0, 0, int(qtd))
        except Exception:
            pass
        sr.quantity = int(qtd)
        sr.spacing = float(espac)
        sr.RebarLine(x_ferro, y_ferro, angulo, 1.0, 1, 1, 1, 0, 220, -1, -1)
        return qtd, comp_total
    except Exception:
        pass

    # ---------------- Fallback gráfico fiel ao padrão TQS (Nível 220) ----------------
    draw.level = 220
    draw.style = 0
    txt = f"{qtd} P{marca} %% {bitola:g} C/{espac:g} C={comp_total}"
    larg_seta = 8.0

    if horizontal:
        xa, xb = x_ferro, x_ferro + comp_reto
        # Linha magenta do ferro (com dobras voltadas para cima)
        draw.color = 6
        draw.Line(xa, y_ferro, xb, y_ferro)
        draw.Line(xa, y_ferro, xa, y_ferro + comp_dobra)
        draw.Line(xb, y_ferro, xb, y_ferro + comp_dobra)

        # Linha verde de distribuição conectada
        draw.color = 3
        draw.Line(p1[0], p1[1], p2[0], p2[1])
        draw.Line(p1[0] - larg_seta, p1[1] + larg_seta, p1[0] + larg_seta, p1[1] - larg_seta)
        draw.Line(p1[0], p1[1], p1[0] - (larg_seta * 0.7), p1[1] + larg_seta)
        draw.Line(p1[0], p1[1], p1[0] + (larg_seta * 0.7), p1[1] + larg_seta)

        draw.Line(p2[0] - larg_seta, p2[1] + larg_seta, p2[0] + larg_seta, p2[1] - larg_seta)
        draw.Line(p2[0], p2[1], p2[0] - (larg_seta * 0.7), p2[1] - larg_seta)
        draw.Line(p2[0], p2[1], p2[0] + (larg_seta * 0.7), p2[1] - larg_seta)

        # Ponto verde na interseção da linha de distribuição com o ferro
        draw.Circle(x_distr, y_ferro, 2.0)

        # Textos em amarelo (Nível 220)
        draw.color = 2
        # Texto de chamada principal (acima do ferro)
        draw.Text(xa + 12.0, y_ferro + 4.0, 8.5, 0.0, txt)
        # Comprimento reto centralizado abaixo do ferro
        txt_comp_reto = f"{int(round(comp_reto))}"
        draw.Text((xa + xb) / 2.0 - 10.0, y_ferro - 12.0, 8.0, 0.0, txt_comp_reto)
        # Dobras nas laterais
        draw.Text(xa - 18.0, y_ferro + 2.0, 7.5, 0.0, f"{int(comp_dobra)}")
        draw.Text(xb + 5.0, y_ferro + 2.0, 7.5, 0.0, f"{int(comp_dobra)}")
    else:
        ya, yb2 = y_ferro, y_ferro + comp_reto
        # Linha magenta do ferro (com dobras voltadas para a direita)
        draw.color = 6
        draw.Line(x_ferro, ya, x_ferro, yb2)
        draw.Line(x_ferro, ya, x_ferro + comp_dobra, ya)
        draw.Line(x_ferro, yb2, x_ferro + comp_dobra, yb2)

        # Linha verde de distribuição conectada
        draw.color = 3
        draw.Line(p1[0], p1[1], p2[0], p2[1])
        draw.Line(p1[0] - larg_seta, p1[1] + larg_seta, p1[0] + larg_seta, p1[1] - larg_seta)
        draw.Line(p2[0] - larg_seta, p2[1] + larg_seta, p2[0] + larg_seta, p2[1] - larg_seta)

        # Ponto verde na interseção da linha de distribuição com o ferro
        draw.Circle(x_ferro, y_distr, 2.0)

        # Textos em amarelo
        draw.color = 2
        draw.Text(x_ferro - 12.0, ya + 12.0, 8.5, 90.0, txt)
        txt_comp_reto = f"{int(round(comp_reto))}"
        draw.Text(x_ferro + 8.0, (ya + yb2) / 2.0 - 10.0, 8.0, 90.0, txt_comp_reto)
        draw.Text(x_ferro + 2.0, ya - 14.0, 7.5, 0.0, f"{int(comp_dobra)}")
        draw.Text(x_ferro + 2.0, yb2 + 4.0, 7.5, 0.0, f"{int(comp_dobra)}")

    return qtd, comp_total


def meucmd(eag, tqsjan):
    """
    Entry point do plugin Capitel no TQS EAG.
    Permite arrastar uma janela (retângulo por 2 pontos) cobrindo a laje ou capitel
    para identificar os pilares e detalhar a armação automaticamente.
    """
    try:
        dados = pedir_dados_capitel()
        if dados is None:
            return

        dwg = tqsjan.dwg
        total_geral = 0
        janela_idx = 1
        marcas_globais = {}

        while True:
            prompt1 = f"Clique o 1º canto da janela sobre a laje/capitel [Botão Direito ou Esc para ENCERRAR]:"
            icod1, x1, y1 = eag.locate.GetPoint(tqsjan, prompt1)
            if icod1 != 1:
                break

            prompt2 = f"Clique o 2º canto oposto (arraste o retângulo sobre a laje):"
            icod2, x2, y2 = eag.locate.GetSecondPoint(
                tqsjan, x1, y1,
                TQSEag.EAG_RUBRETANG,
                TQSEag.EAG_RUBRET_NAOPREEN,
                prompt2
            )
            if icod2 != 1:
                continue

            xmin_sel = min(x1, x2)
            xmax_sel = max(x1, x2)
            ymin_sel = min(y1, y2)
            ymax_sel = max(y1, y2)

            if (xmax_sel - xmin_sel) < 15.0 or (ymax_sel - ymin_sel) < 15.0:
                continue

            janela = (xmin_sel, ymin_sel, xmax_sel, ymax_sel)

            seg_pilar, pilares_prontos, faces_v, faces_h = coletar_geometria(dwg, janela=janela)
            pilares = agrupar_pilares(seg_pilar, pilares_prontos=pilares_prontos)

            # Filtra pilares cujo centro está dentro da janela arrastada
            pilares_janela = [
                p for p in pilares
                if xmin_sel <= ((p[0] + p[2]) / 2.0) <= xmax_sel and
                   ymin_sel <= ((p[1] + p[3]) / 2.0) <= ymax_sel
            ]

            if not pilares_janela:
                continue

            capiteis = []
            for pil in pilares_janela:
                cap = limites_capitel(pil, faces_v, faces_h)
                # Ignora se não achou cubetas ao redor (capitel = próprio pilar)
                if (cap[2] - cap[0]) <= (pil[2] - pil[0]) + 5.0 and (cap[3] - cap[1]) <= (pil[3] - pil[1]) + 5.0:
                    continue
                if not any(abs(cap[0] - c[0]) < 3 and abs(cap[1] - c[1]) < 3 and
                           abs(cap[2] - c[2]) < 3 and abs(cap[3] - c[3]) < 3 for c in capiteis):
                    capiteis.append(cap)

            if not capiteis:
                continue

            total_janela = 0
            for cap in capiteis:
                larg, alt = cap[2] - cap[0], cap[3] - cap[1]
                chave = (int(round(larg)), int(round(alt)))
                if chave not in marcas_globais:
                    marcas_globais[chave] = len(marcas_globais) + 1
                qtd, _ = desenhar_ferro_capitel(dwg, cap, dados, marcas_globais[chave])
                if qtd:
                    total_janela += 1

            total_geral += total_janela
            tqsjan.Regen()
            janela_idx += 1

    except Exception:
        pass
    finally:
        try:
            tqsjan.Regen()
        except:
            pass
