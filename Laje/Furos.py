# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - ARMAÇÃO DE FUROS EM LAJE (TQS EAG)
================================================================================
Este módulo implementa o reforço de furos soltos em lajes de concreto.
- O usuário abre uma janela de seleção cobrindo um ou mais furos no EAG.
- O plugin detecta automaticamente cada furo individual no Nível 237.
- Se houver múltiplos furos distantes na seleção, arma cada um separadamente.
- Insere 2 ferros horizontais no topo e 2 ferros horizontais na base de cada furo.
- Insere 2 ferros verticais à esquerda e 2 ferros verticais à direita de cada furo.
- Cobrimento: 3 cm da face do furo.
- Extensão: o ferro passa 60 cm de cada lado do furo.
- Cor da Armadura: Ciano (cor 4) no Nível 220.
- Apenas as barras dos ferros (sem textos informativos).
================================================================================
"""
import math
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag


COBRIMENTO = 3.0          # Cobrimento de 3 cm da face do furo
PASSAR = 60.0             # O ferro passa 60 cm dos dois lados do furo
ESPAC_BARRAS = 5.0        # Espaçamento de 5 cm entre os 2 ferros paralelos
NIVEL_ARMADURA = 220      # Nível TQS oficial para armaduras
COR_ARMADURA = 4          # Ciano (cor 4 do TQS)
NIVEL_FURO = 237          # Nível TQS oficial para contorno de furo


def _unir_caixas(lista_segs, tol=12.0):
    """
    Agrupa segmentos ou caixas conectadas dentro de uma tolerância (tol cm).
    Elementos do mesmo furo se agrupam; furos separados mantêm-se individuais.
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


def detectar_furos(dwg, xmin_sel, ymin_sel, xmax_sel, ymax_sel):
    """
    Localiza todos os furos distintos no Nível 237 dentro da janela selecionada.
    Retorna uma lista de tuplas: [(xmin, ymin, xmax, ymax), ...]
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

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
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
        # Agrupa segmentos conectados para formar cada furo individual
        caixas_furos = _unir_caixas(segs, tol=12.0)
        furos_validos = []
        for c in caixas_furos:
            larg = c[2] - c[0]
            alt = c[3] - c[1]
            if larg >= 3.0 and alt >= 3.0:
                furos_validos.append((c[0], c[1], c[2], c[3]))

        if furos_validos:
            return furos_validos

    return [(xmin_sel, ymin_sel, xmax_sel, ymax_sel)]


def desenhar_barra(draw, x1, y1, x2, y2):
    """Desenha a linha do ferro em Ciano (cor 4) no Nível 220."""
    draw.level = NIVEL_ARMADURA
    draw.color = COR_ARMADURA  # Ciano (cor 4)
    draw.style = 0
    draw.Line(x1, y1, x2, y2)


def armar_furo_solto(dwg, xmin, ymin, xmax, ymax):
    """
    Posiciona exatamente 2 ferros em cada um dos 4 lados de um furo em CIANO:
    - 2 ferros horizontais no topo
    - 2 ferros horizontais na base
    - 2 ferros verticais à esquerda
    - 2 ferros verticais à direita
    Passando 60 cm dos dois lados do furo com cobrimento de 3 cm da face.
    Sem nenhum texto informativo.
    """
    draw = dwg.draw

    # Coordenadas X para barras horizontais
    x_h_ini = xmin - PASSAR
    x_h_fim = xmax + PASSAR

    # Coordenadas Y para barras verticais
    y_v_ini = ymin - PASSAR
    y_v_fim = ymax + PASSAR

    # 1. Topo (2 ferros horizontais)
    y_top_inner = ymax + COBRIMENTO
    y_top_outer = ymax + COBRIMENTO + ESPAC_BARRAS
    desenhar_barra(draw, x_h_ini, y_top_inner, x_h_fim, y_top_inner)
    desenhar_barra(draw, x_h_ini, y_top_outer, x_h_fim, y_top_outer)

    # 2. Base (2 ferros horizontais)
    y_bot_inner = ymin - COBRIMENTO
    y_bot_outer = ymin - COBRIMENTO - ESPAC_BARRAS
    desenhar_barra(draw, x_h_ini, y_bot_inner, x_h_fim, y_bot_inner)
    desenhar_barra(draw, x_h_ini, y_bot_outer, x_h_fim, y_bot_outer)

    # 3. Esquerda (2 ferros verticais)
    x_esq_inner = xmin - COBRIMENTO
    x_esq_outer = xmin - COBRIMENTO - ESPAC_BARRAS
    desenhar_barra(draw, x_esq_inner, y_v_ini, x_esq_inner, y_v_fim)
    desenhar_barra(draw, x_esq_outer, y_v_ini, x_esq_outer, y_v_fim)

    # 4. Direita (2 ferros verticais)
    x_dir_inner = xmax + COBRIMENTO
    x_dir_outer = xmax + COBRIMENTO + ESPAC_BARRAS
    desenhar_barra(draw, x_dir_inner, y_v_ini, x_dir_inner, y_v_fim)
    desenhar_barra(draw, x_dir_outer, y_v_ini, x_dir_outer, y_v_fim)


def meucmd(eag, tqsjan):
    """
    Entry point do plugin 'Furos' chamado pelo menu do TQS EAG.
    Abre janela cobrindo um ou mais furos e arma cada um separadamente.
    """
    try:
        dwg = tqsjan.dwg
        janela_idx = 1

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

            # Detecta todos os furos distintos no Nível 237 dentro da janela
            furos = detectar_furos(
                dwg, xmin_sel, ymin_sel, xmax_sel, ymax_sel
            )

            # Arma cada furo individualmente
            for xmin_f, ymin_f, xmax_f, ymax_f in furos:
                armar_furo_solto(dwg, xmin_f, ymin_f, xmax_f, ymax_f)

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
