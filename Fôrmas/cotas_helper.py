# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - COTAS HELPER (TQS EAG)
================================================================================
Modulo utilitario para cotagem automatica e inteligente de plantas de formas
e elementos estruturais de concreto armado no ambiente TQS EAG.

Principais Recursos:
  - Padrao de cotagem em 3 camadas (Parciais/Faces, Eixos/Pilares e Total)
  - Extracao automatica da geometria da planta de formas (Nivel 1, 2, 4, 201)
  - Deteccao de cotas ja existentes (IPOCOT / Textos) para evitar duplicidade
  - Completamento inteligente de cadeias internas existentes (ex: espessuras de
    vigas de borda e vaos de balanco/sacada)
  - Prevencao de sobreposicoes e organizacao automatica de textos de pilares,
    vigas e lajes (incluindo linha de chamada com seta DimNote quando necessario)
================================================================================
"""

import math
from TQS import TQSUtil, TQSDwg

try:
    TQSUtil.LoadDll("IPOCOT.DLL")
except Exception:
    pass


def _garantir_ipocot_carregado():
    """Garante que IPOCOT.DLL esteja carregada para que dwg.iterator leia objetos IPOCOT."""
    try:
        TQSUtil.LoadDll("IPOCOT.DLL")
    except Exception:
        pass


def _normalizar_angulo(ang):
    a = ang % 360.0
    if a < 0:
        a += 360.0
    if abs(a - 0.0) < 5.0 or abs(a - 360.0) < 5.0 or abs(a - 180.0) < 5.0:
        return 0.0
    if abs(a - 90.0) < 5.0 or abs(a - 270.0) < 5.0:
        return 90.0
    return round(a, 2)


def _bbox_texto(x1, y1, h, ang, texto_str):
    """
    Calcula o bounding box (xmin, ymin, xmax, ymax) de um texto no TQS.
    No TQS, cada caractere ocupa ~1.0 * h de largura na fonte padrao.
    """
    comp = len(texto_str) * h * 1.0
    a = _normalizar_angulo(ang)
    if a == 90.0:
        return (x1 - h * 1.15, y1, x1 + h * 0.25, y1 + comp)
    else:
        return (x1, y1 - h * 0.25, x1 + comp, y1 + h * 1.15)


def _boxes_colidem(b1, b2, margem=2.0):
    """Verifica se dois bounding boxes (xmin, ymin, xmax, ymax) se sobrepoem com margem."""
    return not (
        b1[2] + margem < b2[0] or
        b1[0] - margem > b2[2] or
        b1[3] + margem < b2[1] or
        b1[1] - margem > b2[3]
    )


def configurar_estilo_cotas(
    dwg,
    altura_texto=0.20,
    bloco="TICK",
    nivel=216,
    extensao_linha=0.25,
    extensao_chamada=0.25,
    folga_chamada=0.25,
    arredondar_5=False
):
    """
    Define as variaveis globais de aparencia de cotagem no objeto dwg.dim do TQS.
    Por padrao utiliza o estilo nativo de plantas de formas do TQS:
      - altura_texto = 0.20 (10cm na escala 1:50)
      - bloco = 'TICK'
      - nivel = 216 (textos/pontos de cota em 216, linhas de cota/chamada em 221)
    """
    dwg.dim.dimblk = str(bloco)
    dwg.dim.dimtxt = float(altura_texto)
    dwg.dim.dimdle = float(extensao_linha)
    dwg.dim.dimexe = float(extensao_chamada)
    dwg.dim.dimexo = float(folga_chamada)
    dwg.dim.idmniv = int(nivel)
    dwg.dim.idmnic = 221
    dwg.dim.idmnil = 221
    dwg.dim.idmnib = 221
    dwg.dim.idmar5 = 1 if arredondar_5 else 0


def filtrar_e_ordenar_pontos(lista_pontos, tolerancia=0.5):
    """
    Remove pontos repetidos ou excessivamente proximos (menores que a tolerancia)
    e retorna a lista ordenada de forma crescente.
    """
    if not lista_pontos:
        return []

    ordenados = sorted(float(p) for p in lista_pontos)
    filtrados = [ordenados[0]]

    for p in ordenados[1:]:
        if abs(p - filtrados[-1]) >= tolerancia:
            filtrados.append(p)

    return filtrados


def coletar_cotas_existentes(dwg, nivel_cota=None):
    """
    Varre o DWG coletando todas as cotas inteligentes (IPOCOT) e textos de cota
    ja existentes para evitar sobreposicoes e identificar linhas de cota ativas.
    """
    _garantir_ipocot_carregado()
    cotas = []
    try:
        dwg.iterator.Begin()
        cur_obj = None
        while True:
            tipo = dwg.iterator.Next()
            if tipo == TQSDwg.DWGTYPE_EOF:
                break

            if tipo == TQSDwg.DWGTYPE_OBJECT and dwg.iterator.objectName == "IPOCOT":
                cur_obj = {
                    "addr": dwg.iterator.GetElementReadPosition(),
                    "level": dwg.iterator.level,
                    "lines": [],
                    "text": None,
                }
            elif tipo == TQSDwg.DWGTYPE_OBJECTEND and cur_obj is not None:
                if cur_obj["text"] is not None:
                    txt_info = cur_obj["text"]
                    ang = txt_info["ang"]
                    orient = "V" if (abs(ang - 90.0) < 10.0 or abs(ang - 270.0) < 10.0) else "H"

                    pts_orig = [
                        ln for ln in cur_obj["lines"]
                        if abs(ln[1] - ln[3]) < 0.05 and abs(ln[2] - ln[4]) < 0.05
                    ]
                    linhas_221 = [
                        ln for ln in cur_obj["lines"]
                        if abs(ln[1] - ln[3]) >= 0.05 or abs(ln[2] - ln[4]) >= 0.05
                    ]

                    p1 = None
                    p2 = None
                    pos_linha = txt_info["y"] if orient == "H" else txt_info["x"]

                    if len(pts_orig) >= 2:
                        if orient == "H":
                            xs = sorted([pts_orig[0][1], pts_orig[1][1]])
                            p1, p2 = xs[0], xs[1]
                        else:
                            ys = sorted([pts_orig[0][2], pts_orig[1][2]])
                            p1, p2 = ys[0], ys[1]

                    if linhas_221:
                        ln0 = linhas_221[0]
                        if orient == "H" and abs(ln0[2] - ln0[4]) < 0.5:
                            pos_linha = 0.5 * (ln0[2] + ln0[4])
                        elif orient == "V" and abs(ln0[1] - ln0[3]) < 0.5:
                            pos_linha = 0.5 * (ln0[1] + ln0[3])

                    cotas.append({
                        "tipo": "IPOCOT",
                        "orient": orient,
                        "p1": p1,
                        "p2": p2,
                        "pos_linha": pos_linha,
                        "x": txt_info["x"],
                        "y": txt_info["y"],
                        "h": txt_info["h"],
                        "ang": txt_info["ang"],
                        "texto": txt_info["texto"],
                        "lines": cur_obj["lines"],
                        "addr": cur_obj["addr"],
                    })
                cur_obj = None
            elif cur_obj is not None:
                if tipo == TQSDwg.DWGTYPE_TEXT:
                    cur_obj["text"] = {
                        "texto": dwg.iterator.text.strip(),
                        "x": dwg.iterator.x1,
                        "y": dwg.iterator.y1,
                        "h": dwg.iterator.textHeight,
                        "ang": dwg.iterator.textAngle % 360.0,
                    }
                elif tipo == TQSDwg.DWGTYPE_LINE:
                    cur_obj["lines"].append((
                        dwg.iterator.level,
                        dwg.iterator.x1,
                        dwg.iterator.y1,
                        dwg.iterator.x2,
                        dwg.iterator.y2,
                    ))
            elif tipo == TQSDwg.DWGTYPE_TEXT:
                if nivel_cota is not None and dwg.iterator.level == nivel_cota:
                    ang = dwg.iterator.textAngle % 360.0
                    orient = "V" if (abs(ang - 90.0) < 10.0 or abs(ang - 270.0) < 10.0) else "H"
                    cotas.append({
                        "tipo": "TEXT",
                        "orient": orient,
                        "p1": None,
                        "p2": None,
                        "pos_linha": dwg.iterator.y1 if orient == "H" else dwg.iterator.x1,
                        "x": dwg.iterator.xc,
                        "y": dwg.iterator.yc,
                        "h": dwg.iterator.textHeight,
                        "ang": ang,
                        "texto": dwg.iterator.text.strip(),
                        "lines": [],
                    })
    except Exception:
        pass

    return cotas


def cota_ja_existe(
    p1,
    p2,
    cotas_existentes,
    tolerancia=2.0,
    orient=None,
    pos_linha=None,
    tol_linha=25.0
):
    """
    Verifica se ja existe uma cota cobrindo aproximadamente o mesmo intervalo [p1, p2].
    Se pos_linha for informado, verifica apenas cotas na mesma faixa/camada (dentro de tol_linha).
    """
    if not cotas_existentes:
        return False

    a1, a2 = min(p1, p2), max(p1, p2)
    comp_alvo = a2 - a1
    meio_alvo = 0.5 * (a1 + a2)

    for c in cotas_existentes:
        if orient is not None and c.get("orient") and c["orient"] != orient:
            continue
        if pos_linha is not None and c.get("pos_linha") is not None:
            if abs(c["pos_linha"] - pos_linha) > tol_linha:
                continue

        if c.get("p1") is not None and c.get("p2") is not None:
            if abs(c["p1"] - a1) <= tolerancia and abs(c["p2"] - a2) <= tolerancia:
                return True

        if c.get("texto"):
            try:
                val = float(c["texto"].replace(",", "."))
                if abs(val - comp_alvo) <= tolerancia:
                    coord_meio = c["x"] if c.get("orient") != "V" else c["y"]
                    if abs(coord_meio - meio_alvo) <= max(25.0, tolerancia * 8.0):
                        return True
            except ValueError:
                continue

    return False


def _registrar_cota_em_memoria(cotas_existentes, orient, p1, p2, pos_linha):
    """Registra uma cota recem-criada na lista em memoria para evitar duplicidade no mesmo comando."""
    if cotas_existentes is None:
        return
    a1, a2 = min(p1, p2), max(p1, p2)
    meio = 0.5 * (a1 + a2)
    cotas_existentes.append({
        "tipo": "IPOCOT",
        "orient": orient,
        "p1": a1,
        "p2": a2,
        "pos_linha": pos_linha,
        "x": meio if orient == "H" else pos_linha,
        "y": pos_linha if orient == "H" else meio,
        "h": 10.0,
        "ang": 0.0 if orient == "H" else 90.0,
        "texto": "%g" % round(a2 - a1, 1),
        "lines": [],
    })


def cotar_cadeia_horizontal(dwg, pontos_x, y_ref, y_cota, cotas_existentes=None, tolerancia=0.5):
    """
    Gera uma sequencia continua de cotas horizontais entre os pontos de pontos_x.
    """
    pts = filtrar_e_ordenar_pontos(pontos_x, tolerancia=tolerancia)
    if len(pts) < 2:
        return 0

    criadas = 0
    for i in range(len(pts) - 1):
        x1 = pts[i]
        x2 = pts[i + 1]

        if cotas_existentes is not None and cota_ja_existe(
            x1, x2, cotas_existentes, orient="H", pos_linha=y_cota
        ):
            continue

        dwg.dim.DimHorizontal(x1, y_ref, x2, y_ref, 0.5 * (x1 + x2), y_cota)
        _registrar_cota_em_memoria(cotas_existentes, "H", x1, x2, y_cota)
        criadas += 1

    return criadas


def cotar_cadeia_vertical(dwg, pontos_y, x_ref, x_cota, cotas_existentes=None, tolerancia=0.5):
    """
    Gera uma sequencia continua de cotas verticais entre os pontos de pontos_y.
    """
    pts = filtrar_e_ordenar_pontos(pontos_y, tolerancia=tolerancia)
    if len(pts) < 2:
        return 0

    criadas = 0
    for i in range(len(pts) - 1):
        y1 = pts[i]
        y2 = pts[i + 1]

        if cotas_existentes is not None and cota_ja_existe(
            y1, y2, cotas_existentes, orient="V", pos_linha=x_cota
        ):
            continue

        dwg.dim.DimVertical(x_ref, y1, x_ref, y2, x_cota, 0.5 * (y1 + y2))
        _registrar_cota_em_memoria(cotas_existentes, "V", y1, y2, x_cota)
        criadas += 1

    return criadas


def cotar_lado_tres_camadas(
    dwg,
    lado,
    bbox_estrutura,
    pontos_parciais=None,
    pontos_eixos=None,
    incluir_total=True,
    offsets=(40.0, 64.0, 99.4),
    cotas_existentes=None
):
    """
    Cria a hierarquia de cotas em 3 camadas para um dos lados da forma:
      - Camada 1: Cotas parciais de faces de vigas, pilares e vaos de laje.
      - Camada 2: Cotas entre eixos ou faces principais de pilares.
      - Camada 3: Cota total acumulada da estrutura de ponta a ponta.
    """
    x_min, y_min, x_max, y_max = bbox_estrutura
    lado_upper = lado.upper()
    off1, off2, off3 = offsets

    total_criadas = 0

    if lado_upper == "TOPO":
        y_ref = y_max
        if pontos_parciais:
            total_criadas += cotar_cadeia_horizontal(dwg, pontos_parciais, y_ref, y_max + off1, cotas_existentes)
        if pontos_eixos:
            total_criadas += cotar_cadeia_horizontal(dwg, pontos_eixos, y_ref, y_max + off2, cotas_existentes)
        if incluir_total:
            y_tot = y_max + off3
            if not (cotas_existentes is not None and cota_ja_existe(x_min, x_max, cotas_existentes, orient="H", pos_linha=y_tot)):
                dwg.dim.DimHorizontal(x_min, y_ref, x_max, y_ref, 0.5 * (x_min + x_max), y_tot)
                _registrar_cota_em_memoria(cotas_existentes, "H", x_min, x_max, y_tot)
                total_criadas += 1

    elif lado_upper == "BASE":
        y_ref = y_min
        if pontos_parciais:
            total_criadas += cotar_cadeia_horizontal(dwg, pontos_parciais, y_ref, y_min - off1, cotas_existentes)
        if pontos_eixos:
            total_criadas += cotar_cadeia_horizontal(dwg, pontos_eixos, y_ref, y_min - off2, cotas_existentes)
        if incluir_total:
            y_tot = y_min - off3
            if not (cotas_existentes is not None and cota_ja_existe(x_min, x_max, cotas_existentes, orient="H", pos_linha=y_tot)):
                dwg.dim.DimHorizontal(x_min, y_ref, x_max, y_ref, 0.5 * (x_min + x_max), y_tot)
                _registrar_cota_em_memoria(cotas_existentes, "H", x_min, x_max, y_tot)
                total_criadas += 1

    elif lado_upper == "ESQUERDA":
        x_ref = x_min
        if pontos_parciais:
            total_criadas += cotar_cadeia_vertical(dwg, pontos_parciais, x_ref, x_min - off1, cotas_existentes)
        if pontos_eixos:
            total_criadas += cotar_cadeia_vertical(dwg, pontos_eixos, x_ref, x_min - off2, cotas_existentes)
        if incluir_total:
            x_tot = x_min - off3
            if not (cotas_existentes is not None and cota_ja_existe(y_min, y_max, cotas_existentes, orient="V", pos_linha=x_tot)):
                dwg.dim.DimVertical(x_ref, y_min, x_ref, y_max, x_tot, 0.5 * (y_min + y_max))
                _registrar_cota_em_memoria(cotas_existentes, "V", y_min, y_max, x_tot)
                total_criadas += 1

    elif lado_upper == "DIREITA":
        x_ref = x_max
        if pontos_parciais:
            total_criadas += cotar_cadeia_vertical(dwg, pontos_parciais, x_ref, x_max + off1, cotas_existentes)
        if pontos_eixos:
            total_criadas += cotar_cadeia_vertical(dwg, pontos_eixos, x_ref, x_max + off2, cotas_existentes)
        if incluir_total:
            x_tot = x_max + off3
            if not (cotas_existentes is not None and cota_ja_existe(y_min, y_max, cotas_existentes, orient="V", pos_linha=x_tot)):
                dwg.dim.DimVertical(x_ref, y_min, x_ref, y_max, x_tot, 0.5 * (y_min + y_max))
                _registrar_cota_em_memoria(cotas_existentes, "V", y_min, y_max, x_tot)
                total_criadas += 1

    return total_criadas


def extrair_geometria_forma(dwg):
    """
    Extrai automaticamente a geometria estrutural da planta de formas:
      - bbox_estrutura: (x_min, y_min, x_max, y_max) das faces de concreto (Niveis 1, 2, 4, 201)
      - pontos_x_todos: todas as faces verticais de vigas (comprimento >= 40cm)
      - pontos_y_todos: todas as faces horizontais de vigas (comprimento >= 40cm)
      - pontos_x_pilares: faces externas + faces de pilares para a Camada 2 horizontal
      - pontos_y_pilares: faces externas + faces de pilares para a Camada 2 vertical
      - pontos_y_bordas: [y_min, y_face_int_inf, y_face_int_sup, y_max]
      - pilares_bboxes: lista de bounding boxes (xmin, ymin, xmax, ymax) de cada pilar (Nivel 4)
    """
    xs_concreto = []
    ys_concreto = []
    xs_pilares = []
    ys_pilares = []
    pilares_bboxes = []
    seg_vert = []
    seg_horiz = []

    dwg.iterator.Begin()
    while True:
        tipo = dwg.iterator.Next()
        if tipo == TQSDwg.DWGTYPE_EOF:
            break
        if dwg.iterator.inBlock != 0:
            continue

        nivel = dwg.iterator.level
        if tipo == TQSDwg.DWGTYPE_POLYLINE and nivel in (1, 2, 4, 201):
            pts = [dwg.iterator.GetPolylinePt(i) for i in range(dwg.iterator.xySize)]
            if not pts:
                continue

            if nivel == 4:
                pxs = [p[0] for p in pts]
                pys = [p[1] for p in pts]
                pilares_bboxes.append((min(pxs), min(pys), max(pxs), max(pys)))
                for px, py in pts:
                    xs_pilares.append(px)
                    ys_pilares.append(py)
                    xs_concreto.append(px)
                    ys_concreto.append(py)
            else:
                for k in range(len(pts) - 1):
                    x1, y1 = pts[k]
                    x2, y2 = pts[k + 1]
                    comp = math.hypot(x2 - x1, y2 - y1)
                    if comp < 5.0:
                        continue
                    xs_concreto.extend([x1, x2])
                    ys_concreto.extend([y1, y2])
                    if abs(x1 - x2) < 0.5 and abs(y2 - y1) >= 20.0:
                        seg_vert.append((0.5 * (x1 + x2), min(y1, y2), max(y1, y2)))
                    elif abs(y1 - y2) < 0.5 and abs(x2 - x1) >= 20.0:
                        seg_horiz.append((0.5 * (y1 + y2), min(x1, x2), max(x1, x2)))

    if not xs_concreto or not ys_concreto:
        return None

    x_min = min(xs_concreto)
    x_max = max(xs_concreto)
    y_min = min(ys_concreto)
    y_max = max(ys_concreto)
    bbox = (x_min, y_min, x_max, y_max)

    xs_vigas = [s[0] for s in seg_vert if (s[2] - s[1]) >= 40.0]
    ys_vigas = [s[0] for s in seg_horiz if (s[2] - s[1]) >= 40.0]

    pontos_x_todos = filtrar_e_ordenar_pontos([x_min, x_max] + xs_vigas, tolerancia=1.0)
    pontos_y_todos = filtrar_e_ordenar_pontos([y_min, y_max] + ys_vigas, tolerancia=1.0)

    pontos_x_pilares = filtrar_e_ordenar_pontos([x_min, x_max] + xs_pilares, tolerancia=1.0)
    pontos_y_pilares = filtrar_e_ordenar_pontos([y_min, y_max] + ys_pilares, tolerancia=1.0)

    x_int_esq = None
    for x in pontos_x_todos:
        if 8.0 <= (x - x_min) <= 35.0:
            x_int_esq = x
            break

    x_int_dir = None
    for x in reversed(pontos_x_todos):
        if 8.0 <= (x_max - x) <= 35.0:
            x_int_dir = x
            break

    y_int_inf = None
    for y in pontos_y_todos:
        if 8.0 <= (y - y_min) <= 35.0:
            y_int_inf = y
            break

    y_int_sup = None
    for y in reversed(pontos_y_todos):
        if 8.0 <= (y_max - y) <= 35.0:
            y_int_sup = y
            break

    pts_y_bordas = [y_min]
    if y_int_inf is not None:
        pts_y_bordas.append(y_int_inf)
    if y_int_sup is not None:
        pts_y_bordas.append(y_int_sup)
    pts_y_bordas.append(y_max)
    pts_y_bordas = filtrar_e_ordenar_pontos(pts_y_bordas, tolerancia=1.0)

    return {
        "bbox": bbox,
        "pontos_x_todos": pontos_x_todos,
        "pontos_y_todos": pontos_y_todos,
        "pontos_x_pilares": pontos_x_pilares,
        "pontos_y_pilares": pontos_y_pilares,
        "pontos_y_bordas": pts_y_bordas,
        "pilares_bboxes": pilares_bboxes,
        "seg_vert": seg_vert,
        "seg_horiz": seg_horiz,
        "x_int_esq": x_int_esq,
        "x_int_dir": x_int_dir,
        "y_int_inf": y_int_inf,
        "y_int_sup": y_int_sup,
    }


def _escolher_x_livre_para_cota_vertical(dwg, x_pref, x_min_faixa, x_max_faixa, y_ini, y_fim):
    """
    Escolhe uma coordenada X dentro de [x_min_faixa, x_max_faixa] para uma linha de cota
    vertical que minimize colisoes com textos de laje (L..., h=..., LAJE REBAIXADA).
    """
    textos_laje = []
    dwg.iterator.Begin()
    while True:
        it = dwg.iterator.Next()
        if it == TQSDwg.DWGTYPE_EOF:
            break
        if it == TQSDwg.DWGTYPE_TEXT and dwg.iterator.level in (10, 13):
            txt = dwg.iterator.text.strip()
            x1, y1 = dwg.iterator.x1, dwg.iterator.y1
            h = dwg.iterator.textHeight
            ang = dwg.iterator.textAngle
            textos_laje.append(_bbox_texto(x1, y1, h, ang, txt))

    def _colide_com_laje(x_cand):
        # Faixa ocupada pela linha de cota vertical e seu texto (x_cand - 14 a x_cand + 6)
        b_cota = (x_cand - 14.0, y_ini, x_cand + 6.0, y_fim)
        for bl in textos_laje:
            if _boxes_colidem(b_cota, bl, margem=3.0):
                return True
        return False

    if not _colide_com_laje(x_pref):
        return x_pref

    # Testa candidatos dentro da faixa do balanco
    for delta in (70.0, 60.0, 50.0, 75.0, -10.0, 40.0):
        cand = x_pref + delta
        if x_min_faixa <= cand <= x_max_faixa and not _colide_com_laje(cand):
            return cand

    return x_pref


def _desenhar_seta_chamada_pilar(dwg, x_fim_patamar, x_joelho, y_patamar, x_seta, y_seta):
    """
    Desenha uma linha de chamada com patamar horizontal (sublinhando o texto do pilar)
    e seta na ponta tocando o pilar, no nivel 221 (padrao de cotas/chamadas do TQS).
    """
    dwg.draw.level = 221
    dwg.draw.color = -1
    dwg.draw.style = 0

    # 1. Patamar horizontal sob o nome do pilar
    dwg.draw.Line(x_fim_patamar, y_patamar, x_joelho, y_patamar)
    # 2. Linha diagonal do joelho ate a borda do pilar
    dwg.draw.Line(x_joelho, y_patamar, x_seta, y_seta)

    # 3. Seta na ponta (x_seta, y_seta) apontando de (x_joelho, y_patamar) para (x_seta, y_seta)
    dx = x_joelho - x_seta
    dy = y_patamar - y_seta
    comp = math.hypot(dx, dy)
    if comp > 1.0:
        ang_base = math.atan2(dy, dx)
        comp_seta = 6.0
        abertura = math.radians(18.0)
        for sinal in (-1.0, 1.0):
            ang_asa = ang_base + sinal * abertura
            xa = x_seta + comp_seta * math.cos(ang_asa)
            ya = y_seta + comp_seta * math.sin(ang_asa)
            dwg.draw.Line(x_seta, y_seta, xa, ya)


def organizar_textos_sem_sobreposicao(dwg, geo=None, cotas=None):
    """
    Reorganiza automaticamente textos de pilares (P1..Pn + secao), vigas (V101..Vn + secao
    + VIGA INVERTIDA) e lajes (L103 + h=15 + LAJE REBAIXADA) para eliminar colisoes com
    linhas de cota, ticks e textos de cota.
    Quando um pilar precisa ser afastado da linha de cota, desenha tambem a linha de
    chamada com seta e patamar sublinhando o nome do pilar (padrao executivo de obra).
    """
    _garantir_ipocot_carregado()
    if geo is None:
        geo = extrair_geometria_forma(dwg)
    if not geo:
        return 0

    if cotas is None:
        cotas = coletar_cotas_existentes(dwg)
    else:
        cotas_dwg = coletar_cotas_existentes(dwg)
        if len(cotas_dwg) > len(cotas):
            cotas = cotas_dwg

    # Coleta todas as caixas de textos de cota (nivel 216) e linhas de cota principais (nivel 221)
    caixas_cota_txt = []
    linhas_cota_v = []  # (x_linha, y_min, y_max)
    linhas_cota_h = []  # (y_linha, x_min, x_max)
    todos_segmentos_cota = []  # (xmin, ymin, xmax, ymax)

    for c in cotas:
        bx_txt = _bbox_texto(c["x"], c["y"], c.get("h", 10.0), c.get("ang", 0.0), c["texto"])
        caixas_cota_txt.append(bx_txt)
        todos_segmentos_cota.append(bx_txt)

        if c.get("orient") == "V" and c.get("p1") is not None and c.get("p2") is not None:
            xv = c["pos_linha"]
            p_min = min(c["p1"], c["p2"])
            p_max = max(c["p1"], c["p2"])
            yv1 = p_min - 12.5
            yv2 = p_max + 12.5
            linhas_cota_v.append((xv, yv1, yv2))
            # Haste fina da linha de cota vertical + blocos de tick nas extremidades
            todos_segmentos_cota.append((xv - 0.8, yv1, xv + 0.8, yv2))
            todos_segmentos_cota.append((xv - 5.0, p_min - 5.0, xv + 5.0, p_min + 5.0))
            todos_segmentos_cota.append((xv - 5.0, p_max - 5.0, xv + 5.0, p_max + 5.0))
        elif c.get("orient") == "H" and c.get("p1") is not None and c.get("p2") is not None:
            yh = c["pos_linha"]
            p_min = min(c["p1"], c["p2"])
            p_max = max(c["p1"], c["p2"])
            xh1 = p_min - 12.5
            xh2 = p_max + 12.5
            linhas_cota_h.append((yh, xh1, xh2))
            todos_segmentos_cota.append((xh1, yh - 0.8, xh2, yh + 0.8))
            todos_segmentos_cota.append((p_min - 5.0, yh - 5.0, p_min + 5.0, yh + 5.0))
            todos_segmentos_cota.append((p_max - 5.0, yh - 5.0, p_max + 5.0, yh + 5.0))

        for ln in c.get("lines", []):
            lvl, lx1, ly1, lx2, ly2 = ln
            if abs(lx1 - lx2) < 0.05 and abs(ly1 - ly2) < 0.05:
                continue
            b_ln = (min(lx1, lx2), min(ly1, ly2), max(lx1, lx2), max(ly1, ly2))
            todos_segmentos_cota.append(b_ln)
            # Se for linha de chamada vertical longa, adiciona tambem em linhas_cota_v
            if abs(lx1 - lx2) < 0.5 and abs(ly2 - ly1) >= 15.0:
                linhas_cota_v.append((0.5 * (lx1 + lx2), min(ly1, ly2), max(ly1, ly2)))

    # Coleta textos estruturais: Pilares (9, 12), Vigas (8, 11), Lajes (10, 13) e Linhas 242
    pilares_txt = []
    vigas_txt = []
    lajes_txt = []
    linhas_242 = []
    linhas_corte = []

    pilar_atual = None
    viga_atual = None
    laje_atual = None

    dwg.iterator.Begin()
    while True:
        tipo = dwg.iterator.Next()
        if tipo == TQSDwg.DWGTYPE_EOF:
            break
        if dwg.iterator.inBlock != 0:
            continue

        nivel = dwg.iterator.level
        addr = dwg.iterator.GetElementReadPosition()

        if tipo == TQSDwg.DWGTYPE_LINE and nivel == 242:
            linhas_242.append({
                "addr": addr,
                "x1": dwg.iterator.x1,
                "y1": dwg.iterator.y1,
                "x2": dwg.iterator.x2,
                "y2": dwg.iterator.y2,
            })
        elif tipo == TQSDwg.DWGTYPE_LINE and nivel in (200, 205):
            linhas_corte.append((
                min(dwg.iterator.x1, dwg.iterator.x2) - 2.0,
                min(dwg.iterator.y1, dwg.iterator.y2) - 2.0,
                max(dwg.iterator.x1, dwg.iterator.x2) + 2.0,
                max(dwg.iterator.y1, dwg.iterator.y2) + 2.0,
            ))
        elif tipo == TQSDwg.DWGTYPE_TEXT:
            txt = dwg.iterator.text.strip()
            x1, y1 = dwg.iterator.x1, dwg.iterator.y1
            x2, y2 = dwg.iterator.x2, dwg.iterator.y2
            h = dwg.iterator.textHeight
            ang = _normalizar_angulo(dwg.iterator.textAngle)

            if nivel == 9 and txt.upper().startswith("P"):
                pilar_atual = {
                    "nome": txt,
                    "addr_nome": addr,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "h": h, "ang": ang,
                    "secao": None,
                }
                pilares_txt.append(pilar_atual)
            elif nivel == 12 and pilar_atual is not None and pilar_atual["secao"] is None:
                pilar_atual["secao"] = {
                    "texto": txt,
                    "addr": addr,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "h": h, "ang": ang,
                }
            elif nivel == 8 and txt.upper().startswith("V"):
                viga_atual = {
                    "nome": txt,
                    "addr_nome": addr,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "h": h, "ang": ang,
                    "secao": None,
                    "invertida": None,
                }
                vigas_txt.append(viga_atual)
            elif nivel == 11:
                if "/" in txt and viga_atual is not None and viga_atual["secao"] is None:
                    viga_atual["secao"] = {
                        "texto": txt,
                        "addr": addr,
                        "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                        "h": h, "ang": ang,
                    }
                elif "INVERTIDA" in txt.upper():
                    # Associa ao cabecalho da viga na mesma faixa
                    for v in vigas_txt:
                        if v["ang"] == ang:
                            if ang == 0.0 and abs(v["y1"] - y1) <= 15.0:
                                v["invertida"] = {
                                    "texto": txt, "addr": addr,
                                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                                    "h": h, "ang": ang,
                                }
                                break
                            elif ang == 90.0 and abs(v["x1"] - x1) <= 15.0:
                                v["invertida"] = {
                                    "texto": txt, "addr": addr,
                                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                                    "h": h, "ang": ang,
                                }
                                break
            elif nivel == 10 and txt.upper().startswith("L"):
                laje_atual = {
                    "nome": txt,
                    "addr_nome": addr,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "h": h, "ang": ang,
                    "itens": [],
                }
                lajes_txt.append(laje_atual)
            elif nivel == 13 and any(ch.isalpha() for ch in txt):
                if laje_atual is not None and abs(x1 - laje_atual["x1"]) <= 45.0 and 0.0 <= (laje_atual["y1"] - y1) <= 115.0:
                    laje_atual["itens"].append({
                        "texto": txt,
                        "addr": addr,
                        "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                        "h": h, "ang": ang,
                    })
                else:
                    for lj in lajes_txt:
                        if abs(x1 - lj["x1"]) <= 45.0 and 0.0 <= (lj["y1"] - y1) <= 115.0:
                            lj["itens"].append({
                                "texto": txt,
                                "addr": addr,
                                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                                "h": h, "ang": ang,
                            })
                            break

    ajustes = 0

    # -------------------------------------------------------------------------
    # 1. AJUSTAR TEXTOS DE VIGAS HORIZONTAIS QUE COLIDEM COM LINHAS DE COTA VERTICAIS
    # -------------------------------------------------------------------------
    for v in vigas_txt:
        if v["ang"] != 0.0 or v["secao"] is None:
            continue
        sec = v["secao"]
        inv = v["invertida"]

        # Verifica se alguma linha de cota vertical cruza o titulo V... ou a secao b/h
        b_nome = _bbox_texto(v["x1"], v["y1"], v["h"], 0.0, v["nome"])
        b_sec = _bbox_texto(sec["x1"], sec["y1"], sec["h"], 0.0, sec["texto"])

        colide_v = False
        for xv, yv1, yv2 in linhas_cota_v:
            b_lv = (xv - 6.0, yv1, xv + 4.0, yv2)
            if _boxes_colidem(b_nome, b_lv, margem=2.0) or _boxes_colidem(b_sec, b_lv, margem=2.0):
                colide_v = True
                break

        if not colide_v:
            continue

        larg_nome = len(v["nome"]) * v["h"]
        larg_sec = len(sec["texto"]) * sec["h"]
        larg_inv = (len(inv["texto"]) * inv["h"]) if inv else 0.0

        # Procura um X inicial livre para o grupo [V..., b/h, VIGA INVERTIDA]
        # mantendo o mesmo Y
        y_v = v["y1"]
        x_orig = v["x1"]
        candidatos_x = []
        # Adiciona candidatos logo apos qualquer linha de cota vertical que esteja na faixa da viga
        xvs_proximos = sorted(
            [xv for xv, yv1, yv2 in linhas_cota_v if yv1 <= y_v <= yv2 and -20.0 <= (xv - x_orig) <= 220.0]
        )
        for xv in xvs_proximos:
            candidatos_x.append(xv + 8.0)

        # Adiciona candidatos logo apos linhas de corte verticais (ex: corte D-D em x=320.1)
        for lc in sorted(linhas_corte):
            if (lc[2] - lc[0]) <= 15.0 and lc[1] <= y_v <= lc[3]:
                candidatos_x.append(lc[2] + 8.0)

        candidatos_x.extend([
            x_orig + 42.0,
            x_orig + 48.0,
            x_orig + 55.0,
            x_orig + 165.0,
            x_orig + 175.0,
            x_orig + 310.0,
            x_orig + 25.0,
            x_orig - 20.0,
        ])

        melhor_x = None
        for xc in candidatos_x:
            bn = _bbox_texto(xc, y_v, v["h"], 0.0, v["nome"])
            xs_cand = xc + larg_nome + 12.0
            bs = _bbox_texto(xs_cand, y_v, sec["h"], 0.0, sec["texto"])

            # Verifica se bn ou bs batem em alguma linha de cota vertical ou linha de corte
            bate = False
            for xv, yv1, yv2 in linhas_cota_v:
                b_lv = (xv - 6.0, yv1, xv + 4.0, yv2)
                if _boxes_colidem(bn, b_lv, margem=1.5) or _boxes_colidem(bs, b_lv, margem=1.5):
                    bate = True
                    break
            if not bate:
                for lc in linhas_corte:
                    if _boxes_colidem(bn, lc, margem=2.0) or _boxes_colidem(bs, lc, margem=2.0):
                        bate = True
                        break
            if not bate:
                melhor_x = xc
                break

        if melhor_x is not None and abs(melhor_x - x_orig) > 0.5:
            dx_n = melhor_x - v["x1"]
            dwg.edit.Move(v["addr_nome"], dx_n, 0.0)
            v["x1"] = melhor_x
            v["x2"] += dx_n

            novo_x_sec = melhor_x + larg_nome + 12.0
            dx_s = novo_x_sec - sec["x1"]
            dy_s = y_v - sec["y1"]
            dwg.edit.Move(sec["addr"], dx_s, dy_s)
            sec["x1"] = novo_x_sec
            sec["x2"] += dx_s
            sec["y1"] = y_v
            sec["y2"] = y_v

            if inv is not None:
                novo_x_inv = novo_x_sec + larg_sec + 14.0
                # Se novo_x_inv cruzar alguma linha vertical ou linha de corte, empurra logo para depois dela
                bi_test = _bbox_texto(novo_x_inv, y_v, inv["h"], 0.0, inv["texto"])
                for xv, yv1, yv2 in sorted(linhas_cota_v):
                    b_lv = (xv - 6.0, yv1, xv + 4.0, yv2)
                    if _boxes_colidem(bi_test, b_lv, margem=1.5) and abs(xv - novo_x_inv) <= 180.0:
                        novo_x_inv = max(novo_x_inv, xv + 8.0)
                        bi_test = _bbox_texto(novo_x_inv, y_v, inv["h"], 0.0, inv["texto"])
                for lc in sorted(linhas_corte):
                    # Apenas linhas de corte verticais (largura pequena em X)
                    if (lc[2] - lc[0]) <= 15.0 and _boxes_colidem(bi_test, lc, margem=2.0):
                        novo_x_inv = max(novo_x_inv, lc[2] + 6.0)
                        bi_test = _bbox_texto(novo_x_inv, y_v, inv["h"], 0.0, inv["texto"])
                dx_i = novo_x_inv - inv["x1"]
                dy_i = y_v - inv["y1"]
                dwg.edit.Move(inv["addr"], dx_i, dy_i)
                inv["x1"] = novo_x_inv
                inv["x2"] += dx_i
                inv["y1"] = y_v
                inv["y2"] = y_v

            ajustes += 1

    # -------------------------------------------------------------------------
    # 2. AJUSTAR TEXTOS DE PILARES (P1..Pn + SECAO) E CRIAR SETA DE CHAMADA
    # -------------------------------------------------------------------------
    pilares_bboxes = geo["pilares_bboxes"]

    # Coleta obstaculos fixos (vigas, lajes, linhas de concreto, cotas) para posicionar pilares
    obstaculos_para_pilar = list(todos_segmentos_cota) + list(pilares_bboxes) + list(linhas_corte)
    for v in vigas_txt:
        obstaculos_para_pilar.append(_bbox_texto(v["x1"], v["y1"], v["h"], v["ang"], v["nome"]))
        if v["secao"]:
            s = v["secao"]
            obstaculos_para_pilar.append(_bbox_texto(s["x1"], s["y1"], s["h"], s["ang"], s["texto"]))
        if v["invertida"]:
            i_obj = v["invertida"]
            obstaculos_para_pilar.append(_bbox_texto(i_obj["x1"], i_obj["y1"], i_obj["h"], i_obj["ang"], i_obj["texto"]))

    for p in pilares_txt:
        sec = p["secao"]
        b_p = _bbox_texto(p["x1"], p["y1"], p["h"], p["ang"], p["nome"])
        b_s = _bbox_texto(sec["x1"], sec["y1"], sec["h"], sec["ang"], sec["texto"]) if sec else b_p
        b_conj = (
            min(b_p[0], b_s[0]),
            min(b_p[1], b_s[1]),
            max(b_p[2], b_s[2]),
            max(b_p[3], b_s[3]),
        )

        # Encontra o poligono do pilar (Nivel 4) mais proximo
        pilar_box = None
        menor_d = float("inf")
        for pb in pilares_bboxes:
            pcx = 0.5 * (pb[0] + pb[2])
            pcy = 0.5 * (pb[1] + pb[3])
            d = math.hypot(p["x1"] - pcx, p["y1"] - pcy)
            if d < menor_d:
                menor_d = d
                pilar_box = pb

        # Verifica se o texto atual do pilar colide com alguma cota ou linha de concreto
        colide = False
        for obs in todos_segmentos_cota:
            if _boxes_colidem(b_conj, obs, margem=2.5):
                colide = True
                break

        if not colide:
            continue

        larg_conj = b_conj[2] - b_conj[0]
        alt_conj = b_conj[3] - b_conj[1]
        dy_sec = (sec["y1"] - p["y1"]) if sec else -18.0
        dx_sec = (sec["x1"] - p["x1"]) if sec else 0.0

        # Gera candidatos de posicao (x_novo, y_novo) ao redor do pilar
        pcx = 0.5 * (pilar_box[0] + pilar_box[2]) if pilar_box else p["x1"]
        pcy = 0.5 * (pilar_box[1] + pilar_box[3]) if pilar_box else p["y1"]

        candidatos = [
            # A direita da linha de cota vertical e abaixo do pilar (ideal p/ P1)
            (pcx + 62.0, pcy - 52.0),
            (pcx + 68.0, pcy - 56.0),
            # A esquerda do pilar e abaixo (ideal p/ P2, P3, P4)
            (pcx - larg_conj - 18.0, pcy - 32.0),
            (pcx - larg_conj - 18.0, pcy - 42.0),
            # A direita do pilar e abaixo (caso nao haja cota a direita)
            (pcx + 25.0, pcy - 38.0),
            (pcx + 25.0, pcy - 48.0),
            # A esquerda mais afastado (caso haja cota a esquerda)
            (pcx - larg_conj - 55.0, pcy - 32.0),
            # Acima e a direita/esquerda
            (pcx + 62.0, pcy + 30.0),
            (pcx - larg_conj - 18.0, pcy + 30.0),
        ]

        escolhido = None
        for cx_cand, cy_cand in candidatos:
            bp_c = _bbox_texto(cx_cand, cy_cand, p["h"], p["ang"], p["nome"])
            bs_c = _bbox_texto(cx_cand + dx_sec, cy_cand + dy_sec, sec["h"], sec["ang"], sec["texto"]) if sec else bp_c
            bc_c = (
                min(bp_c[0], bs_c[0]),
                min(bp_c[1], bs_c[1]),
                max(bp_c[2], bs_c[2]),
                max(bp_c[3], bs_c[3]),
            )

            # Verifica colisao com cotas, pilares e vigas
            livre = True
            for obs in obstaculos_para_pilar:
                if _boxes_colidem(bc_c, obs, margem=3.0):
                    livre = False
                    break
            # Evita tambem cruzar segmentos horizontais/verticais de concreto (vigas)
            if livre:
                for xv, yv1, yv2 in geo["seg_vert"]:
                    if _boxes_colidem(bc_c, (xv - 1.0, yv1, xv + 1.0, yv2), margem=2.0):
                        livre = False
                        break
            if livre:
                for yh, xh1, xh2 in geo["seg_horiz"]:
                    if _boxes_colidem(bc_c, (xh1, yh - 1.0, xh2, yh + 1.0), margem=2.0):
                        livre = False
                        break

            if livre:
                escolhido = (cx_cand, cy_cand, bc_c)
                break

        if escolhido is not None:
            nx, ny, bc_novo = escolhido
            dx = nx - p["x1"]
            dy = ny - p["y1"]
            dwg.edit.Move(p["addr_nome"], dx, dy)
            if sec is not None:
                dwg.edit.Move(sec["addr"], dx, dy)

            p["x1"] = nx
            p["y1"] = ny
            if sec is not None:
                sec["x1"] += dx
                sec["y1"] += dy

            obstaculos_para_pilar.append(bc_novo)

            # Se o texto do pilar ficou mais afastado do pilar (ou atravessou uma linha de cota),
            # desenha a seta de chamada com patamar sublinhando o nome do pilar (padrao Foto 1)
            if pilar_box is not None:
                y_patamar = ny - 3.0
                if nx >= pilar_box[2]:
                    x_joelho = nx - 4.0
                    x_fim_patamar = nx + larg_conj + 2.0
                    x_seta = min(pilar_box[2], max(pilar_box[0] + 6.0, 0.5 * (pilar_box[0] + pilar_box[2]) + 4.0))
                    y_seta = pilar_box[1] if y_patamar < pilar_box[1] else pilar_box[3]
                else:
                    x_joelho = nx + larg_conj + 4.0
                    x_fim_patamar = nx - 2.0
                    x_seta = max(pilar_box[0], min(pilar_box[2] - 6.0, 0.5 * (pilar_box[0] + pilar_box[2]) - 4.0))
                    y_seta = pilar_box[1] if y_patamar < pilar_box[1] else pilar_box[3]

                dist_pilar = math.hypot(x_joelho - x_seta, y_patamar - y_seta)
                if dist_pilar >= 40.0:
                    for l242 in linhas_242:
                        if abs(l242["x1"] - pcx) <= 5.0 and abs(l242["y1"] - pcy) <= 5.0:
                            dwg.edit.Erase(l242["addr"])

                    _desenhar_seta_chamada_pilar(
                        dwg, x_fim_patamar, x_joelho, y_patamar, x_seta, y_seta
                    )

            ajustes += 1

    # -------------------------------------------------------------------------
    # 3. AJUSTAR BLOCOS DE LAJE (L103 / h=15 / LAJE REBAIXADA) SE COLIDIREM COM COTAS
    # -------------------------------------------------------------------------
    for lj in lajes_txt:
        bloco_elems = [{"addr": lj["addr_nome"], "x1": lj["x1"], "y1": lj["y1"], "h": lj["h"], "ang": lj["ang"], "texto": lj["nome"]}]
        for it in lj["itens"]:
            bloco_elems.append(it)

        def _bloco_laje_colide(dx_t, dy_t):
            for el in bloco_elems:
                bx = _bbox_texto(el["x1"] + dx_t, el["y1"] + dy_t, el["h"], el["ang"], el["texto"])
                for obs in todos_segmentos_cota:
                    if _boxes_colidem(bx, obs, margem=1.5):
                        return True
                for lc in linhas_corte:
                    if _boxes_colidem(bx, lc, margem=2.5):
                        return True
                for v in vigas_txt:
                    if v["invertida"]:
                        inv = v["invertida"]
                        bi = _bbox_texto(inv["x1"], inv["y1"], inv["h"], inv["ang"], inv["texto"])
                        if _boxes_colidem(bx, bi, margem=2.5):
                            return True
            return False

        if _bloco_laje_colide(0.0, 0.0):
            encontrou = None
            for dy_c in (0.0, 15.0, -15.0, 75.0, 88.0, 95.0, -45.0, -60.0):
                for dx_c in (0.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0, 32.0, -14.0, -25.0):
                    if not _bloco_laje_colide(dx_c, dy_c):
                        encontrou = (dx_c, dy_c)
                        break
                if encontrou:
                    break
            if encontrou:
                dx_c, dy_c = encontrou
                for el in bloco_elems:
                    dwg.edit.Move(el["addr"], dx_c, dy_c)
                ajustes += 1

    return ajustes


class CotadorFormas(object):
    """
    Classe utilitaria orientada a objetos para gerenciamento completo
    de cotagem em plantas de formas no TQS EAG.
    """

    def __init__(self, dwg, carregar_existentes=True):
        self.dwg = dwg
        self.cotas_existentes = coletar_cotas_existentes(dwg) if carregar_existentes else []

    def configurar_estilo(self, **kwargs):
        """Aplica configuracoes visuais no dwg.dim."""
        configurar_estilo_cotas(self.dwg, **kwargs)

    def cotar_lado(
        self,
        lado,
        bbox_estrutura,
        pontos_parciais=None,
        pontos_eixos=None,
        incluir_total=True,
        offsets=(40.0, 64.0, 99.4)
    ):
        """Cota um lado completo da forma respeitando as 3 camadas."""
        return cotar_lado_tres_camadas(
            dwg=self.dwg,
            lado=lado,
            bbox_estrutura=bbox_estrutura,
            pontos_parciais=pontos_parciais,
            pontos_eixos=pontos_eixos,
            incluir_total=incluir_total,
            offsets=offsets,
            cotas_existentes=self.cotas_existentes
        )

    def cotar_forma_completa(self, organizar_textos=True):
        """
        Executa a cotagem automatica completa da planta de formas:
          1. Extrai a geometria da estrutura (vigas, pilares, lajes e bordas).
          2. Completa as cadeias de cotas internas existentes (horizontal e vertical)
             ate as faces externas das vigas de borda.
          3. Adiciona cadeia vertical interna esquerda e cotas das vigas de borda
             nas extremidades dos balancos, escolhendo posicoes livres de textos de laje.
          4. Gera as cotas externas nos 4 lados (TOPO, BASE, ESQUERDA, DIREITA)
             seguindo o padrao de camadas sem duplicar cotas existentes.
          5. Reorganiza automaticamente textos de pilares (com seta DimNote quando
             necessario), vigas e lajes para eliminar sobreposicoes para leitura em obra.
        """
        geo = extrair_geometria_forma(self.dwg)
        if not geo:
            return 0

        self.configurar_estilo()

        bbox = geo["bbox"]
        x_min, y_min, x_max, y_max = bbox
        pts_x_todos = geo["pontos_x_todos"]
        pts_y_todos = geo["pontos_y_todos"]
        pts_x_pilares = geo["pontos_x_pilares"]
        pts_y_bordas = geo["pontos_y_bordas"]

        total_criadas = 0

        # ---------------------------------------------------------------------
        # 1. COMPLETAR CADEIAS INTERNAS EXISTENTES (HORIZONTAL E VERTICAL)
        # ---------------------------------------------------------------------
        cotas_h_internas = [
            c for c in self.cotas_existentes
            if c.get("orient") == "H" and (y_min + 20.0) < c.get("pos_linha", 0.0) < (y_max - 20.0)
        ]
        if cotas_h_internas:
            y_linha_h = cotas_h_internas[0]["pos_linha"]
        else:
            y_linha_h = y_min + 0.78 * (y_max - y_min)

        total_criadas += cotar_cadeia_horizontal(
            self.dwg, pts_x_todos, y_linha_h, y_linha_h, self.cotas_existentes
        )

        cotas_v_internas = [
            c for c in self.cotas_existentes
            if c.get("orient") == "V" and (x_min + 20.0) < c.get("pos_linha", 0.0) < (x_max - 20.0)
        ]
        if cotas_v_internas:
            x_linha_v_dir = cotas_v_internas[0]["pos_linha"]
        else:
            x_linha_v_dir = x_min + 0.76 * (x_max - x_min)

        total_criadas += cotar_cadeia_vertical(
            self.dwg, pts_y_todos, x_linha_v_dir, x_linha_v_dir, self.cotas_existentes
        )

        # ---------------------------------------------------------------------
        # 2. CADEIA VERTICAL INTERNA ESQUERDA (JUNTO AO 1o PILAR INTERNO)
        # ---------------------------------------------------------------------
        if len(pts_x_pilares) >= 4:
            x_pilar_esq_int = pts_x_pilares[2]  # face direita do pilar esquerdo (ex: 150.5)
            x_linha_v_esq = x_pilar_esq_int + 32.4  # ex: 182.9
            if abs(x_linha_v_esq - x_linha_v_dir) > 60.0:
                total_criadas += cotar_cadeia_vertical(
                    self.dwg, pts_y_todos, x_linha_v_esq, x_linha_v_esq, self.cotas_existentes
                )

        # ---------------------------------------------------------------------
        # 3. COTAS VERTICAIS DE BALANCO / BORDAS ESQUERDA E DIREITA (14 | 710 | 14)
        # ---------------------------------------------------------------------
        if len(pts_y_bordas) >= 3:
            # Balanco esquerdo (entre borda externa esquerda e 1o pilar)
            if len(pts_x_pilares) >= 2 and (pts_x_pilares[1] - x_min) >= 60.0:
                x_bal_esq = _escolher_x_livre_para_cota_vertical(
                    self.dwg,
                    x_min + 59.1,
                    x_min + 22.0,
                    pts_x_pilares[1] - 18.0,
                    y_min,
                    y_max
                )
                total_criadas += cotar_cadeia_vertical(
                    self.dwg, pts_y_bordas, x_bal_esq, x_bal_esq, self.cotas_existentes
                )

            # Balanco direito (entre ultimo pilar e borda externa direita)
            if len(pts_x_pilares) >= 2 and (x_max - pts_x_pilares[-2]) >= 60.0:
                x_bal_dir = _escolher_x_livre_para_cota_vertical(
                    self.dwg,
                    pts_x_pilares[-2] + 21.9,
                    pts_x_pilares[-2] + 18.0,
                    x_max - 22.0,
                    y_min,
                    y_max
                )
                total_criadas += cotar_cadeia_vertical(
                    self.dwg, pts_y_bordas, x_bal_dir, x_bal_dir, self.cotas_existentes
                )

        # ---------------------------------------------------------------------
        # 4. COTAS EXTERNAS NOS 4 LADOS (TOPO, BASE, ESQUERDA, DIREITA)
        # ---------------------------------------------------------------------
        total_criadas += self.cotar_lado(
            lado="TOPO",
            bbox_estrutura=bbox,
            pontos_parciais=None,
            pontos_eixos=pts_x_pilares if len(pts_x_pilares) > 2 else None,
            incluir_total=True,
            offsets=(35.0, 64.1, 99.4)
        )

        total_criadas += self.cotar_lado(
            lado="BASE",
            bbox_estrutura=bbox,
            pontos_parciais=None,
            pontos_eixos=None,
            incluir_total=True,
            offsets=(25.0, 35.0, 48.6)
        )

        total_criadas += self.cotar_lado(
            lado="ESQUERDA",
            bbox_estrutura=bbox,
            pontos_parciais=None,
            pontos_eixos=None,
            incluir_total=True,
            offsets=(25.0, 40.0, 56.5)
        )

        total_criadas += self.cotar_lado(
            lado="DIREITA",
            bbox_estrutura=bbox,
            pontos_parciais=None,
            pontos_eixos=None,
            incluir_total=True,
            offsets=(25.0, 40.0, 50.4)
        )

        # ---------------------------------------------------------------------
        # 5. REORGANIZAR TEXTOS PARA ELIMINAR SOBREPOSICOES COM AS COTAS
        # ---------------------------------------------------------------------
        if organizar_textos:
            organizar_textos_sem_sobreposicao(self.dwg, geo=geo, cotas=self.cotas_existentes)

        return total_criadas


def cmd_criar_cotas(eag, tqsjan):
    """
    Entry point do comando Criar Cotas para o EAG do TQS.
    Cria automaticamente as cotas externas (em camadas) e completa as cadeias
    de cotas internas da planta de formas sem duplicar cotas existentes.
    """
    try:
        dwg = tqsjan.dwg
        cotador = CotadorFormas(dwg)
        criadas = cotador.cotar_forma_completa()

        if criadas > 0:
            tqsjan.Regen()
            eag.msg.Print("G3 Plugins: %d cota(s) gerada(s) automaticamente na planta de formas!" % criadas)
            eag.msg.PrintStatus("%d cota(s) criada(s) com sucesso!" % criadas)
        else:
            eag.msg.Print("G3 Plugins: Todas as cotas da planta de formas ja existem (nenhuma cota duplicada).")
            eag.msg.PrintStatus("Nenhuma cota nova necessaria.")

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass


def meucmd(eag, tqsjan):
    """Entry point padrao quando chamado diretamente."""
    cmd_criar_cotas(eag, tqsjan)
