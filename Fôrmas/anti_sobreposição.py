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

import math
from TQS import TQSUtil, TQSDwg

try:
    TQSUtil.LoadDll("IPOCOT.DLL")
except Exception:
    pass


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


def _bbox_texto(x1, y1, h, ang, texto_str):
    """
    Calcula bounding box (xmin, ymin, xmax, ymax) de um texto no TQS.
    Cada caractere ocupa aproximadamente 0.85 * h na fonte padrao TQS.
    """
    comp = len(texto_str) * h * 0.85
    a = _normalizar_angulo(ang)
    if a == 90.0:
        return (x1 - h * 1.15, y1, x1 + h * 0.25, y1 + comp)
    else:
        return (x1, y1 - h * 0.25, x1 + comp, y1 + h * 1.15)


def _boxes_colidem(b1, b2, margem=2.0):
    """Verifica se dois bounding boxes (xmin, ymin, xmax, ymax) se sobrepoem com margem."""
    return not (
        b1[2] + margem < b2[0] or
        b1[0] - margem > b2[2] or
        b1[3] + margem < b2[1] or
        b1[1] - margem > b2[3]
    )


def _segmento_colide_box(x1, y1, x2, y2, box, margem=1.0):
    """Verifica se um segmento de reta cruza ou toca um bounding box."""
    bx_seg = (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
    if not _boxes_colidem(bx_seg, box, margem=margem):
        return False
    if abs(x1 - x2) <= 3.0:  # Segmento vertical
        xv = 0.5 * (x1 + x2)
        if (box[0] - margem) <= xv <= (box[2] + margem):
            return max(box[1], min(y1, y2)) <= min(box[3], max(y1, y2))
        return False
    elif abs(y1 - y2) <= 3.0:  # Segmento horizontal
        yh = 0.5 * (y1 + y2)
        if (box[1] - margem) <= yh <= (box[3] + margem):
            return max(box[0], min(x1, x2)) <= min(box[2], max(x1, x2))
        return False
    return True


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
        if abs(y1 - y2) <= 3.0 and abs(x1 - x2) > 10.0:
            segs_h.append((0.5 * (y1 + y2), min(x1, x2), max(x1, x2)))
        elif abs(x1 - x2) <= 3.0 and abs(y1 - y2) > 10.0:
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


def associar_elemento_a_viga(xc, yc, ang, vigas_geom):
    """
    Associa uma secao 'xx/xx', bolinha '(xx)' ou texto 'VIGA INVERTIDA' a sua viga
    branca continua correspondente verificando tanto a faixa transversal [t_min, t_max]
    quanto a extensao longitudinal [l_min, l_max].
    """
    cands = []
    for vg in vigas_geom:
        if abs((ang - vg["ang"]) % 180.0) < 5.0:
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
                if dt <= 45.0 and dl <= 45.0:
                    cands.append((dt + dl * 0.5, abs(xc - vg["l_txt"]), vg))
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
                if dt <= 45.0 and dl <= 45.0:
                    cands.append((dt + dl * 0.5, abs(yc - vg["l_txt"]), vg))
    if cands:
        cands.sort(key=lambda x: (x[0], x[1]))
        return cands[0][2]
    return None


def _box_colide_com_concreto_alheio(box, vg, lines_concreto, margem=1.0):
    """
    Verifica se o box colide com alguma linha de concreto que NAO seja uma das duas
    faces paralelas da propria viga 'vg'.
    """
    for lx1, ly1, lx2, ly2, _ in lines_concreto:
        if vg is not None:
            if vg["ang"] == 0.0 and abs(ly1 - ly2) <= 3.0:
                ym = 0.5 * (ly1 + ly2)
                if vg["t_min"] - 12.0 <= ym <= vg["t_max"] + 12.0:
                    continue
            elif vg["ang"] == 90.0 and abs(lx1 - lx2) <= 3.0:
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
            t_pos = vg["t_max"] + 0.25 * tam_t + 6.0
            t_pos_alto = vg["t_max"] + 0.25 * tam_t + 35.0
            t_neg = vg["t_min"] - 1.15 * tam_t - 6.0
            t_neg_baixo = vg["t_min"] - 1.15 * tam_t - 35.0
            lados_testar = [t_pos, t_pos_alto, t_neg, t_neg_baixo] if lado_pref >= 0 else [t_neg, t_neg_baixo, t_pos, t_pos_alto]
        else:
            t_pos = vg["t_min"] - 0.25 * tam_t - 6.0
            t_pos_afast = vg["t_min"] - 0.25 * tam_t - 26.0
            t_neg = vg["t_max"] + 1.15 * tam_t + 6.0
            t_neg_afast = vg["t_max"] + 1.15 * tam_t + 26.0
            lados_testar = [t_pos, t_pos_afast, t_neg, t_neg_afast] if lado_pref >= 0 else [t_neg, t_neg_afast, t_pos, t_pos_afast]

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
        # Toca concreto do pilar
        d1 = math.hypot(l221["x1"] - pcx, l221["y1"] - pcy)
        d2 = math.hypot(l221["x2"] - pcx, l221["y2"] - pcy)
        toca_poly = min(d1, d2) <= raio_busca
        if p_box is not None:
            if (p_box[0] - 15.0 <= l221["x1"] <= p_box[2] + 15.0 and p_box[1] - 15.0 <= l221["y1"] <= p_box[3] + 15.0) or \
               (p_box[0] - 15.0 <= l221["x2"] <= p_box[2] + 15.0 and p_box[1] - 15.0 <= l221["y2"] <= p_box[3] + 15.0):
                toca_poly = True

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
                if min(d_old1, d_old2) <= 25.0:
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
    Varre as linhas no Nivel 221 e apaga quaisquer patamares horizontais orfaos:
    linhas horizontais que nao tem leader diagonal conectado e nao tem nenhum texto
    de pilar logo acima delas no desenho.
    """
    apagadas = 0
    remover = []
    for i, l in enumerate(linhas_221_setas):
        # Verifica se e horizontal (patamar)
        if abs(l["y1"] - l["y2"]) <= 1.5:
            # Verifica se tem algum leader diagonal conectado a ela
            tem_leader = False
            for j, other in enumerate(linhas_221_setas):
                if i == j:
                    continue
                d11 = math.hypot(l["x1"] - other["x1"], l["y1"] - other["y1"])
                d12 = math.hypot(l["x1"] - other["x2"], l["y1"] - other["y2"])
                d21 = math.hypot(l["x2"] - other["x1"], l["y2"] - other["y1"])
                d22 = math.hypot(l["x2"] - other["x2"], l["y2"] - other["y2"])
                if min(d11, d12, d21, d22) <= 3.0:
                    tem_leader = True
                    break

            # Verifica se algum pilar esta imediatamente acima deste patamar
            y_lin = 0.5 * (l["y1"] + l["y2"])
            xmin_lin = min(l["x1"], l["x2"])
            xmax_lin = max(l["x1"], l["x2"])
            tem_texto_acima = False
            for pg in pilares_group:
                bx = pg["box"]
                p9_y = pg["p9"]["y1"]
                if abs(y_lin - (p9_y - 3.0)) <= 6.0:
                    if bx[2] >= xmin_lin - 10.0 and bx[0] <= xmax_lin + 10.0:
                        tem_texto_acima = True
                        break

            # Se for um patamar isolado sem leader e sem texto de pilar em cima, e orfao!
            if not tem_leader and not tem_texto_acima:
                try:
                    dwg.edit.Erase(l["addr"])
                    apagadas += 1
                except Exception:
                    pass
                remover.append(l)

    for r in remover:
        if r in linhas_221_setas:
            linhas_221_setas.remove(r)

    return apagadas


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
            if l in (2, 3, 4, 5) and 8.0 <= dx_poly <= 180.0 and 8.0 <= dy_poly <= 180.0 and len(pts) >= 4:
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
            elif l in (210, 241, 200, 205):
                obstaculos_fixos.append((min(xs), min(ys), max(xs), max(ys)))

        elif tipo == TQSDwg.DWGTYPE_LINE:
            x1, y1, x2, y2 = dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2
            if l in (1, 2, 201):
                lines_concreto.append((x1, y1, x2, y2, l))
            elif l in (210, 241, 200, 205):
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
            b = _bbox_texto(x1, y1, h, ang, txt_str)

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

    # Pilares (Nivel 9 + Nivel 12) com pareamento 1-para-1 ao poligono fisico
    p9_list = [tx for tx in texts_raw if tx["level"] == 9 and tx["txt"].upper().startswith("P")]
    p12_list = [tx for tx in texts_raw if tx["level"] == 12 and "/" in tx["txt"]]
    pilares_group = []
    used_12_idx = set()

    poly_usados = set()
    pilares_com_cands = []
    for p9 in p9_list:
        cands_p = []
        for idx_pb, pb in enumerate(poly_pilares):
            dp = math.hypot(p9["x1"] - pb["pcx"], p9["y1"] - pb["pcy"])
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

    for p9 in p9_list:
        best_12 = None
        min_d = float("inf")
        for i, p12 in enumerate(p12_list):
            if i in used_12_idx:
                continue
            d = math.hypot(p9["x1"] - p12["x1"], p9["y1"] - p12["y1"])
            if d <= 45.0 and d < min_d:
                min_d = d
                best_12 = (i, p12)
        p12_obj = None
        if best_12 is not None:
            used_12_idx.add(best_12[0])
            p12_obj = best_12[1]

        bp9 = p9["box"]
        bp12 = p12_obj["box"] if p12_obj else bp9
        bconj = (min(bp9[0], bp12[0]), min(bp9[1], bp12[1]), max(bp9[2], bp12[2]), max(bp9[3], bp12[3]))
        p_poly = map_p9_poly.get(id(p9))

        pilares_group.append({
            "p9": p9,
            "p12": p12_obj,
            "dx_sec": (p12_obj["x1"] - p9["x1"]) if p12_obj else 0.0,
            "dy_sec": (p12_obj["y1"] - p9["y1"]) if p12_obj else -18.0,
            "box": bconj,
            "larg_conj": bconj[2] - bconj[0],
            "alt_conj": bconj[3] - bconj[1],
            "p_poly": p_poly,
        })

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
            comp_vi = len(vi["txt"]) * vi["h"] * 0.85
            colide_com_secoes = any(_boxes_colidem(vi["box"], s["box"], margem=2.0) for s in vg["secoes"])
            colide_com_nome = _boxes_colidem(vi["box"], vg["viga"]["box"], margem=2.0)
            # Move apenas se colidir com outro texto, secao, pilar, ou se ultrapassar [l_min, l_max] da viga!
            obst_com_pilares_vi = boxes_ocupados_vigas + [pg["box"] for pg in pilares_group]
            precisa_mover_vi = (
                any(_boxes_colidem(vi["box"], obs, margem=5.0) for obs in obst_com_pilares_vi)
                or colide_com_secoes
                or colide_com_nome
                or _box_colide_com_concreto_alheio(vi["box"], vg, lines_concreto, margem=1.0)
            )
            if precisa_mover_vi:
                t_meio = 0.5 * (vg["t_min"] + vg["t_max"])
                if ang == 0.0:
                    lado_atual = 1 if vi["y1"] >= t_meio else -1
                    pos_l_atual = vi["x1"]
                else:
                    lado_atual = 1 if vi["x1"] <= t_meio else -1
                    pos_l_atual = vi["y1"]

                # 1o: Se colide com secao, tenta posicionar inline logo apos ela com espacamento limpo
                res = None
                s_col = None
                for s_cand in vg["secoes"]:
                    if _boxes_colidem(vi["box"], s_cand["box"], margem=2.0):
                        s_col = s_cand
                        break
                if s_col is not None:
                    if ang == 0.0:
                        cand_x = s_col["box"][2] + 12.0
                        cand_y = s_col["y1"]
                        cand_bx = _bbox_texto(cand_x, cand_y, vi["h"], 0.0, vi["txt"])
                        if (cand_x + comp_vi <= vg["l_max"] - 4.0
                            and not any(_boxes_colidem(cand_bx, ob, margem=2.0) for ob in boxes_ocupados_vigas)
                            and not _box_colide_com_concreto_alheio(cand_bx, vg, lines_concreto, margem=1.0)):
                            res = (cand_x, cand_y, cand_bx)
                    else:
                        cand_x = s_col["x1"]
                        cand_y = s_col["box"][3] + 12.0
                        cand_bx = _bbox_texto(cand_x, cand_y, vi["h"], 90.0, vi["txt"])
                        if (cand_y + comp_vi <= vg["l_max"] - 4.0
                            and not any(_boxes_colidem(cand_bx, ob, margem=2.0) for ob in boxes_ocupados_vigas)
                            and not _box_colide_com_concreto_alheio(cand_bx, vg, lines_concreto, margem=1.0)):
                            res = (cand_x, cand_y, cand_bx)

                # 2o: Prioriza o lado oposto da viga no mesmo trecho
                if res is None:
                    obst_com_pilares_txt = boxes_ocupados_vigas + [pg["box"] for pg in pilares_group]
                    res = encontrar_posicao_livre_na_viga(
                        vg, comp_vi, vi["h"], False,
                        pos_l_atual, -lado_atual,
                        obst_com_pilares_txt, lines_concreto
                    )
                if res is None:
                    res = encontrar_posicao_livre_na_viga(
                        vg, comp_vi, vi["h"], False,
                        pos_l_atual, -lado_atual,
                        boxes_ocupados_vigas, lines_concreto
                    )
                if res is None:
                    res = encontrar_posicao_livre_na_viga(
                        vg, comp_vi, vi["h"], False,
                        pos_l_atual, lado_atual,
                        boxes_ocupados_vigas, lines_concreto
                    )

                if res is not None:
                    nx, ny, nbox = res
                    dx = nx - vi["x1"]
                    dy = ny - vi["y1"]
                    if math.hypot(dx, dy) > 1.0:
                        dwg.edit.Move(vi["addr"], dx, dy)
                        vi["x1"] = nx
                        vi["y1"] = ny
                        vi["xc"] = nx
                        vi["yc"] = ny
                        vi["box"] = nbox
                        total_ajustes += 1

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
    obstaculos_para_pilar = (
        list(boxes_ocupados_vigas)
        + [tx["box"] for tx in texts_raw if tx["level"] not in (28, 29, 9, 12)]
    )

    for p_grp in pilares_group:
        p9 = p_grp["p9"]
        p12 = p_grp["p12"]
        p_poly = p_grp["p_poly"]
        b_conj = p_grp["box"]

        colide = False
        for obs in obstaculos_para_pilar:
            if _boxes_colidem(b_conj, obs, margem=5.0):
                colide = True
                break

        if not colide:
            for lx1, ly1, lx2, ly2, _ in lines_concreto:
                if _segmento_colide_box(lx1, ly1, lx2, ly2, b_conj, margem=1.0):
                    colide = True
                    break

        if not colide:
            if any(_boxes_colidem(b_conj, p_outro["box"], margem=5.0) for p_outro in pilares_group if p_outro is not p_grp):
                colide = True

        if not colide:
            continue

        pcx = p_poly["pcx"] if p_poly else p9["x1"]
        pcy = p_poly["pcy"] if p_poly else p9["y1"]
        larg_conj = p_grp["larg_conj"]
        alt_conj = p_grp["alt_conj"]
        p_box = p_poly["box"] if p_poly else (pcx - 12.5, pcy - 12.5, pcx + 12.5, pcy + 12.5)

        candidatos = []
        for r in (35.0, 50.0, 65.0, 80.0, 95.0, 115.0, 140.0):
            candidatos.append((pcx + r, pcy + r * 0.7))
            candidatos.append((pcx - r - larg_conj, pcy + r * 0.7))
            candidatos.append((pcx + r, pcy - r * 0.7 - alt_conj))
            candidatos.append((pcx - r - larg_conj, pcy - r * 0.7 - alt_conj))
            candidatos.append((pcx + r + 5.0, pcy - 0.5 * alt_conj))
            candidatos.append((pcx - r - larg_conj - 5.0, pcy - 0.5 * alt_conj))
            candidatos.append((pcx - 0.5 * larg_conj, pcy + r + 5.0))
            candidatos.append((pcx - 0.5 * larg_conj, pcy - r - alt_conj - 5.0))

        escolhido = None
        for cand_x, cand_y in candidatos:
            cb9 = _bbox_texto(cand_x, cand_y, p9["h"], p9["ang"], p9["txt"])
            cb12 = _bbox_texto(
                cand_x + p_grp["dx_sec"], cand_y + p_grp["dy_sec"],
                p12["h"] if p12 else 12.0, p9["ang"], p12["txt"] if p12 else ""
            )
            c_conj = (min(cb9[0], cb12[0]), min(cb9[1], cb12[1]), max(cb9[2], cb12[2]), max(cb9[3], cb12[3]))

            if any(_boxes_colidem(c_conj, p_outro["box"], margem=5.0) for p_outro in pilares_group if p_outro is not p_grp):
                continue
            if any(_boxes_colidem(c_conj, obs_p, margem=5.0) for obs_p in obstaculos_para_pilar):
                continue

            corte_concreto = False
            for lx1, ly1, lx2, ly2, _ in lines_concreto:
                if _segmento_colide_box(lx1, ly1, lx2, ly2, c_conj, margem=1.0):
                    corte_concreto = True
                    break
            if corte_concreto:
                continue

            escolhido = (cand_x, cand_y, c_conj)
            break

        if escolhido is not None:
            nx, ny, novo_box = escolhido
            dx = nx - p9["x1"]
            dy = ny - p9["y1"]

            # Apaga qualquer chamada anterior (nativa 242 ou executiva 221 com patamar)
            apagar_chamadas_antigas_do_pilar(
                dwg, pcx, pcy, p_box, b_conj, linhas_242, linhas_221_setas, raio_busca=60.0
            )

            dwg.edit.Move(p9["addr"], dx, dy)
            p9["x1"] = nx
            p9["y1"] = ny
            p9["box"] = _bbox_texto(nx, ny, p9["h"], p9["ang"], p9["txt"])

            if p12 is not None:
                dwg.edit.Move(p12["addr"], dx, dy)
                p12["x1"] += dx
                p12["y1"] += dy
                p12["box"] = _bbox_texto(p12["x1"], p12["y1"], p12["h"], p12["ang"], p12["txt"])

            p_grp["box"] = novo_box
            obstaculos_para_pilar.append(novo_box)

            y_patamar = ny - 3.0
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
            if dist_seta >= 20.0:
                desenhar_seta_chamada_executiva(
                    dwg, x_fim_patamar, x_joelho, y_patamar, x_seta, y_seta, linhas_221_setas=linhas_221_setas
                )

            total_ajustes += 1

    # 5. LIMPEZA DE CHAMADAS ORFAS (NIVEL 221):
    # Apaga quaisquer linhas horizontais de patamar orfas deixadas no desenho
    # (sem leader diagonal conectado e sem texto de pilar em cima)
    limpar_chamadas_orfas_221(dwg, linhas_221_setas, pilares_group)

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


def cmd_corrigir_sobreposicao(eag, tqsjan):
    """Alias de compatibilidade para cmd_organizar."""
    cmd_organizar(eag, tqsjan)


def meucmd(eag, tqsjan):
    """Entry point padrao quando acionado diretamente."""
    cmd_organizar(eag, tqsjan)
