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
                if nivel in (2, 3, 4, 5) and 8.0 <= dx_p <= 180.0 and 8.0 <= dy_p <= 180.0 and len(pts) >= 4:
                    obstaculos.append({"tipo": "pilar", "bbox": (min(xs), min(ys), max(xs), max(ys))})
                elif nivel in (1, 2, 201) and len(pts) >= 2:
                    for k in range(len(pts) - 1):
                        x1, y1 = pts[k]
                        x2, y2 = pts[k + 1]
                        if abs(x1 - x2) <= 3.0 and abs(y1 - y2) > 10.0:
                            linhas_vert_concreto.append((0.5 * (x1 + x2), min(y1, y2), max(y1, y2)))
                        elif abs(y1 - y2) <= 3.0 and abs(x1 - x2) > 10.0:
                            linhas_horiz_concreto.append((0.5 * (y1 + y2), min(x1, x2), max(x1, y2)))

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

        lines_concreto = []
        for y, x1, x2 in ctx.get("linhas_horiz_concreto", []):
            lines_concreto.append((x1, y, x2, y, 1))
        for x, y1, y2 in ctx.get("linhas_vert_concreto", []):
            lines_concreto.append((x, y1, x, y2, 1))

        textos_criados = 0
        bolinhas_apagadas = 0

        # ---------------------------------------------------------------------
        # 1. PROCESSA VIGAS (NIVEL 11) - 1 UNICO TEXTO POR VIGA (SEM REPETIR)
        # ---------------------------------------------------------------------
        grupos_vigas = _agrupar_bolinhas_vigas(bolinhas_viga, ctx["vigas"], ctx.get("secoes", []), lines_concreto)

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
                cand_sec = (sec_box[2] + 8.0, sec["y1"], 0.0) if ang_viga == 0.0 else (sec["x1"], sec_box[3] + 8.0, 90.0)
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

            precisa_seta = False
            # 2. Se nao coube direto no trecho local, POSICIONA COM SETA DE CHAMADA (validando linha da seta!)
            if not colocou_direto:
                candidatos_seta = []
                for r in (25.0, 40.0, 55.0, 75.0, 95.0, 120.0, 150.0):
                    # Horizontal (ang = 0)
                    for dy in (0.0, 20.0, -20.0, 40.0, -40.0):
                        candidatos_seta.append((xa_alvo + r, ya_alvo + dy - 0.5 * h_txt, 0.0))
                        candidatos_seta.append((xa_alvo - r - comp, ya_alvo + dy - 0.5 * h_txt, 0.0))
                    for dx in (0.0, 25.0, -25.0, 50.0, -50.0):
                        candidatos_seta.append((xa_alvo - 0.5 * comp + dx, ya_alvo + r, 0.0))
                        candidatos_seta.append((xa_alvo - 0.5 * comp + dx, ya_alvo - r - h_txt, 0.0))
                    # Se viga for vertical, testa tambem vertical
                    if ang_viga == 90.0:
                        for dy in (0.0, 25.0, -25.0):
                            candidatos_seta.append((xa_alvo + r, ya_alvo - 0.5 * comp + dy, 90.0))
                            candidatos_seta.append((xa_alvo - r - h_txt, ya_alvo - 0.5 * comp + dy, 90.0))

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

                    # Valida linha da seta
                    if cs_ang == 0.0:
                        if cs_x >= xa_alvo:
                            x_j = cs_x - 2.0
                            y_j = cs_y - 2.0
                            x_fp = cs_x + min(35.0, comp)
                        else:
                            x_j = cs_x + comp + 2.0
                            y_j = cs_y - 2.0
                            x_fp = cs_x + comp - min(35.0, comp)
                    else:
                        x_j = (cs_x - 2.0) if cs_x >= xa_alvo else (cs_x + 2.0)
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

            if precisa_seta and math.hypot(x_dest - xa_alvo, y_dest - ya_alvo) >= 25.0:
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

        # Se ja houver cotas no desenho, reorganiza textos de pilares/vigas/lajes sem sobreposicao
        try:
            cotas_helper.organizar_textos_sem_sobreposicao(dwg)
        except Exception:
            pass

        # Executa tambem o organizador de vigas/pilares para fechar gaps (ex: 15/60 V505-A) e garantir zero sobreposicao
        try:
            anti_sobreposicao.executar_anti_sobreposicao(dwg)
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
    Cria automaticamente as cotas externas (em camadas) e completa as cadeias
    de cotas internas da planta de formas sem duplicar cotas existentes.
    (Delega para o modulo dedicado cotas_helper.py)
    """
    cotas_helper.cmd_criar_cotas(eag, tqsjan)


def cmd_corrigir_vazios(eag, tqsjan):
    """
    Substitui o nivel de todas as linhas de representacao em X de vazios
    do Nivel 241 para o Nivel 210 e apaga as setas/indicadores de direcao
    de lajes no Nivel 240.
    """
    try:
        dwg = tqsjan.dwg
        addrs_241 = []
        addrs_240 = []

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

        if not addrs_241 and not addrs_240:
            eag.msg.Print("G3 Plugins: Nenhuma linha de vazio (nivel 241) ou indicador de laje (nivel 240) encontrado.")
            eag.msg.PrintStatus("Nenhum elemento encontrado.")
            return

        for addr in addrs_241:
            dwg.edit.ModifyLevel(addr, 210)

        for addr in addrs_240:
            dwg.edit.Erase(addr)

        tqsjan.Regen()

        msgs = []
        if addrs_241:
            msgs.append("%d linha(s) de vazio (241 -> 210)" % len(addrs_241))
        if addrs_240:
            msgs.append("%d indicador(es)/seta(s) de laje (nivel 240 apagados)" % len(addrs_240))

        resumo = " e ".join(msgs)
        eag.msg.Print("G3 Plugins: Sucesso! %s." % resumo)
        eag.msg.PrintStatus("Vazios e indicadores de laje corrigidos!")

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass


def cmd_organizar(eag, tqsjan):
    """Entry point para organizar vigas, bolinhas e pilares na planta de formas."""
    import importlib
    importlib.reload(anti_sobreposicao)
    anti_sobreposicao.cmd_organizar(eag, tqsjan)


def cmd_organizar_pilar(eag, tqsjan):
    """Entry point dedicado para organizar exclusivamente pilares sobrepostos."""
    import importlib
    importlib.reload(anti_sobreposicao)
    anti_sobreposicao.cmd_organizar_pilar(eag, tqsjan)


def cmd_corrigir_sobreposicao(eag, tqsjan):
    """Alias de compatibilidade para cmd_organizar."""
    import importlib
    importlib.reload(anti_sobreposicao)
    anti_sobreposicao.cmd_organizar(eag, tqsjan)


def meucmd(eag, tqsjan):
    """Entry point padrao de Formas (chama Linha de Corte)."""
    cmd_linha_de_corte(eag, tqsjan)
