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
  3. Criar Cotas (cotagem automatica completa de formas em camadas usando cotas_helper)
  4. Corrigir Vazio e Indicador de Laje (substitui linhas em X de vazios do Nivel 241
     para o Nivel 210 e apaga setas/indicadores de direcao de laje no Nivel 240)
================================================================================
"""
import math
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag
import cotas_helper
import anti_sobreposicao


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
    comp = len(texto_str) * h * 0.85
    a = _normalizar_angulo(ang)
    if a == 90.0:
        # Quando rotacionado a 90 graus, o texto cresce em +Y e tem altura para a esquerda (-X)
        return (xc - h * 1.15, yc, xc + h * 0.25, yc + comp)
    else:
        return (xc, yc - h * 0.25, xc + comp, yc + h * 1.15)


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
    lines_concreto_exatas = []
    secoes_viga_coletadas = []

    viga_atual = None
    laje_atual = None

    # Linhas de corte (pares de corte) sao referencias visuais de fundo e nao obstaculos fisicos de texto
    pares_corte = encontrar_pares_de_corte(dwg)

    dwg.iterator.Begin()
    while True:
        tipo = dwg.iterator.Next()
        if tipo == TQSDwg.DWGTYPE_EOF:
            break
        if dwg.iterator.inBlock != 0:
            if tipo == TQSDwg.DWGTYPE_POLYLINE and dwg.iterator.level == 208:
                pts_c = [dwg.iterator.GetPolylinePt(i) for i in range(dwg.iterator.xySize)]
                if pts_c:
                    xs_c = [p[0] for p in pts_c]
                    ys_c = [p[1] for p in pts_c]
                    obstaculos.append({"tipo": "cubeta", "bbox": (min(xs_c), min(ys_c), max(xs_c), max(ys_c))})
            continue

        nivel = dwg.iterator.level
        addr = dwg.iterator.GetElementReadPosition()

        # Linhas/Polylines de concreto (Nivel 1, 2, 201) e pilares (Nivel 2, 3, 4, 5)
        if tipo == TQSDwg.DWGTYPE_POLYLINE and nivel in (1, 2, 3, 4, 5, 201):
            pts = [dwg.iterator.GetPolylinePt(i) for i in range(dwg.iterator.xySize)]
            if pts:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                dx_p = max(xs) - min(xs)
                dy_p = max(ys) - min(ys)
                if nivel in (2, 3, 4, 5) and 5.0 <= dx_p <= 450.0 and 5.0 <= dy_p <= 450.0 and len(pts) >= 4:
                    obstaculos.append({"tipo": "pilar", "bbox": (min(xs), min(ys), max(xs), max(ys))})
                elif nivel in (1, 2, 201) and len(pts) >= 2:
                    for k in range(len(pts) - 1):
                        x1, y1 = pts[k]
                        x2, y2 = pts[k + 1]
                        lines_concreto_exatas.append((x1, y1, x2, y2, nivel))
                        if abs(x1 - x2) <= 8.0 and abs(y1 - y2) > 10.0:
                            linhas_vert_concreto.append((0.5 * (x1 + x2), min(y1, y2), max(y1, y2)))
                        elif abs(y1 - y2) <= 8.0 and abs(x1 - x2) > 10.0:
                            linhas_horiz_concreto.append((0.5 * (y1 + y2), min(x1, x2), max(x1, x2)))

        elif tipo == TQSDwg.DWGTYPE_LINE and nivel in (1, 2, 201):
            x1, y1, x2, y2 = dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2
            lines_concreto_exatas.append((x1, y1, x2, y2, nivel))
            if abs(x1 - x2) <= 8.0 and abs(y1 - y2) > 10.0:
                linhas_vert_concreto.append((0.5 * (x1 + x2), min(y1, y2), max(y1, y2)))
            elif abs(y1 - y2) <= 8.0 and abs(x1 - x2) > 10.0:
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
                bx = _bbox_texto(xc, yc, h, ang, txt_raw)
                viga_atual = {
                    "nome": txt_raw,
                    "addr_titulo": addr,
                    "xc": xc, "yc": yc,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "h": h, "ang": ang,
                    "bbox": bx,
                    "secao": None,
                }
                laje_atual = None
                vigas.append(viga_atual)
                obstaculos.append({
                    "tipo": "viga_titulo",
                    "addr": addr,
                    "bbox": bx
                })
                continue

            # 2. Secao de Viga (Nivel 11, ex: '14/70')
            if nivel == 11 and "/" in txt_raw:
                bx = _bbox_texto(xc, yc, h, ang, txt_raw)
                sec_obj = {
                    "texto": txt_raw,
                    "addr": addr,
                    "xc": xc, "yc": yc,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "h": h, "ang": ang,
                    "bbox": bx,
                }
                secoes_viga_coletadas.append(sec_obj)
                obstaculos.append({
                    "tipo": "viga_secao",
                    "addr": addr,
                    "bbox": bx
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
                # Outros textos (ex: P1, 25/25, etc.) sao obstaculos (pilares marcados com tipo='pilar')
                is_pilar = nivel in (9, 12) or (txt_raw.strip().upper().startswith("P") and nivel in (8, 9, 10, 11, 12))
                obstaculos.append({
                    "tipo": "pilar" if is_pilar else "texto",
                    "nivel": nivel,
                    "texto": txt_raw,
                    "addr": addr,
                    "bbox": anti_sobreposicao._bbox_texto_exato(x1, y1, x2, y2, h)
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

    # Pareamento geometrico de secoes de viga com titulos de viga
    for v in vigas:
        if v["secao"] is None:
            best_sec = None
            min_d = float("inf")
            for s in secoes_viga_coletadas:
                if s["ang"] == v["ang"]:
                    if v["ang"] == 0.0:
                        if abs(v["y1"] - s["y1"]) <= 45.0:
                            d = math.hypot(v["xc"] - s["xc"], v["yc"] - s["yc"])
                            if d < 180.0 and d < min_d:
                                min_d = d
                                best_sec = s
                    else:
                        if abs(v["x1"] - s["x1"]) <= 45.0:
                            d = math.hypot(v["xc"] - s["xc"], v["yc"] - s["yc"])
                            if d < 180.0 and d < min_d:
                                min_d = d
                                best_sec = s
            if best_sec is not None:
                v["secao"] = best_sec

    return {
        "bolinhas": bolinhas,
        "vigas": vigas,
        "secoes": secoes_viga_coletadas,
        "lajes": lajes,
        "obstaculos": obstaculos,
        "linhas_vert_concreto": linhas_vert_concreto,
        "linhas_horiz_concreto": linhas_horiz_concreto,
        "lines_concreto_exatas": lines_concreto_exatas,
    }


def _agrupar_bolinhas_vigas(bolinhas_viga, vigas, secoes, lines_concreto=None):
    """
    Agrupa bolinhas de Nivel 11 por viga usando o mapeamento da viga branca continua.
    Se uma viga inteira tiver o mesmo valor de inversao (ex: V501-A ou V513-A com 40cm em
    todos os vaos), gera apenas 1 unica indicacao na viga, apagando todas as bolinhas repetidas.
    """
    vigas_geom = anti_sobreposicao.mapear_vigas_continuas(vigas, lines_concreto or [])
    bolinhas_por_viga = {}
    for vg in vigas_geom:
        bolinhas_por_viga[vg["nome"]] = {"viga": vg["viga"], "vg": vg, "bolinhas": []}

    bolinhas_avulsas = []
    for b in bolinhas_viga:
        vg = anti_sobreposicao.associar_elemento_a_viga(b["xc"], b["yc"], b["ang"], vigas_geom)
        if vg is not None:
            bolinhas_por_viga[vg["nome"]]["bolinhas"].append(b)
        else:
            bolinhas_avulsas.append(b)

    resultado = []
    for v_nome, data in bolinhas_por_viga.items():
        v = data["viga"]
        vg = data["vg"]
        blist = data["bolinhas"]
        if not blist:
            continue

        por_valor = {}
        for b in blist:
            v_key = round(b["val"], 1)
            por_valor.setdefault(v_key, []).append(b)

        for val, grp in por_valor.items():
            b_ref = grp[0]
            ang = v["ang"]
            cands_sec = [
                s for s in secoes
                if anti_sobreposicao.associar_elemento_a_viga(s["xc"], s["yc"], s["ang"], vigas_geom) is vg
            ]
            sec_prox = None
            min_ds = float("inf")
            for s in cands_sec:
                d = math.hypot(s["xc"] - b_ref["xc"], s["yc"] - b_ref["yc"])
                if d < min_ds:
                    min_ds = d
                    sec_prox = s

            sec_usar = v.get("secao") if (len(por_valor) == 1 and v.get("secao") in cands_sec) else (sec_prox or v.get("secao"))
            resultado.append((v, vg, sec_usar, grp, val))

    for b in bolinhas_avulsas:
        resultado.append((None, None, None, [b], b["val"]))

    return resultado


def cmd_inversoes(eag, tqsjan):
    """
    Identifica as bolinhas estritamente pelo seu NIVEL:
      - Nivel 11 (Dimensoes de vigas): 'VIGA INVERTIDA xCM' (1 unico texto por valor na viga branca)
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
        bolinhas_viga = [b for b in bolinhas if b["level"] == 11]
        bolinhas_laje = [b for b in bolinhas if b["level"] == 13]

        lines_concreto_map = []
        for y, x1, x2 in ctx.get("linhas_horiz_concreto", []):
            lines_concreto_map.append((x1, y, x2, y, 1))
        for x, y1, y2 in ctx.get("linhas_vert_concreto", []):
            lines_concreto_map.append((x, y1, x, y2, 1))
        lines_concreto = list(ctx.get("lines_concreto_exatas", [])) or lines_concreto_map

        textos_criados = 0
        bolinhas_apagadas = 0

        # ---------------------------------------------------------------------
        # 1. PROCESSA VIGAS (NIVEL 11) - 1 UNICO TEXTO POR VIGA (SEM REPETIR)
        # ---------------------------------------------------------------------
        grupos_vigas = _agrupar_bolinhas_vigas(bolinhas_viga, ctx["vigas"], ctx.get("secoes", []), lines_concreto_map)

        for viga, vg, sec, grupo, val in grupos_vigas:
            # Apaga TODAS as bolinhas desse grupo na viga
            for b in grupo:
                dwg.edit.Erase(b["addr_circulo"])
                dwg.edit.Erase(b["addr_texto"])
                bolinhas_apagadas += 1

            b_ref = grupo[0]
            val_str = _formatar_valor_cm(val)
            novo_texto = "VIGA INVERTIDA %sCM" % val_str
            h_txt = b_ref["h"]
            ang_viga = viga["ang"] if viga else b_ref["ang"]
            nivel_txt = 11
            comp = len(novo_texto) * h_txt * 1.0

            # Ponto alvo no concreto da viga (centro do segmento de inversao)
            xa_alvo = b_ref["xc"]
            ya_alvo = b_ref["yc"]
            if vg is not None:
                if ang_viga == 0.0:
                    ya_alvo = 0.5 * (vg["t_min"] + vg["t_max"])
                else:
                    xa_alvo = 0.5 * (vg["t_min"] + vg["t_max"])

            obst_boxes = [obs["bbox"] for obs in obstaculos]

            # 1. Tenta posicionamento direto na face da viga NO TRECHO LOCAL (sem pular de vao!)
            colocou_direto = False
            x_dest, y_dest, ang_dest = None, None, ang_viga

            sec_box = (sec.get("bbox") or sec.get("box")) if sec else None
            candidatos_diretos = []
            if sec is not None and sec_box is not None:
                if ang_viga == 0.0:
                    candidatos_diretos.append((sec_box[2] + 8.0, sec["y1"], 0.0))
                    candidatos_diretos.append((sec_box[0] - comp - 8.0, sec["y1"], 0.0))
                else:
                    candidatos_diretos.append((sec["x1"], sec_box[3] + 8.0, 90.0))
                    candidatos_diretos.append((sec["x1"], sec_box[1] - comp - 8.0, 90.0))

            if vg is not None:
                passos = [0.0] + [d for step in (15.0, 30.0, 50.0, 75.0, 100.0, 130.0, 160.0, 200.0) for d in (step, -step)]
                if ang_viga == 0.0:
                    for cy in (vg["t_max"] + 0.25 * h_txt + 3.0, vg["t_min"] - 1.15 * h_txt - 3.0):
                        for d_local in passos:
                            cx = xa_alvo - 0.5 * comp + d_local
                            if cx >= vg["l_min"] - 40.0 and cx + comp <= vg["l_max"] + 40.0:
                                candidatos_diretos.append((cx, cy, 0.0))
                else:
                    for cx in (vg["t_min"] - 0.25 * h_txt - 3.0, vg["t_max"] + 1.15 * h_txt + 3.0):
                        for d_local in passos:
                            cy = ya_alvo - 0.5 * comp + d_local
                            if cy >= vg["l_min"] - 40.0 and cy + comp <= vg["l_max"] + 40.0:
                                candidatos_diretos.append((cx, cy, 90.0))

            for cd_x, cd_y, cd_ang in candidatos_diretos:
                bx = anti_sobreposicao._bbox_texto(cd_x, cd_y, h_txt, cd_ang, novo_texto)
                if any(_boxes_colidem(bx, ob, margem=0.5) for ob in obst_boxes):
                    continue
                if anti_sobreposicao._box_colide_com_concreto_alheio(bx, vg, lines_concreto, margem=1.0):
                    continue
                x_dest, y_dest, ang_dest = cd_x, cd_y, cd_ang
                colocou_direto = True
                break

            # Se todos colidiram, mas junto a secao na face da viga nao corta concreto e so toca pilar
            # (que sera reposicionado pelo botao Pilar/Organizar), mantem direto na viga sem seta!
            if not colocou_direto and sec is not None and sec_box is not None:
                for d_sec in (8.0, 20.0, 35.0, 50.0, 65.0, 80.0):
                    cand_sec = (sec_box[2] + d_sec, sec["y1"], 0.0) if ang_viga == 0.0 else (sec["x1"], sec_box[3] + d_sec, 90.0)
                    bx_sec = anti_sobreposicao._bbox_texto(cand_sec[0], cand_sec[1], h_txt, cand_sec[2], novo_texto)
                    if not anti_sobreposicao._box_colide_com_concreto_alheio(bx_sec, vg, lines_concreto, margem=1.0):
                        col_fixos = any(
                            _boxes_colidem(bx_sec, ob["bbox"], margem=0.5)
                            for ob in obstaculos
                            if ob.get("tipo") != "pilar" and ob.get("nivel") not in (9, 12)
                        )
                        if not col_fixos:
                            x_dest, y_dest, ang_dest = cand_sec[0], cand_sec[1], cand_sec[2]
                            colocou_direto = True
                            break

            precisa_seta = False
            # 2. Se nao coube direto no trecho local, POSICIONA COM SETA DE CHAMADA (validando linha da seta!)
            if not colocou_direto:
                candidatos_seta = []
                raios_seta = (12.0, 20.0, 30.0, 42.0, 55.0, 75.0, 95.0, 120.0, 150.0)
                if ang_viga == 90.0:
                    for r in raios_seta:
                        for dy in (0.0, 15.0, -15.0, 30.0, -30.0, 50.0, -50.0, 80.0, -80.0, 110.0, -110.0):
                            candidatos_seta.append((xa_alvo + r + h_txt, ya_alvo - 0.5 * comp + dy, 90.0))
                            candidatos_seta.append((xa_alvo - r, ya_alvo - 0.5 * comp + dy, 90.0))
                        for dx in (0.0, 15.0, -15.0, 30.0, -30.0, 50.0, -50.0):
                            candidatos_seta.append((xa_alvo + dx, ya_alvo + r, 90.0))
                            candidatos_seta.append((xa_alvo + dx, ya_alvo - r - comp, 90.0))

                for r in raios_seta:
                    # Horizontal (ang = 0)
                    for dy in (0.0, 12.0, -12.0, 24.0, -24.0, 40.0, -40.0):
                        candidatos_seta.append((xa_alvo + r, ya_alvo + dy - 0.5 * h_txt, 0.0))
                        candidatos_seta.append((xa_alvo - r - comp, ya_alvo + dy - 0.5 * h_txt, 0.0))
                    for dx in (0.0, 15.0, -15.0, 30.0, -30.0, 50.0, -50.0):
                        candidatos_seta.append((xa_alvo - 0.5 * comp + dx, ya_alvo + r, 0.0))
                        candidatos_seta.append((xa_alvo - 0.5 * comp + dx, ya_alvo - r - h_txt, 0.0))

                for cs_x, cs_y, cs_ang in candidatos_seta:
                    bx = anti_sobreposicao._bbox_texto(cs_x, cs_y, h_txt, cs_ang, novo_texto)
                    if any(_boxes_colidem(bx, ob, margem=2.0) for ob in obst_boxes):
                        continue
                    corta_concreto = False
                    for lx1, ly1, lx2, ly2, _ in lines_concreto:
                        if anti_sobreposicao._segmento_colide_box(lx1, ly1, lx2, ly2, bx, margem=1.0):
                            corta_concreto = True
                            break
                    if corta_concreto:
                        continue

                    # Valida linha da seta (sem sublinhado, apontando direto da borda do texto)
                    if cs_ang == 0.0:
                        if cs_x > xa_alvo + 5.0:
                            x_j = cs_x - 2.0
                            y_j = cs_y + 0.5 * h_txt
                        elif cs_x + comp < xa_alvo - 5.0:
                            x_j = cs_x + comp + 2.0
                            y_j = cs_y + 0.5 * h_txt
                        elif cs_y > ya_alvo + 2.0:
                            x_j = max(cs_x, min(cs_x + comp, xa_alvo))
                            y_j = cs_y - 2.0
                        else:
                            x_j = max(cs_x, min(cs_x + comp, xa_alvo))
                            y_j = cs_y + h_txt + 2.0
                        x_fp = None
                    else:
                        if cs_y + comp < ya_alvo - 5.0:
                            x_j = cs_x - 0.5 * h_txt
                            y_j = cs_y + comp + 2.0
                        elif cs_y > ya_alvo + 5.0:
                            x_j = cs_x - 0.5 * h_txt
                            y_j = cs_y - 2.0
                        else:
                            x_j = (cs_x - h_txt - 2.0) if cs_x >= xa_alvo else (cs_x + 2.0)
                            y_j = cs_y + 0.5 * comp
                        x_fp = None

                    corta_seta = False
                    for ob_b in obst_boxes:
                        if abs(xa_alvo - 0.5 * (ob_b[0] + ob_b[2])) < 5.0 and abs(ya_alvo - 0.5 * (ob_b[1] + ob_b[3])) < 5.0:
                            continue
                        if anti_sobreposicao._segmento_colide_box(x_j, y_j, xa_alvo, ya_alvo, ob_b, margem=0.5):
                            corta_seta = True
                            break
                        if x_fp is not None and anti_sobreposicao._segmento_colide_box(x_fp, y_j, x_j, y_j, ob_b, margem=0.5):
                            corta_seta = True
                            break
                    if corta_seta:
                        continue

                    x_dest, y_dest, ang_dest = cs_x, cs_y, cs_ang
                    precisa_seta = True
                    break

            if x_dest is None:
                x_dest = b_ref["xc"]
                y_dest = b_ref["yc"]
                ang_dest = ang_viga

            dwg.draw.level = nivel_txt
            dwg.draw.color = -1
            dwg.draw.style = 0
            dwg.draw.Text(x_dest, y_dest, h_txt, ang_dest, novo_texto)
            textos_criados += 1

            if precisa_seta and math.hypot(x_dest - xa_alvo, y_dest - ya_alvo) >= 10.0:
                anti_sobreposicao.desenhar_seta_inversao(
                    dwg, x_dest, y_dest, comp, h_txt, ang_dest, xa_alvo, ya_alvo
                )

            cand_box = anti_sobreposicao._bbox_texto(x_dest, y_dest, h_txt, ang_dest, novo_texto)
            obstaculos.append({
                "tipo": "viga_invertida",
                "bbox": cand_box
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
                if abs(lj["xc"] - b["xc"]) <= 45.0 and 0.0 <= (lj["yc"] - b["yc"]) <= 160.0:
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
                            if obs.get("nivel") in (9, 12):
                                continue
                            if _boxes_colidem(bx, obs["bbox"], margem=5.0):
                                return True
                        for lx1, ly1, lx2, ly2, _ in lines_concreto:
                            if anti_sobreposicao._segmento_colide_box(lx1, ly1, lx2, ly2, bx, margem=1.0):
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

        # Se alguma nova inversao sobrepos o identificador/secao de algum pilar,
        # organiza automaticamente os pilares conflitantes com a regra de 10 cm para seta
        try:
            import importlib
            importlib.reload(anti_sobreposicao)
            anti_sobreposicao.executar_organizar_apenas_pilares(dwg)
        except Exception:
            pass

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


def cmd_criar_cotas(eag, tqsjan):
    """
    Cria automaticamente as cotas externas (em camadas) ou cotas de pilares
    nos quadrados/capiteis da planta de formas sem duplicar cotas existentes.
    (Delega para o modulo dedicado cotas_helper.py)
    """
    import importlib
    importlib.reload(cotas_helper)
    cotas_helper.cmd_criar_cotas(eag, tqsjan)


def cmd_corrigir_vazios(eag, tqsjan):
    """
    Substitui o nivel de todas as linhas de representacao em X de vazios
    do Nivel 241 para o Nivel 210, apaga as setas/indicadores de direcao
    de lajes no Nivel 240 e cria o retangulo de fechamento (Nivel 237,
    cor/estilo por nivel) em volta de cada shaft em X que ainda nao possua.
    """
    try:
        dwg = tqsjan.dwg
        addrs_241 = []
        addrs_240 = []
        diags_vazio = []
        lines_237 = []

        dwg.iterator.Begin()
        while True:
            tipo = dwg.iterator.Next()
            if tipo == TQSDwg.DWGTYPE_EOF:
                break
            nivel = dwg.iterator.level
            addr = dwg.iterator.GetElementReadPosition()

            if nivel == 241:
                addrs_241.append(addr)
            elif nivel == 240:
                addrs_240.append(addr)

            if dwg.iterator.inBlock != 0:
                continue

            if tipo == TQSDwg.DWGTYPE_LINE:
                x1, y1 = dwg.iterator.x1, dwg.iterator.y1
                x2, y2 = dwg.iterator.x2, dwg.iterator.y2
                if nivel in (241, 210) and abs(x2 - x1) >= 3.0 and abs(y2 - y1) >= 3.0:
                    diags_vazio.append((x1, y1, x2, y2))
                elif nivel == 237:
                    lines_237.append((x1, y1, x2, y2))

        for addr in addrs_241:
            dwg.edit.ModifyLevel(addr, 210)

        for addr in addrs_240:
            dwg.edit.Erase(addr)

        # Pareia as diagonais em X dos shafts/vazios e cria retangulo no Nivel 237
        usados_diag = set()
        retangulos_criados = 0
        old_lvl = dwg.draw.level
        old_col = dwg.draw.color
        old_sty = dwg.draw.style
        try:
            dwg.draw.level = 237
            dwg.draw.color = -1
            dwg.draw.style = -1

            def _seg_237_existe(ax1, ay1, ax2, ay2):
                for bx1, by1, bx2, by2 in lines_237:
                    if (math.hypot(ax1 - bx1, ay1 - by1) <= 1.0 and math.hypot(ax2 - bx2, ay2 - by2) <= 1.0) or \
                       (math.hypot(ax1 - bx2, ay1 - by2) <= 1.0 and math.hypot(ax2 - bx1, ay2 - by1) <= 1.0):
                        return True
                return False

            for i in range(len(diags_vazio)):
                if i in usados_diag:
                    continue
                x1a, y1a, x2a, y2a = diags_vazio[i]
                sa = (x2a - x1a) * (y2a - y1a)
                mxa, mya = 0.5 * (x1a + x2a), 0.5 * (y1a + y2a)
                for j in range(i + 1, len(diags_vazio)):
                    if j in usados_diag:
                        continue
                    x1b, y1b, x2b, y2b = diags_vazio[j]
                    sb = (x2b - x1b) * (y2b - y1b)
                    if sa * sb >= 0.0:
                        continue
                    mxb, myb = 0.5 * (x1b + x2b), 0.5 * (y1b + y2b)
                    if math.hypot(mxa - mxb, mya - myb) <= 5.0:
                        usados_diag.add(i)
                        usados_diag.add(j)
                        xmin = min(x1a, x2a, x1b, x2b)
                        ymin = min(y1a, y2a, y1b, y2b)
                        xmax = max(x1a, x2a, x1b, x2b)
                        ymax = max(y1a, y2a, y1b, y2b)
                        # Apenas shafts estreitos/pequenos (menor dimensao <= 50 cm); aberturas grandes de laje ficam de fora
                        if min(xmax - xmin, ymax - ymin) > 50.0:
                            break
                        lados = [
                            (xmin, ymin, xmax, ymin),
                            (xmax, ymin, xmax, ymax),
                            (xmax, ymax, xmin, ymax),
                            (xmin, ymax, xmin, ymin),
                        ]
                        criou_lado = False
                        for lx1, ly1, lx2, ly2 in lados:
                            if not _seg_237_existe(lx1, ly1, lx2, ly2):
                                dwg.draw.Line(lx1, ly1, lx2, ly2)
                                lines_237.append((lx1, ly1, lx2, ly2))
                                criou_lado = True
                        if criou_lado:
                            retangulos_criados += 1
                        break
        finally:
            dwg.draw.level = old_lvl
            dwg.draw.color = old_col
            dwg.draw.style = old_sty

        if not addrs_241 and not addrs_240 and retangulos_criados == 0:
            eag.msg.Print("G3 Plugins: Nenhuma linha de vazio (nivel 241), indicador (nivel 240) ou shaft sem fechamento encontrado.")
            eag.msg.PrintStatus("Nenhum elemento encontrado.")
            return

        tqsjan.Regen()

        msgs = []
        if addrs_241:
            msgs.append("%d linha(s) de vazio (241 -> 210)" % len(addrs_241))
        if addrs_240:
            msgs.append("%d indicador(es)/seta(s) de laje (nivel 240 apagados)" % len(addrs_240))
        if retangulos_criados:
            msgs.append("%d retangulo(s) de fechamento de shaft (nivel 237)" % retangulos_criados)

        resumo = " e ".join(msgs)
        eag.msg.Print("G3 Plugins: Sucesso! %s." % resumo)
        eag.msg.PrintStatus("Vazios e indicadores de laje corrigidos!")

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass


def cmd_organizar(eag, tqsjan):
    """Entry point para organizar vigas, secoes, bolinhas, pilares e cotas na planta de formas."""
    import importlib
    import organizar
    importlib.reload(organizar)
    organizar.cmd_organizar(eag, tqsjan)


def cmd_organizar_pilar(eag, tqsjan):
    """Entry point dedicado para organizar exclusivamente pilares sobrepostos."""
    import importlib
    importlib.reload(anti_sobreposicao)
    anti_sobreposicao.cmd_organizar_pilar(eag, tqsjan)


def cmd_inverter_e_organizar(eag, tqsjan):
    """
    Executa em sequencia os comandos Inversoes e Organizar.
    Prioriza micro-ajustes de ate 5 cm sem seta e limita o alcance maximo
    de reposicionamento de pilares sobrepostos para nunca sairem de perto do proprio pilar.
    """
    import os
    chave = "G3_MAX_DESLOC_PILAR"
    valor_anterior = os.environ.get(chave)
    os.environ[chave] = "75.0"
    try:
        cmd_inversoes(eag, tqsjan)
        cmd_organizar(eag, tqsjan)
    finally:
        if valor_anterior is None:
            os.environ.pop(chave, None)
        else:
            os.environ[chave] = valor_anterior


def cmd_corrigir_sobreposicao(eag, tqsjan):
    """Alias de compatibilidade para cmd_organizar."""
    import importlib
    import organizar
    importlib.reload(organizar)
    organizar.cmd_organizar(eag, tqsjan)


def meucmd(eag, tqsjan):
    """Entry point padrao de Formas (chama Linha de Corte)."""
    cmd_linha_de_corte(eag, tqsjan)
