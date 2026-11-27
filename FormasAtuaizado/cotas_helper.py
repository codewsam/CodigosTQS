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

import os
import json
import math
import subprocess
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
    tamanho_tick=0.25,
    arredondar_5=False,
    fator_comprimento=1.0
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
    dwg.dim.dimtsz = float(tamanho_tick)
    dwg.dim.dimdle = float(extensao_linha)
    dwg.dim.dimexe = float(extensao_chamada)
    dwg.dim.dimexo = float(folga_chamada)
    dwg.dim.dimlfc = float(fator_comprimento)
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


def coletar_cotas_existentes(dwg, nivel_cota=216):
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
                        "addr_txt": txt_info.get("addr_txt"),
                        "bbox_texto": _bbox_texto(
                            txt_info["x"], txt_info["y"], txt_info["h"], txt_info["ang"], txt_info["texto"]
                        ),
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
                        "addr_txt": dwg.iterator.GetElementReadPosition(),
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
                    tx1 = dwg.iterator.x1
                    ty1 = dwg.iterator.y1
                    th = dwg.iterator.textHeight
                    tstr = dwg.iterator.text.strip()
                    addr = dwg.iterator.GetElementReadPosition()
                    cotas.append({
                        "tipo": "TEXT",
                        "orient": orient,
                        "p1": None,
                        "p2": None,
                        "pos_linha": (ty1 - 3.0) if orient == "H" else (tx1 + 3.0),
                        "x": tx1,
                        "y": ty1,
                        "h": th,
                        "ang": ang,
                        "texto": tstr,
                        "bbox_texto": _bbox_texto(tx1, ty1, th, ang, tstr),
                        "lines": [],
                        "addr": addr,
                    })
    except Exception:
        pass

    return cotas


def arredondar_valor_cota(valor):
    """
    Regra de arredondamento personalizada:
      - Termina em 0.1 ate 0.2 -> arredonda para .0
      - Termina em 0.3 ate 0.7 -> arredonda para .5
      - Termina em 0.8 ate 0.9 -> arredonda para 1.0 (inteiro seguinte)
    """
    v = round(float(valor), 2)
    sinal = -1.0 if v < 0 else 1.0
    v = abs(v)
    inteiro = int(math.floor(v + 1e-7))
    dec = round(v - inteiro, 2)

    if dec <= 0.25:
        res = float(inteiro)
    elif dec <= 0.75:
        res = float(inteiro) + 0.5
    else:
        res = float(inteiro + 1)

    return sinal * res


def formatar_valor_cota(valor_arr):
    """
    Formata o valor arredondado:
      - Se inteiro (ex: 80.0): '80'
      - Se meio (ex: 7.5): '7.5'
    """
    if abs(valor_arr - round(valor_arr)) < 1e-5:
        return str(int(round(valor_arr)))
    else:
        return "%.1f" % valor_arr


def _desativar_texto_manual_cota(dwg):
    """Desativa o modo de texto manual (COTETX) no TQS para nao abrir o popup em cotagens futuras."""
    try:
        dwg.m_mdwg.COTDTX()
    except Exception:
        pass


def criar_dim_horizontal(dwg, x1, y1, x2, y2, x3, y3, arredondar=False):
    """
    Cria uma cota horizontal IPOCOT REAL no TQS.
    Se arredondar=True, calcula o valor arredondado pela regra (0.1..0.2->0, 0.3..0.7->0.5, 0.8..0.9->1.0)
    e define em dwg.dim.dimtxu, garantindo que o objeto continue sendo uma COTA REAL associativa do TQS
    e nao linhas/textos soltos.
    """
    if arredondar:
        fator = float(getattr(dwg.dim, "dimlfc", 1.0) or 1.0)
        dist = abs(x2 - x1) * fator
        val_arr = arredondar_valor_cota(dist)
        dwg.dim.dimtxu = formatar_valor_cota(val_arr)
    else:
        _desativar_texto_manual_cota(dwg)
    try:
        dwg.dim.DimHorizontal(x1, y1, x2, y2, x3, y3)
    finally:
        _desativar_texto_manual_cota(dwg)


def criar_dim_vertical(dwg, x1, y1, x2, y2, x3, y3, arredondar=False):
    """
    Cria uma cota vertical IPOCOT REAL no TQS.
    Se arredondar=True, calcula o valor arredondado pela regra (0.1..0.2->0, 0.3..0.7->0.5, 0.8..0.9->1.0)
    e define em dwg.dim.dimtxu, garantindo que o objeto continue sendo uma COTA REAL associativa do TQS
    e nao linhas/textos soltos.
    """
    if arredondar:
        fator = float(getattr(dwg.dim, "dimlfc", 1.0) or 1.0)
        dist = abs(y2 - y1) * fator
        val_arr = arredondar_valor_cota(dist)
        dwg.dim.dimtxu = formatar_valor_cota(val_arr)
    else:
        _desativar_texto_manual_cota(dwg)
    try:
        dwg.dim.DimVertical(x1, y1, x2, y2, x3, y3)
    finally:
        _desativar_texto_manual_cota(dwg)


def re_criar_cota_ipocot(dwg, cota_dict, novo_texto):
    """
    Recria uma cota existente como um objeto IPOCOT REAL com o novo texto (arredondado),
    mantendo os pontos originais de definicao e a linha de cota.
    Garante que a cota continue sendo uma COTA REAL do TQS, permitindo mover/esticar normalmente.
    """
    if cota_dict.get("tipo") != "IPOCOT" or not cota_dict.get("addr"):
        return False

    orient = cota_dict.get("orient", "H")
    pos_linha = float(cota_dict.get("pos_linha", 0.0))

    pts_orig = [
        ln for ln in cota_dict.get("lines", [])
        if abs(ln[1] - ln[3]) < 0.05 and abs(ln[2] - ln[4]) < 0.05
    ]

    if len(pts_orig) >= 2:
        pt1 = (float(pts_orig[0][1]), float(pts_orig[0][2]))
        pt2 = (float(pts_orig[1][1]), float(pts_orig[1][2]))
    elif cota_dict.get("p1") is not None and cota_dict.get("p2") is not None:
        p1 = float(cota_dict["p1"])
        p2 = float(cota_dict["p2"])
        if orient == "H":
            pt1 = (p1, pos_linha)
            pt2 = (p2, pos_linha)
        else:
            pt1 = (pos_linha, p1)
            pt2 = (pos_linha, p2)
    else:
        return False

    try:
        dwg.edit.Erase(cota_dict["addr"])
    except Exception:
        return False

    try:
        dwg.dim.dimtxu = str(novo_texto)
        if orient == "H":
            dwg.dim.DimHorizontal(pt1[0], pt1[1], pt2[0], pt2[1], 0.5 * (pt1[0] + pt2[0]), pos_linha)
        else:
            dwg.dim.DimVertical(pt1[0], pt1[1], pt2[0], pt2[1], pos_linha, 0.5 * (pt1[1] + pt2[1]))
    finally:
        _desativar_texto_manual_cota(dwg)

    cota_dict["texto"] = str(novo_texto)
    return True


def aplicar_arredondamento_cotas(dwg, cotas_alvo=None):
    """
    Aplica o arredondamento (0.1..0.2 -> 0, 0.3..0.7 -> 0.5, 0.8..0.9 -> 1.0)
    nas cotas mantendo-as 100% como objetos IPOCOT REAIS do TQS.
    """
    cotas = coletar_cotas_existentes(dwg, nivel_cota=216) if cotas_alvo is None else cotas_alvo
    if not cotas:
        return 0

    total_arredondadas = 0
    for c in cotas:
        txt_orig = c.get("texto", "").strip()
        try:
            val = float(txt_orig.replace(",", "."))
        except (ValueError, TypeError):
            continue

        val_arr = arredondar_valor_cota(val)
        txt_novo = formatar_valor_cota(val_arr)

        if txt_novo == txt_orig:
            continue

        if c.get("tipo") == "IPOCOT" and c.get("addr"):
            if re_criar_cota_ipocot(dwg, c, txt_novo):
                total_arredondadas += 1
        elif c.get("tipo") == "TEXT" and c.get("addr"):
            old_lvl = dwg.draw.level
            old_col = dwg.draw.color
            try:
                dwg.edit.Erase(c["addr"])
                dwg.draw.level = 216
                dwg.draw.color = 3
                dwg.draw.Text(float(c["x"]), float(c["y"]), float(c.get("h", 10.0)), float(c.get("ang", 0.0)), txt_novo)
                total_arredondadas += 1
            finally:
                dwg.draw.level = old_lvl
                dwg.draw.color = old_col

    return total_arredondadas


def _substituir_ipocot_por_primitivos(dwg, cota_dict, novo_x, novo_y, estender_linha=True):
    """
    Substitui APENAS o objeto IPOCOT estreito especifico (cujo texto foi jogado
    para fora pelo TQS por ter vao < 40 cm) pelas suas linhas/ticks exatos
    no nivel 221 e pelo texto no nivel 216 na nova posicao (novo_x, novo_y),
    mantendo-o limpo dentro do vao sem sobrepor cotas vizinhas.
    NUNCA toca nem explode a cota vizinha (ex: 115, 50, etc.), preservando-a como IPOCOT real.
    """
    if cota_dict.get("tipo") != "IPOCOT" or not cota_dict.get("addr"):
        return False

    try:
        dwg.edit.Erase(cota_dict["addr"])
    except Exception:
        return False

    old_lvl = dwg.draw.level
    old_col = dwg.draw.color

    try:
        orient = cota_dict.get("orient", "H")
        h = float(cota_dict.get("h", 10.0))
        texto = str(cota_dict.get("texto", ""))
        larg_txt = max(h * 0.7, len(texto) * h * 0.65)

        for idx, (lvl, lx1, ly1, lx2, ly2) in enumerate(cota_dict.get("lines", [])):
            dwg.draw.level = int(lvl)
            dwg.draw.color = -1
            if estender_linha and idx == 0 and int(lvl) == 221:
                if orient == "H" and abs(ly1 - ly2) < 0.5:
                    xmin_l = min(lx1, lx2, novo_x - 1.0)
                    xmax_l = max(lx1, lx2, novo_x + larg_txt + 1.0)
                    lx1, lx2 = xmin_l, xmax_l
                elif orient == "V" and abs(lx1 - lx2) < 0.5:
                    ymin_l = min(ly1, ly2, novo_y - 1.0)
                    ymax_l = max(ly1, ly2, novo_y + larg_txt + 1.0)
                    ly1, ly2 = ymin_l, ymax_l
            dwg.draw.Line(float(lx1), float(ly1), float(lx2), float(ly2))

        dwg.draw.level = 216
        dwg.draw.color = 3
        dwg.draw.Text(float(novo_x), float(novo_y), h, float(cota_dict.get("ang", 0.0)), texto)
    finally:
        dwg.draw.level = old_lvl
        dwg.draw.color = old_col

    cota_dict["tipo"] = "TEXT"
    cota_dict["x"] = float(novo_x)
    cota_dict["y"] = float(novo_y)
    cota_dict["bbox_texto"] = _bbox_texto(
        float(novo_x), float(novo_y), float(cota_dict.get("h", 10.0)), float(cota_dict.get("ang", 0.0)), str(cota_dict.get("texto", ""))
    )
    return True


def _organizar_cotas_apertadas(dwg):
    """
    Corrige a posicao do texto de cotas em vaos estreitos (< 40 cm, ex: 8.5, 12.5),
    onde o TQS joga o texto para fora/esquerda em cima da cota vizinha (ex: 115 ou 75).
    Posiciona o texto exatamente dentro do espacinho da cota (ou logo apos o primeiro tick),
    preservando 100% a cota vizinha maior como cota IPOCOT real e interativa.
    """
    cotas = coletar_cotas_existentes(dwg, nivel_cota=216)
    if not cotas:
        return 0

    ajustadas = 0
    for c in cotas:
        if c.get("tipo") != "IPOCOT":
            continue
        p1 = c.get("p1")
        p2 = c.get("p2")
        if p1 is None or p2 is None:
            continue
        span = abs(p2 - p1)
        if span >= 40.0:
            continue

        orient = c.get("orient", "H")
        kicked_out = False
        if orient == "H":
            if c["x"] < (p1 - 1.0) or c["x"] > (p2 + 1.0):
                kicked_out = True
        else:
            if c["y"] < (p1 - 1.0) or c["y"] > (p2 + 1.0):
                kicked_out = True

        if not kicked_out:
            continue

        txt = str(c.get("texto", ""))
        h = float(c.get("h", 10.0))
        larg_txt = max(h * 0.6, (len(txt) - 0.2) * h * 0.5)
        meio = 0.5 * (p1 + p2)

        if orient == "H":
            # No vao estreito, posiciona o texto no espacinho entre p1 e p2
            # garantindo que nao invada a cota a esquerda (>= p1 + 0.8)
            if span <= larg_txt:
                novo_x = p1 + 0.8
            else:
                novo_x = meio - 0.5 * larg_txt
            novo_y = c["y"]
        else:
            if span <= larg_txt:
                novo_y = p1 + 0.8
            else:
                novo_y = meio - 0.5 * larg_txt
            novo_x = c["x"]

        if _substituir_ipocot_por_primitivos(dwg, c, novo_x, novo_y, estender_linha=True):
            ajustadas += 1

    return ajustadas


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
        elif c.get("texto"):
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


def cotar_cadeia_horizontal(dwg, pontos_x, y_ref, y_cota, cotas_existentes=None, tolerancia=0.5, arredondar_valores=False):
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

        criar_dim_horizontal(dwg, x1, y_ref, x2, y_ref, 0.5 * (x1 + x2), y_cota, arredondar=arredondar_valores)
        _registrar_cota_em_memoria(cotas_existentes, "H", x1, x2, y_cota)
        criadas += 1

    return criadas


def cotar_cadeia_vertical(dwg, pontos_y, x_ref, x_cota, cotas_existentes=None, tolerancia=0.5, arredondar_valores=False):
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

        criar_dim_vertical(dwg, x_ref, y1, x_ref, y2, x_cota, 0.5 * (y1 + y2), arredondar=arredondar_valores)
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
    cotas_existentes=None,
    arredondar_valores=False
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
            total_criadas += cotar_cadeia_horizontal(dwg, pontos_parciais, y_ref, y_max + off1, cotas_existentes, arredondar_valores=arredondar_valores)
        if pontos_eixos:
            total_criadas += cotar_cadeia_horizontal(dwg, pontos_eixos, y_ref, y_max + off2, cotas_existentes, arredondar_valores=arredondar_valores)
        if incluir_total:
            y_tot = y_max + off3
            if not (cotas_existentes is not None and cota_ja_existe(x_min, x_max, cotas_existentes, orient="H", pos_linha=y_tot)):
                criar_dim_horizontal(dwg, x_min, y_ref, x_max, y_ref, 0.5 * (x_min + x_max), y_tot, arredondar=arredondar_valores)
                _registrar_cota_em_memoria(cotas_existentes, "H", x_min, x_max, y_tot)
                total_criadas += 1

    elif lado_upper == "BASE":
        y_ref = y_min
        if pontos_parciais:
            total_criadas += cotar_cadeia_horizontal(dwg, pontos_parciais, y_ref, y_min - off1, cotas_existentes, arredondar_valores=arredondar_valores)
        if pontos_eixos:
            total_criadas += cotar_cadeia_horizontal(dwg, pontos_eixos, y_ref, y_min - off2, cotas_existentes, arredondar_valores=arredondar_valores)
        if incluir_total:
            y_tot = y_min - off3
            if not (cotas_existentes is not None and cota_ja_existe(x_min, x_max, cotas_existentes, orient="H", pos_linha=y_tot)):
                criar_dim_horizontal(dwg, x_min, y_ref, x_max, y_ref, 0.5 * (x_min + x_max), y_tot, arredondar=arredondar_valores)
                _registrar_cota_em_memoria(cotas_existentes, "H", x_min, x_max, y_tot)
                total_criadas += 1

    elif lado_upper == "ESQUERDA":
        x_ref = x_min
        if pontos_parciais:
            total_criadas += cotar_cadeia_vertical(dwg, pontos_parciais, x_ref, x_min - off1, cotas_existentes, arredondar_valores=arredondar_valores)
        if pontos_eixos:
            total_criadas += cotar_cadeia_vertical(dwg, pontos_eixos, x_ref, x_min - off2, cotas_existentes, arredondar_valores=arredondar_valores)
        if incluir_total:
            x_tot = x_min - off3
            if not (cotas_existentes is not None and cota_ja_existe(y_min, y_max, cotas_existentes, orient="V", pos_linha=x_tot)):
                criar_dim_vertical(dwg, x_ref, y_min, x_ref, y_max, x_tot, 0.5 * (y_min + y_max), arredondar=arredondar_valores)
                _registrar_cota_em_memoria(cotas_existentes, "V", y_min, y_max, x_tot)
                total_criadas += 1

    elif lado_upper == "DIREITA":
        x_ref = x_max
        if pontos_parciais:
            total_criadas += cotar_cadeia_vertical(dwg, pontos_parciais, x_ref, x_max + off1, cotas_existentes, arredondar_valores=arredondar_valores)
        if pontos_eixos:
            total_criadas += cotar_cadeia_vertical(dwg, pontos_eixos, x_ref, x_max + off2, cotas_existentes, arredondar_valores=arredondar_valores)
        if incluir_total:
            x_tot = x_max + off3
            if not (cotas_existentes is not None and cota_ja_existe(y_min, y_max, cotas_existentes, orient="V", pos_linha=x_tot)):
                criar_dim_vertical(dwg, x_ref, y_min, x_ref, y_max, x_tot, 0.5 * (y_min + y_max), arredondar=arredondar_valores)
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
        offsets=(40.0, 64.0, 99.4),
        arredondar_valores=False
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
            cotas_existentes=self.cotas_existentes,
            arredondar_valores=arredondar_valores
        )

    def cotar_forma(self, organizar_textos=True, arredondar_valores=True):
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
            self.dwg, pts_x_todos, y_linha_h, y_linha_h, self.cotas_existentes, arredondar_valores=arredondar_valores
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
            self.dwg, pts_y_todos, x_linha_v_dir, x_linha_v_dir, self.cotas_existentes, arredondar_valores=arredondar_valores
        )

        # ---------------------------------------------------------------------
        # 2. CADEIA VERTICAL INTERNA ESQUERDA (JUNTO AO 1o PILAR INTERNO)
        # ---------------------------------------------------------------------
        if len(pts_x_pilares) >= 4:
            x_pilar_esq_int = pts_x_pilares[2]  # face direita do pilar esquerdo (ex: 150.5)
            x_linha_v_esq = x_pilar_esq_int + 32.4  # ex: 182.9
            if abs(x_linha_v_esq - x_linha_v_dir) > 60.0:
                total_criadas += cotar_cadeia_vertical(
                    self.dwg, pts_y_todos, x_linha_v_esq, x_linha_v_esq, self.cotas_existentes, arredondar_valores=arredondar_valores
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
                    self.dwg, pts_y_bordas, x_bal_esq, x_bal_esq, self.cotas_existentes, arredondar_valores=arredondar_valores
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
                    self.dwg, pts_y_bordas, x_bal_dir, x_bal_dir, self.cotas_existentes, arredondar_valores=arredondar_valores
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
            offsets=(35.0, 64.1, 99.4),
            arredondar_valores=arredondar_valores
        )

        total_criadas += self.cotar_lado(
            lado="BASE",
            bbox_estrutura=bbox,
            pontos_parciais=None,
            pontos_eixos=None,
            incluir_total=True,
            offsets=(25.0, 35.0, 48.6),
            arredondar_valores=arredondar_valores
        )

        total_criadas += self.cotar_lado(
            lado="ESQUERDA",
            bbox_estrutura=bbox,
            pontos_parciais=None,
            pontos_eixos=None,
            incluir_total=True,
            offsets=(25.0, 40.0, 56.5),
            arredondar_valores=arredondar_valores
        )

        total_criadas += self.cotar_lado(
            lado="DIREITA",
            bbox_estrutura=bbox,
            pontos_parciais=None,
            pontos_eixos=None,
            incluir_total=True,
            offsets=(25.0, 40.0, 50.4),
            arredondar_valores=arredondar_valores
        )

        # ---------------------------------------------------------------------
        # 5. REORGANIZAR COTAS APERTADAS E TEXTOS PARA ELIMINAR SOBREPOSICOES
        # ---------------------------------------------------------------------
        _organizar_cotas_apertadas(self.dwg)
        if arredondar_valores:
            aplicar_arredondamento_cotas(self.dwg)
        self.cotas_existentes = coletar_cotas_existentes(self.dwg)
        if organizar_textos:
            organizar_textos_sem_sobreposicao(self.dwg, geo=geo, cotas=self.cotas_existentes)

        return total_criadas

    def cotar_forma_completa(self, organizar_textos=False, arredondar_valores=True):
        """
        Executa a cotagem externa em camadas e interna por completo da planta de formas.
        """
        return self.cotar_forma(organizar_textos=organizar_textos, arredondar_valores=arredondar_valores)

    def cotar_pilares_quadrados(
        self,
        incluir_cadeia_horizontal=True,
        incluir_cotas_capitel=True,
        incluir_pilares_laterais=True,
        arredondar_valores=True
    ):
        """
        Identifica automaticamente os pilares que estao dentro dos quadrados amarelos
        (capiteis/macicos no Nivel 207, ignorando pilares soltos nas bordas) e gera:
          1. Cadeia horizontal continua comecando la do inicio horizontal (vigas de borda/apoio)
             e passando pelas faces dos pilares dos quadrados ao longo de cada alinhamento.
          2. Cotas locais de cada quadrado/capitel (distancias do pilar ate as faces do
             quadrado, folga ate as cubetas e abertura total entre cubetas na horizontal e vertical).
          3. Cotas dos pilares laterais de borda: o quanto ele se sobressai da viga e a
             distancia entre eles ao longo da viga (com cota da face de contato do pilar).
        """
        self.configurar_estilo()

        quadrados_207 = []
        pilares_poly = []
        vigas_vert = []
        vigas_horiz = []
        cubetas = []
        textos_pilar = []

        self.dwg.iterator.Begin()
        while True:
            tipo = self.dwg.iterator.Next()
            if tipo == TQSDwg.DWGTYPE_EOF:
                break

            nivel = self.dwg.iterator.level
            if self.dwg.iterator.inBlock != 0:
                if tipo == TQSDwg.DWGTYPE_POLYLINE and nivel == 208:
                    pts = [self.dwg.iterator.GetPolylinePt(i) for i in range(self.dwg.iterator.xySize)]
                    if pts:
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        cubetas.append((min(xs), min(ys), max(xs), max(ys)))
                continue

            if tipo == TQSDwg.DWGTYPE_POLYLINE:
                pts = [self.dwg.iterator.GetPolylinePt(i) for i in range(self.dwg.iterator.xySize)]
                if not pts:
                    continue
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                bx = (min(xs), min(ys), max(xs), max(ys))
                dx_b = bx[2] - bx[0]
                dy_b = bx[3] - bx[1]

                if nivel == 207 and len(pts) >= 4 and 80.0 <= dx_b <= 600.0 and 80.0 <= dy_b <= 600.0:
                    quadrados_207.append((bx, pts))
                elif nivel in (3, 4, 5) and len(pts) >= 4 and 8.0 <= dx_b <= 250.0 and 8.0 <= dy_b <= 250.0:
                    pilares_poly.append((nivel, bx, pts))
                elif nivel in (1, 2, 201):
                    for k in range(len(pts) - 1):
                        x1, y1 = pts[k]
                        x2, y2 = pts[k + 1]
                        dy = abs(y2 - y1)
                        dx = abs(x2 - x1)
                        if dy >= 15.0 and dx <= 0.15 * dy:
                            vigas_vert.append((x1, y1, x2, y2, nivel))
                        elif dx >= 15.0 and dy <= 0.15 * dx:
                            vigas_horiz.append((x1, y1, x2, y2, nivel))
            elif tipo == TQSDwg.DWGTYPE_LINE and nivel in (1, 2, 201):
                x1, y1 = self.dwg.iterator.x1, self.dwg.iterator.y1
                x2, y2 = self.dwg.iterator.x2, self.dwg.iterator.y2
                dy = abs(y2 - y1)
                dx = abs(x2 - x1)
                if dy >= 15.0 and dx <= 0.15 * dy:
                    vigas_vert.append((x1, y1, x2, y2, nivel))
                elif dx >= 15.0 and dy <= 0.15 * dx:
                    vigas_horiz.append((x1, y1, x2, y2, nivel))
            elif tipo == TQSDwg.DWGTYPE_TEXT and nivel in (9, 12):
                textos_pilar.append((
                    nivel,
                    self.dwg.iterator.text.strip(),
                    self.dwg.iterator.x1,
                    self.dwg.iterator.y1,
                    self.dwg.iterator.textHeight,
                ))

        def _faces_exatas_pilar(pts):
            return CotadorFormas._faces_exatas_pilar(pts)

        # Associa cada quadrado amarelo (Nivel 207) ao pilar interno (ignorando pilares soltos)
        capiteis = []
        for sq_bx, sq_pts in quadrados_207:
            sx1, sy1, sx2, sy2 = sq_bx
            scx = 0.5 * (sx1 + sx2)
            scy = 0.5 * (sy1 + sy2)
            melhor_pilar = None
            menor_d = float("inf")
            for _, pbx, ppts in pilares_poly:
                pcx = 0.5 * (pbx[0] + pbx[2])
                pcy = 0.5 * (pbx[1] + pbx[3])
                if sx1 <= pcx <= sx2 and sy1 <= pcy <= sy2:
                    d = math.hypot(pcx - scx, pcy - scy)
                    if d < menor_d:
                        menor_d = d
                        melhor_pilar = _faces_exatas_pilar(ppts)

            if melhor_pilar is not None:
                txs = [
                    t for t in textos_pilar
                    if (sx1 - 30.0) <= t[2] <= (sx2 + 30.0) and (sy1 - 30.0) <= t[3] <= (sy2 + 30.0)
                ]
                y_txt_min = min(t[3] for t in txs) if txs else melhor_pilar[1]
                capiteis.append({
                    "sq": sq_bx,
                    "pilar": melhor_pilar,
                    "y_txt_min": y_txt_min,
                })

        total_criadas = 0
        criadas_capitel = 0

        # Agrupa os quadrados em linhas horizontais (mesma faixa Y, tolerancia 200 cm)
        capiteis_ord = sorted(capiteis, key=lambda c: -0.5 * (c["sq"][1] + c["sq"][3]))
        linhas_capiteis = []
        for c in capiteis_ord:
            cy = 0.5 * (c["sq"][1] + c["sq"][3])
            if not linhas_capiteis or abs(cy - linhas_capiteis[-1]["cy"]) > 200.0:
                linhas_capiteis.append({"cy": cy, "caps": [c]})
            else:
                linhas_capiteis[-1]["caps"].append(c)
                linhas_capiteis[-1]["cy"] = (
                    sum(0.5 * (x["sq"][1] + x["sq"][3]) for x in linhas_capiteis[-1]["caps"])
                    / float(len(linhas_capiteis[-1]["caps"]))
                )

        for row in linhas_capiteis:
            caps_row = row["caps"]
            y_cota_row = min(c["y_txt_min"] for c in caps_row) - 18.0
            row["y_cota"] = y_cota_row
            for c in caps_row:
                c["y_cota_row"] = y_cota_row

        # ---------------------------------------------------------------------
        # 1. COTAS LOCAIS DE CADA QUADRADO / CAPITEL (PADRAO IMAGEM 2)
        # ---------------------------------------------------------------------
        if incluir_cotas_capitel:
            for c in capiteis:
                sx1, sy1, sx2, sy2 = c["sq"]
                px1, py1, px2, py2 = c["pilar"]
                y_cota_r = c.get("y_cota_row", c["y_txt_min"] - 18.0)

                c_esq = [
                    cb[2] for cb in cubetas
                    if not (cb[3] < sy1 + 45.0 or cb[1] > sy2 - 45.0) and (sx1 - 120.0) <= cb[2] <= (sx1 + 0.5)
                ]
                c_dir = [
                    cb[0] for cb in cubetas
                    if not (cb[3] < sy1 + 45.0 or cb[1] > sy2 - 45.0) and (sx2 - 0.5) <= cb[0] <= (sx2 + 120.0)
                ]
                c_inf = [
                    cb[3] for cb in cubetas
                    if not (cb[2] < sx1 + 45.0 or cb[0] > sx2 - 45.0) and (sy1 - 120.0) <= cb[3] <= (sy1 + 0.5)
                ]
                c_sup = [
                    cb[1] for cb in cubetas
                    if not (cb[2] < sx1 + 45.0 or cb[0] > sx2 - 45.0) and (sy2 - 0.5) <= cb[1] <= (sy2 + 120.0)
                ]

                xe = max(c_esq) if c_esq else None
                xd = min(c_dir) if c_dir else None
                yi = max(c_inf) if c_inf else None
                ys = min(c_sup) if c_sup else None

                # A) Cotas verticais a esquerda do pilar (109.9 | 110.1, 334.2 e 37.7)
                x_v1 = px1 - 22.0
                if (py1 - sy1) >= 2.0 and not cota_ja_existe(sy1, py1, self.cotas_existentes, orient="V", pos_linha=x_v1, tol_linha=12.0):
                    criar_dim_vertical(self.dwg, px1, sy1, px1, py1, x_v1, 0.5 * (sy1 + py1), arredondar=arredondar_valores)
                    _registrar_cota_em_memoria(self.cotas_existentes, "V", sy1, py1, x_v1)
                    total_criadas += 1

                if (sy2 - py2) >= 2.0 and not cota_ja_existe(py2, sy2, self.cotas_existentes, orient="V", pos_linha=x_v1, tol_linha=12.0):
                    criar_dim_vertical(self.dwg, px1, py2, px1, sy2, x_v1, 0.5 * (py2 + sy2), arredondar=arredondar_valores)
                    _registrar_cota_em_memoria(self.cotas_existentes, "V", py2, sy2, x_v1)
                    total_criadas += 1

                x_v2 = px1 - 52.0
                if yi is not None and ys is not None and (ys - yi) >= 10.0:
                    if not cota_ja_existe(yi, ys, self.cotas_existentes, orient="V", pos_linha=x_v2, tol_linha=12.0):
                        criar_dim_vertical(self.dwg, x_v2, yi, x_v2, ys, x_v2, 0.5 * (yi + ys), arredondar=arredondar_valores)
                        _registrar_cota_em_memoria(self.cotas_existentes, "V", yi, ys, x_v2)
                        total_criadas += 1

                x_v3 = sx1 + 12.0
                if ys is not None and (ys - sy2) >= 2.0:
                    if not cota_ja_existe(sy2, ys, self.cotas_existentes, orient="V", pos_linha=x_v3, tol_linha=12.0):
                        criar_dim_vertical(self.dwg, sx1, sy2, sx1, ys, x_v3, 0.5 * (sy2 + ys), arredondar=arredondar_valores)
                        _registrar_cota_em_memoria(self.cotas_existentes, "V", sy2, ys, x_v3)
                        total_criadas += 1

                # B) Cotas horizontais locais do quadrado (115.1 | 47.1 e 334.3)
                y_h1 = min(c["y_txt_min"] - 14.0, py1 - 48.0)
                if incluir_cadeia_horizontal and abs(y_h1 - y_cota_r) < 18.0:
                    y_h1 = y_cota_r - 20.0

                if (sx2 - px2) >= 2.0 and not cota_ja_existe(px2, sx2, self.cotas_existentes, orient="H", pos_linha=y_h1, tol_linha=12.0):
                    criar_dim_horizontal(self.dwg, px2, py1, sx2, y_h1, 0.5 * (px2 + sx2), y_h1, arredondar=arredondar_valores)
                    _registrar_cota_em_memoria(self.cotas_existentes, "H", px2, sx2, y_h1)
                    total_criadas += 1

                if xd is not None and (xd - sx2) >= 2.0:
                    if not cota_ja_existe(sx2, xd, self.cotas_existentes, orient="H", pos_linha=y_h1, tol_linha=12.0):
                        criar_dim_horizontal(self.dwg, sx2, y_h1, xd, y_h1, 0.5 * (sx2 + xd), y_h1, arredondar=arredondar_valores)
                        _registrar_cota_em_memoria(self.cotas_existentes, "H", sx2, xd, y_h1)
                        total_criadas += 1

                y_h2 = sy1 + 14.0
                if incluir_cadeia_horizontal and abs(y_h2 - y_cota_r) < 18.0:
                    y_h2 = min(sy1 + 10.0, y_cota_r - 20.0)
                if abs(y_h2 - y_h1) < 18.0:
                    y_h2 = y_h1 - 20.0

                if xe is not None and xd is not None and (xd - xe) >= 10.0:
                    if not cota_ja_existe(xe, xd, self.cotas_existentes, orient="H", pos_linha=y_h2, tol_linha=12.0):
                        criar_dim_horizontal(self.dwg, xe, y_h2, xd, y_h2, 0.5 * (xe + xd), y_h2, arredondar=arredondar_valores)
                        _registrar_cota_em_memoria(self.cotas_existentes, "H", xe, xd, y_h2)
                        total_criadas += 1

        # ---------------------------------------------------------------------
        # 2. CADEIA HORIZONTAL CONTINUA DO INICIO HORIZONTAL PASSANDO PELOS PILARES (IMAGENS 3 E 4)
        # ---------------------------------------------------------------------
        if incluir_cadeia_horizontal:
            for row in linhas_capiteis:
                caps = sorted(row["caps"], key=lambda c: c["sq"][0])
                y_cota = row["y_cota"]

                pts_chain = []
                # Vigas verticais de borda/apoio que cruzam a linha horizontal y_cota (inicio horizontal ate o fim)
                for x1, y1, x2, y2, _ in vigas_vert:
                    ymin_v = min(y1, y2)
                    ymax_v = max(y1, y2)
                    if (ymin_v - 10.0) <= y_cota <= (ymax_v + 10.0):
                        x_at = x1 + (y_cota - y1) / (y2 - y1) * (x2 - x1) if abs(y2 - y1) > 0.1 else x1
                        pts_chain.append((x_at, y_cota, "viga"))

                # Faces esquerda e direita dos pilares dentro dos quadrados desta linha
                for c in caps:
                    px1, py1, px2, py2 = c["pilar"]
                    pts_chain.append((px1, py1, "pilar_esq"))
                    pts_chain.append((px2, py1, "pilar_dir"))

                pts_chain.sort(key=lambda item: item[0])

                # Remove pontos duplicados (< 1.0 cm), priorizando o ponto do pilar
                filtrados = []
                for pt in pts_chain:
                    if not filtrados or abs(pt[0] - filtrados[-1][0]) >= 1.0:
                        filtrados.append(pt)
                    elif pt[2].startswith("pilar") and filtrados[-1][2] == "viga":
                        filtrados[-1] = pt

                for i in range(len(filtrados) - 1):
                    x1, y1, t1 = filtrados[i]
                    x2, y2, t2 = filtrados[i + 1]
                    # Ignora frestas de junta de dilatacao (< 5.0 cm)
                    if (x2 - x1) < 5.0:
                        continue

                    if cota_ja_existe(x1, x2, self.cotas_existentes, orient="H", pos_linha=y_cota, tol_linha=12.0):
                        continue

                    if t1 == "pilar_esq" and t2 == "pilar_dir":
                        yr1, yr2 = y1, y2
                    else:
                        yr1, yr2 = y_cota, y_cota

                    dx = x2 - x1
                    x1_d, x2_d = x1, x2
                    if 19.85 <= dx < 20.02 or 29.85 <= dx < 30.02 or 39.85 <= dx < 40.02:
                        x1_d -= 0.015
                        x2_d += 0.015

                    criar_dim_horizontal(self.dwg, x1_d, yr1, x2_d, yr2, 0.5 * (x1_d + x2_d), y_cota, arredondar=arredondar_valores)
                    _registrar_cota_em_memoria(self.cotas_existentes, "H", x1, x2, y_cota)
                    total_criadas += 1

        # ---------------------------------------------------------------------
        # 3. COTAS DOS PILARES LATERAIS (CADEIA EXTERNA ENCADEADA NO CONTORNO)
        # ---------------------------------------------------------------------
        criadas_capitel = total_criadas
        if criadas_capitel > 0:
            _organizar_cotas_apertadas(self.dwg)
            if arredondar_valores:
                aplicar_arredondamento_cotas(self.dwg)
            self.cotas_existentes = coletar_cotas_existentes(self.dwg)

        if incluir_pilares_laterais:
            total_criadas += self.cotar_pilares_laterais(arredondar_valores=arredondar_valores)

        return total_criadas

    def cotar_pilares_laterais(self, arredondar_valores=True):
        """
        Gera cadeias encadeadas de cotas externas para todos os pilares do contorno
        exterior da planta (esquerda, direita, topo e base), alternando a medida do
        proprio pilar e o vao livre ate o proximo pilar em sequencia.
        Funciona em qualquer planta de formas (com ou sem quadrados/capiteis) e
        calcula automaticamente um afastamento externo livre de sobreposicoes.
        """
        self.configurar_estilo()
        self.cotas_existentes = coletar_cotas_existentes(self.dwg)

        # 1. Identifica eventual quadro de "DETALHE MUDANCA DE SECAO DE PILARES" para ignora-lo
        titulos_det = []
        quadros_200 = []
        self.dwg.iterator.Begin()
        while True:
            tipo = self.dwg.iterator.Next()
            if tipo == TQSDwg.DWGTYPE_EOF:
                break
            if self.dwg.iterator.inBlock != 0:
                continue
            lvl = self.dwg.iterator.level
            if tipo == TQSDwg.DWGTYPE_TEXT:
                s = (self.dwg.iterator.text or "").strip().upper()
                if "DETALHE MUDANCA DE SECAO DE PILARES" in s:
                    titulos_det.append((self.dwg.iterator.x1, self.dwg.iterator.y1))
            elif tipo == TQSDwg.DWGTYPE_POLYLINE and lvl == 200:
                pts = [self.dwg.iterator.GetPolylinePt(i) for i in range(self.dwg.iterator.xySize)]
                if len(pts) >= 4:
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    quadros_200.append((min(xs), min(ys), max(xs), max(ys)))

        caixas_ignorar = []
        for tx, ty in titulos_det:
            for qx1, qy1, qx2, qy2 in quadros_200:
                if (qx1 - 20.0) <= tx <= (qx2 + 20.0) and (qy1 - 20.0) <= ty <= (qy2 + 20.0):
                    caixas_ignorar.append((qx1 - 10.0, qy1 - 10.0, qx2 + 10.0, qy2 + 10.0))

        def _dentro_ignorar(x, y):
            return any(ix1 <= x <= ix2 and iy1 <= y <= iy2 for ix1, iy1, ix2, iy2 in caixas_ignorar)

        # 2. Coleta pilares, segmentos de concreto/laje, textos e blocos de corte
        pilares_raw = []
        segs_concreto = []
        boxes_pilares = []
        boxes_textos = []

        self.dwg.iterator.Begin()
        while True:
            tipo = self.dwg.iterator.Next()
            if tipo == TQSDwg.DWGTYPE_EOF:
                break
            if self.dwg.iterator.inBlock != 0:
                continue
            lvl = self.dwg.iterator.level

            if tipo == TQSDwg.DWGTYPE_POLYLINE:
                pts = [self.dwg.iterator.GetPolylinePt(i) for i in range(self.dwg.iterator.xySize)]
                if not pts:
                    continue
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                bx = (min(xs), min(ys), max(xs), max(ys))
                if _dentro_ignorar(0.5 * (bx[0] + bx[2]), 0.5 * (bx[1] + bx[3])):
                    continue
                dx_b = bx[2] - bx[0]
                dy_b = bx[3] - bx[1]
                if lvl in (2, 3, 4, 5) and len(pts) >= 4 and 8.0 <= dx_b <= 450.0 and 8.0 <= dy_b <= 450.0:
                    faces = self._faces_exatas_pilar(pts)
                    pilares_raw.append(faces)
                    boxes_pilares.append(faces)
                if lvl in (1, 2, 3, 4, 5, 201, 237) and len(pts) >= 2:
                    for k in range(len(pts) - 1):
                        segs_concreto.append((pts[k][0], pts[k][1], pts[k + 1][0], pts[k + 1][1]))
            elif tipo == TQSDwg.DWGTYPE_LINE and lvl in (1, 2, 201, 237):
                x1, y1, x2, y2 = self.dwg.iterator.x1, self.dwg.iterator.y1, self.dwg.iterator.x2, self.dwg.iterator.y2
                if not _dentro_ignorar(0.5 * (x1 + x2), 0.5 * (y1 + y2)):
                    segs_concreto.append((x1, y1, x2, y2))
            elif tipo == TQSDwg.DWGTYPE_TEXT:
                txt = (self.dwg.iterator.text or "").strip()
                if txt and lvl != 216:
                    tx, ty = self.dwg.iterator.x1, self.dwg.iterator.y1
                    if not _dentro_ignorar(tx, ty):
                        boxes_textos.append(
                            _bbox_texto(tx, ty, self.dwg.iterator.textHeight, self.dwg.iterator.textAngle, txt)
                        )
            elif tipo == TQSDwg.DWGTYPE_BLOCK:
                bname = (self.dwg.iterator.blockName or "").upper()
                if "CORTE" in bname or "LINCOR" in bname:
                    bx_c, by_c = self.dwg.iterator.xc, self.dwg.iterator.yc
                    if not _dentro_ignorar(bx_c, by_c):
                        boxes_textos.append((bx_c - 30.0, by_c - 30.0, bx_c + 30.0, by_c + 30.0))

        # Deduplica poligonos de pilares sobrepostos (ex: pilar de mudanca de secao)
        pilares = []
        for pb in pilares_raw:
            if not any(
                abs(pb[0] - u[0]) < 2.0 and abs(pb[1] - u[1]) < 2.0
                and abs(pb[2] - u[2]) < 2.0 and abs(pb[3] - u[3]) < 2.0
                for u in pilares
            ):
                pilares.append(pb)

        if len(pilares) < 2:
            return 0

        def _seg_cruza_box(x1, y1, x2, y2, box):
            bx1, by1, bx2, by2 = box
            if max(x1, x2) < bx1 or min(x1, x2) > bx2 or max(y1, y2) < by1 or min(y1, y2) > by2:
                return False
            # Se algum ponto esta dentro, ou cruza a caixa (amostragem + clipping exato)
            if (bx1 <= x1 <= bx2 and by1 <= y1 <= by2) or (bx1 <= x2 <= bx2 and by1 <= y2 <= by2):
                return True
            dx = x2 - x1
            dy = y2 - y1
            t0, t1 = 0.0, 1.0
            for p_v, q_v in (
                (-dx, x1 - bx1),
                (dx, bx2 - x1),
                (-dy, y1 - by1),
                (dy, by2 - y1),
            ):
                if abs(p_v) < 1e-9:
                    if q_v < 0.0:
                        return False
                else:
                    r = q_v / p_v
                    if p_v < 0.0:
                        if r > t1:
                            return False
                        if r > t0:
                            t0 = r
                    else:
                        if r < t0:
                            return False
                        if r < t1:
                            t1 = r
            return t0 <= t1

        def _cota_ja_existe_lado_ext(a, b, orient, borda_ref, direcao):
            pmin, pmax = min(a, b), max(a, b)
            for c in self.cotas_existentes:
                if c.get("orient") != orient:
                    continue
                if c.get("p1") is None or c.get("p2") is None:
                    continue
                cmin = min(c["p1"], c["p2"])
                cmax = max(c["p1"], c["p2"])
                if abs(cmin - pmin) <= 2.5 and abs(cmax - pmax) <= 2.5:
                    delta = (c["pos_linha"] - borda_ref) * direcao
                    if -15.0 <= delta <= 400.0:
                        return True
            return False

        def _escolher_pos_externa(orient, direcao, borda_ref, s_min, s_max):
            # Distancia confortavel inicial: 55 cm para fora da borda externa local
            extras = (0.0, 20.0, 40.0, 65.0, 90.0, 120.0, 155.0, 195.0, 240.0, 290.0)
            candidatos = [borda_ref + direcao * (55.0 + d) for d in extras]

            melhor_pos = candidatos[0]
            menor_penalidade = float("inf")

            for pos_c in candidatos:
                if orient == "V":
                    # Texto da cota vertical fica a esquerda da linha (h=10 cm)
                    box_band = (pos_c - 15.0, s_min - 14.0, pos_c + 5.0, s_max + 14.0)
                    box_band_cota = (pos_c - 20.0, s_min - 14.0, pos_c + 14.0, s_max + 14.0)
                else:
                    # Texto da cota horizontal fica acima da linha (h=10 cm)
                    box_band = (s_min - 14.0, pos_c - 5.0, s_max + 14.0, pos_c + 15.0)
                    box_band_cota = (s_min - 14.0, pos_c - 14.0, s_max + 14.0, pos_c + 20.0)

                pen = 0
                for pb in boxes_pilares:
                    if _boxes_colidem(box_band, pb, margem=5.0):
                        pen += 100
                for x1, y1, x2, y2 in segs_concreto:
                    if _seg_cruza_box(x1, y1, x2, y2, box_band):
                        # Se for uma viga perpendicular de outra ala em L que se estende >300 cm para fora,
                        # nao empurra a cota indefinidamente para longe
                        if orient == "V":
                            ext_out = (max(x1, x2) - borda_ref) * direcao if direcao > 0 else (borda_ref - min(x1, x2))
                            eh_ala_perp = abs(y2 - y1) <= 15.0 and ext_out > 300.0
                        else:
                            ext_out = (max(y1, y2) - borda_ref) * direcao if direcao > 0 else (borda_ref - min(y1, y2))
                            eh_ala_perp = abs(x2 - x1) <= 15.0 and ext_out > 300.0
                        pen += 1 if eh_ala_perp else 50
                for tb in boxes_textos:
                    if _boxes_colidem(box_band, tb, margem=4.0):
                        pen += 20
                for c in self.cotas_existentes:
                    btxt = c.get("bbox_texto")
                    if btxt and _boxes_colidem(box_band, btxt, margem=4.0):
                        pen += 25
                    for ln in c.get("lines", []):
                        _, lx1, ly1, lx2, ly2 = ln
                        if abs(lx1 - lx2) < 0.05 and abs(ly1 - ly2) < 0.05:
                            continue
                        if _seg_cruza_box(lx1, ly1, lx2, ly2, box_band_cota):
                            pen += 30
                    if c.get("orient") == orient and c.get("p1") is not None and c.get("p2") is not None:
                        cmin = min(c["p1"], c["p2"])
                        cmax = max(c["p1"], c["p2"])
                        if not (cmax < s_min - 10.0 or cmin > s_max + 10.0):
                            if abs(c["pos_linha"] - pos_c) < 28.0:
                                pen += 30

                if pen == 0:
                    return pos_c
                if pen < menor_penalidade:
                    menor_penalidade = pen
                    melhor_pos = pos_c

            return melhor_pos

        total_criadas = 0
        tol_alin = 120.0

        configs_lados = (
            # (nome, orient, direcao, reverse_ext)
            ("ESQ", "V", -1.0, False),
            ("DIR", "V", 1.0, True),
            ("SUP", "H", 1.0, True),
            ("INF", "H", -1.0, False),
        )

        for lado, orient, direcao, reverse_ext in configs_lados:
            if lado == "ESQ":
                key_ext = lambda p: p[0]
                span_fn = lambda p: (p[1], p[3])
            elif lado == "DIR":
                key_ext = lambda p: p[2]
                span_fn = lambda p: (p[1], p[3])
            elif lado == "SUP":
                key_ext = lambda p: p[3]
                span_fn = lambda p: (p[0], p[2])
            else:
                key_ext = lambda p: p[1]
                span_fn = lambda p: (p[0], p[2])

            ordenados = sorted(pilares, key=key_ext, reverse=reverse_ext)
            grupos = []
            for p in ordenados:
                v = key_ext(p)
                alocado = False
                for g in grupos:
                    if abs(v - g["ref"]) <= tol_alin:
                        g["pilares"].append(p)
                        alocado = True
                        break
                if not alocado:
                    grupos.append({"ref": v, "pilares": [p]})

            # Varredura de sombra do mais externo para o mais interno (filtra apenas contorno)
            sombras = []
            cadeias = []
            for g in grupos:
                visiveis = []
                for p in g["pilares"]:
                    a, b = span_fn(p)
                    mid = 0.5 * (a + b)
                    if not any((smin - 5.0) <= mid <= (smax + 5.0) for smin, smax in sombras):
                        visiveis.append(p)

                novas = []
                if len(visiveis) >= 2:
                    visiveis.sort(key=lambda p: span_fn(p)[0])
                    # Remove pilares paralelos no mesmo trecho (ex: junta de dilatacao lado a lado no outro eixo),
                    # mantendo o mais externo
                    vis_seq = []
                    for p in visiveis:
                        a_p, b_p = span_fn(p)
                        if vis_seq:
                            a_ant, b_ant = span_fn(vis_seq[-1])
                            if a_p < b_ant - 2.0 and b_p > a_ant + 2.0:
                                # Sobrepoe longitudinalmente -> mantem apenas o mais externo
                                if (key_ext(p) - key_ext(vis_seq[-1])) * direcao > 0.0:
                                    vis_seq[-1] = p
                                continue
                        vis_seq.append(p)

                    if len(vis_seq) >= 2:
                        sub = [vis_seq[0]]
                        for p in vis_seq[1:]:
                            meio_vao = 0.5 * (span_fn(sub[-1])[1] + span_fn(p)[0])
                            if any((smin + 10.0) < meio_vao < (smax - 10.0) for smin, smax in sombras):
                                if len(sub) >= 2:
                                    novas.append(sub)
                                sub = [p]
                            else:
                                sub.append(p)
                        if len(sub) >= 2:
                            novas.append(sub)

                    for c in novas:
                        cadeias.append(c)
                        sombras.append((min(span_fn(p)[0] for p in c), max(span_fn(p)[1] for p in c)))
                    if not novas and len(vis_seq) == 1:
                        a, b = span_fn(vis_seq[0])
                        sombras.append((a, b))
                elif len(visiveis) == 1:
                    a, b = span_fn(visiveis[0])
                    sombras.append((a, b))

            # Para cada cadeia externa do contorno, posiciona por fora e gera as cotas encadeadas
            for cadeia in cadeias:
                s_min = min(span_fn(p)[0] for p in cadeia)
                s_max = max(span_fn(p)[1] for p in cadeia)
                if direcao < 0:
                    face_ext = min(key_ext(p) for p in cadeia)
                else:
                    face_ext = max(key_ext(p) for p in cadeia)

                # Considera balancos/sacadas/vigas ate 250 cm fora da face dos pilares desta cadeia
                borda_local = face_ext
                for x1, y1, x2, y2 in segs_concreto:
                    if orient == "V":
                        seg_s1, seg_s2 = min(y1, y2), max(y1, y2)
                        ov = min(seg_s2, s_max) - max(seg_s1, s_min)
                        if ov < 25.0:
                            continue
                        val_ext = min(x1, x2) if direcao < 0 else max(x1, x2)
                    else:
                        seg_s1, seg_s2 = min(x1, x2), max(x1, x2)
                        ov = min(seg_s2, s_max) - max(seg_s1, s_min)
                        if ov < 25.0:
                            continue
                        val_ext = min(y1, y2) if direcao < 0 else max(y1, y2)

                    dist_fora = (val_ext - face_ext) * direcao
                    if 0.0 < dist_fora <= 250.0:
                        if (val_ext - borda_local) * direcao > 0.0:
                            borda_local = val_ext

                pos_c = _escolher_pos_externa(orient, direcao, borda_local, s_min, s_max)

                # Gera cadeia continua: pilar_0 -> vao_0_1 -> pilar_1 -> ... -> pilar_n
                for idx, p in enumerate(cadeia):
                    a_i, b_i = span_fn(p)
                    ref_i = key_ext(p)

                    # 1) Medida do proprio pilar
                    if (b_i - a_i) >= 3.0 and not _cota_ja_existe_lado_ext(a_i, b_i, orient, borda_local, direcao):
                        if orient == "V":
                            criar_dim_vertical(
                                self.dwg, ref_i, a_i, ref_i, b_i, pos_c, 0.5 * (a_i + b_i),
                                arredondar=arredondar_valores,
                            )
                            boxes_textos.append((pos_c - 14.0, a_i, pos_c + 2.0, b_i))
                        else:
                            criar_dim_horizontal(
                                self.dwg, a_i, ref_i, b_i, ref_i, 0.5 * (a_i + b_i), pos_c,
                                arredondar=arredondar_valores,
                            )
                            boxes_textos.append((a_i, pos_c - 2.0, b_i, pos_c + 14.0))
                        _registrar_cota_em_memoria(self.cotas_existentes, orient, a_i, b_i, pos_c)
                        total_criadas += 1

                    # 2) Distancia livre ate o proximo pilar (ignora fresta < 5 cm de junta de dilatacao)
                    if idx + 1 < len(cadeia):
                        p_next = cadeia[idx + 1]
                        a_next, _ = span_fn(p_next)
                        ref_next = key_ext(p_next)
                        if (a_next - b_i) >= 5.0 and not _cota_ja_existe_lado_ext(b_i, a_next, orient, borda_local, direcao):
                            if orient == "V":
                                criar_dim_vertical(
                                    self.dwg, ref_i, b_i, ref_next, a_next, pos_c, 0.5 * (b_i + a_next),
                                    arredondar=arredondar_valores,
                                )
                                boxes_textos.append((pos_c - 14.0, b_i, pos_c + 2.0, a_next))
                            else:
                                criar_dim_horizontal(
                                    self.dwg, b_i, ref_i, a_next, ref_next, 0.5 * (b_i + a_next), pos_c,
                                    arredondar=arredondar_valores,
                                )
                                boxes_textos.append((b_i, pos_c - 2.0, a_next, pos_c + 14.0))
                            _registrar_cota_em_memoria(self.cotas_existentes, orient, b_i, a_next, pos_c)
                            total_criadas += 1

        self.cotas_existentes = coletar_cotas_existentes(self.dwg)
        return total_criadas

    @staticmethod
    def _faces_exatas_pilar(pts):
        u_pts = (
            pts[:-1]
            if len(pts) > 1 and abs(pts[0][0] - pts[-1][0]) < 0.1 and abs(pts[0][1] - pts[-1][1]) < 0.1
            else pts
        )
        if len(u_pts) == 4:
            sx = sorted(u_pts, key=lambda p: p[0])
            sy = sorted(u_pts, key=lambda p: p[1])
            x_esq = 0.5 * (sx[0][0] + sx[1][0])
            x_dir = 0.5 * (sx[2][0] + sx[3][0])
            y_inf = 0.5 * (sy[0][1] + sy[1][1])
            y_sup = 0.5 * (sy[2][1] + sy[3][1])
            return (x_esq, y_inf, x_dir, y_sup)
        xs = [p[0] for p in u_pts]
        ys = [p[1] for p in u_pts]
        return (min(xs), min(ys), max(xs), max(ys))

    def cotar_detalhes(self, arredondar_valores=True):
        """
        Cota pequenos detalhes geometricos da forma (ressaltos/degraus entre pilares proximos
        e quanto um pilar passa de uma viga), usando fonte reduzida e posicionando
        as cotas SEMPRE fora dos poligonos dos pilares e sem sobrepor textos.
        """
        h_det = 6.0
        configurar_estilo_cotas(
            self.dwg,
            altura_texto=0.12,
            extensao_linha=0.12,
            extensao_chamada=0.12,
            folga_chamada=0.06,
            tamanho_tick=0.12,
        )

        pilares_poly = []
        vigas_vert = []
        vigas_horiz = []
        lajes_237_seg = []
        textos_obst = []

        try:
            self.dwg.iterator.Begin()
            while True:
                tipo = self.dwg.iterator.Next()
                if tipo == TQSDwg.DWGTYPE_EOF:
                    break
                if self.dwg.iterator.inBlock != 0:
                    continue
                nivel = self.dwg.iterator.level

                if tipo == TQSDwg.DWGTYPE_POLYLINE:
                    pts = [self.dwg.iterator.GetPolylinePt(i) for i in range(self.dwg.iterator.xySize)]
                    if not pts:
                        continue
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    bx = (min(xs), min(ys), max(xs), max(ys))
                    dx_b = bx[2] - bx[0]
                    dy_b = bx[3] - bx[1]
                    if nivel in (2, 3, 4, 5) and len(pts) >= 4 and 5.0 <= dx_b <= 450.0 and 5.0 <= dy_b <= 450.0:
                        pilares_poly.append((bx, self._faces_exatas_pilar(pts)))
                    elif nivel in (1, 2, 201, 237):
                        for k in range(len(pts) - 1):
                            x1, y1 = pts[k]
                            x2, y2 = pts[k + 1]
                            dy = abs(y2 - y1)
                            dx = abs(x2 - x1)
                            if nivel == 237:
                                if (dy >= 10.0 and dx <= 0.15 * dy) or (dx >= 10.0 and dy <= 0.15 * dx):
                                    lajes_237_seg.append((x1, y1, x2, y2))
                            else:
                                if dy >= 10.0 and dx <= 0.15 * dy:
                                    vigas_vert.append((x1, y1, x2, y2))
                                elif dx >= 10.0 and dy <= 0.15 * dx:
                                    vigas_horiz.append((x1, y1, x2, y2))
                elif tipo == TQSDwg.DWGTYPE_LINE and nivel in (1, 2, 201, 237):
                    x1, y1 = self.dwg.iterator.x1, self.dwg.iterator.y1
                    x2, y2 = self.dwg.iterator.x2, self.dwg.iterator.y2
                    dy = abs(y2 - y1)
                    dx = abs(x2 - x1)
                    if nivel == 237:
                        if (dy >= 10.0 and dx <= 0.15 * dy) or (dx >= 10.0 and dy <= 0.15 * dx):
                            lajes_237_seg.append((x1, y1, x2, y2))
                    else:
                        if dy >= 10.0 and dx <= 0.15 * dy:
                            vigas_vert.append((x1, y1, x2, y2))
                        elif dx >= 10.0 and dy <= 0.15 * dx:
                            vigas_horiz.append((x1, y1, x2, y2))
                elif tipo == TQSDwg.DWGTYPE_TEXT and nivel not in (28, 29, 122, 216):
                    textos_obst.append(_bbox_texto(
                        self.dwg.iterator.x1,
                        self.dwg.iterator.y1,
                        self.dwg.iterator.textHeight,
                        _normalizar_angulo(self.dwg.iterator.textAngle),
                        self.dwg.iterator.text.strip(),
                    ))

            if not pilares_poly:
                return 0

            boxes_pilares = [pbx for pbx, _ in pilares_poly]
            vigas_todas = vigas_vert + vigas_horiz
            cotas_det_boxes = []
            total_criadas = 0

            def _chamada_corta_texto_h(x_c, y_a, y_b):
                y_lo, y_hi = min(y_a, y_b) + 1.0, max(y_a, y_b) - 1.0
                if y_hi <= y_lo:
                    return False
                bx_ch = (x_c - 0.5, y_lo, x_c + 0.5, y_hi)
                return any(_boxes_colidem(bx_ch, tb, margem=0.2) for tb in textos_obst)

            def _chamada_corta_texto_v(y_c, x_a, x_b):
                x_lo, x_hi = min(x_a, x_b) + 1.0, max(x_a, x_b) - 1.0
                if x_hi <= x_lo:
                    return False
                bx_ch = (x_lo, y_c - 0.5, x_hi, y_c + 0.5)
                return any(_boxes_colidem(bx_ch, tb, margem=0.2) for tb in textos_obst)

            def _pos_livre_h(x1, x2, y_pref, direcao, y_alt=None):
                """Escolhe Y fora de todos os pilares; evita textos se possivel, mas nunca pula o detalhe."""
                xmin, xmax = min(x1, x2), max(x1, x2)
                xc_m = 0.5 * (xmin + xmax)
                if (xmax - xmin) < 20.0:
                    tx_x1 = xmin - 24.0
                    tx_x2 = xmax
                else:
                    larg_t = max(8.0, min(xmax - xmin - 1.6, 15.0))
                    tx_x1 = xc_m - 0.5 * larg_t
                    tx_x2 = xc_m + 0.5 * larg_t

                offs_up = [6.5, 10.5, 15.0, 20.0]
                offs_dn = [11.0, 15.0, 19.5, 24.0]
                pares = []
                if direcao > 0:
                    pares.extend((y_pref, y_pref + d) for d in offs_up)
                    yr2 = y_alt if y_alt is not None else y_pref
                    pares.extend((yr2, yr2 - d) for d in offs_dn)
                else:
                    pares.extend((y_pref, y_pref - d) for d in offs_dn)
                    yr2 = y_alt if y_alt is not None else y_pref
                    pares.extend((yr2, yr2 + d) for d in offs_up)

                # Passada 1: fora de pilares, fora de textos, fora de outras cotas de detalhe e sem chamada cortando texto
                for y_ref_c, yc in pares:
                    bx_linha = (xmin, yc - 1.0, xmax, yc + h_det + 2.5)
                    bx_texto = (tx_x1, yc + 1.0, tx_x2, yc + h_det + 2.5)
                    if any(_boxes_colidem(bx_linha, pb, margem=0.5) for pb in boxes_pilares):
                        continue
                    if any(_boxes_colidem(bx_texto, pb, margem=0.5) for pb in boxes_pilares):
                        continue
                    if any(_boxes_colidem(bx_texto, cb, margem=0.3) for cb in cotas_det_boxes):
                        continue
                    if any(_boxes_colidem(bx_texto, tb, margem=0.3) for tb in textos_obst):
                        continue
                    if _chamada_corta_texto_h(xmin, y_ref_c, yc) or _chamada_corta_texto_h(xmax, y_ref_c, yc):
                        continue
                    sgn_c = 1.0 if yc >= y_ref_c else -1.0
                    if cota_ja_existe(xmin, xmax, self.cotas_existentes, orient="H", pos_linha=y_ref_c + sgn_c * 15.0, tol_linha=16.0):
                        continue
                    return (y_ref_c, yc)

                # Passada 2 (fallback): garante que o detalhe SEMPRE seja cotado fora dos pilares e sem encavalar outra cota
                for y_ref_c, yc in pares:
                    bx_linha = (xmin, yc - 1.0, xmax, yc + h_det + 2.5)
                    bx_texto = (tx_x1, yc + 1.0, tx_x2, yc + h_det + 2.5)
                    if any(_boxes_colidem(bx_linha, pb, margem=0.5) for pb in boxes_pilares):
                        continue
                    if any(_boxes_colidem(bx_texto, pb, margem=0.5) for pb in boxes_pilares):
                        continue
                    if any(_boxes_colidem(bx_texto, cb, margem=0.3) for cb in cotas_det_boxes):
                        continue
                    sgn_c = 1.0 if yc >= y_ref_c else -1.0
                    if cota_ja_existe(xmin, xmax, self.cotas_existentes, orient="H", pos_linha=y_ref_c + sgn_c * 15.0, tol_linha=16.0):
                        continue
                    return (y_ref_c, yc)
                return None

            def _pos_livre_v(y1, y2, x_pref, direcao, x_alt=None):
                """Escolhe X fora de todos os pilares; evita textos se possivel, mas nunca pula o detalhe."""
                ymin, ymax = min(y1, y2), max(y1, y2)
                yc_m = 0.5 * (ymin + ymax)
                if (ymax - ymin) < 20.0:
                    ty_y1 = ymin - 24.0
                    ty_y2 = ymax
                else:
                    larg_t = max(8.0, min(ymax - ymin - 1.6, 15.0))
                    ty_y1 = yc_m - 0.5 * larg_t
                    ty_y2 = yc_m + 0.5 * larg_t

                offs_esq = [6.5, 10.5, 15.0, 20.0]
                offs_dir = [11.0, 15.0, 19.5, 24.0]
                pares = []
                if direcao < 0:
                    pares.extend((x_pref, x_pref - d) for d in offs_esq)
                    xr2 = x_alt if x_alt is not None else x_pref
                    pares.extend((xr2, xr2 + d) for d in offs_dir)
                else:
                    pares.extend((x_pref, x_pref + d) for d in offs_dir)
                    xr2 = x_alt if x_alt is not None else x_pref
                    pares.extend((xr2, xr2 - d) for d in offs_esq)

                for x_ref_c, xc in pares:
                    bx_linha = (xc - h_det - 2.5, ymin, xc + 1.0, ymax)
                    bx_texto = (xc - h_det - 2.5, ty_y1, xc - 1.0, ty_y2)
                    if any(_boxes_colidem(bx_linha, pb, margem=0.5) for pb in boxes_pilares):
                        continue
                    if any(_boxes_colidem(bx_texto, pb, margem=0.5) for pb in boxes_pilares):
                        continue
                    if any(_boxes_colidem(bx_texto, cb, margem=0.3) for cb in cotas_det_boxes):
                        continue
                    if any(_boxes_colidem(bx_texto, tb, margem=0.3) for tb in textos_obst):
                        continue
                    if _chamada_corta_texto_v(ymin, x_ref_c, xc) or _chamada_corta_texto_v(ymax, x_ref_c, xc):
                        continue
                    sgn_c = 1.0 if xc >= x_ref_c else -1.0
                    if cota_ja_existe(ymin, ymax, self.cotas_existentes, orient="V", pos_linha=x_ref_c + sgn_c * 15.0, tol_linha=16.0):
                        continue
                    return (x_ref_c, xc)

                for x_ref_c, xc in pares:
                    bx_linha = (xc - h_det - 2.5, ymin, xc + 1.0, ymax)
                    bx_texto = (xc - h_det - 2.5, ty_y1, xc - 1.0, ty_y2)
                    if any(_boxes_colidem(bx_linha, pb, margem=0.5) for pb in boxes_pilares):
                        continue
                    if any(_boxes_colidem(bx_texto, pb, margem=0.5) for pb in boxes_pilares):
                        continue
                    if any(_boxes_colidem(bx_texto, cb, margem=0.3) for cb in cotas_det_boxes):
                        continue
                    sgn_c = 1.0 if xc >= x_ref_c else -1.0
                    if cota_ja_existe(ymin, ymax, self.cotas_existentes, orient="V", pos_linha=x_ref_c + sgn_c * 15.0, tol_linha=16.0):
                        continue
                    return (x_ref_c, xc)
                return None

            def _add_h(x1, x2, y_ref, direcao, y_alt=None):
                nonlocal total_criadas
                xa, xb = min(x1, x2), max(x1, x2)
                if not (2.0 <= (xb - xa) <= 80.0):
                    return
                # Evita duplicar qualquer cota ja existente naquela mesma face/lado (sem bloquear a face oposta em pilares estreitos)
                if cota_ja_existe(xa, xb, self.cotas_existentes, orient="H", pos_linha=y_ref + direcao * 15.0, tol_linha=16.0):
                    return
                if y_alt is not None and cota_ja_existe(xa, xb, self.cotas_existentes, orient="H", pos_linha=y_alt - direcao * 15.0, tol_linha=16.0):
                    return
                res = _pos_livre_h(xa, xb, y_ref, direcao, y_alt=y_alt)
                if res is None:
                    return
                y_ref_ok, yc = res
                criar_dim_horizontal(self.dwg, xa, y_ref_ok, xb, y_ref_ok, 0.5 * (xa + xb), yc, arredondar=arredondar_valores)
                _registrar_cota_em_memoria(self.cotas_existentes, "H", xa, xb, yc)
                if (xb - xa) < 20.0:
                    cotas_det_boxes.append((xa - 24.0, yc + 1.0, xb - 0.8, yc + h_det + 2.5))
                else:
                    cotas_det_boxes.append((xa + 0.8, yc + 1.0, xb - 0.8, yc + h_det + 2.5))
                total_criadas += 1

            def _add_v(y1, y2, x_ref, direcao, x_alt=None):
                nonlocal total_criadas
                ya, yb = min(y1, y2), max(y1, y2)
                if not (2.0 <= (yb - ya) <= 80.0):
                    return
                # Evita duplicar qualquer cota ja existente naquela mesma face/lado (sem bloquear a face oposta em pilares estreitos)
                if cota_ja_existe(ya, yb, self.cotas_existentes, orient="V", pos_linha=x_ref + direcao * 15.0, tol_linha=16.0):
                    return
                if x_alt is not None and cota_ja_existe(ya, yb, self.cotas_existentes, orient="V", pos_linha=x_alt - direcao * 15.0, tol_linha=16.0):
                    return
                res = _pos_livre_v(ya, yb, x_ref, direcao, x_alt=x_alt)
                if res is None:
                    return
                x_ref_ok, xc = res
                criar_dim_vertical(self.dwg, x_ref_ok, ya, x_ref_ok, yb, xc, 0.5 * (ya + yb), arredondar=arredondar_valores)
                _registrar_cota_em_memoria(self.cotas_existentes, "V", ya, yb, xc)
                if (yb - ya) < 20.0:
                    cotas_det_boxes.append((xc - h_det - 2.5, ya - 24.0, xc - 1.0, yb - 0.8))
                else:
                    cotas_det_boxes.append((xc - h_det - 2.5, ya + 0.8, xc - 1.0, yb - 0.8))
                total_criadas += 1

            # 1. Sobressaimentos de pilares em relacao as vigas (niveis 1/2/201) e linhas de fechamento de laje (nivel 237)
            for _, (px1, py1, px2, py2) in pilares_poly:
                for y_face, dir_y in ((py2, 1.0), (py1, -1.0)):
                    xs_v = []
                    for x1, y1, x2, y2 in vigas_todas:
                        if abs(x2 - x1) <= 0.25 * abs(y2 - y1) or abs(x2 - x1) < 4.0:
                            ymin_s, ymax_s = min(y1, y2), max(y1, y2)
                            sai_para_lado = (ymax_s > py2 + 5.0) if dir_y > 0 else (ymin_s < py1 - 5.0)
                            entra_no_pilar = (ymin_s <= py2 + 4.0) and (ymax_s >= py1 - 4.0)
                            if sai_para_lado and entra_no_pilar:
                                if abs(y2 - y1) > 0.1:
                                    xp = x1 + (y_face - y1) / (y2 - y1) * (x2 - x1)
                                else:
                                    xp = 0.5 * (x1 + x2)
                                if (px1 - 4.0) <= xp <= (px2 + 4.0):
                                    xs_v.append(xp)
                    xs_u = sorted(list(set(round(x, 1) for x in xs_v)))
                    tem_viga_face = False
                    if len(xs_u) >= 2:
                        v_esq, v_dir = xs_u[0], xs_u[-1]
                        if 10.0 <= (v_dir - v_esq) <= 45.0:
                            tem_viga_face = True
                            if (v_esq - px1) >= 3.0:
                                _add_h(px1, v_esq, y_face, dir_y)
                            if (px2 - v_dir) >= 3.0:
                                _add_h(v_dir, px2, y_face, dir_y)

                    if not tem_viga_face and lajes_237_seg:
                        xs_l = []
                        for x1, y1, x2, y2 in lajes_237_seg:
                            if abs(x2 - x1) <= 0.25 * abs(y2 - y1) or abs(x2 - x1) < 4.0:
                                ymin_s, ymax_s = min(y1, y2), max(y1, y2)
                                sai_para_lado = (ymax_s > py2 + 5.0) if dir_y > 0 else (ymin_s < py1 - 5.0)
                                entra_no_pilar = (ymin_s <= py2 + 4.0) and (ymax_s >= py1 - 4.0)
                                if sai_para_lado and entra_no_pilar:
                                    xp = (x1 + (y_face - y1) / (y2 - y1) * (x2 - x1)) if abs(y2 - y1) > 0.1 else 0.5 * (x1 + x2)
                                    if (px1 - 4.0) <= xp <= (px2 + 4.0):
                                        xs_l.append(round(xp, 1))
                        for x_l in sorted(set(xs_l)):
                            if (x_l - px1) >= 3.0:
                                _add_h(px1, x_l, y_face, dir_y)
                            if (px2 - x_l) >= 3.0:
                                _add_h(x_l, px2, y_face, dir_y)

                for x_face, dir_x in ((px1, -1.0), (px2, 1.0)):
                    ys_v = []
                    for x1, y1, x2, y2 in vigas_todas:
                        if abs(y2 - y1) <= 0.25 * abs(x2 - x1) or abs(y2 - y1) < 4.0:
                            xmin_s, xmax_s = min(x1, x2), max(x1, x2)
                            sai_para_lado = (xmax_s > px2 + 5.0) if dir_x > 0 else (xmin_s < px1 - 5.0)
                            entra_no_pilar = (xmin_s <= px2 + 4.0) and (xmax_s >= px1 - 4.0)
                            if sai_para_lado and entra_no_pilar:
                                if abs(x2 - x1) > 0.1:
                                    yp = y1 + (x_face - x1) / (x2 - x1) * (y2 - y1)
                                else:
                                    yp = 0.5 * (y1 + y2)
                                if (py1 - 4.0) <= yp <= (py2 + 4.0):
                                    ys_v.append(yp)
                    ys_u = sorted(list(set(round(y, 1) for y in ys_v)))
                    tem_viga_face = False
                    if len(ys_u) >= 2:
                        v_inf, v_sup = ys_u[0], ys_u[-1]
                        if 10.0 <= (v_sup - v_inf) <= 45.0:
                            tem_viga_face = True
                            if (v_inf - py1) >= 3.0:
                                _add_v(py1, v_inf, x_face, dir_x)
                            if (py2 - v_sup) >= 3.0:
                                _add_v(v_sup, py2, x_face, dir_x)

                    if not tem_viga_face and lajes_237_seg:
                        ys_l = []
                        for x1, y1, x2, y2 in lajes_237_seg:
                            if abs(y2 - y1) <= 0.25 * abs(x2 - x1) or abs(y2 - y1) < 4.0:
                                xmin_s, xmax_s = min(x1, x2), max(x1, x2)
                                sai_para_lado = (xmax_s > px2 + 5.0) if dir_x > 0 else (xmin_s < px1 - 5.0)
                                entra_no_pilar = (xmin_s <= px2 + 4.0) and (xmax_s >= px1 - 4.0)
                                if sai_para_lado and entra_no_pilar:
                                    yp = (y1 + (x_face - x1) / (x2 - x1) * (y2 - y1)) if abs(x2 - x1) > 0.1 else 0.5 * (y1 + y2)
                                    if (py1 - 4.0) <= yp <= (py2 + 4.0):
                                        ys_l.append(round(yp, 1))
                        for y_l in sorted(set(ys_l)):
                            if (y_l - py1) >= 3.0:
                                _add_v(py1, y_l, x_face, dir_x)
                            if (py2 - y_l) >= 3.0:
                                _add_v(y_l, py2, x_face, dir_x)

            # 2. Degraus / ressaltos entre pares de pilares proximos (junta de dilatacao)
            # Posiciona no lado do pilar recuado (menor), alinhando em cadeia com o sobressaimento dele
            for i in range(len(pilares_poly)):
                _, (ax1, ay1, ax2, ay2) = pilares_poly[i]
                for j in range(i + 1, len(pilares_poly)):
                    _, (bx1, by1, bx2, by2) = pilares_poly[j]
                    gx = max(0.0, max(ax1, bx1) - min(ax2, bx2))
                    gy = max(0.0, max(ay1, by1) - min(ay2, by2))
                    if gx > 15.0 or gy > 15.0:
                        continue

                    if gy <= 15.0 and min(ax2, bx2) > max(ax1, bx1):
                        if ay2 >= by2:
                            sup, inf = (ax1, ay1, ax2, ay2), (bx1, by1, bx2, by2)
                        else:
                            sup, inf = (bx1, by1, bx2, by2), (ax1, ay1, ax2, ay2)

                        if 3.0 <= abs(sup[0] - inf[0]) <= 80.0:
                            if sup[0] > inf[0]:
                                _add_h(sup[0], inf[0], sup[3], 1.0, y_alt=inf[1])
                            else:
                                _add_h(sup[0], inf[0], inf[1], -1.0, y_alt=sup[3])
                        if 3.0 <= abs(sup[2] - inf[2]) <= 80.0:
                            if sup[2] < inf[2]:
                                _add_h(sup[2], inf[2], sup[3], 1.0, y_alt=inf[1])
                            else:
                                _add_h(sup[2], inf[2], inf[1], -1.0, y_alt=sup[3])
                    elif gx <= 15.0 and min(ay2, by2) > max(ay1, by1):
                        if ax2 >= bx2:
                            dir_p, esq_p = (ax1, ay1, ax2, ay2), (bx1, by1, bx2, by2)
                        else:
                            dir_p, esq_p = (bx1, by1, bx2, by2), (ax1, ay1, ax2, ay2)

                        if 3.0 <= abs(dir_p[1] - esq_p[1]) <= 80.0:
                            if dir_p[1] > esq_p[1]:
                                _add_v(dir_p[1], esq_p[1], dir_p[2], 1.0, x_alt=esq_p[0])
                            else:
                                _add_v(dir_p[1], esq_p[1], esq_p[0], -1.0, x_alt=dir_p[2])
                        if 3.0 <= abs(dir_p[3] - esq_p[3]) <= 80.0:
                            if dir_p[3] < esq_p[3]:
                                _add_v(dir_p[3], esq_p[3], dir_p[2], 1.0, x_alt=esq_p[0])
                            else:
                                _add_v(dir_p[3], esq_p[3], esq_p[0], -1.0, x_alt=dir_p[2])

            if arredondar_valores:
                aplicar_arredondamento_cotas(self.dwg)
            self.cotas_existentes = coletar_cotas_existentes(self.dwg)

            return total_criadas
        finally:
            self.configurar_estilo()


def pedir_modo_cotas():
    """
    Exibe uma janela HTA perguntando ao usuario se deseja gerar:
      - Cota Geral (cotas externas em camadas e cadeias internas gerais da forma)
      - Cota de Pilar (cotagem automatica dos pilares nos quadrados/capiteis)
    Retorna um dicionario com a escolha ou None se cancelado.
    """
    pasta_temp = os.environ.get("TEMP", os.path.dirname(os.path.abspath(__file__)))
    hta_path = os.path.join(pasta_temp, "g3_modo_cotas.hta")
    json_path = os.path.join(pasta_temp, "g3_modo_cotas.json")
    json_js = json_path.replace("\\", "\\\\")

    if os.path.exists(json_path):
        try:
            os.remove(json_path)
        except Exception:
            pass

    hta_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta http-equiv="x-ua-compatible" content="ie=edge" />
    <title>G3 Plugins - Criar Cotas</title>
    <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="G3CriarCotas" BORDER="dialog" MAXIMIZEBUTTON="no" MINIMIZEBUTTON="no" INNERBORDER="no" SCROLL="no" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #f8fafc;
            color: #1e293b;
            font-size: 13px;
            user-select: none;
        }}
        .topbar {{
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
            color: #ffffff;
            padding: 14px 20px;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .topbar-icon {{
            width: 34px;
            height: 34px;
            background: #2563eb;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 17px;
            font-weight: bold;
        }}
        .topbar h1 {{ font-size: 16px; font-weight: 700; }}
        .topbar p {{ font-size: 11px; color: #93c5fd; margin-top: 2px; }}
        .container {{ padding: 16px 20px 10px 20px; }}
        .subtitle {{ font-size: 12px; font-weight: 600; color: #475569; margin-bottom: 9px; text-transform: uppercase; letter-spacing: 0.4px; }}
        .card-option {{
            background: #ffffff;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            padding: 12px 14px;
            margin-bottom: 9px;
            cursor: pointer;
            transition: all 0.15s ease;
        }}
        .card-option.active {{
            border-color: #2563eb;
            background: #eff6ff;
        }}
        .card-title {{
            font-size: 13.5px;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 3px;
        }}
        .card-desc {{
            font-size: 11.5px;
            color: #475569;
            line-height: 1.35;
        }}
        .sub-options {{
            margin-top: 9px;
            padding-top: 8px;
            border-top: 1px solid #bfdbfe;
            display: none;
        }}
        .card-option.active .sub-options {{
            display: block;
        }}
        .chk-row {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 11.5px;
            color: #1e3a8a;
            font-weight: 600;
            margin-top: 4px;
            cursor: pointer;
        }}
        .panel-round {{
            background: #f1f5f9;
            border: 1px solid #cbd5e1;
            border-radius: 9px;
            padding: 10px 14px;
            margin-top: 6px;
        }}
        .panel-round-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12.5px;
            font-weight: 700;
            color: #0f172a;
            cursor: pointer;
        }}
        .panel-round-desc {{
            font-size: 11px;
            color: #64748b;
            margin-top: 3px;
            margin-left: 21px;
            line-height: 1.35;
        }}
        .panel-round-desc strong {{
            color: #1e3a8a;
        }}
        .footer {{
            padding: 12px 20px;
            background: #f1f5f9;
            border-top: 1px solid #e2e8f0;
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        }}
        button {{
            padding: 8px 18px;
            border-radius: 7px;
            border: 1px solid #cbd5e1;
            background: #ffffff;
            color: #334155;
            font-size: 12.5px;
            font-weight: 600;
            cursor: pointer;
        }}
        .btn-primary {{
            background: #2563eb;
            border-color: #1d4ed8;
            color: #ffffff;
        }}
    </style>
    <script language="javascript">
        var modoSelecionado = "pilar";

        function initDialog() {{
            try {{
                window.resizeTo(480, 600);
                window.moveTo((screen.availWidth - 480) / 2, (screen.availHeight - 600) / 2);
            }} catch(e) {{}}
            selecionarModo("pilar");
        }}

        function selecionarModo(modo) {{
            modoSelecionado = modo;
            document.getElementById("card-geral").className = (modo === "geral") ? "card-option active" : "card-option";
            document.getElementById("card-pilar").className = (modo === "pilar") ? "card-option active" : "card-option";
        }}

        function confirmar() {{
            try {{
                var incH = document.getElementById("chk-horiz").checked ? "true" : "false";
                var incC = document.getElementById("chk-capitel").checked ? "true" : "false";
                var incL = document.getElementById("chk-lateral").checked ? "true" : "false";
                var incD = document.getElementById("chk-detalhe").checked ? "true" : "false";
                var arrV = document.getElementById("chk-arredondar").checked ? "true" : "false";
                var fso = new ActiveXObject("Scripting.FileSystemObject");
                var a = fso.CreateTextFile("{json_js}", true);
                var jsonStr = '{{"modo":"' + modoSelecionado + '","cadeia_horizontal":' + incH + ',"cotas_capitel":' + incC + ',"pilares_laterais":' + incL + ',"cotar_detalhe":' + incD + ',"arredondar_valores":' + arrV + '}}';
                a.WriteLine(jsonStr);
                a.Close();
                window.close();
            }} catch(e) {{
                alert("Erro: " + e.message);
            }}
        }}
    </script>
</head>
<body onload="initDialog();">
    <div class="topbar">
        <div class="topbar-icon">&#8660;</div>
        <div>
            <h1>Criar Cotas da F&ocirc;rma</h1>
            <p>G3 Plugins &bull; Selecione o tipo de cotagem desejada</p>
        </div>
    </div>

    <div class="container">
        <div class="subtitle">Modo de Cotagem</div>

        <div id="card-pilar" class="card-option active" onclick="selecionarModo('pilar')" ondblclick="selecionarModo('pilar'); confirmar();">
            <div class="card-title">1. Cota de Pilar (Quadrados / Capit&eacute;is)</div>
            <div class="card-desc">Identifica apenas os pilares nos quadrados (maci&ccedil;os), puxando a cota do in&iacute;cio horizontal passando pelos pilares.</div>
            <div class="sub-options" onclick="event.cancelBubble = true;">
                <label class="chk-row">
                    <input type="checkbox" id="chk-horiz" checked />
                    Cadeia horizontal cont&iacute;nua (passando pelos pilares)
                </label>
                <label class="chk-row">
                    <input type="checkbox" id="chk-capitel" checked />
                    Cotas locais do quadrado / capitel (dist&acirc;ncias e cubetas)
                </label>
                <label class="chk-row">
                    <input type="checkbox" id="chk-lateral" checked />
                    Cotas de pilares laterais (cadeia externa nos pilares do contorno)
                </label>
            </div>
        </div>

        <div id="card-geral" class="card-option" onclick="selecionarModo('geral')" ondblclick="selecionarModo('geral'); confirmar();">
            <div class="card-title">2. Cota Geral da F&ocirc;rma</div>
            <div class="card-desc">Gera as cotas externas em 3 camadas (parciais, eixos e total) e completa as cadeias internas da estrutura.</div>
        </div>

        <div class="panel-round">
            <label class="panel-round-header">
                <input type="checkbox" id="chk-detalhe" />
                Cotar detalhe
            </label>
            <div class="panel-round-desc">
                Cota os detalhezinhos pequenos (ressaltos entre pilares e sobressaimentos em vigas), mantendo as cotas <strong>fora dos pilares</strong>.
            </div>
        </div>

        <div class="panel-round">
            <label class="panel-round-header">
                <input type="checkbox" id="chk-arredondar" checked />
                Arredondar valores das cotas
            </label>
            <div class="panel-round-desc">
                Final <strong>0.1 a 0.2 &rarr; 0</strong> &bull; Final <strong>0.3 a 0.7 &rarr; 0.5</strong> &bull; Final <strong>0.8 a 0.9 &rarr; 1.0</strong>
            </div>
        </div>
    </div>

    <div class="footer">
        <button onclick="window.close()">Cancelar</button>
        <button class="btn-primary" onclick="confirmar()">Gerar Cotas</button>
    </div>
</body>
</html>"""

    with open(hta_path, "w", encoding="utf-8-sig") as f:
        f.write(hta_content)

    subprocess.call(["mshta", hta_path])

    dados = None
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                dados = json.load(f)
            os.remove(json_path)
        except Exception:
            pass

    if os.path.exists(hta_path):
        try:
            os.remove(hta_path)
        except Exception:
            pass

    return dados


def cmd_criar_cotas(eag, tqsjan):
    """
    Entry point do comando Criar Cotas para o EAG do TQS.
    Pergunta se o usuario deseja Cota Geral ou Cota de Pilar (quadrados/capiteis)
    e executa automaticamente a cotagem escolhida.
    """
    try:
        escolha = pedir_modo_cotas()
        if not escolha:
            return

        modo = escolha.get("modo", "geral")
        arredondar = bool(escolha.get("arredondar_valores", True))
        cotar_detalhe = bool(escolha.get("cotar_detalhe", False))
        dwg = tqsjan.dwg
        cotador = CotadorFormas(dwg)

        if modo == "pilar":
            inc_h = bool(escolha.get("cadeia_horizontal", True))
            inc_c = bool(escolha.get("cotas_capitel", True))
            inc_l = bool(escolha.get("pilares_laterais", True))
            criadas = cotador.cotar_pilares_quadrados(
                incluir_cadeia_horizontal=inc_h,
                incluir_cotas_capitel=inc_c,
                incluir_pilares_laterais=inc_l,
                arredondar_valores=arredondar,
            )
            detalhes_criadas = cotador.cotar_detalhes(arredondar_valores=arredondar) if cotar_detalhe else 0
            total_pilar = criadas + detalhes_criadas
            if total_pilar > 0:
                tqsjan.Regen()
                if criadas > 0:
                    eag.msg.Print("G3 Plugins: %d cota(s) de pilar e %d cota(s) de detalhe gerada(s)!" % (criadas, detalhes_criadas))
                    eag.msg.PrintStatus("%d cota(s) criada(s)!" % total_pilar)
                else:
                    eag.msg.Print("G3 Plugins: %d cota(s) de detalhe gerada(s) com sucesso!" % detalhes_criadas)
                    eag.msg.PrintStatus("%d cota(s) de detalhe criada(s)!" % detalhes_criadas)
            else:
                eag.msg.Print("G3 Plugins: Nenhuma cota nova de pilar, contorno lateral ou detalhe necessaria.")
                eag.msg.PrintStatus("Nenhuma cota nova necessaria.")
        else:
            criadas = cotador.cotar_forma_completa(arredondar_valores=arredondar)
            if cotar_detalhe:
                criadas += cotador.cotar_detalhes(arredondar_valores=arredondar)
            if criadas > 0:
                tqsjan.Regen()
                eag.msg.Print("G3 Plugins: %d cota(s) geral(is) gerada(s) automaticamente na planta de formas!" % criadas)
                eag.msg.PrintStatus("%d cota(s) criada(s) com sucesso!" % criadas)
            else:
                eag.msg.Print("G3 Plugins: Todas as cotas da planta de formas ja existem (nenhuma cota duplicada).")
                eag.msg.PrintStatus("Nenhuma cota nova necessaria.")

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass


def cmd_arredondar_cotas(eag, tqsjan):
    """Arredonda apenas cotas reais (IPOCOT) existentes no desenho (0..2->.0, 3..7->.5, 8..9->1.0)."""
    try:
        dwg = tqsjan.dwg
        cotas_ipocot = [
            c for c in coletar_cotas_existentes(dwg, nivel_cota=None)
            if c.get("tipo") == "IPOCOT"
        ]
        total = aplicar_arredondamento_cotas(dwg, cotas_alvo=cotas_ipocot)
        if total > 0:
            tqsjan.Regen()
            eag.msg.Print("G3 Plugins: %d cota(s) arredondada(s) com sucesso!" % total)
            eag.msg.PrintStatus("%d cota(s) arredondada(s)!" % total)
        else:
            eag.msg.Print("G3 Plugins: Todas as cotas ja estao arredondadas.")
            eag.msg.PrintStatus("Nenhuma cota precisou ser arredondada.")
    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass


def meucmd(eag, tqsjan):
    """Entry point padrao quando chamado diretamente."""
    cmd_criar_cotas(eag, tqsjan)
