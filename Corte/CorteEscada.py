from TQS import TQSUtil, TQSGeo

# Import isolado num bloco try/except só pra dar uma mensagem clara
# caso o Python do TQS não tenha o tkinter disponível.
try:
    import tkinter as tk
    from tkinter import ttk
    TKINTER_OK = True
except Exception:
    TKINTER_OK = False


class DialogoEscada:
    """
    Caixa de diálogo para entrada dos dados da escada: piso, espelho,
    número de degraus, espessura, patamares e vigas de partida/chegada.
    Uso:
        dlg = DialogoEscada()
        resultado = dlg.pedir_dados()
        # resultado é None (usuário cancelou) ou um dicionário com os campos
    """

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
            ("espessura", "Espessura do degrau (cm):", "15"),
            ("patamar_partida", "Comprimento patamar de partida (cm):", "150"),
            ("patamar_chegada", "Comprimento patamar de chegada (cm):", "150"),
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
    """

    """
    piso = dados["piso"]
    espelho = dados["espelho"]
    n_degraus = int(dados["n_degraus"])
    espessura = dados["espessura"]
    patamar_partida = dados["patamar_partida"]
    patamar_chegada = dados["patamar_chegada"]
    viga_largura = dados["viga_largura"]
    viga_altura = dados["viga_altura"]

    draw = dwg.draw
    draw.level = 241     # nível observado no editor (ajuste se necessário)
    draw.color = 3       # verde

    # --- Degraus ---
    x, y = x0, y0
    ponta_inicial = None
    ponta_final = None
    for _ in range(n_degraus):
        draw.Line(x, y, x + piso, y)                    # piso do degrau
        # Ponta do degrau: canto em "L" onde o piso encontra o espelho
        ponta_x, ponta_y = x + piso, y
        if ponta_inicial is None:
            ponta_inicial = (ponta_x, ponta_y)
        ponta_final = (ponta_x, ponta_y)

        draw.Line(x + piso, y, x + piso, y + espelho)    # espelho (subida)
        x += piso
        y += espelho

    x_final, y_final = x, y   # ponto final do último degrau (topo)

    # --- Linha de espessura do degrau ---
    # Paralela à linha que liga a ponta do primeiro degrau à ponta do
    # último, "espessura" cm por baixo dela.
    xp1, yp1, xp2, yp2 = TQSGeo.ParallelLine(
        ponta_inicial[0], ponta_inicial[1], ponta_final[0], ponta_final[1], espessura
    )
    draw.Line(xp1, yp1, xp2, yp2)

    # --- Patamar de partida (à esquerda de x0,y0) ---
    x_patamar_partida = x0 - patamar_partida
    draw.Line(x_patamar_partida, y0, x0, y0)

    # Viga de partida: retângulo na ponta externa do patamar (mais longe
    # da escada), descendo "viga_altura" cm abaixo do nível do patamar.
    x_viga_partida = x_patamar_partida - viga_largura
    draw.Rectangle(x_viga_partida, y0 - viga_altura, x_patamar_partida, y0)

    # --- Patamar de chegada (à direita do último degrau) ---
    x_patamar_chegada = x_final + patamar_chegada
    draw.Line(x_final, y_final, x_patamar_chegada, y_final)

    # Viga de chegada: retângulo na ponta externa do patamar (mais longe
    # da escada), descendo "viga_altura" cm abaixo do nível do patamar.
    x_viga_chegada = x_patamar_chegada + viga_largura
    draw.Rectangle(x_patamar_chegada, y_final - viga_altura, x_viga_chegada, y_final)


def meucmd(eag, tqsjan):
    if not TKINTER_OK:
        TQSUtil.writef("ERRO: tkinter não está disponível neste Python do TQS.")
        return

    dlg = DialogoEscada()
    dados = dlg.pedir_dados()
    if dados is None:
        TQSUtil.writef("Operação cancelada.")
        return

    icod, x0, y0 = eag.locate.GetPoint(tqsjan, "Ponto inicial da escada (canto inferior esquerdo)")
    if icod == -1:
        TQSUtil.writef("Operação cancelada.")
        return

    desenhar_perfil_escada(tqsjan.dwg, x0, y0, dados)
    tqsjan.ZoomTotal()

    TQSUtil.writef(
        "Escada gerada: %d degraus, piso=%.1f cm, espelho=%.1f cm, espessura=%.1f cm, "
        "patamar partida=%.1f cm, patamar chegada=%.1f cm, viga %.1fx%.1f cm"
        % (
            dados["n_degraus"], dados["piso"], dados["espelho"], dados["espessura"],
            dados["patamar_partida"], dados["patamar_chegada"],
            dados["viga_largura"], dados["viga_altura"],
        )
    )
