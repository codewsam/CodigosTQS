# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - ARMAÇÃO DE FUROS EM LAJE (TQS EAG)
================================================================================
Este módulo implementa o reforço automático de furos soltos em lajes de concreto
utilizando elementos nativos de armadura do TQS (SmartRebar / IPOFER).

Características:
- Criação de ferros reais (SmartRebar):
  - Reconhecidos nativamente pelo EAG como IPOFER.
  - Símbolo oficial da bitola (Phi) renderizado perfeitamente pela fonte TQS.
  - Integrados à tabela de ferros e quantitativos do projeto.
  - Nível 220, Cor 4 (Ciano).
- Detecção e Tratamento de Obstáculos / Pilares (Cor 1 Vermelha / Nível 227):
  - Identifica automaticamente linhas vermelhas de pilar próximas ao furo.
  - NÃO invade o pilar: as barras horizontais param antes do pilar com cobrimento
    respeitado (ex: 3 cm antes da face do pilar).
  - Aloca os 2 ferros verticais no espaço de concreto entre o furo e a face do pilar.
  - Ajusta o comprimento real (C=...) e o posicionamento das chamadas.
- Tratamento de Furos Próximos (distância <= 50 cm):
  - Unifica a armadura horizontal em ferros contínuos de ponta a ponta.
  - Insere exatamente 2 ferros verticais em cada espaço/nervo entre os furos.
  - Mantém 2 ferros verticais nas extremidades externas.
  - Notação atualizada proporcionalmente (ex: 3x2, 4x2...).
- Notação com chamadas limpas e organizadas ao lado dos ferros:
  - 1 chamada com seta para as barras horizontais.
  - 1 chamada com seta para as barras verticais.
- Cotagem de Transpasse (60 cm):
  - Cota de 60 na horizontal e na vertical nas faces livres.
  - Padrão TQS com ticks inclinados e linhas no Nível 221.
================================================================================
"""
import math
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag


COBRIMENTO = 3.0          # Cobrimento de 3 cm da face do furo e do pilar
PASSAR = 60.0             # O ferro passa 60 cm dos dois lados do furo
BITOLA = 10.0             # Bitola padrão de 10.0 mm
ESPAC_BARRAS = 5.0        # Espaçamento de 5 cm entre os 2 ferros paralelos
NIVEL_ARMADURA = 220      # Nível TQS oficial para armaduras
COR_ARMADURA = 4          # Ciano (cor 4 do TQS)
NIVEL_FURO = 237          # Nível TQS oficial para contorno de furo
NIVEL_COTA = 221          # Nível TQS oficial para linhas e textos de cotagem
DIST_MAX_UNIR = 50.0      # Furos a até 50 cm são agrupados como um conjunto contínuo


def _unir_caixas(lista_segs, tol=2.5):
    """
    Agrupa segmentos ou caixas conectadas dentro de uma tolerância pequena (tol cm).
    Elementos do mesmo furo (linhas e diagonais do retângulo) se agrupam;
    furos separados (mesmo que próximos, com espaçamento >= 4 cm) mantêm-se individuais.
    """
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


def _agrupar_furos_com_subfuros(furos_individuais, tol=50.0):
    """
    Agrupa furos individuais próximos (distância <= tol) mantendo a lista
    de subfuros internos para posicionamento das barras intermediárias.
    Retorna lista de dicts: [{'box': (xmin, ymin, xmax, ymax), 'subfuros': [...]}, ...]
    """
    grupos = [{'box': list(f), 'subfuros': [tuple(f)]} for f in furos_individuais]
    mudou = True
    while mudou:
        mudou = False
        for i in range(len(grupos)):
            for j in range(i + 1, len(grupos)):
                b1 = grupos[i]['box']
                b2 = grupos[j]['box']
                if (b1[0] - tol <= b2[2] and b2[0] - tol <= b1[2] and
                    b1[1] - tol <= b2[3] and b2[1] - tol <= b1[3]):
                    b1[0] = min(b1[0], b2[0])
                    b1[1] = min(b1[1], b2[1])
                    b1[2] = max(b1[2], b2[2])
                    b1[3] = max(b1[3], b2[3])
                    grupos[i]['subfuros'].extend(grupos[j]['subfuros'])
                    grupos.pop(j)
                    mudou = True
                    break
            if mudou:
                break

    resultado = []
    for g in grupos:
        resultado.append({
            'box': tuple(g['box']),
            'subfuros': sorted(g['subfuros'], key=lambda s: (s[0], s[1]))
        })
    return resultado


def detectar_furos(dwg, xmin_sel, ymin_sel, xmax_sel, ymax_sel):
    """
    Localiza todos os furos no Nível 237 dentro da janela selecionada.
    Retorna uma lista de dicts: [{'box': (xmin, ymin, xmax, ymax), 'subfuros': [...]}, ...]
    """
    segs = []
    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break

            nivel = getattr(dwg.iterator, "level", 0)
            if nivel != NIVEL_FURO:
                continue

            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                if (max(lx1, lx2) >= xmin_sel - 5.0 and min(lx1, lx2) <= xmax_sel + 5.0 and
                    max(ly1, ly2) >= ymin_sel - 5.0 and min(ly1, ly2) <= ymax_sel + 5.0):
                    segs.append((min(lx1, lx2), min(ly1, ly2), max(lx1, lx2), max(ly1, ly2)))

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 3), getattr(TQSDwg, "DWGTYPE_CURVE", 8)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    pxs = [p[0] for p in pts]
                    pys = [p[1] for p in pts]
                    if (max(pxs) >= xmin_sel - 5.0 and min(pxs) <= xmax_sel + 5.0 and
                        max(pys) >= ymin_sel - 5.0 and min(pys) <= ymax_sel + 5.0):
                        segs.append((min(pxs), min(pys), max(pxs), max(pys)))
                except Exception:
                    pass
    except Exception:
        pass

    if segs:
        # 1. Agrupa os traços individuais para obter os contornos de cada furo individualmente
        caixas_furos = _unir_caixas(segs, tol=2.5)
        furos_validos = []
        for c in caixas_furos:
            larg = c[2] - c[0]
            alt = c[3] - c[1]
            if larg >= 3.0 and alt >= 3.0:
                furos_validos.append((c[0], c[1], c[2], c[3]))

        if furos_validos:
            # 2. Agrupa furos próximos (<= DIST_MAX_UNIR) mantendo a lista de subfuros
            return _agrupar_furos_com_subfuros(furos_validos, tol=DIST_MAX_UNIR)

    box_padrao = (xmin_sel, ymin_sel, xmax_sel, ymax_sel)
    return [{'box': box_padrao, 'subfuros': [box_padrao]}]


def _linhas_distintas(valores, tol=3.0):
    """Retorna lista ordenada de coordenadas distintas (filtrando duplicatas a menos de tol cm)."""
    if not valores:
        return []
    val_ord = sorted(valores)
    linhas = [val_ord[0]]
    for v in val_ord[1:]:
        if abs(v - linhas[-1]) > tol:
            linhas.append(v)
    return linhas


def detectar_obstaculos_pilar(dwg, xmin, ymin, xmax, ymax, margem=80.0):
    """
    Identifica se há contornos de pilar (linhas vermelhas / Cor 1 ou Nível 227)
    nas proximidades do furo (dentro do alcance de transpasse de 60-80 cm).
    Retorna dict com as coordenadas limites e flags de colado:
    {'dir': x, 'esq': x, 'top': y, 'bot': y, 'colado_dir': bool, ...}
    Se o furo estiver colado a uma linha externa de pilar/capitel e houver uma
    segunda linha interna (face real do pilar), o ferro horizontal avança até
    ancorar na SEGUNDA linha!
    """
    segs_dir = []
    segs_esq = []
    segs_top = []
    segs_bot = []

    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break

            nivel = getattr(dwg.iterator, "level", 0)
            cor = getattr(dwg.iterator, "color", -1)

            # Elementos de pilar: cor 1 (vermelho), nível 227, ou nível 201 vermelho
            eh_pilar = (cor == 1) or (nivel == 227) or (cor in (-1, 0, 1) and nivel == 201)
            if not eh_pilar:
                continue

            segs = []
            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                segs.append((dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2))
            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 3), getattr(TQSDwg, "DWGTYPE_CURVE", 8)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    for i in range(len(pts) - 1):
                        segs.append((pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]))
                    if len(pts) >= 3:
                        segs.append((pts[-1][0], pts[-1][1], pts[0][0], pts[0][1]))
                except Exception:
                    pass

            for x1, y1, x2, y2 in segs:
                dx = abs(x2 - x1)
                dy = abs(y2 - y1)
                min_x, max_x = min(x1, x2), max(x1, x2)
                min_y, max_y = min(y1, y2), max(y1, y2)

                # Segmento vertical (face esquerda ou direita de pilar)
                if dx <= 5.0 and dy >= 5.0:
                    x_seg = (x1 + x2) / 2.0
                    # Verifica se o segmento intercepta a faixa vertical do furo
                    if max_y >= ymin - 15.0 and min_y <= ymax + 15.0:
                        # Pilar à direita
                        if xmax - 5.0 <= x_seg <= xmax + margem:
                            segs_dir.append(x_seg)
                        # Pilar à esquerda
                        elif xmin - margem <= x_seg <= xmin + 5.0:
                            segs_esq.append(x_seg)

                # Segmento horizontal (face superior ou inferior de pilar)
                elif dy <= 5.0 and dx >= 5.0:
                    y_seg = (y1 + y2) / 2.0
                    # Verifica se o segmento intercepta a faixa horizontal do furo
                    if max_x >= xmin - 15.0 and min_x <= xmax + 15.0:
                        # Pilar acima
                        if ymax - 5.0 <= y_seg <= ymax + margem:
                            segs_top.append(y_seg)
                        # Pilar abaixo
                        elif ymin - margem <= y_seg <= ymin + 5.0:
                            segs_bot.append(y_seg)
    except Exception:
        pass

    # Análise das linhas à direita
    lim_dir = None
    colado_dir = False
    linhas_dir = _linhas_distintas(segs_dir)
    if linhas_dir:
        if linhas_dir[0] <= xmax + 8.0:
            colado_dir = True
            # Se colado e há uma segunda linha (face interna do pilar), ancora na SEGUNDA linha!
            if len(linhas_dir) >= 2:
                lim_dir = linhas_dir[1]
            else:
                lim_dir = linhas_dir[0]
        else:
            lim_dir = linhas_dir[0]

    # Análise das linhas à esquerda
    lim_esq = None
    colado_esq = False
    linhas_esq = sorted(_linhas_distintas(segs_esq), reverse=True)
    if linhas_esq:
        if linhas_esq[0] >= xmin - 8.0:
            colado_esq = True
            if len(linhas_esq) >= 2:
                lim_esq = linhas_esq[1]
            else:
                lim_esq = linhas_esq[0]
        else:
            lim_esq = linhas_esq[0]

    # Análise das linhas acima
    lim_top = None
    colado_top = False
    linhas_top = _linhas_distintas(segs_top)
    if linhas_top:
        if linhas_top[0] <= ymax + 8.0:
            colado_top = True
            if len(linhas_top) >= 2:
                lim_top = linhas_top[1]
            else:
                lim_top = linhas_top[0]
        else:
            lim_top = linhas_top[0]

    # Análise das linhas abaixo
    lim_bot = None
    colado_bot = False
    linhas_bot = sorted(_linhas_distintas(segs_bot), reverse=True)
    if linhas_bot:
        if linhas_bot[0] >= ymin - 8.0:
            colado_bot = True
            if len(linhas_bot) >= 2:
                lim_bot = linhas_bot[1]
            else:
                lim_bot = linhas_bot[0]
        else:
            lim_bot = linhas_bot[0]

    return {
        'dir': lim_dir, 'esq': lim_esq, 'top': lim_top, 'bot': lim_bot,
        'colado_dir': colado_dir, 'colado_esq': colado_esq,
        'colado_top': colado_top, 'colado_bot': colado_bot
    }


def desenhar_cota_horizontal(draw, x1, x2, y_cota, witness_y_start, valor_txt="60", h=4.2):
    """
    Desenha uma linha de cota horizontal no padrão TQS (Nível 221):
    - Linha de cota com prolongamentos de 2.5 cm.
    - Linhas de testemunha conectando o ponto medido até além da cota.
    - Ticks inclinados a 45 graus nas extremidades.
    - Valor numérico da cota centralizado em Amarelo.
    """
    draw.level = NIVEL_COTA
    draw.color = 3  # Verde
    draw.style = 0

    # Linha principal
    draw.Line(x1 - 2.5, y_cota, x2 + 2.5, y_cota)

    # Linhas de testemunha
    draw.Line(x1, witness_y_start, x1, y_cota - 2.5)
    draw.Line(x2, witness_y_start, x2, y_cota - 2.5)

    # Ticks a 45 graus
    t = 1.2
    draw.Line(x1 - t, y_cota - t, x1 + t, y_cota + t)
    draw.Line(x2 - t, y_cota - t, x2 + t, y_cota + t)

    # Texto da cota
    draw.color = 2  # Amarelo
    xm = (x1 + x2) / 2.0
    larg_txt = len(valor_txt) * (h * 0.70)
    draw.Text(xm - larg_txt / 2.0, y_cota + 1.2, h, 0.0, str(valor_txt))


def desenhar_cota_vertical(draw, y1, y2, x_cota, witness_x_start, valor_txt="60", h=4.2):
    """
    Desenha uma linha de cota vertical no padrão TQS (Nível 221):
    - Linha de cota vertical com prolongamentos de 2.5 cm.
    - Linhas de testemunha da peça até além da cota.
    - Ticks inclinados a 45 graus nas extremidades.
    - Valor numérico da cota a 90 graus em Amarelo.
    """
    draw.level = NIVEL_COTA
    draw.color = 3  # Verde
    draw.style = 0

    # Linha principal
    draw.Line(x_cota, y1 - 2.5, x_cota, y2 + 2.5)

    # Linhas de testemunha
    draw.Line(witness_x_start, y1, x_cota - 2.5, y1)
    draw.Line(witness_x_start, y2, x_cota - 2.5, y2)

    # Ticks a 45 graus
    t = 1.2
    draw.Line(x_cota - t, y1 - t, x_cota + t, y1 + t)
    draw.Line(x_cota - t, y2 - t, x_cota + t, y2 + t)

    # Texto da cota a 90 graus
    draw.color = 2  # Amarelo
    ym = (y1 + y2) / 2.0
    larg_txt = len(valor_txt) * (h * 0.70)
    draw.Text(x_cota - 1.5, ym - larg_txt / 2.0, h, 90.0, str(valor_txt))


def armar_furo_solto(dwg, xmin, ymin, xmax, ymax, marca_h, marca_v, subfuros=None):
    """
    Cria ferros nativos do TQS (SmartRebar / IPOFER) para armar o furo ou conjunto de furos:
    - Se houver pilar (linha vermelha), interrompe a armadura antes da face com cobrimento.
    - Barras horizontais contínuas em Ciano (2 topo + 2 base cobrindo toda a extensão).
    - Barras verticais em Ciano: 2 na borda esquerda, 2 na borda direita E exatamente
      2 barras verticais em cada espaço/nervo intermediário entre furos próximos.
    - Chamadas automáticas posicionadas ao lado dos ferros, sem colisões.
    - Cotas de 60 cm na horizontal e na vertical indicando o transpasse nas faces livres.
    """
    draw = dwg.draw

    # 1. Detecta se há pilares vermelhos vizinhos limitando a passagem das barras
    obs = detectar_obstaculos_pilar(dwg, xmin, ymin, xmax, ymax)

    # Limites X para barras horizontais
    x_h_ini = xmin - PASSAR
    if obs['esq'] is not None:
        x_h_ini = max(x_h_ini, obs['esq'] + COBRIMENTO)

    x_h_fim = xmax + PASSAR
    if obs['dir'] is not None:
        x_h_fim = min(x_h_fim, obs['dir'] - COBRIMENTO)

    # Limites Y para barras verticais
    y_v_ini = ymin - PASSAR
    if obs['bot'] is not None:
        y_v_ini = max(y_v_ini, obs['bot'] + COBRIMENTO)

    y_v_fim = ymax + PASSAR
    if obs['top'] is not None:
        y_v_fim = min(y_v_fim, obs['top'] - COBRIMENTO)

    # Comprimentos efetivos
    comp_h = int(round(x_h_fim - x_h_ini))
    comp_v = int(round(y_v_fim - y_v_ini))

    # Linhas horizontais (Y) de contorno externo
    tem_horizontal_top = True
    if obs.get('colado_top', False):
        tem_horizontal_top = False
        y_top_outer = y_top_inner = ymax + COBRIMENTO
    elif obs['top'] is not None:
        gap_t = obs['top'] - ymax
        if gap_t < (2.0 * COBRIMENTO + ESPAC_BARRAS + 2.0):
            tem_horizontal_top = False
            y_top_outer = y_top_inner = ymax + COBRIMENTO
        else:
            y_top_outer = min(ymax + COBRIMENTO + ESPAC_BARRAS, obs['top'] - COBRIMENTO)
            y_top_inner = ymax + COBRIMENTO
    else:
        y_top_inner = ymax + COBRIMENTO
        y_top_outer = ymax + COBRIMENTO + ESPAC_BARRAS

    tem_horizontal_bot = True
    if obs.get('colado_bot', False):
        tem_horizontal_bot = False
        y_bot_outer = y_bot_inner = ymin - COBRIMENTO
    elif obs['bot'] is not None:
        gap_b = ymin - obs['bot']
        if gap_b < (2.0 * COBRIMENTO + ESPAC_BARRAS + 2.0):
            tem_horizontal_bot = False
            y_bot_outer = y_bot_inner = ymin - COBRIMENTO
        else:
            y_bot_outer = max(ymin - COBRIMENTO - ESPAC_BARRAS, obs['bot'] + COBRIMENTO)
            y_bot_inner = ymin - COBRIMENTO
    else:
        y_bot_inner = ymin - COBRIMENTO
        y_bot_outer = ymin - COBRIMENTO - ESPAC_BARRAS

    # Linhas verticais (X) de contorno externo
    tem_vertical_dir = True
    if obs.get('colado_dir', False):
        tem_vertical_dir = False
        x_dir_outer = x_dir_inner = xmax + COBRIMENTO
    elif obs['dir'] is not None:
        gap_d = obs['dir'] - xmax
        # Se a face do pilar está encostada ou muito próxima (gap < 13 cm),
        # NÃO gera ferros dentro do pilar nem no vão minúsculo
        if gap_d < (2.0 * COBRIMENTO + ESPAC_BARRAS + 2.0):
            tem_vertical_dir = False
            x_dir_outer = x_dir_inner = xmax + COBRIMENTO
        else:
            x_dir_outer = min(xmax + COBRIMENTO + ESPAC_BARRAS, obs['dir'] - COBRIMENTO)
            x_dir_inner = xmax + COBRIMENTO
    else:
        x_dir_inner = xmax + COBRIMENTO
        x_dir_outer = xmax + COBRIMENTO + ESPAC_BARRAS

    tem_vertical_esq = True
    if obs.get('colado_esq', False):
        tem_vertical_esq = False
        x_esq_outer = x_esq_inner = xmin - COBRIMENTO
    elif obs['esq'] is not None:
        gap_e = xmin - obs['esq']
        if gap_e < (2.0 * COBRIMENTO + ESPAC_BARRAS + 2.0):
            tem_vertical_esq = False
            x_esq_outer = x_esq_inner = xmin - COBRIMENTO
        else:
            x_esq_outer = max(xmin - COBRIMENTO - ESPAC_BARRAS, obs['esq'] + COBRIMENTO)
            x_esq_inner = xmin - COBRIMENTO
    else:
        x_esq_inner = xmin - COBRIMENTO
        x_esq_outer = xmin - COBRIMENTO - ESPAC_BARRAS

    # Identifica vãos intermediários em X (furos lado a lado) e em Y (furos empilhados)
    gaps_x = []
    gaps_y = []
    if subfuros and len(subfuros) > 1:
        sub_x = sorted(subfuros, key=lambda f: f[0])
        for i in range(len(sub_x) - 1):
            x1_gap = sub_x[i][2]
            x2_gap = sub_x[i+1][0]
            if (x2_gap - x1_gap) >= 2.0:
                gaps_x.append((x1_gap + x2_gap) / 2.0)

        sub_y = sorted(subfuros, key=lambda f: f[1])
        for j in range(len(sub_y) - 1):
            y1_gap = sub_y[j][3]
            y2_gap = sub_y[j+1][1]
            if (y2_gap - y1_gap) >= 2.0:
                gaps_y.append((y1_gap + y2_gap) / 2.0)

    # -------------------------------------------------------------------------
    # 2. FERRO HORIZONTAL (SMARTREBAR)
    # -------------------------------------------------------------------------
    num_pares_h = (1 if tem_horizontal_top else 0) + len(gaps_y) + (1 if tem_horizontal_bot else 0)
    num_pares_h = max(1, num_pares_h)
    sr_h = TQSDwg.SmartRebar(dwg)
    sr_h.type = getattr(TQSDwg, "ICPFRT", 1)  # Ferro reto
    sr_h.multiplier = num_pares_h
    sr_h.quantity = 2                         # 2 barras por par
    sr_h.diameter = BITOLA
    sr_h.straightBarMainLength = float(comp_h)
    sr_h.mark = int(marca_h)
    sr_h.straightBarZone = getattr(TQSDwg, "ICPPOS", 0)
    sr_h.leaderLine = 1
    sr_h.leaderLineDistance = 0.1

    # Insere as barras horizontais em CIANO (cor 4) no Nível 220
    first_h = True
    if tem_horizontal_top:
        sr_h.RebarLine(x_h_ini, y_top_outer, 0.0, 1.0, 1 if first_h else 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
        first_h = False
        sr_h.RebarLine(x_h_ini, y_top_inner, 0.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)

    for ym in gaps_y:
        y_mid1 = ym + (ESPAC_BARRAS / 2.0)
        y_mid2 = ym - (ESPAC_BARRAS / 2.0)
        sr_h.RebarLine(x_h_ini, y_mid1, 0.0, 1.0, 1 if first_h else 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
        first_h = False
        sr_h.RebarLine(x_h_ini, y_mid2, 0.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)

    if tem_horizontal_bot:
        sr_h.RebarLine(x_h_ini, y_bot_inner, 0.0, 1.0, 1 if first_h else 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
        first_h = False
        sr_h.RebarLine(x_h_ini, y_bot_outer, 0.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)

    # Formatação do texto do ferro horizontal
    if obs['dir'] is not None:
        sr_h.RebarTextDisplaySelection(
            1, 1, 1, 0, 1,
            getattr(TQSDwg, "ICPCENTR_CENTRAD", 0),
            getattr(TQSDwg, "ICPQUEBR_SEMQUEBRA", 0)
        )
        x_txt_h = (x_h_ini + x_h_fim) / 2.0
        if obs['dir'] is not None:
            x_txt_h = min(x_txt_h, obs['dir'] - 30.0)
        y_txt_h = y_top_outer + 25.0
        try:
            sr_h.RebarTextDisplayPosition(
                x_txt_h, y_txt_h, 4.5, 0.0, 0,
                getattr(TQSDwg, "ICPCENTR_CENTRAD", 0),
                getattr(TQSDwg, "ICPQUEBR_SEMQUEBRA", 0)
            )
        except Exception:
            pass
    else:
        # Espaço livre à direita: texto após a ponta direita da barra
        sr_h.RebarTextDisplaySelection(
            1, 1, 1, 0, 1,
            getattr(TQSDwg, "ICPCENTR_ESQUERD", 1),
            getattr(TQSDwg, "ICPQUEBR_SEMQUEBRA", 0)
        )
        x_txt_h = x_h_fim + 15.0
        y_txt_h = y_top_outer + 12.0
        try:
            sr_h.RebarTextDisplayPosition(
                x_txt_h, y_txt_h, 4.5, 0.0, 0,
                getattr(TQSDwg, "ICPCENTR_ESQUERD", 1),
                getattr(TQSDwg, "ICPQUEBR_SEMQUEBRA", 0)
            )
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # 3. FERRO VERTICAL (SMARTREBAR)
    # -------------------------------------------------------------------------
    num_pares_v = (1 if tem_vertical_esq else 0) + len(gaps_x) + (1 if tem_vertical_dir else 0)
    num_pares_v = max(1, num_pares_v)
    sr_v = TQSDwg.SmartRebar(dwg)
    sr_v.type = getattr(TQSDwg, "ICPFRT", 1)  # Ferro reto
    sr_v.multiplier = num_pares_v             # Borda esq + vão(s) intermediário(s) + borda dir
    sr_v.quantity = 2                         # 2 barras por par
    sr_v.diameter = BITOLA
    sr_v.straightBarMainLength = float(comp_v)
    sr_v.mark = int(marca_v)
    sr_v.straightBarZone = getattr(TQSDwg, "ICPPOS", 0)
    sr_v.leaderLine = 1
    sr_v.leaderLineDistance = 0.1

    # Insere as barras verticais e determina qual recebe a linha de chamada (lLeader)
    first_v = True
    x_v_lead = None

    if tem_vertical_dir:
        sr_v.RebarLine(x_dir_outer, y_v_ini, 90.0, 1.0, 1 if first_v else 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
        if first_v:
            x_v_lead = x_dir_outer
            first_v = False
        sr_v.RebarLine(x_dir_inner, y_v_ini, 90.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)

    # Insere exatamente 2 ferros verticais em cada vão intermediário entre furos próximos
    for xm in reversed(gaps_x):
        x_mid2 = xm + (ESPAC_BARRAS / 2.0)
        x_mid1 = xm - (ESPAC_BARRAS / 2.0)
        sr_v.RebarLine(x_mid2, y_v_ini, 90.0, 1.0, 1 if first_v else 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
        if first_v:
            x_v_lead = x_mid2
            first_v = False
        sr_v.RebarLine(x_mid1, y_v_ini, 90.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)

    if tem_vertical_esq:
        sr_v.RebarLine(x_esq_inner, y_v_ini, 90.0, 1.0, 1 if first_v else 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
        if first_v:
            x_v_lead = x_esq_inner
            first_v = False
        sr_v.RebarLine(x_esq_outer, y_v_ini, 90.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)

    if x_v_lead is None:
        x_v_lead = (xmin + xmax) / 2.0

    # Formatação do texto do ferro vertical
    sr_v.RebarTextDisplaySelection(
        1, 1, 1, 0, 1,
        getattr(TQSDwg, "ICPCENTR_CENTRAD", 0),
        getattr(TQSDwg, "ICPQUEBR_SEMQUEBRA", 0)
    )
    if tem_vertical_dir and obs['dir'] is None:
        x_txt_v = x_v_lead + 30.0
    elif obs['dir'] is not None:
        x_txt_v = min(x_v_lead + 10.0, obs['dir'] - 30.0)
    else:
        x_txt_v = x_v_lead + 20.0

    y_txt_v = y_v_fim + 20.0
    try:
        sr_v.RebarTextDisplayPosition(
            x_txt_v, y_txt_v, 4.5, 0.0, 0,
            getattr(TQSDwg, "ICPCENTR_CENTRAD", 0),
            getattr(TQSDwg, "ICPQUEBR_SEMQUEBRA", 0)
        )
    except Exception:
        pass

    # -------------------------------------------------------------------------
    # 4. COTAS DE TRANSPASSE (60 cm)
    # -------------------------------------------------------------------------
    txt_cota = f"{int(PASSAR)}"

    # 4.1 Cota Horizontal: posicionada na face que possui o transpasse livre de 60 cm
    ref_y_witness = y_bot_outer if tem_horizontal_bot else (ymin - COBRIMENTO)
    if obs['esq'] is None:
        y_cota_h = ref_y_witness - 15.0
        desenhar_cota_horizontal(draw, x_h_ini, xmin, y_cota_h, ref_y_witness, txt_cota, h=4.2)
    elif obs['dir'] is None:
        y_cota_h = ref_y_witness - 15.0
        desenhar_cota_horizontal(draw, xmax, x_h_fim, y_cota_h, ref_y_witness, txt_cota, h=4.2)

    # 4.2 Cota Vertical: posicionada na face que possui o transpasse livre de 60 cm
    ref_x_witness = x_esq_outer if tem_vertical_esq else (xmin - COBRIMENTO)
    if obs['bot'] is None:
        x_cota_v = ref_x_witness - 15.0
        desenhar_cota_vertical(draw, y_v_ini, ymin, x_cota_v, ref_x_witness, txt_cota, h=4.2)
    elif obs['top'] is None:
        x_cota_v = ref_x_witness - 15.0
        desenhar_cota_vertical(draw, ymax, y_v_fim, x_cota_v, ref_x_witness, txt_cota, h=4.2)


def meucmd(eag, tqsjan):
    """
    Entry point do plugin 'Furos' chamado pelo menu do TQS EAG.
    Abre janela cobrindo um ou mais furos e arma cada um separadamente com ferros reais.
    """
    try:
        dwg = tqsjan.dwg
        janela_idx = 1
        marcas_globais = {}

        def _obter_marca(chave):
            if chave not in marcas_globais:
                try:
                    f_m = dwg.globalrebar.FreeMark()
                    marcas_globais[chave] = f_m if f_m > 0 else (len(marcas_globais) + 1)
                except Exception:
                    marcas_globais[chave] = len(marcas_globais) + 1
            return marcas_globais[chave]

        while True:
            prompt1 = f"Abra a janela sobre o(s) furo(s) [Botão Direito ou Esc para ENCERRAR]:"
            icod1, x1, y1 = eag.locate.GetPoint(tqsjan, prompt1)
            if icod1 != 1:
                break

            prompt2 = f"Clique o canto oposto (arraste o retângulo cobrindo o(s) furo(s)):"
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

            if (xmax_sel - xmin_sel) < 5.0 or (ymax_sel - ymin_sel) < 5.0:
                continue

            # Detecta os furos no Nível 237 com agrupamento de furos próximos
            grupos = detectar_furos(
                dwg, xmin_sel, ymin_sel, xmax_sel, ymax_sel
            )

            # Arma cada grupo de furos com ferros nativos e respeito a pilares
            for g in grupos:
                xmin_f, ymin_f, xmax_f, ymax_f = g['box']
                subfuros_g = g['subfuros']

                # Verifica se há pilar para estimar o comprimento real da barra
                obs = detectar_obstaculos_pilar(dwg, xmin_f, ymin_f, xmax_f, ymax_f)
                x_ini_ef = xmin_f - PASSAR if obs['esq'] is None else max(xmin_f - PASSAR, obs['esq'] + COBRIMENTO)
                x_fim_ef = xmax_f + PASSAR if obs['dir'] is None else min(xmax_f + PASSAR, obs['dir'] - COBRIMENTO)
                y_ini_ef = ymin_f - PASSAR if obs['bot'] is None else max(ymin_f - PASSAR, obs['bot'] + COBRIMENTO)
                y_fim_ef = ymax_f + PASSAR if obs['top'] is None else min(ymax_f + PASSAR, obs['top'] - COBRIMENTO)

                comp_h_int = int(round(x_fim_ef - x_ini_ef))
                comp_v_int = int(round(y_fim_ef - y_ini_ef))

                chave_h = (comp_h_int, BITOLA)
                marca_h = _obter_marca(chave_h)

                chave_v = (comp_v_int, BITOLA)
                marca_v = _obter_marca(chave_v)
                if marca_v == marca_h and comp_v_int != comp_h_int:
                    marca_v = marca_h + 1
                    marcas_globais[chave_v] = marca_v

                armar_furo_solto(dwg, xmin_f, ymin_f, xmax_f, ymax_f, marca_h, marca_v, subfuros=subfuros_g)

            tqsjan.Regen()
            janela_idx += 1

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
