# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - ORGANIZAR FORMAS (TQS EAG)
================================================================================
Modulo especializado em organizacao inteligente e eliminacao de sobreposicoes
em plantas de formas no ambiente TQS EAG.

Logica Estrutural de Formas:
  1. Viga Branca Continua: uma viga e definida pelo corredor de linhas brancas
     de concreto (Niveis 1, 2, 201) e se estende continuamente ate o fim do
     concreto ou ate encontrar outro nome "VXXX" no mesmo alinhamento.
  2. Nome da Viga ("VXXX", Nivel 8) + Secao ("xx/xx", Nivel 11): ficam proximos
     e podem deslizar ou trocar de lado na mesma viga para nao sobrepor nada.
  3. Bolinhas de Inversao ("(xx)", Nivel 11) e Textos "VIGA INVERTIDA xxCM":
     - Se uma mesma viga tiver varias bolinhas com o mesmo valor (ex: varias
       bolinhas 40 ao longo da V513-A ou V501-A), mantem apenas 1 identificacao
       naquela viga e apaga as repetidas.
     - Podem trocar de lado da viga branca ou deslizar para outro trecho livre
       da mesma viga para nunca colidir com pilares, textos ou vigas.
  4. Pilares ("P..." Nivel 9 + "b/h" Nivel 12): agrupados atomicamente ao seu
     poligono fisico (1-para-1) e realocados com Seta de Chamada Executiva no
     Nivel 221 quando houver qualquer sobreposicao.
================================================================================
"""

import os
import math
import re
from TQS import TQSUtil, TQSDwg

try:
    TQSUtil.LoadDll("IPOCOT.DLL")
except Exception:
    pass

LIMITE_SEM_SETA_INVERSAO_VIGA = 40.0


def _garantir_ipocot_carregado():
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
    return round(a, 2)


def _bbox_texto_exato(x1, y1, x2, y2, h):
    """
    Calcula bounding box exato (xmin, ymin, xmax, ymax) a partir dos pontos reais do TQS
    (dwg.iterator.x1, y1 e x2, y2).
    No TQS, o vetor (x2 - x1, y2 - y1) define a linha de base com comprimento exato len * h.
    A altura do caractere e perpendicular a essa linha (com margem de descidas e acentos).
    """
    vx = x2 - x1
    vy = y2 - y1
    L = math.hypot(vx, vy)
    if L < 1e-4:
        return (x1 - h * 1.15, y1 - h * 0.25, x1 + h * 1.15, y1 + h * 1.15)
    ux, uy = vx / L, vy / L
    nx, ny = -uy, ux
    corners = [
        (x1 - 0.25 * h * nx, y1 - 0.25 * h * ny),
        (x1 + 1.15 * h * nx, y1 + 1.15 * h * ny),
        (x2 + 1.15 * h * nx, y2 + 1.15 * h * ny),
        (x2 - 0.25 * h * nx, y2 - 0.25 * h * ny),
    ]
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    return (min(xs), min(ys), max(xs), max(ys))


def _bbox_texto(x1, y1, h, ang, texto_str):
    """
    Calcula bounding box (xmin, ymin, xmax, ymax) de um texto candidato no TQS.
    No TQS o espaco por caractere e 1.0 * h.
    """
    comp = len(texto_str) * h * 1.0
    rad = math.radians(ang)
    vx = comp * math.cos(rad)
    vy = comp * math.sin(rad)
    return _bbox_texto_exato(x1, y1, x1 + vx, y1 + vy, h)


def _boxes_colidem(b1, b2, margem=2.0):
    """Verifica se dois bounding boxes (xmin, ymin, xmax, ymax) se sobrepoem com margem."""
    return not (
        b1[2] + margem < b2[0] or
        b1[0] - margem > b2[2] or
        b1[3] + margem < b2[1] or
        b1[1] - margem > b2[3]
    )


def _segmento_colide_box(x1, y1, x2, y2, box, margem=0.5):
    """
    Verifica com precisao matematica (Liang-Barsky) se o segmento de reta (x1, y1) -> (x2, y2)
    cruza ou toca o retangulo box expandido por 'margem'.
    """
    xmin = box[0] - margem
    ymin = box[1] - margem
    xmax = box[2] + margem
    ymax = box[3] + margem

    dx = x2 - x1
    dy = y2 - y1

    p = [-dx, dx, -dy, dy]
    q = [x1 - xmin, xmax - x1, y1 - ymin, ymax - y1]

    u1 = 0.0
    u2 = 1.0

    for i in range(4):
        if p[i] == 0:
            if q[i] < 0:
                return False
        else:
            t = q[i] / p[i]
            if p[i] < 0:
                if t > u2:
                    return False
                if t > u1:
                    u1 = t
            else:
                if t < u1:
                    return False
                if t < u2:
                    u2 = t

    return u1 <= u2


def mapear_vigas_continuas(vigas_titulo, lines_concreto):
    """
    Mapeia cada titulo de viga 'VXXX' para o seu corredor continuo de concreto branco:
      - t_min, t_max: coordenadas das duas faces paralelas da viga branca
      - l_min, l_max: extensao longitudinal continua da viga branca (terminando onde
        acaba o concreto ou onde comeca outro nome 'VXXX' no mesmo alinhamento).
    """
    segs_h = []
    segs_v = []
    for x1, y1, x2, y2, _ in lines_concreto:
        if abs(y1 - y2) <= 8.0 and abs(x1 - x2) > 10.0:
            segs_h.append((0.5 * (y1 + y2), min(x1, x2), max(x1, x2)))
        elif abs(x1 - x2) <= 8.0 and abs(y1 - y2) > 10.0:
            segs_v.append((0.5 * (x1 + x2), min(y1, y2), max(y1, y2)))

    vigas_geom = []
    for v in vigas_titulo:
        ang = v["ang"]
        bx = v.get("box") or v.get("bbox")
        if ang == 0.0:
            vx1, vx2 = bx[0], bx[2]
            vxm = 0.5 * (vx1 + vx2)
            vy = v["yc"]
            perto = [s for s in segs_h if abs(s[0] - vy) <= 45.0 and (s[1] - 80.0 <= vxm <= s[2] + 80.0)]
            if not perto:
                perto = [s for s in segs_h if abs(s[0] - vy) <= 45.0]
            ys = sorted(list(set(round(s[0], 1) for s in perto)))
            # Encontra o par de faces paralelas que define a viga (espessura tipica 9 a 40 cm) mais proximo do centro
            par_faces_h = None
            menor_d_h = float("inf")
            for i in range(len(ys)):
                for j in range(i + 1, len(ys)):
                    w = ys[j] - ys[i]
                    if 9.0 <= w <= 40.0:
                        d_c = abs(0.5 * (ys[i] + ys[j]) - vy)
                        if d_c < menor_d_h:
                            menor_d_h = d_c
                            par_faces_h = (ys[i], ys[j])
            if par_faces_h:
                y_inf, y_sup = par_faces_h
            else:
                y_inf = min(ys) if ys else vy - 15.0
                y_sup = max(ys) if ys else vy
                if abs(y_sup - y_inf) < 5.0:
                    if vy >= y_sup:
                        y_inf = y_sup - 15.0
                    else:
                        y_sup = y_inf + 15.0

            faixa_segs = sorted([s for s in segs_h if y_inf - 12.0 <= s[0] <= y_sup + 12.0], key=lambda x: x[1])
            clusters = []
            for s in faixa_segs:
                if not clusters or s[1] > clusters[-1][1] + 90.0:
                    clusters.append([s[1], s[2]])
                else:
                    clusters[-1][1] = max(clusters[-1][1], s[2])
            xmin, xmax = vx1, vx2
            for c in clusters:
                if c[0] - 50.0 <= vxm <= c[1] + 50.0:
                    xmin, xmax = c[0], c[1]
                    break
            vigas_geom.append({
                "viga": v,
                "nome": v.get("txt") or v.get("nome"),
                "ang": 0.0,
                "t_min": y_inf,
                "t_max": y_sup,
                "l_min": xmin,
                "l_max": xmax,
                "l_txt": vxm,
            })
        else:
            vy1, vy2 = bx[1], bx[3]
            vym = 0.5 * (vy1 + vy2)
            vx = v["xc"]
            perto = [s for s in segs_v if abs(s[0] - vx) <= 45.0 and (s[1] - 80.0 <= vym <= s[2] + 80.0)]
            if not perto:
                perto = [s for s in segs_v if abs(s[0] - vx) <= 45.0]
            xs = sorted(list(set(round(s[0], 1) for s in perto)))
            # Encontra o par de faces paralelas que define a viga (espessura tipica 9 a 40 cm) mais proximo do centro
            par_faces_v = None
            menor_d_v = float("inf")
            for i in range(len(xs)):
                for j in range(i + 1, len(xs)):
                    w = xs[j] - xs[i]
                    if 9.0 <= w <= 40.0:
                        d_c = abs(0.5 * (xs[i] + xs[j]) - vx)
                        if d_c < menor_d_v:
                            menor_d_v = d_c
                            par_faces_v = (xs[i], xs[j])
            if par_faces_v:
                x_esq, x_dir = par_faces_v
            else:
                x_esq = min(xs) if xs else vx
                x_dir = max(xs) if xs else vx + 15.0
                if abs(x_dir - x_esq) < 5.0:
                    if vx <= x_esq:
                        x_dir = x_esq + 15.0
                    else:
                        x_esq = x_dir - 15.0

            faixa_segs = sorted([s for s in segs_v if x_esq - 12.0 <= s[0] <= x_dir + 12.0], key=lambda x: x[1])
            clusters = []
            for s in faixa_segs:
                if not clusters or s[1] > clusters[-1][1] + 90.0:
                    clusters.append([s[1], s[2]])
                else:
                    clusters[-1][1] = max(clusters[-1][1], s[2])
            ymin, ymax = vy1, vy2
            for c in clusters:
                if c[0] - 50.0 <= vym <= c[1] + 50.0:
                    ymin, ymax = c[0], c[1]
                    break
            vigas_geom.append({
                "viga": v,
                "nome": v.get("txt") or v.get("nome"),
                "ang": 90.0,
                "t_min": x_esq,
                "t_max": x_dir,
                "l_min": ymin,
                "l_max": ymax,
                "l_txt": vym,
            })

    # Se duas vigas compartilham o mesmo alinhamento continuo, divide na fronteira entre elas
    for i in range(len(vigas_geom)):
        for j in range(i + 1, len(vigas_geom)):
            v1, v2 = vigas_geom[i], vigas_geom[j]
            if v1["ang"] == v2["ang"]:
                if not (v1["t_max"] + 15.0 < v2["t_min"] or v1["t_min"] - 15.0 > v2["t_max"]):
                    if not (v1["l_max"] <= v2["l_min"] + 10.0 or v2["l_max"] <= v1["l_min"] + 10.0):
                        split_pt = 0.5 * (v1["l_txt"] + v2["l_txt"])
                        if v1["l_txt"] < v2["l_txt"]:
                            v1["l_max"] = min(v1["l_max"], split_pt)
                            v2["l_min"] = max(v2["l_min"], split_pt)
                        else:
                            v2["l_max"] = min(v2["l_max"], split_pt)
                            v1["l_min"] = max(v1["l_min"], split_pt)

    return vigas_geom


def associar_elemento_a_viga(xc, yc, ang, vigas_geom, tol_dist=90.0):
    """
    Associa uma secao 'xx/xx', bolinha '(xx)' ou texto 'VIGA INVERTIDA' a sua viga
    branca continua correspondente verificando compatibilidade estrita de angulo,
    faixa transversal [t_min, t_max] e extensao longitudinal [l_min, l_max].
    Mantem prioridade para correspondencias estritas (<= 45 cm) e faz fallback
    controlado para elementos da mesma viga com afastamento ate tol_dist ou vao continuo.
    """
    cands_estritos = []
    cands_ext = []
    for vg in vigas_geom:
        da = abs((ang - vg["ang"]) % 180.0)
        if min(da, 180.0 - da) >= 10.0:
            continue
        if vg["ang"] == 0.0:
            dt = 0.0
            if yc < vg["t_min"]:
                dt = vg["t_min"] - yc
            elif yc > vg["t_max"]:
                dt = yc - vg["t_max"]
            dl = 0.0
            if xc < vg["l_min"]:
                dl = vg["l_min"] - xc
            elif xc > vg["l_max"]:
                dl = xc - vg["l_max"]
            pos_l = xc
            t_mid = 0.5 * (vg["t_min"] + vg["t_max"])
        else:
            dt = 0.0
            if xc < vg["t_min"]:
                dt = vg["t_min"] - xc
            elif xc > vg["t_max"]:
                dt = xc - vg["t_max"]
            dl = 0.0
            if yc < vg["l_min"]:
                dl = vg["l_min"] - yc
            elif yc > vg["l_max"]:
                dl = yc - vg["l_max"]
            pos_l = yc
            t_mid = 0.5 * (vg["t_min"] + vg["t_max"])

        dist_txt = abs(pos_l - vg["l_txt"])
        if dt <= 45.0 and dl <= 45.0:
            cands_estritos.append((dt + dl * 0.5, dist_txt, vg))
        elif (dt <= tol_dist and dl <= 45.0) or (dt <= 55.0 and dl <= 600.0):
            # Evita atravessar o territorio de outra viga colinear no mesmo alinhamento
            invade_outra = False
            if dl > 45.0:
                for vg2 in vigas_geom:
                    if vg2 is vg or vg2["ang"] != vg["ang"]:
                        continue
                    t_mid2 = 0.5 * (vg2["t_min"] + vg2["t_max"])
                    if abs(t_mid - t_mid2) <= 25.0:
                        if abs(pos_l - vg2["l_txt"]) + 10.0 < dist_txt:
                            invade_outra = True
                            break
            if not invade_outra:
                cands_ext.append((dt * 1.5 + dl * 0.4, dist_txt, vg))

    if cands_estritos:
        cands_estritos.sort(key=lambda x: (x[0], x[1]))
        return cands_estritos[0][2]
    if cands_ext:
        cands_ext.sort(key=lambda x: (x[0], x[1]))
        return cands_ext[0][2]
    return None


def _box_colide_com_concreto_alheio(box, vg, lines_concreto, margem=1.0):
    """
    Verifica se o box colide com alguma linha de concreto que NAO seja uma das duas
    faces paralelas da propria viga 'vg'.
    """
    for lx1, ly1, lx2, ly2, _ in lines_concreto:
        if vg is not None:
            if vg["ang"] == 0.0 and abs(ly1 - ly2) <= 8.0:
                ym = 0.5 * (ly1 + ly2)
                if vg["t_min"] - 12.0 <= ym <= vg["t_max"] + 12.0:
                    continue
            elif vg["ang"] == 90.0 and abs(lx1 - lx2) <= 8.0:
                xm = 0.5 * (lx1 + lx2)
                if vg["t_min"] - 12.0 <= xm <= vg["t_max"] + 12.0:
                    continue
        if _segmento_colide_box(lx1, ly1, lx2, ly2, box, margem=margem):
            return True
    return False


def encontrar_posicao_livre_na_viga(
    vg, comp_l, tam_t, eh_circulo, pos_l_pref, lado_pref,
    obstaculos_boxes, lines_concreto
):
    """
    Procura uma posicao 100% livre de sobreposicao ao longo da mesma viga branca 'vg',
    testando primeiro o lado preferido e o lado oposto na mesma posicao longitudinal
    (trocar de lado na viga) e, se necessario, deslizando ao longo da extensao [l_min, l_max]
    da viga em ambos os lados.
    Retorna (x_escolhido, y_escolhido, box_escolhido) ou None.
    """
    ang = vg["ang"]
    l_min = vg["l_min"] + 8.0
    l_max = vg["l_max"] - 8.0 - (0.0 if eh_circulo else comp_l)
    if l_max < l_min:
        l_min = vg["l_min"]
        l_max = vg["l_max"]

    # Coordenadas transversais para Lado +1 (acima / esquerda) e Lado -1 (abaixo / direita)
    if eh_circulo:
        r = 0.5 * tam_t
        t_pos = vg["t_max"] + r + 2.5 if ang == 0.0 else vg["t_min"] - r - 2.5
        t_neg = vg["t_min"] - r - 2.5 if ang == 0.0 else vg["t_max"] + r + 2.5
        lados_testar = [t_pos, t_neg] if lado_pref >= 0 else [t_neg, t_pos]
    else:
        if ang == 0.0:
            t_pos = vg["t_max"] + 0.25 * tam_t + 4.0
            t_neg = vg["t_min"] - 1.15 * tam_t - 4.0
            lados_testar = [t_pos, t_neg] if lado_pref >= 0 else [t_neg, t_pos]
        else:
            t_pos = vg["t_min"] - 0.25 * tam_t - 4.0
            t_neg = vg["t_max"] + 1.15 * tam_t + 4.0
            lados_testar = [t_pos, t_neg] if lado_pref >= 0 else [t_neg, t_pos]

    # Gera candidatos longitudinais dentro da mesma viga branca:
    # 1o: posicao atual (para permitir apenas trocar de lado!)
    # 2o: deslocamentos graduais ao longo da viga com passo fino (5.0 cm)
    pos_l_clamped = max(l_min, min(l_max, pos_l_pref))
    cands_l = [pos_l_clamped]
    passo = 5.0
    for d in range(1, 120):
        for s in (1.0, -1.0):
            cl = pos_l_clamped + s * d * passo
            if l_min <= cl <= l_max:
                cands_l.append(cl)

    # Prioridade 1: testar ambos os lados na posicao longitudinal atual/proxima antes de deslizar longe
    sequencia_testes = []
    for cl in cands_l[:6]:
        for t_val in lados_testar:
            sequencia_testes.append((cl, t_val))
    for cl in cands_l[6:]:
        for t_val in lados_testar:
            sequencia_testes.append((cl, t_val))

    if eh_circulo:
        r = 0.5 * tam_t
        for cl, t_val in sequencia_testes:
            cx, cy = (cl, t_val) if ang == 0.0 else (t_val, cl)
            c_box = (cx - r, cy - r, cx + r, cy + r)
            if any(_boxes_colidem(c_box, obs, margem=2.5) for obs in obstaculos_boxes):
                continue
            if _box_colide_com_concreto_alheio(c_box, vg, lines_concreto, margem=1.0):
                continue

            # Passo 1: Prefere posicoes onde o texto futuro 'VIGA INVERTIDA xxCM' tambem caiba sem colidir
            comp_futuro = 175.0
            h_futuro = 12.0
            l_min_v = vg["l_min"] + 5.0
            l_max_v = vg["l_max"] - 5.0 - comp_futuro
            cl_f = max(l_min_v, min(l_max_v, cl - r)) if l_max_v >= l_min_v else (cl - r)
            if ang == 0.0:
                ty_f = vg["t_max"] + 5.0 if t_val > vg["t_max"] else vg["t_min"] - h_futuro - 4.0
                box_futuro = (cl_f, ty_f - h_futuro * 0.25, cl_f + comp_futuro, ty_f + h_futuro * 1.15)
            else:
                tx_f = vg["t_min"] - 5.0 if t_val < vg["t_min"] else vg["t_max"] + h_futuro + 4.0
                box_futuro = (tx_f - h_futuro * 1.15, cl_f, tx_f + h_futuro * 0.25, cl_f + comp_futuro)

            if not any(_boxes_colidem(box_futuro, obs, margem=1.5) for obs in obstaculos_boxes) and not _box_colide_com_concreto_alheio(box_futuro, vg, lines_concreto, margem=1.0):
                return (cx, cy, c_box)

        # Passo 2: Se a viga tiver outra viga transversal (ex: V509-A cruzada pela V506-A),
        # aceita a posicao limpa para o circulo da bolinha (ex: lado direito da V509-A como na Foto 2!)
        for cl, t_val in sequencia_testes:
            cx, cy = (cl, t_val) if ang == 0.0 else (t_val, cl)
            c_box = (cx - r, cy - r, cx + r, cy + r)
            if any(_boxes_colidem(c_box, obs, margem=2.5) for obs in obstaculos_boxes):
                continue
            if _box_colide_com_concreto_alheio(c_box, vg, lines_concreto, margem=1.0):
                continue
            return (cx, cy, c_box)

        return None

    for cl, t_val in sequencia_testes:
        l_min_t = vg["l_min"] + 5.0
        l_max_t = vg["l_max"] - 5.0 - comp_l
        cl_t = max(l_min_t, min(l_max_t, cl)) if l_max_t >= l_min_t else cl
        if ang == 0.0:
            cx, cy = cl_t, t_val
            c_box = (cx, cy - tam_t * 0.25, cx + comp_l, cy + tam_t * 1.15)
        else:
            cx, cy = t_val, cl_t
            c_box = (cx - tam_t * 1.15, cy, cx + tam_t * 0.25, cy + comp_l)

        # Verifica colisao com obstaculos (pilares, outros textos, outras bolinhas, etc.)
        if any(_boxes_colidem(c_box, obs, margem=2.5) for obs in obstaculos_boxes):
            continue
        # Verifica colisao com linhas de concreto perpendiculares / de outras vigas
        if _box_colide_com_concreto_alheio(c_box, vg, lines_concreto, margem=1.0):
            continue

        return (cx, cy, c_box)

    return None


def desenhar_seta_chamada_executiva(dwg, x_fim_patamar, x_joelho, y_patamar, x_seta, y_seta, linhas_221_setas=None):
    """
    Desenha a Seta de Chamada Executiva no Nivel 221 (padrao executivo da Skill):
      - Patamar horizontal passando exatamente entre o nome do pilar e a secao
      - Linha diagonal (leader) do joelho ate a borda mais proxima do pilar
      - Cabeca da seta na ponta com duas asas de 6.0 cm a 18 graus
    """
    dwg.draw.level = 221
    dwg.draw.color = -1
    dwg.draw.style = 0

    dwg.draw.Line(x_fim_patamar, y_patamar, x_joelho, y_patamar)
    if linhas_221_setas is not None:
        try:
            a1 = dwg.iterator.GetElementWritePosition()
            linhas_221_setas.append({"addr": a1, "x1": x_fim_patamar, "y1": y_patamar, "x2": x_joelho, "y2": y_patamar})
        except Exception:
            pass

    dwg.draw.Line(x_joelho, y_patamar, x_seta, y_seta)
    if linhas_221_setas is not None:
        try:
            a2 = dwg.iterator.GetElementWritePosition()
            linhas_221_setas.append({"addr": a2, "x1": x_joelho, "y1": y_patamar, "x2": x_seta, "y2": y_seta})
        except Exception:
            pass

    dx = x_joelho - x_seta
    dy = y_patamar - y_seta
    comp = math.hypot(dx, dy)
    if comp > 1.0:
        ang_base = math.atan2(dy, dx)
        comp_seta = 6.0
        abertura = math.radians(18.0)
        for sinal in (-1.0, 1.0):
            ang_asa = ang_base + sinal * abertura
            xa = x_seta + comp_seta * math.cos(ang_asa)
            ya = y_seta + comp_seta * math.sin(ang_asa)
            dwg.draw.Line(x_seta, y_seta, xa, ya)
            if linhas_221_setas is not None:
                try:
                    aw = dwg.iterator.GetElementWritePosition()
                    linhas_221_setas.append({"addr": aw, "x1": x_seta, "y1": y_seta, "x2": xa, "y2": ya})
                except Exception:
                    pass


def _ponto_saida_seta_inversao(xt, yt, comp, h, ang_txt, xa, ya):
    """
    Calcula o ponto de saida (x_joelho, y_joelho) na borda da caixa do texto
    orientada em 'ang_txt' (0°, 90° ou qualquer angulo inclinado) mais proxima
    do ponto alvo (xa, ya) na viga.
    """
    ang_n = _normalizar_angulo(ang_txt)
    if ang_n == 0.0:
        if xt > xa + 5.0:
            return (xt - 2.0, yt + 0.5 * h)
        elif xt + comp < xa - 5.0:
            return (xt + comp + 2.0, yt + 0.5 * h)
        elif yt > ya + 2.0:
            return (max(xt + 2.0, min(xt + comp - 2.0, xa)), yt - 2.0)
        else:
            return (max(xt + 2.0, min(xt + comp - 2.0, xa)), yt + h + 2.0)
    elif ang_n == 90.0:
        if yt + comp < ya - 5.0:
            return (xt - 0.5 * h, yt + comp + 2.0)
        elif yt > ya + 5.0:
            return (xt - 0.5 * h, yt - 2.0)
        else:
            x_j = (xt - h - 2.0) if (xt - 0.5 * h) >= xa else (xt + 2.0)
            y_j = max(yt + 2.0, min(yt + comp - 2.0, ya))
            return (x_j, y_j)
    else:
        rad = math.radians(ang_txt)
        ux, uy = math.cos(rad), math.sin(rad)
        nx, ny = -uy, ux
        sa = (xa - xt) * ux + (ya - yt) * uy
        qa = (xa - xt) * nx + (ya - yt) * ny
        s_clamped = max(2.0, min(max(2.0, comp - 2.0), sa))
        if sa < -5.0:
            sj, qj = -2.0, 0.5 * h
        elif sa > comp + 5.0:
            sj, qj = comp + 2.0, 0.5 * h
        elif qa < 0.5 * h:
            sj, qj = s_clamped, -2.0
        else:
            sj, qj = s_clamped, h + 2.0
        return (xt + sj * ux + qj * nx, yt + sj * uy + qj * ny)


def desenhar_seta_inversao(dwg, xt, yt, comp, h, ang_txt, xa, ya, linhas_221_setas=None):
    """
    Desenha Seta de Chamada Executiva para Inversoes de Viga no Nivel 221:
      - Suporta 0°, 90° e angulos inclinados gerais mantendo assinatura original.
      - Leader conectando da borda mais proxima do texto ao ponto alvo (xa, ya) na viga.
      - Cabeca da seta na ponta (duas asas de 6.0 cm a 18 graus) apontando para o concreto da viga invertida.
    """
    dwg.draw.level = 221
    dwg.draw.color = -1
    dwg.draw.style = 0

    start_x, start_y = _ponto_saida_seta_inversao(xt, yt, comp, h, ang_txt, xa, ya)
    dwg.draw.Line(start_x, start_y, xa, ya)
    if linhas_221_setas is not None:
        try:
            a_lin = dwg.iterator.GetElementWritePosition()
            linhas_221_setas.append({"addr": a_lin, "x1": start_x, "y1": start_y, "x2": xa, "y2": ya})
        except Exception:
            pass

    dx = start_x - xa
    dy = start_y - ya
    c = math.hypot(dx, dy)
    if c > 1.0:
        ang_base = math.atan2(dy, dx)
        comp_seta = 6.0
        abertura = math.radians(18.0)
        for sinal in (-1.0, 1.0):
            ang_asa = ang_base + sinal * abertura
            x_asa = xa + comp_seta * math.cos(ang_asa)
            y_asa = ya + comp_seta * math.sin(ang_asa)
            dwg.draw.Line(xa, ya, x_asa, y_asa)
            if linhas_221_setas is not None:
                try:
                    aw = dwg.iterator.GetElementWritePosition()
                    linhas_221_setas.append({"addr": aw, "x1": xa, "y1": ya, "x2": x_asa, "y2": y_asa})
                except Exception:
                    pass


def apagar_chamadas_antigas_do_pilar(dwg, pcx, pcy, p_box, old_box, linhas_242, linhas_221_setas, raio_busca=60.0):
    """
    Idempotencia e Limpeza Completa:
    Apaga todas as linhas nativas de chamada (Nivel 242) e o sistema completo
    de seta de chamada (Nivel 221 - patamar horizontal, leader diagonal e asas)
    associado ao pilar fisico e a posicao anterior do seu texto.
    """
    apagadas = 0

    # 1. Linhas Nivel 242 (chamada nativa do TQS)
    remover_242 = []
    for l242 in linhas_242:
        d1 = math.hypot(l242["x1"] - pcx, l242["y1"] - pcy)
        d2 = math.hypot(l242["x2"] - pcx, l242["y2"] - pcy)
        toca_poly = min(d1, d2) <= raio_busca
        toca_old = False
        if old_box is not None:
            toca_old = (
                old_box[0] - 15.0 <= l242["x1"] <= old_box[2] + 15.0
                and old_box[1] - 15.0 <= l242["y1"] <= old_box[3] + 15.0
            )
        if toca_poly or toca_old:
            try:
                dwg.edit.Erase(l242["addr"])
                apagadas += 1
            except Exception:
                pass
            remover_242.append(l242)

    for r in remover_242:
        if r in linhas_242:
            linhas_242.remove(r)

    # 2. Linhas Nivel 221 (Seta executiva: patamar + leader + asas)
    selecionadas = set()
    for i, l221 in enumerate(linhas_221_setas):
        # Toca concreto do pilar (apenas borda proxima ao poligono do pilar, sem invadir setas de vigas vizinhas)
        toca_poly = False
        if p_box is not None:
            if (p_box[0] - 4.0 <= l221["x1"] <= p_box[2] + 4.0 and p_box[1] - 4.0 <= l221["y1"] <= p_box[3] + 4.0) or \
               (p_box[0] - 4.0 <= l221["x2"] <= p_box[2] + 4.0 and p_box[1] - 4.0 <= l221["y2"] <= p_box[3] + 4.0):
                toca_poly = True
        else:
            d1 = math.hypot(l221["x1"] - pcx, l221["y1"] - pcy)
            d2 = math.hypot(l221["x2"] - pcx, l221["y2"] - pcy)
            toca_poly = min(d1, d2) <= raio_busca

        # Toca caixa do texto anterior do pilar (patamar horizontal no lugar antigo)
        toca_old = False
        if old_box is not None:
            if abs(l221["y1"] - l221["y2"]) <= 1.5:
                y_lin = 0.5 * (l221["y1"] + l221["y2"])
                if abs(y_lin - (old_box[1] - 3.0)) <= 8.0 or (old_box[1] - 10.0 <= y_lin <= old_box[3] + 5.0):
                    if max(l221["x1"], l221["x2"]) >= old_box[0] - 15.0 and min(l221["x1"], l221["x2"]) <= old_box[2] + 15.0:
                        toca_old = True
            else:
                d_old1 = math.hypot(l221["x1"] - old_box[0], l221["y1"] - old_box[1])
                d_old2 = math.hypot(l221["x2"] - old_box[0], l221["y2"] - old_box[1])
                if min(d_old1, d_old2) <= 8.0:
                    toca_old = True

        if toca_poly or toca_old:
            selecionadas.add(i)

    # Propagacao por conectividade (para pegar joelho, patamar e pontas conectadas)
    mudou = True
    while mudou:
        mudou = False
        for i, cand in enumerate(linhas_221_setas):
            if i in selecionadas:
                continue
            for sel_idx in list(selecionadas):
                sel = linhas_221_setas[sel_idx]
                d11 = math.hypot(cand["x1"] - sel["x1"], cand["y1"] - sel["y1"])
                d12 = math.hypot(cand["x1"] - sel["x2"], cand["y1"] - sel["y2"])
                d21 = math.hypot(cand["x2"] - sel["x1"], cand["y2"] - sel["y1"])
                d22 = math.hypot(cand["x2"] - sel["x2"], cand["y2"] - sel["y2"])
                if min(d11, d12, d21, d22) <= 3.0:
                    selecionadas.add(i)
                    mudou = True
                    break

    # So apaga o grupo de nivel 221 se contiver asa de seta executiva (comp ~ 6.0 cm),
    # protegendo 100% linhas primitivas de cotas apertadas no nivel 221.
    tem_asa_seta = any(
        5.2 <= math.hypot(linhas_221_setas[idx]["x2"] - linhas_221_setas[idx]["x1"],
                          linhas_221_setas[idx]["y2"] - linhas_221_setas[idx]["y1"]) <= 6.8
        for idx in selecionadas
    )
    if not tem_asa_seta:
        return apagadas

    remover_221 = []
    for idx in sorted(selecionadas, reverse=True):
        l221 = linhas_221_setas[idx]
        try:
            dwg.edit.Erase(l221["addr"])
            apagadas += 1
        except Exception:
            pass
        remover_221.append(l221)

    for r in remover_221:
        if r in linhas_221_setas:
            linhas_221_setas.remove(r)

    return apagadas


def limpar_chamadas_orfas_221(dwg, linhas_221_setas, pilares_group):
    """
    Preserva todas as linhas horizontais de cotas no Nivel 221.
    """
    return 0


def _dist_ponto_a_box(px, py, box):
    dx = max(0.0, box[0] - px, px - box[2])
    dy = max(0.0, box[1] - py, py - box[3])
    return math.hypot(dx, dy)


def _box_exato_de_texto_dict(tx):
    if "x2" in tx and "y2" in tx:
        return _bbox_texto_exato(tx["x1"], tx["y1"], tx["x2"], tx["y2"], tx["h"])
    if "txt" in tx and "h" in tx and "ang" in tx:
        return _bbox_texto(tx["x1"], tx["y1"], tx["h"], tx["ang"], tx["txt"])
    return tx["box"]


def _encontrar_seta_de_inversao(vi, linhas_221_setas, tol_caixa=5.5, texts_raw=None):
    """
    Identifica de forma cirurgica o conjunto (haste + 2 asas) no Nivel 221 pertencente
    ao texto 'vi':
      - Avalia cada haste individualmente junto ao seu par de asas alinhado (~18°), sem
        descartar setas cujas pontas toquem concreto proximo (< 3 cm) de outra seta.
      - Exige que a cauda saia da borda de 'vi' (<= tol_caixa, padrao 5.5 cm), nao possua
        patamar de pilar conectado e nao esteja mais proxima de outro texto em texts_raw.
    Retorna (set_de_indices, (x_tip, y_tip) ou None).
    """
    if not linhas_221_setas:
        return set(), None

    vi_box = _box_exato_de_texto_dict(vi)
    vi_addr = vi.get("addr")
    outros_boxes = []
    if texts_raw:
        for tO in texts_raw:
            if tO is vi or (vi_addr is not None and tO.get("addr") == vi_addr):
                continue
            outros_boxes.append(_box_exato_de_texto_dict(tO))

    asas_idx = []
    hastes_idx = []
    for idx, ln in enumerate(linhas_221_setas):
        L_seg = math.hypot(ln["x2"] - ln["x1"], ln["y2"] - ln["y1"])
        if 5.2 <= L_seg <= 6.8:
            asas_idx.append(idx)
        elif L_seg > 3.0:
            hastes_idx.append(idx)

    if len(asas_idx) < 2 or not hastes_idx:
        return set(), None

    indices_escolhidos = set()
    tip_escolhido = None
    melhor_d_tail = float("inf")

    for h_idx in hastes_idx:
        lh = linhas_221_setas[h_idx]
        for tip_x, tip_y, tail_x, tail_y in (
            (lh["x1"], lh["y1"], lh["x2"], lh["y2"]),
            (lh["x2"], lh["y2"], lh["x1"], lh["y1"]),
        ):
            if math.hypot(tail_x - tip_x, tail_y - tip_y) <= 3.0:
                continue

            d_meu = _dist_ponto_a_box(tail_x, tail_y, vi_box)
            if d_meu > tol_caixa or d_meu >= melhor_d_tail:
                continue

            # Nunca rouba seta cuja cauda esteja mais proxima da caixa de outro texto
            if any(_dist_ponto_a_box(tail_x, tail_y, obx) + 0.5 < d_meu for obx in outros_boxes):
                continue

            # Rejeita se houver patamar de pilar (outra haste conectada na cauda)
            tem_patamar_cauda = False
            for o_idx in hastes_idx:
                if o_idx == h_idx:
                    continue
                lo = linhas_221_setas[o_idx]
                if min(math.hypot(tail_x - lo["x1"], tail_y - lo["y1"]),
                       math.hypot(tail_x - lo["x2"], tail_y - lo["y2"])) <= 2.5:
                    tem_patamar_cauda = True
                    break
            if tem_patamar_cauda:
                continue

            # Procura as 2 asas conectadas em (tip_x, tip_y) e alinhadas com a direcao da haste
            ang_haste = math.atan2(tail_y - tip_y, tail_x - tip_x)
            asas_alinhadas = []
            for w_idx in asas_idx:
                lw = linhas_221_setas[w_idx]
                d1 = math.hypot(lw["x1"] - tip_x, lw["y1"] - tip_y)
                d2 = math.hypot(lw["x2"] - tip_x, lw["y2"] - tip_y)
                if min(d1, d2) > 1.8:
                    continue
                wx_far, wy_far = (lw["x2"], lw["y2"]) if d1 <= d2 else (lw["x1"], lw["y1"])
                ang_w = math.atan2(wy_far - tip_y, wx_far - tip_x)
                diff_ang = abs((ang_w - ang_haste + math.pi) % (2.0 * math.pi) - math.pi)
                if diff_ang <= math.radians(42.0):
                    asas_alinhadas.append((abs(diff_ang - math.radians(18.0)), w_idx))

            if len(asas_alinhadas) >= 2:
                asas_alinhadas.sort(key=lambda it: it[0])
                melhor_d_tail = d_meu
                indices_escolhidos = {h_idx, asas_alinhadas[0][1], asas_alinhadas[1][1]}
                tip_escolhido = (tip_x, tip_y)

    return indices_escolhidos, tip_escolhido


def apagar_chamadas_antigas_de_inversao(dwg, vi, linhas_221_setas, raio_busca=5.5, texts_raw=None):
    """
    Apaga linhas de chamada executiva (nivel 221) associadas ao texto de inversao 'vi'
    que esta sendo movido, evitando deixar linhas orfas/fantasmas no desenho e sem
    tocar em cotas, setas de pilares ou setas de textos vizinhos.
    """
    if not linhas_221_setas:
        return 0
    tol = min(float(raio_busca), 5.5) if raio_busca is not None else 5.5
    selecionadas, _ = _encontrar_seta_de_inversao(vi, linhas_221_setas, tol_caixa=tol, texts_raw=texts_raw)
    if not selecionadas:
        return 0

    apagadas = 0
    for idx in sorted(selecionadas, reverse=True):
        try:
            dwg.edit.Erase(linhas_221_setas[idx]["addr"])
            apagadas += 1
        except Exception:
            pass
    linhas_221_setas[:] = [l for i, l in enumerate(linhas_221_setas) if i not in selecionadas]
    return apagadas


def _construir_pilares_group(texts_raw, poly_pilares):
    """
    Pareia pilares (Nivel 9) com poligonos fisicos e secoes (Nivel 12):
      - Ordena pilares de cima para baixo (y decrescente) para evitar troca de secoes em juntas de dilatacao.
      - Apenas pareia secoes p12 que estejam geometricamente abaixo de p9 (dy <= 2.0).
      - Padroniza dx_sec = 0.0 e dy_sec = -18.0 para garantir que a secao nunca fique sobreposta ou acima do pilar.
    """
    p9_list = [tx for tx in texts_raw if tx["level"] == 9 and tx["txt"].upper().startswith("P")]
    p12_list = [tx for tx in texts_raw if tx["level"] == 12 and "/" in tx["txt"]]
    p9_list.sort(key=lambda p: -p["y1"])

    poly_usados = set()
    pilares_com_cands = []
    for p9 in p9_list:
        cands_p = []
        for idx_pb, pb in enumerate(poly_pilares):
            b_pb = pb["box"]
            dx_b = max(0.0, b_pb[0] - p9["x1"], p9["x1"] - b_pb[2])
            dy_b = max(0.0, b_pb[1] - p9["y1"], p9["y1"] - b_pb[3])
            dp = math.hypot(dx_b, dy_b) + 0.05 * math.hypot(p9["x1"] - pb["pcx"], p9["y1"] - pb["pcy"])
            cands_p.append((dp, idx_pb, pb))
        cands_p.sort(key=lambda x: x[0])
        pilares_com_cands.append((p9, cands_p))

    pilares_com_cands.sort(key=lambda x: x[1][0][0] if x[1] else float("inf"))
    map_p9_poly = {}
    for p9, cands_p in pilares_com_cands:
        for dp, idx_pb, pb in cands_p:
            if idx_pb not in poly_usados:
                poly_usados.add(idx_pb)
                map_p9_poly[id(p9)] = pb
                break
        if id(p9) not in map_p9_poly and cands_p:
            map_p9_poly[id(p9)] = cands_p[0][2]

    # Passada de Otimizacao e Desentrelacamento Topologico (2-opt uncrossing):
    # Previne que pilares vizinhos (ex: juntas de dilatacao como P15/P16, P59/P61, etc.)
    # tenham seus poligonos fisicos invertidos por proximidade euclidiana gananciosa.
    def _extrair_num_pilar(txt):
        m = re.search(r'\d+', txt)
        return int(m.group()) if m else 0

    improved = True
    pass_num = 0
    while improved and pass_num < 10:
        improved = False
        pass_num += 1
        for i in range(len(p9_list)):
            pA = p9_list[i]
            if id(pA) not in map_p9_poly:
                continue
            pbA = map_p9_poly[id(pA)]
            for j in range(i + 1, len(p9_list)):
                pB = p9_list[j]
                if id(pB) not in map_p9_poly:
                    continue
                pbB = map_p9_poly[id(pB)]

                dist_p = math.hypot(pA["x1"] - pB["x1"], pA["y1"] - pB["y1"])
                dist_pb = math.hypot(pbA["pcx"] - pbB["pcx"], pbA["pcy"] - pbB["pcy"])
                if dist_p > 120.0 or dist_pb > 120.0:
                    continue

                cur_cost = math.hypot(pA["x1"] - pbA["pcx"], pA["y1"] - pbA["pcy"]) + \
                           math.hypot(pB["x1"] - pbB["pcx"], pB["y1"] - pbB["pcy"])
                swap_cost = math.hypot(pA["x1"] - pbB["pcx"], pA["y1"] - pbB["pcy"]) + \
                            math.hypot(pB["x1"] - pbA["pcx"], pB["y1"] - pbA["pcy"])

                # 1. Cruzamento topologico em X
                cross_x = False
                dx_p = pA["x1"] - pB["x1"]
                dx_pb = pbA["pcx"] - pbB["pcx"]
                if abs(dx_p) > 5.0 and abs(dx_pb) > 5.0 and (dx_p * dx_pb < 0):
                    cross_x = True

                # 2. Cruzamento topologico em Y
                cross_y = False
                dy_p = pA["y1"] - pB["y1"]
                dy_pb = pbA["pcy"] - pbB["pcy"]
                if abs(dy_p) > 5.0 and abs(dy_pb) > 5.0 and (dy_p * dy_pb < 0):
                    cross_y = True

                # 3. Cruzamento de ordem numerica (ex: P15 e P16 em junta)
                numA = _extrair_num_pilar(pA["txt"])
                numB = _extrair_num_pilar(pB["txt"])
                num_cross = False
                if numA != numB and (abs(dx_pb) > 5.0 or abs(dy_pb) > 5.0):
                    if abs(dx_pb) >= abs(dy_pb):
                        if (numA < numB and pbA["pcx"] > pbB["pcx"]) or (numA > numB and pbA["pcx"] < pbB["pcx"]):
                            num_cross = True
                    else:
                        if (numA < numB and pbA["pcy"] < pbB["pcy"]) or (numA > numB and pbA["pcy"] > pbB["pcy"]):
                            num_cross = True

                should_swap = False
                if cross_x or cross_y or num_cross:
                    should_swap = True
                elif swap_cost < cur_cost - 1e-4:
                    should_swap = True

                if should_swap:
                    if swap_cost < cur_cost + 25.0:
                        map_p9_poly[id(pA)] = pbB
                        map_p9_poly[id(pB)] = pbA
                        improved = True

    pilares_group = []
    used_12_idx = set()
    for p9 in p9_list:
        best_12 = None
        min_score = float("inf")
        for i, p12 in enumerate(p12_list):
            if i in used_12_idx:
                continue
            d = math.hypot(p9["x1"] - p12["x1"], p9["y1"] - p12["y1"])
            dy = p12["y1"] - p9["y1"]
            dx = p12["x1"] - p9["x1"]
            # Secao de pilar deve ficar abaixo do nome do pilar (nunca acima!)
            if dy > 2.0:
                continue
            score = d + abs(dx) * 0.5
            if d <= 55.0 and score < min_score:
                min_score = score
                best_12 = (i, p12)

        p12_obj = None
        if best_12 is not None:
            used_12_idx.add(best_12[0])
            p12_obj = best_12[1]

        bp9 = p9["box"]
        # Padrao executivo: secao do pilar alinhada horizontalmente e abaixo do nome
        dx_sec = 0.0
        dy_sec = -16.0 if p12_obj else 0.0
        if p12_obj:
            bp12_atual = p12_obj["box"]
        else:
            bp12_atual = bp9
        bconj_atual = (
            min(bp9[0], bp12_atual[0]), min(bp9[1], bp12_atual[1]),
            max(bp9[2], bp12_atual[2]), max(bp9[3], bp12_atual[3])
        )
        if p12_obj:
            bp12_pad = _bbox_texto(p9["x1"] + dx_sec, p9["y1"] + dy_sec, p12_obj["h"], p9["ang"], p12_obj["txt"])
        else:
            bp12_pad = bp9
        bconj_pad = (
            min(bp9[0], bp12_pad[0]), min(bp9[1], bp12_pad[1]),
            max(bp9[2], bp12_pad[2]), max(bp9[3], bp12_pad[3])
        )
        p_poly = map_p9_poly.get(id(p9))

        pilares_group.append({
            "p9": p9,
            "p12": p12_obj,
            "dx_sec": dx_sec,
            "dy_sec": dy_sec,
            "box": bconj_atual,
            "larg_conj": bconj_pad[2] - bconj_pad[0],
            "alt_conj": bconj_pad[3] - bconj_pad[1],
            "p_poly": p_poly,
        })

    return pilares_group


def _limite_desloc_pilar():
    """
    Limite maximo (cm) de deslocamento dos identificadores de pilar, definido pela
    variavel de ambiente G3_MAX_DESLOC_PILAR (usada pelo botao 'Inverter e Organizar').
    """
    val = os.environ.get("G3_MAX_DESLOC_PILAR", "").strip()
    if not val:
        return None
    try:
        return max(0.0, float(val))
    except ValueError:
        return None


def reposicionar_pilares_conflitantes(
    dwg, pilares_group, poly_pilares, lines_concreto, obstaculos_fixos,
    todos_obstaculos_cotas, texts_raw, linhas_242, linhas_221_setas,
    forcar_ciclo_se_deslocado=False, apenas_grupos_ids=None
):
    """
    Reorganiza pilares com sobreposicao em 2 estagios inteligentes:
      1. Estagio 1 (Micro-Deslocamento sem Seta): tenta afastar apenas alguns cm (0 a 30 cm)
         mantendo o texto colado ao pilar sem precisar de seta de chamada.
      2. Estagio 2 (Seta Executiva): somente se nao couber perto do pilar, afasta para
         uma regiao livre (40 a 150 cm) e desenha a Seta Executiva no Nivel 221.
    """
    total_ajustes = 0
    boxes_pilares_poly = [pb["box"] for pb in poly_pilares]

    # Mapeia pilares gemeos (juntas de dilatacao com distancia <= 45 cm entre poligonos)
    map_twins = {}
    for i in range(len(pilares_group)):
        pA = pilares_group[i]
        if not pA.get("p_poly"):
            continue
        for j in range(i + 1, len(pilares_group)):
            pB = pilares_group[j]
            if not pB.get("p_poly"):
                continue
            d_poly = math.hypot(pA["p_poly"]["pcx"] - pB["p_poly"]["pcx"], pA["p_poly"]["pcy"] - pB["p_poly"]["pcy"])
            if d_poly <= 45.0:
                map_twins[id(pA)] = pB
                map_twins[id(pB)] = pA

    for p_grp in pilares_group:
        if apenas_grupos_ids is not None and id(p_grp) not in apenas_grupos_ids:
            continue

        p9 = p_grp["p9"]
        p12 = p_grp["p12"]
        p_poly = p_grp["p_poly"]
        b_conj = p_grp["box"]
        larg_conj = p_grp["larg_conj"]
        alt_conj = p_grp["alt_conj"]
        pcx = p_poly["pcx"] if p_poly else p9["x1"]
        pcy = p_poly["pcy"] if p_poly else p9["y1"]
        p_box = p_poly["box"] if p_poly else (pcx - 12.5, pcy - 12.5, pcx + 12.5, pcy + 12.5)

        tw = map_twins.get(id(p_grp))
        dx_gem = (pcx - tw["p_poly"]["pcx"]) if tw else 0.0
        dy_gem = (pcy - tw["p_poly"]["pcy"]) if tw else 0.0
        mid_x = 0.5 * (pcx + tw["p_poly"]["pcx"]) if tw else pcx
        mid_y = 0.5 * (pcy + tw["p_poly"]["pcy"]) if tw else pcy

        addr_p12 = p12["addr"] if p12 else -1
        obstaculos_pilar = (
            list(boxes_pilares_poly)
            + list(obstaculos_fixos)
            + list(todos_obstaculos_cotas)
            + [tx["box"] for tx in texts_raw if tx["addr"] not in (p9["addr"], addr_p12)]
        )

        colide = False
        # Se no desenho atual a secao p12 estiver sobreposta ao nome p9 (ou acima dele):
        if p12 and p12["y1"] >= p9["y1"] - 8.0:
            colide = True

        # Se for pilar de junta de dilatacao e o texto atual estiver invadindo o lado do pilar irmao:
        if tw:
            if abs(dx_gem) >= abs(dy_gem):
                if dx_gem < 0 and p9["x1"] > mid_x + 5.0:
                    colide = True
                elif dx_gem > 0 and (p9["x1"] + larg_conj) < mid_x - 5.0:
                    colide = True
            else:
                if dy_gem < 0 and p9["y1"] > mid_y + 5.0:
                    colide = True
                elif dy_gem > 0 and p9["y1"] < mid_y - 5.0:
                    colide = True

        if not colide:
            for obs in obstaculos_pilar:
                if _boxes_colidem(b_conj, obs, margem=0.5):
                    colide = True
                    break

        if not colide:
            for lx1, ly1, lx2, ly2, _ in lines_concreto:
                if _segmento_colide_box(lx1, ly1, lx2, ly2, b_conj, margem=0.5):
                    colide = True
                    break

        if not colide:
            for p_outro in pilares_group:
                if p_outro is not p_grp and _boxes_colidem(b_conj, p_outro["box"], margem=0.5):
                    colide = True
                    break

        colisoes_iniciais = [obs for obs in obstaculos_pilar if _boxes_colidem(b_conj, obs, margem=0.5)]

        # Verifica se o pilar tem uma seta de chamada (leader line) conectada
        tem_seta = False
        setas_do_pilar = []
        for l in linhas_221_setas + linhas_242:
            d1_9 = math.hypot(l["x1"] - p9["x1"], l["y1"] - p9["y1"])
            d2_9 = math.hypot(l["x2"] - p9["x1"], l["y2"] - p9["y1"])
            d1_12 = math.hypot(l["x1"] - p12["x1"], l["y1"] - p12["y1"]) if p12 else float("inf")
            d2_12 = math.hypot(l["x2"] - p12["x1"], l["y2"] - p12["y1"]) if p12 else float("inf")
            if min(d1_9, d2_9, d1_12, d2_12) <= 35.0:
                tem_seta = True
                setas_do_pilar.append(l)

        # Se o texto em si nao colide, mas a SETA dele colide com algum outro texto/obstaculo:
        if not colide and tem_seta:
            for l in setas_do_pilar:
                lx1, ly1, lx2, ly2 = l["x1"], l["y1"], l["x2"], l["y2"]
                for obs in obstaculos_pilar:
                    if p_box and (p_box[0] - 2.0 <= 0.5 * (obs[0] + obs[2]) <= p_box[2] + 2.0) and (p_box[1] - 2.0 <= 0.5 * (obs[1] + obs[3]) <= p_box[3] + 2.0):
                        continue
                    if _segmento_colide_box(lx1, ly1, lx2, ly2, obs, margem=0.5):
                        colide = True
                        break
                if colide:
                    break
                for p_outro in pilares_group:
                    if p_outro is not p_grp and _segmento_colide_box(lx1, ly1, lx2, ly2, p_outro["box"], margem=0.5):
                        colide = True
                        break
                if colide:
                    break

        # Regra de ouro: so move se colidir, ou se forcar ciclo quando ja deslocado
        if not colide:
            if not (forcar_ciclo_se_deslocado and tem_seta):
                continue

        # Prioriza posicoes EM BAIXO (270) respeitando o territorio de cada pilar da junta
        direcoes_base = []
        direcoes_base.append((270.0, lambda r: (pcx - 0.5 * larg_conj, pcy - r - alt_conj - 5.0)))
        if tw and abs(dx_gem) >= abs(dy_gem):
            if dx_gem < 0:
                # Pilar da esquerda: movimentos para esquerda e baixo-esquerda
                direcoes_base.append((225.0, lambda r: (pcx - r - larg_conj, pcy - r * 0.7 - alt_conj)))
                direcoes_base.append((180.0, lambda r: (pcx - r - larg_conj - 5.0, pcy - 0.5 * alt_conj)))
                direcoes_base.append((135.0, lambda r: (pcx - r - larg_conj, pcy + r * 0.7)))
                direcoes_base.append((90.0, lambda r: (pcx - 0.5 * larg_conj, pcy + r + 5.0)))
            else:
                # Pilar da direita: movimentos para direita e baixo-direita
                direcoes_base.append((315.0, lambda r: (pcx + r, pcy - r * 0.7 - alt_conj)))
                direcoes_base.append((0.0, lambda r: (pcx + r + 5.0, pcy - 0.5 * alt_conj)))
                direcoes_base.append((45.0, lambda r: (pcx + r, pcy + r * 0.7)))
                direcoes_base.append((90.0, lambda r: (pcx - 0.5 * larg_conj, pcy + r + 5.0)))
        elif tw and abs(dy_gem) > abs(dx_gem):
            if dy_gem < 0:
                # Pilar de baixo: movimentos para baixo
                direcoes_base.append((315.0, lambda r: (pcx + r, pcy - r * 0.7 - alt_conj)))
                direcoes_base.append((225.0, lambda r: (pcx - r - larg_conj, pcy - r * 0.7 - alt_conj)))
                direcoes_base.append((0.0, lambda r: (pcx + r + 5.0, pcy - 0.5 * alt_conj)))
                direcoes_base.append((180.0, lambda r: (pcx - r - larg_conj - 5.0, pcy - 0.5 * alt_conj)))
            else:
                # Pilar de cima: movimentos para cima
                direcoes_base.append((90.0, lambda r: (pcx - 0.5 * larg_conj, pcy + r + 5.0)))
                direcoes_base.append((45.0, lambda r: (pcx + r, pcy + r * 0.7)))
                direcoes_base.append((135.0, lambda r: (pcx - r - larg_conj, pcy + r * 0.7)))
                direcoes_base.append((0.0, lambda r: (pcx + r + 5.0, pcy - 0.5 * alt_conj)))
                direcoes_base.append((180.0, lambda r: (pcx - r - larg_conj - 5.0, pcy - 0.5 * alt_conj)))
        else:
            direcoes_base = [
                (270.0, lambda r: (pcx - 0.5 * larg_conj, pcy - r - alt_conj - 5.0)),
                (315.0, lambda r: (pcx + r, pcy - r * 0.7 - alt_conj)),
                (225.0, lambda r: (pcx - r - larg_conj, pcy - r * 0.7 - alt_conj)),
                (0.0, lambda r: (pcx + r + 5.0, pcy - 0.5 * alt_conj)),
                (180.0, lambda r: (pcx - r - larg_conj - 5.0, pcy - 0.5 * alt_conj)),
                (45.0, lambda r: (pcx + r, pcy + r * 0.7)),
                (135.0, lambda r: (pcx - r - larg_conj, pcy + r * 0.7)),
                (90.0, lambda r: (pcx - 0.5 * larg_conj, pcy + r + 5.0)),
            ]

        cur_x, cur_y = p9["x1"], p9["y1"]
        if forcar_ciclo_se_deslocado and tem_seta and not colide:
            cur_ang = math.atan2(cur_y - pcy, cur_x - pcx) * 180.0 / math.pi
            if cur_ang < 0.0:
                cur_ang += 360.0
            direcoes_ord = sorted(direcoes_base, key=lambda d: (d[0] - cur_ang - 20.0) % 360.0)
            pular_proximas = True
        else:
            direcoes_ord = list(direcoes_base)
            pular_proximas = False

        escolhido = None
        precisa_seta_pilar = False

        lim_desloc = _limite_desloc_pilar()
        if lim_desloc is not None:
            if not colide:
                continue
            pular_proximas = False
        lim1 = 5.0 if lim_desloc is not None else 10.0
        lim_r_max = 75.0 if lim_desloc is None else max(25.0, lim_desloc)

        # ESTAGIO 1: Micro-deslocamentos sutis muito proximos ao pilar (SEM SETA, limite estrito de 5 cm no Inverter e Organizar)
        if not pular_proximas:
            offsets_curtos = []
            passos_s = [0.0] + [s * d for d in (1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0) if d <= lim1 for s in (-1.0, 1.0)]
            for dx_s in passos_s:
                for dy_s in passos_s:
                    d_hyp = math.hypot(dx_s, dy_s)
                    if d_hyp <= lim1:
                        offsets_curtos.append((d_hyp, cur_x + dx_s, cur_y + dy_s))
            offsets_curtos.sort(key=lambda it: it[0])
            candidatos_curtos = [(cx, cy) for _, cx, cy in offsets_curtos]
            for _, fpos in direcoes_ord:
                for r_curto in (3.0, 5.0, 7.0, 10.0):
                    pos_c = fpos(r_curto)
                    if math.hypot(pos_c[0] - cur_x, pos_c[1] - cur_y) <= lim1:
                        candidatos_curtos.append(pos_c)

            for cand_x, cand_y in candidatos_curtos:
                # Regra dos 5 cm / 10 cm: acima disso, vai para o estagio 2 com seta
                if math.hypot(cand_x - cur_x, cand_y - cur_y) > lim1:
                    continue

                cb9 = _bbox_texto(cand_x, cand_y, p9["h"], p9["ang"], p9["txt"])
                cb12 = _bbox_texto(
                    cand_x + p_grp["dx_sec"], cand_y + p_grp["dy_sec"],
                    p12["h"] if p12 else 12.0, p9["ang"], p12["txt"] if p12 else ""
                )
                c_conj = (min(cb9[0], cb12[0]), min(cb9[1], cb12[1]), max(cb9[2], cb12[2]), max(cb9[3], cb12[3]))

                # Precisa continuar proximo da caixa fisica do pilar (<= 10 cm) para dispensar seta
                dx_pb = max(0.0, p_box[0] - c_conj[2], c_conj[0] - p_box[2])
                dy_pb = max(0.0, p_box[1] - c_conj[3], c_conj[1] - p_box[3])
                if math.hypot(dx_pb, dy_pb) > 10.0:
                    continue

                if tw and abs(dx_gem) >= abs(dy_gem):
                    if dx_gem < 0 and (cand_x + 0.5 * larg_conj > mid_x):
                        continue
                    if dx_gem > 0 and (cand_x + 0.5 * larg_conj < mid_x):
                        continue
                elif tw and abs(dy_gem) > abs(dx_gem):
                    if dy_gem < 0 and (c_conj[3] > mid_y + 2.0):
                        continue
                    if dy_gem > 0 and (c_conj[1] < mid_y - 2.0):
                        continue

                if any(_boxes_colidem(c_conj, p_outro["box"], margem=2.0) for p_outro in pilares_group if p_outro is not p_grp):
                    continue
                if any(_boxes_colidem(c_conj, obs_p, margem=2.0) for obs_p in obstaculos_pilar):
                    continue

                corte_concreto = False
                for lx1, ly1, lx2, ly2, _ in lines_concreto:
                    if _segmento_colide_box(lx1, ly1, lx2, ly2, c_conj, margem=0.5):
                        corte_concreto = True
                        break
                if corte_concreto:
                    continue

                escolhido = (cand_x, cand_y, c_conj)
                precisa_seta_pilar = False
                break

        # ESTAGIO 2: Se nao resolveu dentro de 5 cm (ex: pilares gemeos P55/P57 ou P56/P58 sobrepostos),
        # busca vaga livre proxima ao proprio pilar COM SETA EXECUTIVA (limitado a lim_r_max)
        if escolhido is None:
            for _, fpos in direcoes_ord:
                for r in [rv for rv in (15.0, 25.0, 40.0, 60.0, 75.0, 100.0, 125.0, 150.0) if rv <= lim_r_max]:
                    cand_x, cand_y = fpos(r)
                    if pular_proximas and math.hypot(cand_x - cur_x, cand_y - cur_y) < 15.0:
                        continue

                    # Restricao estrita de territorio para pilares gemeos (nunca invade o lado oposto da junta)
                    if tw and abs(dx_gem) >= abs(dy_gem):
                        if dx_gem < 0 and (cand_x + 0.5 * larg_conj > mid_x):
                            continue
                        if dx_gem > 0 and (cand_x + 0.5 * larg_conj < mid_x):
                            continue
                    elif tw and abs(dy_gem) > abs(dx_gem):
                        if dy_gem < 0 and (cand_y > mid_y):
                            continue
                        if dy_gem > 0 and (cand_y < mid_y):
                            continue

                    cb9 = _bbox_texto(cand_x, cand_y, p9["h"], p9["ang"], p9["txt"])
                    cb12 = _bbox_texto(
                        cand_x + p_grp["dx_sec"], cand_y + p_grp["dy_sec"],
                        p12["h"] if p12 else 12.0, p9["ang"], p12["txt"] if p12 else ""
                    )
                    c_conj = (min(cb9[0], cb12[0]), min(cb9[1], cb12[1]), max(cb9[2], cb12[2]), max(cb9[3], cb12[3]))

                    if any(_boxes_colidem(c_conj, p_outro["box"], margem=5.0) for p_outro in pilares_group if p_outro is not p_grp):
                        continue
                    if any(_boxes_colidem(c_conj, obs_p, margem=5.0) for obs_p in obstaculos_pilar):
                        continue

                    corte_concreto = False
                    for lx1, ly1, lx2, ly2, _ in lines_concreto:
                        if _segmento_colide_box(lx1, ly1, lx2, ly2, c_conj, margem=1.0):
                            corte_concreto = True
                            break
                    if corte_concreto:
                        continue

                    # Calcula geometria da seta para validar se a linha nao corta textos/obstaculos
                    y_pat = (cand_y + p_grp["dy_sec"] - 3.0) if p12 else (cand_y - 3.0)
                    if cand_x >= pcx:
                        x_jlh = cand_x - 3.0
                        x_fp = cand_x + larg_conj + 2.0
                        x_st = min(p_box[2], max(p_box[0] + 5.0, pcx + 3.0))
                        y_st = p_box[1] if y_pat < pcy else p_box[3]
                    else:
                        x_jlh = cand_x + larg_conj + 3.0
                        x_fp = cand_x - 2.0
                        x_st = max(p_box[0], min(p_box[2] - 5.0, pcx - 3.0))
                        y_st = p_box[1] if y_pat < pcy else p_box[3]

                    dist_s = math.hypot(x_jlh - x_st, y_pat - y_st)
                    if dist_s >= 8.0:
                        corta_seta = False
                        for obs_p in obstaculos_pilar:
                            if p_box and (p_box[0] - 2.0 <= 0.5 * (obs_p[0] + obs_p[2]) <= p_box[2] + 2.0) and (p_box[1] - 2.0 <= 0.5 * (obs_p[1] + obs_p[3]) <= p_box[3] + 2.0):
                                continue
                            if _segmento_colide_box(x_jlh, y_pat, x_st, y_st, obs_p, margem=0.5) or \
                               _segmento_colide_box(x_fp, y_pat, x_jlh, y_pat, obs_p, margem=0.5):
                                corta_seta = True
                                break
                        if corta_seta:
                            continue
                        for p_outro in pilares_group:
                            if p_outro is not p_grp and (
                                _segmento_colide_box(x_jlh, y_pat, x_st, y_st, p_outro["box"], margem=0.5) or
                                _segmento_colide_box(x_fp, y_pat, x_jlh, y_pat, p_outro["box"], margem=0.5)
                            ):
                                corta_seta = True
                                break
                        if corta_seta:
                            continue

                    escolhido = (cand_x, cand_y, c_conj)
                    precisa_seta_pilar = True
                    break
                if escolhido is not None:
                    break

        # Se for pilar de junta e nao achou vaga em r <= lim_r_max apenas por causa de um rotulo de laje (L... / h=...),
        # tenta afastar levemente o rotulo da laje (25..32 cm) para abrir a vaga colada ao pilar!
        if escolhido is None:
            for _, fpos in direcoes_ord:
                for r in (15.0, 25.0, 35.0, 45.0):
                    cand_x, cand_y = fpos(r)
                    if tw and abs(dx_gem) >= abs(dy_gem):
                        if (dx_gem < 0 and cand_x + 0.5 * larg_conj > mid_x) or (dx_gem > 0 and cand_x + 0.5 * larg_conj < mid_x):
                            continue
                    elif tw and abs(dy_gem) > abs(dx_gem):
                        if (dy_gem < 0 and cand_y > mid_y) or (dy_gem > 0 and cand_y < mid_y):
                            continue
                    cb9 = _bbox_texto(cand_x, cand_y, p9["h"], p9["ang"], p9["txt"])
                    cb12 = _bbox_texto(
                        cand_x + p_grp["dx_sec"], cand_y + p_grp["dy_sec"],
                        p12["h"] if p12 else 12.0, p9["ang"], p12["txt"] if p12 else ""
                    )
                    c_conj = (min(cb9[0], cb12[0]), min(cb9[1], cb12[1]), max(cb9[2], cb12[2]), max(cb9[3], cb12[3]))
                    if any(_boxes_colidem(c_conj, p_outro["box"], margem=3.0) for p_outro in pilares_group if p_outro is not p_grp):
                        continue
                    if any(_boxes_colidem(c_conj, bp, margem=2.0) for bp in boxes_pilares_poly):
                        continue
                    if any(_segmento_colide_box(lx1, ly1, lx2, ly2, c_conj, margem=0.5) for lx1, ly1, lx2, ly2, _ in lines_concreto):
                        continue
                    tx_col = [
                        tx for tx in texts_raw
                        if tx["addr"] not in (p9["addr"], addr_p12) and _boxes_colidem(c_conj, tx["box"], margem=3.0)
                    ]
                    if not tx_col or any(tx["level"] not in (10, 13) for tx in tx_col):
                        continue
                    # Coleta o par completo da laje (L... + h=...)
                    laje_grp = list(tx_col)
                    for tx in texts_raw:
                        if tx not in laje_grp and tx["level"] in (10, 13):
                            if any(abs(tx["x1"] - tl["x1"]) <= 8.0 and abs(tx["y1"] - tl["y1"]) <= 30.0 for tl in tx_col):
                                laje_grp.append(tx)
                    moveu_laje = False
                    for dy_lj in (28.0, 34.0, -28.0, -34.0):
                        novos_lj = [(tl, (tl["box"][0], tl["box"][1] + dy_lj, tl["box"][2], tl["box"][3] + dy_lj)) for tl in laje_grp]
                        if any(_boxes_colidem(c_conj, nb, margem=2.0) for _, nb in novos_lj):
                            continue
                        if any(
                            _boxes_colidem(nb, tx["box"], margem=1.5)
                            for _, nb in novos_lj
                            for tx in texts_raw
                            if tx not in laje_grp and tx["addr"] not in (p9["addr"], addr_p12)
                        ):
                            continue
                        if any(_boxes_colidem(nb, bp, margem=1.5) for _, nb in novos_lj for bp in boxes_pilares_poly):
                            continue
                        if any(
                            _segmento_colide_box(lx1, ly1, lx2, ly2, nb, margem=0.5)
                            for _, nb in novos_lj
                            for lx1, ly1, lx2, ly2, _ in lines_concreto
                        ):
                            continue
                        for tl, nb in novos_lj:
                            dwg.edit.Move(tl["addr"], 0.0, dy_lj)
                            tl["y1"] += dy_lj
                            tl["y2"] += dy_lj
                            tl["yc"] += dy_lj
                            tl["box"] = nb
                            if "rbox" in tl:
                                tl["rbox"] = (tl["rbox"][0], tl["rbox"][1] + dy_lj, tl["rbox"][2], tl["rbox"][3] + dy_lj)
                        obstaculos_pilar = (
                            list(boxes_pilares_poly)
                            + list(obstaculos_fixos)
                            + list(todos_obstaculos_cotas)
                            + [tx["box"] for tx in texts_raw if tx["addr"] not in (p9["addr"], addr_p12)]
                        )
                        escolhido = (cand_x, cand_y, c_conj)
                        precisa_seta_pilar = True
                        moveu_laje = True
                        break
                    if moveu_laje:
                        break
                if escolhido is not None:
                    break

        # Fallback 2D em malha se os 8 raios fixos nao encontraram vaga com seta (ex: juntas muito apertadas)
        if escolhido is None:
            grid_cands = []
            for r_g in [rv for rv in (25.0, 45.0, 65.0, 75.0, 105.0, 125.0, 145.0, 165.0, 190.0) if rv <= lim_r_max]:
                for ang_deg in range(0, 360, 15):
                    rad_g = math.radians(ang_deg)
                    cx = pcx + r_g * math.cos(rad_g) - 0.5 * larg_conj
                    cy = pcy + r_g * math.sin(rad_g) - 0.5 * alt_conj
                    grid_cands.append((math.hypot(cx - pcx, cy - pcy), cx, cy))
            grid_cands.sort(key=lambda it: it[0])
            for _, cand_x, cand_y in grid_cands:
                if pular_proximas and math.hypot(cand_x - cur_x, cand_y - cur_y) < 15.0:
                    continue
                if tw and abs(dx_gem) >= abs(dy_gem):
                    if dx_gem < 0 and (cand_x + 0.5 * larg_conj > mid_x):
                        continue
                    if dx_gem > 0 and (cand_x + 0.5 * larg_conj < mid_x):
                        continue
                elif tw and abs(dy_gem) > abs(dx_gem):
                    if dy_gem < 0 and (cand_y > mid_y):
                        continue
                    if dy_gem > 0 and (cand_y < mid_y):
                        continue

                cb9 = _bbox_texto(cand_x, cand_y, p9["h"], p9["ang"], p9["txt"])
                cb12 = _bbox_texto(
                    cand_x + p_grp["dx_sec"], cand_y + p_grp["dy_sec"],
                    p12["h"] if p12 else 12.0, p9["ang"], p12["txt"] if p12 else ""
                )
                c_conj = (min(cb9[0], cb12[0]), min(cb9[1], cb12[1]), max(cb9[2], cb12[2]), max(cb9[3], cb12[3]))

                if any(_boxes_colidem(c_conj, p_outro["box"], margem=3.0) for p_outro in pilares_group if p_outro is not p_grp):
                    continue
                if any(_boxes_colidem(c_conj, obs_p, margem=2.0) for obs_p in obstaculos_pilar):
                    continue
                if any(_segmento_colide_box(lx1, ly1, lx2, ly2, c_conj, margem=0.5) for lx1, ly1, lx2, ly2, _ in lines_concreto):
                    continue

                y_pat = (cand_y + p_grp["dy_sec"] - 3.0) if p12 else (cand_y - 3.0)
                if cand_x >= pcx:
                    x_jlh = cand_x - 3.0
                    x_fp = cand_x + larg_conj + 2.0
                    x_st = min(p_box[2], max(p_box[0] + 5.0, pcx + 3.0))
                else:
                    x_jlh = cand_x + larg_conj + 3.0
                    x_fp = cand_x - 2.0
                    x_st = max(p_box[0], min(p_box[2] - 5.0, pcx - 3.0))
                y_st = p_box[1] if y_pat < pcy else p_box[3]

                dist_s = math.hypot(x_jlh - x_st, y_pat - y_st)
                if dist_s >= 8.0:
                    corta_seta = False
                    for obs_p in obstaculos_pilar:
                        if p_box and (p_box[0] - 2.0 <= 0.5 * (obs_p[0] + obs_p[2]) <= p_box[2] + 2.0) and (p_box[1] - 2.0 <= 0.5 * (obs_p[1] + obs_p[3]) <= p_box[3] + 2.0):
                            continue
                        if _segmento_colide_box(x_jlh, y_pat, x_st, y_st, obs_p, margem=0.5) or \
                           _segmento_colide_box(x_fp, y_pat, x_jlh, y_pat, obs_p, margem=0.5):
                            corta_seta = True
                            break
                    if corta_seta:
                        continue
                    if any(
                        p_outro is not p_grp and (
                            _segmento_colide_box(x_jlh, y_pat, x_st, y_st, p_outro["box"], margem=0.5) or
                            _segmento_colide_box(x_fp, y_pat, x_jlh, y_pat, p_outro["box"], margem=0.5)
                        )
                        for p_outro in pilares_group
                    ):
                        continue

                escolhido = (cand_x, cand_y, c_conj)
                precisa_seta_pilar = True
                break

        if escolhido is not None:
            nx, ny, novo_box = escolhido
            dx = nx - p9["x1"]
            dy = ny - p9["y1"]

            apagar_chamadas_antigas_do_pilar(
                dwg, pcx, pcy, p_box, b_conj, linhas_242, linhas_221_setas, raio_busca=35.0
            )

            dwg.edit.Move(p9["addr"], dx, dy)
            p9["x1"] = nx
            p9["y1"] = ny
            p9["box"] = _bbox_texto(nx, ny, p9["h"], p9["ang"], p9["txt"])

            if p12 is not None:
                target_12_x = nx + p_grp["dx_sec"]
                target_12_y = ny + p_grp["dy_sec"]
                dx12 = target_12_x - p12["x1"]
                dy12 = target_12_y - p12["y1"]
                dwg.edit.Move(p12["addr"], dx12, dy12)
                p12["x1"] = target_12_x
                p12["y1"] = target_12_y
                p12["box"] = _bbox_texto(target_12_x, target_12_y, p12["h"], p12["ang"], p12["txt"])

            p_grp["box"] = novo_box

            desloc_total = math.hypot(dx, dy)
            if precisa_seta_pilar or desloc_total > 10.0:
                y_patamar = (ny + p_grp["dy_sec"] - 3.0) if p12 is not None else (ny - 3.0)
                if nx >= pcx:
                    x_joelho = nx - 3.0
                    x_fim_patamar = nx + larg_conj + 2.0
                    x_seta = min(p_box[2], max(p_box[0] + 5.0, pcx + 3.0))
                    y_seta = p_box[1] if y_patamar < pcy else p_box[3]
                else:
                    x_joelho = nx + larg_conj + 3.0
                    x_fim_patamar = nx - 2.0
                    x_seta = max(p_box[0], min(p_box[2] - 5.0, pcx - 3.0))
                    y_seta = p_box[1] if y_patamar < pcy else p_box[3]

                dist_seta = math.hypot(x_joelho - x_seta, y_patamar - y_seta)
                if dist_seta >= 8.0 or desloc_total > 10.0:
                    desenhar_seta_chamada_executiva(
                        dwg, x_fim_patamar, x_joelho, y_patamar, x_seta, y_seta, linhas_221_setas=linhas_221_setas
                    )

            total_ajustes += 1

    limpar_chamadas_orfas_221(dwg, linhas_221_setas, pilares_group)
    return total_ajustes


def _descolar_texto_concreto_viga(dwg, tx, vg, lines_concreto, folga_min=6.0):
    """
    Se o texto estiver tocando ou cortando a linha de concreto da viga (ou perpendicular),
    afasta-o alguns centimetros para o lado livre, garantindo folga minima sem grandes saltos.
    """
    h = tx["h"]
    ang = tx["ang"]
    t_min, t_max = vg["t_min"], vg["t_max"]
    dx, dy = 0.0, 0.0

    if ang == 0.0:
        t_meio = 0.5 * (t_min + t_max)
        if tx["y1"] >= t_meio:
            y_bot = tx["y1"] - 0.25 * h
            if y_bot < t_max + folga_min:
                novo_y = t_max + 0.25 * h + folga_min
                dy = novo_y - tx["y1"]
        else:
            y_top = tx["y1"] + 1.15 * h
            if y_top > t_min - folga_min:
                novo_y = t_min - 1.15 * h - folga_min
                dy = novo_y - tx["y1"]
    else:
        t_meio = 0.5 * (t_min + t_max)
        if tx["x1"] <= t_meio:
            x_right = tx["x1"] + 0.25 * h
            if x_right > t_min - folga_min:
                novo_x = t_min - 0.25 * h - folga_min
                dx = novo_x - tx["x1"]
        else:
            x_left = tx["x1"] - 1.15 * h
            if x_left < t_max + folga_min:
                novo_x = t_max + 1.15 * h + folga_min
                dx = novo_x - tx["x1"]

    if abs(dx) > 0.5 or abs(dy) > 0.5:
        dwg.edit.Move(tx["addr"], dx, dy)
        tx["x1"] += dx
        tx["y1"] += dy
        tx["xc"] += dx
        tx["yc"] += dy
        tx["box"] = _bbox_texto(tx["x1"], tx["y1"], tx["h"], tx["ang"], tx.get("txt", ""))
        return True
    return False


def resolver_sobreposicao_viga_com_seta(
    dwg, t_viga, texts_raw, lines_concreto, obstaculos_fixos, poly_pilares, linhas_221_setas=None
):
    """
    Resolve sobreposicao persistente de titulo de viga 'VXXX' (Nivel 8) ou texto de
    inversao 'VIGA INVERTIDA xCM' (Nivel 11):
      - Trava estritamente a orientacao original 'ang' do texto (JAMAIS gira 90° <-> 0°).
      - Respeita poligonos fisicos de pilares, textos de pilares (9/12), cubetas (208),
        cotas, linhas de concreto e demais textos.
      - Para VIGA INVERTIDA: se couber encostado na mesma face com deslocamento ate a
        ancora <= LIMITE_SEM_SETA_INVERSAO_VIGA (40.0 cm) e sem seta previa, posiciona
        sem seta; caso contrario (afastou > 40 cm, desencostou ou trocou de lado), limpa
        eventual seta antiga e desenha Seta de Chamada Executiva no Nivel 221 validada.
    """
    txt_up = t_viga.get("txt", "").upper()
    eh_inversao = (t_viga.get("level") == 11 and "INVERTIDA" in txt_up)
    comp_v = len(t_viga["txt"]) * t_viga["h"] * (1.0 if eh_inversao else 0.85)
    h_v = t_viga["h"]
    ang = t_viga["ang"]
    ang_n = _normalizar_angulo(ang)

    cur_box = _box_exato_de_texto_dict(t_viga)
    cx_cur = 0.5 * (cur_box[0] + cur_box[2])
    cy_cur = 0.5 * (cur_box[1] + cur_box[3])

    setas_chk = linhas_221_setas if linhas_221_setas is not None else []
    idxs_seta_antiga, tip_antigo = _encontrar_seta_de_inversao(t_viga, setas_chk, tol_caixa=5.5, texts_raw=texts_raw)
    tem_seta_antiga = len(idxs_seta_antiga) > 0
    other_setas = [l for idx, l in enumerate(setas_chk) if idx not in idxs_seta_antiga]

    boxes_pilares = [pb["box"] for pb in (poly_pilares or [])]
    obst_texts = [_box_exato_de_texto_dict(t) for t in texts_raw if id(t) != id(t_viga)]
    obst_fixos = list(obstaculos_fixos or [])
    obst_all = obst_texts + boxes_pilares + obst_fixos
    obst_criticos_seta = obst_texts + boxes_pilares

    # 1. Identifica a viga de concreto correspondente e suas faces [t_min, t_max]
    vigas_titulo = [tx for tx in texts_raw if tx.get("level") == 8 and tx.get("txt", "").upper().startswith("V")]
    for vt in vigas_titulo:
        if "box" not in vt or (vt["ang"] == 90.0 and abs(vt["box"][2] - vt["box"][0]) < 1.0):
            vt["box"] = _box_exato_de_texto_dict(vt)
    vigas_geom = mapear_vigas_continuas(vigas_titulo, lines_concreto) if vigas_titulo else []
    ref_x = tip_antigo[0] if tip_antigo is not None else cx_cur
    ref_y = tip_antigo[1] if tip_antigo is not None else cy_cur
    vg = associar_elemento_a_viga(ref_x, ref_y, ang, vigas_geom, tol_dist=120.0) if vigas_geom else None

    faces = None
    l_min_vg, l_max_vg = None, None
    if vg is not None:
        faces = (vg["t_min"], vg["t_max"])
        l_min_vg, l_max_vg = vg["l_min"], vg["l_max"]
    elif ang_n == 90.0:
        segs = [s for s in lines_concreto if abs(s[0] - s[2]) <= 8.0 and abs(s[1] - s[3]) > 10.0]
        perto = [s for s in segs if abs(0.5 * (s[0] + s[2]) - ref_x) <= 55.0 and min(s[1], s[3]) - 80.0 <= ref_y <= max(s[1], s[3]) + 80.0]
        if not perto:
            perto = [s for s in segs if abs(0.5 * (s[0] + s[2]) - ref_x) <= 95.0]
        xs = sorted(list(set(round(0.5 * (s[0] + s[2]), 1) for s in perto)))
        menor_d = float("inf")
        for i in range(len(xs)):
            for j in range(i + 1, len(xs)):
                w = xs[j] - xs[i]
                if 9.0 <= w <= 45.0:
                    d_c = abs(0.5 * (xs[i] + xs[j]) - ref_x)
                    if d_c < menor_d:
                        menor_d = d_c
                        faces = (xs[i], xs[j])
    elif ang_n == 0.0:
        segs = [s for s in lines_concreto if abs(s[1] - s[3]) <= 8.0 and abs(s[0] - s[2]) > 10.0]
        perto = [s for s in segs if abs(0.5 * (s[1] + s[3]) - ref_y) <= 55.0 and min(s[0], s[2]) - 80.0 <= ref_x <= max(s[0], s[2]) + 80.0]
        if not perto:
            perto = [s for s in segs if abs(0.5 * (s[1] + s[3]) - ref_y) <= 95.0]
        ys = sorted(list(set(round(0.5 * (s[1] + s[3]), 1) for s in perto)))
        menor_d = float("inf")
        for i in range(len(ys)):
            for j in range(i + 1, len(ys)):
                w = ys[j] - ys[i]
                if 9.0 <= w <= 45.0:
                    d_c = abs(0.5 * (ys[i] + ys[j]) - ref_y)
                    if d_c < menor_d:
                        menor_d = d_c
                        faces = (ys[i], ys[j])

    if ang_n == 90.0:
        if faces is not None:
            t_meio = 0.5 * (faces[0] + faces[1])
            lado_orig = 1.0 if cx_cur <= t_meio else -1.0
            xa_alvo = tip_antigo[0] if tip_antigo is not None else (faces[0] if lado_orig > 0 else faces[1])
        else:
            lado_orig = 1.0
            xa_alvo = tip_antigo[0] if tip_antigo is not None else cx_cur
        ya_alvo = tip_antigo[1] if tip_antigo is not None else cy_cur
        if l_min_vg is not None and l_max_vg is not None and tip_antigo is None:
            ya_alvo = max(l_min_vg + 5.0, min(l_max_vg - 5.0, ya_alvo))
        dt_face_atual = min(abs(cur_box[2] - faces[0]), abs(cur_box[0] - faces[1])) if faces is not None else 999.0
    elif ang_n == 0.0:
        if faces is not None:
            t_meio = 0.5 * (faces[0] + faces[1])
            lado_orig = 1.0 if cy_cur >= t_meio else -1.0
            ya_alvo = tip_antigo[1] if tip_antigo is not None else (faces[1] if lado_orig > 0 else faces[0])
        else:
            lado_orig = 1.0
            ya_alvo = tip_antigo[1] if tip_antigo is not None else cy_cur
        xa_alvo = tip_antigo[0] if tip_antigo is not None else cx_cur
        if l_min_vg is not None and l_max_vg is not None and tip_antigo is None:
            xa_alvo = max(l_min_vg + 5.0, min(l_max_vg - 5.0, xa_alvo))
        dt_face_atual = min(abs(cur_box[1] - faces[1]), abs(cur_box[3] - faces[0])) if faces is not None else 999.0
    else:
        lado_orig = 1.0
        xa_alvo = tip_antigo[0] if tip_antigo is not None else cx_cur
        ya_alvo = tip_antigo[1] if tip_antigo is not None else cy_cur
        dt_face_atual = 999.0

    def _aplicar_movimento_viga(nx, ny, nbox):
        dx = nx - t_viga["x1"]
        dy = ny - t_viga["y1"]
        if abs(dx) > 1e-4 or abs(dy) > 1e-4:
            dwg.edit.Move(t_viga["addr"], dx, dy)
        t_viga["x1"] = nx
        t_viga["y1"] = ny
        if "x2" in t_viga:
            t_viga["x2"] += dx
        if "y2" in t_viga:
            t_viga["y2"] += dy
        t_viga["xc"] = t_viga.get("xc", nx) + dx
        t_viga["yc"] = t_viga.get("yc", ny) + dy
        t_viga["box"] = nbox
        if "rbox" in t_viga:
            rb = t_viga["rbox"]
            t_viga["rbox"] = (rb[0] + dx, rb[1] + dy, rb[2] + dx, rb[3] + dy)
        else:
            t_viga["rbox"] = nbox

    # Passo A (Tier 1 - SEM SETA):
    # Para VIGA INVERTIDA: apenas na mesma face original e com d_box <= LIMITE_SEM_SETA_INVERSAO_VIGA (40 cm).
    if not tem_seta_antiga:
        if eh_inversao:
            if faces is not None and dt_face_atual <= 18.0:
                passos_tier1 = (0.0, 6.0, -6.0, 12.0, -12.0, 18.0, -18.0, 24.0, -24.0, 30.0, -30.0, 35.0, -35.0, 40.0, -40.0)
                if ang_n == 0.0:
                    y_face_ok = (faces[1] + 0.25 * h_v + 3.5) if lado_orig > 0 else (faces[0] - 1.15 * h_v - 3.5)
                    ys_try = [t_viga["y1"]] if abs(t_viga["y1"] - y_face_ok) <= 2.5 else [t_viga["y1"], y_face_ok]
                else:
                    x_face_ok = (faces[0] - 0.25 * h_v - 3.5) if lado_orig > 0 else (faces[1] + 1.15 * h_v + 3.5)
                    xs_try = [t_viga["x1"]] if abs(t_viga["x1"] - x_face_ok) <= 2.5 else [t_viga["x1"], x_face_ok]

                cands_t1 = []
                for d_sl in passos_tier1:
                    if ang_n == 0.0:
                        for sy in ys_try:
                            sx = t_viga["x1"] + d_sl
                            if l_min_vg is not None and (sx < l_min_vg - 15.0 or sx + comp_v > l_max_vg + 15.0):
                                continue
                            cands_t1.append((abs(d_sl) + abs(sy - t_viga["y1"]), sx, sy))
                    elif ang_n == 90.0:
                        for sx in xs_try:
                            sy = t_viga["y1"] + d_sl
                            if l_min_vg is not None and (sy < l_min_vg - 15.0 or sy + comp_v > l_max_vg + 15.0):
                                continue
                            cands_t1.append((abs(d_sl) + abs(sx - t_viga["x1"]), sx, sy))
                cands_t1.sort(key=lambda it: it[0])

                for _, sx, sy in cands_t1:
                    sbx = _bbox_texto(sx, sy, h_v, ang, t_viga["txt"])
                    if _dist_ponto_a_box(xa_alvo, ya_alvo, sbx) > LIMITE_SEM_SETA_INVERSAO_VIGA:
                        continue
                    if any(_boxes_colidem(sbx, pb, margem=1.0) for pb in boxes_pilares):
                        continue
                    if any(_boxes_colidem(sbx, ob, margem=0.5) for ob in obst_texts):
                        continue
                    if any(_boxes_colidem(sbx, ob, margem=0.5) for ob in obst_fixos):
                        continue
                    if any(_segmento_colide_box(lx1, ly1, lx2, ly2, sbx, margem=0.5) for lx1, ly1, lx2, ly2, _ in lines_concreto):
                        continue
                    if any(_segmento_colide_box(l["x1"], l["y1"], l["x2"], l["y2"], sbx, margem=0.8) for l in other_setas):
                        continue
                    _aplicar_movimento_viga(sx, sy, sbx)
                    return True
        else:
            rad_a = math.radians(ang)
            ux_a, uy_a = math.cos(rad_a), math.sin(rad_a)
            for d_slide in (8.0, -8.0, 15.0, -15.0, 25.0, -25.0, 35.0, -35.0, 50.0, -50.0, 62.0, -62.0, 75.0, -75.0, 90.0, -90.0):
                sx = t_viga["x1"] + d_slide * ux_a
                sy = t_viga["y1"] + d_slide * uy_a
                sbx = _bbox_texto(sx, sy, h_v, ang, t_viga["txt"])
                if any(_boxes_colidem(sbx, ob, margem=1.5) for ob in obst_all):
                    continue
                if any(_segmento_colide_box(lx1, ly1, lx2, ly2, sbx, margem=-1.5) for lx1, ly1, lx2, ly2, _ in lines_concreto):
                    continue
                if any(_segmento_colide_box(l["x1"], l["y1"], l["x2"], l["y2"], sbx, margem=1.0) for l in other_setas):
                    continue
                _aplicar_movimento_viga(sx, sy, sbx)
                return True

    # Passo B (Tier 2 - COM SETA NO NIVEL 221, orientacao 'ang' 100% TRAVADA):
    raw_cands = [(t_viga["x1"], t_viga["y1"], lado_orig)]
    lados_ord = (lado_orig, -lado_orig)
    d_longs = (0.0, -15.0, 15.0, -30.0, 30.0, -50.0, 50.0, -75.0, 75.0, -105.0, 105.0, -140.0, 140.0, -175.0, 175.0)
    raios = (4.0, 12.0, 20.0, 30.0, 42.0, 55.0, 75.0, 95.0, 120.0, 150.0, 185.0, 220.0)

    if ang_n == 90.0:
        x_esq_ref = faces[0] if faces is not None else xa_alvo
        x_dir_ref = faces[1] if faces is not None else xa_alvo
        for r in raios:
            for s_side in lados_ord:
                cs_x = (x_esq_ref - 0.25 * h_v - r) if s_side > 0 else (x_dir_ref + 1.15 * h_v + r)
                for d_long in d_longs:
                    cs_y = ya_alvo - 0.5 * comp_v + d_long
                    raw_cands.append((cs_x, cs_y, s_side))
            for d_perp in (0.0, -15.0, 15.0, -30.0, 30.0):
                raw_cands.append((xa_alvo + d_perp + 0.5 * h_v, ya_alvo + r + 8.0, lado_orig))
                raw_cands.append((xa_alvo + d_perp + 0.5 * h_v, ya_alvo - r - comp_v - 8.0, lado_orig))
    elif ang_n == 0.0:
        y_inf_ref = faces[0] if faces is not None else ya_alvo
        y_sup_ref = faces[1] if faces is not None else ya_alvo
        for r in raios:
            for s_side in lados_ord:
                cs_y = (y_sup_ref + 0.25 * h_v + r) if s_side > 0 else (y_inf_ref - 1.15 * h_v - r)
                for d_long in d_longs:
                    cs_x = xa_alvo - 0.5 * comp_v + d_long
                    raw_cands.append((cs_x, cs_y, s_side))
            for d_perp in (0.0, -15.0, 15.0, -30.0, 30.0):
                raw_cands.append((xa_alvo + r + 8.0, ya_alvo + d_perp - 0.5 * h_v, lado_orig))
                raw_cands.append((xa_alvo - r - comp_v - 8.0, ya_alvo + d_perp - 0.5 * h_v, lado_orig))
    else:
        rad_g = math.radians(ang)
        ux_g, uy_g = math.cos(rad_g), math.sin(rad_g)
        nx_g, ny_g = -uy_g, ux_g
        for r in raios:
            for s_side in lados_ord:
                off_n = s_side * (r + 0.65 * h_v)
                for d_long in d_longs:
                    cx_m = xa_alvo + d_long * ux_g + off_n * nx_g
                    cy_m = ya_alvo + d_long * uy_g + off_n * ny_g
                    cs_x = cx_m - 0.5 * comp_v * ux_g - 0.5 * h_v * nx_g
                    cs_y = cy_m - 0.5 * comp_v * uy_g - 0.5 * h_v * ny_g
                    raw_cands.append((cs_x, cs_y, s_side))

    # Ordena estritamente pela menor distancia ao local original/atual (com leve bonus para manter mesmo lado)
    scored_cands = []
    seen_grid = set()
    for cs_x, cs_y, s_side in raw_cands:
        gk = (round(cs_x, 1), round(cs_y, 1))
        if gk in seen_grid:
            continue
        seen_grid.add(gk)
        cbx = _bbox_texto(cs_x, cs_y, h_v, ang, t_viga["txt"])
        cmx = 0.5 * (cbx[0] + cbx[2])
        cmy = 0.5 * (cbx[1] + cbx[3])
        pen_lado = 0.0 if s_side == lado_orig else 6.0
        dist_score = math.hypot(cmx - cx_cur, cmy - cy_cur) + 0.35 * _dist_ponto_a_box(xa_alvo, ya_alvo, cbx) + pen_lado
        scored_cands.append((dist_score, cs_x, cs_y, cbx))
    scored_cands.sort(key=lambda it: it[0])

    def _alvos_na_viga_para_cand(cs_x, cs_y, cbx):
        cmx = 0.5 * (cbx[0] + cbx[2])
        cmy = 0.5 * (cbx[1] + cbx[3])
        raw_pts = []
        offs_long = (
            0.0, -10.0, 10.0, -18.0, 18.0, -28.0, 28.0, -38.0, 38.0,
            -50.0, 50.0, -65.0, 65.0, -85.0, 85.0, -110.0, 110.0,
            -140.0, 140.0, -175.0, 175.0, -220.0, 220.0
        )
        fracs = (0.5, 0.3, 0.7, 0.15, 0.85, 0.05, 0.95)
        if ang_n == 0.0:
            ya_face = (faces[1] if cmy >= 0.5 * (faces[0] + faces[1]) else faces[0]) if faces is not None else ya_alvo
            for off in offs_long:
                xs_a = xa_alvo + off
                if l_min_vg is not None and not (l_min_vg + 4.0 <= xs_a <= l_max_vg - 4.0):
                    continue
                raw_pts.append((xs_a, ya_face))
            for frac in fracs:
                xs_a = cs_x + frac * comp_v
                if l_min_vg is not None and not (l_min_vg + 4.0 <= xs_a <= l_max_vg - 4.0):
                    continue
                if abs(xs_a - xa_alvo) <= 220.0:
                    raw_pts.append((xs_a, ya_face))
        elif ang_n == 90.0:
            xa_face = (faces[0] if cmx <= 0.5 * (faces[0] + faces[1]) else faces[1]) if faces is not None else xa_alvo
            for off in offs_long:
                ys_a = ya_alvo + off
                if l_min_vg is not None and not (l_min_vg + 4.0 <= ys_a <= l_max_vg - 4.0):
                    continue
                raw_pts.append((xa_face, ys_a))
            for frac in fracs:
                ys_a = cs_y + frac * comp_v
                if l_min_vg is not None and not (l_min_vg + 4.0 <= ys_a <= l_max_vg - 4.0):
                    continue
                if abs(ys_a - ya_alvo) <= 220.0:
                    raw_pts.append((xa_face, ys_a))
        else:
            rad_t = math.radians(ang)
            ux_t, uy_t = math.cos(rad_t), math.sin(rad_t)
            for off in offs_long:
                raw_pts.append((xa_alvo + off * ux_t, ya_alvo + off * uy_t))

        seen_pts = set()
        pts_limpos = []
        for px, py in raw_pts:
            pk = (round(px, 1), round(py, 1))
            if pk in seen_pts:
                continue
            seen_pts.add(pk)
            if any(_dist_ponto_a_box(px, py, pb) < 6.0 for pb in boxes_pilares):
                continue
            d_orig = math.hypot(px - xa_alvo, py - ya_alvo)
            d_cbx = _dist_ponto_a_box(px, py, cbx)
            pts_limpos.append((0.6 * d_orig + 0.4 * d_cbx, px, py))

        pts_limpos.sort(key=lambda it: it[0])
        return [(px, py) for _, px, py in pts_limpos]

    corredor_viga_miolo = None
    if faces is not None and (faces[1] - faces[0]) > 4.0:
        if ang_n == 0.0:
            lx0 = (l_min_vg - 5.0) if l_min_vg is not None else (xa_alvo - 250.0)
            lx1 = (l_max_vg + 5.0) if l_max_vg is not None else (xa_alvo + 250.0)
            corredor_viga_miolo = (lx0, faces[0] + 1.0, lx1, faces[1] - 1.0)
        elif ang_n == 90.0:
            ly0 = (l_min_vg - 5.0) if l_min_vg is not None else (ya_alvo - 250.0)
            ly1 = (l_max_vg + 5.0) if l_max_vg is not None else (ya_alvo + 250.0)
            corredor_viga_miolo = (faces[0] + 1.0, ly0, faces[1] - 1.0, ly1)

    best_cand = None
    for m_txt, m_fix, m_conc, obst_seta_list in (
        (1.2, 1.2, 0.5, obst_all),
        (0.3, 0.2, 0.2, obst_criticos_seta),
    ):
        for _, cs_x, cs_y, cand_bx in scored_cands:
            if corredor_viga_miolo is not None and _boxes_colidem(cand_bx, corredor_viga_miolo, margem=0.0):
                continue
            if any(_boxes_colidem(cand_bx, pb, margem=1.0) for pb in boxes_pilares):
                continue
            if any(_boxes_colidem(cand_bx, ob, margem=m_txt) for ob in obst_texts):
                continue
            if any(_boxes_colidem(cand_bx, ob, margem=m_fix) for ob in obst_fixos):
                continue
            if any(_segmento_colide_box(l["x1"], l["y1"], l["x2"], l["y2"], cand_bx, margem=0.8) for l in other_setas):
                continue
            if any(_segmento_colide_box(lx1, ly1, lx2, ly2, cand_bx, margem=m_conc) for lx1, ly1, lx2, ly2, _ in lines_concreto):
                continue

            alvo_ok = None
            for xa_s, ya_s in _alvos_na_viga_para_cand(cs_x, cs_y, cand_bx):
                x_j, y_j = _ponto_saida_seta_inversao(cs_x, cs_y, comp_v, h_v, ang, xa_s, ya_s)
                if math.hypot(x_j - xa_s, y_j - ya_s) < 3.0:
                    continue
                corta_seta = False
                for ob_b in obst_seta_list:
                    if _segmento_colide_box(x_j, y_j, xa_s, ya_s, ob_b, margem=0.4):
                        corta_seta = True
                        break
                if not corta_seta:
                    alvo_ok = (xa_s, ya_s)
                    break

            if alvo_ok is not None:
                best_cand = (cs_x, cs_y, cand_bx, alvo_ok[0], alvo_ok[1])
                break
        if best_cand is not None:
            break

    if best_cand is not None:
        nx, ny, nbox, xa_f, ya_f = best_cand
        if linhas_221_setas is not None:
            apagar_chamadas_antigas_de_inversao(dwg, t_viga, linhas_221_setas, raio_busca=5.5, texts_raw=texts_raw)
        _aplicar_movimento_viga(nx, ny, nbox)
        desenhar_seta_inversao(
            dwg, nx, ny, comp_v, h_v, ang, xa_f, ya_f, linhas_221_setas
        )
        return True
    return False


def executar_anti_sobreposicao(dwg):
    """
    Executa a organizacao completa da planta de formas:
      1. Mapeia todas as vigas brancas continuas (corredor de concreto ate o proximo VXXX).
      2. Deduplica bolinhas repetidas de mesmo valor na mesma viga (ex: 5 bolinhas 40 na V513-A -> fica 1).
      3. Organiza nomes de vigas (VXXX), secoes (xx/xx), bolinhas ((xx)) e textos VIGA INVERTIDA:
         - Fecha buracos desnecessarios entre a secao xx/xx e o nome VXXX quando a bolinha sai do meio.
         - Troca de lado na viga branca ou desliza ao longo da mesma viga se houver colisao com
           pilar, linha perpendicular ou outro texto (ex: bolinha (20) da V509-A perto do P75
           passando para o lado direito limpo da V509-A).
      4. Organiza pilares (P... + b/h) com pareamento 1-para-1 e Seta Executiva no Nivel 221.
    """
    _garantir_ipocot_carregado()

    poly_pilares = []
    lines_concreto = []
    obstaculos_fixos = []
    todos_obstaculos_cotas = []
    texts_raw = []
    circs_raw = []
    linhas_242 = []
    linhas_221_setas = []

    dwg.iterator.Begin()
    while True:
        tipo = dwg.iterator.Next()
        if tipo == TQSDwg.DWGTYPE_EOF:
            break
        if dwg.iterator.inBlock != 0:
            continue
        if dwg.iterator.isOpenObject != 0:
            if tipo == TQSDwg.DWGTYPE_TEXT and dwg.iterator.level in (122, 216):
                todos_obstaculos_cotas.append(_bbox_texto_exato(
                    dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2, dwg.iterator.textHeight
                ))
            continue

        l = dwg.iterator.level
        addr = dwg.iterator.GetElementReadPosition()

        if tipo == TQSDwg.DWGTYPE_POLYLINE:
            pts = [dwg.iterator.GetPolylinePt(i) for i in range(dwg.iterator.xySize)]
            if not pts:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            dx_poly = max(xs) - min(xs)
            dy_poly = max(ys) - min(ys)
            if l in (2, 3, 4, 5) and 5.0 <= dx_poly <= 450.0 and 5.0 <= dy_poly <= 450.0 and len(pts) >= 4:
                poly_pilares.append({
                    "addr": addr,
                    "level": l,
                    "pts": pts,
                    "box": (min(xs), min(ys), max(xs), max(ys)),
                    "pcx": 0.5 * (min(xs) + max(xs)),
                    "pcy": 0.5 * (min(ys) + max(ys)),
                })
            elif l in (1, 2, 201):
                for i in range(len(pts) - 1):
                    lines_concreto.append((pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], l))
            elif l in (200, 205):
                obstaculos_fixos.append((min(xs), min(ys), max(xs), max(ys)))

        elif tipo == TQSDwg.DWGTYPE_LINE:
            x1, y1, x2, y2 = dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2
            if l in (1, 2, 201):
                lines_concreto.append((x1, y1, x2, y2, l))
            elif l in (200, 205):
                obstaculos_fixos.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
            elif l in (122, 216):
                todos_obstaculos_cotas.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
            elif l == 221:
                linhas_221_setas.append({
                    "addr": addr, "x1": x1, "y1": y1, "x2": x2, "y2": y2
                })
            elif l == 242:
                linhas_242.append({
                    "addr": addr, "x1": x1, "y1": y1, "x2": x2, "y2": y2
                })

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
            else:
                texts_raw.append({
                    "addr": addr, "level": l, "txt": txt_str,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "xc": xc, "yc": yc, "h": h, "ang": ang, "box": b
                })

        elif tipo == TQSDwg.DWGTYPE_CIRCLE:
            if l in (28, 29):
                continue
            circs_raw.append({
                "addr": addr, "level": l,
                "xc": dwg.iterator.xc, "yc": dwg.iterator.yc, "r": dwg.iterator.radius
            })

    total_ajustes = 0
    boxes_pilares = [pb["box"] for pb in poly_pilares]

    # -------------------------------------------------------------------------
    # 2. GRUPOS ATOMICOS: BOLINHAS, PILARES, VIGAS E LAJES
    # -------------------------------------------------------------------------
    bolinhas_group = []
    used_tx_idx = set()
    for c in circs_raw:
        best_tx = None
        min_d = float("inf")
        for i, tx in enumerate(texts_raw):
            if i in used_tx_idx or tx["level"] not in (11, 13):
                continue
            if "/" in tx["txt"] or "=" in tx["txt"] or tx["txt"].lower().startswith("h") or "VIGA" in tx["txt"].upper():
                continue
            d = math.hypot(c["xc"] - tx["xc"], c["yc"] - tx["yc"])
            if d <= c["r"] * 1.35 and d < min_d:
                min_d = d
                best_tx = (i, tx)
        if best_tx is not None:
            used_tx_idx.add(best_tx[0])
            tx = best_tx[1]
            try:
                val_num = round(float(tx["txt"].replace(",", ".")), 1)
            except Exception:
                val_num = 0.0
            bolinhas_group.append({
                "addr_circ": c["addr"],
                "addr_txt": tx["addr"],
                "xc": c["xc"], "yc": c["yc"], "r": c["r"], "level": c["level"],
                "txt": tx["txt"], "val": val_num, "h": tx["h"], "ang": tx["ang"],
                "tx_x1": tx["x1"], "tx_y1": tx["y1"],
                "box": (c["xc"] - c["r"], c["yc"] - c["r"], c["xc"] + c["r"], c["yc"] + c["r"]),
                "dx_txt": tx["x1"] - c["xc"],
                "dy_txt": tx["y1"] - c["yc"],
            })

    # Pilares (Nivel 9 + Nivel 12) com pareamento 1-para-1 ao poligono fisico e secao
    pilares_group = _construir_pilares_group(texts_raw, poly_pilares)

    # Lajes (Nivel 10 + Nivel 13) para que textos de viga nao invadam textos de laje
    lajes_boxes = [tx["box"] for tx in texts_raw if tx["level"] in (10, 13) and tx["addr"] not in [b["addr_txt"] for b in bolinhas_group]]

    # -------------------------------------------------------------------------
    # 3. MAPEAMENTO DE VIGAS BRANCAS CONTINUAS E ORGANIZACAO DE VIGAS/BOLINHAS
    # -------------------------------------------------------------------------
    vigas_titulo = [tx for tx in texts_raw if tx["level"] == 8 and tx["txt"].upper().startswith("V")]
    secoes_viga = [tx for tx in texts_raw if tx["level"] == 11 and "/" in tx["txt"]]
    vigas_inv_group = [tx for tx in texts_raw if tx["level"] == 11 and "VIGA INVERTIDA" in tx["txt"].upper()]

    vigas_geom = mapear_vigas_continuas(vigas_titulo, lines_concreto)
    for vg in vigas_geom:
        vg["secoes"] = []
        vg["bolinhas"] = []
        vg["inversoes_txt"] = []

    for s in secoes_viga:
        vg = associar_elemento_a_viga(s["xc"], s["yc"], s["ang"], vigas_geom)
        if vg is not None:
            vg["secoes"].append(s)

    for b in bolinhas_group:
        if b["level"] == 11:
            vg = associar_elemento_a_viga(b["xc"], b["yc"], b["ang"], vigas_geom)
            if vg is not None:
                vg["bolinhas"].append(b)

    for vi in vigas_inv_group:
        vg = associar_elemento_a_viga(vi["xc"], vi["yc"], vi["ang"], vigas_geom)
        if vg is not None:
            vg["inversoes_txt"].append(vi)

    # 3A. DEDUPLICACAO DE BOLINHAS DE MESMO VALOR NA MESMA VIGA BRANCA
    # (Ex: V513-A com 5 bolinhas (40) -> mantem apenas 1 bolinha limpa e apaga as 4 repetidas)
    bolinhas_ativas = []
    for vg in vigas_geom:
        por_val = {}
        for b in vg["bolinhas"]:
            por_val.setdefault(b["val"], []).append(b)

        vg_bolinhas_filtradas = []
        for val, grp in por_val.items():
            if len(grp) > 1:
                # Escolhe a bolinha mais limpa (que nao colide com pilar nem linha perpendicular)
                def _score_bolinha(bol):
                    penal = 0
                    if any(_boxes_colidem(bol["box"], pb, margem=3.0) for pb in boxes_pilares):
                        penal += 100
                    if _box_colide_com_concreto_alheio(bol["box"], vg, lines_concreto, margem=1.0):
                        penal += 50
                    if any(_boxes_colidem(bol["box"], pg["box"], margem=10.0) for pg in pilares_group):
                        penal += 30
                    # Prefere ficar proxima do nome da viga quando limpa
                    dist_v = math.hypot(bol["xc"] - vg["viga"]["xc"], bol["yc"] - vg["viga"]["yc"])
                    return (penal, dist_v)

                grp_ord = sorted(grp, key=_score_bolinha)
                escolhida = grp_ord[0]
                vg_bolinhas_filtradas.append(escolhida)
                for b_rep in grp_ord[1:]:
                    try:
                        dwg.edit.Erase(b_rep["addr_circ"])
                        dwg.edit.Erase(b_rep["addr_txt"])
                        total_ajustes += 1
                    except Exception:
                        pass
            else:
                vg_bolinhas_filtradas.append(grp[0])

        vg["bolinhas"] = vg_bolinhas_filtradas
        bolinhas_ativas.extend(vg_bolinhas_filtradas)

    # 3B. REPOSICIONAMENTO INTELIGENTE DE ELEMENTOS DE VIGA (TROCAR DE LADO OU DESLIZAR NA VIGA)
    # Coleta boxes fixos para verificar colisoes de vigas/bolinhas
    boxes_ocupados_vigas = (
        list(boxes_pilares)
        + list(obstaculos_fixos)
        + list(todos_obstaculos_cotas)
        + list(lajes_boxes)
    )
    # Adiciona todas as posicoes atuais de titulos, secoes, bolinhas e textos de inversao
    for vg in vigas_geom:
        boxes_ocupados_vigas.append(vg["viga"]["box"])
        for s in vg["secoes"]:
            boxes_ocupados_vigas.append(s["box"])
        for b in vg["bolinhas"]:
            boxes_ocupados_vigas.append(b["box"])
        for vi in vg["inversoes_txt"]:
            boxes_ocupados_vigas.append(vi["box"])

    def _remover_box_da_lista(bx_alvo, lista):
        for i, bx in enumerate(lista):
            if bx == bx_alvo:
                lista.pop(i)
                return

    # 3.0 MICRO-AJUSTE DESATIVADO: So move se identificar sobreposicao real!
    # (Textos perfeitamente posicionados sao mantidos quietos sem empurrao arbitrario)

    # Verifica e organiza bolinhas (Nivel 11) em cada viga
    for vg in vigas_geom:
        ang = vg["ang"]
        for b in vg["bolinhas"]:
            _remover_box_da_lista(b["box"], boxes_ocupados_vigas)

            # Bolinha precisa mover se:
            # 1. Toca poligono de pilar (ex: V507-A (40) no P312-A)
            # 2. Toca linha de concreto perpendicular
            # 3. Colide com outro texto de viga/secao/bolinha
            # 4. Esta num trecho onde o texto 'VIGA INVERTIDA xxCM' (comp ~ 175cm) colidiria com
            #    lajes estreitas (ex: L511-A), pilares (ex: P75) ou o proprio nome VXXX (ex: V505-A)!
            obst_com_pilares_txt = boxes_ocupados_vigas + [pg["box"] for pg in pilares_group]
            # So move se a bolinha identificar sobreposicao real com obstaculo ou concreto perpendicular!
            precisa_mover = (
                any(_boxes_colidem(b["box"], obs, margem=1.0) for obs in obst_com_pilares_txt)
                or _box_colide_com_concreto_alheio(b["box"], vg, lines_concreto, margem=1.0)
            )

            if precisa_mover:
                # Se a bolinha esta perto de um pilar de um lado da viga, prefere trocar para o lado oposto!
                t_meio = 0.5 * (vg["t_min"] + vg["t_max"])
                if ang == 0.0:
                    lado_atual = 1 if b["yc"] >= t_meio else -1
                    pos_l_atual = b["xc"]
                else:
                    lado_atual = 1 if b["xc"] <= t_meio else -1
                    pos_l_atual = b["yc"]

                # Tenta primeiro o lado oposto (trocar de lado na viga, como ensinado pelo usuario!)
                obst_com_pilares_txt = boxes_ocupados_vigas + [pg["box"] for pg in pilares_group]
                res = encontrar_posicao_livre_na_viga(
                    vg, b["r"] * 2.0, b["r"] * 2.0, True,
                    pos_l_atual, -lado_atual,
                    obst_com_pilares_txt, lines_concreto
                )
                if res is None:
                    res = encontrar_posicao_livre_na_viga(
                        vg, b["r"] * 2.0, b["r"] * 2.0, True,
                        pos_l_atual, -lado_atual,
                        boxes_ocupados_vigas, lines_concreto
                    )

                if res is not None:
                    nx, ny, nbox = res
                    dx = nx - b["xc"]
                    dy = ny - b["yc"]
                    if math.hypot(dx, dy) > 1.0:
                        dwg.edit.Move(b["addr_circ"], dx, dy)
                        dwg.edit.Move(b["addr_txt"], dx, dy)
                        b["xc"] = nx
                        b["yc"] = ny
                        b["tx_x1"] += dx
                        b["tx_y1"] += dy
                        b["box"] = nbox
                        total_ajustes += 1

            boxes_ocupados_vigas.append(b["box"])

        # Verifica e organiza textos 'VIGA INVERTIDA xxCM' (se ja existirem no desenho)
        for vi in vg["inversoes_txt"]:
            _remover_box_da_lista(vi["box"], boxes_ocupados_vigas)
            comp_vi = len(vi["txt"]) * vi["h"] * 1.0
            colide_com_secoes = any(_boxes_colidem(vi["box"], s["box"], margem=0.5) for s in vg["secoes"])
            colide_com_nome = _boxes_colidem(vi["box"], vg["viga"]["box"], margem=0.5)
            obst_com_pilares_vi = boxes_ocupados_vigas + [pg["box"] for pg in pilares_group]

            # Verifica se alguma linha de seta conectada a 'vi' colide com textos/obstaculos
            seta_vi_colide = False
            for l in linhas_221_setas:
                d1 = math.hypot(l["x1"] - vi["x1"], l["y1"] - vi["y1"])
                d2 = math.hypot(l["x2"] - vi["x1"], l["y2"] - vi["y1"])
                if min(d1, d2) <= 30.0:
                    for ob in obst_com_pilares_vi:
                        if _segmento_colide_box(l["x1"], l["y1"], l["x2"], l["y2"], ob, margem=0.5):
                            seta_vi_colide = True
                            break
                    if seta_vi_colide:
                        break

            precisa_mover_vi = (
                any(_boxes_colidem(vi["box"], obs, margem=0.5) for obs in obst_com_pilares_vi)
                or colide_com_secoes
                or colide_com_nome
                or _box_colide_com_concreto_alheio(vi["box"], vg, lines_concreto, margem=1.0)
                or seta_vi_colide
            )
            if precisa_mover_vi:
                vi_ang = vi["ang"]
                vi_cx = 0.5 * (vi["box"][0] + vi["box"][2])
                vi_cy = 0.5 * (vi["box"][1] + vi["box"][3])
                t_meio = 0.5 * (vg["t_min"] + vg["t_max"])
                if ang == 0.0:
                    lado_vi = 1.0 if vi_cy >= t_meio else -1.0
                    xa_alvo = max(vg["l_min"] + 5.0, min(vg["l_max"] - 5.0, vi_cx))
                    ya_alvo = vg["t_max"] if lado_vi > 0 else vg["t_min"]
                else:
                    lado_vi = 1.0 if vi_cx <= t_meio else -1.0
                    xa_alvo = vg["t_min"] if lado_vi > 0 else vg["t_max"]
                    ya_alvo = max(vg["l_min"] + 5.0, min(vg["l_max"] - 5.0, vi_cy))

                res = None
                precisa_seta = False

                # 1o: Tenta posicionamento direto na mesma face ate LIMITE_SEM_SETA_INVERSAO_VIGA (40 cm), mantendo vi_ang
                candidatos_locais = []
                passos = [0.0] + [d for step in (8.0, 16.0, 24.0, 32.0, 40.0) for d in (step, -step)]
                if ang == 0.0:
                    cy_same = (vg["t_max"] + 0.25 * vi["h"] + 3.5) if lado_vi > 0 else (vg["t_min"] - 1.15 * vi["h"] - 3.5)
                    for d_local in passos:
                        cx = xa_alvo - 0.5 * comp_vi + d_local
                        if cx >= vg["l_min"] - 10.0 and cx + comp_vi <= vg["l_max"] + 10.0:
                            candidatos_locais.append((cx, cy_same, vi_ang))
                else:
                    cx_same = (vg["t_min"] - 0.25 * vi["h"] - 3.5) if lado_vi > 0 else (vg["t_max"] + 1.15 * vi["h"] + 3.5)
                    for d_local in passos:
                        cy = ya_alvo - 0.5 * comp_vi + d_local
                        if cy >= vg["l_min"] - 10.0 and cy + comp_vi <= vg["l_max"] + 10.0:
                            candidatos_locais.append((cx_same, cy, vi_ang))

                for cd_x, cd_y, cd_ang in candidatos_locais:
                    cand_bx = _bbox_texto(cd_x, cd_y, vi["h"], cd_ang, vi["txt"])
                    if _dist_ponto_a_box(xa_alvo, ya_alvo, cand_bx) > LIMITE_SEM_SETA_INVERSAO_VIGA:
                        continue
                    if any(_boxes_colidem(cand_bx, ob, margem=0.5) for ob in obst_com_pilares_vi):
                        continue
                    if _box_colide_com_concreto_alheio(cand_bx, vg, lines_concreto, margem=1.0):
                        continue
                    res = (cd_x, cd_y, cand_bx, cd_ang)
                    break

                # 2o: Se nao coube direto em <= 40 cm, procura posicao com SETA DE CHAMADA travando vi_ang!
                if res is None:
                    candidatos_seta = []
                    for r in (12.0, 25.0, 40.0, 55.0, 75.0, 95.0, 120.0, 150.0):
                        if _normalizar_angulo(vi_ang) == 90.0:
                            for s_side in (lado_vi, -lado_vi):
                                cx_s = (vg["t_min"] - 0.25 * vi["h"] - r) if s_side > 0 else (vg["t_max"] + 1.15 * vi["h"] + r)
                                for dy in (0.0, -20.0, 20.0, -45.0, 45.0, -75.0, 75.0, -110.0, 110.0):
                                    candidatos_seta.append((cx_s, ya_alvo - 0.5 * comp_vi + dy, vi_ang))
                        else:
                            for s_side in (lado_vi, -lado_vi):
                                cy_s = (vg["t_max"] + 0.25 * vi["h"] + r) if s_side > 0 else (vg["t_min"] - 1.15 * vi["h"] - r)
                                for dx in (0.0, -20.0, 20.0, -45.0, 45.0, -75.0, 75.0, -110.0, 110.0):
                                    candidatos_seta.append((xa_alvo - 0.5 * comp_vi + dx, cy_s, vi_ang))

                    for cs_x, cs_y, cs_ang in candidatos_seta:
                        cand_bx = _bbox_texto(cs_x, cs_y, vi["h"], cs_ang, vi["txt"])
                        if any(_boxes_colidem(cand_bx, ob, margem=1.5) for ob in obst_com_pilares_vi):
                            continue
                        if any(_segmento_colide_box(lx1, ly1, lx2, ly2, cand_bx, margem=0.8) for lx1, ly1, lx2, ly2, _ in lines_concreto):
                            continue

                        x_j, y_j = _ponto_saida_seta_inversao(cs_x, cs_y, comp_vi, vi["h"], cs_ang, xa_alvo, ya_alvo)
                        corta_seta = False
                        for ob_b in obst_com_pilares_vi:
                            if _dist_ponto_a_box(xa_alvo, ya_alvo, ob_b) < 2.0:
                                continue
                            if _segmento_colide_box(x_j, y_j, xa_alvo, ya_alvo, ob_b, margem=0.5):
                                corta_seta = True
                                break
                        if corta_seta:
                            continue

                        res = (cs_x, cs_y, cand_bx, cs_ang)
                        precisa_seta = True
                        break

                if res is not None:
                    nx, ny, nbox, nang = res
                    dx = nx - vi["x1"]
                    dy = ny - vi["y1"]
                    if math.hypot(dx, dy) > 0.5 or seta_vi_colide or precisa_seta:
                        apagar_chamadas_antigas_de_inversao(dwg, vi, linhas_221_setas, raio_busca=40.0)
                        if math.hypot(dx, dy) > 0.1:
                            dwg.edit.Move(vi["addr"], dx, dy)
                        vi["x1"] = nx
                        vi["y1"] = ny
                        if "x2" in vi:
                            vi["x2"] += dx
                        if "y2" in vi:
                            vi["y2"] += dy
                        vi["xc"] = vi.get("xc", nx) + dx
                        vi["yc"] = vi.get("yc", ny) + dy
                        vi["box"] = nbox
                        total_ajustes += 1

                        if precisa_seta:
                            desenhar_seta_inversao(
                                dwg, nx, ny, comp_vi, vi["h"], nang, xa_alvo, ya_alvo, linhas_221_setas
                            )

            boxes_ocupados_vigas.append(vi["box"])

        boxes_futuros_bolinhas = []

        # Verifica e organiza o proprio nome 'VXXX' da viga se colidir com pilar, concreto perpendicular ou outro texto
        v = vg["viga"]
        _remover_box_da_lista(v["box"], boxes_ocupados_vigas)
        obst_com_pilares = boxes_ocupados_vigas + [pg["box"] for pg in pilares_group]
        precisa_mover_v = (
            any(_boxes_colidem(v["box"], obs, margem=1.5) for obs in obst_com_pilares)
            or _box_colide_com_concreto_alheio(v["box"], vg, lines_concreto, margem=1.0)
        )
        if precisa_mover_v:
            t_meio = 0.5 * (vg["t_min"] + vg["t_max"])
            comp_v = len(v["txt"]) * v["h"] * 0.85
            if ang == 0.0:
                lado_atual = 1 if v["y1"] >= t_meio else -1
                pos_l_atual = v["x1"]
            else:
                lado_atual = 1 if v["x1"] <= t_meio else -1
                pos_l_atual = v["y1"]

            obst_com_pilares_txt = boxes_ocupados_vigas + boxes_futuros_bolinhas + [pg["box"] for pg in pilares_group]
            res = encontrar_posicao_livre_na_viga(
                vg, comp_v, v["h"], False,
                pos_l_atual, lado_atual,
                obst_com_pilares_txt, lines_concreto
            )
            if res is None:
                res = encontrar_posicao_livre_na_viga(
                    vg, comp_v, v["h"], False,
                    pos_l_atual, lado_atual,
                    boxes_ocupados_vigas + boxes_futuros_bolinhas, lines_concreto
                )
            if res is None and ang == 0.0:
                # Viga curta (ex: V507-A): afasta alguns centimetros em X ou Y para nao tocar o pilar
                for dx_try, dy_try in ((6.0, 4.0), (8.0, 4.0), (5.0, 6.0)):
                    nx_t, ny_t = v["x1"] + dx_try, v["y1"] + dy_try
                    nb_t = _bbox_texto(nx_t, ny_t, v["h"], ang, v["txt"])
                    if not any(_boxes_colidem(nb_t, obs, margem=0.5) for obs in boxes_ocupados_vigas):
                        res = (nx_t, ny_t, nb_t)
                        break
            if res is not None:
                nx, ny, nbox = res
                dx = nx - v["x1"]
                dy = ny - v["y1"]
                if math.hypot(dx, dy) > 1.0:
                    dwg.edit.Move(v["addr"], dx, dy)
                    v["x1"] = nx
                    v["y1"] = ny
                    v["xc"] = nx
                    v["yc"] = ny
                    v["box"] = nbox
                    total_ajustes += 1

        boxes_ocupados_vigas.append(v["box"])

        # Verifica se secao e nome da mesma viga estao se sobrepondo no mesmo lado e separa se necessario
        if vg["secoes"]:
            for s in vg["secoes"]:
                if _boxes_colidem(v["box"], s["box"], margem=1.5):
                    _remover_box_da_lista(s["box"], boxes_ocupados_vigas)
                    t_meio = 0.5 * (vg["t_min"] + vg["t_max"])
                    comp_s = len(s["txt"]) * s["h"] * 0.85
                    lado_v = (1 if v["y1"] >= t_meio else -1) if ang == 0.0 else (1 if v["x1"] <= t_meio else -1)
                    pos_l_s = (v["box"][2] + 8.0) if ang == 0.0 else (v["box"][3] + 8.0)
                    res = encontrar_posicao_livre_na_viga(
                        vg, comp_s, s["h"], False,
                        pos_l_s, lado_v,
                        boxes_ocupados_vigas + boxes_futuros_bolinhas, lines_concreto
                    )
                    if res is not None:
                        nx, ny, nbox = res
                        dx = nx - s["x1"]
                        dy = ny - s["y1"]
                        if math.hypot(dx, dy) > 1.0:
                            dwg.edit.Move(s["addr"], dx, dy)
                            s["x1"], s["y1"], s["xc"], s["yc"], s["box"] = nx, ny, nx, ny, nbox
                            total_ajustes += 1
                    boxes_ocupados_vigas.append(s["box"])

        # Verifica se as secoes precisam de pequenos ajustes sem NUNCA pular para outro vao (maximo 35 cm)
        for s in vg["secoes"]:
            _remover_box_da_lista(s["box"], boxes_ocupados_vigas)
            obst_com_pilares_s = boxes_ocupados_vigas + [pg["box"] for pg in pilares_group]
            precisa_mover_s = (
                any(_boxes_colidem(s["box"], obs, margem=1.5) for obs in obst_com_pilares_s)
                or _box_colide_com_concreto_alheio(s["box"], vg, lines_concreto, margem=1.0)
            )
            if precisa_mover_s:
                t_meio = 0.5 * (vg["t_min"] + vg["t_max"])
                comp_s = len(s["txt"]) * s["h"] * 0.85
                if ang == 0.0:
                    lado_atual = 1 if s["y1"] >= t_meio else -1
                    pos_l_atual = s["x1"]
                else:
                    lado_atual = 1 if s["x1"] <= t_meio else -1
                    pos_l_atual = s["y1"]

                # 1o: Tenta trocar de lado no mesmo vao (sem deslizar longe)
                res = None
                for lado_teste in (-lado_atual, lado_atual):
                    if ang == 0.0:
                        cand_ty = (vg["t_max"] + 0.25 * s["h"] + 6.0) if lado_teste > 0 else (vg["t_min"] - 1.15 * s["h"] - 6.0)
                        for d_sl in (0.0, 10.0, -10.0, 20.0, -20.0, 30.0, -30.0):
                            cx = pos_l_atual + d_sl
                            cb = _bbox_texto(cx, cand_ty, s["h"], 0.0, s["txt"])
                            if not any(_boxes_colidem(cb, obs, margem=1.5) for obs in boxes_ocupados_vigas) and not _box_colide_com_concreto_alheio(cb, vg, lines_concreto, margem=1.0):
                                res = (cx, cand_ty, cb)
                                break
                    else:
                        cand_tx = (vg["t_min"] - 0.25 * s["h"] - 6.0) if lado_teste > 0 else (vg["t_max"] + 1.15 * s["h"] + 6.0)
                        for d_sl in (0.0, 10.0, -10.0, 20.0, -20.0, 30.0, -30.0):
                            cy = pos_l_atual + d_sl
                            cb = _bbox_texto(cand_tx, cy, s["h"], 90.0, s["txt"])
                            if not any(_boxes_colidem(cb, obs, margem=1.5) for obs in boxes_ocupados_vigas) and not _box_colide_com_concreto_alheio(cb, vg, lines_concreto, margem=1.0):
                                res = (cand_tx, cy, cb)
                                break
                    if res is not None:
                        break

                if res is not None:
                    nx, ny, nbox = res
                    dx = nx - s["x1"]
                    dy = ny - s["y1"]
                    if math.hypot(dx, dy) > 1.0:
                        dwg.edit.Move(s["addr"], dx, dy)
                        s["x1"] = nx
                        s["y1"] = ny
                        s["xc"] = nx
                        s["yc"] = ny
                        s["box"] = nbox
                        total_ajustes += 1

            boxes_ocupados_vigas.append(s["box"])

    # 3C. GAP CLOSING DESATIVADO: So move se identificar sobreposicao real!
    # (Textos e secoes sem sobreposicao ficam exatamente onde estao)

    # -------------------------------------------------------------------------
    # 4. REALOCACAO INTELIGENTE DE PILARES + SETA EXECUTIVA (NIVEL 221)
    # -------------------------------------------------------------------------
    ajustes_pilares = reposicionar_pilares_conflitantes(
        dwg, pilares_group, poly_pilares, lines_concreto, obstaculos_fixos,
        todos_obstaculos_cotas, texts_raw, linhas_242, linhas_221_setas,
        forcar_ciclo_se_deslocado=False
    )
    total_ajustes += ajustes_pilares

    try:
        import cotas_helper
        total_ajustes += cotas_helper._organizar_cotas_apertadas(dwg)
    except Exception:
        pass

    return total_ajustes


def cmd_organizar(eag, tqsjan):
    """
    Entry point do comando Organizar no EAG do TQS.
    Deduplica bolinhas repetidas na mesma viga, organiza vigas/secoes/bolinhas
    (trocando de lado ou deslizando na mesma viga) e posiciona pilares com seta executiva.
    """
    try:
        dwg = tqsjan.dwg
        total = executar_anti_sobreposicao(dwg)
        tqsjan.Regen()

        if total > 0:
            eag.msg.Print("G3 Plugins: %d elemento(s) organizado(s) sem sobreposicao com sucesso!" % total)
            eag.msg.PrintStatus("%d elemento(s) organizado(s)!" % total)
        else:
            eag.msg.Print("G3 Plugins: Planta de formas ja se encontra perfeitamente organizada e limpa.")
            eag.msg.PrintStatus("Planta ja organizada.")

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass


def cmd_organizar_pilar(eag, tqsjan):
    """
    Entry point do comando Pilar no EAG do TQS.
    Organiza EXCLUSIVAMENTE os identificadores de pilares que estiverem sobrepondo
    outros textos ou concreto, sem mover qualquer outro elemento da forma.
    """
    try:
        dwg = tqsjan.dwg
        total = executar_organizar_apenas_pilares(dwg)
        tqsjan.Regen()

        if total > 0:
            eag.msg.Print("G3 Plugins: %d pilar(es) reorganizado(s) sem sobreposicao com sucesso!" % total)
            eag.msg.PrintStatus("%d pilar(es) organizado(s)!" % total)
        else:
            eag.msg.Print("G3 Plugins: Todos os identificadores de pilares ja estao desimpedidos.")
            eag.msg.PrintStatus("Pilares ja desimpedidos.")

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass


def executar_organizar_apenas_pilares(dwg):
    """
    Organiza exclusivamente os identificadores de pilares (P... + b/h) que apresentarem
    sobreposicao fisica real com textos (vigas, secoes, lajes, inversoes), concreto ou outros pilares.
    Pilares desimpedidos sao mantidos 100% inalterados.
    """
    _garantir_ipocot_carregado()

    poly_pilares = []
    lines_concreto = []
    obstaculos_fixos = []
    todos_obstaculos_cotas = []
    texts_raw = []
    linhas_242 = []
    linhas_221_setas = []

    dwg.iterator.Begin()
    while True:
        tipo = dwg.iterator.Next()
        if tipo == TQSDwg.DWGTYPE_EOF:
            break
        if dwg.iterator.inBlock != 0:
            continue
        if dwg.iterator.isOpenObject != 0:
            if tipo == TQSDwg.DWGTYPE_TEXT and dwg.iterator.level in (122, 216):
                todos_obstaculos_cotas.append(_bbox_texto_exato(
                    dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2, dwg.iterator.textHeight
                ))
            continue

        l = dwg.iterator.level
        addr = dwg.iterator.GetElementReadPosition()

        if tipo == TQSDwg.DWGTYPE_POLYLINE:
            pts = [dwg.iterator.GetPolylinePt(i) for i in range(dwg.iterator.xySize)]
            if not pts:
                continue
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            dx_poly = max(xs) - min(xs)
            dy_poly = max(ys) - min(ys)
            if l in (2, 3, 4, 5) and 5.0 <= dx_poly <= 450.0 and 5.0 <= dy_poly <= 450.0 and len(pts) >= 4:
                poly_pilares.append({
                    "addr": addr, "level": l, "pts": pts,
                    "box": (min(xs), min(ys), max(xs), max(ys)),
                    "pcx": 0.5 * (min(xs) + max(xs)),
                    "pcy": 0.5 * (min(ys) + max(ys)),
                })
            elif l in (1, 2, 201):
                for i in range(len(pts) - 1):
                    lines_concreto.append((pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], l))
            elif l in (200, 205):
                obstaculos_fixos.append((min(xs), min(ys), max(xs), max(ys)))

        elif tipo == TQSDwg.DWGTYPE_LINE:
            x1, y1, x2, y2 = dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2
            if l in (1, 2, 201):
                lines_concreto.append((x1, y1, x2, y2, l))
            elif l in (200, 205):
                obstaculos_fixos.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
            elif l in (122, 216):
                todos_obstaculos_cotas.append((min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)))
            elif l == 221:
                linhas_221_setas.append({
                    "addr": addr, "x1": x1, "y1": y1, "x2": x2, "y2": y2
                })
            elif l == 242:
                linhas_242.append({
                    "addr": addr, "x1": x1, "y1": y1, "x2": x2, "y2": y2
                })

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
            else:
                texts_raw.append({
                    "addr": addr, "level": l, "txt": txt_str,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "xc": xc, "yc": yc, "h": h, "ang": ang, "box": b
                })

    # Pilares (Nivel 9 + Nivel 12) com pareamento 1-para-1 ao poligono fisico e secao
    pilares_group = _construir_pilares_group(texts_raw, poly_pilares)

    return reposicionar_pilares_conflitantes(
        dwg, pilares_group, poly_pilares, lines_concreto, obstaculos_fixos,
        todos_obstaculos_cotas, texts_raw, linhas_242, linhas_221_setas,
        forcar_ciclo_se_deslocado=True
    )


def cmd_corrigir_sobreposicao(eag, tqsjan):
    """Alias de compatibilidade para cmd_organizar."""
    cmd_organizar(eag, tqsjan)


def meucmd(eag, tqsjan):
    """Entry point padrao quando acionado diretamente."""
    cmd_organizar(eag, tqsjan)
