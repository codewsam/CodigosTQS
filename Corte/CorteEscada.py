from TQS import TQSUtil, TQSGeo

try:
    import tkinter as tk
    from tkinter import ttk
    TKINTER_OK = True
except Exception:
    TKINTER_OK = False


class DialogoEscada:
    """Caixa de diálogo para os dados da escada."""

    def __init__(self):
        self.resultado = None

    def pedir_dados(self):
        root = tk.Tk()
        root.title("Dados da Escada")
        root.attributes("-topmost", True)
        root.resizable(False, False)

        frm = ttk.Frame(root, padding=15)
        frm.grid(row=0, column=0)

        campos = [
            ("piso", "Piso (largura do degrau, cm):", "29"),
            ("espelho", "Espelho (altura do degrau, cm):", "17.9"),
            ("n_degraus", "Número de degraus:", "12"),
            ("patamar_partida", "Patamar de partida (cm):", "150"),
            ("patamar_chegada", "Patamar de chegada (cm):", "150"),
            ("espessura", "Espessura da viga (cm):", "15"),
            ("viga_largura", "Largura da viga (cm):", "20"),
            ("viga_altura", "Altura da viga (cm):", "40"),
        ]

        variaveis = {}
        row = 0
        for chave, rotulo, valor_padrao in campos:
            ttk.Label(frm, text=rotulo).grid(row=row, column=0, sticky="w", pady=5)
            var = tk.StringVar(value=valor_padrao)
            ttk.Entry(frm, textvariable=var, width=12).grid(row=row, column=1, pady=5, padx=5)
            variaveis[chave] = var
            row += 1

        msg_var = tk.StringVar(value="")
        ttk.Label(frm, textvariable=msg_var, foreground="red").grid(
            row=row, column=0, columnspan=2, pady=(0, 5)
        )
        row += 1

        def confirmar():
            try:
                dados = {}
                for chave, _, _ in campos:
                    texto = variaveis[chave].get().replace(",", ".")
                    if chave == "n_degraus":
                        dados[chave] = int(texto)
                    else:
                        dados[chave] = float(texto)
                if any(v <= 0 for v in dados.values()):
                    raise ValueError
            except ValueError:
                msg_var.set("Preencha valores numéricos válidos (> 0).")
                return
            self.resultado = dados
            root.destroy()

        def cancelar():
            self.resultado = None
            root.destroy()

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=(10, 0))
        ttk.Button(btn_frame, text="Gerar", command=confirmar).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=cancelar).grid(row=0, column=1, padx=5)

        root.bind("<Return>", lambda e: confirmar())
        root.bind("<Escape>", lambda e: cancelar())

        root.update_idletasks()
        w, h = root.winfo_width(), root.winfo_height()
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

        root.mainloop()
        return self.resultado


def desenhar_perfil_escada(dwg, x0, y0, dados):
    """Desenha os degraus e os patamares de partida/chegada."""
    piso = dados["piso"]
    espelho = dados["espelho"]
    n_degraus = int(dados["n_degraus"])
    patamar_partida = dados["patamar_partida"]
    patamar_chegada = dados["patamar_chegada"]
    espessura = dados["espessura"]
    viga_largura = dados["viga_largura"]
    viga_altura = dados["viga_altura"]

    draw = dwg.draw
    draw.level = 241
    draw.color = 3

    x, y = x0, y0
    for i in range(n_degraus):
        draw.Line(x, y, x, y + espelho)  # espelho do degrau

        if i < n_degraus - 1:
            draw.Line(x, y + espelho, x + piso, y + espelho)  # piso do degrau
            x += piso
            y += espelho
        else:
            # Último degrau: termina em espelho, sem gerar piso final.
            x += 0
            y += espelho

    x_final, y_final = x, y

    draw.Line(x0 - patamar_partida, y0, x0, y0)
    draw.Line(x_final, y_final, x_final + patamar_chegada, y_final)

    # Linha paralela ao patamar (base).
    x_base_ini = x0 - patamar_partida
    y_base = y0 - espessura

    # Reta paralela ao alinhamento das pontas dos degraus, mantendo
    # afastamento constante de "espessura".
    p1x = x0 + piso
    p1y = y0 + espelho
    if n_degraus > 1:
        p2x = x_final
        p2y = y_final - espelho
    else:
        p2x = p1x + piso
        p2y = p1y + espelho

    xa1, ya1, xa2, ya2 = TQSGeo.ParallelLine(p1x, p1y, p2x, p2y, espessura)
    xb1, yb1, xb2, yb2 = TQSGeo.ParallelLine(p1x, p1y, p2x, p2y, -espessura)

    ym = (p1y + p2y) / 2.0
    if ((ya1 + ya2) / 2.0) < ym:
        xp1, yp1, xp2, yp2 = xa1, ya1, xa2, ya2
    else:
        xp1, yp1, xp2, yp2 = xb1, yb1, xb2, yb2

    if abs(yp2 - yp1) > 1e-9:
        t = (y_base - yp1) / (yp2 - yp1)
        x_base_fim = xp1 + t * (xp2 - xp1)
    else:
        x_base_fim = xp1

    draw.Line(x_base_ini, y_base, x_base_fim, y_base)

    # Termina a reta inclinada no nível da espessura da chegada para manter
    # o afastamento e permitir o fechamento com a viga de chegada.
    y_chegada_corte = y_final - espessura
    if abs(yp2 - yp1) > 1e-9:
        t2 = (y_chegada_corte - yp1) / (yp2 - yp1)
        x_linha_fim = xp1 + t2 * (xp2 - xp1)
    else:
        x_linha_fim = xp2
    y_linha_fim = y_chegada_corte
    draw.Line(x_base_fim, y_base, x_linha_fim, y_linha_fim)

    # Viga de saída: contorno em L/U como no desenho.
    # A espessura define a linha interna que vai até a reta do primeiro espelho.
    x_viga_saida_ini = x0 - patamar_partida - viga_largura
    x_viga_saida_meio = x_viga_saida_ini + viga_largura
    x_viga_saida_fim = x0
    y_viga_saida_topo = y0
    y_viga_saida_base = y0 - viga_altura
    y_viga_saida_corte = y0 - espessura

    draw.Line(x_viga_saida_ini, y_viga_saida_topo, x_viga_saida_ini, y_viga_saida_base)
    draw.Line(x_viga_saida_ini, y_viga_saida_base, x_viga_saida_meio, y_viga_saida_base)
    draw.Line(x_viga_saida_meio, y_viga_saida_base, x_viga_saida_meio, y_viga_saida_corte)
    draw.Line(x_viga_saida_meio, y_viga_saida_corte, x_viga_saida_fim, y_viga_saida_corte)
    draw.Line(x_viga_saida_fim, y_viga_saida_topo, x_viga_saida_ini, y_viga_saida_topo)

    # Viga de chegada espelhada (formato L/U), preservando a espessura.
    x_viga_chegada_borda = x_final + patamar_chegada
    x_viga_chegada_externa = x_viga_chegada_borda + viga_largura
    y_viga_chegada_topo = y_final
    y_viga_chegada_base = y_final - viga_altura
    y_viga_chegada_corte = y_final - espessura

    if x_linha_fim > x_viga_chegada_borda:
        x_linha_fim = x_viga_chegada_borda

    draw.Line(x_viga_chegada_externa, y_viga_chegada_topo, x_viga_chegada_externa, y_viga_chegada_base)
    draw.Line(x_viga_chegada_externa, y_viga_chegada_base, x_viga_chegada_borda, y_viga_chegada_base)
    draw.Line(x_viga_chegada_borda, y_viga_chegada_base, x_viga_chegada_borda, y_viga_chegada_corte)
    draw.Line(x_viga_chegada_borda, y_viga_chegada_corte, x_linha_fim, y_viga_chegada_corte)
    draw.Line(x_viga_chegada_borda, y_viga_chegada_topo, x_viga_chegada_externa, y_viga_chegada_topo)

def meucmd(eag, tqsjan):
    if not TKINTER_OK:
        TQSUtil.writef("ERRO: tkinter não está disponível neste Python do TQS.")
        return

    dlg = DialogoEscada()
    dados = dlg.pedir_dados()
    if dados is None:
        TQSUtil.writef("Operação cancelada.")
        return

    icod, x0, y0 = eag.locate.GetPoint(tqsjan, "Ponto inicial da escada")
    if icod == -1:
        TQSUtil.writef("Operação cancelada.")
        return

    desenhar_perfil_escada(tqsjan.dwg, x0, y0, dados)
    tqsjan.ZoomTotal()

    TQSUtil.writef(
        "Escada gerada: %d degraus, piso=%.1f cm, espelho=%.1f cm, "
        "patamar partida=%.1f cm, patamar chegada=%.1f cm, "
        "espessura=%.1f cm, viga %.1fx%.1f cm"
        % (
            dados["n_degraus"], dados["piso"], dados["espelho"],
            dados["patamar_partida"], dados["patamar_chegada"],
            dados["espessura"],
            dados["viga_largura"], dados["viga_altura"],
        )
    )
