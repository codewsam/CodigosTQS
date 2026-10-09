# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - ARMAÇÃO AUTOMÁTICA DE LAJE NERVURADA (MODO HORIZONTAL)
================================================================================
- Ferros horizontais com linha de distribuição vertical.
- Detecção precisa de bordas no Nível 228 e Nível 201.
- Tratamento de obstáculos no Nível 237 e vazios com 'X'.
- Representação gráfica fina no Nível 220 com notação multiplicadora (ex: 5x1).
================================================================================
"""
import os
import json
import math
import subprocess
from collections import Counter
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
# SEÇÃO 1: FUNÇÕES DE CONTORNO, BORDAS E OBSTÁCULOS
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
                lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
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


def coletar_obstaculos_e_vazios(dwg):
    """
    Varre o desenho em busca de obstáculos e aberturas:
    1. Elementos no Nível 237 (rosa)
    2. Linhas e polilinhas diagonais formando o 'X' dos espaços vazios / furos / shafts
    3. Linhas/caixas vermelhas (cor 1) APENAS quando estiverem próximas (<= 40cm) de um 'X' de abertura
    Retorna lista de dicionários com limites: [{'xmin': ..., 'xmax': ..., 'ymin': ..., 'ymax': ...}, ...]
    """
    obstaculos_rosa = []
    vazios_x = []
    linhas_vermelhas = []

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
                    obstaculos_rosa.append({
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
                            obstaculos_rosa.append({
                                'xmin': min(xs),
                                'xmax': max(xs),
                                'ymin': min(ys),
                                'ymax': max(ys)
                            })
                    except Exception:
                        pass
                continue

            # 2. Linhas diagonais com 'X' e linhas vermelhas
            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                dx = abs(lx2 - lx1)
                dy = abs(ly2 - ly1)
                if dx >= 15.0 and dy >= 15.0:
                    vazios_x.append({
                        'xmin': min(lx1, lx2),
                        'xmax': max(lx1, lx2),
                        'ymin': min(ly1, ly2),
                        'ymax': max(ly1, ly2)
                    })
                elif cor == 1 and (dx >= 10.0 or dy >= 10.0):
                    linhas_vermelhas.append({
                        'xmin': min(lx1, lx2),
                        'xmax': max(lx1, lx2),
                        'ymin': min(ly1, ly2),
                        'ymax': max(ly1, ly2)
                    })

            # 3. Polilinhas com segmentos diagonais ou contornos vermelhos
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
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        if tem_diag:
                            vazios_x.append({
                                'xmin': min(xs),
                                'xmax': max(xs),
                                'ymin': min(ys),
                                'ymax': max(ys)
                            })
                        elif cor == 1:
                            linhas_vermelhas.append({
                                'xmin': min(xs),
                                'xmax': max(xs),
                                'ymin': min(ys),
                                'ymax': max(ys)
                            })
                except Exception:
                    pass
    except Exception:
        pass

    # Associar linhas vermelhas aos vazios com 'X' (se estiverem a até 40cm de distância)
    obstaculos_vazios = []
    for vx in vazios_x:
        x_min_v = vx['xmin']
        x_max_v = vx['xmax']
        y_min_v = vx['ymin']
        y_max_v = vx['ymax']

        for red in linhas_vermelhas:
            if (x_min_v - 40.0) <= red['xmax'] and red['xmin'] <= (x_max_v + 40.0):
                if (y_min_v - 40.0) <= red['ymax'] and red['ymin'] <= (y_max_v + 40.0):
                    x_min_v = min(x_min_v, red['xmin'])
                    x_max_v = max(x_max_v, red['xmax'])
                    y_min_v = min(y_min_v, red['ymin'])
                    y_max_v = max(y_max_v, red['ymax'])

        obstaculos_vazios.append({
            'xmin': x_min_v,
            'xmax': x_max_v,
            'ymin': y_min_v,
            'ymax': y_max_v
        })

    return obstaculos_rosa + obstaculos_vazios


def desenhar_cota_transpasse_horiz(draw, x_ini, x_fim, y_barra, dist_t):
    """Desenha a cota de transpasse horizontal elegante e proporcional."""
    y_cota = y_barra + 7.0
    draw.level = 220
    draw.color = 1  # Vermelho
    draw.style = 0
    draw.Line(x_ini, y_cota, x_fim, y_cota)
    draw.Line(x_ini, y_barra - 1.0, x_ini, y_cota + 2.0)
    draw.Line(x_fim, y_barra - 1.0, x_fim, y_cota + 2.0)
    tick = 2.0
    draw.Line(x_ini - tick, y_cota - tick, x_ini + tick, y_cota + tick)
    draw.Line(x_fim - tick, y_cota - tick, x_fim + tick, y_cota + tick)
    draw.color = 2  # Amarelo
    txt_val = f"{int(round(dist_t))}"
    tam_txt = 8.5
    larg_txt = len(txt_val) * (tam_txt * 0.72)
    xm = (x_ini + x_fim) / 2.0
    draw.Text(xm - larg_txt / 2.0, y_cota + 2.0, tam_txt, 0.0, txt_val)


# ==============================================================================
# SEÇÃO 2: DETECÇÃO DE NERVURAS E PROCESSAMENTO HORIZONTAL
# ==============================================================================

def detectar_canais_reais_entre_pontos(dwg, y_min, y_max, x_reta, modulo=65.0):
    """
    Varre o desenho e encontra APENAS as nervuras horizontais reais (espaços entre 5cm e 24cm
    entre linhas de cubetas), filtradas estritamente na linha vertical X da reta clicada.
    """
    y_horiz = []
    linhas_201_horiz = []

    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break

            nivel = getattr(dwg.iterator, "level", 0)

            # Nível 201 (Borda/Viga horizontal que cruza a reta vertical do usuário)
            if nivel == 201:
                if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                    lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                    lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                    if abs(ly1 - ly2) <= 3.0 and min(lx1, lx2) - 5.0 <= x_reta <= max(lx1, lx2) + 5.0:
                        linhas_201_horiz.append((ly1 + ly2) / 2.0)
                elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                    try:
                        npts = dwg.iterator.xySize
                        pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                        for i in range(len(pts)):
                            p_a = pts[i]
                            p_b = pts[(i + 1) % len(pts)]
                            if abs(p_a[1] - p_b[1]) <= 3.0 and min(p_a[0], p_b[0]) - 5.0 <= x_reta <= max(p_a[0], p_b[0]) + 5.0:
                                linhas_201_horiz.append((p_a[1] + p_b[1]) / 2.0)
                    except Exception:
                        pass
                continue

            if nivel >= 220:
                continue

            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                if abs(ly1 - ly2) <= 3.0:
                    if min(lx1, lx2) - 5.0 <= x_reta <= max(lx1, lx2) + 5.0:
                        y_val = (ly1 + ly2) / 2.0
                        if y_min - 35.0 <= y_val <= y_max + 35.0:
                            y_horiz.append(y_val)

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    for i in range(len(pts)):
                        p_a = pts[i]
                        p_b = pts[(i + 1) % len(pts)]
                        if abs(p_a[1] - p_b[1]) <= 3.0:
                            if min(p_a[0], p_b[0]) - 5.0 <= x_reta <= max(p_a[0], p_b[0]) + 5.0:
                                y_val = (p_a[1] + p_b[1]) / 2.0
                                if y_min - 35.0 <= y_val <= y_max + 35.0:
                                    y_horiz.append(y_val)
                except Exception:
                    pass
    except Exception:
        pass

    if not y_horiz:
        h = abs(y_max - y_min)
        num_nervuras = max(int(round(h / modulo)), 1)
        if num_nervuras == 1:
            return [(y_min + y_max) / 2.0], 1
        esp = h / float(num_nervuras)
        return [y_min + (i + 0.5) * esp for i in range(num_nervuras)], num_nervuras

    arredondados = [round(y, 1) for y in y_horiz]
    contagem = Counter(arredondados)
    chaves_ordenadas = sorted(contagem.keys())

    picos_y = []
    for y in chaves_ordenadas:
        qtd = contagem[y]
        if not picos_y or abs(y - picos_y[-1]['y']) > 3.0:
            picos_y.append({'y': y, 'qtd': qtd})
        else:
            tot = picos_y[-1]['qtd'] + qtd
            picos_y[-1]['y'] = (picos_y[-1]['y'] * picos_y[-1]['qtd'] + y * qtd) / tot
            picos_y[-1]['qtd'] = tot

    niveis = sorted([p['y'] for p in picos_y if p['qtd'] >= 1])

    canais_reais = []
    for i in range(len(niveis) - 1):
        gap = niveis[i + 1] - niveis[i]
        if 5.0 <= gap <= 24.0:
            canal_meio = (niveis[i] + niveis[i + 1]) / 2.0
            if y_min - 10.0 <= canal_meio <= y_max + 10.0:
                canais_reais.append(canal_meio)

    # Checar bordo Nível 201
    if niveis:
        y_cubeta_inf = min(niveis)
        y_cubeta_sup = max(niveis)
        for y_201 in linhas_201_horiz:
            if y_201 <= y_cubeta_inf + 20.0 and y_min <= y_201 + 25.0:
                y_b_inf = (y_201 + y_cubeta_inf) / 2.0
                if not any(abs(y_b_inf - c) < 5.0 for c in canais_reais):
                    canais_reais.insert(0, y_b_inf)
            if y_201 >= y_cubeta_sup - 20.0 and y_max >= y_201 - 25.0:
                y_b_sup = (y_201 + y_cubeta_sup) / 2.0
                if not any(abs(y_b_sup - c) < 5.0 for c in canais_reais):
                    canais_reais.append(y_b_sup)

    canais_reais = sorted(list(set(round(c, 1) for c in canais_reais)))
    qtd_final = max(len(canais_reais), 1)

    return canais_reais, qtd_final


def encontrar_limites_x_bordas(dwg, y_min_band, y_max_band, x_ponto, canais_reais=None):
    """
    Determina os limites externos X (borda esquerda e borda direita) da laje
    para toda a faixa vertical [y_min_band, y_max_band], priorizando a linha branca
    do Nível 228 onde os ferros laterais devem parar.
    """
    linhas_borda_horiz, linhas_borda_vert = coletar_linhas_borda_dwg(dwg)

    if canais_reais and len(canais_reais) > 0:
        pontos_y = [y for y in canais_reais if (y_min_band - 5.0) <= y <= (y_max_band + 5.0)]
        if not pontos_y:
            pontos_y = list(canais_reais)
    else:
        num_passos = max(int(round(abs(y_max_band - y_min_band) / 20.0)), 1)
        pontos_y = [y_min_band + i * (y_max_band - y_min_band) / float(num_passos) for i in range(num_passos + 1)]

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
        xs_neste_y = []
        for xmin_c, xmax_c, ymin_c, ymax_c in cubetas_segmentos:
            if (ymin_c - 20.0) <= y_amostra <= (ymax_c + 20.0):
                xs_neste_y.extend([xmin_c, xmax_c])

        linhas_vert_y = []
        for x_lim, y_a, y_b, eh_228 in linhas_borda_vert:
            if (min(y_a, y_b) - 40.0) <= y_amostra <= (max(y_a, y_b) + 40.0):
                linhas_vert_y.append((x_lim, eh_228))

        if xs_neste_y:
            x_cub_min = min(xs_neste_y)
            x_cub_max = max(xs_neste_y)

            cands_esq_228 = [x for x, eh_228 in linhas_vert_y if eh_228 and x <= x_cub_min + 30.0]
            cands_esq_todos = [x for x, eh_228 in linhas_vert_y if x <= x_cub_min + 30.0]
            if cands_esq_228:
                limites_esq.append(max(cands_esq_228))
            elif cands_esq_todos:
                limites_esq.append(max(cands_esq_todos))
            else:
                limites_esq.append(x_cub_min - 15.0)

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

    x_left = max(limites_esq) if limites_esq else None
    x_right = min(limites_dir) if limites_dir else None

    return x_left, x_right


def encontrar_limites_x_rib(dwg, y_rib, x_ponto, cobrimento_237=2.5):
    """
    Determina os limites X (borda esquerda e direita) da armadura para uma nervura horizontal na cota y_rib.
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


def processar_faixa_horizontal(dwg, x1, y1, x2, y2, dados):
    """
    Processa e detalha armadura no MODO HORIZONTAL:
    - Linha de distribuição vertical definida por (x1, y1) a (x2, y2).
    - Ferros horizontais com bitola, transpasses comerciais e dobras configuráveis.
    """
    draw = dwg.draw

    bitola = float(dados.get("bitola", 16.0))
    transpasse_cm = float(dados.get("transpasse", TABELA_TRANSPASSE.get(bitola, 90.0)))
    comp_dobra = float(dados.get("dobra", 15.0))
    comp_max_barra = 1180.0  # 11.80m
    modulo = float(dados.get("modulo", 65.0))

    x_reta = (x1 + x2) / 2.0
    y_p1 = min(y1, y2)
    y_p2 = max(y1, y2)

    extensao_vertical = y_p2 - y_p1
    if extensao_vertical < 10.0:
        return

    canais_reais, total_nervuras = detectar_canais_reais_entre_pontos(dwg, y_p1, y_p2, x_reta, modulo)

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

    pos_num = 1

    for g_idx, grupo in enumerate(grupos):
        qtd_nervuras_g = len(grupo['ribs'])

        if qtd_nervuras_g > 1:
            y_min_g = min(grupo['ribs'])
            y_max_g = max(grupo['ribs'])
            y_barra = grupo['ribs'][-2] if len(grupo['ribs']) >= 2 else grupo['ribs'][0]
        else:
            y_barra = grupo['ribs'][0]
            y_min_g = y_barra
            y_max_g = y_barra

        delta_cubeta = 6.5
        y_distr_min = y_min_g - delta_cubeta
        y_distr_max = y_max_g + delta_cubeta

        x_ini_ferro = grupo['x_left']
        x_fim_ferro = grupo['x_right']

        dobra_esq_efetiva = 0.0 if grupo['parou_esq'] else comp_dobra
        dobra_dir_efetiva = 0.0 if grupo['parou_dir'] else comp_dobra

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

        for i_t, (xa_t, xb_t, idx_trecho) in enumerate(trechos_x):
            comp_trecho = xb_t - xa_t
            xm_trecho = (xa_t + xb_t) / 2.0

            off_y = 0.0
            if len(trechos_x) > 1:
                off_y = 1.5 if (idx_trecho % 2 == 1) else -1.5

            y_ferro = y_barra + off_y
            eh_ponta_esq = (i_t == 0)
            eh_ponta_dir = (i_t == len(trechos_x) - 1)

            usou_smart = False
            try:
                sr = TQSDwg.SmartRebar(dwg)
                sr.type = getattr(TQSDwg, "ICPFRT", 1)
                sr.diameter = float(bitola)
                sr.mark = int(pos_num)
                sr.quantity = int(qtd_nervuras_g)
                sr.spacing = float(modulo)
                sr.ribbed = 1
                sr.showRibbed = 0
                sr.straightBarMainLength = float(comp_trecho)
                sr.straightBarLeftLength = float(dobra_esq_efetiva if eh_ponta_esq else 0.0)
                sr.straightBarRightLength = float(dobra_dir_efetiva if eh_ponta_dir else 0.0)
                sr.straightBarTextPosition = 2
                sr.straightBarZone = getattr(TQSDwg, "ICPPOS", 0)

                if qtd_nervuras_g > 1:
                    x_distr = x_reta if (i_t == 0 and xa_t <= x_reta <= xb_t) else ((xa_t + xb_t) / 2.0)
                    comp_faixa = abs(y_distr_max - y_distr_min)
                    esp_faixa = (comp_faixa / float(qtd_nervuras_g)) if qtd_nervuras_g > 0 else float(modulo)
                    sr.RebarDistrAdd(
                        getattr(TQSDwg, "ICPESP", 2),
                        90.0,
                        x_distr, y_distr_min,
                        x_distr, y_distr_max,
                        x_distr, (y_distr_min + y_distr_max) / 2.0,
                        0, 0, 0, 0, 0,
                        getattr(TQSDwg, "ICPCENTR_CENTRAD", 0),
                        getattr(TQSDwg, "ICPQUEBR_SEMQUEBRA", 0),
                        "", 0, 0, 1, 0, 0,
                        float(esp_faixa), 1.0
                    )

                sr.RebarLine(xa_t, y_ferro, 0.0, 1.0, 1, 1, 1, 0, 220, -1, -1)
                usou_smart = True
            except Exception:
                usou_smart = False

            if not usou_smart:
                draw.level = 220
                draw.color = 6  # Nível 220 magenta
                draw.style = 0
                draw.Line(xa_t, y_ferro, xb_t, y_ferro)

                if eh_ponta_esq and dobra_esq_efetiva > 0:
                    draw.Line(xa_t, y_ferro, xa_t, y_ferro - dobra_esq_efetiva)

                if eh_ponta_dir and dobra_dir_efetiva > 0:
                    draw.Line(xb_t, y_ferro, xb_t, y_ferro - dobra_dir_efetiva)

                if qtd_nervuras_g > 1:
                    x_distr = x_reta if (i_t == 0 and xa_t <= x_reta <= xb_t) else ((xa_t + xb_t) / 2.0)
                    draw.level = 220
                    draw.color = 3  # Verde
                    draw.style = 0
                    draw.Line(x_distr, y_distr_min, x_distr, y_distr_max)

                    larg_seta = 8.0
                    alt_seta = 12.0
                    draw.Line(x_distr - larg_seta, y_distr_min, x_distr + larg_seta, y_distr_min)
                    draw.Line(x_distr, y_distr_min, x_distr - (larg_seta * 0.7), y_distr_min + alt_seta)
                    draw.Line(x_distr, y_distr_min, x_distr + (larg_seta * 0.7), y_distr_min + alt_seta)

                    draw.Line(x_distr - larg_seta, y_distr_max, x_distr + larg_seta, y_distr_max)
                    draw.Line(x_distr, y_distr_max, x_distr - (larg_seta * 0.7), y_distr_max - alt_seta)
                    draw.Line(x_distr, y_distr_max, x_distr + (larg_seta * 0.7), y_distr_max - alt_seta)

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
                draw.Text(xm_trecho - (larg_txt / 2.0), y_ferro + 4.0, tam_txt, 0.0, txt_chamada)

                # Cota do comprimento do trecho reto sem a dobra
                txt_sem_dobra = f"{int(round(comp_trecho))}"
                tam_txt_cota = 8.0
                larg_cota = len(txt_sem_dobra) * (tam_txt_cota * 0.72)
                draw.Text(xm_trecho - (larg_cota / 2.0), y_ferro - 10.0, tam_txt_cota, 0.0, txt_sem_dobra)

                if eh_ponta_esq and dobra_esq_efetiva > 0:
                    txt_d_esq = f"{int(round(dobra_esq_efetiva))}"
                    draw.Text(xa_t - 7.5, y_ferro - (dobra_esq_efetiva / 2.0) - 2.0, 6.5, 0.0, txt_d_esq)

                if eh_ponta_dir and dobra_dir_efetiva > 0:
                    txt_d_dir = f"{int(round(dobra_dir_efetiva))}"
                    draw.Text(xb_t + 2.5, y_ferro - (dobra_dir_efetiva / 2.0) - 2.0, 6.5, 0.0, txt_d_dir)

            if i_t > 0:
                x_trans_ini = xa_t
                x_trans_fim = trechos_x[i_t - 1][1]
                dist_t = x_trans_fim - x_trans_ini
                if dist_t > 1.0:
                    desenhar_cota_transpasse_horiz(draw, x_trans_ini, x_trans_fim, y_ferro, dist_t)

            pos_num += 1


# ==============================================================================
# SEÇÃO 3: INTERFACE E EXECUÇÃO (MODO HORIZONTAL)
# ==============================================================================

def pedir_dados_laje_horizontal():
    """Abre janela para parâmetros da armadura horizontal."""
    caminho_script = os.path.dirname(os.path.abspath(__file__))
    hta_path = os.path.join(caminho_script, "dialogo_laje_h.hta")
    json_path = os.path.join(caminho_script, "dados_laje_temp_h.json")

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
        <title>Armação de Laje - Horizontal (G3 Plugins)</title>
        <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="ArmarFaixaH" BORDER="dialog" INNERBORDER="no" SCROLL="no" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
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
                background: linear-gradient(135deg, #1b5e20 0%, #003300 100%);
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
                font-size: 18px;
            }}
            .topbar h1 {{
                margin: 0;
                font-size: 15px;
                font-weight: 600;
            }}
            .topbar p {{
                margin: 2px 0 0 0;
                font-size: 11px;
                opacity: 0.85;
            }}
            .container {{
                padding: 16px;
            }}
            .card {{
                background: #fff;
                border: 1px solid #e0d8e8;
                border-radius: 8px;
                padding: 12px 14px;
                margin-bottom: 12px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            }}
            .card h3 {{
                margin: 0 0 10px 0;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                color: #1b5e20;
                font-weight: 700;
            }}
            .campo {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }}
            .campo:last-child {{
                margin-bottom: 0;
            }}
            .campo label {{
                font-weight: 500;
                color: #444;
            }}
            .campo select, .campo input {{
                width: 140px;
                padding: 5px 8px;
                border: 1px solid #c9bfd4;
                border-radius: 5px;
                background: #fff;
                font-size: 12px;
                text-align: right;
                font-weight: 600;
                color: #1b5e20;
            }}
            .info-box {{
                background: #e8f5e9;
                border-left: 4px solid #2e7d32;
                padding: 9px 12px;
                border-radius: 0 6px 6px 0;
                margin-top: 10px;
                font-size: 11.5px;
                color: #1b5e20;
            }}
            .btns {{
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                padding: 0 16px 16px 16px;
            }}
            button {{
                padding: 8px 18px;
                border-radius: 6px;
                font-size: 12.5px;
                font-weight: 600;
                cursor: pointer;
                border: 1px solid #ccc;
                background: #fff;
                color: #444;
            }}
            button.btn-gerar {{
                background: #1b5e20;
                color: #fff;
                border-color: #1b5e20;
            }}
        </style>
        <script language="javascript">
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
                    window.resizeTo(470, 480);
                    window.moveTo((screen.availWidth - 470) / 2, (screen.availHeight - 480) / 2);
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
            <div class="icon">━</div>
            <div>
                <h1>Armação de Laje - Horizontal</h1>
                <p>Plugin TQS &#9679 G3 Engenharia</p>
            </div>
        </div>

        <div class="container">
            <div class="card">
                <h3>Parâmetros do Ferro Horizontal</h3>
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
                💡 <b>Instrução:</b> Clique 2 pontos na vertical para definir a faixa. O ferro horizontal e a linha de distribuição vertical são criados automaticamente.
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


def meucmd(eag, tqsjan):
    """
    Entry point do plugin para MODO HORIZONTAL no TQS EAG.
    """
    try:
        dados = pedir_dados_laje_horizontal()
        if dados is None:
            return

        faixa_idx = 1
        while True:
            prompt1 = f"Clique o 1º ponto da {faixa_idx}ª faixa (HORIZONTAL) [Botão Direito ou Esc para ENCERRAR]:"
            icod1, x1, y1 = eag.locate.GetPoint(tqsjan, prompt1)
            if icod1 != 1:
                break

            prompt2 = f"Clique o 2º ponto da {faixa_idx}ª faixa (HORIZONTAL) [Botão Direito ou Esc para CANCELAR]:"
            icod2, x2, y2 = eag.locate.GetSecondPoint(
                tqsjan, x1, y1,
                TQSEag.EAG_RUBLINEAR,
                TQSEag.EAG_RUBRET_NAOPREEN,
                prompt2
            )
            if icod2 != 1:
                break

            processar_faixa_horizontal(tqsjan.dwg, x1, y1, x2, y2, dados)
            tqsjan.Regen()
            faixa_idx += 1

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except:
            pass
    finally:
        try:
            tqsjan.Regen()
        except:
            pass
