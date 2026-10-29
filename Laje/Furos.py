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
- Notação 2x2 com uma única chamada por direção:
  - 1 chamada com seta para as 4 barras horizontais (2 topo + 2 base).
  - 1 chamada com seta para as 4 barras verticais (2 esquerda + 2 direita).
- Detecção inteligente no Nível 237:
  - Reconhece múltiplos furos distantes na mesma seleção e arma cada um separadamente.
- Parâmetros predefinidos:
  - Cobrimento: 3.0 cm da face do furo.
  - Transpasse (passar): 60.0 cm dos dois lados.
  - Bitola: 10.0 mm.
  - Espaçamento entre as barras paralelas: 5.0 cm.
================================================================================
"""
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag


COBRIMENTO = 3.0          # Cobrimento de 3 cm da face do furo
PASSAR = 60.0             # O ferro passa 60 cm dos dois lados do furo
BITOLA = 10.0             # Bitola padrão de 10.0 mm
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


def armar_furo_solto(dwg, xmin, ymin, xmax, ymax, marca_h, marca_v):
    """
    Cria ferros nativos do TQS (SmartRebar / IPOFER) para armar o furo:
    - 4 barras horizontais em Ciano (2 topo + 2 base), representadas por 1 SmartRebar (2x2).
    - 4 barras verticais em Ciano (2 esq + 2 dir), representadas por 1 SmartRebar (2x2).
    - Chamadas automáticas com seta nativas do TQS exibindo o símbolo correto da bitola.
    """
    larg_furo = xmax - xmin
    alt_furo = ymax - ymin

    comp_h = int(round(larg_furo + (2.0 * PASSAR)))
    comp_v = int(round(alt_furo + (2.0 * PASSAR)))

    # Coordenadas X para barras horizontais
    x_h_ini = xmin - PASSAR
    # Coordenadas Y para barras verticais
    y_v_ini = ymin - PASSAR

    # Linhas horizontais (Y)
    y_top_inner = ymax + COBRIMENTO
    y_top_outer = ymax + COBRIMENTO + ESPAC_BARRAS
    y_bot_inner = ymin - COBRIMENTO
    y_bot_outer = ymin - COBRIMENTO - ESPAC_BARRAS

    # Linhas verticais (X)
    x_dir_inner = xmax + COBRIMENTO
    x_dir_outer = xmax + COBRIMENTO + ESPAC_BARRAS
    x_esq_inner = xmin - COBRIMENTO
    x_esq_outer = xmin - COBRIMENTO - ESPAC_BARRAS

    # -------------------------------------------------------------------------
    # 1. FERRO HORIZONTAL (SMARTREBAR - 2x2)
    # -------------------------------------------------------------------------
    sr_h = TQSDwg.SmartRebar(dwg)
    sr_h.type = getattr(TQSDwg, "ICPFRT", 1)  # Ferro reto
    sr_h.multiplier = 2                       # 2 faces (topo e base)
    sr_h.quantity = 2                         # 2 barras por face (total 4)
    sr_h.diameter = BITOLA
    sr_h.straightBarMainLength = float(comp_h)
    sr_h.mark = int(marca_h)
    sr_h.straightBarZone = getattr(TQSDwg, "ICPPOS", 0)
    sr_h.leaderLine = 1
    sr_h.leaderLineDistance = 0.1

    # Insere as 4 barras da posição horizontal em CIANO (cor 4) no Nível 220
    # Apenas a barra externa do topo recebe identify=1 para gerar a chamada com seta
    sr_h.RebarLine(x_h_ini, y_top_outer, 0.0, 1.0, 1, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
    sr_h.RebarLine(x_h_ini, y_top_inner, 0.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
    sr_h.RebarLine(x_h_ini, y_bot_inner, 0.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
    sr_h.RebarLine(x_h_ini, y_bot_outer, 0.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)

    # Formatação do texto: '2x2 N... Phi 10 C=...'
    sr_h.RebarTextDisplaySelection(
        1, 1, 1, 0, 1,
        getattr(TQSDwg, "ICPCENTR_CENTRAD", 0),
        getattr(TQSDwg, "ICPQUEBR_SEMQUEBRA", 0)
    )
    # Posiciona o texto acima do furo com prateleira e seta descendo para as barras
    x_txt_h = (xmin + xmax) / 2.0
    y_txt_h = y_top_outer + 18.0
    try:
        sr_h.RebarTextDisplayPosition(
            x_txt_h, y_txt_h, 4.5, 0.0, 0,
            getattr(TQSDwg, "ICPCENTR_CENTRAD", 0),
            getattr(TQSDwg, "ICPQUEBR_SEMQUEBRA", 0)
        )
    except Exception:
        pass

    # -------------------------------------------------------------------------
    # 2. FERRO VERTICAL (SMARTREBAR - 2x2)
    # -------------------------------------------------------------------------
    sr_v = TQSDwg.SmartRebar(dwg)
    sr_v.type = getattr(TQSDwg, "ICPFRT", 1)  # Ferro reto
    sr_v.multiplier = 2                       # 2 faces (direita e esquerda)
    sr_v.quantity = 2                         # 2 barras por face (total 4)
    sr_v.diameter = BITOLA
    sr_v.straightBarMainLength = float(comp_v)
    sr_v.mark = int(marca_v)
    sr_v.straightBarZone = getattr(TQSDwg, "ICPPOS", 0)
    sr_v.leaderLine = 1
    sr_v.leaderLineDistance = 0.1

    # Insere as 4 barras da posição vertical a 90 graus em CIANO (cor 4) no Nível 220
    # Apenas a barra externa da direita recebe identify=1 para gerar a chamada com seta
    sr_v.RebarLine(x_dir_outer, y_v_ini, 90.0, 1.0, 1, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
    sr_v.RebarLine(x_dir_inner, y_v_ini, 90.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
    sr_v.RebarLine(x_esq_inner, y_v_ini, 90.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
    sr_v.RebarLine(x_esq_outer, y_v_ini, 90.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)

    # Formatação do texto: '2x2 N... Phi 10 C=...'
    sr_v.RebarTextDisplaySelection(
        1, 1, 1, 0, 1,
        getattr(TQSDwg, "ICPCENTR_CENTRAD", 0),
        getattr(TQSDwg, "ICPQUEBR_SEMQUEBRA", 0)
    )
    # Posiciona o texto à direita do furo com prateleira horizontal e seta apontando para as barras
    x_txt_v = x_dir_outer + 25.0
    y_txt_v = (ymin + ymax) / 2.0
    try:
        sr_v.RebarTextDisplayPosition(
            x_txt_v, y_txt_v, 4.5, 0.0, 0,
            getattr(TQSDwg, "ICPCENTR_CENTRAD", 0),
            getattr(TQSDwg, "ICPQUEBR_SEMQUEBRA", 0)
        )
    except Exception:
        pass


def meucmd(eag, tqsjan):
    """
    Entry point do plugin 'Furos' chamado pelo menu do TQS EAG.
    Abre janela cobrindo um ou mais furos e arma cada um separadamente com ferros reais.
    """
    try:
        dwg = tqsjan.dwg
        janela_idx = 1
        marcas_globais = {}

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

            # Arma cada furo individualmente com ferros nativos
            for xmin_f, ymin_f, xmax_f, ymax_f in furos:
                larg_f = xmax_f - xmin_f
                alt_f = ymax_f - ymin_f
                comp_h_int = int(round(larg_f + 2.0 * PASSAR))
                comp_v_int = int(round(alt_f + 2.0 * PASSAR))

                chave_h = (comp_h_int, BITOLA)
                if chave_h not in marcas_globais:
                    try:
                        f_m = dwg.globalrebar.FreeMark()
                        marcas_globais[chave_h] = f_m if f_m > 0 else (len(marcas_globais) + 1)
                    except Exception:
                        marcas_globais[chave_h] = len(marcas_globais) + 1
                marca_h = marcas_globais[chave_h]

                chave_v = (comp_v_int, BITOLA)
                if chave_v not in marcas_globais:
                    try:
                        f_m = dwg.globalrebar.FreeMark()
                        marcas_globais[chave_v] = f_m if f_m > 0 else (len(marcas_globais) + 1)
                    except Exception:
                        marcas_globais[chave_v] = len(marcas_globais) + 1
                marca_v = marcas_globais[chave_v]

                armar_furo_solto(dwg, xmin_f, ymin_f, xmax_f, ymax_f, marca_h, marca_v)

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
