# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - ARMAÇÃO AUTOMÁTICA DE LAJE NERVURADA (MODO VERTICAL)
================================================================================
- Ferros verticais com linha de distribuição horizontal.
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
                elif abs(lx1 - lx2) <= 5.0 and abs(ly2 - ly1) >= 5.0:
                    linhas_borda_vert.append((min(ly1, ly2), (lx1 + lx2) / 2.0, max(ly1, ly2), eh_228))

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    for i in range(len(pts) - 1):
                        px1, py1 = pts[i][0], pts[i][1]
                        px2, py2 = pts[i+1][0], pts[i+1][1]
                        if abs(py1 - py2) <= 5.0 and abs(px2 - px1) >= 5.0:
                            linhas_borda_horiz.append((min(px1, px2), (py1 + py2) / 2.0, max(px1, px2), eh_228))
                        elif abs(px1 - px2) <= 5.0 and abs(py2 - py1) >= 5.0:
                            linhas_borda_vert.append((min(py1, py2), (px1 + px2) / 2.0, max(py1, py2), eh_228))
                except Exception:
                    pass
    except Exception:
        pass

    return linhas_borda_horiz, linhas_borda_vert


def coletar_obstaculos_e_vazios(dwg):
    """
    Coleta todos os elementos de obstáculo no desenho:
    1. Polígonos ou linhas no Nível 237 (cor rosa/vazio).
    2. Cruzes 'X' que marcam vazios ou aberturas na laje.
    """
    obstaculos = []
    linhas_avulsas = []

    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break

            nivel = getattr(dwg.iterator, "level", 0)

            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                comp = math.hypot(lx2 - lx1, ly2 - ly1)

                if nivel == 237:
                    obstaculos.append({
                        'xmin': min(lx1, lx2),
                        'xmax': max(lx1, lx2),
                        'ymin': min(ly1, ly2),
                        'ymax': max(ly1, ly2),
                        'tipo': 'nivel_237'
                    })
                elif comp > 20.0 and abs(lx1 - lx2) > 10.0 and abs(ly1 - ly2) > 10.0:
                    linhas_avulsas.append((lx1, ly1, lx2, ly2, comp, nivel))

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                if nivel == 237:
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
                                'ymax': max(ys),
                                'tipo': 'poligono_237'
                            })
                    except Exception:
                        pass
    except Exception:
        pass

    for i in range(len(linhas_avulsas)):
        l1 = linhas_avulsas[i]
        for j in range(i + 1, len(linhas_avulsas)):
            l2 = linhas_avulsas[j]
            xm1 = (l1[0] + l1[2]) / 2.0
            ym1 = (l1[1] + l1[3]) / 2.0
            xm2 = (l2[0] + l2[2]) / 2.0
            ym2 = (l2[1] + l2[3]) / 2.0

            if math.hypot(xm1 - xm2, ym1 - ym2) < 20.0 and abs(l1[4] - l2[4]) < 25.0:
                all_x = [l1[0], l1[2], l2[0], l2[2]]
                all_y = [l1[1], l1[3], l2[1], l2[3]]
                obstaculos.append({
                    'xmin': min(all_x),
                    'xmax': max(all_x),
                    'ymin': min(all_y),
                    'ymax': max(all_y),
                    'tipo': 'cruz_vazio_X'
                })

    return obstaculos


# ==============================================================================
# SEÇÃO 2: DETECÇÃO DE CANAIS E LIMITES VERTICAIS
# ==============================================================================

def detectar_canais_verticais_entre_pontos(dwg, x_p1, x_p2, y_reta, modulo=65.0, info=None):
    """
    Detecta a posição X exata de cada nervura vertical ao longo da faixa [x_p1, x_p2]:
    1. Faces de cubeta: linhas verticais curtas (níveis < 220, exceto 201/228/237).
    2. Limites: linhas brancas 201/228 e linhas longas (aberturas/maciços) que cruzam a reta.
    3. Nervura interna: vão de 5 a 28cm entre faces de cubetas consecutivas.
    4. Vão maior entre cubetas (até 60cm, sem limite no meio): conta APENAS 1 nervura.
    5. Entre a última cubeta e o limite (linha branca): conta APENAS 1 nervura,
       nunca criando nervura além da linha branca.
    Se 'info' (dict) for passado, recebe:
       info['bordas']     = {x_nervura: x_limite}
       info['bordas_228'] = {x_nervura: x_linha_branca}  (só limites 201/228)
    """
    x_min_sel = min(x_p1, x_p2)
    x_max_sel = max(x_p1, x_p2)
    largura_total = x_max_sel - x_min_sel

    faces_cubeta = []
    limites = []        # (x, eh_linha_branca)
    comp_max_face = 1.6 * float(modulo)

    def _registrar(nivel, xa, ya, xb, yb):
        if abs(xa - xb) > 3.0 or abs(yb - ya) < 8.0:
            return
        xm = (xa + xb) / 2.0
        y_lo, y_hi = min(ya, yb), max(ya, yb)
        if not ((x_min_sel - 80.0) <= xm <= (x_max_sel + 80.0)):
            return
        if nivel in (201, 228):
            if (y_lo - 10.0) <= y_reta <= (y_hi + 10.0):
                limites.append((xm, True))
            return
        if nivel >= 220 or nivel == 237:
            return
        if (y_hi - y_lo) > comp_max_face:
            # Linha longa (borda de abertura / maciço / viga): funciona como limite
            if (y_lo - 10.0) <= y_reta <= (y_hi + 10.0):
                limites.append((xm, False))
            return
        if (y_lo - 40.0) <= y_reta <= (y_hi + 40.0):
            faces_cubeta.append(xm)

    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break
            nivel = getattr(dwg.iterator, "level", 0)

            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                _registrar(nivel, dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2)

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    for i in range(len(pts) - 1):
                        _registrar(nivel, pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1])
                except Exception:
                    pass
    except Exception:
        pass

    def _clusterizar(valores, tol=4.0):
        grupos_x = []
        for v in sorted(valores):
            if grupos_x and abs(v - (sum(grupos_x[-1]) / len(grupos_x[-1]))) <= tol:
                grupos_x[-1].append(v)
            else:
                grupos_x.append([v])
        return [sum(g) / len(g) for g in grupos_x]

    xs = _clusterizar(faces_cubeta)
    # Só faces que pertencem a uma cubeta (existe a face oposta a ~1 cubeta de distância)
    xs = [x for x in xs if any(0.3 * modulo <= abs(x - o) <= 1.05 * modulo for o in xs if o != x)]

    brancas = set(round(x, 1) for x in _clusterizar([x for x, b in limites if b]))
    lims = _clusterizar([x for x, _ in limites])

    def _eh_branca(xl):
        return any(abs(xl - b) <= 4.0 for b in brancas)

    def _lims_entre(xa, xb):
        return [b for b in lims if xa + 1.0 < b < xb - 1.0]

    mapa_bordas = {}
    canais = []

    def _add_borda(x_face, x_lim):
        xc = (x_face + x_lim) / 2.0
        canais.append(xc)
        mapa_bordas[xc] = x_lim

    for i in range(len(xs) - 1):
        x_a, x_b = xs[i], xs[i + 1]
        dist = x_b - x_a
        bs = _lims_entre(x_a, x_b)
        if not bs:
            if 5.0 <= dist <= 60.0:
                # Nervura normal ou espaço maior: conta APENAS 1
                canais.append((x_a + x_b) / 2.0)
        else:
            b_esq, b_dir = min(bs), max(bs)
            if (b_esq - x_a) <= 60.0:
                _add_borda(x_a, b_esq)
            if (x_b - b_dir) <= 60.0:
                _add_borda(x_b, b_dir)

    # Bordas externas do painel (antes da primeira e depois da última cubeta)
    if xs:
        x_ini, x_fim = xs[0], xs[-1]
        bs_dir = [b for b in lims if x_fim + 1.0 < b <= x_fim + 60.0]
        if bs_dir and x_max_sel >= x_fim + 2.0:
            _add_borda(x_fim, min(bs_dir))
        bs_esq = [b for b in lims if x_ini - 60.0 <= b < x_ini - 1.0]
        if bs_esq and x_min_sel <= x_ini - 2.0:
            _add_borda(x_ini, max(bs_esq))

    canais_verticais = []
    for x_c in sorted(canais):
        if not ((x_min_sel - 10.0) <= x_c <= (x_max_sel + 10.0)):
            continue
        if canais_verticais and (x_c - canais_verticais[-1]) <= 30.0:
            continue
        canais_verticais.append(x_c)

    if not canais_verticais:
        n_espacos = max(1, int(round(largura_total / modulo)))
        passo = largura_total / float(n_espacos)
        for i in range(n_espacos):
            canais_verticais.append(x_min_sel + (i + 0.5) * passo)

    if info is not None:
        info['bordas'] = {x: mapa_bordas[x] for x in canais_verticais if x in mapa_bordas}
        info['bordas_228'] = {x: b for x, b in info['bordas'].items() if _eh_branca(b)}

    return canais_verticais, len(canais_verticais)


def encontrar_limites_y_bordas(dwg, x_min_band, x_max_band, y_ponto, canais_verticais=None, x_borda_corte=None):
    """
    Determina os limites externos Y (borda inferior e superior) da laje
    para a faixa horizontal [x_min_band, x_max_band], priorizando o Nível 228 e Nível 201.
    x_borda_corte: (x_borda, lado) -> ignora linhas totalmente do outro lado da linha branca
    (usado só na nervura de borda, para não pegar a viga/laje vizinha).
    """
    linhas_borda_horiz, linhas_borda_vert = coletar_linhas_borda_dwg(dwg)

    if x_borda_corte is not None:
        x_corte, lado_corte = x_borda_corte
        if lado_corte == 'dir':
            x_max_band = min(x_max_band, x_corte - 1.0)
            linhas_borda_horiz = [l for l in linhas_borda_horiz if min(l[0], l[2]) < x_corte - 1.0]
        else:
            x_min_band = max(x_min_band, x_corte + 1.0)
            linhas_borda_horiz = [l for l in linhas_borda_horiz if max(l[0], l[2]) > x_corte + 1.0]

    if canais_verticais and len(canais_verticais) > 0:
        pontos_x = [x for x in canais_verticais if (x_min_band - 5.0) <= x <= (x_max_band + 5.0)]
        if not pontos_x:
            pontos_x = list(canais_verticais)
    else:
        num_passos = max(int(round(abs(x_max_band - x_min_band) / 20.0)), 1)
        pontos_x = [x_min_band + i * (x_max_band - x_min_band) / float(num_passos) for i in range(num_passos + 1)]

    limites_bot = []
    limites_top = []

    for x_amostra in pontos_x:
        linhas_horiz_x = []
        for x_a, y_lim, x_b, eh_228 in linhas_borda_horiz:
            if (min(x_a, x_b) - 40.0) <= x_amostra <= (max(x_a, x_b) + 40.0):
                linhas_horiz_x.append((y_lim, eh_228))

        if linhas_horiz_x:
            cands_bot_228 = [y for y, eh_228 in linhas_horiz_x if eh_228 and y < y_ponto]
            cands_top_228 = [y for y, eh_228 in linhas_horiz_x if eh_228 and y > y_ponto]

            cands_bot_todos = [y for y, _ in linhas_horiz_x if y < y_ponto]
            cands_top_todos = [y for y, _ in linhas_horiz_x if y > y_ponto]

            if cands_bot_todos:
                limites_bot.append(max(cands_bot_todos))

            if cands_top_todos:
                limites_top.append(min(cands_top_todos))

    y_bot = max(limites_bot) if limites_bot else None
    y_top = min(limites_top) if limites_top else None

    return y_bot, y_top


def encontrar_limites_y_rib(dwg, x_rib, y_ponto, cobrimento_237=2.5, x_borda=None):
    """
    Determina os limites Y (borda inferior e superior) da armadura para uma nervura vertical na cota x_rib:
    1. Busca os limites no Nível 228 (linha branca de borda) e Nível 201 na vizinhança de x_rib.
    2. Aplica cobrimento de 2.5cm nas dobras das bordas (recuo para dentro da laje).
    3. Se houver elemento no Nível 237 (rosa) ou VAZIO com 'X' cobrindo a cota x_rib (+/- 12cm):
       - Para antes dele com cobrimento de 2.5cm (y_obs_min - 2.5 acima ou y_obs_max + 2.5 abaixo).
    x_borda: se a nervura é de borda, x da linha branca vizinha (ignora o que está além dela).
    Retorna: (y_bot, y_top, parou_237_bot, parou_237_top)
    """
    corte = None
    if x_borda is not None:
        corte = (x_borda, 'dir' if x_borda > x_rib else 'esq')
    y_bot_borda, y_top_borda = encontrar_limites_y_bordas(dwg, x_rib - 15.0, x_rib + 15.0, y_ponto, x_borda_corte=corte)

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


# ==============================================================================
# SEÇÃO 3: DESENHO E DETALHAMENTO VERTICAL
# ==============================================================================

def desenhar_cota_transpasse_vert(draw, y1, y2, x_base, dist_t, modulo=65.0):
    """
    Desenha a cota de transpasse vertical no padrão verde oficial do TQS/EAG:
    - Linhas de chamada horizontais conectando os pontos de transpasse à linha de cota.
    - Linha de cotagem vertical verde deslocada para a cubeta (à esquerda da barra).
    - Traços inclinados (ticks a 45°) nas interseções da cota.
    - Valor numérico do transpasse em verde (sem prefixo 'T='), rotacionado a 90° e centralizado.
    """
    tam_t = 8.0
    y_min_t = min(y1, y2)
    y_max_t = max(y1, y2)

    # Deslocamento da cota para dentro da cubeta à esquerda
    offset_cota = float(modulo) * 0.5 if modulo else 25.0
    offset_cota = min(40.0, max(20.0, offset_cota))
    x_cota = x_base - offset_cota

    draw.level = 220
    draw.color = 3  # Verde
    draw.style = 0

    # Linhas de chamada horizontais (da barra até um pouco além da linha de cota)
    sobra_chamada = 3.5
    draw.Line(x_cota - sobra_chamada, y_min_t, x_base, y_min_t)
    draw.Line(x_cota - sobra_chamada, y_max_t, x_base, y_max_t)

    # Linha de cotagem vertical (passando ligeiramente além das linhas de chamada)
    sobra_cota = 3.0
    draw.Line(x_cota, y_min_t - sobra_cota, x_cota, y_max_t + sobra_cota)

    # Traços inclinados (ticks 45° padrão TQS de cima-esquerda para baixo-direita)
    tilt = 3.0
    draw.Line(x_cota - tilt, y_min_t + tilt, x_cota + tilt, y_min_t - tilt)
    draw.Line(x_cota - tilt, y_max_t + tilt, x_cota + tilt, y_max_t - tilt)

    # Texto com o valor numérico em verde (sem o prefixo 'T='), centralizado na vertical
    txt_t = f"{int(round(dist_t))}"
    larg_txt = len(txt_t) * (tam_t * 0.72)
    ym = (y_min_t + y_max_t) / 2.0
    draw.Text(x_cota - 2.5, ym - (larg_txt / 2.0), tam_t, 90.0, txt_t)



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

    info_canais = {}
    canais_verticais, total_nervuras = detectar_canais_verticais_entre_pontos(dwg, x_p1, x_p2, y_reta, modulo, info=info_canais)
    mapa_bordas = info_canais.get('bordas', {})
    mapa_bordas_228 = info_canais.get('bordas_228', {})

    grupos = []
    if canais_verticais:
        grupo_atual = None
        for x_rib in canais_verticais:
            y_b, y_t, p_bot, p_top = encontrar_limites_y_rib(dwg, x_rib, y_reta, cobrimento_237=2.5,
                                                             x_borda=mapa_bordas_228.get(x_rib))
            if grupo_atual is None:
                grupo_atual = {
                    'ribs': [x_rib],
                    'y_bot': y_b,
                    'y_top': y_t,
                    'parou_bot': p_bot,
                    'parou_top': p_top
                }
            else:
                mesmo_y_bot = (abs(y_b - grupo_atual['y_bot']) <= 8.0)
                mesmo_y_top = (abs(y_t - grupo_atual['y_top']) <= 8.0)
                if mesmo_y_bot and mesmo_y_top:
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

        # Unificar grupos adjacentes com barras de mesmo tamanho
        grupos_unificados = []
        for g in grupos:
            if not grupos_unificados:
                grupos_unificados.append(g)
            else:
                g_ant = grupos_unificados[-1]
                comp_g = g['y_top'] - g['y_bot']
                comp_ant = g_ant['y_top'] - g_ant['y_bot']
                if abs(comp_g - comp_ant) <= 25.0 and abs(g['y_bot'] - g_ant['y_bot']) <= 30.0 and abs(g['y_top'] - g_ant['y_top']) <= 30.0:
                    g_ant['ribs'].extend(g['ribs'])
                    if len(g['ribs']) > len(g_ant['ribs']) - len(g['ribs']):
                        g_ant['y_bot'] = g['y_bot']
                        g_ant['y_top'] = g['y_top']
                        g_ant['parou_bot'] = g['parou_bot']
                        g_ant['parou_top'] = g['parou_top']
                else:
                    grupos_unificados.append(g)
        grupos = grupos_unificados
    else:
        y_b, y_t, p_bot, p_top = encontrar_limites_y_rib(dwg, (x_p1 + x_p2) / 2.0, y_reta, cobrimento_237=2.5)
        grupos.append({
            'ribs': [(x_p1 + x_p2) / 2.0],
            'y_bot': y_b,
            'y_top': y_t,
            'parou_bot': p_bot,
            'parou_top': p_top
        })

    apenas_contar = bool(dados.get("apenas_contar", False))
    if apenas_contar:
        for g_idx, grupo in enumerate(grupos):
            qtd_nervuras_g = len(grupo['ribs'])
            x_min_g = min(grupo['ribs'])
            x_max_g = max(grupo['ribs'])

            delta_cubeta = 6.5
            x_distr_min = x_min_g - delta_cubeta
            x_distr_max = x_max_g + delta_cubeta

            if x_max_g in mapa_bordas_228 and mapa_bordas_228[x_max_g] > x_max_g:
                x_distr_max = mapa_bordas_228[x_max_g]
            if x_min_g in mapa_bordas_228 and mapa_bordas_228[x_min_g] < x_min_g:
                x_distr_min = mapa_bordas_228[x_min_g]

            y_distr = y_reta
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

            for xr in grupo['ribs']:
                draw.Line(xr, y_distr - 4.0, xr, y_distr + 4.0)

            draw.level = 220
            draw.color = 2  # Amarelo
            draw.style = 0
            txt_contagem = f"{qtd_nervuras_g} NERV."
            tam_txt = 9.0
            larg_txt = len(txt_contagem) * (tam_txt * 0.72)
            xm_distr = (x_distr_min + x_distr_max) / 2.0
            draw.Text(xm_distr - (larg_txt / 2.0), y_distr + 3.0, tam_txt, 0.0, txt_contagem)

        return total_nervuras

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

        # Se a nervura extrema do grupo é de borda, a seta encosta na linha branca
        if x_max_g in mapa_bordas_228 and mapa_bordas_228[x_max_g] > x_max_g:
            x_distr_max = mapa_bordas_228[x_max_g]
        if x_min_g in mapa_bordas_228 and mapa_bordas_228[x_min_g] < x_min_g:
            x_distr_min = mapa_bordas_228[x_min_g]

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
                sr.showRibbed = 0
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

                sr.RebarLine(x_ferro, ya_t, 90.0, 1.0, 1, 1, 1, 0, 220, -1, -1)
                usou_smart = True
            except Exception:
                usou_smart = False

            if not usou_smart:
                draw.level = 220
                draw.color = 6  # Nível 220 magenta
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

                # Cota do comprimento do trecho reto sem a dobra
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
                    desenhar_cota_transpasse_vert(draw, y_trans_ini, y_trans_fim, x_ferro, dist_t, modulo=modulo)

            pos_num += 1


# ==============================================================================
# SEÇÃO 4: INTERFACE GRÁFICA (MODO VERTICAL)
# ==============================================================================

def pedir_dados_laje_vertical():
    """Abre janela para parâmetros da armação vertical."""
    caminho_script = os.path.dirname(os.path.abspath(__file__))
    hta_path = os.path.join(caminho_script, "dialogo_laje_v.hta")
    json_path = os.path.join(caminho_script, "dados_laje_v_temp.json")

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
        <title>Armação de Laje (Vertical) - G3 Plugins</title>
        <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="ArmarLajeVertical" BORDER="dialog" INNERBORDER="no" SCROLL="no" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
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
                background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%);
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
                color: #bbdefb;
            }}
            .container {{
                padding: 14px 18px 8px 18px;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }}
            .card {{
                background: #ffffff;
                border: 1px solid #bbdefb;
                border-radius: 8px;
                padding: 14px 16px;
                box-shadow: 0 1px 3px rgba(21,101,192,0.06);
            }}
            .card h3 {{
                margin: 0 0 12px 0;
                color: #0d47a1;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.4px;
                border-bottom: 1px solid #e3f2fd;
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
                color: #37474f;
                font-size: 12.5px;
            }}
            input, select {{
                width: 140px;
                padding: 5px 8px;
                text-align: right;
                border: 1px solid #90caf9;
                border-radius: 4px;
                background: #fbfdff;
                font-size: 12.5px;
            }}
            select {{ text-align: left; width: 150px; }}
            input:focus, select:focus {{
                outline: none;
                border-color: #1976d2;
                box-shadow: 0 0 0 2px rgba(25,118,210,0.18);
                background: #fff;
            }}
            .info-box {{
                background: #e3f2fd;
                border: 1px solid #bbdefb;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 11px;
                color: #0d47a1;
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
                border: 1px solid #90caf9;
                border-radius: 5px;
                background: #f0f7ff;
                font-size: 12px;
                font-weight: 500;
                color: #0d47a1;
            }}
            button:hover {{ background: #e1f0ff; }}
            .btn-gerar {{
                background: linear-gradient(135deg, #1976d2 0%, #0d47a1 100%);
                color: #ffffff;
                border: none;
                font-weight: 600;
                box-shadow: 0 2px 4px rgba(25,118,210,0.3);
            }}
            .btn-gerar:hover {{
                background: linear-gradient(135deg, #1565c0 0%, #0a3880 100%);
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

            window.onload = function() {{
                window.resizeTo(450, 480);
                window.moveTo((screen.width - 450) / 2, (screen.height - 480) / 2);
                atualizarTranspasse();
            }};

            function atualizarTranspasse() {{
                var bitola = document.getElementById("bitola").value;
                if (tabelaTranspasse[bitola]) {{
                    document.getElementById("transpasse").value = tabelaTranspasse[bitola];
                }}
            }}

            function toggleModoContar() {{
                var apenasContar = document.getElementById("apenas_contar").checked;
                var btn = document.querySelector(".btn-gerar");
                if (btn) {{
                    btn.innerHTML = apenasContar ? "Contar Nervuras no EAG" : "Definir Pontos no EAG";
                }}
            }}

            function confirmar() {{
                var dados = {{
                    bitola: parseFloat(document.getElementById("bitola").value),
                    transpasse: parseFloat(document.getElementById("transpasse").value),
                    dobra: parseFloat(document.getElementById("dobra").value),
                    modulo: parseFloat(document.getElementById("modulo").value),
                    apenas_contar: document.getElementById("apenas_contar").checked
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
            <div class="icon">↕️</div>
            <div>
                <h1>Armação de Laje Nervurada (Vertical)</h1>
                <p>G3 Plugins - Detalhamento Automático TQS</p>
            </div>
        </div>

        <div class="container">
            <div class="card">
                <h3>Parâmetros da Armadura</h3>
                <div class="campo">
                    <label>Bitola dos Ferros:</label>
                    <select id="bitola" onchange="atualizarTranspasse()">
                        <option value="6.3">Ø 6.3 mm</option>
                        <option value="8.0">Ø 8.0 mm</option>
                        <option value="10.0">Ø 10.0 mm</option>
                        <option value="12.5">Ø 12.5 mm</option>
                        <option value="16.0" selected>Ø 16.0 mm</option>
                        <option value="20.0">Ø 20.0 mm</option>
                    </select>
                </div>
                <div class="campo">
                    <label>Transpasse Comercial (cm):</label>
                    <input type="text" id="transpasse" value="90">
                </div>
                <div class="campo">
                    <label>Comprimento da Dobra (cm):</label>
                    <input type="text" id="dobra" value="15">
                </div>
                <input type="hidden" id="modulo" value="65">
                <div class="campo" style="margin-top:10px; padding-top:8px; border-top:1px dashed #bbdefb;">
                    <label style="color:#0d47a1; font-weight:600;">Apenas Contar Nervuras:</label>
                    <input type="checkbox" id="apenas_contar" onchange="toggleModoContar()" style="width:18px; height:18px; cursor:pointer;">
                </div>
            </div>

            <div class="info-box">
                💡 <b>Instrução:</b> Clique 2 pontos na horizontal para definir a faixa. Com <i>Apenas Contar</i> marcado, indica a contagem das nervuras sem desenhar as barras de armadura.
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
    Entry point do plugin para MODO VERTICAL no TQS EAG.
    """
    try:
        dados = pedir_dados_laje_vertical()
        if dados is None:
            return

        faixa_idx = 1
        modo_txt = "CONTAGEM" if dados.get("apenas_contar") else "VERTICAL"
        while True:
            prompt1 = f"Clique o 1º ponto da {faixa_idx}ª faixa ({modo_txt}) [Botão Direito ou Esc para ENCERRAR]:"
            icod1, x1, y1 = eag.locate.GetPoint(tqsjan, prompt1)
            if icod1 != 1:
                break

            prompt2 = f"Clique o 2º ponto da {faixa_idx}ª faixa ({modo_txt}) [Botão Direito ou Esc para CANCELAR]:"
            icod2, x2, y2 = eag.locate.GetSecondPoint(
                tqsjan, x1, y1,
                TQSEag.EAG_RUBLINEAR,
                TQSEag.EAG_RUBRET_NAOPREEN,
                prompt2
            )
            if icod2 != 1:
                break

            processar_faixa_vertical(tqsjan.dwg, x1, y1, x2, y2, dados)
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
