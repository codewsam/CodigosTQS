# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - TRANSPORTE FIDEDIGNO: PILAR, QUADRADO DA ÁREA E FERRO DE DENTRO (TQS EAG)
================================================================================
Autor: Ediglânthio Samuel Araújo Brandão
1. Abrir janela (tela) sobre o pilar na planta da laje.
2. A área do quadrado aberto se torna a área do quadrado em volta (perímetro com HD=26).
3. Capta toda a geometria do pilar e o ferro de dentro de forma 100% fidedigna.
4. Tela HTA mostra qual pilar e área foram selecionados.
5. Cola no ponto clicado o conjunto completo idêntico:
   - O quadrado da área em volta com HD=26;
   - O pilar em sua posição exata;
   - O ferro de dentro;
   - O título PUNÇÃO - ...
================================================================================
"""
import os
import re
import json
import math
import subprocess
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag


ARQUIVO_PILAR_COPIADO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ultimo_pilar_copiado.json")


def salvar_geometria_em_memoria(dados):
    """Salva os elementos capturados em JSON para transporte entre arquivos DWG."""
    try:
        with open(ARQUIVO_PILAR_COPIADO, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def carregar_geometria_em_memoria():
    """Carrega a geometria capturada da memória."""
    if os.path.exists(ARQUIVO_PILAR_COPIADO):
        try:
            with open(ARQUIVO_PILAR_COPIADO, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if dados and dados.get("total_elementos", 0) > 0:
                    return dados
        except Exception:
            return None
    return None


# ==============================================================================
# ALGORITMO DE CLIPPING DE LINHAS PARA A JANELA (COHEN-SUTHERLAND)
# ==============================================================================

def clip_linha_na_janela(x1, y1, x2, y2, xmin, xmax, ymin, ymax):
    """
    Recorta linhas longas que cruzam a janela para que o ferro de dentro
    fique exatamente contido nos limites do quadrado aberto.
    """
    INSIDE = 0
    LEFT = 1
    RIGHT = 2
    BOTTOM = 4
    TOP = 8

    def _code(x, y):
        c = INSIDE
        if x < xmin:
            c |= LEFT
        elif x > xmax:
            c |= RIGHT
        if y < ymin:
            c |= BOTTOM
        elif y > ymax:
            c |= TOP
        return c

    c1 = _code(x1, y1)
    c2 = _code(x2, y2)
    aceita = False

    while True:
        if c1 == 0 and c2 == 0:
            aceita = True
            break
        elif (c1 & c2) != 0:
            break
        else:
            c_fora = c1 if c1 != 0 else c2
            x = 0.0
            y = 0.0
            dx = x2 - x1
            dy = y2 - y1

            if c_fora & TOP:
                x = x1 + dx * (ymax - y1) / dy if dy != 0 else x1
                y = ymax
            elif c_fora & BOTTOM:
                x = x1 + dx * (ymin - y1) / dy if dy != 0 else x1
                y = ymin
            elif c_fora & RIGHT:
                y = y1 + dy * (xmax - x1) / dx if dx != 0 else y1
                x = xmax
            elif c_fora & LEFT:
                y = y1 + dy * (xmin - x1) / dx if dx != 0 else y1
                x = xmin

            if c_fora == c1:
                x1, y1 = x, y
                c1 = _code(x1, y1)
            else:
                x2, y2 = x, y
                c2 = _code(x2, y2)

    if aceita:
        return x1, y1, x2, y2
    return None


def eh_linha_de_borda(x1, y1, x2, y2, xmin, xmax, ymin, ymax, tol=1.5):
    """
    Retorna True se a linha coincide com qualquer uma das 4 bordas da janela de corte.
    Isso elimina artefatos de corte de cubetas externas que encostam no perímetro.
    """
    na_esq = abs(x1 - xmin) < tol and abs(x2 - xmin) < tol
    na_dir = abs(x1 - xmax) < tol and abs(x2 - xmax) < tol
    no_inf = abs(y1 - ymin) < tol and abs(y2 - ymin) < tol
    no_sup = abs(y1 - ymax) < tol and abs(y2 - ymax) < tol
    return na_esq or na_dir or no_inf or no_sup


# ==============================================================================
# CAPTURA DA JANELA (O TAMANHO DA JANELA DEFINE A ÁREA DO QUADRADO EM VOLTA)
# ==============================================================================

def capturar_janela_com_area(eag, tqsjan):
    """
    O usuário abre uma janela na tela sobre o pilar.
    - O retângulo da janela define exatamente a área do quadrado em volta.
    - Captura o pilar e o ferro de dentro contidos nela.
    """
    dwg = tqsjan.dwg

    prompt1 = "Abra a janela da area do pilar (Clique no 1º canto) [Esc para cancelar]:"
    icod1, x1, y1 = eag.locate.GetPoint(tqsjan, prompt1)
    if icod1 != 1:
        return None

    prompt2 = "Abra o retangulo ate o tamanho desejado da area e clique no 2º canto:"
    icod2, x2, y2 = eag.locate.GetSecondPoint(
        tqsjan, x1, y1,
        TQSEag.EAG_RUBLINEAR,
        TQSEag.EAG_RUBRET_NAOPREEN,
        prompt2
    )
    if icod2 != 1:
        return None

    xmin_j = min(x1, x2)
    xmax_j = max(x1, x2)
    ymin_j = min(y1, y2)
    ymax_j = max(y1, y2)

    # Centro de referência e dimensões exatas da janela aberta
    xc = (xmin_j + xmax_j) / 2.0
    yc = (ymin_j + ymax_j) / 2.0
    larg_area = round(xmax_j - xmin_j, 1)
    alt_area = round(ymax_j - ymin_j, 1)

    linhas = []
    polilinhas = []
    textos = []
    arcos = []
    circulos = []

    # Constantes reais do TQSDwg
    TIPO_LINE = getattr(TQSDwg, "DWGTYPE_LINE", 1)
    TIPO_TEXT = getattr(TQSDwg, "DWGTYPE_TEXT", 2)
    TIPO_POLYLINE = getattr(TQSDwg, "DWGTYPE_POLYLINE", 3)
    TIPO_CIRCLE = getattr(TQSDwg, "DWGTYPE_CIRCLE", 6)
    TIPO_ARC = getattr(TQSDwg, "DWGTYPE_ARC", 7)
    TIPO_CURVE = getattr(TQSDwg, "DWGTYPE_CURVE", 8)

    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break

            nivel = getattr(dwg.iterator, "level", 0)
            cor = getattr(dwg.iterator, "color", -1)
            estilo = getattr(dwg.iterator, "style", -1)

            # Ignora linhas de cubetas (nível 208) da laje nervurada
            if nivel == 208:
                continue

            # 1. LINHAS (pilar e ferro de dentro)
            if itipo == TIPO_LINE:
                try:
                    lx1 = float(dwg.iterator.x1)
                    ly1 = float(dwg.iterator.y1)
                    lx2 = float(dwg.iterator.x2)
                    ly2 = float(dwg.iterator.y2)

                    # Recorta exatamente nos limites da janela aberta
                    clipped = clip_linha_na_janela(lx1, ly1, lx2, ly2, xmin_j, xmax_j, ymin_j, ymax_j)
                    if clipped:
                        cx1, cy1, cx2, cy2 = clipped
                        if eh_linha_de_borda(cx1, cy1, cx2, cy2, xmin_j, xmax_j, ymin_j, ymax_j):
                            continue
                        if math.hypot(cx2 - cx1, cy2 - cy1) > 0.3:
                            linhas.append({
                                "dx1": cx1 - xc, "dy1": cy1 - yc,
                                "dx2": cx2 - xc, "dy2": cy2 - yc,
                                "nivel": nivel, "cor": cor, "estilo": estilo
                            })
                except Exception:
                    pass

            # 2. POLILINHAS E CURVAS (contorno do pilar e polilinhas da forma)
            elif itipo in (TIPO_POLYLINE, TIPO_CURVE):
                try:
                    npts = getattr(dwg.iterator, "xySize", 0)
                    if npts >= 2:
                        pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                        for i in range(len(pts) - 1):
                            p1, p2 = pts[i], pts[i + 1]
                            clipped = clip_linha_na_janela(p1[0], p1[1], p2[0], p2[1], xmin_j, xmax_j, ymin_j, ymax_j)
                            if clipped:
                                cx1, cy1, cx2, cy2 = clipped
                                if eh_linha_de_borda(cx1, cy1, cx2, cy2, xmin_j, xmax_j, ymin_j, ymax_j):
                                    continue
                                if math.hypot(cx2 - cx1, cy2 - cy1) > 0.3:
                                    linhas.append({
                                        "dx1": cx1 - xc, "dy1": cy1 - yc,
                                        "dx2": cx2 - xc, "dy2": cy2 - yc,
                                        "nivel": nivel, "cor": cor, "estilo": estilo
                                    })
                except Exception:
                    pass

            # 3. TEXTOS (P10, 30/180, etc.)
            elif itipo == TIPO_TEXT:
                try:
                    tx = float(dwg.iterator.x1)
                    ty = float(dwg.iterator.y1)
                    if xmin_j <= tx <= xmax_j and ymin_j <= ty <= ymax_j:
                        txt = str(getattr(dwg.iterator, "text", "")).strip()
                        h_t = float(getattr(dwg.iterator, "textHeight", 8.0))
                        ang_t = float(getattr(dwg.iterator, "textAngle", 0.0))
                        textos.append({
                            "dx": tx - xc, "dy": ty - yc,
                            "h": h_t, "ang": ang_t,
                            "txt": txt, "nivel": nivel, "cor": cor
                        })
                except Exception:
                    pass

            # 4. ARCOS
            elif itipo == TIPO_ARC:
                try:
                    axc = float(dwg.iterator.xc)
                    ayc = float(dwg.iterator.yc)
                    raio = float(dwg.iterator.radius)
                    if xmin_j <= axc <= xmax_j and ymin_j <= ayc <= ymax_j:
                        arcos.append({
                            "dxc": axc - xc, "dyc": ayc - yc,
                            "raio": raio,
                            "aini": float(dwg.iterator.startAngle), "afim": float(dwg.iterator.endAngle),
                            "nivel": nivel, "cor": cor, "estilo": estilo
                        })
                except Exception:
                    pass

            # 5. CÍRCULOS
            elif itipo == TIPO_CIRCLE:
                try:
                    cxc = float(dwg.iterator.xc)
                    cyc = float(dwg.iterator.yc)
                    raio = float(dwg.iterator.radius)
                    if xmin_j <= cxc <= xmax_j and ymin_j <= cyc <= ymax_j:
                        circulos.append({
                            "dxc": cxc - xc, "dyc": cyc - yc,
                            "raio": raio,
                            "nivel": nivel, "cor": cor, "estilo": estilo
                        })
                except Exception:
                    pass

    except Exception:
        pass

    # Nome do pilar identificado a partir dos textos internos
    nome_pilar = "P10 - P13"
    padrao_pilar = re.compile(r"^P\s*[-.]?\s*(\d+)", re.IGNORECASE)
    melhor_dist = 1e9

    for t in textos:
        d = math.hypot(t["dx"], t["dy"])
        txt = t["txt"]
        if padrao_pilar.search(txt) and d < melhor_dist:
            melhor_dist = d
            nome_pilar = txt

    total = len(linhas) + len(textos) + len(arcos) + len(circulos)

    return {
        "nome": nome_pilar,
        "larg_area": larg_area,
        "alt_area": alt_area,
        "hd": 26.0,
        "total_elementos": total,
        "num_linhas": len(linhas),
        "num_textos": len(textos),
        "linhas": linhas,
        "textos": textos,
        "arcos": arcos,
        "circulos": circulos
    }


# ==============================================================================
# GEOMETRIA DO PILAR IDENTIFICADO
# ==============================================================================

def obter_geometria_pilar(pilar):
    """
    Obtém as dimensões e bounding box do pilar a partir dos elementos capturados.
    Retorna (c_xmin, c_xmax, c_ymin, c_ymax, col_dx, col_dy, orientacao)
    onde orientacao é 'H' (horizontal) ou 'V' (vertical).
    """
    linhas_pilar = [l for l in pilar.get("linhas", []) if l.get("nivel") in (227, 226, 228, 220)]
    if not linhas_pilar:
        linhas_pilar = pilar.get("linhas", [])

    if linhas_pilar:
        xs = [l["dx1"] for l in linhas_pilar] + [l["dx2"] for l in linhas_pilar]
        ys = [l["dy1"] for l in linhas_pilar] + [l["dy2"] for l in linhas_pilar]
        c_xmin, c_xmax = min(xs), max(xs)
        c_ymin, c_ymax = min(ys), max(ys)
    else:
        c_xmin, c_xmax = -15.0, 15.0
        c_ymin, c_ymax = -90.0, 90.0

    col_dx = round(c_xmax - c_xmin, 1)
    col_dy = round(c_ymax - c_ymin, 1)
    orientacao = 'H' if col_dx >= col_dy else 'V'
    return c_xmin, c_xmax, c_ymin, c_ymax, col_dx, col_dy, orientacao


# ==============================================================================
# JANELA HTA DE CONFIRMAÇÃO E CONFIGURAÇÃO DA ARMADURA DE PUNÇÃO
# ==============================================================================

def mostrar_tela_confirmacao(pilar):
    """
    Abre a tela HTA para o usuário visualizar o pilar, área e configurar a armadura de punção:
    - Diagrama interativo com as cotas x, y, y', x' preenchidas diretamente nos espaços quadrados da imagem!
    - Quantidade de ferros na face maior e face menor
    - Opção de ferros inclinados na diagonal (4 quinas)
    - Pinos / conectores por ferro e espaçamento
    - Opção de desenhar cotas verdes
    """
    caminho_script = os.path.dirname(os.path.abspath(__file__))
    hta_path = os.path.join(caminho_script, "dialogo_puncao.hta")
    json_path = os.path.join(caminho_script, "dados_puncao_temp.json")

    if os.path.exists(json_path):
        try:
            os.remove(json_path)
        except Exception:
            pass

    json_js = json_path.replace('\\', '\\\\')

    nome_p = pilar.get("nome", "P10 - P13") if pilar else "P10 - P13"
    larg_area = pilar.get("larg_area", 180.0) if pilar else 180.0
    alt_area = pilar.get("alt_area", 140.0) if pilar else 140.0
    hd_p = pilar.get("hd", 26.0) if pilar else 26.0

    c_xmin, c_xmax, c_ymin, c_ymax, col_dx, col_dy, orientacao = obter_geometria_pilar(pilar)
    comp_maior = col_dx if orientacao == 'H' else col_dy
    comp_menor = col_dy if orientacao == 'H' else col_dx

    # Sugestão inicial de colunas e linhas (Face Maior) e estribos (Face Menor)
    cota_x_ini = 6.75
    cota_y_ini = 10.0
    cota_y_linha_ini = 7.55
    cota_x_linha_ini = 10.0
    cota_inclinado_ini = 10.0

    larg_estribo_ini = 15.0
    alt_estribo_ini = round(max(10.0, float(hd_p) - 5.0), 1)
    bitola_estribo_ini = 8.0
    pos_estribo_ini = "1"

    vao_util_maior = max(larg_estribo_ini, comp_maior - 2.0 * cota_x_ini)
    num_colunas_sug = max(2, int(vao_util_maior // (larg_estribo_ini + 12.0)))
    if num_colunas_sug * larg_estribo_ini > vao_util_maior and num_colunas_sug > 2:
        num_colunas_sug = max(2, int(vao_util_maior // larg_estribo_ini))
    num_linhas_sug = 4
    espaco_linhas_ini = 13.0

    num_menor_sug = 3
    espaco_menor_sug = 13.0
    num_pinos_ini = num_linhas_sug

    espaco_colunas_sug = round((comp_maior - 2.0 * cota_x_ini - num_colunas_sug * larg_estribo_ini) / (num_colunas_sug - 1), 2) if num_colunas_sug > 1 else 0.0

    total_estribos_ini = (2 * num_colunas_sug * num_linhas_sug) + (2 * num_menor_sug) + (4 * num_linhas_sug)
    comp_ini = int(round(2.0 * (larg_estribo_ini + alt_estribo_ini) + 15.0))

    hta_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta http-equiv="x-ua-compatible" content="ie=edge" />
    <title>Configuração da Armadura de Punção - G3 Plugins</title>
    <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="PuncaoConfig" BORDER="dialog" INNERBORDER="no" SCROLL="no" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #eef2f5;
            margin: 0;
            padding: 0;
            font-size: 12px;
            color: #212529;
            user-select: none;
        }}
        .topbar {{
            background: linear-gradient(135deg, #004d40 0%, #00796b 100%);
            color: #ffffff;
            padding: 10px 18px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.25);
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .topbar .icon {{
            width: 34px;
            height: 34px;
            background: rgba(255,255,255,0.18);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 17px;
            font-weight: bold;
        }}
        .topbar h1 {{
            font-size: 15px;
            margin: 0;
            font-weight: 700;
            letter-spacing: 0.3px;
        }}
        .topbar p {{
            margin: 2px 0 0 0;
            font-size: 11px;
            color: #b2dfdb;
        }}
        .main-wrapper {{
            display: flex;
            gap: 14px;
            padding: 12px 18px 4px 18px;
        }}
        .col-left {{
            flex: 1.25;
            min-width: 530px;
        }}
        .col-right {{
            flex: 0.95;
            min-width: 370px;
            display: flex;
            flex-direction: column;
            gap: 9px;
        }}
        .card {{
            background: #ffffff;
            border: 1px solid #b0bec5;
            border-radius: 8px;
            padding: 11px 14px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.06);
        }}
        .card h3 {{
            font-size: 11.5px;
            margin: 0 0 8px 0;
            color: #004d40;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 2px solid #e0f2f1;
            padding-bottom: 4px;
            font-weight: 700;
        }}
        .diag-container {{
            position: relative;
            width: 100%;
            margin: 0 auto;
            border-radius: 6px;
            overflow: hidden;
            box-shadow: 0 2px 6px rgba(0,0,0,0.12);
            background: #ffffff;
            border: 1px solid #cfd8dc;
        }}
        .diag-img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .cota-box {{
            position: absolute;
            background: #ffffff;
            border: 2px solid #d32f2f;
            border-radius: 4px;
            font-size: 15px;
            font-weight: bold;
            color: #b71c1c;
            text-align: center;
            box-shadow: 0 2px 5px rgba(0,0,0,0.25);
            outline: none;
            box-sizing: border-box;
            font-family: 'Segoe UI', Tahoma, sans-serif;
        }}
        .cota-box:focus {{
            border-color: #00796b;
            background: #e0f2f1;
            color: #004d40;
            box-shadow: 0 0 8px rgba(0, 121, 107, 0.6);
        }}
        .box-x {{
            left: 25.35%; top: 12.5%; width: 14.76%; height: 7.81%;
        }}
        .box-y {{
            left: 75.95%; top: 35.15%; width: 14.76%; height: 7.81%;
        }}
        .box-y-linha {{
            left: 5.12%; top: 30.47%; width: 14.76%; height: 7.81%;
        }}
        .box-x-linha {{
            left: 5.12%; top: 79.69%; width: 14.64%; height: 7.81%;
        }}
        .diag-legenda {{
            display: flex;
            justify-content: space-between;
            margin-top: 8px;
            background: #e8f5e9;
            border: 1px solid #c8e6c9;
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 11px;
        }}
        .leg-item {{
            display: flex;
            align-items: center;
            gap: 4px;
            color: #2e7d32;
            font-weight: 600;
        }}
        .badge-red {{
            background: #d32f2f;
            color: #ffffff;
            padding: 1px 6px;
            border-radius: 3px;
            font-weight: bold;
            font-size: 10.5px;
        }}
        .campo {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }}
        .campo label {{
            font-weight: 600;
            color: #37474f;
            font-size: 11.5px;
        }}
        .campo input[type="text"], .campo input[type="number"], .campo select {{
            width: 85px;
            padding: 4px 6px;
            border: 1px solid #80cbc4;
            border-radius: 4px;
            font-size: 12px;
            text-align: right;
            color: #004d40;
            font-weight: 700;
            background: #ffffff;
        }}
        .campo select {{
            text-align: left;
            cursor: pointer;
        }}
        .campo-check {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 6px 0;
            padding: 6px 8px;
            background: #f1f8e9;
            border: 1px solid #dcedc8;
            border-radius: 5px;
        }}
        .campo-check input[type="checkbox"] {{
            width: 16px;
            height: 16px;
            cursor: pointer;
            accent-color: #00796b;
        }}
        .campo-check label {{
            font-size: 11.5px;
            color: #33691e;
            font-weight: 600;
            cursor: pointer;
        }}
        .item-info {{
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            border-bottom: 1px dashed #e0f2f1;
            font-size: 11.5px;
        }}
        .item-info:last-child {{
            border-bottom: none;
        }}
        .item-info .rotulo {{
            color: #546e7a;
            font-weight: 500;
        }}
        .item-info .valor {{
            color: #004d40;
            font-weight: 700;
        }}
        .btns {{
            display: flex;
            justify-content: flex-end;
            gap: 12px;
            padding: 10px 18px 14px 18px;
            background: #eef2f5;
            border-top: 1px solid #cfd8dc;
        }}
        button {{
            padding: 8px 18px;
            cursor: pointer;
            border: 1px solid #b2dfdb;
            border-radius: 6px;
            background: #ffffff;
            font-size: 12.5px;
            font-weight: 700;
            color: #004d40;
        }}
        button:hover {{ background: #e0f2f1; }}
        .btn-principal {{
            background: linear-gradient(135deg, #00796b 0%, #004d40 100%);
            color: #ffffff;
            border: none;
            box-shadow: 0 2px 5px rgba(0,77,64,0.35);
        }}
        .btn-principal:hover {{
            background: linear-gradient(135deg, #00695c 0%, #00332c 100%);
        }}
    </style>
    <script language="javascript">
        window.onload = function() {{
            window.resizeTo(1040, 800);
            window.moveTo((screen.width - 1040) / 2, (screen.height - 780) / 2);
            calcContagemEstribos();
        }};

        function calcEspacoMaior() {{
            calcContagemEstribos();
        }}

        function calcEspacoMenor() {{
            calcContagemEstribos();
        }}

        function toggleInclinado() {{
            var chk = document.getElementById("tem_inclinado").checked;
            var box = document.getElementById("wrap_cota_inclinado");
            if (box) {{
                box.style.display = chk ? "flex" : "none";
            }}
            calcContagemEstribos();
        }}

        function atualizarHdEstribo() {{
            var hdVal = parseFloat(document.getElementById("hd").value.replace(',', '.')) || 26.0;
            var altSug = Math.max(10.0, hdVal - 5.0);
            var elAltMaior = document.getElementById("alt_estribo_maior");
            var elAltMenor = document.getElementById("alt_estribo_menor");
            if (elAltMaior) elAltMaior.value = altSug.toFixed(1);
            if (elAltMenor) elAltMenor.value = altSug.toFixed(1);
            calcContagemEstribos();
        }}

        function calcContagemEstribos() {{
            var nCol = parseInt(document.getElementById("num_colunas").value) || 0;
            var nLin = parseInt(document.getElementById("num_linhas").value) || 0;
            var nMenor = parseInt(document.getElementById("num_menor").value) || 0;
            var temInc = document.getElementById("tem_inclinado").checked;
            var largStMaior = parseFloat(document.getElementById("larg_estribo_maior").value.replace(',', '.')) || 15.0;
            var altStMaior = parseFloat(document.getElementById("alt_estribo_maior").value.replace(',', '.')) || 21.0;
            var largStMenor = parseFloat(document.getElementById("larg_estribo_menor").value.replace(',', '.')) || 15.0;
            var altStMenor = parseFloat(document.getElementById("alt_estribo_menor").value.replace(',', '.')) || 21.0;
            var bitolaVal = document.getElementById("bitola_estribo").value || "8.0";
            var posSt = (document.getElementById("pos_estribo").value || "1").trim().toUpperCase();
            var posNum = parseInt(posSt.replace(/\\D/g, '')) || 1;

            var multMaior = 2 * nCol;
            var compMenor = Math.round(2.0 * (largStMenor + altStMenor) + 15.0);
            var compMaior = Math.round(2.0 * (largStMaior + altStMaior) + 15.0);
            var elCotaInc = document.getElementById("cota_inclinado");
            var cotaInc = elCotaInc ? (parseFloat(elCotaInc.value.replace(',', '.')) || 10.0) : 10.0;
            var elEspLin = document.getElementById("espaco_linhas");
            var espLin = elEspLin ? (parseFloat(elEspLin.value.replace(',', '.')) || 13.0) : 13.0;
            var compCob = Math.round(2.0 * cotaInc + nLin * altStMaior + Math.max(0, nLin - 1) * espLin);

            var bNum = parseFloat(bitolaVal);
            var bitolaTxt = (bNum % 1 === 0) ? bNum.toFixed(0) : bNum.toString();

            var elResumo = document.getElementById("txt_resumo_preview");
            if (elResumo) {{
                var html = "<div style='font-size:11px; color:#004d40; line-height:1.5;'>";
                html += "<div><b>Face Menor:</b> 2x" + nMenor + " N" + posNum + " \u00f8 " + bitolaTxt + " (" + largStMenor + "x" + altStMenor + " cm)</div>";
                html += "<div><b>Face Maior:</b> " + multMaior + "x" + nLin + " N" + (posNum + 1) + " \u00f8 " + bitolaTxt + " (" + largStMaior + "x" + altStMaior + " cm)</div>";
                html += "</div>";
                elResumo.innerHTML = html;
            }}
        }}

        function responder(acao) {{
            var L = {comp_maior};
            var nCol = parseInt(document.getElementById("num_colunas").value) || {num_colunas_sug};
            var nLin = parseInt(document.getElementById("num_linhas").value) || {num_linhas_sug};
            var cx = parseFloat(document.getElementById("cota_x").value.replace(',', '.')) || {cota_x_ini};
            var largStMaior = parseFloat(document.getElementById("larg_estribo_maior").value.replace(',', '.')) || 15.0;
            var altStMaior = parseFloat(document.getElementById("alt_estribo_maior").value.replace(',', '.')) || 21.0;
            var largStMenor = parseFloat(document.getElementById("larg_estribo_menor").value.replace(',', '.')) || 15.0;
            var altStMenor = parseFloat(document.getElementById("alt_estribo_menor").value.replace(',', '.')) || 21.0;
            var espLin = parseFloat(document.getElementById("espaco_linhas").value.replace(',', '.')) || {espaco_linhas_ini};
            var espColAuto = (nCol > 1) ? ((L - 2.0 * cx - (nCol * largStMaior)) / (nCol - 1.0)) : 0.0;

            var dados = {{
                acao: acao,
                nome_pilar: document.getElementById("nome_pilar").value || "{nome_p}",
                hd: parseFloat(document.getElementById("hd").value.replace(',', '.')) || {hd_p},
                cota_x: cx,
                cota_y: parseFloat(document.getElementById("cota_y").value.replace(',', '.')) || {cota_y_ini},
                cota_y_linha: parseFloat(document.getElementById("cota_y_linha").value.replace(',', '.')) || {cota_y_linha_ini},
                cota_x_linha: parseFloat(document.getElementById("cota_x_linha").value.replace(',', '.')) || {cota_x_linha_ini},
                num_colunas: nCol,
                num_linhas: nLin,
                espaco_colunas: espColAuto,
                espaco_linhas: espLin,
                num_maior: nCol,
                espaco_maior: espColAuto,
                num_menor: parseInt(document.getElementById("num_menor").value) || {num_menor_sug},
                espaco_menor: espLin,
                tem_inclinado: document.getElementById("tem_inclinado").checked,
                cota_inclinado: parseFloat(document.getElementById("cota_inclinado").value.replace(',', '.')) || {cota_inclinado_ini},
                num_pinos: nLin,
                larg_estribo_maior: largStMaior,
                alt_estribo_maior: altStMaior,
                larg_estribo_menor: largStMenor,
                alt_estribo_menor: altStMenor,
                larg_estribo: largStMaior,
                alt_estribo: altStMaior,
                bitola_estribo: parseFloat(document.getElementById("bitola_estribo").value.replace(',', '.')) || 8.0,
                pos_estribo: (document.getElementById("pos_estribo").value || "1").trim(),
                esp_pinos: largStMaior,
                desenhar_detalhe_estribo: true,
                desenhar_cotas: true
            }};

            try {{
                var fso = new ActiveXObject("Scripting.FileSystemObject");
                var a = fso.CreateTextFile("{json_js}", true);
                a.WriteLine(JSON.stringify(dados));
                a.Close();
            }} catch (e) {{
                alert("Erro ao salvar: " + e.message);
            }}

            window.close();
        }}
    </script>
</head>
<body>
    <div class="topbar">
        <div>
            <h1>Armação de Punção - Detalhamento das Cotas & Geometria</h1>
            <p>G3 Plugins - Ediglânthio Samuel Araújo Brandão - TQS</p>
        </div>
    </div>

    <div class="main-wrapper">
        <!-- COLUNA ESQUERDA: DIAGRAMA INTERATIVO COM COTAS SOBREPOSTAS -->
        <div class="col-left">
            <div class="card">
                <h3>Detalhamento das Cotas (Preencha os valores nas caixas vermelhas)</h3>
                <div class="diag-container">
                    <img src="diagrama_cotas.png" class="diag-img" alt="Diagrama de Cotas da Punção" />
                    <!-- Box 1: x (Face Maior - da quina ao 1º ferro) -->
                    <input type="text" id="cota_x" class="cota-box box-x" value="{cota_x_ini}" title="Distância da quina até o 1º ferro da face maior (x)" onchange="calcEspacoMaior()" />
                    <!-- Box 2: y (Face Maior - da face do pilar ao 1º pino) -->
                    <input type="text" id="cota_y" class="cota-box box-y" value="{cota_y_ini}" title="Distância da face até o 1º pino/conector da face maior (y)" />
                    <!-- Box 3: y' (Face Menor - da quina ao 1º ferro) -->
                    <input type="text" id="cota_y_linha" class="cota-box box-y-linha" value="{cota_y_linha_ini}" title="Distância da quina até o 1º ferro da face menor (y')" onchange="calcEspacoMenor()" />
                    <!-- Box 4: x' (Face Menor - da face do pilar ao 1º pino) -->
                    <input type="text" id="cota_x_linha" class="cota-box box-x-linha" value="{cota_x_linha_ini}" title="Distância da face até o 1º pino/conector da face menor (x')" />
                </div>
            </div>

            <!-- IDENTIFICAÇÃO DO PILAR (EMBAIXO DA IMAGEM) -->
            <div class="card" style="margin-top:9px;">
                <h3>Identificação do Pilar</h3>
                <div class="campo">
                    <label>Título / Identificação:</label>
                    <input type="text" id="nome_pilar" value="{nome_p}" style="width:130px; text-align:left;" />
                </div>
                <div class="item-info">
                    <span class="rotulo">Dimensões do Pilar:</span>
                    <span class="valor">{int(col_dx)} x {int(col_dy)} cm (Face maior: {int(comp_maior)} cm)</span>
                </div>
                <div class="item-info">
                    <span class="rotulo">Área do Quadrado da Laje:</span>
                    <span class="valor">{int(larg_area)} x {int(alt_area)} cm</span>
                </div>
                <div class="campo" style="margin-top:6px;">
                    <label>Espessura HC (cm):</label>
                    <input type="text" id="hd" value="{hd_p}" onchange="atualizarHdEstribo()" />
                </div>
            </div>
        </div>

        <!-- COLUNA DIREITA: CONFIGURAÇÕES DA ARMADURA -->
        <div class="col-right">
            <!-- 1. ESTRIBOS DA FACE MAIOR -->
            <div class="card">
                <h3>Estribos — Face Maior ({int(comp_maior)} cm)</h3>
                <div class="campo">
                    <label>Nº de Colunas:</label>
                    <input type="number" id="num_colunas" value="{num_colunas_sug}" min="1" max="30" onchange="calcEspacoMaior()" />
                </div>
                <div class="campo">
                    <label>Nº de Linhas:</label>
                    <input type="number" id="num_linhas" value="{num_linhas_sug}" min="1" max="20" onchange="calcContagemEstribos()" />
                </div>
                <div class="campo">
                    <label>Distância entre linhas (cm):</label>
                    <input type="text" id="espaco_linhas" value="{espaco_linhas_ini}" onchange="calcContagemEstribos()" />
                </div>
                <div class="campo" style="border-top: 1px dashed #e0f2f1; padding-top: 5px; margin-top: 4px;">
                    <label>Largura do estribo (cm):</label>
                    <input type="text" id="larg_estribo_maior" value="{larg_estribo_ini}" onchange="calcEspacoMaior()" />
                </div>
                <div class="campo" style="margin-bottom: 0;">
                    <label>Altura do estribo (cm):</label>
                    <input type="text" id="alt_estribo_maior" value="{alt_estribo_ini}" onchange="calcContagemEstribos()" />
                </div>
            </div>

            <!-- 2. ESTRIBOS DA FACE MENOR -->
            <div class="card">
                <h3>Estribos — Face Menor ({int(comp_menor)} cm)</h3>
                <div class="campo">
                    <label>Nº de Estribos:</label>
                    <input type="number" id="num_menor" value="{num_menor_sug}" min="1" max="20" onchange="calcEspacoMenor()" />
                </div>
                <div class="campo" style="border-top: 1px dashed #e0f2f1; padding-top: 5px; margin-top: 4px;">
                    <label>Largura do estribo (cm):</label>
                    <input type="text" id="larg_estribo_menor" value="{larg_estribo_ini}" onchange="calcContagemEstribos()" />
                </div>
                <div class="campo" style="margin-bottom: 0;">
                    <label>Altura do estribo (cm):</label>
                    <input type="text" id="alt_estribo_menor" value="{alt_estribo_ini}" onchange="calcContagemEstribos()" />
                </div>
            </div>

            <!-- 3. FERROS INCLINADOS & DADOS GERAIS -->
            <div class="card">
                <h3>Ferros Inclinados &amp; Dados Gerais</h3>
                <div class="campo-check" style="margin-top: 0;">
                    <input type="checkbox" id="tem_inclinado" checked onclick="toggleInclinado()" onchange="toggleInclinado()" />
                    <label for="tem_inclinado"><b>Gerar ferros inclinados</b> (diagonal nas 4 quinas)</label>
                </div>
                <div class="campo" id="wrap_cota_inclinado" style="margin-top:4px; padding:4px 8px; background:#e0f2f1; border-radius:4px; border:1px solid #80cbc4;">
                    <label for="cota_inclinado" style="color:#004d40;">Cota do ferro inclinado (cm):</label>
                    <input type="text" id="cota_inclinado" value="{cota_inclinado_ini}" />
                </div>
                <div class="campo" style="margin-top: 6px;">
                    <label>Bitola do estribo:</label>
                    <select id="bitola_estribo" onchange="calcContagemEstribos()">
                        <option value="5.0">ø 5.0 mm</option>
                        <option value="6.3">ø 6.3 mm</option>
                        <option value="8.0" selected>ø 8.0 mm</option>
                        <option value="10.0">ø 10.0 mm</option>
                        <option value="12.5">ø 12.5 mm</option>
                    </select>
                </div>
                <div class="campo" style="margin-bottom: 0;">
                    <label>Posição / Marca:</label>
                    <input type="text" id="pos_estribo" value="{pos_estribo_ini}" style="width:85px; text-align:center;" onchange="calcContagemEstribos()" />
                </div>
                <div id="txt_resumo_preview" style="margin-top: 8px; padding: 6px 10px; background: #f1f8e9; border: 1px solid #c8e6c9; border-radius: 5px;"></div>
            </div>
        </div>
    </div>

    <div class="btns">
        <button onclick="responder('cancelar')">Cancelar</button>
        <button style="border-color:#00796b; color:#00796b;" onclick="responder('recopiar')">
            ⬚ Abrir Nova Janela
        </button>
        <button class="btn-principal" onclick="responder('colar')">
            ✓ Confirmar e Colar no Desenho
        </button>
    </div>
</body>
</html>
"""

    with open(hta_path, "w", encoding="utf-8") as f:
        f.write(hta_content)

    subprocess.call(["mshta.exe", hta_path])

    dados = None
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            dados = json.load(f)
        try:
            os.remove(json_path)
        except Exception:
            pass

    if os.path.exists(hta_path):
        try:
            os.remove(hta_path)
        except Exception:
            pass

    return dados


# ==============================================================================
# DESENHO DA ARMADURA DE PUNÇÃO: TRILHOS, PINOS E COTAGEM
# ==============================================================================

def desenhar_armadura_puncao(dwg, x_alvo, y_alvo, pilar, config):
    """
    Desenha os estribos, conectores/pinos e cotas da Armadura de Punção em volta do pilar:
    - Face maior: malha de (num_colunas x num_linhas) com estribos na horizontal em sequência,
      descontando cota_x de cada lado e o tamanho do estribo para calcular o espaço entre colunas;
    - Face menor: sequência de num_menor estribos na vertical indo para os lados;
    - 4 quinas: ferros inclinados a 45° (mantidos inalterados por enquanto).
    """
    draw = dwg.draw

    # 1. Parâmetros da configuração
    cota_x = float(config.get("cota_x", 6.75))
    cota_y = float(config.get("cota_y", 10.0))
    cota_y_linha = float(config.get("cota_y_linha", 7.55))
    cota_x_linha = float(config.get("cota_x_linha", 10.0))
    cota_inclinado = float(config.get("cota_inclinado", 10.0))

    num_colunas = max(1, int(config.get("num_colunas", config.get("num_maior", 5))))
    num_linhas = max(1, int(config.get("num_linhas", 4)))
    espaco_linhas = float(config.get("espaco_linhas", 15.0))

    num_menor = max(1, int(config.get("num_menor", 3)))
    espaco_menor = float(config.get("espaco_menor", 15.0))

    tem_inclinado = bool(config.get("tem_inclinado", True))
    num_pinos = int(config.get("num_pinos", 3))
    larg_estribo = float(config.get("larg_estribo", config.get("esp_pinos", 15.0)))
    larg_estribo_maior = float(config.get("larg_estribo_maior", larg_estribo))
    larg_estribo_menor = float(config.get("larg_estribo_menor", larg_estribo))
    esp_pinos = larg_estribo_maior
    desenhar_cotas = bool(config.get("desenhar_cotas", True))

    # 2. Dimensões do pilar
    c_xmin, c_xmax, c_ymin, c_ymax, col_dx, col_dy, orientacao = obter_geometria_pilar(pilar)

    px_min = x_alvo + c_xmin
    px_max = x_alvo + c_xmax
    py_min = y_alvo + c_ymin
    py_max = y_alvo + c_ymax

    raio_pino = 1.15
    # Lógica dinâmica do reforço radial (ferros inclinados nas 4 quinas):
    # - Pontas antes da 1ª bolinha e depois da última usam cota_inclinado (ex: 10 cm)
    # - Espaço entre as bolinhas usa espaco_linhas (distância vertical entre as linhas de estribos paralelos, ex: 13 cm)
    ponta_inclinado = cota_inclinado if cota_inclinado > 0 else 10.0
    passo_inclinado = espaco_linhas if espaco_linhas > 0 else 13.0
    n_estribos = max(1, int(config.get("num_linhas", num_pinos)))
    comp_trilho = 2.0 * ponta_inclinado + max(0, n_estribos - 1) * passo_inclinado

    NIV_FERRO = 220
    COR_TRILHO = 4    # Ciano
    COR_PINO = 1      # Vermelho
    NIV_COTA = 241
    COR_COTA = 3      # Verde

    def _fmt_num(val):
        val_r = round(float(val), 2)
        return f"{int(val_r)}" if val_r.is_integer() else f"{val_r}"

    def _linha_ferro(x1, y1, x2, y2):
        draw.level = NIV_FERRO
        draw.color = COR_TRILHO
        draw.style = 0
        draw.Line(x1, y1, x2, y2)

    def _pino(xc_p, yc_p):
        draw.level = NIV_FERRO
        draw.color = COR_PINO
        draw.style = 0
        draw.Circle(xc_p, yc_p, raio_pino)

    def _desenhar_estribo_individual(x1, y1, x2, y2):
        """
        Desenha um estribo individual na planta:
        1 linha ciano de (x1, y1) até (x2, y2) com 1 bolinha vermelha em cada extremidade.
        """
        _linha_ferro(x1, y1, x2, y2)
        _pino(x1, y1)
        _pino(x2, y2)

    def _desenhar_trilho_estribos(x_base, y_base, ux, uy, d_ini):
        """
        Desenha o ferro inclinado (reforço radial) nas 4 quinas:
        - A linha azul começa em d_ini, passa direto pelas bolinhas (sobrando 10 cm antes da 1ª
          e 10 cm depois da última);
        - Cada bolinha vermelha simples fica espaçada a cada 13 cm ao longo da diagonal.
        """
        x_ini = x_base + ux * d_ini
        y_ini = y_base + uy * d_ini
        x_fim = x_base + ux * (d_ini + comp_trilho)
        y_fim = y_base + uy * (d_ini + comp_trilho)
        _linha_ferro(x_ini, y_ini, x_fim, y_fim)

        for k in range(n_estribos):
            d_bolinha = d_ini + ponta_inclinado + k * passo_inclinado
            _pino(x_base + ux * d_bolinha, y_base + uy * d_bolinha)

    def _linha_cota(x1, y1, x2, y2):
        draw.level = NIV_COTA
        draw.color = COR_COTA
        draw.style = 0
        draw.Line(x1, y1, x2, y2)

    def _tick_cota(x, y):
        draw.level = NIV_COTA
        draw.color = COR_COTA
        draw.style = 0
        draw.Line(x - 1.2, y - 1.2, x + 1.2, y + 1.2)

    def _texto_cota(x, y, txt, h=4.8, ang=0.0):
        draw.level = NIV_COTA
        draw.color = COR_COTA
        draw.Text(x, y, h, ang, str(txt))

    def _cota_horizontal_staggered(y_cota, pts_x, witness_y_start):
        """
        Desenha linha de cota horizontal no padrão TQS.
        """
        _linha_cota(pts_x[0] - 3.0, y_cota, pts_x[-1] + 3.0, y_cota)

        n_pts = len(pts_x)
        for idx, px_c in enumerate(pts_x):
            if idx == 0 or idx == n_pts - 1:
                _linha_cota(px_c, witness_y_start, px_c, y_cota + 4.5)
            else:
                _linha_cota(px_c, y_cota - 2.5, px_c, y_cota + 5.0)
            _tick_cota(px_c, y_cota)

        n_interv = n_pts - 1
        for i in range(n_interv):
            x1_c, x2_c = pts_x[i], pts_x[i + 1]
            txt_v = _fmt_num(x2_c - x1_c)
            larg_txt = len(txt_v) * 3.5
            xm_c = (x1_c + x2_c) / 2.0

            if i == 0 and n_interv > 1:
                _texto_cota(x1_c - larg_txt - 1.8, y_cota + 1.8, txt_v, h=4.8)
            elif i == n_interv - 1 and n_interv > 1:
                _texto_cota(x2_c + 2.0, y_cota + 1.8, txt_v, h=4.8)
            else:
                if (i % 2) == 1:
                    x_start = xm_c + 2.0
                    y_start = y_cota + 1.2
                    x_knee = xm_c - 1.2
                    y_knee = y_cota + 10.5
                    x_shelf_left = x_knee - max(larg_txt + 2.0, 14.0)
                    _linha_cota(x_start, y_start, x_knee, y_knee)
                    _linha_cota(x_knee, y_knee, x_shelf_left, y_knee)
                    _texto_cota(x_shelf_left + 0.8, y_knee + 1.5, txt_v, h=4.8)
                else:
                    _texto_cota(xm_c - larg_txt / 2.0, y_cota + 1.8, txt_v, h=4.8)

    def _cota_vertical_alinhada(x_cota, pts_y, witness_x_start):
        """
        Desenha linha de cota vertical no padrão TQS.
        """
        _linha_cota(x_cota, pts_y[0] - 3.0, x_cota, pts_y[-1] + 3.0)

        n_pts = len(pts_y)
        for idx, py_c in enumerate(pts_y):
            if idx == 0 or idx == n_pts - 1:
                _linha_cota(witness_x_start, py_c, x_cota - 4.0, py_c)
            else:
                _linha_cota(x_cota - 4.0, py_c, x_cota + 2.5, py_c)
            _tick_cota(x_cota, py_c)

        n_interv = n_pts - 1
        for j in range(n_interv):
            y1_c, y2_c = pts_y[j], pts_y[j + 1]
            txt_vy = _fmt_num(y2_c - y1_c)
            larg_txt = len(txt_vy) * 3.5
            ym_c = (y1_c + y2_c) / 2.0

            if j == 0 and n_interv > 1:
                _texto_cota(x_cota - 1.8, y1_c - larg_txt - 2.0, txt_vy, h=4.8, ang=90.0)
            elif j == n_interv - 1 and n_interv > 1:
                _texto_cota(x_cota - 1.8, y2_c + 2.2, txt_vy, h=4.8, ang=90.0)
            else:
                if n_interv > 3 and (j % 2) == 1:
                    y_start = ym_c - 1.5
                    x_knee = x_cota - 12.5
                    y_knee = ym_c + 1.2
                    y_shelf_top = y_knee + max(larg_txt + 2.0, 14.0)
                    _linha_cota(x_cota - 1.2, y_start, x_knee, y_knee)
                    _linha_cota(x_knee, y_knee, x_knee, y_shelf_top)
                    _texto_cota(x_knee - 1.8, y_knee + 0.8, txt_vy, h=4.8, ang=90.0)
                else:
                    _texto_cota(x_cota - 7.5, ym_c - larg_txt / 2.0, txt_vy, h=4.8, ang=90.0)

    def _cotas_afastamento_ferros(dist_esq, dist_inf):
        """
        Desenha as cotas de afastamento entre a face do pilar e o 1º pino dos ferros.
        """
        # 1. Cota horizontal no canto superior esquerdo (distância da face esquerda ao 1º pino)
        x_pino_esq = px_min - dist_esq
        y_cota_h = py_max + max(dist_inf, 10.0) + 15.0
        _linha_cota(x_pino_esq, py_max - min(cota_y_linha * 0.5, 3.0), x_pino_esq, y_cota_h + 3.5)
        _linha_cota(px_min, py_max + 3.5, px_min, y_cota_h + 3.5)
        _linha_cota(x_pino_esq - 2.5, y_cota_h, px_min + 2.5, y_cota_h)
        _tick_cota(x_pino_esq, y_cota_h)
        _tick_cota(px_min, y_cota_h)
        txt_esq = _fmt_num(dist_esq)
        larg_esq = len(txt_esq) * 3.5
        _texto_cota(x_pino_esq - larg_esq - 2.0, y_cota_h + 1.5, txt_esq, h=4.8, ang=0.0)

        # 2. Cota vertical no canto inferior direito (distância da face inferior ao 1º pino)
        y_pino_inf = py_min - dist_inf
        x_cota_v = px_max + 8.5
        txt_inf = _fmt_num(dist_inf)
        larg_inf = len(txt_inf) * 3.5
        _linha_cota(px_max + 2.0, py_min, x_cota_v + 3.5, py_min)
        _linha_cota(px_max + 3.5, y_pino_inf, x_cota_v + 3.5, y_pino_inf)
        _linha_cota(x_cota_v, py_min + 2.5, x_cota_v, y_pino_inf - larg_inf - 3.5)
        _tick_cota(x_cota_v, py_min)
        _tick_cota(x_cota_v, y_pino_inf)
        _texto_cota(x_cota_v - 1.8, y_pino_inf - larg_inf - 2.5, txt_inf, h=4.8, ang=90.0)

    # ==========================================================================
    # CASO 1: PILAR HORIZONTAL (Face maior no topo e base)
    # ==========================================================================
    if orientacao == 'H':
        # 1. FACES MAIORES (Superior e Inferior):
        #    Estribos na HORIZONTAL em sequência (num_colunas x num_linhas).
        #    Desconta cota_x de cada lado e o tamanho do estribo da face maior (larg_estribo_maior) para calcular o espaço entre eles.
        if num_colunas == 1:
            x0_col = (px_min + px_max - larg_estribo_maior) / 2.0
            colunas_x = [(x0_col, x0_col + larg_estribo_maior)]
        else:
            gap_col = (col_dx - 2.0 * cota_x - num_colunas * larg_estribo_maior) / (num_colunas - 1)
            passo_col = larg_estribo_maior + gap_col
            colunas_x = [
                (px_min + cota_x + c * passo_col, px_min + cota_x + c * passo_col + larg_estribo_maior)
                for c in range(num_colunas)
            ]

        for r in range(num_linhas):
            y_sup_r = py_max + cota_y + r * espaco_linhas
            y_inf_r = py_min - (cota_y + r * espaco_linhas)
            for x_ini_c, x_fim_c in colunas_x:
                # Face superior (horizontal)
                _desenhar_estribo_individual(x_ini_c, y_sup_r, x_fim_c, y_sup_r)
                # Face inferior (horizontal)
                _desenhar_estribo_individual(x_ini_c, y_inf_r, x_fim_c, y_inf_r)

        # 2. FACES MENORES (Esquerda e Direita):
        #    1 sequência de num_menor estribos na VERTICAL indo para os lados (usa larg_estribo_menor).
        y_top_menor = py_max - cota_y_linha
        y_bot_menor = y_top_menor - larg_estribo_menor

        for k in range(num_menor):
            x_esq_k = px_min - (cota_x_linha + k * espaco_menor)
            x_dir_k = px_max + (cota_x_linha + k * espaco_menor)
            # Face esquerda (vertical)
            _desenhar_estribo_individual(x_esq_k, y_bot_menor, x_esq_k, y_top_menor)
            # Face direita (vertical)
            _desenhar_estribo_individual(x_dir_k, y_bot_menor, x_dir_k, y_top_menor)

        # 3. COTAS (Se ativadas)
        if desenhar_cotas:
            alt_malha_sup = cota_y + (num_linhas - 1) * espaco_linhas
            y_cota_sup = py_max + alt_malha_sup + 9.0
            pts_cota_x = [px_min]
            for x_ini_c, x_fim_c in colunas_x:
                pts_cota_x.extend([x_ini_c, x_fim_c])
            pts_cota_x.append(px_max)
            pts_cota_x = sorted(list(set(round(p, 4) for p in pts_cota_x)))
            _cota_horizontal_staggered(y_cota_sup, pts_cota_x, py_max + 3.5)

            larg_seq_esq = cota_x_linha + (num_menor - 1) * espaco_menor
            x_cota_esq = px_min - larg_seq_esq - 9.0
            pts_cota_y = sorted(list(set([round(py_min, 4), round(y_bot_menor, 4), round(y_top_menor, 4), round(py_max, 4)])))
            _cota_vertical_alinhada(x_cota_esq, pts_cota_y, px_min - 3.5)

            _cotas_afastamento_ferros(cota_x_linha, cota_y)

    # ==========================================================================
    # CASO 2: PILAR VERTICAL (Face maior na lateral esquerda/direita)
    # ==========================================================================
    else:
        # 1. FACES MAIORES (Esquerda e Direita):
        #    Estribos paralelos à face maior (verticais) em malha (num_colunas x num_linhas).
        if num_colunas == 1:
            y0_col = (py_min + py_max - larg_estribo_maior) / 2.0
            colunas_y = [(y0_col, y0_col + larg_estribo_maior)]
        else:
            gap_col = (col_dy - 2.0 * cota_x - num_colunas * larg_estribo_maior) / (num_colunas - 1)
            passo_col = larg_estribo_maior + gap_col
            colunas_y = [
                (py_min + cota_x + c * passo_col, py_min + cota_x + c * passo_col + larg_estribo_maior)
                for c in range(num_colunas)
            ]

        for r in range(num_linhas):
            x_esq_r = px_min - (cota_y + r * espaco_linhas)
            x_dir_r = px_max + cota_y + r * espaco_linhas
            for y_ini_c, y_fim_c in colunas_y:
                _desenhar_estribo_individual(x_esq_r, y_ini_c, x_esq_r, y_fim_c)
                _desenhar_estribo_individual(x_dir_r, y_ini_c, x_dir_r, y_fim_c)

        # 2. FACES MENORES (Superior e Inferior):
        #    1 sequência de num_menor estribos paralelos à face menor (horizontais, usa larg_estribo_menor).
        x_ini_menor = px_min + cota_y_linha
        x_fim_menor = x_ini_menor + larg_estribo_menor

        for k in range(num_menor):
            y_sup_k = py_max + cota_x_linha + k * espaco_menor
            y_inf_k = py_min - (cota_x_linha + k * espaco_menor)
            _desenhar_estribo_individual(x_ini_menor, y_sup_k, x_fim_menor, y_sup_k)
            _desenhar_estribo_individual(x_ini_menor, y_inf_k, x_fim_menor, y_inf_k)

        # 3. COTAS
        if desenhar_cotas:
            larg_malha_esq = cota_y + (num_linhas - 1) * espaco_linhas
            x_cota_esq = px_min - larg_malha_esq - 9.0
            pts_cota_y = [py_min]
            for y_ini_c, y_fim_c in colunas_y:
                pts_cota_y.extend([y_ini_c, y_fim_c])
            pts_cota_y.append(py_max)
            pts_cota_y = sorted(list(set(round(p, 4) for p in pts_cota_y)))
            _cota_vertical_alinhada(x_cota_esq, pts_cota_y, px_min - 3.5)

            alt_seq_sup = cota_x_linha + (num_menor - 1) * espaco_menor
            y_cota_sup = py_max + alt_seq_sup + 9.0
            pts_cota_x = sorted(list(set([round(px_min, 4), round(x_ini_menor, 4), round(x_fim_menor, 4), round(px_max, 4)])))
            _cota_horizontal_staggered(y_cota_sup, pts_cota_x, py_max + 3.5)

            _cotas_afastamento_ferros(cota_y, cota_x_linha)

    # ==========================================================================
    # 3. FERROS INCLINADOS NAS 4 QUINAS (DIAGONAL A 45°)
    # ==========================================================================
    if tem_inclinado:
        d0 = cota_inclinado if cota_inclinado > 0 else 10.0
        quinas = [
            (px_min, py_max, -1.0, 1.0),   # Quina Sup-Esq
            (px_max, py_max, 1.0, 1.0),    # Quina Sup-Dir
            (px_max, py_min, 1.0, -1.0),   # Quina Inf-Dir
            (px_min, py_min, -1.0, -1.0)   # Quina Inf-Esq
        ]
        cos45 = 0.70710678
        sin45 = 0.70710678

        for qx, qy, sx, sy in quinas:
            # Desenha o ferro inclinado tocando exatamente na quina (d_ini=0.0)
            _desenhar_trilho_estribos(qx, qy, sx * cos45, sy * sin45, 0.0)
            lx1 = qx + sx * d0 * cos45
            ly1 = qy + sy * d0 * sin45

            # Cota inclinada na quina superior direita (igual à imagem de referência)
            if desenhar_cotas and sx == 1.0 and sy == 1.0:
                offset_d = 7.5
                txt_d0 = _fmt_num(d0)
                larg_d0 = len(txt_d0) * 3.6
                ext_esq = larg_d0 + 3.5

                # Vetor ao longo da diagonal u=(cos45, sin45), vetor perpendicular para baixo-direita v=(cos45, -sin45)
                c1_x = qx + offset_d * cos45
                c1_y = qy - offset_d * sin45
                c2_x = lx1 + offset_d * cos45
                c2_y = ly1 - offset_d * sin45

                # Linhas de chamada perpendiculares à diagonal (a -45°)
                _linha_cota(qx + 1.5 * cos45, qy - 1.5 * sin45, qx + (offset_d + 3.2) * cos45, qy - (offset_d + 3.2) * sin45)
                _linha_cota(lx1 + 1.8 * cos45, ly1 - 1.8 * sin45, lx1 + (offset_d + 3.2) * cos45, ly1 - (offset_d + 3.2) * sin45)

                # Linha de cota paralela à diagonal (a +45°) com prolongamento inferior-esquerdo para o texto
                _linha_cota(c1_x - ext_esq * cos45, c1_y - ext_esq * sin45, c2_x + 2.5 * cos45, c2_y + 2.5 * sin45)

                # Ticks verticais nas interseções da cota diagonal (padrão TQS para cota a 45°)
                _linha_cota(c1_x, c1_y - 2.0, c1_x, c1_y + 2.0)
                _linha_cota(c2_x, c2_y - 2.0, c2_x, c2_y + 2.0)

                # Texto posicionado sobre o prolongamento inferior-esquerdo da linha de cota a 45°
                tx_d = c1_x - (larg_d0 + 2.2) * cos45 - 1.5 * cos45
                ty_d = c1_y - (larg_d0 + 2.2) * sin45 + 1.5 * sin45
                _texto_cota(tx_d, ty_d, txt_d0, h=4.8, ang=45.0)


# ==============================================================================
# DESENHO DO CORTE A-A E SÍMBOLOS DE CORTE NA PLANTA (OPCIONAL/FUTURO)
# ==============================================================================

def desenhar_corte_aa(dwg, x_alvo, y_alvo, pilar, config, rebar_estribo=None):
    """
    Desenha o corte esquemático na parte inferior e os símbolos de corte A na planta:
    1. Símbolos A ▲ nas laterais do quadrado da planta (Nível 241, Cor 2 Amarelo);
    2. Perfil de concreto da laje e do pilar com linhas de quebra (Nível 241, Cor 3 Verde);
    3. Barras longitudinais contínuas superior e inferior (Nível 220, Cor 4 Ciano);
    4. Bolinhas vermelhas da armadura transversal (Nível 220, Cor 1 Vermelho);
    5. Estribos de punção em corte alinhados com os estribos da planta, com ganchos a 45°
       (Nível 220, Amarelos na esquerda; 1º Roxo e demais Amarelos na direita);
    6. Cota vertical da espessura da laje HD na lateral direita (Nível 241, Cor 3 Verde).
    """
    draw = dwg.draw

    hd = float(config.get("hd", pilar.get("hd", 26.0)))
    num_pinos = int(config.get("num_pinos", 3))
    esp_pinos = float(config.get("esp_pinos", 15.0))
    larg_area = float(pilar.get("larg_area", 248.0))
    alt_area = float(pilar.get("alt_area", 200.0))

    c_xmin, c_xmax, c_ymin, c_ymax, col_dx, col_dy, orientacao = obter_geometria_pilar(pilar)

    px_min = x_alvo + c_xmin
    px_max = x_alvo + c_xmax
    py_min = y_alvo + c_ymin
    py_max = y_alvo + c_ymax

    box_x1 = x_alvo - larg_area / 2.0
    box_x2 = x_alvo + larg_area / 2.0
    box_y1 = y_alvo - alt_area / 2.0

    num_menor = max(1, int(config.get("num_menor", 3)))
    espaco_menor = float(config.get("espaco_menor", 13.0))
    cota_x_linha = float(config.get("cota_x_linha", 10.0))
    cota_x = float(config.get("cota_x", 6.75))
    cota_y = float(config.get("cota_y", 10.0))
    cota_y_linha = float(config.get("cota_y_linha", 7.55))
    num_colunas = max(1, int(config.get("num_colunas", config.get("num_maior", 4))))
    num_linhas = max(1, int(config.get("num_linhas", 4)))
    espaco_linhas = float(config.get("espaco_linhas", 13.0))
    larg_st_maior = float(config.get("larg_estribo_maior", config.get("larg_estribo", 15.0)))
    alt_st_maior = float(config.get("alt_estribo_maior", config.get("alt_estribo", 21.0)))
    larg_estribo_menor = float(config.get("larg_estribo_menor", larg_st_maior))

    if orientacao == 'H':
        d_face_corte = cota_x_linha
        esp_corte_menor = espaco_menor
        n_ferros_laterais = num_menor
    else:
        d_face_corte = cota_y
        esp_corte_menor = espaco_linhas
        n_ferros_laterais = num_linhas

    raio_dot = 1.15
    comp_trilho_lateral = d_face_corte + (n_ferros_laterais - 1) * esp_corte_menor

    # ==========================================================================
    # 1. SIMBOLOS DE CORTE A-A NA PLANTA (Laterais da laje - Padrao Espelhado)
    # ==========================================================================
    # Padrao TQS de corte espelhado nas laterais da planta:
    # - Esquerda: [ Seta ] [ Letra A ]  (seta na ponta externa, 'A' voltado para o desenho)
    # - Direita:  [ Letra A ] [ Seta ]  ('A' voltado para o desenho, seta na ponta externa)
    # Ambas as setas sao triangulos amarelos preenchidos apontando para CIMA.
    # Sem linha horizontal passando por baixo.
    py_corte_planta = (py_min + py_max) / 2.0

    draw.level = 241
    draw.color = 2  # Amarelo
    draw.style = 0

    larg_seta = 7.0
    alt_seta = 6.0
    alt_txt = 6.5
    larg_txt = 4.5
    gap_seta_txt = 3.5
    ext_linha = 5.5

    # Alinhamento vertical centrado no eixo do corte
    y_base_corte = py_corte_planta - alt_seta / 2.0

    def _desenhar_seta_solida(x_c, y_b):
        """Desenha triangulo amarelo solido apontando para CIMA."""
        draw.Line(x_c - larg_seta / 2.0, y_b, x_c + larg_seta / 2.0, y_b)
        draw.Line(x_c - larg_seta / 2.0, y_b, x_c, y_b + alt_seta)
        draw.Line(x_c + larg_seta / 2.0, y_b, x_c, y_b + alt_seta)
        n_passos = int(alt_seta / 0.20)
        for i in range(1, n_passos):
            y_curr = y_b + i * 0.20
            t = (y_b + alt_seta - y_curr) / alt_seta
            w_h = (larg_seta / 2.0) * t
            draw.Line(x_c - w_h, y_curr, x_c + w_h, y_curr)

    # Afastamento lateral seguro em relacao aos trilhos/area
    x_ext_esq = min(box_x1, px_min - comp_trilho_lateral - 15.0)
    x_ext_dir = max(box_x2, px_max + comp_trilho_lateral + 15.0)

    # Posicoes de referencia nas laterais - coladas no quadrado da area
    x_ref_esq = box_x1 - 8.0
    x_ref_dir = box_x2 + 8.0

    # 1.1 Simbolo Esquerdo: [ Seta ]  [ A ] + Linha na base
    x_tri_esq = x_ref_esq - (larg_seta / 2.0)
    _desenhar_seta_solida(x_tri_esq, y_base_corte)
    x_txt_esq = x_tri_esq + (larg_seta / 2.0) + gap_seta_txt
    draw.Text(x_txt_esq, y_base_corte, alt_txt, 0.0, "A")
    # Linha horizontal na base passando sob a seta e o texto, prolongando em direcao ao desenho
    x_lin_esq_ini = x_tri_esq - (larg_seta / 2.0)
    x_lin_esq_fim = x_txt_esq + larg_txt + ext_linha
    draw.Line(x_lin_esq_ini, y_base_corte, x_lin_esq_fim, y_base_corte)

    # 1.2 Simbolo Direito: [ A ]  [ Seta ] + Linha na base
    x_tri_dir = x_ref_dir + (larg_seta / 2.0)
    _desenhar_seta_solida(x_tri_dir, y_base_corte)
    x_txt_dir = x_tri_dir - (larg_seta / 2.0) - gap_seta_txt - larg_txt
    draw.Text(x_txt_dir, y_base_corte, alt_txt, 0.0, "A")
    # Linha horizontal na base passando sob o texto e a seta, prolongando em direcao ao desenho
    x_lin_dir_ini = x_txt_dir - ext_linha
    x_lin_dir_fim = x_tri_dir + (larg_seta / 2.0)
    draw.Line(x_lin_dir_ini, y_base_corte, x_lin_dir_fim, y_base_corte)

    # ==========================================================================
    # 2. POSICIONAMENTO E GEOMETRIA DO CONCRETO NO CORTE (PARTE DE BAIXO)
    # ==========================================================================
    y_corte_topo = box_y1 - 45.0
    y_corte_base = y_corte_topo - hd

    # Largura da laje no corte acompanha os estribos laterais + folga
    x_corte_esq = px_min - comp_trilho_lateral - 24.0
    x_corte_dir = px_max + comp_trilho_lateral + 24.0

    y_col_sup = y_corte_topo + 18.0
    y_col_inf = y_corte_base - 18.0

    def _linha_quebra_h(x1, x2, y, h_zig=6.5, w_zig=2.5):
        xm = (x1 + x2) / 2.0
        draw.Line(x1, y, xm - w_zig, y)
        draw.Line(xm - w_zig, y, xm - w_zig / 3.0, y + h_zig)
        draw.Line(xm - w_zig / 3.0, y + h_zig, xm + w_zig / 3.0, y - h_zig)
        draw.Line(xm + w_zig / 3.0, y - h_zig, xm + w_zig, y)
        draw.Line(xm + w_zig, y, x2, y)

    # Contorno de Concreto (Nível 241, Cor 3 Verde)
    draw.level = 241
    draw.color = 3  # Verde
    draw.style = 0

    # Laje Superior
    draw.Line(x_corte_esq, y_corte_topo, px_min, y_corte_topo)
    draw.Line(px_max, y_corte_topo, x_corte_dir, y_corte_topo)

    # Laje Inferior
    draw.Line(x_corte_esq, y_corte_base, px_min, y_corte_base)
    draw.Line(px_max, y_corte_base, x_corte_dir, y_corte_base)

    # Fechamentos laterais da laje
    draw.Line(x_corte_esq, y_corte_base, x_corte_esq, y_corte_topo)
    draw.Line(x_corte_dir, y_corte_base, x_corte_dir, y_corte_topo)

    # Projeção do Pilar Superior
    draw.Line(px_min, y_corte_topo, px_min, y_col_sup)
    draw.Line(px_max, y_corte_topo, px_max, y_col_sup)
    _linha_quebra_h(px_min, px_max, y_col_sup)

    # Projeção do Pilar Inferior
    draw.Line(px_min, y_corte_base, px_min, y_col_inf)
    draw.Line(px_max, y_corte_base, px_max, y_col_inf)
    _linha_quebra_h(px_min, px_max, y_col_inf)

    # ==========================================================================
    # 3. BARRAS LONGITUDINAIS CONTÍNUAS SUPERIOR E INFERIOR (Ciano)
    # ==========================================================================
    draw.level = 220
    draw.color = 4  # Ciano
    draw.style = 0

    cob = 2.0
    y_bar_top = y_corte_topo - cob
    y_bar_bot = y_corte_base + cob

    draw.Line(x_corte_esq + 1.5, y_bar_top, x_corte_dir - 1.5, y_bar_top)
    draw.Line(x_corte_esq + 1.5, y_bar_bot, x_corte_dir - 1.5, y_bar_bot)

    # ==========================================================================
    # 4. ESTRIBOS DE PUNÇÃO NO CORTE E BOLINHAS VERMELHAS DA ARMADURA TRANSVERSAL
    # ==========================================================================
    y_dot_top = y_bar_top - raio_dot
    y_dot_bot = y_bar_bot + raio_dot
    y_st_top = y_dot_top + raio_dot  # Tangente ao topo dos círculos (alinhado a y_bar_top)
    y_st_bot = y_dot_bot - raio_dot  # Tangente à base dos círculos (alinhado a y_bar_bot)

    def _desenhar_dot_par(xd):
        draw.level = 220
        draw.color = 1  # Vermelho
        draw.style = 0
        draw.Circle(xd, y_dot_top, raio_dot)
        draw.Circle(xd, y_dot_bot, raio_dot)

    def _desenhar_estribo_corte(x_left, x_right, cor_st=2):
        draw.level = 220
        draw.color = cor_st
        draw.style = 0
        # O estribo fica exatamente tangente aos círculos nos 4 lados
        x_st_l = x_left - raio_dot
        x_st_r = x_right + raio_dot
        # Retângulo do estribo perfeitamente encaixado
        draw.Line(x_st_l, y_st_bot, x_st_r, y_st_bot)
        draw.Line(x_st_r, y_st_bot, x_st_r, y_st_top)
        draw.Line(x_st_r, y_st_top, x_st_l, y_st_top)
        draw.Line(x_st_l, y_st_top, x_st_l, y_st_bot)
        # Gancho paralelo a -45° no canto superior esquerdo do estribo
        draw.Line(x_st_l + 1.2, y_st_top, x_st_l + 3.4, y_st_top - 2.2)
        draw.Line(x_st_l, y_st_top - 1.2, x_st_l + 2.2, y_st_top - 3.4)
        # Bolinhas vermelhas nas pernas do estribo
        _desenhar_dot_par(x_left)
        _desenhar_dot_par(x_right)

    # --------------------------------------------------------------------------
    # 4.1. FERROS DA FACE MENOR (Laterais no corte, formato tipo bastão)
    # --------------------------------------------------------------------------
    pts_x_esq = [px_min - (d_face_corte + k * esp_corte_menor) for k in range(n_ferros_laterais)]
    pts_x_dir = [px_max + (d_face_corte + k * esp_corte_menor) for k in range(n_ferros_laterais)]

    def _desenhar_bastao(xf):
        """
        Desenha o ferro da face menor no corte em formato de bastão:
        - Par de bolinhas vermelhas;
        - Duas pernas verticais em ciano nas bordas das bolinhas,
          acabando exatamente na metade (centro) das bolinhas (de y_dot_bot a y_dot_top).
        """
        # 1. Par de bolinhas vermelhas
        _desenhar_dot_par(xf)

        # 2. Haste do bastão (duas linhas verticais em ciano acabando no centro das bolinhas)
        draw.level = 220
        draw.color = 4  # Ciano
        draw.style = 0
        shank_w = raio_dot
        draw.Line(xf - shank_w, y_dot_bot, xf - shank_w, y_dot_top)
        draw.Line(xf + shank_w, y_dot_bot, xf + shank_w, y_dot_top)

    # Ferros na esquerda (formato bastão, simétricos à planta)
    for xf in pts_x_esq:
        _desenhar_bastao(xf)

    # Ferros na direita (formato bastão, simétricos à planta)
    for xf in pts_x_dir:
        _desenhar_bastao(xf)

    # Bolinhas ao longo de toda a extensão da laje além dos estribos laterais
    x_step = esp_corte_menor if esp_corte_menor > 0 else 13.0
    x_ult_esq = min(pts_x_esq)
    x_curr = x_ult_esq - x_step
    while x_curr >= x_corte_esq + 3.5:
        _desenhar_dot_par(x_curr)
        x_curr -= x_step

    x_ult_dir = max(pts_x_dir)
    x_curr = x_ult_dir + x_step
    while x_curr <= x_corte_dir - 3.5:
        _desenhar_dot_par(x_curr)
        x_curr += x_step

    # --------------------------------------------------------------------------
    # 4.2. ESTRIBOS DO CENTRO (Seguindo a quantidade de colunas e o espaço entre eles)
    # --------------------------------------------------------------------------
    if orientacao == 'H':
        if num_colunas == 1:
            x0_col = (px_min + px_max - larg_st_maior) / 2.0
            colunas_x = [(x0_col, x0_col + larg_st_maior)]
        else:
            gap_col = (col_dx - 2.0 * cota_x - num_colunas * larg_st_maior) / (num_colunas - 1)
            passo_col = larg_st_maior + gap_col
            colunas_x = [
                (px_min + cota_x + c * passo_col, px_min + cota_x + c * passo_col + larg_st_maior)
                for c in range(num_colunas)
            ]
    else:
        x_ini_menor = px_min + cota_y_linha
        colunas_x = [(x_ini_menor, x_ini_menor + larg_estribo_menor)]

    for x_l, x_r in colunas_x:
        _desenhar_estribo_corte(x_l, x_r, cor_st=2)

    # Bolinhas intermediárias nos vãos entre colunas se o espaçamento for grande
    for c_idx in range(len(colunas_x) - 1):
        x_gap_ini = colunas_x[c_idx][1]
        x_gap_fim = colunas_x[c_idx + 1][0]
        vao = x_gap_fim - x_gap_ini
        if vao >= 18.0:
            n_dots = max(1, int(round(vao / 13.0)))
            passo = vao / (n_dots + 1)
            for i in range(1, n_dots + 1):
                _desenhar_dot_par(x_gap_ini + i * passo)


    # ==========================================================================
    # 6. CHAMADAS DE TEXTO: FERRAGEM NEGATIVA & FERRAGEM POSITIVA
    # ==========================================================================
    draw.level = 241
    draw.color = 3  # Verde
    draw.style = 0

    # Chamada Superior (apontando para a barra ciano superior, prateleira voltada para a esquerda)
    x_pt_sup = x_corte_esq + 5.0
    y_pt_sup = y_bar_top
    x_knee_sup = x_pt_sup - 7.0
    y_knee_sup = y_corte_topo + 8.0
    x_shelf_sup = x_knee_sup - 52.0
    draw.Line(x_pt_sup, y_pt_sup, x_knee_sup, y_knee_sup)
    draw.Line(x_shelf_sup, y_knee_sup, x_knee_sup, y_knee_sup)
    # Seta na ponta da chamada superior
    draw.Line(x_pt_sup, y_pt_sup, x_pt_sup - 2.8, y_pt_sup + 1.4)
    draw.Line(x_pt_sup, y_pt_sup, x_pt_sup - 1.4, y_pt_sup + 2.8)
    draw.Text(x_shelf_sup + 1.0, y_knee_sup + 1.2, 4.2, 0.0, "FERRAGEM NEGATIVA")

    # Chamada Inferior (apontando para a barra ciano inferior, prateleira voltada para a esquerda)
    x_pt_inf = x_corte_esq + 5.0
    y_pt_inf = y_bar_bot
    x_knee_inf = x_pt_inf - 7.0
    y_knee_inf = y_corte_base - 10.0
    x_shelf_inf = x_knee_inf - 52.0
    draw.Line(x_pt_inf, y_pt_inf, x_knee_inf, y_knee_inf)
    draw.Line(x_shelf_inf, y_knee_inf, x_knee_inf, y_knee_inf)
    # Seta na ponta da chamada inferior
    draw.Line(x_pt_inf, y_pt_inf, x_pt_inf - 2.8, y_pt_inf - 1.4)
    draw.Line(x_pt_inf, y_pt_inf, x_pt_inf - 1.4, y_pt_inf - 2.8)
    draw.Text(x_shelf_inf + 1.0, y_knee_inf + 1.2, 4.2, 0.0, "FERRAGEM POSITIVA")

    # ==========================================================================
    # 7. COTA VERTICAL DA ESPESSURA HD DA LAJE (Direita)
    # ==========================================================================
    draw.level = 241
    draw.color = 3  # Verde
    draw.style = 0

    x_cota_hd = x_corte_dir + 10.0
    draw.Line(x_corte_dir + 2.0, y_corte_base, x_cota_hd + 3.5, y_corte_base)
    draw.Line(x_corte_dir + 2.0, y_corte_topo, x_cota_hd + 3.5, y_corte_topo)
    draw.Line(x_cota_hd, y_corte_base - 3.5, x_cota_hd, y_corte_topo + 3.5)
    draw.Line(x_cota_hd - 1.2, y_corte_base - 1.2, x_cota_hd + 1.2, y_corte_base + 1.2)
    draw.Line(x_cota_hd - 1.2, y_corte_topo - 1.2, x_cota_hd + 1.2, y_corte_topo + 1.2)
    txt_hd = f"{int(hd) if hd.is_integer() else hd}"
    larg_hd = len(txt_hd) * 3.5
    draw.Text(x_cota_hd - 1.8, (y_corte_base + y_corte_topo) / 2.0 - larg_hd / 2.0, 4.8, 90.0, txt_hd)

    # ==========================================================================
    # 8. TÍTULO CORTE A-A
    # ==========================================================================
    draw.level = 245
    draw.color = 2  # Amarelo
    draw.Text((px_min + px_max) / 2.0 - 20.0, y_col_inf - 16.0, 8.5, 0.0, "CORTE  A-A")


# ==============================================================================
# DESENHO DO CORTE B-B (Abaixo do Corte A-A) E SÍMBOLOS DE CORTE B-B
# ==============================================================================

def desenhar_corte_bb(dwg, x_alvo, y_alvo, pilar, config, rebar_estribo=None):
    """
    Desenha o corte esquemático B-B abaixo do CORTE A-A e os símbolos de corte B na planta:
    - Visão da Direita para a Esquerda (setas amarelas apontando para a ESQUERDA ◄);
    - Largura do pilar no corte = col_dy (dimensão vertical da seção do pilar);
    - Estribos das colunas (fora do pilar) ficam DE LADO (formato bastão);
    - Estribos dentro do pilar (face menor) ficam DE FRENTE (formato fechado).
    """
    draw = dwg.draw

    hd = float(config.get("hd", pilar.get("hd", 26.0)))
    larg_area = float(pilar.get("larg_area", 248.0))
    alt_area = float(pilar.get("alt_area", 200.0))

    c_xmin, c_xmax, c_ymin, c_ymax, col_dx, col_dy, orientacao = obter_geometria_pilar(pilar)

    px_min = x_alvo + c_xmin
    px_max = x_alvo + c_xmax
    py_min = y_alvo + c_ymin
    py_max = y_alvo + c_ymax

    box_x1 = x_alvo - larg_area / 2.0
    box_x2 = x_alvo + larg_area / 2.0
    box_y1 = y_alvo - alt_area / 2.0
    box_y2 = y_alvo + alt_area / 2.0

    num_linhas = max(1, int(config.get("num_linhas", 4)))
    espaco_linhas = float(config.get("espaco_linhas", 13.0))
    cota_y = float(config.get("cota_y", 10.0))
    larg_estribo_menor = float(config.get("larg_estribo_menor", config.get("larg_estribo_maior", 15.0)))

    raio_dot = 1.15
    comp_trilho_bb = cota_y + max(0, num_linhas - 1) * espaco_linhas

    # ==========================================================================
    # 1. SÍMBOLOS DE CORTE B-B NA PLANTA (Topo e Base da laje - Visão para a Direita ►)
    # ==========================================================================
    px_corte_planta = (px_min + px_max) / 2.0

    draw.level = 241
    draw.color = 2  # Amarelo
    draw.style = 0

    larg_seta = 7.0
    alt_seta = 6.0
    alt_txt = 6.5
    larg_txt = 4.5
    comp_lin = 20.0

    def _desenhar_seta_solida_dir(x_base, y_c):
        """Desenha triângulo amarelo sólido com base vertical apontando para a DIREITA (►)."""
        x_ponta = x_base + alt_seta
        y_b1 = y_c - larg_seta / 2.0
        y_b2 = y_c + larg_seta / 2.0
        draw.Line(x_base, y_b1, x_base, y_b2)
        draw.Line(x_base, y_b1, x_ponta, y_c)
        draw.Line(x_base, y_b2, x_ponta, y_c)
        n_passos = int(alt_seta / 0.20)
        for i in range(1, n_passos):
            dx = i * 0.20
            x_curr = x_base + dx
            t = (alt_seta - dx) / alt_seta
            h_h = (larg_seta / 2.0) * t
            draw.Line(x_curr, y_c - h_h, x_curr, y_c + h_h)

    # 1.1 Símbolo Superior: Linha vertical saindo de box_y2 + [ B ] ao lado + [ ► ] na ponta
    y_lin_sup_fim = box_y2 + comp_lin
    draw.Line(px_corte_planta, box_y2, px_corte_planta, y_lin_sup_fim)
    y_c_tri_sup = y_lin_sup_fim - larg_seta / 2.0
    _desenhar_seta_solida_dir(px_corte_planta, y_c_tri_sup)
    y_txt_sup = box_y2 + (comp_lin - larg_seta - larg_txt) / 2.0
    draw.Text(px_corte_planta + alt_txt + 1.5, y_txt_sup, alt_txt, 90.0, "B")

    # 1.2 Símbolo Inferior: Linha vertical saindo de box_y1 + [ B ] ao lado + [ ► ] na ponta
    y_lin_inf_fim = box_y1 - comp_lin
    draw.Line(px_corte_planta, box_y1, px_corte_planta, y_lin_inf_fim)
    y_c_tri_inf = y_lin_inf_fim + larg_seta / 2.0
    _desenhar_seta_solida_dir(px_corte_planta, y_c_tri_inf)
    y_txt_inf = y_lin_inf_fim + larg_seta + (comp_lin - larg_seta - larg_txt) / 2.0
    draw.Text(px_corte_planta + alt_txt + 1.5, y_txt_inf, alt_txt, 90.0, "B")

    # ==========================================================================
    # 2. POSICIONAMENTO E GEOMETRIA DO CONCRETO NO CORTE B-B (ABAIXO DO CORTE A-A)
    # ==========================================================================
    y_corte_topo_aa = box_y1 - 45.0
    y_corte_base_aa = y_corte_topo_aa - hd
    y_col_inf_aa = y_corte_base_aa - 18.0

    # Posicionamento do CORTE B-B abaixo de CORTE A-A
    y_corte_topo_bb = y_col_inf_aa - 75.0
    y_corte_base_bb = y_corte_topo_bb - hd

    xc_corte = (px_min + px_max) / 2.0

    # Largura do pilar no corte B-B é a dimensão vertical (col_dy)
    pilar_bb_x1 = xc_corte - col_dy / 2.0
    pilar_bb_x2 = xc_corte + col_dy / 2.0

    # Extensão da laje para os dois lados acompanhando os trilhos verticais
    x_corte_bb_esq = pilar_bb_x1 - comp_trilho_bb - 24.0
    x_corte_bb_dir = pilar_bb_x2 + comp_trilho_bb + 24.0

    y_col_sup_bb = y_corte_topo_bb + 18.0
    y_col_inf_bb = y_corte_base_bb - 18.0

    def _linha_quebra_h(x1, x2, y, h_zig=6.5, w_zig=2.5):
        xm = (x1 + x2) / 2.0
        draw.Line(x1, y, xm - w_zig, y)
        draw.Line(xm - w_zig, y, xm - w_zig / 3.0, y + h_zig)
        draw.Line(xm - w_zig / 3.0, y + h_zig, xm + w_zig / 3.0, y - h_zig)
        draw.Line(xm + w_zig / 3.0, y - h_zig, xm + w_zig, y)
        draw.Line(xm + w_zig, y, x2, y)

    # Contorno de Concreto (Nível 241, Cor 3 Verde)
    draw.level = 241
    draw.color = 3  # Verde
    draw.style = 0

    # Laje Superior
    draw.Line(x_corte_bb_esq, y_corte_topo_bb, pilar_bb_x1, y_corte_topo_bb)
    draw.Line(pilar_bb_x2, y_corte_topo_bb, x_corte_bb_dir, y_corte_topo_bb)

    # Laje Inferior
    draw.Line(x_corte_bb_esq, y_corte_base_bb, pilar_bb_x1, y_corte_base_bb)
    draw.Line(pilar_bb_x2, y_corte_base_bb, x_corte_bb_dir, y_corte_base_bb)

    # Fechamentos laterais da laje
    draw.Line(x_corte_bb_esq, y_corte_base_bb, x_corte_bb_esq, y_corte_topo_bb)
    draw.Line(x_corte_bb_dir, y_corte_base_bb, x_corte_bb_dir, y_corte_topo_bb)

    # Projeção do Pilar Superior
    draw.Line(pilar_bb_x1, y_corte_topo_bb, pilar_bb_x1, y_col_sup_bb)
    draw.Line(pilar_bb_x2, y_corte_topo_bb, pilar_bb_x2, y_col_sup_bb)
    _linha_quebra_h(pilar_bb_x1, pilar_bb_x2, y_col_sup_bb)

    # Projeção do Pilar Inferior
    draw.Line(pilar_bb_x1, y_corte_base_bb, pilar_bb_x1, y_col_inf_bb)
    draw.Line(pilar_bb_x2, y_corte_base_bb, pilar_bb_x2, y_col_inf_bb)
    _linha_quebra_h(pilar_bb_x1, pilar_bb_x2, y_col_inf_bb)

    # ==========================================================================
    # 3. BARRAS LONGITUDINAIS CONTÍNUAS SUPERIOR E INFERIOR (Ciano)
    # ==========================================================================
    draw.level = 220
    draw.color = 4  # Ciano
    draw.style = 0

    cob = 2.0
    y_bar_top = y_corte_topo_bb - cob
    y_bar_bot = y_corte_base_bb + cob

    draw.Line(x_corte_bb_esq + 1.5, y_bar_top, x_corte_bb_dir - 1.5, y_bar_top)
    draw.Line(x_corte_bb_esq + 1.5, y_bar_bot, x_corte_bb_dir - 1.5, y_bar_bot)

    # ==========================================================================
    # 4. ESTRIBOS DE PUNÇÃO NO CORTE B-B
    # ==========================================================================
    y_dot_top = y_bar_top - raio_dot
    y_dot_bot = y_bar_bot + raio_dot
    y_st_top = y_dot_top + raio_dot
    y_st_bot = y_dot_bot - raio_dot

    def _desenhar_dot_par(xd):
        draw.level = 220
        draw.color = 1  # Vermelho
        draw.style = 0
        draw.Circle(xd, y_dot_top, raio_dot)
        draw.Circle(xd, y_dot_bot, raio_dot)

    def _desenhar_estribo_corte(x_left, x_right, cor_st=2):
        draw.level = 220
        draw.color = cor_st
        draw.style = 0
        x_st_l = x_left - raio_dot
        x_st_r = x_right + raio_dot
        draw.Line(x_st_l, y_st_bot, x_st_r, y_st_bot)
        draw.Line(x_st_r, y_st_bot, x_st_r, y_st_top)
        draw.Line(x_st_r, y_st_top, x_st_l, y_st_top)
        draw.Line(x_st_l, y_st_top, x_st_l, y_st_bot)
        # Gancho a -45° no canto superior esquerdo
        draw.Line(x_st_l + 1.2, y_st_top, x_st_l + 3.4, y_st_top - 2.2)
        draw.Line(x_st_l, y_st_top - 1.2, x_st_l + 2.2, y_st_top - 3.4)
        _desenhar_dot_par(x_left)
        _desenhar_dot_par(x_right)

    def _desenhar_bastao(xf):
        _desenhar_dot_par(xf)
        draw.level = 220
        draw.color = 4  # Ciano
        draw.style = 0
        shank_w = raio_dot
        draw.Line(xf - shank_w, y_dot_bot, xf - shank_w, y_dot_top)
        draw.Line(xf + shank_w, y_dot_bot, xf + shank_w, y_dot_top)

    # 4.1 ESTRIBOS DENTRO DO PILAR: DE FRENTE (Estribo fechado face menor)
    x_st_bb_l = xc_corte - larg_estribo_menor / 2.0
    x_st_bb_r = xc_corte + larg_estribo_menor / 2.0
    _desenhar_estribo_corte(x_st_bb_l, x_st_bb_r, cor_st=2)

    # 4.2 ESTRIBOS FORA DO PILAR: DE LADO (Formato bastão nas colunas)
    pts_bb_esq = [pilar_bb_x1 - (cota_y + k * espaco_linhas) for k in range(num_linhas)]
    pts_bb_dir = [pilar_bb_x2 + (cota_y + k * espaco_linhas) for k in range(num_linhas)]

    for xf in pts_bb_esq:
        _desenhar_bastao(xf)

    for xf in pts_bb_dir:
        _desenhar_bastao(xf)

    # Bolinhas ao longo da laje além dos trilhos
    x_step = espaco_linhas if espaco_linhas > 0 else 13.0
    x_ult_esq = min(pts_bb_esq) if pts_bb_esq else pilar_bb_x1
    x_curr = x_ult_esq - x_step
    while x_curr >= x_corte_bb_esq + 3.5:
        _desenhar_dot_par(x_curr)
        x_curr -= x_step

    x_ult_dir = max(pts_bb_dir) if pts_bb_dir else pilar_bb_x2
    x_curr = x_ult_dir + x_step
    while x_curr <= x_corte_bb_dir - 3.5:
        _desenhar_dot_par(x_curr)
        x_curr += x_step

    # ==========================================================================
    # 5. CHAMADAS DE TEXTO: FERRAGEM NEGATIVA & FERRAGEM POSITIVA
    # ==========================================================================
    draw.level = 241
    draw.color = 3  # Verde
    draw.style = 0

    # Chamada Superior (apontando para a barra ciano superior, prateleira voltada para a esquerda)
    x_pt_sup = x_corte_bb_esq + 5.0
    y_pt_sup = y_bar_top
    x_knee_sup = x_pt_sup - 7.0
    y_knee_sup = y_corte_topo_bb + 8.0
    x_shelf_sup = x_knee_sup - 52.0
    draw.Line(x_pt_sup, y_pt_sup, x_knee_sup, y_knee_sup)
    draw.Line(x_shelf_sup, y_knee_sup, x_knee_sup, y_knee_sup)
    # Seta na ponta da chamada superior
    draw.Line(x_pt_sup, y_pt_sup, x_pt_sup - 2.8, y_pt_sup + 1.4)
    draw.Line(x_pt_sup, y_pt_sup, x_pt_sup - 1.4, y_pt_sup + 2.8)
    draw.Text(x_shelf_sup + 1.0, y_knee_sup + 1.2, 4.2, 0.0, "FERRAGEM NEGATIVA")

    # Chamada Inferior (apontando para a barra ciano inferior, prateleira voltada para a esquerda)
    x_pt_inf = x_corte_bb_esq + 5.0
    y_pt_inf = y_bar_bot
    x_knee_inf = x_pt_inf - 7.0
    y_knee_inf = y_corte_base_bb - 10.0
    x_shelf_inf = x_knee_inf - 52.0
    draw.Line(x_pt_inf, y_pt_inf, x_knee_inf, y_knee_inf)
    draw.Line(x_shelf_inf, y_knee_inf, x_knee_inf, y_knee_inf)
    # Seta na ponta da chamada inferior
    draw.Line(x_pt_inf, y_pt_inf, x_pt_inf - 2.8, y_pt_inf - 1.4)
    draw.Line(x_pt_inf, y_pt_inf, x_pt_inf - 1.4, y_pt_inf - 2.8)
    draw.Text(x_shelf_inf + 1.0, y_knee_inf + 1.2, 4.2, 0.0, "FERRAGEM POSITIVA")

    # ==========================================================================
    # 6. COTA VERTICAL DA ESPESSURA HD DA LAJE (Direita)
    # ==========================================================================
    x_cota_hd = x_corte_bb_dir + 10.0
    draw.Line(x_corte_bb_dir + 2.0, y_corte_base_bb, x_cota_hd + 3.5, y_corte_base_bb)
    draw.Line(x_corte_bb_dir + 2.0, y_corte_topo_bb, x_cota_hd + 3.5, y_corte_topo_bb)
    draw.Line(x_cota_hd, y_corte_base_bb - 3.5, x_cota_hd, y_corte_topo_bb + 3.5)
    draw.Line(x_cota_hd - 1.2, y_corte_base_bb - 1.2, x_cota_hd + 1.2, y_corte_base_bb + 1.2)
    draw.Line(x_cota_hd - 1.2, y_corte_topo_bb - 1.2, x_cota_hd + 1.2, y_corte_topo_bb + 1.2)
    txt_hd = f"{int(hd) if hd.is_integer() else hd}"
    larg_hd = len(txt_hd) * 3.5
    draw.Text(x_cota_hd - 1.8, (y_corte_base_bb + y_corte_topo_bb) / 2.0 - larg_hd / 2.0, 4.8, 90.0, txt_hd)

    # ==========================================================================
    # 7. TÍTULO CORTE B-B
    # ==========================================================================
    draw.level = 245
    draw.color = 2  # Amarelo
    draw.Text(xc_corte - 20.0, y_col_inf_bb - 16.0, 8.5, 0.0, "CORTE  B-B")


# ==============================================================================
# DETALHE ESQUEMÁTICO DOS ESTRIBOS E REFORÇO RADIAL (COBRINHA)
# ==============================================================================

def desenhar_detalhe_estribo(dwg, x_alvo, y_alvo, pilar, config):
    """
    Desenha os ferros esquemáticos e chamadas conforme novo padrão:
    1. Estribo da Face Menor (fechado explodido, ex: 2x3 N1 ø 10 C/12 C=86);
    2. Estribo da Face Maior (fechado explodido, ex: 4x3 N2 ø 10 C/12 C=88).
    """
    draw = dwg.draw

    larg_area = float(pilar.get("larg_area", 180.0))
    alt_area = float(pilar.get("alt_area", 140.0))
    hd = float(config.get("hd", pilar.get("hd", 26.0)))

    box_x1 = x_alvo - larg_area / 2.0
    box_y1 = y_alvo - alt_area / 2.0

    larg_st_maior = float(config.get("larg_estribo_maior", config.get("larg_estribo", 15.0)))
    alt_st_maior = float(config.get("alt_estribo_maior", config.get("alt_estribo", max(10.0, hd - 5.0))))
    larg_st_menor = float(config.get("larg_estribo_menor", config.get("larg_estribo", 15.0)))
    alt_st_menor = float(config.get("alt_estribo_menor", config.get("alt_estribo", max(10.0, hd - 5.0))))

    bitola = float(config.get("bitola_estribo", 8.0))
    pos_str = str(config.get("pos_estribo", "1")).strip().upper()
    digits = ''.join(filter(str.isdigit, pos_str))
    base_pos = int(digits) if digits else 1

    num_colunas = max(1, int(config.get("num_colunas", config.get("num_maior", 2))))
    num_linhas = max(1, int(config.get("num_linhas", 3)))
    num_menor = max(1, int(config.get("num_menor", 3)))
    espaco_linhas = float(config.get("espaco_linhas", 13.0))
    espaco_menor = float(config.get("espaco_menor", 13.0))
    tem_inclinado = bool(config.get("tem_inclinado", True))
    cota_inclinado = float(config.get("cota_inclinado", 10.0))

    # Ponto base inicial no canto inferior esquerdo da área delimitada (organização horizontal paralela)
    y_base = box_y1 + 38.0
    x1 = box_x1 + 38.0
    y1 = y_base

    # Espaçamento horizontal entre os ferros esquemáticos
    espaco_entre_estribos = max(larg_st_menor, larg_st_maior, 15.0) + 55.0
    x2 = x1 + espaco_entre_estribos
    y2 = y_base

    # Geometria do 3º ferro ("cobrinha" / reforço radial das quinas):
    # Totalmente baseada nos valores e dimensões dos estribos da horizontal (Face Maior):
    # - Altura das pernas verticais = altura do estribo horizontal (alt_st_maior)
    # - Espaço horizontal entre as pernas = espaçamento entre linhas da horizontal (espaco_linhas)
    # - Quantidade de pernas verticais = número de linhas da horizontal (num_linhas)
    # - Pontas inicial e final = cota_inclinado (ou cota_y da horizontal)
    ponta_cobr = cota_inclinado if cota_inclinado > 0 else float(config.get("cota_y", 10.0))
    passo_cobr = espaco_linhas if espaco_linhas > 0 else 13.0
    h_onda_cobr = alt_st_maior if alt_st_maior > 0 else 21.0
    n_ondas_cobr = num_linhas

    pts_cobrinha = [(0.0, 0.0)]
    xc_c = ponta_cobr
    yc_c = 0.0
    pts_cobrinha.append((xc_c, yc_c))
    for k in range(n_ondas_cobr):
        if (k % 2) == 0:
            yc_c = h_onda_cobr
            pts_cobrinha.append((xc_c, yc_c))
            if k < n_ondas_cobr - 1:
                xc_c += passo_cobr
                pts_cobrinha.append((xc_c, yc_c))
        else:
            yc_c = 0.0
            pts_cobrinha.append((xc_c, yc_c))
            if k < n_ondas_cobr - 1:
                xc_c += passo_cobr
                pts_cobrinha.append((xc_c, yc_c))
    xc_c += ponta_cobr
    pts_cobrinha.append((xc_c, yc_c))
    comp_x_cobr = xc_c

    # Posição da cobrinha (paralela aos outros dois estribos)
    x3 = x2 + espaco_entre_estribos
    y3 = y_base

    alt_fonte_plot = 0.10  # Altura reduzida da fonte de identificação (cm de plotagem)

    rebar_principal = None
    usou_smart = False

    try:
        # ----------------------------------------------------------------------
        # 1. ESTRIBO DA FACE MENOR (N1)
        # ----------------------------------------------------------------------
        r1 = TQSDwg.SmartRebar(dwg)
        r1.type = TQSDwg.ICPSTR
        r1.mark = base_pos
        r1.multiplier = 2  # 2 faces menores
        r1.quantity = num_menor
        r1.diameter = bitola
        r1.spacing = espaco_menor
        r1.cover = 0.0
        r1.stirrupType = TQSDwg.ICPEFC  # Fechado com ponta triangular
        r1.stirrupLegs = TQSDwg.ICPNR2
        r1.stirrupSectionWidth = larg_st_menor
        r1.stirrupSectionHeight = alt_st_menor
        for attr in ('textHeigth', 'textHeight', 'distributionTextHeigth'):
            try:
                setattr(r1, attr, alt_fonte_plot)
            except Exception:
                pass
        try:
            r1.bendBendLengthMode = TQSDwg.ICPDOBSMS
        except Exception:
            pass
        r1.RebarLine(x1, y1, 0.0, 1.0, 1, 1, 1, 1, 220, -1, -1)
        r1.leaderLine = 0
        r1.RebarTextDisplaySelection(1, 1, 1, 1, 1, TQSDwg.ICPCENTR_CENTRAD, TQSDwg.ICPQUEBR_SALTODECD)
        try:
            r1.RebarTextDisplayPosition(x1 + larg_st_menor / 2.0, y1 - 15.0, alt_fonte_plot, 0.0, 0, TQSDwg.ICPCENTR_CENTRAD, TQSDwg.ICPQUEBR_SALTODECD)
        except Exception:
            pass
        rebar_principal = r1

        # ----------------------------------------------------------------------
        # 2. ESTRIBO DA FACE MAIOR (N2) - paralelo horizontalmente (mesmo Y)
        # ----------------------------------------------------------------------
        r2 = TQSDwg.SmartRebar(dwg)
        r2.type = TQSDwg.ICPSTR
        r2.mark = base_pos + 1
        r2.multiplier = 2 * num_colunas  # 2 faces maiores * número de colunas
        r2.quantity = num_linhas
        r2.diameter = bitola
        r2.spacing = espaco_linhas
        r2.cover = 0.0
        r2.stirrupType = TQSDwg.ICPEFC  # Fechado com ponta triangular
        r2.stirrupLegs = TQSDwg.ICPNR2
        r2.stirrupSectionWidth = larg_st_maior
        r2.stirrupSectionHeight = alt_st_maior
        for attr in ('textHeigth', 'textHeight', 'distributionTextHeigth'):
            try:
                setattr(r2, attr, alt_fonte_plot)
            except Exception:
                pass
        try:
            r2.bendBendLengthMode = TQSDwg.ICPDOBSMS
        except Exception:
            pass
        r2.RebarLine(x2, y2, 0.0, 1.0, 1, 1, 1, 1, 220, -1, -1)
        r2.leaderLine = 0
        r2.RebarTextDisplaySelection(1, 1, 1, 1, 1, TQSDwg.ICPCENTR_CENTRAD, TQSDwg.ICPQUEBR_SALTODECD)
        try:
            r2.RebarTextDisplayPosition(x2 + larg_st_maior / 2.0, y2 - 15.0, alt_fonte_plot, 0.0, 0, TQSDwg.ICPCENTR_CENTRAD, TQSDwg.ICPQUEBR_SALTODECD)
        except Exception:
            pass
        rebar_principal = r2

        if tem_inclinado:
            # ------------------------------------------------------------------
            # 3. FERRO DIAGONAL / COBRINHA (N3) - paralelo horizontalmente (mesmo Y)
            # ------------------------------------------------------------------
            r3 = TQSDwg.SmartRebar(dwg)
            r3.type = TQSDwg.ICPFGN  # Ferro genérico
            r3.mark = base_pos + 2
            r3.multiplier = 1        # Representação direta: 4 barras P3 (1 para cada uma das 4 diagonais)
            r3.quantity = 4          # 4 diagonais no total
            r3.diameter = bitola
            r3.spacing = 0.0
            r3.cover = 0.0
            for attr in ('textHeigth', 'textHeight', 'distributionTextHeigth'):
                try:
                    setattr(r3, attr, alt_fonte_plot)
                except Exception:
                    pass
            try:
                r3.bendBendLengthMode = TQSDwg.ICPDOBSMS
            except Exception:
                pass
            for px, py in pts_cobrinha:
                r3.GenRebarPoint(px, py, 0.0, 0, 1, -1)
            r3.RebarLine(x3, y3, 0.0, 1.0, 1, 1, 1, 1, 220, -1, -1)
            r3.leaderLine = 0
            r3.RebarTextDisplaySelection(1, 1, 1, 0, 1, TQSDwg.ICPCENTR_CENTRAD, TQSDwg.ICPQUEBR_SALTODECD)
            try:
                r3.RebarTextDisplayPosition(x3 + comp_x_cobr / 2.0, y3 - 15.0, alt_fonte_plot, 0.0, 0, TQSDwg.ICPCENTR_CENTRAD, TQSDwg.ICPQUEBR_SALTODECD)
            except Exception:
                pass

        usou_smart = True
    except Exception as e:
        usou_smart = False
        try:
            TQSUtil.writef("Aviso ao criar SmartRebar dos ferros: %s" % str(e))
        except Exception:
            pass

    # --------------------------------------------------------------------------
    # FALLBACK GRÁFICO (caso SmartRebar não esteja disponível)
    # --------------------------------------------------------------------------
    if not usou_smart:
        def _desenhar_estribo_fechado_grafico(x_ins, y_ins, larg_e, alt_e, mult, qtd, pos_n, espac):
            draw.level = 220
            draw.color = 4  # Ciano
            draw.style = 0
            # Retângulo base
            draw.Line(x_ins, y_ins, x_ins + larg_e, y_ins)
            draw.Line(x_ins + larg_e, y_ins, x_ins + larg_e, y_ins + alt_e)
            draw.Line(x_ins + larg_e, y_ins + alt_e, x_ins, y_ins + alt_e)
            draw.Line(x_ins, y_ins + alt_e, x_ins, y_ins)
            # Gancho triangular no topo
            xm = x_ins + larg_e * 0.45
            draw.Line(x_ins + larg_e, y_ins + alt_e, xm, y_ins + alt_e + 4.0)
            draw.Line(xm, y_ins + alt_e + 4.0, xm - 1.8, y_ins + alt_e + 1.2)

            # Cotas de largura (embaixo) e altura (na esquerda) com fonte menor
            draw.level = 241
            draw.color = 3  # Verde
            txt_l = f"{int(larg_e) if larg_e.is_integer() else larg_e}"
            draw.Text(x_ins + (larg_e / 2.0) - (len(txt_l) * 1.0), y_ins - 4.5, 3.2, 0.0, txt_l)
            txt_a = f"{int(alt_e) if alt_e.is_integer() else alt_e}"
            draw.Text(x_ins - 4.2, y_ins + (alt_e / 2.0) - (len(txt_a) * 1.0), 3.2, 90.0, txt_a)

            # Texto de identificação (em 2 linhas compactas com fonte menor)
            draw.level = 220
            draw.color = 2  # Amarelo
            comp_e = int(round(2.0 * (larg_e + alt_e) + 15.0))
            bit_txt = f"{int(bitola) if bitola.is_integer() else bitola}"
            t1 = f"{mult}x{qtd} N{pos_n} ø {bit_txt}"
            t2 = f"C/{int(espac)} C={comp_e}"
            draw.Text(x_ins - 2.0, y_ins - 9.0, 3.5, 0.0, t1)
            draw.Text(x_ins - 2.0, y_ins - 14.0, 3.5, 0.0, t2)

        # 1. Estribo menor
        _desenhar_estribo_fechado_grafico(x1, y1, larg_st_menor, alt_st_menor, 2, num_menor, base_pos, espaco_menor)

        # 2. Estribo maior (paralelo horizontalmente, mesmo Y)
        _desenhar_estribo_fechado_grafico(x2, y2, larg_st_maior, alt_st_maior, 2 * num_colunas, num_linhas, base_pos + 1, espaco_linhas)

        # 3. Ferro diagonal / cobrinha (paralelo horizontalmente, mesmo Y)
        if tem_inclinado:
            def _desenhar_cobrinha_grafico(x_ins, y_ins, d_ponta, h_o, p_passo, n_o, mult, qtd, pos_n):
                draw.level = 220
                draw.color = 4  # Ciano
                draw.style = 0
                r_b = 2.0

                # 1. Traçado dos segmentos retos com arcos de curvatura nas quinas
                # Segmento horizontal inicial (inferior)
                draw.Line(x_ins, y_ins, x_ins + d_ponta - r_b, y_ins)

                for k in range(n_o):
                    xk = x_ins + d_ponta + k * p_passo
                    if (k % 2) == 0:
                        # Arco inferior esquerdo (vira para cima)
                        draw.Arc(xk - r_b, y_ins + r_b, r_b, 270.0, 360.0)
                        # Trecho vertical (sobe)
                        draw.Line(xk, y_ins + r_b, xk, y_ins + h_o - r_b)
                        if k < n_o - 1:
                            # Arco superior esquerdo (vira para a direita)
                            draw.Arc(xk + r_b, y_ins + h_o - r_b, r_b, 90.0, 180.0)
                            # Trecho horizontal superior
                            draw.Line(xk + r_b, y_ins + h_o, xk + p_passo - r_b, y_ins + h_o)
                        else:
                            # Arco superior final (vira para a direita)
                            draw.Arc(xk + r_b, y_ins + h_o - r_b, r_b, 90.0, 180.0)
                            # Ponta horizontal final (superior)
                            draw.Line(xk + r_b, y_ins + h_o, xk + d_ponta, y_ins + h_o)
                    else:
                        # Arco superior direito (vira para baixo)
                        draw.Arc(xk - r_b, y_ins + h_o - r_b, r_b, 0.0, 90.0)
                        # Trecho vertical (desce)
                        draw.Line(xk, y_ins + h_o - r_b, xk, y_ins + r_b)
                        if k < n_o - 1:
                            # Arco inferior direito (vira para a direita)
                            draw.Arc(xk + r_b, y_ins + r_b, r_b, 180.0, 270.0)
                            # Trecho horizontal inferior
                            draw.Line(xk + r_b, y_ins, xk + p_passo - r_b, y_ins)
                        else:
                            # Arco inferior final (vira para a direita)
                            draw.Arc(xk + r_b, y_ins + r_b, r_b, 180.0, 270.0)
                            # Ponta horizontal final (inferior)
                            draw.Line(xk + r_b, y_ins, xk + d_ponta, y_ins)

                # 2. Cotas das dobras conforme imagem de referência (Nível 241, Verde)
                draw.level = 241
                draw.color = 3  # Verde
                txt_pt = f"{int(d_ponta) if d_ponta.is_integer() else d_ponta}"
                # Cota da ponta inicial
                draw.Text(x_ins + d_ponta / 2.0 - len(txt_pt) * 1.0, y_ins - 4.5, 3.2, 0.0, txt_pt)
                # Cotas verticais
                txt_h = f"{int(h_o) if h_o.is_integer() else h_o}"
                for k in range(n_o):
                    xk = x_ins + d_ponta + k * p_passo
                    draw.Text(xk - 4.5, y_ins + h_o / 2.0 - len(txt_h) * 1.0, 3.2, 90.0, txt_h)
                # Cotas horizontais intermediárias
                txt_p = f"{int(p_passo) if p_passo.is_integer() else p_passo}"
                for k in range(n_o - 1):
                    xk_mid = x_ins + d_ponta + k * p_passo + p_passo / 2.0
                    if (k % 2) == 0:
                        draw.Text(xk_mid - len(txt_p) * 1.0, y_ins + h_o + 2.0, 3.2, 0.0, txt_p)
                    else:
                        draw.Text(xk_mid - len(txt_p) * 1.0, y_ins - 4.5, 3.2, 0.0, txt_p)
                # Cota da ponta final
                x_fim_pt = x_ins + d_ponta + (n_o - 1) * p_passo + d_ponta / 2.0
                y_fim_pt = y_ins + h_o + 2.0 if ((n_o - 1) % 2 == 0) else y_ins - 4.5
                draw.Text(x_fim_pt - len(txt_pt) * 1.0, y_fim_pt, 3.2, 0.0, txt_pt)

                # 3. Texto de identificação abaixo do ferro
                draw.level = 220
                draw.color = 2  # Amarelo
                comp_tot = int(round(2.0 * d_ponta + n_o * h_o + (n_o - 1) * p_passo))
                bit_txt = f"{int(bitola) if bitola.is_integer() else bitola}"
                if mult > 1 and qtd > 1:
                    t1 = f"{mult}x{qtd} N{pos_n} ø {bit_txt}"
                else:
                    total_pecas = mult * qtd
                    t1 = f"{total_pecas} N{pos_n} ø {bit_txt}"
                t2 = f"C={comp_tot}"
                xc_tot = x_ins + (2.0 * d_ponta + (n_o - 1) * p_passo) / 2.0
                draw.Text(xc_tot - len(t1) * 1.0, y_ins - 9.0, 3.5, 0.0, t1)
                draw.Text(xc_tot - len(t2) * 1.0, y_ins - 14.0, 3.5, 0.0, t2)

            _desenhar_cobrinha_grafico(x3, y3, ponta_cobr, h_onda_cobr, passo_cobr, n_ondas_cobr, 1, 4, base_pos + 2)

    return rebar_principal


# ==============================================================================
# DESENHO FIDEDIGNO: QUADRADO DA ÁREA + PILAR + FERRO DE DENTRO + PUNÇÃO
# ==============================================================================

def colar_desenho_fidedigno(dwg, x_alvo, y_alvo, pilar, config):
    """
    Desenha exatamente:
    1. O pilar e o ferro de dentro na sua posição relativa exata;
    2. O quadrado da área em volta (Nível 207, Por nível, Estilo Por nível);
    3. Rótulo HD e título PUNÇÃO - ...;
    4. A Armadura de Punção completa (trilhos, conectores/pinos e cotas verdes).
    """
    draw = dwg.draw

    larg_area = float(pilar.get("larg_area", 180.0))
    alt_area = float(pilar.get("alt_area", 140.0))
    nome_p = config.get("nome_pilar", pilar.get("nome", "P10 = P13"))
    hd = float(config.get("hd", pilar.get("hd", 26.0)))

    # Coordenadas do quadrado delimitador (exatamente o tamanho da janela que o usuário abriu)
    box_x1 = x_alvo - larg_area / 2.0
    box_x2 = x_alvo + larg_area / 2.0
    box_y1 = y_alvo - alt_area / 2.0
    box_y2 = y_alvo + alt_area / 2.0

    hw = larg_area / 2.0
    hh = alt_area / 2.0
    tol = 2.0

    # 1. PILAR E FERRO DE DENTRO (LINHAS CAPTURADAS INTERNAS)
    for l in pilar.get("linhas", []):
        try:
            # Nunca desenha linhas de cubeta (208) nem linhas residuais da borda da janela
            if l.get("nivel") == 208:
                continue
            dx1, dy1 = l["dx1"], l["dy1"]
            dx2, dy2 = l["dx2"], l["dy2"]
            if (abs(abs(dx1) - hw) < tol and abs(abs(dx2) - hw) < tol) or \
               (abs(abs(dy1) - hh) < tol and abs(abs(dy2) - hh) < tol):
                continue

            draw.level = l["nivel"]
            draw.color = l["cor"]
            draw.style = l["estilo"]
            draw.Line(x_alvo + dx1, y_alvo + dy1, x_alvo + dx2, y_alvo + dy2)
        except Exception:
            pass

    # 2. ARCOS
    for a in pilar.get("arcos", []):
        try:
            draw.level = a["nivel"]
            draw.color = a["cor"]
            draw.style = a["estilo"]
            draw.Arc(x_alvo + a["dxc"], y_alvo + a["dyc"], a["raio"], a["aini"], a["afim"])
        except Exception:
            pass

    # 3. CÍRCULOS
    for c in pilar.get("circulos", []):
        try:
            draw.level = c["nivel"]
            draw.color = c["cor"]
            draw.style = c["estilo"]
            draw.Circle(x_alvo + c["dxc"], y_alvo + c["dyc"], c["raio"])
        except Exception:
            pass

    # 4. TEXTOS CAPTURADOS
    for t in pilar.get("textos", []):
        try:
            draw.level = t["nivel"]
            draw.color = t["cor"]
            draw.Text(x_alvo + t["dx"], y_alvo + t["dy"], t["h"], t["ang"], t["txt"])
        except Exception:
            pass

    # 5. O RETÂNGULO DA ÁREA (Nível 207, Cor: Por nível, Estilo: Por nível)
    draw.level = 207
    draw.color = -1  # Por nível
    draw.style = -1  # -1: Por nível
    draw.Line(box_x1, box_y1, box_x2, box_y1)
    draw.Line(box_x2, box_y1, box_x2, box_y2)
    draw.Line(box_x2, box_y2, box_x1, box_y2)
    draw.Line(box_x1, box_y2, box_x1, box_y1)

    # Rótulo HC no canto inferior direito interno da área
    draw.level = 241
    draw.color = 3  # Verde
    txt_hc = f"HC={int(hd) if hd.is_integer() else hd}"
    draw.Text(box_x2 - 55.0, box_y1 + 8.0, 11.0, 0.0, txt_hc)

    # Título no topo
    draw.level = 245
    draw.color = 4  # Ciano
    draw.Text(box_x1 + 10.0, box_y2 - 18.0, 14.0, 0.0, f"PUNÇÃO - {nome_p}")

    # 6. ARMADURA DE PUNÇÃO (TRILHOS, PINOS E COTAGEM EM VOLTA DO PILAR)
    try:
        desenhar_armadura_puncao(dwg, x_alvo, y_alvo, pilar, config)
    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass

    # 7. DETALHE ESQUEMÁTICO DOS ESTRIBOS E CHAMADA (SmartRebar conectado)
    rebar_obj = None
    if config.get("desenhar_detalhe_estribo", True):
        try:
            rebar_obj = desenhar_detalhe_estribo(dwg, x_alvo, y_alvo, pilar, config)
        except Exception as e:
            try:
                TQSUtil.ShowException(e)
            except Exception:
                pass

    # 8. CORTE ESQUEMÁTICO NA PARTE DE BAIXO E SÍMBOLOS DE CORTE A-A
    try:
        desenhar_corte_aa(dwg, x_alvo, y_alvo, pilar, config, rebar_estribo=rebar_obj)
    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass

    # 9. CORTE ESQUEMÁTICO B-B (ABAIXO DO CORTE A-A) E SÍMBOLOS DE CORTE B-B
    try:
        desenhar_corte_bb(dwg, x_alvo, y_alvo, pilar, config, rebar_estribo=rebar_obj)
    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass



# ==============================================================================
# COMANDO: COPIAR PILAR DA PLANTA
# ==============================================================================

def cmd_copiar_pilar(eag, tqsjan):
    """
    Abre uma janela elástica na tela sobre o pilar.
    O retângulo aberto define a área do quadrado e capta o pilar e ferro de dentro.
    """
    try:
        pilar = capturar_janela_com_area(eag, tqsjan)
        if pilar and pilar.get("total_elementos", 0) > 0:
            salvar_geometria_em_memoria(pilar)
            try:
                msg = f"Sucesso! {pilar['total_elementos']} elementos ({pilar['nome']}) capturados com area de {int(pilar['larg_area'])}x{int(pilar['alt_area'])} cm!"
                eag.msg.Print(msg)
            except Exception:
                pass
        else:
            try:
                eag.msg.Print("Nenhum elemento identificado dentro da janela aberta.")
            except Exception:
                pass
    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass


# ==============================================================================
# COMANDO: TRANSPORTAR / COLAR PILAR
# ==============================================================================

def meucmd(eag, tqsjan):
    """
    1. Se não tiver pilar copiado, pede para abrir a janela agora.
    2. Abre a tela HTA mostrando o pilar e a área selecionados.
    3. Ao clicar em 'Colar', pede o clique na tela e desenha fidedigno:
       - O quadrado da área em volta com HD=...;
       - O pilar e o ferro de dentro;
       - O título PUNÇÃO - ...
    """
    try:
        dwg = tqsjan.dwg
        pilar = carregar_geometria_em_memoria()

        # Se não há pilar em memória, abre a janela agora
        if not pilar or pilar.get("total_elementos", 0) == 0:
            try:
                eag.msg.Print("Nenhum pilar em memoria. Abra a janela sobre o pilar na planta primeiro:")
            except Exception:
                pass

            pilar = capturar_janela_com_area(eag, tqsjan)
            if not pilar or pilar.get("total_elementos", 0) == 0:
                try:
                    eag.msg.Print("Operacao cancelada. Nenhum elemento capturado.")
                except Exception:
                    pass
                return

            salvar_geometria_em_memoria(pilar)

        # 1. Abre a tela HTA mostrando qual pilar e área foram capturados
        config = mostrar_tela_confirmacao(pilar)
        if not config:
            return

        acao = config.get("acao", "colar")

        # Se o usuário escolheu abrir uma nova janela
        if acao == "recopiar":
            pilar = capturar_janela_com_area(eag, tqsjan)
            if not pilar or pilar.get("total_elementos", 0) == 0:
                return

            salvar_geometria_em_memoria(pilar)
            config = mostrar_tela_confirmacao(pilar)
            if not config or config.get("acao") != "colar":
                return

        elif acao != "colar":
            return

        # 2. Pede o ponto para colar
        nome_p = config.get("nome_pilar", pilar.get("nome", "Pilar"))
        prompt_colar = f"Clique no ponto onde deseja COLAR o {nome_p} com o quadrado da area e o ferro de dentro [Esc para sair]:"
        icod, xc, yc = eag.locate.GetPoint(tqsjan, prompt_colar)
        if icod != 1:
            return

        # 3. Desenha fidedigno: o quadrado da área em volta + pilar + ferro de dentro
        colar_desenho_fidedigno(dwg, xc, yc, pilar, config)
        tqsjan.Regen()

        try:
            eag.msg.Print(f"Pronto! {nome_p} com o quadrado da area e o ferro de dentro colados com sucesso!")
        except Exception:
            pass

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass
    finally:
        try:
            tqsjan.Regen()
        except Exception:
            pass


if __name__ == "__main__":
    pass
