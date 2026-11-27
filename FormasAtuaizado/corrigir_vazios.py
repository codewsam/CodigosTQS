# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - CORRIGIR VAZIO E INDICADOR DE LAJE (TQS EAG)
================================================================================
Modulo dedicado a correcao de vazios em X (Nivel 241 -> 210), remocao de
indicadores/setas de laje (Nivel 240) e fechamento de shafts (Nivel 237).
================================================================================
"""
import math
from TQS import TQSUtil, TQSDwg


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


