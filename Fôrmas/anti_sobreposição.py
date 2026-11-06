# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - ANTI-SOBREPOSICAO (TQS EAG)
================================================================================
Modulo especializado em organizacao espacial e resolucao inteligente de
sobreposicoes em plantas de formas no ambiente TQS EAG.

Implementa rigorosamente as diretrizes da Skill:
  .gemini/skills/tqs-anti-sobreposicao/SKILL.md

Principais Leis e Recursos:
  1. Mapeamento Semantico de Niveis (Layers imutaveis vs moveis/deslizantes)
  2. Lei no 1: Grupos Atomicos (nunca desmembrar P.. de b/h, bolinha de numero, L.. de h=..)
  3. Lei no 2: Seta de Chamada Executiva no Nivel 221 para Pilares com patamar
     passando exatamente entre o nome P.. e a secao b/h, com idempotencia.
  4. Lei no 3: Restricoes de Jaula (deslizamento axial de vigas, orbita de pilares,
     confinamento celular de lajes).
  5. Pipeline Completo: Vigas/Bolinhas -> Pilares + Setas -> Lajes.
================================================================================
"""

import math
from TQS import TQSUtil, TQSDwg

try:
    TQSUtil.LoadDll("IPOCOT.DLL")
except Exception:
    pass


def _garantir_ipocot_carregado():
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
    Calcula bounding box (xmin, ymin, xmax, ymax) de um texto no TQS.
    Cada caractere ocupa aproximadamente 1.0 * h na fonte padrao TQS.
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


def _segmento_colide_box(x1, y1, x2, y2, box, margem=1.0):
    """Verifica se um segmento de reta cruza ou toca um bounding box."""
    bx_seg = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
    if not _boxes_colidem(bx_seg, box, margem=margem):
        return False
    if abs(x1 - x2) < 0.5:  # Segmento vertical
        xv = 0.5 * (x1 + x2)
        if (box[0] - margem) <= xv <= (box[2] + margem):
            return max(box[1], min(y1, y2)) <= min(box[3], max(y1, y2))
    elif abs(y1 - y2) < 0.5:  # Segmento horizontal
        yh = 0.5 * (y1 + y2)
        if (box[1] - margem) <= yh <= (box[3] + margem):
            return max(box[0], min(x1, x2)) <= min(box[2], max(x1, x2))
    return True


def desenhar_seta_chamada_executiva(dwg, x_fim_patamar, x_joelho, y_patamar, x_seta, y_seta):
    """
    Desenha a Seta de Chamada Executiva no Nivel 221 (padrao executivo da Skill):
      - Patamar horizontal passando exatamente entre o nome do pilar e a secao
      - Linha diagonal (leader) do joelho ate a borda mais proxima do pilar
      - Cabeca da seta na ponta com duas asas de 6.0 cm a 18 graus
    """
    dwg.draw.level = 221
    dwg.draw.color = -1
    dwg.draw.style = 0

    # 1. Patamar horizontal
    dwg.draw.Line(x_fim_patamar, y_patamar, x_joelho, y_patamar)

    # 2. Linha diagonal ate o pilar
    dwg.draw.Line(x_joelho, y_patamar, x_seta, y_seta)

    # 3. Cabeca da seta na ponta (x_seta, y_seta)
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


def apagar_chamadas_antigas_do_pilar(dwg, pcx, pcy, linhas_242, linhas_221_setas, raio_busca=35.0):
    """
    Idempotencia: apaga qualquer linha nativa de chamada do TQS (Nivel 242) ou
    seta de chamada anterior (Nivel 221) associada ao pilar fisico, permitindo
    rodar o comando repetidas vezes (antes ou depois de cotar) sem duplicar linhas.
    """
    apagadas = 0
    # Nivel 242 (chamada nativa TQS)
    for l242 in linhas_242:
        if abs(l242["x1"] - pcx) <= raio_busca and abs(l242["y1"] - pcy) <= raio_busca:
            try:
                dwg.edit.Erase(l242["addr"])
                apagadas += 1
            except Exception:
                pass

    # Nivel 221 (setas executivas anteriores que tocam o pilar)
    for l221 in linhas_221_setas:
        d1 = math.hypot(l221["x1"] - pcx, l221["y1"] - pcy)
        d2 = math.hypot(l221["x2"] - pcx, l221["y2"] - pcy)
        if min(d1, d2) <= raio_busca:
            try:
                dwg.edit.Erase(l221["addr"])
                apagadas += 1
            except Exception:
                pass

    return apagadas


def executar_anti_sobreposicao(dwg):
    """
    Executa o pipeline completo de anti-sobreposicao em conformidade com a Skill:
      1. Scanner geral do DWG (obstaculos fixos, cotas, textos, polilineas, bolinhas)
      2. Montagem dos Grupos Atomicos (PilarGroup, BolinhaGroup, SecaoVigaGroup, LajeGroup)
      3. Estagio 1: Desobstrucao axial de vigas e bolinhas (ao longo do eixo da viga)
      4. Estagio 2: Realocacao inteligente de pilares com Seta Executiva no Nivel 221
      5. Estagio 3: Confinamento e ajuste de lajes dentro de sua celula
    Retorna o total de elementos reposicionados e organizados.
    """
    _garantir_ipocot_carregado()

    # -------------------------------------------------------------------------
    # 1. SCANNER DO DWG
    # -------------------------------------------------------------------------
    poly_pilares = []       # Polilineas de pilares fisicos (Niveis 3 e 4)
    lines_concreto = []      # Segmentos de concreto (Niveis 1, 2, 201)
    obstaculos_fixos = []    # Shafts/Vazios em X (210, 241), Linhas de corte (200, 205)
    todos_obstaculos_cotas = [] # Segmentos de cotas/IPOCOT (122, 216, 221)
    texts_raw = []
    circs_raw = []
    linhas_242 = []
    linhas_221_setas = []

    dwg.iterator.Begin()
    while True:
        tipo = dwg.iterator.Next()
        if tipo == TQSDwg.DWGTYPE_EOF:
            break
        if dwg.iterator.inBlock != 0:
            continue

        l = dwg.iterator.level
        addr = dwg.iterator.GetElementReadPosition()

        if tipo == TQSDwg.DWGTYPE_POLYLINE:
            pts = [dwg.iterator.GetPolylinePt(i) for i in range(dwg.iterator.xySize)]
            if not pts:
                continue
            if l in (3, 4):  # Poligono de pilar fisico
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                poly_pilares.append({
                    "addr": addr,
                    "level": l,
                    "pts": pts,
                    "box": (min(xs), min(ys), max(xs), max(ys)),
                    "pcx": 0.5 * (min(xs) + max(xs)),
                    "pcy": 0.5 * (min(ys) + max(ys)),
                })
            elif l in (1, 2, 201):
                for i in range(len(pts) - 1):
                    lines_concreto.append((pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], l))
            elif l in (210, 241, 200, 205):
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                obstaculos_fixos.append((min(xs), min(ys), max(xs), max(ys)))

        elif tipo == TQSDwg.DWGTYPE_LINE:
            x1, y1, x2, y2 = dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2
            if l in (1, 2, 201):
                lines_concreto.append((x1, y1, x2, y2, l))
            elif l in (210, 241, 200, 205):
                obstaculos_fixos.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
            elif l in (122, 216):
                todos_obstaculos_cotas.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
            elif l == 221:
                # Linha de cota existente ou antiga seta de chamada
                todos_obstaculos_cotas.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
                linhas_221_setas.append({
                    "addr": addr, "x1": x1, "y1": y1, "x2": x2, "y2": y2
                })
            elif l == 242:
                linhas_242.append({
                    "addr": addr, "x1": x1, "y1": y1, "x2": x2, "y2": y2
                })

        elif tipo == TQSDwg.DWGTYPE_TEXT:
            txt_str = dwg.iterator.text.strip()
            h = dwg.iterator.textHeight
            ang = _normalizar_angulo(dwg.iterator.textAngle)
            x1, y1 = dwg.iterator.x1, dwg.iterator.y1
            x2, y2 = dwg.iterator.x2, dwg.iterator.y2
            xc, yc = dwg.iterator.xc, dwg.iterator.yc
            b = _bbox_texto(x1, y1, h, ang, txt_str)

            if l in (122, 216):
                todos_obstaculos_cotas.append(b)
            else:
                texts_raw.append({
                    "addr": addr, "level": l, "txt": txt_str,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "xc": xc, "yc": yc, "h": h, "ang": ang, "box": b
                })

        elif tipo == TQSDwg.DWGTYPE_CIRCLE:
            circs_raw.append({
                "addr": addr, "level": l,
                "xc": dwg.iterator.xc, "yc": dwg.iterator.yc, "r": dwg.iterator.radius
            })

    total_ajustes = 0

    # -------------------------------------------------------------------------
    # 2. MONTAGEM DOS GRUPOS ATOMICOS (LEI No 1)
    # -------------------------------------------------------------------------
    # A. BolinhaGroup: Circulo + Texto numerico interno
    bolinhas_group = []
    used_tx_idx = set()
    for c in circs_raw:
        best_tx = None
        min_d = float("inf")
        for i, tx in enumerate(texts_raw):
            if i in used_tx_idx or tx["level"] not in (11, 13):
                continue
            if "/" in tx["txt"] or "=" in tx["txt"] or tx["txt"].lower().startswith("h"):
                continue
            d = math.hypot(c["xc"] - tx["xc"], c["yc"] - tx["yc"])
            if d <= c["r"] * 1.35 and d < min_d:
                min_d = d
                best_tx = (i, tx)
        if best_tx is not None:
            used_tx_idx.add(best_tx[0])
            tx = best_tx[1]
            bolinhas_group.append({
                "addr_circ": c["addr"],
                "addr_txt": tx["addr"],
                "xc": c["xc"], "yc": c["yc"], "r": c["r"], "level": c["level"],
                "txt": tx["txt"], "h": tx["h"], "ang": tx["ang"],
                "box": (c["xc"] - c["r"], c["yc"] - c["r"], c["xc"] + c["r"], c["yc"] + c["r"]),
                "dx_txt": tx["x1"] - c["xc"],
                "dy_txt": tx["y1"] - c["yc"],
            })

    # B. PilarGroup: Nome P.. (Nivel 9) + Secao b/h (Nivel 12)
    p9_list = [tx for tx in texts_raw if tx["level"] == 9 and tx["txt"].upper().startswith("P")]
    p12_list = [tx for tx in texts_raw if tx["level"] == 12 and "/" in tx["txt"]]
    pilares_group = []
    used_12_idx = set()

    for p9 in p9_list:
        best_12 = None
        min_d = float("inf")
        for i, p12 in enumerate(p12_list):
            if i in used_12_idx:
                continue
            d = math.hypot(p9["x1"] - p12["x1"], p9["y1"] - p12["y1"])
            if d <= 45.0 and d < min_d:
                min_d = d
                best_12 = (i, p12)
        p12_obj = None
        if best_12 is not None:
            used_12_idx.add(best_12[0])
            p12_obj = best_12[1]

        bp9 = p9["box"]
        bp12 = p12_obj["box"] if p12_obj else bp9
        bconj = (min(bp9[0], bp12[0]), min(bp9[1], bp12[1]), max(bp9[2], bp12[2]), max(bp9[3], bp12[3]))

        # Associa ao poligono do pilar fisico mais proximo
        p_poly = None
        min_dp = float("inf")
        for pb in poly_pilares:
            dp = math.hypot(p9["x1"] - pb["pcx"], p9["y1"] - pb["pcy"])
            if dp < min_dp:
                min_dp = dp
                p_poly = pb

        pilares_group.append({
            "p9": p9,
            "p12": p12_obj,
            "dx_sec": (p12_obj["x1"] - p9["x1"]) if p12_obj else 0.0,
            "dy_sec": (p12_obj["y1"] - p9["y1"]) if p12_obj else -18.0,
            "box": bconj,
            "larg_conj": bconj[2] - bconj[0],
            "alt_conj": bconj[3] - bconj[1],
            "p_poly": p_poly,
        })

    # C. SecaoVigaGroup: Secao b/h (Nivel 11) + Bolinha acoplada (se houver)
    vigas_titulo = [tx for tx in texts_raw if tx["level"] == 8 and tx["txt"].upper().startswith("V")]
    vigas_inv_group = [tx for tx in texts_raw if tx["level"] == 11 and "VIGA INVERTIDA" in tx["txt"].upper()]
    sec_vigas_group = []
    for tx in texts_raw:
        if tx["level"] == 11 and "/" in tx["txt"]:
            bolinha_acoplada = None
            for b in bolinhas_group:
                if abs(tx["ang"] % 180.0) < 5.0:  # Horizontal
                    if 0.0 < (b["xc"] - max(tx["x1"], tx["x2"])) <= 35.0 and abs(b["yc"] - tx["y1"]) <= 20.0:
                        bolinha_acoplada = b
                        break
                else:  # Vertical
                    if 0.0 < (b["yc"] - max(tx["y1"], tx["y2"])) <= 35.0 and abs(b["xc"] - tx["x1"]) <= 20.0:
                        bolinha_acoplada = b
                        break
            sec_vigas_group.append({
                "tx": tx,
                "bolinha": bolinha_acoplada
            })

    # D. LajeGroup: Titulo L.. (Nivel 10) + Espessura h=.. (Nivel 13) + Itens
    lajes_group = []
    for tx in texts_raw:
        if tx["level"] == 10 and tx["txt"].upper().startswith("L"):
            # Encontra espessura h=... logo abaixo
            esp_obj = None
            for tx_esp in texts_raw:
                if tx_esp["level"] == 13 and ("=" in tx_esp["txt"] or tx_esp["txt"].lower().startswith("h")):
                    if abs(tx["x1"] - tx_esp["x1"]) <= 35.0 and 0.0 <= (tx["y1"] - tx_esp["y1"]) <= 55.0:
                        esp_obj = tx_esp
                        break
            # Outros textos da laje (ex: LAJE REBAIXADA / xCM)
            outros_itens = []
            for tx_it in texts_raw:
                if tx_it["level"] == 13 and tx_it is not esp_obj:
                    if abs(tx["x1"] - tx_it["x1"]) <= 45.0 and 0.0 <= (tx["y1"] - tx_it["y1"]) <= 115.0:
                        outros_itens.append(tx_it)

            lajes_group.append({
                "titulo": tx,
                "esp": esp_obj,
                "itens": outros_itens
            })

    # -------------------------------------------------------------------------
    # 3. ESTAGIO 1 — DESOBSTRUCAO AXIAL DE VIGAS E BOLINHAS (LEI No 3A)
    # -------------------------------------------------------------------------
    # Bounding boxes de pilares fisicos
    boxes_pilares = [pb["box"] for pb in poly_pilares]
    obstaculos_para_vigas = list(boxes_pilares) + list(obstaculos_fixos) + list(todos_obstaculos_cotas)

    # 1.1 Títulos de Vigas (Nivel 8)
    for v in vigas_titulo:
        colide = False
        for obs in obstaculos_para_vigas:
            if _boxes_colidem(v["box"], obs, margem=1.0):
                colide = True
                break
        if not colide:
            continue

        # Desliza estritamente ao longo do eixo da viga
        ang = v["ang"]
        deltas = [30.0, 50.0, 75.0, 100.0, 130.0, 160.0, -30.0, -50.0, -75.0, -100.0, -130.0]
        melhor_delta = None

        for delta in deltas:
            if ang == 0.0:
                cand_box = _bbox_texto(v["x1"] + delta, v["y1"], v["h"], ang, v["txt"])
            else:
                cand_box = _bbox_texto(v["x1"], v["y1"] + delta, v["h"], ang, v["txt"])

            # Verifica colisao com pilares, obstaculos fixos e cotas
            bate = any(_boxes_colidem(cand_box, obs, margem=1.0) for obs in obstaculos_para_vigas)
            if not bate:
                melhor_delta = delta
                break

        if melhor_delta is not None:
            dx = melhor_delta if ang == 0.0 else 0.0
            dy = melhor_delta if ang != 0.0 else 0.0
            dwg.edit.Move(v["addr"], dx, dy)
            v["x1"] += dx
            v["x2"] += dx
            v["y1"] += dy
            v["y2"] += dy
            v["xc"] += dx
            v["yc"] += dy
            v["box"] = _bbox_texto(v["x1"], v["y1"], v["h"], ang, v["txt"])
            total_ajustes += 1

    # 1.2 Secoes de Vigas (Nivel 11) + Bolinhas Acopladas
    for svg in sec_vigas_group:
        sec_tx = svg["tx"]
        bolinha = svg["bolinha"]

        # Caixa conjunta da secao + bolinha acoplada
        b_sec = sec_tx["box"]
        if bolinha:
            b_conj = (
                min(b_sec[0], bolinha["box"][0]),
                min(b_sec[1], bolinha["box"][1]),
                max(b_sec[2], bolinha["box"][2]),
                max(b_sec[3], bolinha["box"][3]),
            )
        else:
            b_conj = b_sec

        colide = False
        for obs in obstaculos_para_vigas:
            if _boxes_colidem(b_conj, obs, margem=1.0):
                colide = True
                break
        if not colide:
            continue

        ang = sec_tx["ang"]
        deltas = [30.0, 50.0, 75.0, 100.0, 130.0, 160.0, -30.0, -50.0, -75.0, -100.0, -130.0]
        melhor_delta = None

        for delta in deltas:
            if ang == 0.0:
                c_sec_box = _bbox_texto(sec_tx["x1"] + delta, sec_tx["y1"], sec_tx["h"], ang, sec_tx["txt"])
                c_bol_box = (
                    bolinha["box"][0] + delta, bolinha["box"][1],
                    bolinha["box"][2] + delta, bolinha["box"][3]
                ) if bolinha else c_sec_box
            else:
                c_sec_box = _bbox_texto(sec_tx["x1"], sec_tx["y1"] + delta, sec_tx["h"], ang, sec_tx["txt"])
                c_bol_box = (
                    bolinha["box"][0], bolinha["box"][1] + delta,
                    bolinha["box"][2], bolinha["box"][3] + delta
                ) if bolinha else c_sec_box

            c_total = (
                min(c_sec_box[0], c_bol_box[0]),
                min(c_sec_box[1], c_bol_box[1]),
                max(c_sec_box[2], c_bol_box[2]),
                max(c_sec_box[3], c_bol_box[3]),
            )

            bate = any(_boxes_colidem(c_total, obs, margem=1.0) for obs in obstaculos_para_vigas)
            if not bate:
                melhor_delta = delta
                break

        if melhor_delta is not None:
            dx = melhor_delta if ang == 0.0 else 0.0
            dy = melhor_delta if ang != 0.0 else 0.0
            dwg.edit.Move(sec_tx["addr"], dx, dy)
            sec_tx["x1"] += dx
            sec_tx["x2"] += dx
            sec_tx["y1"] += dy
            sec_tx["y2"] += dy
            sec_tx["box"] = _bbox_texto(sec_tx["x1"], sec_tx["y1"], sec_tx["h"], ang, sec_tx["txt"])

            if bolinha:
                dwg.edit.Move(bolinha["addr_circ"], dx, dy)
                dwg.edit.Move(bolinha["addr_txt"], dx, dy)
                bolinha["xc"] += dx
                bolinha["yc"] += dy
                bolinha["box"] = (
                    bolinha["box"][0] + dx, bolinha["box"][1] + dy,
                    bolinha["box"][2] + dx, bolinha["box"][3] + dy
                )

            total_ajustes += 1

    # 1.3 Textos de Vigas Invertidas (Nivel 11: 'VIGA INVERTIDA ...')
    for vi in vigas_inv_group:
        obs_vi = list(obstaculos_para_vigas)
        # Nao colidir com titulos de viga nem secoes b/h
        for v in vigas_titulo:
            obs_vi.append(v["box"])
        for svg in sec_vigas_group:
            obs_vi.append(svg["tx"]["box"])
            if svg["bolinha"]:
                obs_vi.append(svg["bolinha"]["box"])

        colide = any(_boxes_colidem(vi["box"], obs, margem=1.0) for obs in obs_vi)
        if not colide:
            continue

        ang = vi["ang"]
        # Prioriza deslizar para frente ao longo do eixo da viga
        deltas = [25.0, 45.0, 70.0, 100.0, 130.0, 160.0, 200.0, -30.0, -60.0, -90.0]
        melhor_delta = None
        for delta in deltas:
            if ang == 0.0:
                cand_box = _bbox_texto(vi["x1"] + delta, vi["y1"], vi["h"], ang, vi["txt"])
            else:
                cand_box = _bbox_texto(vi["x1"], vi["y1"] + delta, vi["h"], ang, vi["txt"])

            bate = any(_boxes_colidem(cand_box, obs, margem=1.0) for obs in obs_vi)
            if not bate:
                melhor_delta = delta
                break

        if melhor_delta is not None:
            dx = melhor_delta if ang == 0.0 else 0.0
            dy = melhor_delta if ang != 0.0 else 0.0
            dwg.edit.Move(vi["addr"], dx, dy)
            vi["x1"] += dx
            vi["x2"] += dx
            vi["y1"] += dy
            vi["y2"] += dy
            vi["box"] = _bbox_texto(vi["x1"], vi["y1"], vi["h"], ang, vi["txt"])
            total_ajustes += 1

    # -------------------------------------------------------------------------
    # 4. ESTAGIO 2 — REALOCACAO INTELIGENTE DE PILARES + SETA EXECUTIVA (LEIS 2 e 3B)
    # -------------------------------------------------------------------------
    # Atualiza obstaculos para pilares (vigas atualizadas, shafts, cotas, linhas de corte)
    obstaculos_para_pilar = list(boxes_pilares) + list(obstaculos_fixos) + list(todos_obstaculos_cotas)
    for v in vigas_titulo:
        obstaculos_para_pilar.append(v["box"])
    for svg in sec_vigas_group:
        obstaculos_para_pilar.append(svg["tx"]["box"])
        if svg["bolinha"]:
            obstaculos_para_pilar.append(svg["bolinha"]["box"])
    for vi in vigas_inv_group:
        obstaculos_para_pilar.append(vi["box"])

    for p_grp in pilares_group:
        p9 = p_grp["p9"]
        p12 = p_grp["p12"]
        p_poly = p_grp["p_poly"]
        b_conj = p_grp["box"]

        # Verifica colisao atual com vigas, shafts, cotas ou outros pilares
        colide = False
        for obs in obstaculos_para_pilar:
            if _boxes_colidem(b_conj, obs, margem=1.5):
                colide = True
                break

        # Verifica se alguma linha de concreto cruza o meio do texto do pilar
        if not colide:
            for lx1, ly1, lx2, ly2, _ in lines_concreto:
                if _segmento_colide_box(lx1, ly1, lx2, ly2, b_conj, margem=1.0):
                    colide = True
                    break

        if not colide:
            continue

        pcx = p_poly["pcx"] if p_poly else p9["x1"]
        pcy = p_poly["pcy"] if p_poly else p9["y1"]
        larg_conj = p_grp["larg_conj"]
        alt_conj = p_grp["alt_conj"]
        p_box = p_poly["box"] if p_poly else (pcx - 12.5, pcy - 12.5, pcx + 12.5, pcy + 12.5)

        # Candidatos em orbita nos 4 quadrantes com raios progressivos (Skill Secao 4B)
        candidatos = []
        for r in (35.0, 50.0, 65.0, 80.0, 95.0, 115.0):
            # Superior direito
            candidatos.append((pcx + r, pcy + r * 0.7))
            # Superior esquerdo
            candidatos.append((pcx - r - larg_conj, pcy + r * 0.7))
            # Inferior direito
            candidatos.append((pcx + r, pcy - r * 0.7 - alt_conj))
            # Inferior esquerdo
            candidatos.append((pcx - r - larg_conj, pcy - r * 0.7 - alt_conj))

        escolhido = None
        for cand_x, cand_y in candidatos:
            cb9 = _bbox_texto(cand_x, cand_y, p9["h"], p9["ang"], p9["txt"])
            cb12 = _bbox_texto(cand_x + p_grp["dx_sec"], cand_y + p_grp["dy_sec"], p12["h"] if p12 else 12.0, p9["ang"], p12["txt"] if p12 else "")
            c_conj = (min(cb9[0], cb12[0]), min(cb9[1], cb12[1]), max(cb9[2], cb12[2]), max(cb9[3], cb12[3]))

            # Restricoes eliminatorias da Skill:
            # 1. Nao pode tocar poligonos de pilares (Nivel 4)
            if any(_boxes_colidem(c_conj, pb, margem=2.0) for pb in boxes_pilares):
                continue
            # 2. Nao pode tocar shafts em X ou linhas de corte
            if any(_boxes_colidem(c_conj, obs, margem=2.0) for obs in obstaculos_fixos):
                continue
            # 3. Nao pode tocar cotas existentes
            if any(_boxes_colidem(c_conj, c_obs, margem=2.0) for c_obs in todos_obstaculos_cotas):
                continue
            # 4. Nao pode tocar vigas (titulos e secoes)
            if any(_boxes_colidem(c_conj, v["box"], margem=2.0) for v in vigas_titulo):
                continue
            if any(_boxes_colidem(c_conj, s["tx"]["box"], margem=2.0) for s in sec_vigas_group):
                continue
            # 5. Nao pode ser cortado por linhas de face de concreto
            corte_concreto = False
            for lx1, ly1, lx2, ly2, _ in lines_concreto:
                if _segmento_colide_box(lx1, ly1, lx2, ly2, c_conj, margem=1.0):
                    corte_concreto = True
                    break
            if corte_concreto:
                continue

            escolhido = (cand_x, cand_y, c_conj)
            break

        if escolhido is not None:
            nx, ny, novo_box = escolhido
            dx = nx - p9["x1"]
            dy = ny - p9["y1"]

            dwg.edit.Move(p9["addr"], dx, dy)
            p9["x1"] = nx
            p9["y1"] = ny
            p9["box"] = _bbox_texto(nx, ny, p9["h"], p9["ang"], p9["txt"])

            if p12 is not None:
                dwg.edit.Move(p12["addr"], dx, dy)
                p12["x1"] += dx
                p12["y1"] += dy
                p12["box"] = _bbox_texto(p12["x1"], p12["y1"], p12["h"], p12["ang"], p12["txt"])

            p_grp["box"] = novo_box
            obstaculos_para_pilar.append(novo_box)

            # Idempotencia: apaga chamada velha (Nivel 242 ou 221)
            apagar_chamadas_antigas_do_pilar(dwg, pcx, pcy, linhas_242, linhas_221_setas, raio_busca=45.0)

            # Desenha a Seta de Chamada Executiva com Patamar no Nivel 221
            y_patamar = ny - 3.0  # Passa exatamente entre P.. e b/h
            if nx >= pcx:
                x_joelho = nx - 3.0
                x_fim_patamar = nx + larg_conj + 2.0
                x_seta = min(p_box[2], max(p_box[0] + 5.0, pcx + 3.0))
                y_seta = p_box[1] if y_patamar < pcy else p_box[3]
            else:
                x_joelho = nx + larg_conj + 3.0
                x_fim_patamar = nx - 2.0
                x_seta = max(p_box[0], min(p_box[2] - 5.0, pcx - 3.0))
                y_seta = p_box[1] if y_patamar < pcy else p_box[3]

            dist_seta = math.hypot(x_joelho - x_seta, y_patamar - y_seta)
            if dist_seta >= 20.0:
                desenhar_seta_chamada_executiva(dwg, x_fim_patamar, x_joelho, y_patamar, x_seta, y_seta)

            total_ajustes += 1

    # -------------------------------------------------------------------------
    # 5. ESTAGIO 3 — CONFINAMENTO E AJUSTE DE LAJES (LEIS 2 e 3C)
    # -------------------------------------------------------------------------
    obstaculos_para_lajes = list(boxes_pilares) + list(obstaculos_fixos) + list(todos_obstaculos_cotas)
    for p_grp in pilares_group:
        obstaculos_para_lajes.append(p_grp["box"])
    for v in vigas_titulo:
        obstaculos_para_lajes.append(v["box"])
    for svg in sec_vigas_group:
        obstaculos_para_lajes.append(svg["tx"]["box"])
        if svg["bolinha"]:
            obstaculos_para_lajes.append(svg["bolinha"]["box"])

    for lj in lajes_group:
        tx_tit = lj["titulo"]
        tx_esp = lj["esp"]
        itens = lj["itens"]

        bloco_elems = [tx_tit]
        if tx_esp:
            bloco_elems.append(tx_esp)
        bloco_elems.extend(itens)

        def _bloco_laje_colide(dx_t, dy_t):
            for el in bloco_elems:
                bx = _bbox_texto(el["x1"] + dx_t, el["y1"] + dy_t, el["h"], el["ang"], el["txt"])
                for obs in obstaculos_para_lajes:
                    if _boxes_colidem(bx, obs, margem=1.5):
                        return True
                # Nao pode atravessar linhas de vigas
                for lx1, ly1, lx2, ly2, _ in lines_concreto:
                    if _segmento_colide_box(lx1, ly1, lx2, ly2, bx, margem=1.0):
                        return True
            return False

        if _bloco_laje_colide(0.0, 0.0):
            # Procura um ajuste leve (dx, dy) dentro do proprio pano de laje
            candidatos_laje = [
                (0.0, 20.0), (0.0, -20.0), (0.0, 35.0), (0.0, -35.0),
                (25.0, 0.0), (-25.0, 0.0), (25.0, 20.0), (-25.0, 20.0),
                (35.0, -25.0), (-35.0, -25.0), (0.0, 50.0), (0.0, -50.0)
            ]
            achou_laje = None
            for dx_c, dy_c in candidatos_laje:
                if not _bloco_laje_colide(dx_c, dy_c):
                    achou_laje = (dx_c, dy_c)
                    break

            if achou_laje is not None:
                dx_c, dy_c = achou_laje
                for el in bloco_elems:
                    dwg.edit.Move(el["addr"], dx_c, dy_c)
                    el["x1"] += dx_c
                    el["x2"] += dx_c
                    el["y1"] += dy_c
                    el["y2"] += dy_c
                total_ajustes += 1

    return total_ajustes


def cmd_corrigir_sobreposicao(eag, tqsjan):
    """
    Entry point do comando Corrigir Sobreposicao no EAG do TQS.
    Organiza textos de vigas, bolinhas, pilares (com setas executivas)
    e lajes eliminando sobreposicoes sem cometer loucuras estruturais.
    """
    try:
        dwg = tqsjan.dwg
        total = executar_anti_sobreposicao(dwg)
        tqsjan.Regen()

        if total > 0:
            eag.msg.Print("G3 Plugins: %d elemento(s) reorganizado(s) sem sobreposicao com sucesso!" % total)
            eag.msg.PrintStatus("%d sobreposicao(oes) corrigida(s)!" % total)
        else:
            eag.msg.Print("G3 Plugins: Planta de formas ja se encontra perfeitamente organizada e limpa.")
            eag.msg.PrintStatus("Nenhuma sobreposicao detectada.")

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass


def meucmd(eag, tqsjan):
    """Entry point padrao quando acionado diretamente."""
    cmd_corrigir_sobreposicao(eag, tqsjan)

