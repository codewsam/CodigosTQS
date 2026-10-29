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
- Tratamento de Furos Próximos (distância <= 50 cm):
  - Unifica a armadura horizontal em ferros grandes e contínuos de ponta a ponta.
  - Insere exatamente 2 ferros verticais em cada espaço/nervo entre os furos.
  - Mantém 2 ferros verticais na extremidade esquerda e 2 na direita.
  - Notação atualizada proporcionalmente (ex: 3x2 P... para 2 furos geminados).
- Notação com chamadas limpas e organizadas ao lado dos ferros:
  - 1 chamada com seta para as barras horizontais (ao lado direito, além do fim do ferro).
  - 1 chamada com seta para as barras verticais (no topo, além da ponta do ferro).
- Cotagem de Transpasse (60 cm):
  - 1 cota de 60 na horizontal indicando a extensão do ferro além do furo.
  - 1 cota de 60 na vertical indicando a extensão do ferro além do furo.
  - Padrão TQS com ticks inclinados e linhas no Nível 221.
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
NIVEL_COTA = 221          # Nível TQS oficial para linhas e textos de cotagem
DIST_MAX_UNIR = 50.0      # Furos a até 50 cm são agrupados como um conjunto contínuo


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
        # 1. Agrupa os traços individuais para obter os contornos dos furos
        caixas_furos = _unir_caixas(segs, tol=10.0)
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
    - Barras horizontais contínuas em Ciano (2 topo + 2 base cobrindo toda a extensão).
    - Barras verticais em Ciano: 2 na borda esquerda, 2 na borda direita E exatamente
      2 barras verticais em cada espaço/nervo intermediário entre furos próximos.
    - Chamadas automáticas posicionadas ao lado dos ferros, sem colisões.
    - Cotas de 60 cm na horizontal e na vertical indicando o transpasse.
    """
    draw = dwg.draw
    larg_conjunto = xmax - xmin
    alt_conjunto = ymax - ymin

    comp_h = int(round(larg_conjunto + (2.0 * PASSAR)))
    comp_v = int(round(alt_conjunto + (2.0 * PASSAR)))

    # Coordenadas X para barras horizontais
    x_h_ini = xmin - PASSAR
    x_h_fim = xmax + PASSAR

    # Coordenadas Y para barras verticais
    y_v_ini = ymin - PASSAR
    y_v_fim = ymax + PASSAR

    # Linhas horizontais (Y) de contorno externo
    y_top_inner = ymax + COBRIMENTO
    y_top_outer = ymax + COBRIMENTO + ESPAC_BARRAS
    y_bot_inner = ymin - COBRIMENTO
    y_bot_outer = ymin - COBRIMENTO - ESPAC_BARRAS

    # Linhas verticais (X) de contorno externo
    x_dir_inner = xmax + COBRIMENTO
    x_dir_outer = xmax + COBRIMENTO + ESPAC_BARRAS
    x_esq_inner = xmin - COBRIMENTO
    x_esq_outer = xmin - COBRIMENTO - ESPAC_BARRAS

    # Identifica vãos intermediários em X (furos lado a lado)
    gaps_x = []
    gaps_y = []
    if subfuros and len(subfuros) > 1:
        # Gaps horizontais
        sub_x = sorted(subfuros, key=lambda f: f[0])
        for i in range(len(sub_x) - 1):
            x1_gap = sub_x[i][2]
            x2_gap = sub_x[i+1][0]
            if (x2_gap - x1_gap) >= 2.0:
                gaps_x.append((x1_gap + x2_gap) / 2.0)

        # Gaps verticais
        sub_y = sorted(subfuros, key=lambda f: f[1])
        for j in range(len(sub_y) - 1):
            y1_gap = sub_y[j][3]
            y2_gap = sub_y[j+1][1]
            if (y2_gap - y1_gap) >= 2.0:
                gaps_y.append((y1_gap + y2_gap) / 2.0)

    # -------------------------------------------------------------------------
    # 1. FERRO HORIZONTAL (SMARTREBAR)
    # -------------------------------------------------------------------------
    num_pares_h = 2 + len(gaps_y)
    sr_h = TQSDwg.SmartRebar(dwg)
    sr_h.type = getattr(TQSDwg, "ICPFRT", 1)  # Ferro reto
    sr_h.multiplier = num_pares_h             # 2 faces (topo e base) + intermediárias
    sr_h.quantity = 2                         # 2 barras por par
    sr_h.diameter = BITOLA
    sr_h.straightBarMainLength = float(comp_h)
    sr_h.mark = int(marca_h)
    sr_h.straightBarZone = getattr(TQSDwg, "ICPPOS", 0)
    sr_h.leaderLine = 1
    sr_h.leaderLineDistance = 0.1

    # Insere as barras horizontais externas em CIANO (cor 4) no Nível 220
    sr_h.RebarLine(x_h_ini, y_top_outer, 0.0, 1.0, 1, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
    sr_h.RebarLine(x_h_ini, y_top_inner, 0.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
    sr_h.RebarLine(x_h_ini, y_bot_inner, 0.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
    sr_h.RebarLine(x_h_ini, y_bot_outer, 0.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)

    # Se houver furos empilhados verticalmente, insere 2 ferros horizontais no vão intermediário
    for ym in gaps_y:
        y_mid1 = ym + (ESPAC_BARRAS / 2.0)
        y_mid2 = ym - (ESPAC_BARRAS / 2.0)
        sr_h.RebarLine(x_h_ini, y_mid1, 0.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
        sr_h.RebarLine(x_h_ini, y_mid2, 0.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)

    # Formatação do texto: '2x2 N... Phi 10 C=...'
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
    # 2. FERRO VERTICAL (SMARTREBAR)
    # -------------------------------------------------------------------------
    num_pares_v = 2 + len(gaps_x)
    sr_v = TQSDwg.SmartRebar(dwg)
    sr_v.type = getattr(TQSDwg, "ICPFRT", 1)  # Ferro reto
    sr_v.multiplier = num_pares_v             # Borda esq + borda dir + vão(s) intermediário(s)
    sr_v.quantity = 2                         # 2 barras por par
    sr_v.diameter = BITOLA
    sr_v.straightBarMainLength = float(comp_v)
    sr_v.mark = int(marca_v)
    sr_v.straightBarZone = getattr(TQSDwg, "ICPPOS", 0)
    sr_v.leaderLine = 1
    sr_v.leaderLineDistance = 0.1

    # Insere as barras verticais externas
    sr_v.RebarLine(x_dir_outer, y_v_ini, 90.0, 1.0, 1, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
    sr_v.RebarLine(x_dir_inner, y_v_ini, 90.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
    sr_v.RebarLine(x_esq_inner, y_v_ini, 90.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
    sr_v.RebarLine(x_esq_outer, y_v_ini, 90.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)

    # INSERE EXATAMENTE 2 FERROS NO ESPAÇO ENTRE OS FUROS PRÓXIMOS
    for xm in gaps_x:
        x_mid1 = xm - (ESPAC_BARRAS / 2.0)
        x_mid2 = xm + (ESPAC_BARRAS / 2.0)
        sr_v.RebarLine(x_mid1, y_v_ini, 90.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)
        sr_v.RebarLine(x_mid2, y_v_ini, 90.0, 1.0, 0, 0, 0, 0, NIVEL_ARMADURA, -1, COR_ARMADURA)

    # Formatação do texto: '(num)x2 N... Phi 10 C=...'
    sr_v.RebarTextDisplaySelection(
        1, 1, 1, 0, 1,
        getattr(TQSDwg, "ICPCENTR_CENTRAD", 0),
        getattr(TQSDwg, "ICPQUEBR_SEMQUEBRA", 0)
    )
    x_txt_v = x_dir_outer + 30.0
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
    # 3. COTAS DE TRANSPASSE (60 cm)
    # -------------------------------------------------------------------------
    txt_cota = f"{int(PASSAR)}"

    # 3.1 Cota Horizontal (à esquerda, abaixo das barras horizontais inferiores)
    y_cota_h = y_bot_outer - 15.0
    desenhar_cota_horizontal(
        draw,
        x_h_ini, xmin,
        y_cota_h,
        witness_y_start=y_bot_outer,
        valor_txt=txt_cota,
        h=4.2
    )

    # 3.2 Cota Vertical (na base, à esquerda das barras verticais)
    x_cota_v = x_esq_outer - 15.0
    desenhar_cota_vertical(
        draw,
        y_v_ini, ymin,
        x_cota_v,
        witness_x_start=x_esq_outer,
        valor_txt=txt_cota,
        h=4.2
    )


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

            # Arma cada grupo de furos com ferros nativos
            for g in grupos:
                xmin_f, ymin_f, xmax_f, ymax_f = g['box']
                subfuros_g = g['subfuros']

                larg_f = xmax_f - xmin_f
                alt_f = ymax_f - ymin_f
                comp_h_int = int(round(larg_f + 2.0 * PASSAR))
                comp_v_int = int(round(alt_f + 2.0 * PASSAR))

                chave_h = (comp_h_int, BITOLA)
                marca_h = _obter_marca(chave_h)

                # Se a marca vertical for nova e coincidir com a horizontal, assegura numeração sequencial distinta
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
