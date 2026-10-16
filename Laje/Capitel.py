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
    - linhas de borda/viga/parede (Níveis 201, 227, 228 ou linhas longas de contorno)
    - vazios e furos (Nível 237 rosa e aberturas com 'X')
    Se 'janela' (xmin, ymin, xmax, ymax) for fornecida, filtra os elementos na região com margem.
    """
    seg_pilar = []
    pilares_prontos = []
    faces_v = []     # (x, y_lo, y_hi) - faces de cubetas
    faces_h = []     # (y, x_lo, x_hi) - faces de cubetas
    bordas_v = []    # (x, y_lo, y_hi, nivel) - vigas, bordas 201/228 e paredes 227
    bordas_h = []    # (y, x_lo, x_hi, nivel) - vigas, bordas 201/228 e paredes 227
    segs_237 = []    # (xmin, ymin, xmax, ymax) - furos rosa nível 237
    diag_pos = []    # diagonais com inclinação positiva para detectar 'X'
    diag_neg = []    # diagonais com inclinação negativa para detectar 'X'
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

    def _processar_seg(xa, ya, xb, yb, nivel, cor, eh_pilar):
        x_min_s, x_max_s = min(xa, xb), max(xa, xb)
        y_min_s, y_max_s = min(ya, yb), max(ya, yb)

        if x_max_s < xmin_g or x_min_s > xmax_g or y_max_s < ymin_g or y_min_s > ymax_g:
            return

        dx = abs(xb - xa)
        dy = abs(yb - ya)
        comp_seg = math.hypot(dx, dy)

        # 1. Nível 237 (borda rosa de furo/vazio)
        if nivel == 237:
            if comp_seg >= 5.0:
                segs_237.append((x_min_s, y_min_s, x_max_s, y_max_s))
            return

        # 2. Diagonais de vazios/shafts ('X')
        if dx >= 15.0 and dy >= 15.0:
            if (xb - xa) * (yb - ya) > 0:
                diag_pos.append((x_min_s, y_min_s, x_max_s, y_max_s))
            else:
                diag_neg.append((x_min_s, y_min_s, x_max_s, y_max_s))
            return

        # 3. Linhas de borda, vigas (201/228) e paredes/pilares (227)
        if nivel in (201, 227, 228) or eh_pilar:
            if dx <= 5.0 and dy >= 8.0:
                bordas_v.append(((xa + xb) / 2.0, y_min_s, y_max_s, nivel))
            elif dy <= 5.0 and dx >= 8.0:
                bordas_h.append(((ya + yb) / 2.0, x_min_s, x_max_s, nivel))

            if eh_pilar and nivel not in (228, 237) and 8.0 <= comp_seg <= 300.0:
                seg_pilar.append((x_min_s, y_min_s, x_max_s, y_max_s))
            return

        # 4. Cubetas e linhas longas de contorno (nível < 220)
        if dx <= 5.0 and dy >= 8.0:
            if dy <= comp_max_face:
                faces_v.append(((xa + xb) / 2.0, y_min_s, y_max_s))
            else:
                bordas_v.append(((xa + xb) / 2.0, y_min_s, y_max_s, nivel))
        elif dy <= 5.0 and dx >= 8.0:
            if dx <= comp_max_face:
                faces_h.append(((ya + yb) / 2.0, x_min_s, x_max_s))
            else:
                bordas_h.append(((ya + yb) / 2.0, x_min_s, x_max_s, nivel))

    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break
            nivel = getattr(dwg.iterator, "level", 0)
            cor = getattr(dwg.iterator, "color", -1)

            # Ignora armaduras desenhadas (nível >= 220), MAS mantém 227 (pilares), 228 (bordas) e 237 (furos)
            if nivel >= 220 and nivel not in (227, 228, 237):
                continue

            eh_pilar = (nivel == 227) or (cor == COR_PILAR and nivel not in (228, 237)) or (cor in (-1, 0, 1) and nivel == 201)

            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                _processar_seg(dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2, nivel, cor, eh_pilar)

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    if not pts:
                        continue

                    if nivel == 237 and len(pts) >= 2:
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        if max(xs) >= xmin_g and min(xs) <= xmax_g and max(ys) >= ymin_g and min(ys) <= ymax_g:
                            segs_237.append((min(xs), min(ys), max(xs), max(ys)))
                        continue

                    # Polilinha fechada de pilar no Nível 227 ou vermelho
                    if eh_pilar and nivel not in (228, 237) and len(pts) >= 4:
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        lx = max(xs) - min(xs)
                        ly = max(ys) - min(ys)
                        if 8.0 <= lx <= 300.0 and 8.0 <= ly <= 300.0:
                            pilares_prontos.append((min(xs), min(ys), max(xs), max(ys)))

                    for i in range(len(pts) - 1):
                        _processar_seg(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], nivel, cor, eh_pilar)
                    if len(pts) >= 3 and (abs(pts[0][0] - pts[-1][0]) > 0.1 or abs(pts[0][1] - pts[-1][1]) > 0.1):
                        _processar_seg(pts[-1][0], pts[-1][1], pts[0][0], pts[0][1], nivel, cor, eh_pilar)
                except Exception:
                    pass
    except Exception:
        pass

    vazios = _agrupar_vazios(segs_237, diag_pos, diag_neg)
    return seg_pilar, pilares_prontos, faces_v, faces_h, bordas_v, bordas_h, vazios


def _unir_caixas(lista_segs, tol=6.0):
    """Agrupa segmentos/caixas conectadas dentro da tolerância."""
    caixas = []
    for s in lista_segs:
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
    return [tuple(c) for c in caixas]


def _agrupar_vazios(segs_237, diag_pos, diag_neg):
    """
    Retorna lista de caixas (xmin, ymin, xmax, ymax, tipo) representando:
    - '237': Furos/obstáculos no Nível 237 (borda rosa)
    - 'X':   Vazios/shafts identificados pelo cruzamento de diagonais em 'X'
    """
    vazios = []
    for c in _unir_caixas(segs_237, tol=6.0):
        if (c[2] - c[0]) >= 10.0 and (c[3] - c[1]) >= 10.0:
            vazios.append((c[0], c[1], c[2], c[3], '237'))

    caixas_x = []
    for dp in diag_pos:
        for dn in diag_neg:
            ox = min(dp[2], dn[2]) - max(dp[0], dn[0])
            oy = min(dp[3], dn[3]) - max(dp[1], dn[1])
            if ox >= 10.0 and oy >= 10.0:
                caixas_x.append((min(dp[0], dn[0]), min(dp[1], dn[1]),
                                 max(dp[2], dn[2]), max(dp[3], dn[3])))

    for c in _unir_caixas(caixas_x, tol=10.0):
        # Evita duplicar se já estiver contido em um furo 237
        if any(v[0] - 8.0 <= c[0] and c[2] <= v[2] + 8.0 and
               v[1] - 8.0 <= c[1] and c[3] <= v[3] + 8.0 for v in vazios):
            continue
        vazios.append((c[0], c[1], c[2], c[3], 'X'))

    return vazios


def agrupar_pilares(seg_pilar, pilares_prontos=None, tol=6.0):
    """Une segmentos vermelhos conectados em retângulos (bounding boxes) de pilares."""
    base = list(pilares_prontos) if pilares_prontos else []
    caixas = _unir_caixas(base + list(seg_pilar), tol=tol)
    pilares = []
    for c in caixas:
        lx, ly = c[2] - c[0], c[3] - c[1]
        if 8.0 <= lx <= 300.0 and 8.0 <= ly <= 300.0:
            pilares.append(c)
    return pilares


def limites_capitel(pilar, faces_v, faces_h):
    """
    A partir do pilar, procura a face de cubeta mais próxima em cada direção.
    A região livre entre elas é o capitel. Refina 2x usando a faixa já encontrada.
    Retorna (xl, yb, xr, yt, eh_capitel_cubeta).
    """
    x_lo, y_lo, x_hi, y_hi = pilar
    alcance = 600.0
    xl, xr, yb, yt = x_lo, x_hi, y_lo, y_hi
    faixa_x = (x_lo - 20.0, x_hi + 20.0)
    faixa_y = (y_lo - 20.0, y_hi + 20.0)
    achou_x = False
    achou_y = False

    for _ in range(2):
        dir_ = [x for x, a, b in faces_v if x > x_hi + 1.0 and x - x_hi <= alcance and a < faixa_y[1] and b > faixa_y[0]]
        esq_ = [x for x, a, b in faces_v if x < x_lo - 1.0 and x_lo - x <= alcance and a < faixa_y[1] and b > faixa_y[0]]
        sup_ = [y for y, a, b in faces_h if y > y_hi + 1.0 and y - y_hi <= alcance and a < faixa_x[1] and b > faixa_x[0]]
        inf_ = [y for y, a, b in faces_h if y < y_lo - 1.0 and y_lo - y <= alcance and a < faixa_x[1] and b > faixa_x[0]]

        xr = min(dir_) if dir_ else x_hi
        xl = max(esq_) if esq_ else x_lo
        yt = min(sup_) if sup_ else y_hi
        yb = max(inf_) if inf_ else y_lo

        achou_x = bool(dir_ or esq_)
        achou_y = bool(sup_ or inf_)

        # Faixa interna (com folga) para a próxima iteração
        faixa_x = (xl + 5.0, xr - 5.0)
        faixa_y = (yb + 5.0, yt - 5.0)

    # Um capitel de laje nervurada tem cubetas limitando nas duas direções (X e Y)
    eh_capitel_cubeta = achou_x and achou_y
    return xl, yb, xr, yt, eh_capitel_cubeta


def _ponto_em_malha_cubetas(x, y, faces_v, faces_h):
    """Verifica se o ponto (x, y) está dentro de uma cubeta ou nervura entre cubetas."""
    tol_y = 35.0
    tol_x = 35.0
    fv_esq = any(x - 65.0 <= fx <= x + 2.0 and (ya - tol_y) <= y <= (yb + tol_y) for fx, ya, yb in faces_v)
    fv_dir = any(x - 2.0 <= fx <= x + 65.0 and (ya - tol_y) <= y <= (yb + tol_y) for fx, ya, yb in faces_v)
    fh_inf = any(y - 65.0 <= fy <= y + 2.0 and (xa - tol_x) <= x <= (xb + tol_x) for fy, xa, xb in faces_h)
    fh_sup = any(y - 2.0 <= fy <= y + 65.0 and (xa - tol_x) <= x <= (xb + tol_x) for fy, xa, xb in faces_h)
    return (fv_esq and fv_dir) and (fh_inf and fh_sup)


def _ajustar_ancoragem_viga(coord_interna, sentido, pos_transv, bordas_paralelas, faces_cubeta, vazios):
    """
    Se a borda encontrada na direção do ferro for a face interna de uma viga/parede dupla
    (outra linha paralela de borda entre 8cm e 30cm adiante, sem cubeta próxima),
    estende o limite até a face externa da viga (como no padrão TQS de maciços).
    sentido: -1 (esquerda/baixo) ou +1 (direita/cima).
    """
    candidatas = []
    for c_borda, t_lo, t_hi, _ in bordas_paralelas:
        if not (t_lo - 10.0 <= pos_transv <= t_hi + 10.0):
            continue
        dist = (c_borda - coord_interna) * sentido
        if 8.0 <= dist <= 30.0:
            c_min = min(coord_interna, c_borda)
            c_max = max(coord_interna, c_borda)
            # Não avança se for transição para região de cubetas (laje nervurada)
            tem_cubeta = any(c_min - 25.0 <= fc <= c_max + 25.0 and a - 15.0 <= pos_transv <= b + 15.0
                             for fc, a, b in faces_cubeta)
            if not tem_cubeta:
                candidatas.append(c_borda)

    if not candidatas:
        return coord_interna
    return max(candidatas) if sentido > 0 else min(candidatas)


def subdividir_regiao_em_faixas(regiao_base, direcao, faces_v, faces_h, bordas_v, bordas_h, vazios, ajustar_viga=False):
    """
    Subdivide uma região (capitel ou maciço) ao longo do eixo de distribuição:
    - Se a borda lateral tiver recorte/degrau ("meio torto"), separa em sequências distintas.
    - Se houver furo no Nível 237 ou vazio com 'X', recorta e cria sequências distintas.
    Retorna lista de tuplas (xl, yb, xr, yt).
    """
    xl_0, yb_0, xr_0, yt_0 = regiao_base
    horizontal = (direcao == "horizontal")
    passo = 2.0
    tol_agrup = 4.0

    # Eixo de distribuição = D (Y se horizontal, X se vertical)
    # Eixo da barra        = B (X se horizontal, Y se vertical)
    if horizontal:
        d_min, d_max = yb_0, yt_0
        b_min_base, b_max_base = xl_0, xr_0
        bordas_bar = bordas_v
        faces_bar = faces_v
    else:
        d_min, d_max = xl_0, xr_0
        b_min_base, b_max_base = yb_0, yt_0
        bordas_bar = bordas_h
        faces_bar = faces_h

    if (d_max - d_min) < 15.0 or (b_max_base - b_min_base) < 15.0:
        return []

    n_fatias = max(int(math.ceil((d_max - d_min) / passo)), 1)
    passo_real = (d_max - d_min) / float(n_fatias)
    fatias = []

    for i in range(n_fatias):
        d_ini = d_min + i * passo_real
        d_fim = d_ini + passo_real
        d_mid = 0.5 * (d_ini + d_fim)
        b_centro = 0.5 * (b_min_base + b_max_base)

        # 1. Determina os limites internos da barra nesta fatia d_mid
        b_esq_int = b_min_base
        b_dir_int = b_max_base

        if ajustar_viga:
            cands_esq = [
                c for c, a, b, _ in bordas_bar
                if a - 2.0 <= d_mid <= b + 2.0 and (b_min_base - 5.0) <= c <= (b_centro - 10.0)
            ]
            cands_dir = [
                c for c, a, b, _ in bordas_bar
                if a - 2.0 <= d_mid <= b + 2.0 and (b_centro + 10.0) <= c <= (b_max_base + 5.0)
            ]
            if cands_esq:
                b_esq_int = max(cands_esq)
            if cands_dir:
                b_dir_int = min(cands_dir)

        # 2. Subtrai vazios (Nível 237 e 'X') do intervalo interno antes de ancorar nas vigas
        # Cada item: (ia, ib, parou_vazio_esq, parou_vazio_dir)
        intervalos_brutos = [(b_esq_int, b_dir_int, False, False)]
        for vx1, vy1, vx2, vy2, _ in vazios:
            v_d_min, v_d_max = (vy1, vy2) if horizontal else (vx1, vx2)
            v_b_min, v_b_max = (vx1, vx2) if horizontal else (vy1, vy2)
            if v_d_min - 0.5 <= d_mid <= v_d_max + 0.5:
                novos = []
                for ia, ib, p_esq, p_dir in intervalos_brutos:
                    if v_b_max <= ia + 2.0 or v_b_min >= ib - 2.0:
                        novos.append((ia, ib, p_esq, p_dir))
                    else:
                        if v_b_min - ia >= 25.0:
                            novos.append((ia, v_b_min, p_esq, True))
                        if ib - v_b_max >= 25.0:
                            novos.append((v_b_max, ib, True, p_dir))
                intervalos_brutos = novos

        # 3. Aplica ajuste de ancoragem em viga apenas nas extremidades que não pararam em furo 237/'X'
        intervalos = []
        for ia, ib, p_esq, p_dir in intervalos_brutos:
            fa = ia if (not ajustar_viga or p_esq) else _ajustar_ancoragem_viga(ia, -1, d_mid, bordas_bar, faces_bar, vazios)
            fb = ib if (not ajustar_viga or p_dir) else _ajustar_ancoragem_viga(ib, +1, d_mid, bordas_bar, faces_bar, vazios)
            intervalos.append((fa, fb))

        fatias.append((d_ini, d_fim, intervalos))

    # Suaviza pequenas transições de pilar (<= 28cm) entre duas vigas desalinhadas
    if len(fatias) >= 3:
        max_pilar_fatias = int(round(28.0 / passo_real))
        i = 0
        while i < len(fatias):
            j = i
            while j < len(fatias) and fatias[j][2] == fatias[i][2]:
                j += 1
            comp_bloco = j - i
            if 0 < comp_bloco <= max_pilar_fatias:
                ant = fatias[i - 1][2] if i > 0 else None
                prox = fatias[j][2] if j < len(fatias) else None
                if ant and prox:
                    meio = i + comp_bloco // 2
                    for k in range(i, meio):
                        fatias[k] = (fatias[k][0], fatias[k][1], list(ant))
                    for k in range(meio, j):
                        fatias[k] = (fatias[k][0], fatias[k][1], list(prox))
                elif ant:
                    for k in range(i, j):
                        fatias[k] = (fatias[k][0], fatias[k][1], list(ant))
                elif prox:
                    for k in range(i, j):
                        fatias[k] = (fatias[k][0], fatias[k][1], list(prox))
            i = j

    # Agrupa fatias consecutivas com os mesmos limites (b_esq, b_dir) em faixas retangulares
    ativas = []
    finalizadas = []

    for d_ini, d_fim, intervalos in fatias:
        usados = set()
        novas_ativas = []
        for f in ativas:
            match_idx = None
            for idx, (ia, ib) in enumerate(intervalos):
                if idx not in usados and abs(ia - f['b_min']) <= tol_agrup and abs(ib - f['b_max']) <= tol_agrup:
                    match_idx = idx
                    break
            if match_idx is not None:
                usados.add(match_idx)
                f['d_max'] = d_fim
                f['amostras_a'].append(intervalos[match_idx][0])
                f['amostras_b'].append(intervalos[match_idx][1])
                novas_ativas.append(f)
            else:
                finalizadas.append(f)

        for idx, (ia, ib) in enumerate(intervalos):
            if idx not in usados:
                novas_ativas.append({
                    'b_min': ia,
                    'b_max': ib,
                    'd_min': d_ini,
                    'd_max': d_fim,
                    'amostras_a': [ia],
                    'amostras_b': [ib]
                })
        ativas = novas_ativas

    finalizadas.extend(ativas)

    resultado = []
    for f in finalizadas:
        b_lo = sum(f['amostras_a']) / len(f['amostras_a'])
        b_hi = sum(f['amostras_b']) / len(f['amostras_b'])
        d_lo = f['d_min']
        d_hi = f['d_max']
        if (b_hi - b_lo) >= 20.0 and (d_hi - d_lo) >= 18.0:
            if horizontal:
                resultado.append((b_lo, d_lo, b_hi, d_hi))
            else:
                resultado.append((d_lo, b_lo, d_hi, b_hi))

    return resultado


def detectar_macicos_na_janela(janela, direcao, faces_v, faces_h, bordas_v, bordas_h, vazios, capiteis_existentes):
    """
    Detecta regiões maciças dentro da janela selecionada que não são cobertas por cubetas
    nem por vazios ('X' / Nível 237), subdividindo em faixas quando houver degraus ou furos.
    """
    xmin_s, ymin_s, xmax_s, ymax_s = janela
    todas_v = [(x, a, b) for x, a, b, _ in bordas_v] + list(faces_v)
    todas_h = [(y, a, b) for y, a, b, _ in bordas_h] + list(faces_h)

    # Gera pontos de semente na janela (incluindo o centro)
    nx = max(min(int((xmax_s - xmin_s) / 50.0), 7), 1)
    ny = max(min(int((ymax_s - ymin_s) / 50.0), 7), 1)
    sementes = [((xmin_s + xmax_s) / 2.0, (ymin_s + ymax_s) / 2.0)]
    for ix in range(nx):
        for iy in range(ny):
            sx = xmin_s + (ix + 0.5) * (xmax_s - xmin_s) / float(nx)
            sy = ymin_s + (iy + 0.5) * (ymax_s - ymin_s) / float(ny)
            sementes.append((sx, sy))

    regioes_base = []
    faixas_finais = []

    for sx, sy in sementes:
        # Ignora se já caiu em capitel ou região maciça já processada
        if any(c[0] - 5.0 <= sx <= c[2] + 5.0 and c[1] - 5.0 <= sy <= c[3] + 5.0
               for c in capiteis_existentes + regioes_base + faixas_finais):
            continue

        # Ignora se estiver dentro de vazio ('X' ou 237) com margem de segurança
        if any(v[0] - 10.0 <= sx <= v[2] + 10.0 and v[1] - 10.0 <= sy <= v[3] + 10.0 for v in vazios):
            continue

        # Ignora se estiver na malha de cubetas
        if _ponto_em_malha_cubetas(sx, sy, faces_v, faces_h):
            continue

        # Procura os limites internos a partir da semente (sx, sy)
        esq_ = [x for x, a, b in todas_v if x < sx - 2.0 and sx - x <= 800.0 and a - 5.0 <= sy <= b + 5.0]
        dir_ = [x for x, a, b in todas_v if x > sx + 2.0 and x - sx <= 800.0 and a - 5.0 <= sy <= b + 5.0]
        inf_ = [y for y, a, b in todas_h if y < sy - 2.0 and sy - y <= 800.0 and a - 5.0 <= sx <= b + 5.0]
        sup_ = [y for y, a, b in todas_h if y > sy + 2.0 and y - sy <= 800.0 and a - 5.0 <= sx <= b + 5.0]

        if not (esq_ and dir_ and inf_ and sup_):
            continue

        xl_int = max(esq_)
        xr_int = min(dir_)
        yb_int = max(inf_)
        yt_int = min(sup_)

        # Ignora se a semente caiu dentro da espessura de uma viga dupla (<= 30cm)
        if (xr_int - xl_int) <= 32.0 or (yt_int - yb_int) <= 32.0:
            continue

        # Refina o alcance na direção de distribuição para cobrir todo o maciço (mesmo com degrau lateral)
        xm_int = 0.5 * (xl_int + xr_int)
        ym_int = 0.5 * (yb_int + yt_int)
        inf_ref = [y for y, a, b in todas_h if y < sy - 2.0 and sy - y <= 800.0 and a - 5.0 <= xm_int <= b + 5.0]
        sup_ref = [y for y, a, b in todas_h if y > sy + 2.0 and y - sy <= 800.0 and a - 5.0 <= xm_int <= b + 5.0]
        esq_ref = [x for x, a, b in todas_v if x < sx - 2.0 and sx - x <= 800.0 and a - 5.0 <= ym_int <= b + 5.0]
        dir_ref = [x for x, a, b in todas_v if x > sx + 2.0 and x - sx <= 800.0 and a - 5.0 <= ym_int <= b + 5.0]

        if inf_ref:
            yb_int = max(inf_ref)
        if sup_ref:
            yt_int = min(sup_ref)
        if esq_ref:
            xl_int = max(esq_ref)
        if dir_ref:
            xr_int = min(dir_ref)

        # Expande o envelope base (sem ancoragem de viga ainda) para cobrir degraus ao longo do maciço
        if direcao == "horizontal":
            esqs_faixa = [
                max([x for x, a, b in todas_v if x < xm_int - 10.0 and a - 2.0 <= y_t <= b + 2.0] or [xl_int])
                for y_t in (yb_int + 15.0, ym_int, yt_int - 15.0)
            ]
            dirs_faixa = [
                min([x for x, a, b in todas_v if x > xm_int + 10.0 and a - 2.0 <= y_t <= b + 2.0] or [xr_int])
                for y_t in (yb_int + 15.0, ym_int, yt_int - 15.0)
            ]
            reg_base = (min(esqs_faixa), yb_int, max(dirs_faixa), yt_int)
        else:
            infs_faixa = [
                max([y for y, a, b in todas_h if y < ym_int - 10.0 and a - 2.0 <= x_t <= b + 2.0] or [yb_int])
                for x_t in (xl_int + 15.0, xm_int, xr_int - 15.0)
            ]
            sups_faixa = [
                min([y for y, a, b in todas_h if y > ym_int + 10.0 and a - 2.0 <= x_t <= b + 2.0] or [yt_int])
                for x_t in (xl_int + 15.0, xm_int, xr_int - 15.0)
            ]
            reg_base = (xl_int, min(infs_faixa), xr_int, max(sups_faixa))

        regioes_base.append(reg_base)
        novas = subdividir_regiao_em_faixas(
            reg_base, direcao, faces_v, faces_h, bordas_v, bordas_h, vazios, ajustar_viga=True
        )
        for nf in novas:
            if not any(abs(nf[0] - c[0]) < 4.0 and abs(nf[1] - c[1]) < 4.0 and
                       abs(nf[2] - c[2]) < 4.0 and abs(nf[3] - c[3]) < 4.0
                       for c in capiteis_existentes + faixas_finais):
                faixas_finais.append(nf)

    return faixas_finais


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
        import ctypes
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

        # Define coordenadas dos textos de dobra no lado oposto ao texto principal para não sobrepor
        if horizontal:
            pos_dobras = [
                ("IPOFER_DEFTXTDES", x_ferro - 25.0, y_ferro - 15.0, 0.0),
                ("IPOFER_DEFTXTTHR", x_ferro + comp_reto * 0.5 - 15.0, y_ferro - 15.0, 0.0),
                ("IPOFER_DEFTXTDED", x_ferro + comp_reto + 5.0, y_ferro - 15.0, 0.0),
            ]
        else:
            pos_dobras = [
                ("IPOFER_DEFTXTDES", x_ferro + 15.0, y_ferro - 25.0, 90.0),
                ("IPOFER_DEFTXTTHR", x_ferro + 15.0, y_ferro + comp_reto * 0.5 - 15.0, 90.0),
                ("IPOFER_DEFTXTDED", x_ferro + 15.0, y_ferro + comp_reto + 5.0, 90.0),
            ]

        def _aplicar_pos_dobras():
            try:
                parfer = ctypes.c_void_p(sr.m_ferobjv)
                for fn_name, tx, ty, tang in pos_dobras:
                    fn = getattr(dwg.m_ipofer, fn_name, None)
                    if fn is not None:
                        cx = ctypes.c_double(tx)
                        cy = ctypes.c_double(ty)
                        ca = ctypes.c_double(tang)
                        fn(ctypes.byref(parfer), ctypes.byref(cx), ctypes.byref(cy), ctypes.byref(ca))
            except Exception:
                pass

        _aplicar_pos_dobras()
        sr.RebarLine(x_ferro, y_ferro, angulo, 1.0, 1, 1, 1, 0, 220, -1, -1)
        _aplicar_pos_dobras()
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
        # Dobras nas laterais (abaixo da linha do ferro para não sobrepor o texto principal)
        draw.Text(xa - 22.0, y_ferro - 12.0, 7.5, 0.0, f"{int(comp_dobra)}")
        draw.Text(xb + 5.0, y_ferro - 12.0, 7.5, 0.0, f"{int(comp_dobra)}")
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
        draw.Text(x_ferro + 12.0, (ya + yb2) / 2.0 - 10.0, 8.0, 90.0, txt_comp_reto)
        draw.Text(x_ferro + 12.0, ya - 22.0, 7.5, 90.0, f"{int(comp_dobra)}")
        draw.Text(x_ferro + 12.0, yb2 + 5.0, 7.5, 90.0, f"{int(comp_dobra)}")

    return qtd, comp_total


def meucmd(eag, tqsjan):
    """
    Entry point do plugin Capitel no TQS EAG.
    Permite arrastar uma janela (retângulo por 2 pontos) cobrindo a laje, capitel ou maciço
    para identificar as regiões e detalhar a armação automaticamente.
    """
    try:
        dados = pedir_dados_capitel()
        if dados is None:
            return

        dwg = tqsjan.dwg
        direcao = dados.get("direcao", "horizontal")
        total_geral = 0
        janela_idx = 1
        marcas_globais = {}

        while True:
            prompt1 = f"Clique o 1º canto da janela sobre a laje/capitel/maciço [Botão Direito ou Esc para ENCERRAR]:"
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

            seg_pilar, pilares_prontos, faces_v, faces_h, bordas_v, bordas_h, vazios = coletar_geometria(dwg, janela=janela)
            pilares = agrupar_pilares(seg_pilar, pilares_prontos=pilares_prontos)

            # 1. Identifica capitéis de pilares cercados por cubetas na janela
            pilares_janela = [
                p for p in pilares
                if xmin_sel <= ((p[0] + p[2]) / 2.0) <= xmax_sel and
                   ymin_sel <= ((p[1] + p[3]) / 2.0) <= ymax_sel
            ]

            capiteis_base = []
            faixas_para_armar = []

            for pil in pilares_janela:
                xl, yb, xr, yt, eh_cap_cubeta = limites_capitel(pil, faces_v, faces_h)
                if not eh_cap_cubeta:
                    continue
                if (xr - xl) <= (pil[2] - pil[0]) + 5.0 and (yt - yb) <= (pil[3] - pil[1]) + 5.0:
                    continue
                cap = (xl, yb, xr, yt)
                if not any(abs(cap[0] - c[0]) < 3 and abs(cap[1] - c[1]) < 3 and
                           abs(cap[2] - c[2]) < 3 and abs(cap[3] - c[3]) < 3 for c in capiteis_base):
                    capiteis_base.append(cap)
                    sub_faixas = subdividir_regiao_em_faixas(
                        cap, direcao, faces_v, faces_h, bordas_v, bordas_h, vazios, ajustar_viga=False
                    )
                    for sf in (sub_faixas or [cap]):
                        faixas_para_armar.append(sf)

            # 2. Identifica regiões maciças (com degraus/recortes ou furos Nível 237 / 'X')
            faixas_macicos = detectar_macicos_na_janela(
                janela, direcao, faces_v, faces_h, bordas_v, bordas_h, vazios, capiteis_base
            )
            faixas_para_armar.extend(faixas_macicos)

            if not faixas_para_armar:
                continue

            total_janela = 0
            for cap in faixas_para_armar:
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
