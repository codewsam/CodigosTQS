# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - ARMAÇÃO DE FUROS EM LAJE (TQS EAG)
================================================================================
Este módulo implementa o reforço de furos soltos em lajes de concreto.
- O usuário abre uma janela de seleção cobrindo o furo no EAG.
- O plugin detecta automaticamente os limites do furo no Nível 237.
- Insere 2 ferros horizontais no topo e 2 ferros horizontais na base.
- Insere 2 ferros verticais à esquerda e 2 ferros verticais à direita.
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


def detectar_furo(dwg, xmin_sel, ymin_sel, xmax_sel, ymax_sel):
    """
    Localiza o contorno do furo no Nível 237 dentro da janela selecionada pelo usuário.
    Retorna (xmin, ymin, xmax, ymax).
    """
    xs = []
    ys = []
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
                    xs.extend([lx1, lx2])
                    ys.extend([ly1, ly2])

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    pxs = [p[0] for p in pts]
                    pys = [p[1] for p in pts]
                    if (max(pxs) >= xmin_sel - 5.0 and min(pxs) <= xmax_sel + 5.0 and
                        max(pys) >= ymin_sel - 5.0 and min(pys) <= ymax_sel + 5.0):
                        xs.extend(pxs)
                        ys.extend(pys)
                except Exception:
                    pass
    except Exception:
        pass

    if xs and ys:
        xmin = min(xs)
        xmax = max(xs)
        ymin = min(ys)
        ymax = max(ys)
        larg = xmax - xmin
        alt = ymax - ymin
        if larg >= 3.0 and alt >= 3.0:
            return xmin, ymin, xmax, ymax

    return xmin_sel, ymin_sel, xmax_sel, ymax_sel


def desenhar_barra(draw, x1, y1, x2, y2):
    """Desenha a linha do ferro em Ciano (cor 4) no Nível 220."""
    draw.level = NIVEL_ARMADURA
    draw.color = COR_ARMADURA  # Ciano (cor 4)
    draw.style = 0
    draw.Line(x1, y1, x2, y2)


def armar_furo_solto(dwg, xmin, ymin, xmax, ymax):
    """
    Posiciona exatamente 2 ferros em cada um dos 4 lados do furo em CIANO:
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
    Abre janela sobre o furo para armá-lo diretamente com as barras em ciano.
    """
    try:
        dwg = tqsjan.dwg
        janela_idx = 1

        while True:
            prompt1 = f"Abra a janela sobre o {janela_idx}º furo [Botão Direito ou Esc para ENCERRAR]:"
            icod1, x1, y1 = eag.locate.GetPoint(tqsjan, prompt1)
            if icod1 != 1:
                break

            prompt2 = f"Clique o canto oposto (arraste o retângulo cobrindo o furo):"
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

            # Detecta o furo no Nível 237 dentro da janela
            xmin_f, ymin_f, xmax_f, ymax_f = detectar_furo(
                dwg, xmin_sel, ymin_sel, xmax_sel, ymax_sel
            )

            # Desenha apenas as barras dos ferros em ciano
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
