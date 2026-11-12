# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - ORGANIZAR (TQS EAG)
================================================================================
Modulo especializado e dedicado exclusivamente a organizacao inteligente de
elementos sobrepostos em plantas de formas no ambiente TQS EAG.

Funcionalidades:
  1. Varredura Global: analisa o projeto inteiro em busca de textos e secoes
     sobrepostas (titulos de viga, secoes, indicadores de laje e nervuras).
  2. Micro-Deslocamentos Inteligentes: afasta os elementos conflitantes apenas
     alguns centimetros (15 a 25 cm), desfazendo sobreposicoes de forma sutil
     e organizada (ex: secoes lado a lado ou escalonadas ao longo da viga).
  3. Integracao com Pilares: preserva os pilares em seus lados da junta e
     alinha as secoes perfeitamente abaixo dos identificadores.
  4. Integracao com Cotas: desembaraca cotas apertadas sem poluir a forma.
================================================================================
"""

import math
import re
import importlib
from TQS import TQSUtil, TQSDwg
import anti_sobreposicao

try:
    TQSUtil.LoadDll("IPOCOT.DLL")
except Exception:
    pass


def _normalizar_angulo(ang):
    a = ang % 360.0
    if a < 0:
        a += 360.0
    if abs(a - 0.0) < 5.0 or abs(a - 360.0) < 5.0 or abs(a - 180.0) < 5.0:
        return 0.0
    if abs(a - 90.0) < 5.0 or abs(a - 270.0) < 5.0:
        return 90.0
    return a


def _bbox_texto_exato(x1, y1, x2, y2, h):
    return (min(x1, x2), min(y1, y2) - 0.25 * h, max(x1, x2), max(y1, y2) + 0.75 * h)


def _bbox_texto(x1, y1, h, ang, txt=""):
    largura = len(txt) * h * 0.8 if txt else h * 2.0
    if largura < h:
        largura = h
    a = _normalizar_angulo(ang)
    if a == 0.0:
        return (x1, y1 - 0.25 * h, x1 + largura, y1 + 0.75 * h)
    elif a == 90.0:
        return (x1 - 0.75 * h, y1, x1 + 0.25 * h, y1 + largura)
    else:
        rad = math.radians(ang)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        dx = largura * cos_a
        dy = largura * sin_a
        return (min(x1, x1 + dx) - 0.5 * h, min(y1, y1 + dy) - 0.5 * h,
                max(x1, x1 + dx) + 0.5 * h, max(y1, y1 + dy) + 0.5 * h)


def _boxes_colidem(b1, b2, margem=0.5):
    return not (
        b1[2] < b2[0] - margem
        or b1[0] > b2[2] + margem
        or b1[3] < b2[1] - margem
        or b1[1] > b2[3] + margem
    )


def _segmento_colide_box(lx1, ly1, lx2, ly2, box, margem=0.5):
    bx1 = box[0] - margem
    by1 = box[1] - margem
    bx2 = box[2] + margem
    by2 = box[3] + margem

    if max(lx1, lx2) < bx1 or min(lx1, lx2) > bx2 or max(ly1, ly2) < by1 or min(ly1, ly2) > by2:
        return False

    dx = lx2 - lx1
    dy = ly2 - ly1
    for t_step in (0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0):
        px = lx1 + t_step * dx
        py = ly1 + t_step * dy
        if bx1 <= px <= bx2 and by1 <= py <= by2:
            return True
    return False


# ------------------------------------------------------------------------------
# Geometria orientada dos textos
# ------------------------------------------------------------------------------
GAPS_TENTATIVA = (10.0, 7.0, 5.0)  # folgas (cm) tentadas em ordem: mais folga primeiro
FOLGA_VALIDACAO = 1.5              # folga exigida contra os demais textos/obstaculos
PROFUNDIDADE_MIN = 0.0             # qualquer encosto/sobreposicao ja conta como colisao
MAX_FILA = 4                       # maximo de textos empurrados juntos ao longo da linha
MAX_DESLOC = 80.0                  # deslocamento maximo de um texto (cm)


def _eixos_texto(t):
    """Retorna (ux, uy, nx, ny, comprimento) do texto: u = direcao de leitura, n = 'para cima'."""
    dx = t["x2"] - t["x1"]
    dy = t["y2"] - t["y1"]
    comp = math.hypot(dx, dy)
    if comp < 1e-6:
        rad = math.radians(t["ang"])
        ux, uy = math.cos(rad), math.sin(rad)
        comp = max(len(t["txt"]) * t["h"], t["h"])
    else:
        ux, uy = dx / comp, dy / comp
    return ux, uy, -uy, ux, comp


def _rbox(t):
    """Caixa real (AABB) do glifo considerando a orientacao (sem o espaco final do ultimo caractere)."""
    ux, uy, nx, ny, comp = _eixos_texto(t)
    h = t["h"]
    comp_real = max(comp - 0.2 * h, 0.5 * h)
    xs, ys = [], []
    for s in (0.0, comp_real):
        for q in (0.0, h):
            xs.append(t["x1"] + ux * s + nx * q)
            ys.append(t["y1"] + uy * s + ny * q)
    return (min(xs), min(ys), max(xs), max(ys))


def _transladar(box, dx, dy):
    return (box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy)


def _sobrepoe(b1, b2, folga=0.0):
    return (b1[0] < b2[2] + folga and b2[0] < b1[2] + folga and
            b1[1] < b2[3] + folga and b2[1] < b1[3] + folga)


def _colisao_real(b1, b2):
    """Colisao com profundidade minima nos dois eixos (ignora toques de canto)."""
    px = min(b1[2], b2[2]) - max(b1[0], b2[0])
    py = min(b1[3], b2[3]) - max(b1[1], b2[1])
    return px > PROFUNDIDADE_MIN and py > PROFUNDIDADE_MIN


def _projecao(box, ux, uy):
    """Intervalo [min, max] da projecao da caixa no eixo (ux, uy)."""
    vals = [x * ux + y * uy for x in (box[0], box[2]) for y in (box[1], box[3])]
    return min(vals), max(vals)


def _n_cortes_concreto(box, lines_concreto):
    n = 0
    for lx1, ly1, lx2, ly2, _ in lines_concreto:
        if _segmento_colide_box(lx1, ly1, lx2, ly2, box, margem=0.0):
            n += 1
    return n


def _par_pilar_secao(tA, tB):
    if {tA["level"], tB["level"]} == {9, 12}:
        return math.hypot(tA["x1"] - tB["x1"], tA["y1"] - tB["y1"]) < 30.0
    return False


def _colinear(ref, t):
    """True se 't' esta na mesma linha de leitura de 'ref' (mesma direcao e mesmo eixo)."""
    ux, uy, nx, ny, _ = _eixos_texto(ref)
    tux, tuy, _, _, _ = _eixos_texto(t)
    if abs(ux * tux + uy * tuy) < 0.99:
        return False
    r0, r1 = _projecao(ref["rbox"], nx, ny)
    t0, t1 = _projecao(t["rbox"], nx, ny)
    return abs(0.5 * (r0 + r1) - 0.5 * (t0 + t1)) < 0.6 * max(ref["h"], t["h"])


def _fila_ao_longo(alvo, outro, sinal, gap, texts_raw):
    """
    Desloca 'alvo' ao longo da sua direcao de leitura (sinal +1 = frente, -1 = tras) ate ficar
    'gap' cm afastado de 'outro'. Se esbarrar em textos da MESMA linha (ex: bolinha logo depois
    da secao), empurra-os junto, como uma fila. Retorna {id(texto): (texto, dx, dy)} ou None.
    """
    ux, uy, _, _, _ = _eixos_texto(alvo)
    a0, a1 = _projecao(alvo["rbox"], ux, uy)
    o0, o1 = _projecao(outro["rbox"], ux, uy)
    s = ((o1 + gap) - a0) if sinal > 0 else ((o0 - gap) - a1)
    if s * sinal <= 0 or abs(s) > MAX_DESLOC:
        return None

    moves = {id(alvo): (alvo, ux * s, uy * s)}
    fila = [alvo]
    while fila:
        m = fila.pop(0)
        _, mdx, mdy = moves[id(m)]
        mbox = _transladar(m["rbox"], mdx, mdy)
        m0, m1 = _projecao(mbox, ux, uy)
        mc_orig = sum(_projecao(m["rbox"], ux, uy)) * 0.5
        for t in texts_raw:
            if id(t) in moves or t is outro:
                continue
            if not _sobrepoe(mbox, t["rbox"], gap * 0.5):
                continue
            if not _colinear(alvo, t):
                continue  # obstaculo fora da linha: a validacao decide
            t0, t1 = _projecao(t["rbox"], ux, uy)
            if (0.5 * (t0 + t1) - mc_orig) * sinal <= 0:
                continue  # esta para tras na fila, nao empurra
            st = ((m1 + gap) - t0) if sinal > 0 else ((m0 - gap) - t1)
            if st * sinal <= 0:
                continue
            if abs(st) > MAX_DESLOC or len(moves) >= MAX_FILA:
                return None
            moves[id(t)] = (t, ux * st, uy * st)
            fila.append(t)
    return moves


def _deslocamento_perpendicular(alvo, outro, sinal, gap):
    _, _, nx, ny, _ = _eixos_texto(alvo)
    a0, a1 = _projecao(alvo["rbox"], nx, ny)
    o0, o1 = _projecao(outro["rbox"], nx, ny)
    s = ((o1 + gap) - a0) if sinal > 0 else ((o0 - gap) - a1)
    limite = 80.0 if alvo["level"] in (10, 13) else 40.0  # nomes de laje podem andar mais
    if s * sinal <= 0 or abs(s) > limite:
        return None
    return {id(alvo): (alvo, nx * s, ny * s)}


def _grupo_valido(moves, outro, gap, texts_raw, lines_concreto, obstaculos_fixos, boxes_pilares):
    novos = {k: _transladar(t["rbox"], dx, dy) for k, (t, dx, dy) in moves.items()}
    for k, (t, dx, dy) in moves.items():
        cbox = novos[k]
        if _sobrepoe(cbox, outro["rbox"], gap * 0.5 - 0.01):
            return False
        for tO in texts_raw:
            if id(tO) in moves or _par_pilar_secao(t, tO):
                continue
            if _sobrepoe(cbox, tO["rbox"], FOLGA_VALIDACAO):
                return False
        for k2, b2 in novos.items():
            if k2 != k and _sobrepoe(cbox, b2, 0.0):
                return False
        if any(_sobrepoe(cbox, obs, FOLGA_VALIDACAO) for obs in obstaculos_fixos):
            return False
        if any(_sobrepoe(cbox, pb, 1.0) for pb in boxes_pilares):
            return False
        # Nao pode cortar MAIS linhas de concreto do que ja cortava na posicao original
        if _n_cortes_concreto(cbox, lines_concreto) > _n_cortes_concreto(t["rbox"], lines_concreto):
            return False
    return True


def _ordem_alvos(tA, tB):
    """Quem cede primeiro: secoes/bolinhas (11) antes de titulos (8); textos menores antes."""
    prioridade = {8: 3, 9: 3, 10: 2, 12: 2, 13: 1, 11: 0}
    pA = prioridade.get(tA["level"], 1)
    pB = prioridade.get(tB["level"], 1)
    if pA != pB:
        par = (tA, tB) if pA < pB else (tB, tA)
    elif tA["h"] != tB["h"]:
        par = (tA, tB) if tA["h"] < tB["h"] else (tB, tA)
    else:
        par = (tB, tA)
    return [par, (par[1], par[0])]


def _planos_de_afastamento(alvo, outro, gap, texts_raw, tipo):
    """Planos em ordem de preferencia: ao longo da leitura (fila) -> perpendicular."""
    # Nomes/secoes de pilar ficam com a rotina dedicada de pilares (seta + juntas)
    if alvo["level"] in (9, 12):
        return []
    planos = []
    for sinal in (+1, -1):
        m = _fila_ao_longo(alvo, outro, sinal, gap, texts_raw)
        if m:
            custo = sum(math.hypot(dx, dy) for _, dx, dy in m.values())
            planos.append((0, custo, m))
    # Titulos de viga e pilares nunca saem de lado (sairiam da viga); so deslizam
    if alvo["level"] not in (8, 9):
        for sinal in (+1, -1):
            m = _deslocamento_perpendicular(alvo, outro, sinal, gap)
            if m:
                _, dx, dy = m[id(alvo)]
                planos.append((1, math.hypot(dx, dy), m))
    planos.sort(key=lambda p: (p[0], p[1]))
    return [p[2] for p in planos if p[0] == tipo]


def resolver_micro_sobreposicoes_textos(dwg, texts_raw, lines_concreto, obstaculos_fixos, poly_pilares):
    """
    Varre todo o projeto identificando textos sobrepostos e os afasta SEGUINDO A ORIENTACAO:
      - Desliza ao longo da direcao de leitura (vertical -> em Y, horizontal -> em X),
        empurrando junto os textos da mesma linha (ex: 'V510-A  15/60  (20)').
      - Tenta primeiro uma folga confortavel (10 cm) e reduz so se faltar espaco.
      - Se nao couber ao longo da linha, empilha perpendicularmente (exceto titulos).
    """
    total_ajustes = 0
    boxes_pilares = [pb["box"] for pb in poly_pilares]

    for t in texts_raw:
        t["rbox"] = _rbox(t)

    # Nome do pilar (9) e sua secao (12) andam sempre juntos
    parceiros = {}
    for t9 in texts_raw:
        if t9["level"] != 9:
            continue
        cands = [t for t in texts_raw if _par_pilar_secao(t9, t)]
        if cands:
            t12 = min(cands, key=lambda t: math.hypot(t["x1"] - t9["x1"], t["y1"] - t9["y1"]))
            parceiros[id(t9)] = t12
            parceiros[id(t12)] = t9

    def _com_parceiros(moves):
        for t, dx, dy in list(moves.values()):
            pt = parceiros.get(id(t))
            if pt is not None and id(pt) not in moves:
                moves[id(pt)] = (pt, dx, dy)
        return moves

    for _passada in range(6):
        mudou = False
        for i in range(len(texts_raw)):
            for j in range(i + 1, len(texts_raw)):
                tA, tB = texts_raw[i], texts_raw[j]
                if _par_pilar_secao(tA, tB):
                    continue
                if not _colisao_real(tA["rbox"], tB["rbox"]):
                    continue

                # Ordem: 1) ao longo da leitura (todas as folgas), 2) perpendicular
                escolhido = None
                for tipo in (0, 1):
                    for gap in GAPS_TENTATIVA:
                        for alvo, outro in _ordem_alvos(tA, tB):
                            for moves in _planos_de_afastamento(alvo, outro, gap, texts_raw, tipo):
                                moves = _com_parceiros(moves)
                                if id(outro) in moves:
                                    continue
                                if _grupo_valido(moves, outro, gap, texts_raw, lines_concreto,
                                                 obstaculos_fixos, boxes_pilares):
                                    escolhido = moves
                                    break
                            if escolhido:
                                break
                        if escolhido:
                            break
                    if escolhido:
                        break

                if escolhido is None:
                    continue

                for t, dx, dy in escolhido.values():
                    try:
                        dwg.edit.Move(t["addr"], dx, dy)
                    except Exception:
                        continue
                    for k in ("x1", "x2", "xc"):
                        t[k] += dx
                    for k in ("y1", "y2", "yc"):
                        t[k] += dy
                    t["rbox"] = _transladar(t["rbox"], dx, dy)
                    t["box"] = _transladar(t["box"], dx, dy)
                    total_ajustes += 1
                mudou = True
        if not mudou:
            break

    return total_ajustes


def executar_organizar_tudo(dwg):
    """
    Fluxo mestre de Organizacao Geral da Planta de Formas:
      1. Carrega todos os elementos graficos do desenho (textos, linhas, poligonos de pilar).
      2. Resolve sobreposicoes gerais de textos com micro-deslocamentos sutis.
      3. Reorganiza pilares e secoes mantendo a restricao estrita de juntas de dilatacao.
      4. Organiza cotas apertadas.
    """
    lines_concreto = []
    obstaculos_fixos = []
    todos_obstaculos_cotas = []
    texts_raw = []
    poly_pilares = []
    linhas_242 = []
    linhas_221_setas = []

    dwg.iterator.Begin()
    while True:
        tipo = dwg.iterator.Next()
        if tipo == TQSDwg.DWGTYPE_EOF:
            break
        if dwg.iterator.inBlock != 0:
            continue

        l = dwg.iterator.level
        addr = dwg.iterator.GetElementReadPosition()

        if tipo == TQSDwg.DWGTYPE_LINE:
            if l in (1, 2, 201):
                lines_concreto.append((dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2, l))
            elif l == 242:
                linhas_242.append({"addr": addr, "x1": dwg.iterator.x1, "y1": dwg.iterator.y1, "x2": dwg.iterator.x2, "y2": dwg.iterator.y2})
            elif l == 221:
                linhas_221_setas.append({"addr": addr, "x1": dwg.iterator.x1, "y1": dwg.iterator.y1, "x2": dwg.iterator.x2, "y2": dwg.iterator.y2})
        elif tipo == TQSDwg.DWGTYPE_TEXT:
            if l in (28, 29):
                continue
            txt_str = dwg.iterator.text.strip()
            h = dwg.iterator.textHeight
            ang = _normalizar_angulo(dwg.iterator.textAngle)
            x1, y1 = dwg.iterator.x1, dwg.iterator.y1
            x2, y2 = dwg.iterator.x2, dwg.iterator.y2
            xc, yc = dwg.iterator.xc, dwg.iterator.yc
            b = _bbox_texto_exato(x1, y1, x2, y2, h)
            if l in (122, 216):
                todos_obstaculos_cotas.append(b)
                obstaculos_fixos.append(b)
            else:
                texts_raw.append({
                    "addr": addr, "level": l, "txt": txt_str,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "xc": xc, "yc": yc, "h": h, "ang": ang, "box": b
                })
        elif tipo == TQSDwg.DWGTYPE_POLYLINE:
            pts = [dwg.iterator.GetPolylinePt(i) for i in range(dwg.iterator.xySize)]
            if pts:
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                dx_poly = max(xs) - min(xs)
                dy_poly = max(ys) - min(ys)
                if l in (2, 3, 4, 5) and 8.0 <= dx_poly <= 180.0 and 8.0 <= dy_poly <= 180.0 and len(pts) >= 4:
                    poly_pilares.append({
                        "addr": addr, "level": l, "pts": pts,
                        "box": (min(xs), min(ys), max(xs), max(ys)),
                        "pcx": 0.5 * (min(xs) + max(xs)),
                        "pcy": 0.5 * (min(ys) + max(ys)),
                    })

    total_ajustes = 0

    # 1. Resolve sobreposicoes gerais de textos (titulos, secoes, lajes, nervuras)
    ajustes_textos = resolver_micro_sobreposicoes_textos(
        dwg, texts_raw, lines_concreto, obstaculos_fixos, poly_pilares
    )
    total_ajustes += ajustes_textos

    # 2. Reorganiza pilares mantendo territorialidade de juntas e secoes abaixo
    try:
        pilares_group = anti_sobreposicao._construir_pilares_group(texts_raw, poly_pilares)
        # So reposiciona (com seta) os pilares cujo nome/secao AINDA estejam realmente
        # sobrepostos a outro texto; os demais ficam exatamente onde estao.
        for t in texts_raw:
            t["rbox"] = _rbox(t)

        def _grupo_sobreposto(g):
            proprios = [x for x in (g.get("p9"), g.get("p12")) if x]
            ids = set(id(x) for x in proprios)
            for x in proprios:
                for tO in texts_raw:
                    if id(tO) in ids or _par_pilar_secao(x, tO):
                        continue
                    if _colisao_real(x["rbox"], tO["rbox"]):
                        return True
            return False

        pilares_group = [g for g in pilares_group if _grupo_sobreposto(g)]
        ajustes_pilares = anti_sobreposicao.reposicionar_pilares_conflitantes(
            dwg, pilares_group, poly_pilares, lines_concreto, obstaculos_fixos,
            todos_obstaculos_cotas, texts_raw, linhas_242, linhas_221_setas,
            forcar_ciclo_se_deslocado=False
        )
        total_ajustes += ajustes_pilares
    except Exception:
        pass

    # 3. Organiza cotas apertadas
    try:
        import cotas_helper
        total_ajustes += cotas_helper._organizar_cotas_apertadas(dwg)
    except Exception:
        pass

    return total_ajustes


def cmd_organizar(eag, tqsjan):
    """
    Comando executado ao clicar no botao 'Organizar'.
    """
    try:
        importlib.reload(anti_sobreposicao)
        dwg = getattr(tqsjan, "dwg", None) or getattr(eag, "ActiveDwg", None)
        if dwg is None:
            if hasattr(eag, "msg"):
                eag.msg.Print("G3 Plugins: Nenhum desenho ativo.")
            return

        n_ajustes = executar_organizar_tudo(dwg)

        try:
            tqsjan.Regen()
        except Exception:
            pass
        try:
            dwg.Update()
            dwg.Display()
        except Exception:
            pass

        if n_ajustes > 0:
            if hasattr(eag, "msg"):
                eag.msg.Print("G3 Plugins: %d elemento(s) organizado(s) sem sobreposicao com sucesso!" % n_ajustes)
                eag.msg.PrintStatus("%d elemento(s) organizado(s)!" % n_ajustes)
            elif hasattr(eag, "dialogs"):
                eag.dialogs.OK("G3 Plugins: %d elemento(s) organizado(s) sem sobreposicao com sucesso!" % n_ajustes)
        else:
            if hasattr(eag, "msg"):
                eag.msg.Print("G3 Plugins: Planta ja se encontra perfeitamente organizada e limpa.")
                eag.msg.PrintStatus("Planta ja organizada.")
            elif hasattr(eag, "dialogs"):
                eag.dialogs.OK("G3 Plugins: Nenhuma sobreposicao detectada na planta.")

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass


def meucmd(eag, tqsjan):
    """Entry point padrao quando acionado pelo menu TQS."""
    cmd_organizar(eag, tqsjan)
