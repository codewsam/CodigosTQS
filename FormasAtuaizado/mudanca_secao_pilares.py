# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - DETALHE MUDANCA DE SECAO DE PILARES (TQS EAG)
================================================================================
Modulo dedicado a deteccao de pilares com mudanca de secao (Nivel 244 + niveis
inferiores 2/3/4/5), agrupamento, desenho ampliado (escala 1:25) e cotagem.
================================================================================
"""
import math
from TQS import TQSUtil, TQSDwg
import cotas_helper


def cmd_detalhe_mudanca_secao_pilares(eag, tqsjan):
    """
    Identifica todos os pilares da planta que possuem mudanca de secao entre o lance
    inferior (poligonos nos niveis 2/3/4/5) e o lance superior (poligono magenta no
    nivel 244 / texto '(sup)'), agrupa pilares geometricamente identicos (ex: P2/P5),
    ordena numericamente e desenha o quadro de detalhe organizado e cotado na lateral
    direita da planta de formas.
    """
    import re
    import importlib
    importlib.reload(cotas_helper)

    try:
        dwg = tqsjan.dwg

        # 0. Remove quadro de detalhe anterior (se o usuario clicar no botao mais de uma vez),
        # evitando duplicar o quadro ou gerar 'P17/P17'
        quadros_antigos = []
        titulos_det = []
        linhas_moldura = []
        dwg.iterator.Begin()
        while True:
            tipo = dwg.iterator.Next()
            if tipo == TQSDwg.DWGTYPE_EOF:
                break
            if dwg.iterator.inBlock != 0:
                continue
            if tipo == TQSDwg.DWGTYPE_TEXT and "DETALHE MUDANCA DE SECAO DE PILARES" in dwg.iterator.text.upper():
                titulos_det.append((dwg.iterator.x1, dwg.iterator.y1))
            elif tipo == TQSDwg.DWGTYPE_LINE and dwg.iterator.level == 0 and dwg.iterator.color == 7:
                linhas_moldura.append((dwg.iterator.x1, dwg.iterator.y1, dwg.iterator.x2, dwg.iterator.y2))

        for tx_d, ty_d in titulos_det:
            # Encontra a moldura retangular (nivel 0, cor 7) que envolve esse titulo
            xs_m = []
            ys_m = []
            for lx1, ly1, lx2, ly2 in linhas_moldura:
                if min(lx1, lx2) - 80.0 <= tx_d <= max(lx1, lx2) + 80.0 and min(ly1, ly2) - 80.0 <= ty_d <= max(ly1, ly2) + 80.0:
                    xs_m.extend([lx1, lx2])
                    ys_m.extend([ly1, ly2])
            if xs_m and ys_m:
                quadros_antigos.append((min(xs_m) - 5.0, min(ys_m) - 5.0, max(xs_m) + 5.0, max(ys_m) + 5.0))

        if quadros_antigos:
            addrs_apagar = []
            dwg.iterator.Begin()
            while True:
                tipo = dwg.iterator.Next()
                if tipo == TQSDwg.DWGTYPE_EOF:
                    break
                if dwg.iterator.inBlock != 0 or dwg.iterator.isOpenObject != 0:
                    continue
                addr_e = dwg.iterator.GetElementReadPosition()
                ex = ey = None
                if tipo == TQSDwg.DWGTYPE_OBJECT and dwg.iterator.objectName == "IPOCOT":
                    # Verifica no proximo sub-elemento ou usa coletor de cotas abaixo
                    continue
                elif tipo == TQSDwg.DWGTYPE_TEXT:
                    ex, ey = dwg.iterator.x1, dwg.iterator.y1
                elif tipo == TQSDwg.DWGTYPE_LINE:
                    ex, ey = 0.5 * (dwg.iterator.x1 + dwg.iterator.x2), 0.5 * (dwg.iterator.y1 + dwg.iterator.y2)
                elif tipo == TQSDwg.DWGTYPE_POLYLINE:
                    pts_e = [dwg.iterator.GetPolylinePt(i) for i in range(dwg.iterator.xySize)]
                    if pts_e:
                        ex = 0.5 * (min(p[0] for p in pts_e) + max(p[0] for p in pts_e))
                        ey = 0.5 * (min(p[1] for p in pts_e) + max(p[1] for p in pts_e))
                if ex is not None:
                    if any(qx1 <= ex <= qx2 and qy1 <= ey <= qy2 for qx1, qy1, qx2, qy2 in quadros_antigos):
                        addrs_apagar.append(addr_e)
            for c_old in cotas_helper.coletar_cotas_existentes(dwg):
                if c_old.get("addr"):
                    cx_o, cy_o = c_old.get("x", 0.0), c_old.get("y", 0.0)
                    if any(qx1 <= cx_o <= qx2 and qy1 <= cy_o <= qy2 for qx1, qy1, qx2, qy2 in quadros_antigos):
                        addrs_apagar.append(c_old["addr"])
            for addr_del in set(addrs_apagar):
                try:
                    dwg.edit.Erase(addr_del)
                except Exception:
                    pass

        sup_polys = []
        inf_polys = []
        txts_p9 = []
        txts_p12 = []

        dwg_xmin = float("inf")
        dwg_xmax = float("-inf")
        dwg_ymin = float("inf")
        dwg_ymax = float("-inf")
        conc_ymin = float("inf")
        conc_ymax = float("-inf")

        def _acc_bbox(x1, y1, x2, y2):
            nonlocal dwg_xmin, dwg_xmax, dwg_ymin, dwg_ymax
            if x1 < dwg_xmin: dwg_xmin = x1
            if x2 > dwg_xmax: dwg_xmax = x2
            if y1 < dwg_ymin: dwg_ymin = y1
            if y2 > dwg_ymax: dwg_ymax = y2

        dwg.iterator.Begin()
        while True:
            tipo = dwg.iterator.Next()
            if tipo == TQSDwg.DWGTYPE_EOF:
                break
            nivel = dwg.iterator.level

            # Acumula o bounding box global de TODOS os elementos visiveis (incluindo blocos de corte, linhas de corte, cotas e textos)
            if tipo == TQSDwg.DWGTYPE_POLYLINE:
                pts_all = [dwg.iterator.GetPolylinePt(i) for i in range(dwg.iterator.xySize)]
                if pts_all:
                    xs_a = [p[0] for p in pts_all]
                    ys_a = [p[1] for p in pts_all]
                    _acc_bbox(min(xs_a), min(ys_a), max(xs_a), max(ys_a))
                    if dwg.iterator.inBlock == 0 and nivel in (1, 2, 3, 4, 5, 201, 244):
                        conc_ymin = min(conc_ymin, min(ys_a))
                        conc_ymax = max(conc_ymax, max(ys_a))
            elif tipo == TQSDwg.DWGTYPE_LINE:
                _acc_bbox(
                    min(dwg.iterator.x1, dwg.iterator.x2),
                    min(dwg.iterator.y1, dwg.iterator.y2),
                    max(dwg.iterator.x1, dwg.iterator.x2),
                    max(dwg.iterator.y1, dwg.iterator.y2),
                )
                if dwg.iterator.inBlock == 0 and nivel in (1, 2, 201):
                    conc_ymin = min(conc_ymin, dwg.iterator.y1, dwg.iterator.y2)
                    conc_ymax = max(conc_ymax, dwg.iterator.y1, dwg.iterator.y2)
            elif tipo == TQSDwg.DWGTYPE_TEXT:
                _acc_bbox(
                    min(dwg.iterator.x1, dwg.iterator.x2),
                    min(dwg.iterator.y1, dwg.iterator.y2),
                    max(dwg.iterator.x1, dwg.iterator.x2),
                    max(dwg.iterator.y1, dwg.iterator.y2),
                )
            elif tipo == TQSDwg.DWGTYPE_BLOCK:
                _acc_bbox(dwg.iterator.x1 - 40.0, dwg.iterator.y1 - 40.0, dwg.iterator.x1 + 40.0, dwg.iterator.y1 + 40.0)
            elif tipo in (TQSDwg.DWGTYPE_CIRCLE, TQSDwg.DWGTYPE_ARC):
                r_e = getattr(dwg.iterator, "radius", 0.0)
                _acc_bbox(dwg.iterator.xc - r_e, dwg.iterator.yc - r_e, dwg.iterator.xc + r_e, dwg.iterator.yc + r_e)

            if dwg.iterator.inBlock != 0:
                continue

            if tipo == TQSDwg.DWGTYPE_POLYLINE:
                pts = [dwg.iterator.GetPolylinePt(i) for i in range(dwg.iterator.xySize)]
                if not pts:
                    continue
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                bx = (min(xs), min(ys), max(xs), max(ys))
                dx_b = bx[2] - bx[0]
                dy_b = bx[3] - bx[1]
                if nivel == 244 and len(pts) >= 4 and dx_b >= 2.0 and dy_b >= 2.0:
                    sup_polys.append({
                        "lvl": nivel,
                        "col": dwg.iterator.color,
                        "sty": dwg.iterator.style,
                        "filled": bool(getattr(dwg.iterator, "isFilled", 0)),
                        "bx": bx,
                        "pts": pts,
                    })
                elif nivel in (2, 3, 4, 5) and len(pts) >= 4 and 2.0 <= dx_b <= 450.0 and 2.0 <= dy_b <= 450.0:
                    inf_polys.append({
                        "lvl": nivel,
                        "col": dwg.iterator.color,
                        "sty": dwg.iterator.style,
                        "filled": bool(getattr(dwg.iterator, "isFilled", 0)),
                        "bx": bx,
                        "pts": pts,
                    })
            elif tipo == TQSDwg.DWGTYPE_TEXT:
                txt = dwg.iterator.text.strip()
                if not txt:
                    continue
                x1, y1 = dwg.iterator.x1, dwg.iterator.y1
                if nivel == 9 and txt.upper().startswith("P"):
                    txts_p9.append({"txt": txt, "x": x1, "y": y1})
                elif nivel == 12:
                    txts_p12.append({"txt": txt, "x": x1, "y": y1})

        if not sup_polys:
            eag.msg.Print("G3 Plugins: Nenhum pilar com mudanca de secao (nivel 244 / sup) encontrado.")
            eag.msg.PrintStatus("Nenhum pilar com mudanca de secao encontrado.")
            return

        def _num_pilar(nome):
            m = re.search(r"(\d+)", nome or "")
            return (int(m.group(1)), nome or "") if m else (999999, nome or "")

        def _fmt_dim(v):
            r = round(float(v), 1)
            return str(int(round(r))) if abs(r - round(r)) < 0.05 else ("%.1f" % r)

        # Associa cada poligono superior (nivel 244) aos poligonos inferiores (niveis 2/3/4/5) e textos
        itens = []
        usados_p9 = set()
        for sp in sup_polys:
            sx1, sy1, sx2, sy2 = sp["bx"]
            infs = [
                ip for ip in inf_polys
                if not (ip["bx"][2] + 2.5 < sx1 or ip["bx"][0] - 2.5 > sx2 or ip["bx"][3] + 2.5 < sy1 or ip["bx"][1] - 2.5 > sy2)
            ]
            if not infs:
                continue

            tx1 = min([sx1] + [ip["bx"][0] for ip in infs])
            ty1 = min([sy1] + [ip["bx"][1] for ip in infs])
            tx2 = max([sx2] + [ip["bx"][2] for ip in infs])
            ty2 = max([sy2] + [ip["bx"][3] for ip in infs])

            # Confirma que realmente houve mudanca de secao (dimensao total difere da secao sup)
            if abs((tx2 - tx1) - (sx2 - sx1)) < 0.5 and abs((ty2 - ty1) - (sy2 - sy1)) < 0.5:
                continue

            cx = 0.5 * (tx1 + tx2)
            cy = 0.5 * (ty1 + ty2)

            melhor_p9 = None
            melhor_i9 = None
            min_d9 = float("inf")
            for idx9, t9 in enumerate(txts_p9):
                if idx9 in usados_p9:
                    continue
                d = math.hypot(t9["x"] - cx, t9["y"] - cy)
                if d < min_d9 and d <= 300.0:
                    min_d9 = d
                    melhor_p9 = t9
                    melhor_i9 = idx9

            if melhor_i9 is not None:
                usados_p9.add(melhor_i9)
                nome = melhor_p9["txt"]
                ref_x, ref_y = melhor_p9["x"], melhor_p9["y"]
            else:
                nome = "P?"
                ref_x, ref_y = cx, cy

            # Busca textos de secao (nivel 12) proximos ao titulo do pilar
            cands_12 = sorted(
                [t12 for t12 in txts_p12 if math.hypot(t12["x"] - ref_x, t12["y"] - ref_y) <= 120.0],
                key=lambda t: math.hypot(t["x"] - ref_x, t["y"] - ref_y)
            )
            sec_sup = next((t["txt"] for t in cands_12 if "sup" in t["txt"].lower()), None)
            sec_inf = next((t["txt"] for t in cands_12 if "sup" not in t["txt"].lower() and "/" in t["txt"]), None)
            if not sec_inf:
                sec_inf = "%s/%s" % (_fmt_dim(min(tx2 - tx1, ty2 - ty1)), _fmt_dim(max(tx2 - tx1, ty2 - ty1)))
            if not sec_sup:
                sec_sup = "%s/%s (sup)" % (_fmt_dim(min(sx2 - sx1, sy2 - sy1)), _fmt_dim(max(sx2 - sx1, sy2 - sy1)))

            # Normaliza geometria relativa a (tx1, ty1)
            tot_w = tx2 - tx1
            tot_h = ty2 - ty1
            off_esq = round(sx1 - tx1, 1)
            off_dir = round(tx2 - sx2, 1)
            off_inf = round(sy1 - ty1, 1)
            off_sup = round(ty2 - sy2, 1)
            chave_geom = (
                round(tot_w, 1), round(tot_h, 1),
                off_esq, off_dir, off_inf, off_sup,
                sec_inf.strip(), sec_sup.strip()
            )

            itens.append({
                "nome": nome,
                "sec_inf": sec_inf,
                "sec_sup": sec_sup,
                "tot_bx": (tx1, ty1, tx2, ty2),
                "sup_bx": (sx1, sy1, sx2, sy2),
                "sup_poly": sp,
                "inf_polys": infs,
                "tot_w": tot_w,
                "tot_h": tot_h,
                "chave_geom": chave_geom,
            })

        if not itens:
            eag.msg.Print("G3 Plugins: Nenhum pilar com reducao/mudanca de secao efetiva encontrado.")
            eag.msg.PrintStatus("Nenhuma mudanca de secao encontrada.")
            return

        # Ordena numericamente (P1, P2, P3, ...) e agrupa pilares geometricamente identicos (ex: P2/P5)
        itens.sort(key=lambda it: _num_pilar(it["nome"]))
        grupos = []
        por_chave = {}
        for it in itens:
            k = it["chave_geom"]
            if k in por_chave:
                if it["nome"] not in por_chave[k]["nomes"]:
                    por_chave[k]["nomes"].append(it["nome"])
            else:
                g = dict(it)
                g["nomes"] = [it["nome"]]
                por_chave[k] = g
                grupos.append(g)

        for g in grupos:
            g["titulo"] = "/".join(g["nomes"])

        # Define posicionamento do quadro na lateral direita, centralizado mais abaixo junto a planta
        if dwg_xmax == float("-inf"):
            x_base_quadro = 200.0
            y_topo_quadro = 200.0
        else:
            x_base_quadro = dwg_xmax + 180.0
            if conc_ymin != float("inf") and conc_ymax != float("-inf"):
                y_topo_quadro = 0.5 * (conc_ymin + conc_ymax)
            else:
                y_topo_quadro = 0.5 * (dwg_ymin + dwg_ymax)

        escala = 2.0
        fator_cota = 1.0 / escala  # 0.5 para cotas reais em escala 2x (1:25)
        max_por_linha = 8
        gap_x = 120.0
        gap_y = 180.0
        margem_quadro = 60.0

        # Divide em linhas
        linhas = [grupos[i:i + max_por_linha] for i in range(0, len(grupos), max_por_linha)]

        old_lvl = dwg.draw.level
        old_col = dwg.draw.color
        old_sty = dwg.draw.style
        #FONTE CONTA
        try:
            cotas_helper.configurar_estilo_cotas(
                dwg,
                altura_texto=0.20,
                bloco="TICK",
                nivel=216,
                extensao_linha=0.20,
                extensao_chamada=0.20,
                folga_chamada=0.10,
                tamanho_tick=0.20,
                fator_comprimento=fator_cota,
            )

            def _copiar_poly_escalada(poly_info, tx1_ref, ty1_ref, ox, oy):
                """Copia fielmente a polyline do pilar original (mesmo nivel, cor, estilo e preenchimento) na escala 2x."""
                dwg.draw.level = int(poly_info["lvl"])
                dwg.draw.color = int(poly_info["col"])
                dwg.draw.style = int(poly_info.get("sty", 0))
                dwg.draw.PolyStart()
                for px, py in poly_info["pts"]:
                    dwg.draw.PolyEnterPoint(ox + (px - tx1_ref) * escala, oy + (py - ty1_ref) * escala)
                if poly_info.get("filled", False):
                    dwg.draw.PolylineFilled()
                else:
                    dwg.draw.Polyline()

            def _precisa_arredondar(dist_desenho):
                val_real = abs(dist_desenho) * fator_cota
                val_arr = cotas_helper.arredondar_valor_cota(val_real)
                return abs(val_real - val_arr) >= 0.05

            q_xmin = x_base_quadro
            q_xmax = x_base_quadro
            q_ymax = y_topo_quadro
            q_ymin = y_topo_quadro

            # Titulo geral do quadro
            dwg.draw.level = 9
            dwg.draw.color = -1
            dwg.draw.style = 0
            titulo_geral = "DETALHE MUDANCA DE SECAO DE PILARES (ESC. 1:25)"
            dwg.draw.Text(x_base_quadro + margem_quadro, y_topo_quadro - 35.0, 22.0, 0.0, titulo_geral)
            q_xmax = max(q_xmax, x_base_quadro + margem_quadro + len(titulo_geral) * 23.0 + margem_quadro)

            y_cursor_top = y_topo_quadro - 175.0

            for row in linhas:
                max_h_row = max(g["tot_h"] * escala for g in row)
                x_cursor = x_base_quadro + margem_quadro + 55.0

                for g in row:
                    tx1, ty1, tx2, ty2 = g["tot_bx"]
                    sx1, sy1, sx2, sy2 = g["sup_bx"]
                    tw_d = g["tot_w"] * escala
                    th_d = g["tot_h"] * escala

                    # Alinha todos os pilares da linha pela face superior
                    ox = x_cursor
                    oy = y_cursor_top - th_d

                    # 1. Textos do cabecalho do pilar (P..., secao inf, secao sup)
                    y_txt_base = y_cursor_top + 56.0
                    dwg.draw.level = 9
                    dwg.draw.color = -1
                    dwg.draw.style = 0
                    dwg.draw.Text(ox, y_txt_base + 36.0, 18.0, 0.0, g["titulo"])
                    dwg.draw.level = 12
                    dwg.draw.Text(ox, y_txt_base + 18.0, 11.0, 0.0, g["sec_inf"])
                    dwg.draw.Text(ox, y_txt_base, 11.0, 0.0, g["sec_sup"])

                    larg_hdr = max(len(g["titulo"]) * 16.0, len(g["sec_inf"]) * 10.5, len(g["sec_sup"]) * 10.5)

                    # 2. Copia literal das polylines originais (sem forcar hachura solida extra) em escala 2x
                    for ip in g["inf_polys"]:
                        _copiar_poly_escalada(ip, tx1, ty1, ox, oy)

                    _copiar_poly_escalada(g["sup_poly"], tx1, ty1, ox, oy)

                    # 3. Cotas horizontais (Topo = parciais se mudou largura, ou total; Base = total se mudou largura)
                    nx1, ny1, nx2, ny2 = ox, oy, ox + tw_d, oy + th_d
                    nsx1 = ox + (sx1 - tx1) * escala
                    nsy1 = oy + (sy1 - ty1) * escala
                    nsx2 = ox + (sx2 - tx1) * escala
                    nsy2 = oy + (sy2 - ty1) * escala

                    pts_x = cotas_helper.filtrar_e_ordenar_pontos([nx1, nsx1, nsx2, nx2], tolerancia=0.5)
                    y_cota_top = ny2 + 18.0
                    if len(pts_x) <= 2:
                        cotas_helper.criar_dim_horizontal(
                            dwg, nx1, ny2, nx2, ny2, 0.5 * (nx1 + nx2), y_cota_top,
                            arredondar=_precisa_arredondar(nx2 - nx1)
                        )
                    else:
                        # Cadeia parcial toda na MESMA linha horizontal (sem subir cota estreita)
                        for k in range(len(pts_x) - 1):
                            xa, xb = pts_x[k], pts_x[k + 1]
                            cotas_helper.criar_dim_horizontal(
                                dwg, xa, ny2, xb, ny2, 0.5 * (xa + xb), y_cota_top,
                                arredondar=_precisa_arredondar(xb - xa)
                            )
                            if k > 0 and (xb - xa) < 25.0:
                                cotas_now = cotas_helper.coletar_cotas_existentes(dwg)
                                c_ult = next(
                                    (c for c in reversed(cotas_now)
                                     if c.get("tipo") == "IPOCOT" and c.get("orient") == "H"
                                     and c.get("p1") is not None and abs(c["p1"] - xa) < 0.8 and abs(c["p2"] - xb) < 0.8
                                     and abs(c.get("pos_linha", 0.0) - y_cota_top) < 2.0),
                                    None
                                )
                                if c_ult is not None and c_ult["x"] < xa - 0.5:
                                    cotas_helper._substituir_ipocot_por_primitivos(
                                        dwg, c_ult, xb + 2.5, c_ult["y"], estender_linha=True
                                    )
                        # Cota total na base
                        cotas_helper.criar_dim_horizontal(
                            dwg, nx1, ny1, nx2, ny1, 0.5 * (nx1 + nx2), ny1 - 22.0,
                            arredondar=_precisa_arredondar(nx2 - nx1)
                        )

                    # 4. Cotas verticais (Esquerda = total; Direita = parciais na MESMA linha vertical)
                    pts_y = cotas_helper.filtrar_e_ordenar_pontos([ny1, nsy1, nsy2, ny2], tolerancia=0.5)
                    x_cota_esq = nx1 - 18.0
                    cotas_helper.criar_dim_vertical(
                        dwg, nx1, ny1, nx1, ny2, x_cota_esq, 0.5 * (ny1 + ny2),
                        arredondar=_precisa_arredondar(ny2 - ny1)
                    )

                    if len(pts_y) > 2:
                        x_cota_dir = nx2 + 22.0
                        for k in range(len(pts_y) - 1):
                            ya, yb = pts_y[k], pts_y[k + 1]
                            cotas_helper.criar_dim_vertical(
                                dwg, nx2, ya, nx2, yb, x_cota_dir, 0.5 * (ya + yb),
                                arredondar=_precisa_arredondar(yb - ya)
                            )
                            if k > 0 and (yb - ya) < 25.0:
                                cotas_now = cotas_helper.coletar_cotas_existentes(dwg)
                                c_ult = next(
                                    (c for c in reversed(cotas_now)
                                     if c.get("tipo") == "IPOCOT" and c.get("orient") == "V"
                                     and c.get("p1") is not None and abs(c["p1"] - ya) < 0.8 and abs(c["p2"] - yb) < 0.8
                                     and abs(c.get("pos_linha", 0.0) - x_cota_dir) < 2.0),
                                    None
                                )
                                if c_ult is not None and c_ult["y"] < ya - 0.5:
                                    cotas_helper._substituir_ipocot_por_primitivos(
                                        dwg, c_ult, c_ult["x"], yb + 2.5, estender_linha=True
                                    )

                    larg_celula = max(tw_d + 45.0, larg_hdr)
                    q_xmax = max(q_xmax, ox + larg_celula + margem_quadro)
                    q_ymin = min(q_ymin, oy - 40.0 - margem_quadro)
                    x_cursor = ox + larg_celula + gap_x

                y_cursor_top -= (max_h_row + gap_y)

            # Moldura externa do quadro
            dwg.draw.level = 0
            dwg.draw.color = 7
            dwg.draw.style = 0
            dwg.draw.Line(q_xmin, q_ymin, q_xmax, q_ymin)
            dwg.draw.Line(q_xmax, q_ymin, q_xmax, q_ymax)
            dwg.draw.Line(q_xmax, q_ymax, q_xmin, q_ymax)
            dwg.draw.Line(q_xmin, q_ymax, q_xmin, q_ymin)

        finally:
            dwg.draw.level = old_lvl
            dwg.draw.color = old_col
            dwg.draw.style = old_sty
            cotas_helper.configurar_estilo_cotas(dwg)

        tqsjan.Regen()
        eag.msg.Print(
            "G3 Plugins: Detalhe de mudanca de secao gerado para %d pilar(es) em %d grupo(s) na lateral direita!"
            % (len(itens), len(grupos))
        )
        eag.msg.PrintStatus("Detalhe de %d pilar(es) gerado!" % len(itens))

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass

