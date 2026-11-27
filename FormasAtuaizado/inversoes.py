# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - INVERSOES DE VIGAS E LAJES (TQS EAG)
================================================================================
Modulo dedicado a conversao de bolinhas de desnivel/inversao:
  - Nivel 11: VIGA INVERTIDA xCM (orientacao travada, seta Nivel 221 se > 40 cm)
  - Nivel 13: LAJE REBAIXADA / xCM
================================================================================
"""
import math
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag
import anti_sobreposicao
from linha_de_corte import encontrar_pares_de_corte

LIMITE_SEM_SETA_INVERSAO_VIGA = 40.0


def _parse_valor_bolinha(texto_str):
    """
    Tenta extrair um valor numerico de desnivel/inversao do texto da bolinha (ex: '15', '-15', '+15').
    Retorna float ou None se nao for numero valido.
    """
    if not texto_str:
        return None
    limpo = texto_str.strip().replace(",", ".")
    try:
        val = float(limpo)
        if abs(val) < 1e-4:
            return None
        return val
    except ValueError:
        return None


def _formatar_valor_cm(val):
    """Formata o valor absoluto sem casas decimais desnecessarias."""
    val_abs = abs(val)
    if abs(val_abs - round(val_abs)) < 1e-4:
        return str(int(round(val_abs)))
    return ("%g" % val_abs).replace(".", ",")


def _normalizar_angulo(ang):
    """Normaliza angulo para 0.0 (horizontal) ou 90.0 (vertical) quando proximo."""
    a = ang % 360.0
    if a < 0:
        a += 360.0
    if abs(a - 0.0) < 5.0 or abs(a - 360.0) < 5.0 or abs(a - 180.0) < 5.0:
        return 0.0
    if abs(a - 90.0) < 5.0 or abs(a - 270.0) < 5.0:
        return 90.0
    return round(a, 2)


def _bbox_texto(xc, yc, h, ang, texto_str):
    """
    Calcula o bounding box aproximado (xmin, ymin, xmax, ymax) de um texto no TQS.
    No TQS, (xc, yc) e o ponto inferior-esquerdo da linha de base.
    """
    comp = len(texto_str) * h * 0.85
    a = _normalizar_angulo(ang)
    if a == 90.0:
        # Quando rotacionado a 90 graus, o texto cresce em +Y e tem altura para a esquerda (-X)
        return (xc - h * 1.15, yc, xc + h * 0.25, yc + comp)
    else:
        return (xc, yc - h * 0.25, xc + comp, yc + h * 1.15)


def _boxes_colidem(b1, b2, margem=4.0):
    """Verifica se dois bounding boxes (xmin, ymin, xmax, ymax) se sobrepoem com margem."""
    return not (
        b1[2] + margem < b2[0] or
        b1[0] - margem > b2[2] or
        b1[3] + margem < b2[1] or
        b1[1] - margem > b2[3]
    )


def _resolver_nivel_bolinha(nivel_circulo, nivel_texto, xc_tx, yc_tx, lajes):
    """
    Determina o nivel efetivo da bolinha (11 = Viga, 13 = Laje):
      - Se Circulo e Texto estao no mesmo nivel, usa esse nivel.
      - Se o usuario alterou apenas o Circulo (ou apenas o Texto) no EAG para testar:
        - Se algum dos dois foi mudado para fora de (11, 13), retorna esse nivel (sera ignorado).
        - Se um e 11 e o outro e 13, verifica o contexto original (abaixo de titulo de laje L...
          era originalmente 13, logo foi mudado para 11; caso contrario era 11 e foi mudado para 13).
    """
    if nivel_circulo == nivel_texto:
        return nivel_circulo

    # Se um deles foi alterado para um nivel diferente de 11 e 13 (ex: nivel 0, 200, etc.)
    if nivel_circulo not in (11, 13):
        return nivel_circulo
    if nivel_texto not in (11, 13):
        return nivel_texto

    # Um e 11 e o outro e 13: descobre qual era o nivel original pela posicao (laje vs viga)
    estava_em_laje = False
    for lj in lajes:
        if abs(lj["xc"] - xc_tx) <= 35.0 and 0.0 <= (lj["yc"] - yc_tx) <= 85.0:
            estava_em_laje = True
            break

    if estava_em_laje:
        # Originalmente era 13 (Laje); se um dos dois agora e 11, o usuario trocou para 11 (Viga)
        return 11
    else:
        # Originalmente era 11 (Viga); se um dos dois agora e 13, o usuario trocou para 13 (Laje)
        return 13


def _diff_angulo_180(a1, a2):
    """Diferenca angular minima modulo 180 graus (mesma direcao de alinhamento)."""
    d = abs((float(a1) - float(a2)) % 180.0)
    return min(d, 180.0 - d)


def _bbox_texto_inversao(x1, y1, h, ang, texto_str):
    """
    Calcula o bounding box real no TQS (largura ~1.0 * h por caractere),
    suportando 0, 90 e qualquer angulo inclinado.
    """
    return anti_sobreposicao._bbox_texto(x1, y1, h, ang, texto_str)


def _rbox_texto_inversao(x1, y1, h, ang, texto_str):
    """
    Caixa exata do glifo maiusculo no TQS ([0..comp_real] x [0..h]),
    identica a metrica de colisao real de organizar.py.
    """
    comp = max(len(texto_str) * h * 1.0 - 0.2 * h, 0.5 * h)
    rad = math.radians(ang)
    ux, uy = math.cos(rad), math.sin(rad)
    nx, ny = -uy, ux
    xs = []
    ys = []
    for s in (0.0, comp):
        for q in (0.0, h):
            xs.append(x1 + ux * s + nx * q)
            ys.append(y1 + uy * s + ny * q)
    return (min(xs), min(ys), max(xs), max(ys))


def _dist_ponto_a_box(px, py, box):
    """Distancia euclidiana minima de um ponto (px, py) ate o retangulo box."""
    dx = max(0.0, box[0] - px, px - box[2])
    dy = max(0.0, box[1] - py, py - box[3])
    return math.hypot(dx, dy)


def _ponto_saida_seta_inversao(xt, yt, comp, h, ang_txt, xa, ya):
    """
    Retorna o ponto de saida (x_joelho, y_joelho) na borda do texto usado por
    anti_sobreposicao.desenhar_seta_inversao para validar colisoes da haste.
    """
    if hasattr(anti_sobreposicao, "_ponto_saida_seta_inversao"):
        return anti_sobreposicao._ponto_saida_seta_inversao(xt, yt, comp, h, ang_txt, xa, ya)
    a_norm = _normalizar_angulo(ang_txt)
    if a_norm == 0.0:
        if xt > xa + 5.0:
            return (xt - 2.0, yt + 0.5 * h)
        elif xt + comp < xa - 5.0:
            return (xt + comp + 2.0, yt + 0.5 * h)
        elif yt > ya + 2.0:
            return (max(xt, min(xt + comp, xa)), yt - 2.0)
        else:
            return (max(xt, min(xt + comp, xa)), yt + h + 2.0)
    elif a_norm == 90.0:
        if yt + comp < ya - 5.0:
            return (xt - 0.5 * h, yt + comp + 2.0)
        elif yt > ya + 5.0:
            return (xt - 0.5 * h, yt - 2.0)
        else:
            x_j = (xt - h - 2.0) if xt >= xa else (xt + 2.0)
            y_j = max(yt + 2.0, min(yt + comp - 2.0, ya))
            return (x_j, y_j)
    else:
        rad = math.radians(ang_txt)
        ux, uy = math.cos(rad), math.sin(rad)
        nx, ny = -uy, ux
        dx = xa - xt
        dy = ya - yt
        s_a = dx * ux + dy * uy
        q_a = dx * nx + dy * ny
        s_c = max(0.0, min(comp, s_a))
        q_c = max(0.0, min(h, q_a))
        vx = s_a - s_c
        vy = q_a - q_c
        vlen = math.hypot(vx, vy)
        if vlen > 1e-4:
            s_c += 2.0 * (vx / vlen)
            q_c += 2.0 * (vy / vlen)
        return (xt + ux * s_c + nx * q_c, yt + uy * s_c + ny * q_c)


def coletar_contexto_inversoes(dwg):
    """
    Varre o DWG coletando:
      - Bolinhas de viga (Nivel 11 - Dimensoes de vigas) e de laje (Nivel 13 - Dimensoes de lajes)
      - Titulos de vigas (Nivel 8, 'V...') e secoes de vigas (Nivel 11, 'b/h')
      - Titulos de lajes (Nivel 10, 'L...') e espessuras de lajes (Nivel 13, 'h=...')
      - Obstaculos (outros textos, pilares, linhas de corte e linhas de concreto)
    """
    anti_sobreposicao._garantir_ipocot_carregado()

    circulos = []
    textos_numericos = []
    vigas = []
    lajes = []
    obstaculos = []
    obstaculos_viga_exatos = []
    linhas_221_existentes = []
    linhas_vert_concreto = []
    linhas_horiz_concreto = []
    lines_concreto_exatas = []
    secoes_viga_coletadas = []

    viga_atual = None
    laje_atual = None

    # Linhas de corte (pares de corte) sao referencias visuais de fundo e nao obstaculos fisicos de texto
    pares_corte = encontrar_pares_de_corte(dwg)

    dwg.iterator.Begin()
    while True:
        tipo = dwg.iterator.Next()
        if tipo == TQSDwg.DWGTYPE_EOF:
            break
        if dwg.iterator.inBlock != 0:
            if tipo == TQSDwg.DWGTYPE_POLYLINE and dwg.iterator.level == 208:
                pts_c = [dwg.iterator.GetPolylinePt(i) for i in range(dwg.iterator.xySize)]
                if pts_c:
                    xs_c = [p[0] for p in pts_c]
                    ys_c = [p[1] for p in pts_c]
                    cb = (min(xs_c), min(ys_c), max(xs_c), max(ys_c))
                    obstaculos.append({"tipo": "cubeta", "bbox": cb})
                    obstaculos_viga_exatos.append(("cubeta", cb))
            continue

        nivel = dwg.iterator.level
        if dwg.iterator.isOpenObject != 0:
            if tipo == TQSDwg.DWGTYPE_TEXT and nivel in (122, 216):
                bx_cota = anti_sobreposicao._bbox_texto_exato(
                    dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2, dwg.iterator.textHeight
                )
                obstaculos_viga_exatos.append(("cota", bx_cota))
            elif tipo == TQSDwg.DWGTYPE_LINE and nivel in (122, 216, 221):
                linhas_221_existentes.append((dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2))
            continue

        addr = dwg.iterator.GetElementReadPosition()

        # Linhas/Polylines de concreto (Nivel 1, 2, 201), pilares (Nivel 2, 3, 4, 5) e cubetas/cortes
        if tipo == TQSDwg.DWGTYPE_POLYLINE and nivel in (1, 2, 3, 4, 5, 200, 201, 205, 208):
            pts = [dwg.iterator.GetPolylinePt(i) for i in range(dwg.iterator.xySize)]
            if pts:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                dx_p = max(xs) - min(xs)
                dy_p = max(ys) - min(ys)
                if nivel == 208:
                    obstaculos_viga_exatos.append(("cubeta", (min(xs), min(ys), max(xs), max(ys))))
                elif nivel in (200, 205):
                    obstaculos_viga_exatos.append(("corte_linha", (min(xs), min(ys), max(xs), max(ys))))
                elif nivel in (2, 3, 4, 5) and 5.0 <= dx_p <= 450.0 and 5.0 <= dy_p <= 450.0 and len(pts) >= 4:
                    pb = (min(xs), min(ys), max(xs), max(ys))
                    obstaculos.append({"tipo": "pilar", "bbox": pb})
                    obstaculos_viga_exatos.append(("pilar_poly", pb))
                elif nivel in (1, 2, 201) and len(pts) >= 2:
                    for k in range(len(pts) - 1):
                        x1, y1 = pts[k]
                        x2, y2 = pts[k + 1]
                        lines_concreto_exatas.append((x1, y1, x2, y2, nivel))
                        if abs(x1 - x2) <= 8.0 and abs(y1 - y2) > 10.0:
                            linhas_vert_concreto.append((0.5 * (x1 + x2), min(y1, y2), max(y1, y2)))
                        elif abs(y1 - y2) <= 8.0 and abs(x1 - x2) > 10.0:
                            linhas_horiz_concreto.append((0.5 * (y1 + y2), min(x1, x2), max(x1, x2)))

        elif tipo == TQSDwg.DWGTYPE_LINE and nivel in (1, 2, 201):
            x1, y1, x2, y2 = dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2
            lines_concreto_exatas.append((x1, y1, x2, y2, nivel))
            if abs(x1 - x2) <= 8.0 and abs(y1 - y2) > 10.0:
                linhas_vert_concreto.append((0.5 * (x1 + x2), min(y1, y2), max(y1, y2)))
            elif abs(y1 - y2) <= 8.0 and abs(x1 - x2) > 10.0:
                linhas_horiz_concreto.append((0.5 * (y1 + y2), min(x1, x2), max(x1, x2)))

        elif tipo == TQSDwg.DWGTYPE_LINE and nivel in (200, 205):
            xmin = min(dwg.iterator.x1, dwg.iterator.x2) - 2.0
            xmax = max(dwg.iterator.x1, dwg.iterator.x2) + 2.0
            ymin = min(dwg.iterator.y1, dwg.iterator.y2) - 2.0
            ymax = max(dwg.iterator.y1, dwg.iterator.y2) + 2.0
            cb_corte = (xmin, ymin, xmax, ymax)
            obstaculos.append({"tipo": "corte_linha", "bbox": cb_corte})
            obstaculos_viga_exatos.append(("corte_linha", cb_corte))

        elif tipo == TQSDwg.DWGTYPE_LINE and nivel in (122, 216, 221, 242):
            x1, y1, x2, y2 = dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2
            if nivel in (221, 242):
                linhas_221_existentes.append((x1, y1, x2, y2))
            else:
                obstaculos_viga_exatos.append(("cota", (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))))

        elif tipo == TQSDwg.DWGTYPE_CIRCLE:
            if nivel in (28, 29):
                continue
            circulos.append({
                "addr": addr,
                "xc": dwg.iterator.xc,
                "yc": dwg.iterator.yc,
                "r": dwg.iterator.radius,
                "level": nivel,
            })

        elif tipo == TQSDwg.DWGTYPE_TEXT:
            if nivel in (28, 29):
                continue
            txt_raw = dwg.iterator.text.strip()
            xc = dwg.iterator.xc
            yc = dwg.iterator.yc
            x1 = dwg.iterator.x1
            y1 = dwg.iterator.y1
            x2 = dwg.iterator.x2
            y2 = dwg.iterator.y2
            h = dwg.iterator.textHeight
            ang_raw = dwg.iterator.textAngle
            ang = _normalizar_angulo(ang_raw)
            bx_exato = anti_sobreposicao._bbox_texto_exato(x1, y1, x2, y2, h)

            if nivel in (122, 216):
                obstaculos_viga_exatos.append(("cota", bx_exato))
                continue

            # 1. Titulo de Viga (Nivel 8, ex: 'V101')
            if nivel == 8 and txt_raw.upper().startswith("V"):
                bx = _bbox_texto(xc, yc, h, ang, txt_raw)
                viga_atual = {
                    "nome": txt_raw,
                    "addr_titulo": addr,
                    "xc": xc, "yc": yc,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "h": h, "ang": ang,
                    "bbox": bx,
                    "box_exato": bx_exato,
                    "secao": None,
                }
                laje_atual = None
                vigas.append(viga_atual)
                obstaculos.append({
                    "tipo": "viga_titulo",
                    "addr": addr,
                    "bbox": bx
                })
                obstaculos_viga_exatos.append(("viga_titulo", bx_exato))
                continue

            # 2. Secao de Viga (Nivel 11, ex: '14/70')
            if nivel == 11 and "/" in txt_raw:
                bx = _bbox_texto(xc, yc, h, ang, txt_raw)
                sec_obj = {
                    "texto": txt_raw,
                    "addr": addr,
                    "xc": xc, "yc": yc,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "h": h, "ang": ang,
                    "bbox": bx,
                    "box_exato": bx_exato,
                }
                secoes_viga_coletadas.append(sec_obj)
                obstaculos.append({
                    "tipo": "viga_secao",
                    "addr": addr,
                    "bbox": bx
                })
                obstaculos_viga_exatos.append(("viga_secao", bx_exato))
                continue

            # 3. Titulo de Laje (Nivel 10, ex: 'L103')
            if nivel == 10 and txt_raw.upper().startswith("L"):
                laje_atual = {
                    "nome": txt_raw,
                    "addr_titulo": addr,
                    "xc": xc, "yc": yc,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "h": h, "ang": ang,
                    "esp": None,
                }
                viga_atual = None
                lajes.append(laje_atual)
                obstaculos_viga_exatos.append(("laje_titulo", bx_exato))
                continue

            # 4. Espessura de Laje (Nivel 13, ex: 'h=15')
            if nivel == 13 and ("=" in txt_raw or txt_raw.lower().startswith("h")):
                esp_obj = {
                    "texto": txt_raw,
                    "addr": addr,
                    "xc": xc, "yc": yc,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "h": h, "ang": ang,
                }
                if laje_atual is not None and laje_atual["esp"] is None:
                    laje_atual["esp"] = esp_obj
                obstaculos_viga_exatos.append(("laje_esp", bx_exato))
                continue

            # 5. Texto numerico (possivel interior de bolinha)
            val = _parse_valor_bolinha(txt_raw)
            if val is not None:
                textos_numericos.append({
                    "addr": addr,
                    "xc": xc, "yc": yc,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "text": txt_raw,
                    "val": val,
                    "h": h, "ang": ang,
                    "ang_raw": ang_raw,
                    "level": nivel,
                    "box_exato": bx_exato,
                })
            else:
                # Outros textos (ex: P1, 25/25, etc.) sao obstaculos (pilares marcados com tipo='pilar')
                is_pilar = nivel in (9, 12) or (txt_raw.strip().upper().startswith("P") and nivel in (8, 9, 10, 11, 12))
                obstaculos.append({
                    "tipo": "pilar" if is_pilar else "texto",
                    "nivel": nivel,
                    "texto": txt_raw,
                    "addr": addr,
                    "bbox": bx_exato
                })
                obstaculos_viga_exatos.append(("pilar_txt" if is_pilar else "texto", bx_exato))

    # Emparelha geometricamente cada circulo com seu texto numerico interno
    # e verifica se o nivel efetivo da bolinha e 11 (Viga) ou 13 (Laje)
    bolinhas = []
    textos_usados = set()

    for c in circulos:
        melhor_tx = None
        menor_dist = float("inf")

        for idx, tx in enumerate(textos_numericos):
            if idx in textos_usados:
                continue

            mx = 0.5 * (tx["x1"] + tx["x2"])
            my = 0.5 * (tx["y1"] + tx["y2"])
            dist_mid = math.hypot(c["xc"] - mx, c["yc"] - my)
            dist_orig = math.hypot(c["xc"] - tx["xc"], c["yc"] - tx["yc"])

            if dist_mid <= c["r"] * 1.25 or dist_orig <= c["r"] * 1.35:
                if dist_mid < menor_dist:
                    menor_dist = dist_mid
                    melhor_tx = (idx, tx)

        if melhor_tx is not None:
            idx_tx, tx_obj = melhor_tx
            textos_usados.add(idx_tx)

            nivel_efetivo = _resolver_nivel_bolinha(
                c["level"], tx_obj["level"], tx_obj["xc"], tx_obj["yc"], lajes
            )
            # So processa bolinhas cujo nivel efetivo seja 11 (Viga) ou 13 (Laje)
            if nivel_efetivo not in (11, 13):
                continue

            ang_bolinha = _normalizar_angulo(tx_obj["ang"])
            bolinhas.append({
                "addr_circulo": c["addr"],
                "addr_texto": tx_obj["addr"],
                "val": tx_obj["val"],
                "xc": tx_obj["xc"],
                "yc": tx_obj["yc"],
                "cx_circ": c["xc"],
                "cy_circ": c["yc"],
                "r_circ": c["r"],
                "h": tx_obj["h"],
                "ang": ang_bolinha,
                "ang_bolinha": ang_bolinha,
                "ang_raw": tx_obj.get("ang_raw", tx_obj["ang"]),
                "level": nivel_efetivo,  # 11 = Viga, 13 = Laje
            })

    addrs_txt_apagados = set(b["addr_texto"] for b in bolinhas)
    addrs_circ_apagados = set(b["addr_circulo"] for b in bolinhas)
    for tx in textos_numericos:
        if tx["addr"] not in addrs_txt_apagados:
            obstaculos_viga_exatos.append(("texto", tx["box_exato"]))
    for c in circulos:
        if c["addr"] not in addrs_circ_apagados and c["level"] not in (245, 246):
            obstaculos_viga_exatos.append((
                "texto",
                (c["xc"] - c["r"], c["yc"] - c["r"], c["xc"] + c["r"], c["yc"] + c["r"])
            ))

    # Pareamento geometrico de secoes de viga com titulos de viga
    for v in vigas:
        if v["secao"] is None:
            best_sec = None
            min_d = float("inf")
            for s in secoes_viga_coletadas:
                if s["ang"] == v["ang"]:
                    if v["ang"] == 0.0:
                        if abs(v["y1"] - s["y1"]) <= 45.0:
                            d = math.hypot(v["xc"] - s["xc"], v["yc"] - s["yc"])
                            if d < 180.0 and d < min_d:
                                min_d = d
                                best_sec = s
                    else:
                        if abs(v["x1"] - s["x1"]) <= 45.0:
                            d = math.hypot(v["xc"] - s["xc"], v["yc"] - s["yc"])
                            if d < 180.0 and d < min_d:
                                min_d = d
                                best_sec = s
            if best_sec is not None:
                v["secao"] = best_sec

    return {
        "bolinhas": bolinhas,
        "vigas": vigas,
        "secoes": secoes_viga_coletadas,
        "lajes": lajes,
        "obstaculos": obstaculos,
        "obstaculos_viga_exatos": obstaculos_viga_exatos,
        "linhas_221": linhas_221_existentes,
        "linhas_vert_concreto": linhas_vert_concreto,
        "linhas_horiz_concreto": linhas_horiz_concreto,
        "lines_concreto_exatas": lines_concreto_exatas,
    }


def _associar_bolinha_viga_estendida(cx, cy, ang_b, vigas_geom, lines_concreto):
    """
    Associa uma bolinha (ou secao) a sua viga continua:
      1. Tenta anti_sobreposicao.associar_elemento_a_viga padrao (validando angulo real da viga).
      2. Fallback 1: mesmo angulo (<= 15 graus), projecao longitudinal com folga 30 cm e dt <= 95 cm.
      3. Fallback 2: mesmo angulo (<= 15 graus), no alinhamento transversal da viga (dt <= 45 cm)
         com concreto local presente no corredor (resolve vaos separados por pilar/abertura > 90 cm)
         ou vigas inclinadas (ex: VR4).
    """
    vg_padrao = anti_sobreposicao.associar_elemento_a_viga(cx, cy, ang_b, vigas_geom)
    if vg_padrao is not None:
        ang_real_v = vg_padrao["viga"]["ang"] if vg_padrao.get("viga") else vg_padrao["ang"]
        if _diff_angulo_180(ang_real_v, ang_b) <= 15.0:
            return vg_padrao

    cands_1 = []
    cands_2 = []
    for vg in vigas_geom:
        v_obj = vg.get("viga")
        ang_v = v_obj["ang"] if v_obj else vg["ang"]
        if _diff_angulo_180(ang_v, ang_b) > 15.0:
            continue

        if ang_v == 0.0:
            dt = 0.0
            if cy < vg["t_min"]:
                dt = vg["t_min"] - cy
            elif cy > vg["t_max"]:
                dt = cy - vg["t_max"]
            dl = 0.0
            if cx < vg["l_min"]:
                dl = vg["l_min"] - cx
            elif cx > vg["l_max"]:
                dl = cx - vg["l_max"]

            if dl <= 30.0 and dt <= 95.0:
                cands_1.append((dt + 0.5 * dl, abs(cx - vg["l_txt"]), vg))
            elif dt <= 45.0 and dl <= 600.0:
                tem_conc_local = any(
                    abs(ly1 - ly2) <= 8.0 and abs(lx2 - lx1) > 10.0
                    and (vg["t_min"] - 18.0 <= 0.5 * (ly1 + ly2) <= vg["t_max"] + 18.0)
                    and (min(lx1, lx2) - 45.0 <= cx <= max(lx1, lx2) + 45.0)
                    for lx1, ly1, lx2, ly2, _ in lines_concreto
                )
                if tem_conc_local:
                    outro_no_meio = any(
                        vg2 is not vg
                        and _diff_angulo_180((vg2["viga"]["ang"] if vg2.get("viga") else vg2["ang"]), 0.0) <= 5.0
                        and not (vg2["t_max"] + 15.0 < vg["t_min"] or vg2["t_min"] - 15.0 > vg["t_max"])
                        and min(vg["l_txt"], cx) < vg2["l_txt"] < max(vg["l_txt"], cx)
                        for vg2 in vigas_geom
                    )
                    if not outro_no_meio:
                        cands_2.append((dt + 0.25 * dl, abs(cx - vg["l_txt"]), vg))

        elif ang_v == 90.0:
            dt = 0.0
            if cx < vg["t_min"]:
                dt = vg["t_min"] - cx
            elif cx > vg["t_max"]:
                dt = cx - vg["t_max"]
            dl = 0.0
            if cy < vg["l_min"]:
                dl = vg["l_min"] - cy
            elif cy > vg["l_max"]:
                dl = cy - vg["l_max"]

            if dl <= 30.0 and dt <= 95.0:
                cands_1.append((dt + 0.5 * dl, abs(cy - vg["l_txt"]), vg))
            elif dt <= 45.0 and dl <= 600.0:
                tem_conc_local = any(
                    abs(lx1 - lx2) <= 8.0 and abs(ly2 - ly1) > 10.0
                    and (vg["t_min"] - 18.0 <= 0.5 * (lx1 + lx2) <= vg["t_max"] + 18.0)
                    and (min(ly1, ly2) - 45.0 <= cy <= max(ly1, ly2) + 45.0)
                    for lx1, ly1, lx2, ly2, _ in lines_concreto
                )
                if tem_conc_local:
                    outro_no_meio = any(
                        vg2 is not vg
                        and _diff_angulo_180((vg2["viga"]["ang"] if vg2.get("viga") else vg2["ang"]), 90.0) <= 5.0
                        and not (vg2["t_max"] + 15.0 < vg["t_min"] or vg2["t_min"] - 15.0 > vg["t_max"])
                        and min(vg["l_txt"], cy) < vg2["l_txt"] < max(vg["l_txt"], cy)
                        for vg2 in vigas_geom
                    )
                    if not outro_no_meio:
                        cands_2.append((dt + 0.25 * dl, abs(cy - vg["l_txt"]), vg))
        else:
            # Viga inclinada (ex: VR4)
            rad = math.radians(ang_v)
            ux, uy = math.cos(rad), math.sin(rad)
            nx, ny = -uy, ux
            vx_ref = v_obj["xc"] if v_obj else 0.0
            vy_ref = v_obj["yc"] if v_obj else 0.0
            ds = abs((cx - vx_ref) * ux + (cy - vy_ref) * uy)
            dn = abs((cx - vx_ref) * nx + (cy - vy_ref) * ny)
            if dn <= 65.0 and ds <= 600.0:
                cands_2.append((dn + 0.15 * ds, ds, vg))

    if cands_1:
        cands_1.sort(key=lambda x: (x[0], x[1]))
        return cands_1[0][2]
    if cands_2:
        cands_2.sort(key=lambda x: (x[0], x[1]))
        return cands_2[0][2]
    return None


def _secao_proxima_da_bolinha(b, secoes_cands, ang_ref, dist_long_max=90.0):
    """
    Retorna a secao mais proxima de 'b' SOMENTE se estiver genuinamente perto da bolinha
    (distancia longitudinal <= dist_long_max e transversal <= 55 cm, com mesmo angulo).
    Nunca retorna uma secao distante em outro vao.
    """
    cx = b.get("cx_circ", b["xc"])
    cy = b.get("cy_circ", b["yc"])
    rad = math.radians(ang_ref)
    ux, uy = math.cos(rad), math.sin(rad)
    nx, ny = -uy, ux

    melhor = None
    menor_d = float("inf")
    for s in secoes_cands:
        if _diff_angulo_180(s["ang"], ang_ref) > 15.0:
            continue
        sbx = s.get("box_exato") or s.get("bbox")
        if ang_ref == 0.0 and sbx is not None:
            dl = max(0.0, sbx[0] - cx, cx - sbx[2])
            dt = abs(0.5 * (sbx[1] + sbx[3]) - cy)
        elif ang_ref == 90.0 and sbx is not None:
            dl = max(0.0, sbx[1] - cy, cy - sbx[3])
            dt = abs(0.5 * (sbx[0] + sbx[2]) - cx)
        else:
            smx = 0.5 * (s["x1"] + s["x2"])
            smy = 0.5 * (s["y1"] + s["y2"])
            dl = max(0.0, abs((cx - smx) * ux + (cy - smy) * uy) - 0.5 * len(s["texto"]) * s["h"])
            dt = abs((cx - smx) * nx + (cy - smy) * ny)

        if dl <= dist_long_max and dt <= 55.0:
            score = dl + 0.5 * dt
            if score < menor_d:
                menor_d = score
                melhor = s
    return melhor


def _agrupar_bolinhas_vigas(bolinhas_viga, vigas, secoes, lines_concreto=None):
    """
    Agrupa bolinhas de Nivel 11 por viga usando o mapeamento da viga branca continua.
    Se uma viga inteira tiver o mesmo valor de inversao (ex: V501-A ou V513-A com 40cm em
    todos os vaos), gera apenas 1 unica indicacao na viga, apagando todas as bolinhas repetidas.
    Ancora cada bolinha apenas em secao genuinamente proxima (<= 90 cm), nunca saltando para
    v['secao'] distante em outro vao.
    """
    lines_conc = lines_concreto or []
    vigas_geom = anti_sobreposicao.mapear_vigas_continuas(vigas, lines_conc)
    bolinhas_por_viga = {}
    for vg in vigas_geom:
        bolinhas_por_viga[vg["nome"]] = {"viga": vg["viga"], "vg": vg, "bolinhas": []}

    bolinhas_avulsas = []
    for b in bolinhas_viga:
        cx_b = b.get("cx_circ", b["xc"])
        cy_b = b.get("cy_circ", b["yc"])
        vg = _associar_bolinha_viga_estendida(cx_b, cy_b, b["ang"], vigas_geom, lines_conc)
        if vg is not None:
            bolinhas_por_viga[vg["nome"]]["bolinhas"].append(b)
        else:
            bolinhas_avulsas.append(b)

    resultado = []
    for v_nome, data in bolinhas_por_viga.items():
        v = data["viga"]
        vg = data["vg"]
        blist = data["bolinhas"]
        if not blist:
            continue

        cands_sec = [
            s for s in secoes
            if _associar_bolinha_viga_estendida(s["xc"], s["yc"], s["ang"], vigas_geom, lines_conc) is vg
        ]

        por_valor = {}
        for b in blist:
            v_key = round(b["val"], 1)
            por_valor.setdefault(v_key, []).append(b)

        for val, grp in por_valor.items():
            grp_ord = sorted(
                grp,
                key=lambda item: (round(item.get("cx_circ", item["xc"]), 1), round(item.get("cy_circ", item["yc"]), 1))
            )
            ang_ref = v["ang"] if (v is not None and _diff_angulo_180(v["ang"], grp_ord[0]["ang"]) <= 15.0) else grp_ord[0]["ang"]
            for b_item in grp_ord:
                b_item["_sec_prox"] = _secao_proxima_da_bolinha(b_item, cands_sec, ang_ref, dist_long_max=90.0)

            sec_usar = grp_ord[0].get("_sec_prox")
            resultado.append((v, vg, sec_usar, grp_ord, val))

    bolinhas_avulsas.sort(
        key=lambda item: (round(item.get("cx_circ", item["xc"]), 1), round(item.get("cy_circ", item["yc"]), 1))
    )
    for b in bolinhas_avulsas:
        b["_sec_prox"] = _secao_proxima_da_bolinha(b, secoes, b["ang"], dist_long_max=90.0)
        resultado.append((None, None, b["_sec_prox"], [b], b["val"]))

    return resultado


def _obter_corredor_viga_local(cx, cy, ang_inv, vg, lines_concreto):
    """
    Obtem o corredor local de concreto (t_min, t_max, l_min, l_max, tem_corredor) ao redor
    da bolinha (cx, cy), expandindo l_min/l_max sobre segmentos contiguos locais quando a
    bolinha estiver alem do cluster principal de vg, ou inferindo das linhas de concreto
    quando vg for None.
    """
    if ang_inv == 0.0:
        segs_h = [
            (0.5 * (ly1 + ly2), min(lx1, lx2), max(lx1, lx2))
            for lx1, ly1, lx2, ly2, _ in lines_concreto
            if abs(ly1 - ly2) <= 8.0 and abs(lx2 - lx1) > 10.0
        ]
        if vg is not None and _diff_angulo_180(vg["ang"], 0.0) <= 5.0:
            t_min, t_max = vg["t_min"], vg["t_max"]
            l_min, l_max = vg["l_min"], vg["l_max"]
            if cx < l_min or cx > l_max:
                faixa = sorted([s for s in segs_h if t_min - 15.0 <= s[0] <= t_max + 15.0], key=lambda x: x[1])
                clusters = []
                for s in faixa:
                    if not clusters or s[1] > clusters[-1][1] + 90.0:
                        clusters.append([s[1], s[2]])
                    else:
                        clusters[-1][1] = max(clusters[-1][1], s[2])
                for c in clusters:
                    if c[0] - 50.0 <= cx <= c[1] + 50.0:
                        l_min = min(l_min, c[0]) if abs(cx - l_min) < abs(cx - c[0]) else c[0]
                        l_max = max(l_max, c[1]) if abs(cx - l_max) < abs(cx - c[1]) else c[1]
                        break
            return (t_min, t_max, l_min, l_max, True)

        perto = [s for s in segs_h if abs(s[0] - cy) <= 55.0 and (s[1] - 60.0 <= cx <= s[2] + 60.0)]
        if not perto:
            return (cy - 7.5, cy + 7.5, cx - 180.0, cx + 180.0, False)
        ys = sorted(list(set(round(s[0], 1) for s in perto)))
        par = None
        menor_d = float("inf")
        for i in range(len(ys)):
            for j in range(i + 1, len(ys)):
                w = ys[j] - ys[i]
                if 9.0 <= w <= 45.0:
                    dc = abs(0.5 * (ys[i] + ys[j]) - cy)
                    if dc < menor_d:
                        menor_d = dc
                        par = (ys[i], ys[j])
        if par:
            t_min, t_max = par
        else:
            y_near = min(ys, key=lambda yv: abs(yv - cy))
            t_min, t_max = (y_near - 15.0, y_near) if cy >= y_near else (y_near, y_near + 15.0)
        faixa = sorted([s for s in segs_h if t_min - 12.0 <= s[0] <= t_max + 12.0], key=lambda x: x[1])
        clusters = []
        for s in faixa:
            if not clusters or s[1] > clusters[-1][1] + 90.0:
                clusters.append([s[1], s[2]])
            else:
                clusters[-1][1] = max(clusters[-1][1], s[2])
        l_min, l_max = cx - 150.0, cx + 150.0
        for c in clusters:
            if c[0] - 50.0 <= cx <= c[1] + 50.0:
                l_min, l_max = c[0], c[1]
                break
        return (t_min, t_max, l_min, l_max, True)

    elif ang_inv == 90.0:
        segs_v = [
            (0.5 * (lx1 + lx2), min(ly1, ly2), max(ly1, ly2))
            for lx1, ly1, lx2, ly2, _ in lines_concreto
            if abs(lx1 - lx2) <= 8.0 and abs(ly2 - ly1) > 10.0
        ]
        if vg is not None and _diff_angulo_180(vg["ang"], 90.0) <= 5.0:
            t_min, t_max = vg["t_min"], vg["t_max"]
            l_min, l_max = vg["l_min"], vg["l_max"]
            if cy < l_min or cy > l_max:
                faixa = sorted([s for s in segs_v if t_min - 15.0 <= s[0] <= t_max + 15.0], key=lambda x: x[1])
                clusters = []
                for s in faixa:
                    if not clusters or s[1] > clusters[-1][1] + 90.0:
                        clusters.append([s[1], s[2]])
                    else:
                        clusters[-1][1] = max(clusters[-1][1], s[2])
                for c in clusters:
                    if c[0] - 50.0 <= cy <= c[1] + 50.0:
                        l_min = min(l_min, c[0]) if abs(cy - l_min) < abs(cy - c[0]) else c[0]
                        l_max = max(l_max, c[1]) if abs(cy - l_max) < abs(cy - c[1]) else c[1]
                        break
            return (t_min, t_max, l_min, l_max, True)

        perto = [s for s in segs_v if abs(s[0] - cx) <= 55.0 and (s[1] - 60.0 <= cy <= s[2] + 60.0)]
        if not perto:
            return (cx - 7.5, cx + 7.5, cy - 180.0, cy + 180.0, False)
        xs = sorted(list(set(round(s[0], 1) for s in perto)))
        par = None
        menor_d = float("inf")
        for i in range(len(xs)):
            for j in range(i + 1, len(xs)):
                w = xs[j] - xs[i]
                if 9.0 <= w <= 45.0:
                    dc = abs(0.5 * (xs[i] + xs[j]) - cx)
                    if dc < menor_d:
                        menor_d = dc
                        par = (xs[i], xs[j])
        if par:
            t_min, t_max = par
        else:
            x_near = min(xs, key=lambda xv: abs(xv - cx))
            t_min, t_max = (x_near, x_near + 15.0) if cx <= x_near else (x_near - 15.0, x_near)
        faixa = sorted([s for s in segs_v if t_min - 12.0 <= s[0] <= t_max + 12.0], key=lambda x: x[1])
        clusters = []
        for s in faixa:
            if not clusters or s[1] > clusters[-1][1] + 90.0:
                clusters.append([s[1], s[2]])
            else:
                clusters[-1][1] = max(clusters[-1][1], s[2])
        l_min, l_max = cy - 150.0, cy + 150.0
        for c in clusters:
            if c[0] - 50.0 <= cy <= c[1] + 50.0:
                l_min, l_max = c[0], c[1]
                break
        return (t_min, t_max, l_min, l_max, True)

    else:
        # Viga inclinada em referencial local (ux, uy) e normal (nx, ny) centrado em (cx, cy)
        rad = math.radians(ang_inv)
        ux, uy = math.cos(rad), math.sin(rad)
        nx, ny = -uy, ux
        segs_i = []
        for lx1, ly1, lx2, ly2, _ in lines_concreto:
            dx_s, dy_s = lx2 - lx1, ly2 - ly1
            slen = math.hypot(dx_s, dy_s)
            if slen <= 10.0:
                continue
            if abs(dx_s * nx + dy_s * ny) <= 0.15 * slen:
                s1 = (lx1 - cx) * ux + (ly1 - cy) * uy
                s2 = (lx2 - cx) * ux + (ly2 - cy) * uy
                qm = 0.5 * (((lx1 - cx) * nx + (ly1 - cy) * ny) + ((lx2 - cx) * nx + (ly2 - cy) * ny))
                if min(s1, s2) - 60.0 <= 0.0 <= max(s1, s2) + 60.0 and abs(qm) <= 60.0:
                    segs_i.append((qm, min(s1, s2), max(s1, s2)))
        if not segs_i:
            return (-7.5, 7.5, -180.0, 180.0, False)
        qs = sorted(list(set(round(s[0], 1) for s in segs_i)))
        par = None
        menor_d = float("inf")
        for i in range(len(qs)):
            for j in range(i + 1, len(qs)):
                w = qs[j] - qs[i]
                if 9.0 <= w <= 45.0:
                    dc = abs(0.5 * (qs[i] + qs[j]))
                    if dc < menor_d:
                        menor_d = dc
                        par = (qs[i], qs[j])
        if par:
            t_min, t_max = par
        else:
            q_near = min(qs, key=lambda qv: abs(qv))
            t_min, t_max = (q_near - 15.0, q_near) if q_near <= 0.0 else (q_near, q_near + 15.0)
        l_min = min(s[1] for s in segs_i)
        l_max = max(s[2] for s in segs_i)
        return (t_min, t_max, l_min, l_max, True)


def _calcular_melhor_posicao_inversao_viga(
    b_cand, viga, vg, sec_prox, novo_texto, h_txt, limite_sem_seta,
    obstaculos_viga_exatos, lines_concreto, linhas_221_ativas,
    corredores_vigas=None
):
    """
    Calcula o posicionamento otimo para 'VIGA INVERTIDA xCM' ancorado na bolinha 'b_cand':
      - Orientacao TRAVADA na orientacao original da bolinha (alinhamento fino <= 15 graus com a viga; JAMAIS gira 90 <-> 0).
      - Tier 1 (SEM SETA): mesma face original da viga e d_box <= limite_sem_seta (40 cm), zero colisao.
      - Tier 2 (COM SETA Nivel 221): mesma orientacao, ordenado por menor distancia ao ponto original,
        validando caixa de texto (incluindo pilares, cubetas e miolo de TODAS as vigas) e haste da seta
        ate a face da viga sem atravessar outras vigas.
    Retorna dicionario completo da solucao escolhida.
    """
    cx_orig = b_cand.get("cx_circ", b_cand["xc"])
    cy_orig = b_cand.get("cy_circ", b_cand["yc"])
    ang_bol = b_cand.get("ang_bolinha", b_cand["ang"])
    if viga is not None and _diff_angulo_180(viga["ang"], ang_bol) <= 15.0:
        ang_inv = viga["ang"]
    else:
        ang_inv = ang_bol

    comp = len(novo_texto) * h_txt * 1.0
    t_min, t_max, l_min, l_max, tem_corredor = _obter_corredor_viga_local(
        cx_orig, cy_orig, ang_inv, vg, lines_concreto
    )

    pilar_polys = [bx for tp, bx in obstaculos_viga_exatos if tp == "pilar_poly"]
    cubetas_boxes = [bx for tp, bx in obstaculos_viga_exatos if tp == "cubeta"]
    textos_e_outros = [bx for tp, bx in obstaculos_viga_exatos if tp not in ("pilar_poly", "cubeta")]

    # Monta lista de miolos de TODAS as vigas mapeadas (evita colocar texto dentro de qualquer viga!)
    miolos_vigas = []
    if tem_corredor and (t_max - t_min) >= 6.0:
        if ang_inv == 0.0:
            miolos_vigas.append((l_min, t_min + 1.0, l_max, t_max - 1.0))
        elif ang_inv == 90.0:
            miolos_vigas.append((t_min + 1.0, l_min, t_max - 1.0, l_max))
    for cv in (corredores_vigas or []):
        c_ang, c_tmin, c_tmax, c_lmin, c_lmax = cv
        if (c_tmax - c_tmin) < 6.0 or (c_tmax - c_tmin) > 65.0:
            continue
        if c_ang == 0.0:
            miolos_vigas.append((c_lmin, c_tmin + 1.0, c_lmax, c_tmax - 1.0))
        elif c_ang == 90.0:
            miolos_vigas.append((c_tmin + 1.0, c_lmin, c_tmax - 1.0, c_lmax))

    def _invade_miolo_viga(bx_chk):
        for mbx in miolos_vigas:
            if _boxes_colidem(bx_chk, mbx, margem=0.0):
                return True
        return False

    def _caixa_texto_livre(cx_t, cy_t):
        bx = _bbox_texto_inversao(cx_t, cy_t, h_txt, ang_inv, novo_texto)
        if _invade_miolo_viga(bx):
            return None
        rbx = _rbox_texto_inversao(cx_t, cy_t, h_txt, ang_inv, novo_texto)
        if any(_boxes_colidem(bx, pb, margem=2.5) for pb in pilar_polys):
            return None
        if any(_boxes_colidem(bx, cb, margem=1.5) for cb in cubetas_boxes):
            return None
        if any(_boxes_colidem(bx, ob, margem=1.2) for ob in textos_e_outros):
            return None
        for lx1, ly1, lx2, ly2, _ in lines_concreto:
            if anti_sobreposicao._segmento_colide_box(lx1, ly1, lx2, ly2, rbx, margem=2.0):
                return None
            if anti_sobreposicao._segmento_colide_box(lx1, ly1, lx2, ly2, bx, margem=0.1):
                return None
        for sx1, sy1, sx2, sy2 in linhas_221_ativas:
            if anti_sobreposicao._segmento_colide_box(sx1, sy1, sx2, sy2, bx, margem=1.0):
                return None
        return bx

    def _ponto_em_pilar_poly(px, py, folga=6.0):
        return any(
            (pb[0] - folga <= px <= pb[2] + folga) and (pb[1] - folga <= py <= pb[3] + folga)
            for pb in pilar_polys
        )

    # Determina lado original da bolinha (+1 = acima/esquerda, -1 = abaixo/direita)
    if ang_inv == 0.0:
        t_meio = 0.5 * (t_min + t_max)
        lado_orig = 1 if cy_orig >= t_meio else -1
    elif ang_inv == 90.0:
        t_meio = 0.5 * (t_min + t_max)
        lado_orig = 1 if cx_orig <= t_meio else -1
    else:
        t_meio = 0.5 * (t_min + t_max)
        lado_orig = 1 if 0.0 >= t_meio else -1

    # -------------------------------------------------------------------------
    # TIER 1: SEM SETA (mesma face original, mesma orientacao, d_box <= 40 cm)
    # -------------------------------------------------------------------------
    sec_bx = (sec_prox.get("box_exato") or sec_prox.get("bbox")) if sec_prox else None
    cands_tier1 = []

    if ang_inv == 0.0:
        ys_face = []
        sec_mesmo_lado = False
        if sec_prox is not None and sec_bx is not None:
            sec_lado = 1 if sec_prox["yc"] >= t_meio else -1
            if sec_lado == lado_orig:
                if (lado_orig > 0 and sec_prox["y1"] >= t_max + 2.0) or (lado_orig < 0 and sec_prox["y1"] + h_txt <= t_min - 2.0):
                    ys_face.append(sec_prox["y1"])
                    sec_mesmo_lado = True
        y_std1 = (t_max + 4.5) if lado_orig > 0 else (t_min - h_txt - 4.5)
        y_std2 = (t_max + 6.5) if lado_orig > 0 else (t_min - h_txt - 6.5)
        for y_c in (y_std1, y_std2):
            if all(abs(y_c - ye) > 0.5 for ye in ys_face):
                ys_face.append(y_c)

        xs_long = []
        if sec_mesmo_lado and sec_bx is not None:
            xs_long.append((sec_bx[2] + 8.0, True))
            xs_long.append((sec_bx[0] - comp - 8.0, True))
        x_center = cx_orig - 0.5 * comp
        xs_long.append((x_center, False))
        max_shift = int(math.ceil((0.5 * comp + limite_sem_seta) / 8.0))
        for step_i in range(1, max_shift + 1):
            for sgn in (1.0, -1.0):
                xs_long.append((x_center + sgn * step_i * 8.0, False))

        folga_ext = 20.0 if (l_max - l_min) >= comp else 35.0
        for y_c in ys_face:
            for x_c, eh_adj_sec in xs_long:
                if tem_corredor and (x_c < l_min - folga_ext or x_c + comp > l_max + folga_ext):
                    continue
                bx_t = _bbox_texto_inversao(x_c, y_c, h_txt, 0.0, novo_texto)
                d_box = _dist_ponto_a_box(cx_orig, cy_orig, bx_t)
                if d_box > limite_sem_seta:
                    continue
                d_mid = math.hypot(0.5 * (bx_t[0] + bx_t[2]) - cx_orig, 0.5 * (bx_t[1] + bx_t[3]) - cy_orig)
                bonus = -8.0 if eh_adj_sec else 0.0
                cands_tier1.append((round(d_box, 1), d_mid + bonus, x_c, y_c))

    elif ang_inv == 90.0:
        xs_face = []
        sec_mesmo_lado = False
        if sec_prox is not None and sec_bx is not None:
            sec_lado = 1 if sec_prox["xc"] <= t_meio else -1
            if sec_lado == lado_orig:
                if (lado_orig > 0 and sec_prox["x1"] <= t_min - 2.0) or (lado_orig < 0 and sec_prox["x1"] - h_txt >= t_max + 2.0):
                    xs_face.append(sec_prox["x1"])
                    sec_mesmo_lado = True
        x_std1 = (t_min - 4.5) if lado_orig > 0 else (t_max + h_txt + 4.5)
        x_std2 = (t_min - 6.5) if lado_orig > 0 else (t_max + h_txt + 6.5)
        for x_c in (x_std1, x_std2):
            if all(abs(x_c - xe) > 0.5 for xe in xs_face):
                xs_face.append(x_c)

        ys_long = []
        if sec_mesmo_lado and sec_bx is not None:
            ys_long.append((sec_bx[3] + 8.0, True))
            ys_long.append((sec_bx[1] - comp - 8.0, True))
        y_center = cy_orig - 0.5 * comp
        ys_long.append((y_center, False))
        max_shift = int(math.ceil((0.5 * comp + limite_sem_seta) / 8.0))
        for step_i in range(1, max_shift + 1):
            for sgn in (1.0, -1.0):
                ys_long.append((y_center + sgn * step_i * 8.0, False))

        folga_ext = 20.0 if (l_max - l_min) >= comp else 35.0
        for x_c in xs_face:
            for y_c, eh_adj_sec in ys_long:
                if tem_corredor and (y_c < l_min - folga_ext or y_c + comp > l_max + folga_ext):
                    continue
                bx_t = _bbox_texto_inversao(x_c, y_c, h_txt, 90.0, novo_texto)
                d_box = _dist_ponto_a_box(cx_orig, cy_orig, bx_t)
                if d_box > limite_sem_seta:
                    continue
                d_mid = math.hypot(0.5 * (bx_t[0] + bx_t[2]) - cx_orig, 0.5 * (bx_t[1] + bx_t[3]) - cy_orig)
                bonus = -8.0 if eh_adj_sec else 0.0
                cands_tier1.append((round(d_box, 1), d_mid + bonus, x_c, y_c))

    else:
        rad = math.radians(ang_inv)
        ux, uy = math.cos(rad), math.sin(rad)
        nx, ny = -uy, ux
        q_std = (t_max + 4.5) if lado_orig > 0 else (t_min - h_txt - 4.5)
        max_shift = int(math.ceil((0.5 * comp + limite_sem_seta) / 8.0))
        s_list = [-0.5 * comp] + [-0.5 * comp + sgn * i * 8.0 for i in range(1, max_shift + 1) for sgn in (1.0, -1.0)]
        for s_c in s_list:
            if tem_corredor and (s_c < l_min - 25.0 or s_c + comp > l_max + 25.0):
                continue
            x_c = cx_orig + ux * s_c + nx * q_std
            y_c = cy_orig + uy * s_c + ny * q_std
            bx_t = _bbox_texto_inversao(x_c, y_c, h_txt, ang_inv, novo_texto)
            d_box = _dist_ponto_a_box(cx_orig, cy_orig, bx_t)
            if d_box <= limite_sem_seta:
                d_mid = math.hypot(0.5 * (bx_t[0] + bx_t[2]) - cx_orig, 0.5 * (bx_t[1] + bx_t[3]) - cy_orig)
                cands_tier1.append((round(d_box, 1), d_mid, x_c, y_c))

    cands_tier1.sort(key=lambda item: (item[0], item[1]))
    for d_box_1, score_mid_1, x_1, y_1 in cands_tier1:
        bx_ok = _caixa_texto_livre(x_1, y_1)
        if bx_ok is not None:
            return {
                "x": x_1, "y": y_1, "ang": ang_inv, "bbox": bx_ok,
                "precisa_seta": False, "xa": cx_orig, "ya": cy_orig,
                "x_j": x_1, "y_j": y_1,
                "score": (0, d_box_1, score_mid_1),
            }

    # -------------------------------------------------------------------------
    # TIER 2: COM SETA (mesma orientacao ang_inv TRAVADA, menor distancia)
    # -------------------------------------------------------------------------
    cands_tier2_raw = []
    raios_perp = (4.5, 10.0, 16.0, 22.0, 30.0, 40.0, 52.0, 66.0, 82.0, 100.0, 120.0, 145.0, 170.0, 200.0, 235.0, 275.0)
    shifts_long = (
        0.0, 5.0, -5.0, 10.0, -10.0, 16.0, -16.0, 24.0, -24.0, 34.0, -34.0,
        46.0, -46.0, 62.0, -62.0, 82.0, -82.0, 108.0, -108.0, 140.0, -140.0,
        180.0, -180.0, 225.0, -225.0, 275.0, -275.0, 330.0, -330.0
    )

    # Inclui tambem centralizacao exata no vao da viga (resolve vaos de ~230-250 cm sem pular o ponto central)
    extra_long_pos = []
    if tem_corredor and (l_max - l_min) >= comp * 0.8:
        extra_long_pos.extend([
            0.5 * (l_min + l_max) - 0.5 * comp,
            l_min + 5.0,
            l_max - comp - 5.0,
        ])

    if ang_inv == 0.0:
        # (a) Mesma face deslizando alem de 40 cm + (b) face oposta / afastamentos perpendiculares
        y_same_face = (t_max + 4.5) if lado_orig > 0 else (t_min - h_txt - 4.5)
        for dl_s in shifts_long:
            xs_cand = cx_orig - 0.5 * comp + dl_s
            if tem_corredor and (l_min - 35.0 <= xs_cand) and (xs_cand + comp <= l_max + 35.0):
                cands_tier2_raw.append((xs_cand, y_same_face, True))
        for xs_ex in extra_long_pos:
            cands_tier2_raw.append((xs_ex, y_same_face, True))

        for s_lado in (lado_orig, -lado_orig):
            eh_mesmo = (s_lado == lado_orig)
            for r in raios_perp:
                cy_r = (t_max + r) if s_lado > 0 else (t_min - h_txt - r)
                for dl_s in shifts_long:
                    cands_tier2_raw.append((cx_orig - 0.5 * comp + dl_s, cy_r, eh_mesmo))
                for xs_ex in extra_long_pos:
                    cands_tier2_raw.append((xs_ex, cy_r, eh_mesmo))
            for r in raios_perp:
                for dy_s in (0.0, 14.0, -14.0, 28.0, -28.0, 45.0, -45.0):
                    cy_lat = cy_orig - 0.5 * h_txt + dy_s
                    mesmo_lat = ((cy_lat + 0.5 * h_txt >= t_meio) == (lado_orig > 0))
                    if mesmo_lat == eh_mesmo:
                        cands_tier2_raw.append((cx_orig + r, cy_lat, eh_mesmo))
                        cands_tier2_raw.append((cx_orig - r - comp, cy_lat, eh_mesmo))

    elif ang_inv == 90.0:
        x_same_face = (t_min - 4.5) if lado_orig > 0 else (t_max + h_txt + 4.5)
        for dl_s in shifts_long:
            ys_cand = cy_orig - 0.5 * comp + dl_s
            if tem_corredor and (l_min - 35.0 <= ys_cand) and (ys_cand + comp <= l_max + 35.0):
                cands_tier2_raw.append((x_same_face, ys_cand, True))
        for ys_ex in extra_long_pos:
            cands_tier2_raw.append((x_same_face, ys_ex, True))

        for s_lado in (lado_orig, -lado_orig):
            eh_mesmo = (s_lado == lado_orig)
            for r in raios_perp:
                cx_r = (t_min - r) if s_lado > 0 else (t_max + h_txt + r)
                for dl_s in shifts_long:
                    cands_tier2_raw.append((cx_r, cy_orig - 0.5 * comp + dl_s, eh_mesmo))
                for ys_ex in extra_long_pos:
                    cands_tier2_raw.append((cx_r, ys_ex, eh_mesmo))
            for r in raios_perp:
                for dx_s in (0.0, 14.0, -14.0, 28.0, -28.0, 45.0, -45.0):
                    cx_lat = cx_orig + 0.5 * h_txt + dx_s
                    mesmo_lat = ((cx_lat - 0.5 * h_txt <= t_meio) == (lado_orig > 0))
                    if mesmo_lat == eh_mesmo:
                        cands_tier2_raw.append((cx_lat, cy_orig + r, eh_mesmo))
                        cands_tier2_raw.append((cx_lat, cy_orig - r - comp, eh_mesmo))

    else:
        rad = math.radians(ang_inv)
        ux, uy = math.cos(rad), math.sin(rad)
        nx, ny = -uy, ux
        for s_lado in (lado_orig, -lado_orig):
            eh_mesmo = (s_lado == lado_orig)
            for r in raios_perp:
                q_r = (t_max + r) if s_lado > 0 else (t_min - h_txt - r)
                for dl_s in shifts_long:
                    s_c = -0.5 * comp + dl_s
                    cands_tier2_raw.append((
                        cx_orig + ux * s_c + nx * q_r,
                        cy_orig + uy * s_c + ny * q_r,
                        eh_mesmo
                    ))

    # Deduplica e ordena estritamente por proximidade ao ponto original (forte preferencia pelo mesmo lado!)
    vistos_t2 = set()
    cands_tier2 = []
    for cs_x, cs_y, eh_mesmo in cands_tier2_raw:
        k_pos = (round(cs_x, 1), round(cs_y, 1))
        if k_pos in vistos_t2:
            continue
        vistos_t2.add(k_pos)
        bx_c = _bbox_texto_inversao(cs_x, cs_y, h_txt, ang_inv, novo_texto)
        d_box = _dist_ponto_a_box(cx_orig, cy_orig, bx_c)
        d_mid = math.hypot(0.5 * (bx_c[0] + bx_c[2]) - cx_orig, 0.5 * (bx_c[1] + bx_c[3]) - cy_orig)
        pen_lado = 0.0 if eh_mesmo else 65.0
        cands_tier2.append((pen_lado + d_box + 0.08 * d_mid, d_box, d_mid, cs_x, cs_y, bx_c))

    cands_tier2.sort(key=lambda item: item[0])

    def _alvos_seta_para_candidato(cs_x, cs_y, bx_c):
        """Gera pontos alvo na face da viga mais proxima do texto (fora de poligonos de pilares)."""
        alvos_raw = []
        offs_alvo = (
            12.0, -12.0, 24.0, -24.0, 40.0, -40.0, 65.0, -65.0,
            95.0, -95.0, 130.0, -130.0, 170.0, -170.0, 220.0, -220.0, 280.0, -280.0
        )
        fracs_alvo = (0.5, 0.25, 0.75, 0.12, 0.88, 0.04, 0.96)
        if ang_inv == 0.0:
            y_face_alvo = t_max if (0.5 * (bx_c[1] + bx_c[3]) >= t_meio) else t_min
            if not tem_corredor:
                y_face_alvo = cy_orig
            x_base_a = max(l_min + 3.0, min(l_max - 3.0, cx_orig)) if tem_corredor and l_max > l_min + 6.0 else cx_orig
            alvos_raw.append((x_base_a, y_face_alvo))
            for frac in fracs_alvo:
                xa_p = cs_x + frac * comp
                if tem_corredor and (l_min + 3.0 <= xa_p <= l_max - 3.0) and abs(xa_p - cx_orig) <= 380.0:
                    alvos_raw.append((xa_p, y_face_alvo))
            for off_a in offs_alvo:
                xa_try = x_base_a + off_a
                if not tem_corredor or (l_min + 2.0 <= xa_try <= l_max - 2.0):
                    alvos_raw.append((xa_try, y_face_alvo))
        elif ang_inv == 90.0:
            x_face_alvo = t_min if (0.5 * (bx_c[0] + bx_c[2]) <= t_meio) else t_max
            if not tem_corredor:
                x_face_alvo = cx_orig
            y_base_a = max(l_min + 3.0, min(l_max - 3.0, cy_orig)) if tem_corredor and l_max > l_min + 6.0 else cy_orig
            alvos_raw.append((x_face_alvo, y_base_a))
            for frac in fracs_alvo:
                ya_p = cs_y + frac * comp
                if tem_corredor and (l_min + 3.0 <= ya_p <= l_max - 3.0) and abs(ya_p - cy_orig) <= 380.0:
                    alvos_raw.append((x_face_alvo, ya_p))
            for off_a in offs_alvo:
                ya_try = y_base_a + off_a
                if not tem_corredor or (l_min + 2.0 <= ya_try <= l_max - 2.0):
                    alvos_raw.append((x_face_alvo, ya_try))
        else:
            rad = math.radians(ang_inv)
            ux, uy = math.cos(rad), math.sin(rad)
            nx, ny = -uy, ux
            q_cand = (0.5 * (bx_c[0] + bx_c[2]) - cx_orig) * nx + (0.5 * (bx_c[1] + bx_c[3]) - cy_orig) * ny
            q_face = (t_max if q_cand >= t_meio else t_min) if tem_corredor else 0.0
            alvos_raw.append((cx_orig + nx * q_face, cy_orig + ny * q_face))
            for off_a in offs_alvo:
                if not tem_corredor or (l_min + 2.0 <= off_a <= l_max - 2.0):
                    alvos_raw.append((cx_orig + ux * off_a + nx * q_face, cy_orig + uy * off_a + ny * q_face))

        vistos_a = set()
        alvos = []
        for ax, ay in alvos_raw:
            ka = (round(ax, 1), round(ay, 1))
            if ka not in vistos_a:
                vistos_a.add(ka)
                alvos.append((ax, ay))

        filtrados = [pt for pt in alvos if not _ponto_em_pilar_poly(pt[0], pt[1], folga=6.0)]
        return filtrados if filtrados else alvos

    def _validar_haste_seta(cs_x, cs_y, xa_s, ya_s, permitir_cruzar_cubeta=False, permitir_cruzar_viga=False):
        if _ponto_em_pilar_poly(xa_s, ya_s, folga=6.0):
            return None
        x_j, y_j = _ponto_saida_seta_inversao(cs_x, cs_y, comp, h_txt, ang_inv, xa_s, ya_s)
        dist_h = math.hypot(x_j - xa_s, y_j - ya_s)
        if dist_h < 9.5:
            return None
        for pb in pilar_polys:
            if anti_sobreposicao._segmento_colide_box(x_j, y_j, xa_s, ya_s, pb, margem=1.0):
                return None
        for ob in textos_e_outros:
            if anti_sobreposicao._segmento_colide_box(x_j, y_j, xa_s, ya_s, ob, margem=0.5):
                return None
        if not permitir_cruzar_viga:
            # Recua 3 cm da ponta (xa_s, ya_s) para nao acusar a propria face-alvo da viga
            dx_h = xa_s - x_j
            dy_h = ya_s - y_j
            f_rec = max(0.0, (dist_h - 3.0) / dist_h)
            xh_fim = x_j + dx_h * f_rec
            yh_fim = y_j + dy_h * f_rec
            for mbx in miolos_vigas:
                if anti_sobreposicao._segmento_colide_box(x_j, y_j, xh_fim, yh_fim, mbx, margem=-0.5):
                    return None
        if not permitir_cruzar_cubeta:
            for cb in cubetas_boxes:
                if anti_sobreposicao._segmento_colide_box(x_j, y_j, xa_s, ya_s, cb, margem=0.2):
                    return None
        return (x_j, y_j)

    # Passada 2A: caixa 100% livre + haste da seta sem tocar nada (nem cubetas nem outras vigas)
    # Passada 2B: caixa 100% livre + haste da seta sem tocar pilares/textos/outras vigas (permitindo cubeta)
    # Passada 2B2: caixa 100% livre + haste da seta sem tocar pilares/textos (ultimo recurso)
    for permitir_cubeta_haste, permitir_viga_haste in ((False, False), (True, False), (True, True)):
        melhor_p2 = None
        for ord_score, d_box_2, d_mid_2, cs_x, cs_y, _ in cands_tier2:
            if melhor_p2 is not None and ord_score >= melhor_p2[0]:
                break
            bx_ok = _caixa_texto_livre(cs_x, cs_y)
            if bx_ok is None:
                continue
            for xa_s, ya_s in _alvos_seta_para_candidato(cs_x, cs_y, bx_ok):
                res_j = _validar_haste_seta(
                    cs_x, cs_y, xa_s, ya_s,
                    permitir_cruzar_cubeta=permitir_cubeta_haste,
                    permitir_cruzar_viga=permitir_viga_haste,
                )
                if res_j is not None:
                    dist_haste = math.hypot(res_j[0] - xa_s, res_j[1] - ya_s)
                    custo_total = ord_score + 0.35 * dist_haste
                    if melhor_p2 is None or custo_total < melhor_p2[0]:
                        melhor_p2 = (
                            custo_total,
                            {
                                "x": cs_x, "y": cs_y, "ang": ang_inv, "bbox": bx_ok,
                                "precisa_seta": True, "xa": xa_s, "ya": ya_s,
                                "x_j": res_j[0], "y_j": res_j[1],
                                "score": (1 if not permitir_cubeta_haste else 2, custo_total, d_mid_2),
                            }
                        )
        if melhor_p2 is not None:
            return melhor_p2[1]

    # Passada 2C (Fallback extremo de seguranca): menor penalidade FORA de poligonos de pilares, sempre com seta
    melhor_fb = None
    menor_pen = float("inf")
    for ord_score, d_box_2, d_mid_2, cs_x, cs_y, bx_c in cands_tier2:
        if _invade_miolo_viga(bx_c):
            continue
        if any(_boxes_colidem(bx_c, pb, margem=2.0) for pb in pilar_polys):
            continue
        n_cub = sum(1 for cb in cubetas_boxes if _boxes_colidem(bx_c, cb, margem=0.5))
        n_txt = sum(1 for ob in textos_e_outros if _boxes_colidem(bx_c, ob, margem=0.5))
        n_conc = sum(
            1 for lx1, ly1, lx2, ly2, _ in lines_concreto
            if anti_sobreposicao._segmento_colide_box(lx1, ly1, lx2, ly2, bx_c, margem=0.5)
        )
        pen_base = 500.0 * n_cub + 600.0 * n_txt + 400.0 * n_conc + 0.25 * ord_score
        if pen_base >= menor_pen:
            continue

        melhor_alvo_fb = None
        menor_pen_seta = float("inf")
        for xa_s, ya_s in _alvos_seta_para_candidato(cs_x, cs_y, bx_c):
            em_pilar = _ponto_em_pilar_poly(xa_s, ya_s, folga=6.0)
            x_j, y_j = _ponto_saida_seta_inversao(cs_x, cs_y, comp, h_txt, ang_inv, xa_s, ya_s)
            if math.hypot(x_j - xa_s, y_j - ya_s) < 9.5:
                continue
            n_seta_p = sum(
                1 for pb in pilar_polys
                if anti_sobreposicao._segmento_colide_box(x_j, y_j, xa_s, ya_s, pb, margem=0.5)
            )
            n_seta_t = sum(
                1 for ob in textos_e_outros
                if anti_sobreposicao._segmento_colide_box(x_j, y_j, xa_s, ya_s, ob, margem=0.5)
            )
            pen_s = (5000.0 if em_pilar else 0.0) + 2000.0 * n_seta_p + 1500.0 * n_seta_t + 0.05 * math.hypot(xa_s - cx_orig, ya_s - cy_orig)
            if pen_s < menor_pen_seta:
                menor_pen_seta = pen_s
                melhor_alvo_fb = (xa_s, ya_s, x_j, y_j)
                if pen_s < 1.0:
                    break

        if melhor_alvo_fb is None:
            continue
        pen = pen_base + menor_pen_seta
        if pen < menor_pen:
            menor_pen = pen
            xa_s, ya_s, x_j, y_j = melhor_alvo_fb
            melhor_fb = {
                "x": cs_x, "y": cs_y, "ang": ang_inv, "bbox": bx_c,
                "precisa_seta": True, "xa": xa_s, "ya": ya_s,
                "x_j": x_j, "y_j": y_j,
                "score": (3, pen, d_mid_2),
            }

    if melhor_fb is not None:
        return melhor_fb

    return {
        "x": cx_orig, "y": cy_orig, "ang": ang_inv,
        "bbox": _bbox_texto_inversao(cx_orig, cy_orig, h_txt, ang_inv, novo_texto),
        "precisa_seta": False, "xa": cx_orig, "ya": cy_orig,
        "x_j": cx_orig, "y_j": cy_orig,
        "score": (4, 99999.0, 99999.0),
    }


def cmd_inversoes(eag, tqsjan):
    """
    Identifica as bolinhas estritamente pelo seu NIVEL:
      - Nivel 11 (Dimensoes de vigas): 'VIGA INVERTIDA xCM' (1 unico texto por valor na viga branca)
      - Nivel 13 (Dimensoes de lajes): 'LAJE REBAIXADA' / 'xCM' (organizado sem sobreposicao)
    """
    try:
        dwg = tqsjan.dwg
        ctx = coletar_contexto_inversoes(dwg)
        bolinhas = ctx["bolinhas"]

        if not bolinhas:
            eag.msg.Print("G3 Plugins: Nenhuma bolinha nos niveis 11 (vigas) ou 13 (lajes) encontrada.")
            eag.msg.PrintStatus("Nenhuma bolinha de viga/laje encontrada.")
            return

        obstaculos = ctx["obstaculos"]
        obstaculos_viga_exatos = list(ctx.get("obstaculos_viga_exatos", []))
        linhas_221_ativas = list(ctx.get("linhas_221", []))
        bolinhas_viga = [b for b in bolinhas if b["level"] == 11]
        bolinhas_laje = [b for b in bolinhas if b["level"] == 13]

        # Reserva antecipadamente a zona dos textos futuros 'LAJE REBAIXADA / xCM' para que
        # nenhuma 'VIGA INVERTIDA' caia sobre uma indicacao de laje que sera criada no passo 2
        for bl in bolinhas_laje:
            val_str_l = _formatar_valor_cm(bl["val"])
            h_reb_l = 10.0 if abs(bl["h"] - 12.0) < 1.0 else round(bl["h"] * 0.85, 1)
            lin1_l = "LAJE REBAIXADA"
            lin2_l = "%sCM" % val_str_l
            laje_match = None
            for lj in ctx["lajes"]:
                if abs(lj["xc"] - bl["xc"]) <= 45.0 and 0.0 <= (lj["yc"] - bl["yc"]) <= 160.0:
                    laje_match = lj
                    break
            if laje_match is not None and laje_match["esp"] is not None and bl["ang"] == 0.0:
                dy_esp_l = laje_match["esp"]["yc"] - laje_match["yc"]
                dy_l1 = dy_esp_l - (h_reb_l * 1.74)
                dy_l2 = dy_l1 - (h_reb_l * 1.70)
                obstaculos_viga_exatos.append(("laje_esp", _bbox_texto_inversao(laje_match["xc"], laje_match["yc"] + dy_l1, h_reb_l, 0.0, lin1_l)))
                obstaculos_viga_exatos.append(("laje_esp", _bbox_texto_inversao(laje_match["xc"], laje_match["yc"] + dy_l2, h_reb_l, 0.0, lin2_l)))
            else:
                obstaculos_viga_exatos.append(("laje_esp", _bbox_texto_inversao(bl["xc"], bl["yc"], h_reb_l, bl["ang"], lin1_l)))
                if bl["ang"] == 90.0:
                    obstaculos_viga_exatos.append(("laje_esp", _bbox_texto_inversao(bl["xc"] + h_reb_l * 1.7, bl["yc"], h_reb_l, bl["ang"], lin2_l)))
                else:
                    obstaculos_viga_exatos.append(("laje_esp", _bbox_texto_inversao(bl["xc"], bl["yc"] - h_reb_l * 1.7, h_reb_l, bl["ang"], lin2_l)))

        lines_concreto_map = []
        for y, x1, x2 in ctx.get("linhas_horiz_concreto", []):
            lines_concreto_map.append((x1, y, x2, y, 1))
        for x, y1, y2 in ctx.get("linhas_vert_concreto", []):
            lines_concreto_map.append((x, y1, x, y2, 1))
        lines_concreto = list(ctx.get("lines_concreto_exatas", [])) or lines_concreto_map

        limite_sem_seta = float(
            getattr(anti_sobreposicao, "LIMITE_SEM_SETA_INVERSAO_VIGA", LIMITE_SEM_SETA_INVERSAO_VIGA)
        )

        textos_criados = 0
        bolinhas_apagadas = 0

        # ---------------------------------------------------------------------
        # 1. PROCESSA VIGAS (NIVEL 11) - 1 UNICO TEXTO POR VIGA (SEM REPETIR)
        # ---------------------------------------------------------------------
        vigas_geom_all = anti_sobreposicao.mapear_vigas_continuas(ctx["vigas"], lines_concreto)
        corredores_vigas = [
            (vg_a["ang"], vg_a["t_min"], vg_a["t_max"], vg_a["l_min"], vg_a["l_max"])
            for vg_a in vigas_geom_all
        ]
        grupos_vigas = _agrupar_bolinhas_vigas(bolinhas_viga, ctx["vigas"], ctx.get("secoes", []), lines_concreto)

        def _chave_ordem_grupo_viga(item_grp):
            v_g, vg_g, _, grp_g, _ = item_grp
            b0 = grp_g[0]
            cx0 = b0.get("cx_circ", b0["xc"])
            cy0 = b0.get("cy_circ", b0["yc"])
            if vg_g is not None:
                comp_viga = max(0.0, vg_g["l_max"] - vg_g["l_min"])
            else:
                ang0 = v_g["ang"] if v_g is not None else b0["ang"]
                _, _, l0, l1, _ = _obter_corredor_viga_local(cx0, cy0, ang0, None, lines_concreto)
                comp_viga = max(0.0, l1 - l0)
            return (round(comp_viga, 1), round(cx0, 1), round(cy0, 1))

        # Vigas mais curtas/restritas primeiro para pegarem sua vaga local antes das vigas longas
        grupos_vigas.sort(key=_chave_ordem_grupo_viga)

        for viga, vg, sec, grupo, val in grupos_vigas:
            # Apaga TODAS as bolinhas desse grupo na viga
            for b in grupo:
                dwg.edit.Erase(b["addr_circulo"])
                dwg.edit.Erase(b["addr_texto"])
                bolinhas_apagadas += 1

            val_str = _formatar_valor_cm(val)
            novo_texto = "VIGA INVERTIDA %sCM" % val_str
            nivel_txt = 11

            melhor_sol = None
            for b_cand in grupo:
                sol_cand = _calcular_melhor_posicao_inversao_viga(
                    b_cand=b_cand,
                    viga=viga,
                    vg=vg,
                    sec_prox=b_cand.get("_sec_prox", sec),
                    novo_texto=novo_texto,
                    h_txt=b_cand["h"],
                    limite_sem_seta=limite_sem_seta,
                    obstaculos_viga_exatos=obstaculos_viga_exatos,
                    lines_concreto=lines_concreto,
                    linhas_221_ativas=linhas_221_ativas,
                    corredores_vigas=corredores_vigas,
                )
                # Desempate leve em grupos multi-bolinha: se duas bolinhas tem mesma qualidade Tier 1,
                # prefere aquela que tem secao proxima (cabeçalho local da viga)
                tem_sec_bonus = -2.0 if b_cand.get("_sec_prox") is not None else 0.0
                chave_comp = (sol_cand["score"][0], sol_cand["score"][1] + tem_sec_bonus, sol_cand["score"][2])
                if melhor_sol is None or chave_comp < melhor_sol[0]:
                    melhor_sol = (chave_comp, b_cand["h"], sol_cand)

            _, h_txt, sol = melhor_sol
            x_dest = sol["x"]
            y_dest = sol["y"]
            ang_dest = sol["ang"]
            cand_box = sol["bbox"]
            comp = len(novo_texto) * h_txt * 1.0

            dwg.draw.level = nivel_txt
            dwg.draw.color = -1
            dwg.draw.style = 0
            dwg.draw.Text(x_dest, y_dest, h_txt, ang_dest, novo_texto)
            textos_criados += 1

            if sol["precisa_seta"]:
                anti_sobreposicao.desenhar_seta_inversao(
                    dwg, x_dest, y_dest, comp, h_txt, ang_dest, sol["xa"], sol["ya"]
                )
                linhas_221_ativas.append((sol["x_j"], sol["y_j"], sol["xa"], sol["ya"]))

            obstaculos_viga_exatos.append(("viga_invertida", cand_box))
            obstaculos.append({
                "tipo": "viga_invertida",
                "bbox": cand_box
            })

        # ---------------------------------------------------------------------
        # 2. PROCESSA LAJES (NIVEL 13) - SEM SOBREPOSICAO
        # ---------------------------------------------------------------------
        for b in bolinhas_laje:
            dwg.edit.Erase(b["addr_circulo"])
            dwg.edit.Erase(b["addr_texto"])
            bolinhas_apagadas += 1

            val_str = _formatar_valor_cm(b["val"])
            ang_txt = b["ang"]
            nivel_txt = 13
            h_reb = 10.0 if abs(b["h"] - 12.0) < 1.0 else round(b["h"] * 0.85, 1)

            lin1 = "LAJE REBAIXADA"
            lin2 = "%sCM" % val_str

            # Associa ao cabecalho da laje (L... / h=...) somente se a bolinha estiver logo abaixo dele
            laje = None
            for lj in ctx["lajes"]:
                if abs(lj["xc"] - b["xc"]) <= 45.0 and 0.0 <= (lj["yc"] - b["yc"]) <= 160.0:
                    laje = lj
                    break

            if laje is not None and laje["esp"] is not None and ang_txt == 0.0:
                esp = laje["esp"]
                x_base = laje["xc"]
                y_laje = laje["yc"]
                y_esp = esp["yc"]

                # Se houver uma linha de concreto vertical logo a esquerda (laje estreita como L103),
                # aproxima levemente da borda esquerda para ganhar espaco a direita
                for xv, yv1, yv2 in ctx["linhas_vert_concreto"]:
                    if yv1 <= y_laje <= yv2 and 0.0 < (x_base - xv) <= 25.0:
                        x_base = max(xv + 2.7, x_base - 14.0)
                        break

                # Posicoes relativas do bloco (Laje, h=15, LAJE REBAIXADA, 15CM)
                dy_esp = y_esp - y_laje
                dy_lin1 = dy_esp - (h_reb * 1.74)
                dy_lin2 = dy_lin1 - (h_reb * 1.70)

                def _testar_colisao_bloco(x_teste, y_laje_teste):
                    boxes = [
                        _bbox_texto(x_teste, y_laje_teste, laje["h"], 0.0, laje["nome"]),
                        _bbox_texto(x_teste, y_laje_teste + dy_esp, esp["h"], 0.0, esp["texto"]),
                        _bbox_texto(x_teste, y_laje_teste + dy_lin1, h_reb, 0.0, lin1),
                        _bbox_texto(x_teste, y_laje_teste + dy_lin2, h_reb, 0.0, lin2),
                    ]
                    for bx in boxes:
                        for obs in obstaculos:
                            if obs.get("nivel") in (9, 12):
                                continue
                            if _boxes_colidem(bx, obs["bbox"], margem=5.0):
                                return True
                        for lx1, ly1, lx2, ly2, _ in lines_concreto:
                            if anti_sobreposicao._segmento_colide_box(lx1, ly1, lx2, ly2, bx, margem=1.0):
                                return True
                    return False

                # Testa a altura atual; se colidir com VIGA INVERTIDA ou linha de corte,
                # procura um deslocamento Y livre
                y_escolhido = y_laje
                if _testar_colisao_bloco(x_base, y_laje):
                    candidatos_dy = [
                        70.0, 80.0, 88.4, 95.0, 105.0, 115.0, 55.0, 40.0,
                        -40.0, -55.0, -70.0, -85.0, -100.0
                    ]
                    for delta_y in candidatos_dy:
                        if not _testar_colisao_bloco(x_base, y_laje + delta_y):
                            y_escolhido = y_laje + delta_y
                            break

                # Move L103 e h=15 se a posicao do bloco foi ajustada para evitar colisao
                dx_bloco = x_base - laje["xc"]
                dy_bloco = y_escolhido - laje["yc"]
                if abs(dx_bloco) > 0.1 or abs(dy_bloco) > 0.1:
                    dwg.edit.Move(laje["addr_titulo"], dx_bloco, dy_bloco)
                    dwg.edit.Move(esp["addr"], dx_bloco, dy_bloco)

                dwg.draw.level = nivel_txt
                dwg.draw.color = -1
                dwg.draw.style = 0
                dwg.draw.Text(x_base, y_escolhido + dy_lin1, h_reb, 0.0, lin1)
                dwg.draw.Text(x_base, y_escolhido + dy_lin2, h_reb, 0.0, lin2)
                textos_criados += 1
            else:
                # Bolinha de Nivel 13 avulsa (ex: trocada pelo usuario para teste):
                # escreve LAJE REBAIXADA xCM direto na posicao e orientacao da bolinha
                dwg.draw.level = nivel_txt
                dwg.draw.color = -1
                dwg.draw.style = 0
                dwg.draw.Text(b["xc"], b["yc"], h_reb, ang_txt, lin1)
                if ang_txt == 90.0:
                    dwg.draw.Text(b["xc"] + h_reb * 1.7, b["yc"], h_reb, ang_txt, lin2)
                else:
                    dwg.draw.Text(b["xc"], b["yc"] - h_reb * 1.7, h_reb, ang_txt, lin2)
                textos_criados += 1

        # Se alguma nova inversao sobrepos o identificador/secao de algum pilar,
        # organiza automaticamente os pilares conflitantes com a regra de 10 cm para seta
        try:
            import importlib
            importlib.reload(anti_sobreposicao)
            anti_sobreposicao.executar_organizar_apenas_pilares(dwg)
        except Exception:
            pass

        tqsjan.Regen()
        eag.msg.Print(
            "G3 Plugins: %d bolinha(s) processada(s) -> %d indicacao(oes) organizada(s) sem sobreposicao!"
            % (bolinhas_apagadas, textos_criados)
        )
        eag.msg.PrintStatus("%d inversao(oes) organizada(s) com sucesso!" % textos_criados)

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass

