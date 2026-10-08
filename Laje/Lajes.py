# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - ARMAÇÃO AUTOMÁTICA DE LAJE NERVURADA (TQS EAG)
================================================================================
Este módulo implementa o detalhamento automático de armaduras em lajes nervuradas,
com suporte total para:
1. MODO HORIZONTAL: Ferros horizontais com linha de distribuição vertical.
2. MODO VERTICAL:   Ferros verticais com linha de distribuição horizontal.
3. Tratamento de obstáculos no Nível 237 (rosa) e aberturas/vazios com "X".
4. Detecção de bordas no Nível 228 (linha branca) e Nível 201 (vigas).
5. Cobrimento de 2.5cm e dobras configuráveis com cotagem visual.
6. Painel de controle flutuante para execução contínua com encerramento por botão.
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
# SEÇÃO 1: FUNÇÕES COMUNS (BORDAS, OBSTÁCULOS, VAZIOS COM 'X', COTAS)
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


def coletar_obstaculos_nivel_237(dwg):
    """Mantido por compatibilidade: redireciona para coletar_obstaculos_e_vazios."""
    return coletar_obstaculos_e_vazios(dwg)


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


def desenhar_cota_transpasse_vert(draw, y_ini, y_fim, x_barra, dist_t):
    """Desenha a cota de transpasse vertical elegante e proporcional."""
    x_cota = x_barra + 7.0
    draw.level = 220
    draw.color = 1  # Vermelho
    draw.style = 0
    draw.Line(x_cota, y_ini, x_cota, y_fim)
    draw.Line(x_barra - 1.0, y_ini, x_cota + 2.0, y_ini)
    draw.Line(x_barra - 1.0, y_fim, x_cota + 2.0, y_fim)
    tick = 2.0
    draw.Line(x_cota - tick, y_ini - tick, x_cota + tick, y_ini + tick)
    draw.Line(x_cota - tick, y_fim - tick, x_cota + tick, y_fim + tick)
    draw.color = 2  # Amarelo
    txt_val = f"{int(round(dist_t))}"
    tam_txt = 8.5
    ym = (y_ini + y_fim) / 2.0
    draw.Text(x_cota + 2.0, ym - (tam_txt / 2.0), tam_txt, 0.0, txt_val)


# ==============================================================================
# SEÇÃO 2: MODO HORIZONTAL (FERROS HORIZONTAIS, DISTRIBUIÇÃO VERTICAL)
# ==============================================================================

def detectar_canais_reais_entre_pontos(dwg, y_min, y_max, x_reta, modulo=65.0):
    """
    Varre o desenho e encontra APENAS as nervuras horizontais reais (espaços entre 5cm e 24cm
    entre fileiras de cubetas), filtradas estritamente na coluna X da reta vertical.
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

            # Nível 201 (Borda/Viga que cruza a reta vertical do usuário)
            if nivel == 201:
                if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                    lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                    lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                    if abs(ly1 - ly2) <= 5.0 and abs(lx2 - lx1) >= 5.0:
                        if (min(lx1, lx2) - 30.0) <= x_reta <= (max(lx1, lx2) + 30.0):
                            linhas_201_horiz.append((ly1 + ly2) / 2.0)
                elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                    try:
                        npts = dwg.iterator.xySize
                        pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                        for i in range(len(pts)):
                            p_a = pts[i]
                            p_b = pts[(i + 1) % len(pts)]
                            if abs(p_a[1] - p_b[1]) <= 5.0 and abs(p_b[0] - p_a[0]) >= 5.0:
                                if (min(p_a[0], p_b[0]) - 30.0) <= x_reta <= (max(p_a[0], p_b[0]) + 30.0):
                                    linhas_201_horiz.append((p_a[1] + p_b[1]) / 2.0)
                    except Exception:
                        pass
                continue

            if nivel >= 220:
                continue

            # Linhas horizontais de cubeta (estritamente na coluna X da reta vertical)
            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                dy = abs(ly2 - ly1)
                dx = abs(lx2 - lx1)
                ym = (ly1 + ly2) / 2.0

                if dy <= 3.0 and dx >= 8.0:
                    if (y_min - 20.0) <= ym <= (y_max + 20.0):
                        if (min(lx1, lx2) - 30.0) <= x_reta <= (max(lx1, lx2) + 30.0):
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
                                if (min(p_a[0], p_b[0]) - 30.0) <= x_reta <= (max(p_a[0], p_b[0]) + 30.0):
                                    y_horiz.append(round(ym, 1))
                except Exception:
                    pass
    except Exception:
        pass

    if not y_horiz:
        extensao = abs(y_max - y_min)
        qtd = max(int(round(extensao / modulo)), 1)
        return [], qtd

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
                sr.showRibbed = 1
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

                sr.RebarLine(xa_t, y_ferro, 0.0, 1.0, 1, 1, 1, 0, 220, 0, 3)
                usou_smart = True
            except Exception:
                usou_smart = False

            if not usou_smart:
                draw.level = 220
                draw.color = 3  # Verde
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

                # Cota do comprimento do trecho reto sem a dobra (fallback)
                txt_sem_dobra = f"{int(round(comp_trecho))}"
                tam_txt_cota = 8.0
                larg_cota = len(txt_sem_dobra) * (tam_txt_cota * 0.72)
                draw.Text(xm_trecho - (larg_cota / 2.0), y_ferro - 11.0, tam_txt_cota, 0.0, txt_sem_dobra)

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


def processar_ferro_por_2pontos(dwg, x1, y1, x2, y2, dados):
    """Alias para compatibilidade com versões anteriores."""
    processar_faixa_horizontal(dwg, x1, y1, x2, y2, dados)


# ==============================================================================
# SEÇÃO 3: MODO VERTICAL (FERROS VERTICAIS, DISTRIBUIÇÃO HORIZONTAL)
# ==============================================================================

def detectar_canais_verticais_entre_pontos(dwg, x_min, x_max, y_reta, modulo=65.0):
    """
    Varre o desenho e encontra APENAS as nervuras verticais reais (espaços entre 5cm e 24cm
    entre colunas de cubetas), filtradas estritamente na linha horizontal Y da reta clicada.
    """
    x_vert = []
    linhas_201_vert = []

    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break

            nivel = getattr(dwg.iterator, "level", 0)

            # Nível 201 (Borda/Viga vertical que cruza a reta horizontal do usuário)
            if nivel == 201:
                if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                    lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                    lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                    if abs(lx1 - lx2) <= 5.0 and abs(ly2 - ly1) >= 5.0:
                        if (min(ly1, ly2) - 30.0) <= y_reta <= (max(ly1, ly2) + 30.0):
                            linhas_201_vert.append((lx1 + lx2) / 2.0)
                elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                    try:
                        npts = dwg.iterator.xySize
                        pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                        for i in range(len(pts)):
                            p_a = pts[i]
                            p_b = pts[(i + 1) % len(pts)]
                            if abs(p_a[0] - p_b[0]) <= 5.0 and abs(p_b[1] - p_a[1]) >= 5.0:
                                if (min(p_a[1], p_b[1]) - 30.0) <= y_reta <= (max(p_a[1], p_b[1]) + 30.0):
                                    linhas_201_vert.append((p_a[0] + p_b[0]) / 2.0)
                    except Exception:
                        pass
                continue

            if nivel >= 220:
                continue

            # Linhas verticais de cubeta (estritamente na linha Y da reta horizontal)
            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                dx = abs(lx2 - lx1)
                dy = abs(ly2 - ly1)
                xm = (lx1 + lx2) / 2.0

                if dx <= 3.0 and dy >= 8.0:
                    if (x_min - 20.0) <= xm <= (x_max + 20.0):
                        if (min(ly1, ly2) - 30.0) <= y_reta <= (max(ly1, ly2) + 30.0):
                            x_vert.append(round(xm, 1))

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    for i in range(len(pts)):
                        p_a = pts[i]
                        p_b = pts[(i + 1) % len(pts)]
                        dx = abs(p_b[0] - p_a[0])
                        dy = abs(p_b[1] - p_a[1])
                        xm = (p_a[0] + p_b[0]) / 2.0
                        if dx <= 3.0 and dy >= 8.0:
                            if (x_min - 20.0) <= xm <= (x_max + 20.0):
                                if (min(p_a[1], p_b[1]) - 30.0) <= y_reta <= (max(p_a[1], p_b[1]) + 30.0):
                                    x_vert.append(round(xm, 1))
                except Exception:
                    pass
    except Exception:
        pass

    if not x_vert:
        extensao = abs(x_max - x_min)
        qtd = max(int(round(extensao / modulo)), 1)
        return [], qtd

    contagem = Counter(x_vert)
    niveis_unicos = sorted(contagem.keys())

    picos_x = []
    for x in niveis_unicos:
        qtd = contagem[x]
        if not picos_x or abs(x - picos_x[-1]['x']) > 3.0:
            picos_x.append({'x': x, 'qtd': qtd})
        else:
            tot = picos_x[-1]['qtd'] + qtd
            picos_x[-1]['x'] = (picos_x[-1]['x'] * picos_x[-1]['qtd'] + x * qtd) / tot
            picos_x[-1]['qtd'] = tot

    niveis = sorted([p['x'] for p in picos_x if p['qtd'] >= 1])

    canais_verticais = []
    for i in range(len(niveis) - 1):
        gap = niveis[i + 1] - niveis[i]
        if 5.0 <= gap <= 24.0:
            canal_meio = (niveis[i] + niveis[i + 1]) / 2.0
            if x_min - 10.0 <= canal_meio <= x_max + 10.0:
                canais_verticais.append(canal_meio)

    # Checar bordo Nível 201
    if niveis:
        x_cubeta_inf = min(niveis)
        x_cubeta_sup = max(niveis)
        for x_201 in linhas_201_vert:
            if x_201 <= x_cubeta_inf + 20.0 and x_min <= x_201 + 25.0:
                x_b_inf = (x_201 + x_cubeta_inf) / 2.0
                if not any(abs(x_b_inf - c) < 5.0 for c in canais_verticais):
                    canais_verticais.insert(0, x_b_inf)
            if x_201 >= x_cubeta_sup - 20.0 and x_max >= x_201 - 25.0:
                x_b_sup = (x_201 + x_cubeta_sup) / 2.0
                if not any(abs(x_b_sup - c) < 5.0 for c in canais_verticais):
                    canais_verticais.append(x_b_sup)

    canais_verticais = sorted(list(set(round(c, 1) for c in canais_verticais)))
    qtd_final = max(len(canais_verticais), 1)

    return canais_verticais, qtd_final


def encontrar_limites_y_bordas(dwg, x_min_band, x_max_band, y_ponto, canais_verticais=None):
    """
    Determina os limites externos Y (borda inferior e superior) da laje
    para toda a faixa horizontal [x_min_band, x_max_band], priorizando o Nível 228 e Nível 201.
    """
    linhas_borda_horiz, linhas_borda_vert = coletar_linhas_borda_dwg(dwg)

    if canais_verticais and len(canais_verticais) > 0:
        pontos_x = [x for x in canais_verticais if (x_min_band - 5.0) <= x <= (x_max_band + 5.0)]
        if not pontos_x:
            pontos_x = list(canais_verticais)
    else:
        num_passos = max(int(round(abs(x_max_band - x_min_band) / 20.0)), 1)
        pontos_x = [x_min_band + i * (x_max_band - x_min_band) / float(num_passos) for i in range(num_passos + 1)]

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
                xmin_seg = min(lx1, lx2)
                xmax_seg = max(lx1, lx2)
                if xmax_seg >= (x_min_band - 30.0) and xmin_seg <= (x_max_band + 30.0):
                    if abs(ly2 - ly1) >= 8.0:
                        cubetas_segmentos.append((xmin_seg, xmax_seg, min(ly1, ly2), max(ly1, ly2)))

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    if pts:
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        xmin_poly = min(xs)
                        xmax_poly = max(xs)
                        if xmax_poly >= (x_min_band - 30.0) and xmin_poly <= (x_max_band + 30.0):
                            cubetas_segmentos.append((xmin_poly, xmax_poly, min(ys), max(ys)))
                except Exception:
                    pass
    except Exception:
        pass

    limites_bot = []
    limites_top = []

    for x_amostra in pontos_x:
        ys_neste_x = []
        for xmin_c, xmax_c, ymin_c, ymax_c in cubetas_segmentos:
            if (xmin_c - 20.0) <= x_amostra <= (xmax_c + 20.0):
                ys_neste_x.extend([ymin_c, ymax_c])

        linhas_horiz_x = []
        for x_a, y_lim, x_b, eh_228 in linhas_borda_horiz:
            if (min(x_a, x_b) - 40.0) <= x_amostra <= (max(x_a, x_b) + 40.0):
                linhas_horiz_x.append((y_lim, eh_228))

        if ys_neste_x:
            y_cub_min = min(ys_neste_x)
            y_cub_max = max(ys_neste_x)

            cands_bot_228 = [y for y, eh_228 in linhas_horiz_x if eh_228 and y <= y_cub_min + 30.0]
            cands_bot_todos = [y for y, eh_228 in linhas_horiz_x if y <= y_cub_min + 30.0]
            if cands_bot_228:
                limites_bot.append(max(cands_bot_228))
            elif cands_bot_todos:
                limites_bot.append(max(cands_bot_todos))
            else:
                limites_bot.append(y_cub_min - 15.0)

            cands_top_228 = [y for y, eh_228 in linhas_horiz_x if eh_228 and y >= y_cub_max - 30.0]
            cands_top_todos = [y for y, eh_228 in linhas_horiz_x if y >= y_cub_max - 30.0]
            if cands_top_228:
                limites_top.append(min(cands_top_228))
            elif cands_top_todos:
                limites_top.append(min(cands_top_todos))
            else:
                limites_top.append(y_cub_max + 15.0)
        elif linhas_horiz_x:
            cands_228 = [y for y, eh_228 in linhas_horiz_x if eh_228]
            if cands_228:
                bot = [y for y in cands_228 if y < y_ponto]
                top = [y for y in cands_228 if y > y_ponto]
                if bot:
                    limites_bot.append(max(bot))
                if top:
                    limites_top.append(min(top))
            else:
                bot = [y for y, _ in linhas_horiz_x if y < y_ponto]
                top = [y for y, _ in linhas_horiz_x if y > y_ponto]
                if bot:
                    limites_bot.append(max(bot))
                if top:
                    limites_top.append(min(top))

    y_bot = max(limites_bot) if limites_bot else None
    y_top = min(limites_top) if limites_top else None

    return y_bot, y_top


def encontrar_limites_y_rib(dwg, x_rib, y_ponto, cobrimento_237=2.5):
    """
    Determina os limites Y (borda inferior e superior) da armadura para uma nervura vertical na cota x_rib.
    """
    y_bot_borda, y_top_borda = encontrar_limites_y_bordas(dwg, x_rib - 15.0, x_rib + 15.0, y_ponto)

    cobrimento_val = float(cobrimento_237)

    if y_bot_borda is not None:
        y_bot = y_bot_borda + cobrimento_val
    else:
        y_bot = y_ponto - 500.0

    if y_top_borda is not None:
        y_top = y_top_borda - cobrimento_val
    else:
        y_top = y_ponto + 500.0

    parou_237_bot = False
    parou_237_top = False

    obstaculos = coletar_obstaculos_e_vazios(dwg)
    if obstaculos:
        obst_na_nervura = [
            obs for obs in obstaculos
            if obs['xmin'] <= (x_rib + 12.0) and obs['xmax'] >= (x_rib - 12.0)
        ]

        obs_top = [obs['ymin'] for obs in obst_na_nervura if obs['ymin'] > y_ponto]
        if obs_top:
            y_obs_top = min(obs_top)
            y_novo_top = y_obs_top - cobrimento_val
            if y_novo_top < y_top:
                y_top = y_novo_top
                parou_237_top = True

        obs_bot = [obs['ymax'] for obs in obst_na_nervura if obs['ymax'] < y_ponto]
        if obs_bot:
            y_obs_bot = max(obs_bot)
            y_novo_bot = y_obs_bot + cobrimento_val
            if y_novo_bot > y_bot:
                y_bot = y_novo_bot
                parou_237_bot = True

    return y_bot, y_top, parou_237_bot, parou_237_top


def processar_faixa_vertical(dwg, x1, y1, x2, y2, dados):
    """
    Processa e detalha armadura no MODO VERTICAL:
    - Linha de distribuição horizontal definida por (x1, y1) a (x2, y2).
    - Ferros verticais com bitola, transpasses comerciais e dobras configuráveis.
    """
    draw = dwg.draw

    bitola = float(dados.get("bitola", 16.0))
    transpasse_cm = float(dados.get("transpasse", TABELA_TRANSPASSE.get(bitola, 90.0)))
    comp_dobra = float(dados.get("dobra", 15.0))
    comp_max_barra = 1180.0  # 11.80m
    modulo = float(dados.get("modulo", 65.0))

    y_reta = (y1 + y2) / 2.0
    x_p1 = min(x1, x2)
    x_p2 = max(x1, x2)

    extensao_horizontal = x_p2 - x_p1
    if extensao_horizontal < 10.0:
        return

    canais_verticais, total_nervuras = detectar_canais_verticais_entre_pontos(dwg, x_p1, x_p2, y_reta, modulo)

    grupos = []
    if canais_verticais:
        grupo_atual = None
        for x_rib in canais_verticais:
            y_b, y_t, p_bot, p_top = encontrar_limites_y_rib(dwg, x_rib, y_reta, cobrimento_237=2.5)
            if grupo_atual is None:
                grupo_atual = {
                    'ribs': [x_rib],
                    'y_bot': y_b,
                    'y_top': y_t,
                    'parou_bot': p_bot,
                    'parou_top': p_top
                }
            else:
                mesmo_y_bot = (abs(y_b - grupo_atual['y_bot']) <= 3.0)
                mesmo_y_top = (abs(y_t - grupo_atual['y_top']) <= 3.0)
                mesmo_p_bot = (p_bot == grupo_atual['parou_bot'])
                mesmo_p_top = (p_top == grupo_atual['parou_top'])
                if mesmo_y_bot and mesmo_y_top and mesmo_p_bot and mesmo_p_top:
                    grupo_atual['ribs'].append(x_rib)
                else:
                    grupos.append(grupo_atual)
                    grupo_atual = {
                        'ribs': [x_rib],
                        'y_bot': y_b,
                        'y_top': y_t,
                        'parou_bot': p_bot,
                        'parou_top': p_top
                    }
        if grupo_atual:
            grupos.append(grupo_atual)
    else:
        y_b, y_t, p_bot, p_top = encontrar_limites_y_rib(dwg, (x_p1 + x_p2) / 2.0, y_reta, cobrimento_237=2.5)
        grupos.append({
            'ribs': [(x_p1 + x_p2) / 2.0],
            'y_bot': y_b,
            'y_top': y_t,
            'parou_bot': p_bot,
            'parou_top': p_top
        })

    pos_num = 1

    for g_idx, grupo in enumerate(grupos):
        qtd_nervuras_g = len(grupo['ribs'])

        if qtd_nervuras_g > 1:
            x_min_g = min(grupo['ribs'])
            x_max_g = max(grupo['ribs'])
            x_barra = grupo['ribs'][-2] if len(grupo['ribs']) >= 2 else grupo['ribs'][0]
        else:
            x_barra = grupo['ribs'][0]
            x_min_g = x_barra
            x_max_g = x_barra

        delta_cubeta = 6.5
        x_distr_min = x_min_g - delta_cubeta
        x_distr_max = x_max_g + delta_cubeta

        y_ini_ferro = grupo['y_bot']
        y_fim_ferro = grupo['y_top']

        dobra_bot_efetiva = 0.0 if grupo['parou_bot'] else comp_dobra
        dobra_top_efetiva = 0.0 if grupo['parou_top'] else comp_dobra

        trechos_y = []
        y_curr = y_ini_ferro
        idx_t = 0

        while y_curr < y_fim_ferro:
            y_fim_t = min(y_curr + comp_max_barra, y_fim_ferro)
            trechos_y.append((y_curr, y_fim_t, idx_t))

            if y_fim_t >= y_fim_ferro:
                break
            y_curr = y_fim_t - transpasse_cm
            idx_t += 1

        for i_t, (ya_t, yb_t, idx_trecho) in enumerate(trechos_y):
            comp_trecho = yb_t - ya_t
            ym_trecho = (ya_t + yb_t) / 2.0

            off_x = 0.0
            if len(trechos_y) > 1:
                off_x = 1.5 if (idx_trecho % 2 == 1) else -1.5

            x_ferro = x_barra + off_x
            eh_ponta_bot = (i_t == 0)
            eh_ponta_top = (i_t == len(trechos_y) - 1)

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
                sr.straightBarLeftLength = float(dobra_bot_efetiva if eh_ponta_bot else 0.0)
                sr.straightBarRightLength = float(dobra_top_efetiva if eh_ponta_top else 0.0)
                sr.straightBarTextPosition = 2
                sr.straightBarZone = getattr(TQSDwg, "ICPPOS", 0)

                if qtd_nervuras_g > 1:
                    y_distr = y_reta if (i_t == 0 and ya_t <= y_reta <= yb_t) else ((ya_t + yb_t) / 2.0)
                    comp_faixa = abs(x_distr_max - x_distr_min)
                    esp_faixa = (comp_faixa / float(qtd_nervuras_g)) if qtd_nervuras_g > 0 else float(modulo)
                    sr.RebarDistrAdd(
                        getattr(TQSDwg, "ICPESP", 2),
                        0.0,
                        x_distr_min, y_distr,
                        x_distr_max, y_distr,
                        (x_distr_min + x_distr_max) / 2.0, y_distr,
                        0, 0, 0, 0, 0,
                        getattr(TQSDwg, "ICPCENTR_CENTRAD", 0),
                        getattr(TQSDwg, "ICPQUEBR_SEMQUEBRA", 0),
                        "", 0, 0, 1, 0, 0,
                        float(esp_faixa), 1.0
                    )

                sr.RebarLine(x_ferro, ya_t, 90.0, 1.0, 1, 1, 1, 0, 220, 0, 3)
                usou_smart = True
            except Exception:
                usou_smart = False

            if not usou_smart:
                draw.level = 220
                draw.color = 3  # Verde
                draw.style = 0
                draw.Line(x_ferro, ya_t, x_ferro, yb_t)

                # Dobras horizontais voltadas para a direita
                if eh_ponta_bot and dobra_bot_efetiva > 0:
                    draw.Line(x_ferro, ya_t, x_ferro + dobra_bot_efetiva, ya_t)

                if eh_ponta_top and dobra_top_efetiva > 0:
                    draw.Line(x_ferro, yb_t, x_ferro + dobra_top_efetiva, yb_t)

                # Reta horizontal com setas
                if qtd_nervuras_g > 1:
                    y_distr = y_reta if (i_t == 0 and ya_t <= y_reta <= yb_t) else ((ya_t + yb_t) / 2.0)
                    draw.level = 220
                    draw.color = 3  # Verde
                    draw.style = 0
                    draw.Line(x_distr_min, y_distr, x_distr_max, y_distr)

                    larg_seta = 8.0
                    alt_seta = 12.0
                    draw.Line(x_distr_min - larg_seta, y_distr + larg_seta, x_distr_min + larg_seta, y_distr - larg_seta)
                    draw.Line(x_distr_min, y_distr, x_distr_min + alt_seta, y_distr - (larg_seta * 0.7))
                    draw.Line(x_distr_min, y_distr, x_distr_min + alt_seta, y_distr + (larg_seta * 0.7))

                    draw.Line(x_distr_max - larg_seta, y_distr + larg_seta, x_distr_max + larg_seta, y_distr - larg_seta)
                    draw.Line(x_distr_max, y_distr, x_distr_max - alt_seta, y_distr - (larg_seta * 0.7))
                    draw.Line(x_distr_max, y_distr, x_distr_max - alt_seta, y_distr + (larg_seta * 0.7))

                draw.level = 220
                draw.color = 2  # Amarelo
                draw.style = 0
                bitola_str = f"{bitola:g}"
                comp_total_barra = comp_trecho + (dobra_bot_efetiva if eh_ponta_bot else 0.0) + (dobra_top_efetiva if eh_ponta_top else 0.0)
                comp_int = int(round(comp_total_barra))
                pos_str = f"P{pos_num}"

                if qtd_nervuras_g > 1:
                    prefixo = f"{qtd_nervuras_g}x1"
                else:
                    prefixo = "1"

                txt_chamada = f"{prefixo} {pos_str} %% {bitola_str} C/NERV C={comp_int}"
                tam_txt = 8.5
                larg_txt = len(txt_chamada) * (tam_txt * 0.72)
                draw.Text(x_ferro - 12.0, ym_trecho - (larg_txt / 2.0), tam_txt, 90.0, txt_chamada)

                # Cota do comprimento do trecho reto sem a dobra (vertical fallback)
                txt_sem_dobra = f"{int(round(comp_trecho))}"
                tam_txt_cota = 8.0
                larg_cota = len(txt_sem_dobra) * (tam_txt_cota * 0.72)
                draw.Text(x_ferro + 8.0, ym_trecho - (larg_cota / 2.0), tam_txt_cota, 90.0, txt_sem_dobra)

                if eh_ponta_bot and dobra_bot_efetiva > 0:
                    txt_d_bot = f"{int(round(dobra_bot_efetiva))}"
                    draw.Text(x_ferro + (dobra_bot_efetiva / 2.0) - 2.0, ya_t + 2.5, 6.5, 0.0, txt_d_bot)

                if eh_ponta_top and dobra_top_efetiva > 0:
                    txt_d_top = f"{int(round(dobra_top_efetiva))}"
                    draw.Text(x_ferro + (dobra_top_efetiva / 2.0) - 2.0, yb_t + 2.5, 6.5, 0.0, txt_d_top)

            if i_t > 0:
                y_trans_ini = ya_t
                y_trans_fim = trechos_y[i_t - 1][1]
                dist_t = y_trans_fim - y_trans_ini
                if dist_t > 1.0:
                    desenhar_cota_transpasse_vert(draw, y_trans_ini, y_trans_fim, x_ferro, dist_t)

            pos_num += 1


# ==============================================================================
# SEÇÃO 4: INTERFACE GRÁFICA E CONTROLE FLUTUANTE
# ==============================================================================

def pedir_dados_laje():
    """Abre janela para parâmetros e seleção de direção da armação da faixa."""
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
            .dir-selector {{
                display: flex;
                gap: 10px;
            }}
            .btn-dir {{
                flex: 1;
                text-align: center;
                padding: 10px 8px;
                border: 1.5px solid #ceb3db;
                border-radius: 6px;
                background: #fdfbfe;
                cursor: pointer;
                font-size: 11.5px;
                font-weight: 600;
                color: #4a148c;
                user-select: none;
            }}
            .btn-dir:hover {{
                background: #f3e5f5;
                border-color: #ab47bc;
            }}
            .btn-dir.active {{
                background: #6a1b9a;
                color: #ffffff;
                border-color: #4a148c;
                box-shadow: 0 2px 4px rgba(106,27,154,0.25);
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

            var direcaoAtual = "horizontal";

            function setDirecao(dir) {{
                direcaoAtual = dir;
                if (dir === "horizontal") {{
                    document.getElementById('btn-h').className = "btn-dir active";
                    document.getElementById('btn-v').className = "btn-dir";
                    document.getElementById('info-txt').innerHTML = "💡 <b>Modo Horizontal:</b> Clique 2 pontos na vertical para definir a faixa. O ferro horizontal é criado automaticamente.";
                }} else {{
                    document.getElementById('btn-h').className = "btn-dir";
                    document.getElementById('btn-v').className = "btn-dir active";
                    document.getElementById('info-txt').innerHTML = "💡 <b>Modo Vertical:</b> Clique 2 pontos na horizontal para definir a faixa. O ferro vertical é criado automaticamente.";
                }}
            }}

            function atualizarTranspasse() {{
                var bit = document.getElementById('bitola').value;
                if (tabelaTranspasse[bit]) {{
                    document.getElementById('transpasse').value = tabelaTranspasse[bit];
                }}
            }}

            function initDialog() {{
                try {{
                    window.resizeTo(470, 560);
                    window.moveTo((screen.availWidth - 470) / 2, (screen.availHeight - 560) / 2);
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
                        ',"direcao":"' + direcaoAtual + '"' +
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
                <h3>Direção da Armadura</h3>
                <div class="dir-selector">
                    <div id="btn-h" class="btn-dir active" onclick="setDirecao('horizontal')">
                        🟢 Horizontal (Faixa Vertical)
                    </div>
                    <div id="btn-v" class="btn-dir" onclick="setDirecao('vertical')">
                        🔵 Vertical (Faixa Horizontal)
                    </div>
                </div>
            </div>

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

            <div class="info-box" id="info-txt">
                💡 <b>Modo Horizontal:</b> Clique 2 pontos na vertical para definir a faixa. O ferro horizontal é criado automaticamente.
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
# ENTRY POINT PRINCIPAL NO TQS EAG (MODO CONTÍNUO MULTI-FAIXAS)
# ==============================================================================
def meucmd(eag, tqsjan):
    """
    Comando acionado pelo menu TQS na aba G3 Plugins.

    Fluxo Nativo e Contínuo / Múltiplas Faixas:
    1. Abre janela de configuração (bitola, transpasse, módulo, direção).
    2. Entra em loop contínuo:
       - Pede o 1º ponto da faixa (ou Botão Direito / Esc para encerrar).
       - Pede o 2º ponto da faixa (com linha elástica).
       - Desenha os ferros e linhas de distribuição na direção selecionada.
       - Atualiza a tela (Regen) e já aguarda a próxima faixa.
    3. Ao clicar com o Botão Direito ou pressionar Esc, encerra limpa e instantaneamente,
       devolvendo o EAG para o modo de seleção padrão sem travar.
    """
    try:
        # 1. Parâmetros via HTA (apenas uma vez para todas as faixas)
        dados = pedir_dados_laje()
        if dados is None:
            return

        direcao = dados.get("direcao", "horizontal")

        faixa_idx = 1
        while True:
            prompt1 = f"Clique o 1º ponto da {faixa_idx}ª faixa ({direcao.upper()}) [Botão Direito ou Esc para ENCERRAR]:"
            icod1, x1, y1 = eag.locate.GetPoint(tqsjan, prompt1)
            if icod1 != 1:
                break

            prompt2 = f"Clique o 2º ponto da {faixa_idx}ª faixa ({direcao.upper()}) [Botão Direito ou Esc para CANCELAR]:"
            icod2, x2, y2 = eag.locate.GetSecondPoint(
                tqsjan, x1, y1,
                TQSEag.EAG_RUBLINEAR,
                TQSEag.EAG_RUBRET_NAOPREEN,
                prompt2
            )
            if icod2 != 1:
                break

            # 3. Processar na direção escolhida
            if direcao == "vertical":
                processar_faixa_vertical(tqsjan.dwg, x1, y1, x2, y2, dados)
            else:
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
