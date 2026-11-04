# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - FORMAS (TQS EAG)
================================================================================
Modulo dedicado a ferramentas e automatizacoes de formas estruturais.
Funcoes:
  1. Linha de Corte (criacao automatica de linha Nivel 200 entre marcas de corte)
  2. Inversoes (transforma bolinhas de desnivel em VIGA INVERTIDA / LAJE REBAIXADA)
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
    Se nao encontrar marcadores automaticos, oferece selecao manual por 2 pontos.
    """
    try:
        dwg = tqsjan.dwg
        pares = encontrar_pares_de_corte(dwg)

        linhas_criadas = 0

        if pares:
            # Configura propriedades da linha de corte: Nivel 200, Cor 2 (Amarelo), Estilo 2 (Traco-Ponto)
            dwg.draw.level = 200
            dwg.draw.color = 2
            dwg.draw.style = 2

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

            dwg.draw.level = 200
            dwg.draw.color = 2
            dwg.draw.style = 2
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


def encontrar_bolinhas_inversao(dwg):
    """
    Localiza todas as bolinhas de inversao/rebaixo na forma (Circulo + Texto numerico interno).
    Ignora circulos de eixos (niveis 28 e 29) e elementos dentro de blocos.
    """
    circulos = []
    textos = []

    dwg.iterator.Begin()
    while True:
        tipo = dwg.iterator.Next()
        if tipo == TQSDwg.DWGTYPE_EOF:
            break
        if dwg.iterator.inBlock != 0:
            continue

        if tipo == TQSDwg.DWGTYPE_CIRCLE:
            nivel = dwg.iterator.level
            if nivel in (28, 29):
                continue
            circulos.append({
                "addr": dwg.iterator.GetElementReadPosition(),
                "xc": dwg.iterator.xc,
                "yc": dwg.iterator.yc,
                "r": dwg.iterator.radius,
                "level": nivel,
            })
        elif tipo == TQSDwg.DWGTYPE_TEXT:
            nivel = dwg.iterator.level
            if nivel in (28, 29):
                continue
            txt_raw = dwg.iterator.text.strip()
            val = _parse_valor_bolinha(txt_raw)
            if val is not None:
                textos.append({
                    "addr": dwg.iterator.GetElementReadPosition(),
                    "xc": dwg.iterator.xc,
                    "yc": dwg.iterator.yc,
                    "x1": dwg.iterator.x1,
                    "y1": dwg.iterator.y1,
                    "x2": dwg.iterator.x2,
                    "y2": dwg.iterator.y2,
                    "text": txt_raw,
                    "val": val,
                    "h": dwg.iterator.textHeight,
                    "ang": dwg.iterator.textAngle,
                    "level": nivel,
                })

    bolinhas = []
    textos_usados = set()

    for c in circulos:
        melhor_tx = None
        menor_dist = float("inf")

        for idx, tx in enumerate(textos):
            if idx in textos_usados:
                continue
            if tx["level"] != c["level"]:
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
            bolinhas.append({
                "addr_circulo": c["addr"],
                "addr_texto": tx_obj["addr"],
                "val": tx_obj["val"],
                "xc": tx_obj["xc"],
                "yc": tx_obj["yc"],
                "h": tx_obj["h"],
                "ang": round(tx_obj["ang"], 2),
                "level": tx_obj["level"],
            })

    return bolinhas


def cmd_inversoes(eag, tqsjan):
    """
    Transforma as bolinhas de inversao/rebaixo nos textos correspondentes:
      - Positivo (+x): 'VIGA INVERTIDA xCM'
      - Negativo (-x): 'LAJE REBAIXADA xCM'
    Mantendo a orientacao (angulo), altura e nivel original (Cor por nivel, Estilo 0).
    """
    try:
        dwg = tqsjan.dwg
        bolinhas = encontrar_bolinhas_inversao(dwg)

        if not bolinhas:
            eag.msg.Print("G3 Plugins: Nenhuma bolinha de inversao/rebaixo encontrada no desenho.")
            eag.msg.PrintStatus("Nenhuma bolinha de inversao encontrada.")
            return

        convertidas = 0
        for b in bolinhas:
            val = b["val"]
            val_str = _formatar_valor_cm(val)
            if val > 0:
                novo_texto = "VIGA INVERTIDA %sCM" % val_str
            else:
                novo_texto = "LAJE REBAIXADA %sCM" % val_str

            # Apaga a bolinha (circulo + numero interno)
            dwg.edit.Erase(b["addr_circulo"])
            dwg.edit.Erase(b["addr_texto"])

            # Desenha o novo texto no mesmo nivel, cor por nivel (-1), estilo 0 e mesma orientacao
            dwg.draw.level = b["level"]
            dwg.draw.color = -1
            dwg.draw.style = 0
            dwg.draw.Text(b["xc"], b["yc"], b["h"], b["ang"], novo_texto)
            convertidas += 1

        tqsjan.Regen()
        eag.msg.Print("G3 Plugins: %d bolinha(s) transformada(s) em texto de inversao/rebaixo!" % convertidas)
        eag.msg.PrintStatus("%d inversao(oes) aplicada(s) com sucesso!" % convertidas)

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass


def meucmd(eag, tqsjan):
    """Entry point padrao de Formas (chama Linha de Corte)."""
    cmd_linha_de_corte(eag, tqsjan)
