# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - FORMAS (TQS EAG)
================================================================================
Modulo dedicado a ferramentas e automatizacoes de formas estruturais.
Funcoes:
  1. Linha de Corte (criacao automatica de linha Nivel 205, Cor 2, Estilo -1)
  2. Inversoes (identifica bolinhas pelo Nivel: Nivel 11 = Viga, Nivel 13 = Laje,
     agrupando bolinhas da mesma viga e organizando textos sem sobreposicao)
================================================================================
"""
import math
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag


def encontrar_pares_de_corte(dwg):
    """
    Varre o desenho procurando blocos de corte ($CORTEA, LINCOR, etc.)
    e agrupa em pares colineares (cortes verticais e horizontais).
    """
    pontos_corte = []
    dwg.iterator.Begin()
    while True:
        tipo = dwg.iterator.Next()
        if tipo == TQSDwg.DWGTYPE_EOF:
            break
        if tipo == TQSDwg.DWGTYPE_BLOCK:
            nome_bloco = dwg.iterator.blockName.upper()
            if "CORTE" in nome_bloco or "LINCOR" in nome_bloco:
                pontos_corte.append({
                    "x": dwg.iterator.xc,
                    "y": dwg.iterator.yc,
                    "ang": dwg.iterator.insertAngle,
                    "bloco": dwg.iterator.blockName
                })

    pares = []
    usados = set()
    n = len(pontos_corte)

    # 1. Cortes Verticais (mesmo X aproximado, delta Y significativo)
    for i in range(n):
        if i in usados:
            continue
        for j in range(i + 1, n):
            if j in usados:
                continue
            p1 = pontos_corte[i]
            p2 = pontos_corte[j]
            if abs(p1["x"] - p2["x"]) <= 2.0 and abs(p1["y"] - p2["y"]) >= 10.0:
                pares.append(((p1["x"], p1["y"]), (p2["x"], p2["y"]), "vertical"))
                usados.add(i)
                usados.add(j)
                break

    # 2. Cortes Horizontais (mesmo Y aproximado, delta X significativo)
    for i in range(n):
        if i in usados:
            continue
        for j in range(i + 1, n):
            if j in usados:
                continue
            p1 = pontos_corte[i]
            p2 = pontos_corte[j]
            if abs(p1["y"] - p2["y"]) <= 2.0 and abs(p1["x"] - p2["x"]) >= 10.0:
                pares.append(((p1["x"], p1["y"]), (p2["x"], p2["y"]), "horizontal"))
                usados.add(i)
                usados.add(j)
                break

    return pares


def cmd_linha_de_corte(eag, tqsjan):
    """
    Cria automaticamente as linhas de corte conectando as marcas existentes ($CORTEA).
    Propriedades definidas: Nivel 205, Cor 2 (Amarelo), Estilo de linha -1 (Por nivel).
    Se nao encontrar marcadores automaticos, oferece selecao manual por 2 pontos.
    """
    try:
        dwg = tqsjan.dwg
        pares = encontrar_pares_de_corte(dwg)

        linhas_criadas = 0

        if pares:
            # Configura propriedades da linha de corte: Nivel 205, Cor 2 (Amarelo), Estilo -1 (Por nivel)
            dwg.draw.level = 205
            dwg.draw.color = 2
            dwg.draw.style = -1

            for pt1, pt2, direcao in pares:
                dwg.draw.Line(pt1[0], pt1[1], pt2[0], pt2[1])
                linhas_criadas += 1

            tqsjan.Regen()
            eag.msg.Print("G3 Plugins: %d linha(s) de corte gerada(s) automaticamente!" % linhas_criadas)
            eag.msg.PrintStatus("%d linha(s) de corte gerada(s) com sucesso!" % linhas_criadas)
        else:
            # Fallback interativo: se a forma nao tiver o bloco $CORTEA padrao
            eag.msg.Print("Nenhum marcador de corte automatico encontrado.")
            eag.msg.Print("Modo manual: selecione os dois pontos da linha de corte.")
            
            icod, x1, y1 = eag.locate.GetPoint(tqsjan, "Linha de Corte: Selecione o 1o ponto (ou <Esc> para sair)")
            if icod != 1:
                return
            
            icod2, x2, y2 = eag.locate.GetSecondPoint(
                tqsjan, x1, y1, TQSEag.EAG_RUBLINEAR, TQSEag.EAG_RUBRET_NAOPREEN,
                "Linha de Corte: Selecione o 2o ponto"
            )
            if icod2 != 1:
                return

            dwg.draw.level = 205
            dwg.draw.color = 2
            dwg.draw.style = -1
            dwg.draw.Line(x1, y1, x2, y2)
            tqsjan.Regen()
            eag.msg.Print("G3 Plugins: Linha de corte manual desenhada com sucesso!")

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass


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
    comp = len(texto_str) * h * 0.95
    a = _normalizar_angulo(ang)
    if a == 90.0:
        # Quando rotacionado a 90 graus, o texto cresce em +Y e tem altura para a esquerda (-X)
        return (xc - h * 1.1, yc, xc + h * 0.2, yc + comp)
    else:
        return (xc, yc - h * 0.2, xc + comp, yc + h * 1.1)


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


def coletar_contexto_inversoes(dwg):
    """
    Varre o DWG coletando:
      - Bolinhas de viga (Nivel 11 - Dimensoes de vigas) e de laje (Nivel 13 - Dimensoes de lajes)
      - Titulos de vigas (Nivel 8, 'V...') e secoes de vigas (Nivel 11, 'b/h')
      - Titulos de lajes (Nivel 10, 'L...') e espessuras de lajes (Nivel 13, 'h=...')
      - Obstaculos (outros textos, pilares, linhas de corte e linhas de concreto)
    """
    circulos = []
    textos_numericos = []
    vigas = []
    lajes = []
    obstaculos = []
    linhas_vert_concreto = []
    linhas_horiz_concreto = []

    viga_atual = None
    laje_atual = None

    # Pares de corte tambem contam como obstaculos (faixas de linha de corte)
    pares_corte = encontrar_pares_de_corte(dwg)
    for pt1, pt2, direcao in pares_corte:
        xmin = min(pt1[0], pt2[0]) - 2.0
        xmax = max(pt1[0], pt2[0]) + 2.0
        ymin = min(pt1[1], pt2[1]) - 2.0
        ymax = max(pt1[1], pt2[1]) + 2.0
        obstaculos.append({"tipo": "corte", "direcao": direcao, "bbox": (xmin, ymin, xmax, ymax)})

    dwg.iterator.Begin()
    while True:
        tipo = dwg.iterator.Next()
        if tipo == TQSDwg.DWGTYPE_EOF:
            break
        if dwg.iterator.inBlock != 0:
            continue

        nivel = dwg.iterator.level
        addr = dwg.iterator.GetElementReadPosition()

        # Linhas/Polylines de concreto (Nivel 1 e 2) e pilares (Nivel 4)
        if tipo == TQSDwg.DWGTYPE_POLYLINE and nivel in (1, 2, 4):
            pts = [dwg.iterator.GetPolylinePt(i) for i in range(dwg.iterator.xySize)]
            if nivel == 4 and pts:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                obstaculos.append({"tipo": "pilar", "bbox": (min(xs), min(ys), max(xs), max(ys))})
            elif nivel in (1, 2) and len(pts) >= 2:
                for k in range(len(pts) - 1):
                    x1, y1 = pts[k]
                    x2, y2 = pts[k + 1]
                    if abs(x1 - x2) < 1.0 and abs(y1 - y2) > 20.0:
                        linhas_vert_concreto.append((0.5 * (x1 + x2), min(y1, y2), max(y1, y2)))
                    elif abs(y1 - y2) < 1.0 and abs(x1 - x2) > 20.0:
                        linhas_horiz_concreto.append((0.5 * (y1 + y2), min(x1, x2), max(x1, x2)))

        elif tipo == TQSDwg.DWGTYPE_LINE and nivel in (200, 205):
            xmin = min(dwg.iterator.x1, dwg.iterator.x2) - 2.0
            xmax = max(dwg.iterator.x1, dwg.iterator.x2) + 2.0
            ymin = min(dwg.iterator.y1, dwg.iterator.y2) - 2.0
            ymax = max(dwg.iterator.y1, dwg.iterator.y2) + 2.0
            obstaculos.append({"tipo": "corte_linha", "bbox": (xmin, ymin, xmax, ymax)})

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
            ang = _normalizar_angulo(dwg.iterator.textAngle)

            # 1. Titulo de Viga (Nivel 8, ex: 'V101')
            if nivel == 8 and txt_raw.upper().startswith("V"):
                viga_atual = {
                    "nome": txt_raw,
                    "addr_titulo": addr,
                    "xc": xc, "yc": yc,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "h": h, "ang": ang,
                    "secao": None,
                }
                laje_atual = None
                vigas.append(viga_atual)
                obstaculos.append({
                    "tipo": "viga_titulo",
                    "addr": addr,
                    "bbox": _bbox_texto(xc, yc, h, ang, txt_raw)
                })
                continue

            # 2. Secao de Viga (Nivel 11, ex: '14/70')
            if nivel == 11 and "/" in txt_raw:
                sec_obj = {
                    "texto": txt_raw,
                    "addr": addr,
                    "xc": xc, "yc": yc,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "h": h, "ang": ang,
                }
                if viga_atual is not None and viga_atual["secao"] is None:
                    viga_atual["secao"] = sec_obj
                obstaculos.append({
                    "tipo": "viga_secao",
                    "addr": addr,
                    "bbox": _bbox_texto(xc, yc, h, ang, txt_raw)
                })
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
                    "level": nivel,
                })
            else:
                # Outros textos (ex: P1, 25/25, etc.) sao obstaculos
                obstaculos.append({
                    "tipo": "texto",
                    "addr": addr,
                    "bbox": _bbox_texto(xc, yc, h, ang, txt_raw)
                })

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

            bolinhas.append({
                "addr_circulo": c["addr"],
                "addr_texto": tx_obj["addr"],
                "val": tx_obj["val"],
                "xc": tx_obj["xc"],
                "yc": tx_obj["yc"],
                "h": tx_obj["h"],
                "ang": tx_obj["ang"],
                "level": nivel_efetivo,  # 11 = Viga, 13 = Laje
            })

    return {
        "bolinhas": bolinhas,
        "vigas": vigas,
        "lajes": lajes,
        "obstaculos": obstaculos,
        "linhas_vert_concreto": linhas_vert_concreto,
        "linhas_horiz_concreto": linhas_horiz_concreto,
    }


def _agrupar_bolinhas_vigas(bolinhas_viga, vigas):
    """
    Agrupa bolinhas de Nivel 11 que pertencem geometricamente ao mesmo eixo de viga
    (mesma orientacao e mesma faixa X ou Y, com mesmo valor) para escrever apenas 1 vez por viga.
    """
    grupos = []
    usadas = set()

    for i, b1 in enumerate(bolinhas_viga):
        if i in usadas:
            continue
        grupo = [b1]
        usadas.add(i)

        for j in range(i + 1, len(bolinhas_viga)):
            if j in usadas:
                continue
            b2 = bolinhas_viga[j]

            mesmo_eixo_horiz = (
                b1["ang"] == 0.0 and b2["ang"] == 0.0 and
                abs(b1["yc"] - b2["yc"]) <= 40.0 and
                abs(b1["val"] - b2["val"]) < 1e-3
            )
            mesmo_eixo_vert = (
                b1["ang"] == 90.0 and b2["ang"] == 90.0 and
                abs(b1["xc"] - b2["xc"]) <= 40.0 and
                abs(b1["val"] - b2["val"]) < 1e-3
            )

            if mesmo_eixo_horiz or mesmo_eixo_vert:
                grupo.append(b2)
                usadas.add(j)

        # Associa ao cabecalho da viga (V... + b/h) se estiver na mesma faixa geometrica
        viga_assoc = None
        for v in vigas:
            if v["ang"] == grupo[0]["ang"]:
                if v["ang"] == 0.0 and any(abs(v["yc"] - b["yc"]) <= 40.0 for b in grupo):
                    viga_assoc = v
                    break
                elif v["ang"] == 90.0 and any(abs(v["xc"] - b["xc"]) <= 40.0 for b in grupo):
                    viga_assoc = v
                    break

        grupos.append((viga_assoc, grupo))

    return grupos


def cmd_inversoes(eag, tqsjan):
    """
    Identifica as bolinhas estritamente pelo seu NIVEL:
      - Nivel 11 (Dimensoes de vigas): 'VIGA INVERTIDA xCM' (1 unico texto por viga)
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
        # Identificacao estritamente pelo Nivel do TQS:
        # Nivel 11 = Dimensoes de vigas | Nivel 13 = Dimensoes de lajes
        bolinhas_viga = [b for b in bolinhas if b["level"] == 11]
        bolinhas_laje = [b for b in bolinhas if b["level"] == 13]

        textos_criados = 0
        bolinhas_apagadas = 0

        # ---------------------------------------------------------------------
        # 1. PROCESSA VIGAS (NIVEL 11) - 1 UNICO TEXTO POR VIGA
        # ---------------------------------------------------------------------
        grupos_vigas = _agrupar_bolinhas_vigas(bolinhas_viga, ctx["vigas"])

        for viga, grupo in grupos_vigas:
            # Apaga TODAS as bolinhas de Nivel 11 dessa mesma viga
            for b in grupo:
                dwg.edit.Erase(b["addr_circulo"])
                dwg.edit.Erase(b["addr_texto"])
                bolinhas_apagadas += 1

            b_ref = grupo[0]
            val_str = _formatar_valor_cm(b_ref["val"])
            novo_texto = "VIGA INVERTIDA %sCM" % val_str
            h_txt = b_ref["h"]
            ang_txt = b_ref["ang"]
            nivel_txt = 11

            x_dest = b_ref["xc"]
            y_dest = b_ref["yc"]

            # Se temos o titulo e a secao da viga (ex: V101 e 14/70), garante alinhamento limpo
            if viga is not None and viga["secao"] is not None:
                sec = viga["secao"]
                if ang_txt == 0.0:
                    larg_sec = abs(sec["x2"] - sec["x1"])
                    # Se a secao (ex: 14/70) estava desalinhada em Y do nome da viga (ex: V101),
                    # alinha a secao na mesma linha do nome da viga para nao bater em pilares
                    if abs(sec["yc"] - viga["yc"]) > 5.0:
                        novo_x_sec = viga["x2"] + 15.0
                        novo_y_sec = viga["yc"]
                        dx_sec = novo_x_sec - sec["xc"]
                        dy_sec = novo_y_sec - sec["yc"]
                        dwg.edit.Move(sec["addr"], dx_sec, dy_sec)
                        sec["xc"] = novo_x_sec
                        sec["yc"] = novo_y_sec
                        sec["x1"] += dx_sec
                        sec["x2"] += dx_sec
                        sec["y1"] += dy_sec
                        sec["y2"] += dy_sec
                        x_dest = novo_x_sec + larg_sec + 15.0
                        y_dest = novo_y_sec
                    else:
                        x_dest = sec["x2"] + 12.0
                        y_dest = sec["yc"]
                elif ang_txt == 90.0:
                    larg_sec = abs(sec["y2"] - sec["y1"])
                    if abs(sec["xc"] - viga["xc"]) > 5.0:
                        novo_x_sec = viga["xc"]
                        novo_y_sec = viga["y2"] + 15.0
                        dx_sec = novo_x_sec - sec["xc"]
                        dy_sec = novo_y_sec - sec["yc"]
                        dwg.edit.Move(sec["addr"], dx_sec, dy_sec)
                        sec["xc"] = novo_x_sec
                        sec["yc"] = novo_y_sec
                        sec["x1"] += dx_sec
                        sec["x2"] += dx_sec
                        sec["y1"] += dy_sec
                        sec["y2"] += dy_sec
                        x_dest = novo_x_sec
                        y_dest = novo_y_sec + larg_sec + 15.0
                    else:
                        x_dest = sec["xc"]
                        y_dest = sec["y2"] + 12.0

            dwg.draw.level = nivel_txt
            dwg.draw.color = -1
            dwg.draw.style = 0
            dwg.draw.Text(x_dest, y_dest, h_txt, ang_txt, novo_texto)
            textos_criados += 1

            # Registra o novo texto de viga invertida como obstaculo para nao sobrepor com lajes
            obstaculos.append({
                "tipo": "viga_invertida",
                "bbox": _bbox_texto(x_dest, y_dest, h_txt, ang_txt, novo_texto)
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
                if abs(lj["xc"] - b["xc"]) <= 35.0 and 0.0 <= (lj["yc"] - b["yc"]) <= 85.0:
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
                            if _boxes_colidem(bx, obs["bbox"], margem=5.0):
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


def meucmd(eag, tqsjan):
    """Entry point padrao de Formas (chama Linha de Corte)."""
    cmd_linha_de_corte(eag, tqsjan)
