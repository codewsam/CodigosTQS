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
    Caixa de diálogo simples para entrada de piso, espelho e número de degraus.
    Uso:
        dlg = DialogoEscada()
        resultado = dlg.pedir_dados()
        # resultado é None (usuário cancelou) ou (piso, espelho, n_degraus)
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

        ttk.Label(frm, text="Passo (largura do degrau, cm):").grid(row=0, column=0, sticky="w", pady=5)
        piso_var = tk.StringVar(value="29")
        ttk.Entry(frm, textvariable=piso_var, width=12).grid(row=0, column=1, pady=5, padx=5)

        ttk.Label(frm, text="Espelho (altura do degrau, cm):").grid(row=1, column=0, sticky="w", pady=5)
        espelho_var = tk.StringVar(value="17.9")
        ttk.Entry(frm, textvariable=espelho_var, width=12).grid(row=1, column=1, pady=5, padx=5)

        ttk.Label(frm, text="Número de degraus:").grid(row=2, column=0, sticky="w", pady=5)
        n_var = tk.StringVar(value="12")
        ttk.Entry(frm, textvariable=n_var, width=12).grid(row=2, column=1, pady=5, padx=5)

        ttk.Label(frm, text="Espessura do degrau (cm):").grid(row=3, column=0, sticky="w", pady=5)
        espessura_var = tk.StringVar(value="15")
        ttk.Entry(frm, textvariable=espessura_var, width=12).grid(row=3, column=1, pady=5, padx=5)

        msg_var = tk.StringVar(value="")
        ttk.Label(frm, textvariable=msg_var, foreground="red").grid(row=4, column=0, columnspan=2, pady=(0, 5))

        def confirmar():
            try:
                piso = float(piso_var.get().replace(",", "."))
                espelho = float(espelho_var.get().replace(",", "."))
                n_degraus = int(n_var.get())
                espessura = float(espessura_var.get().replace(",", "."))
                if piso <= 0 or espelho <= 0 or n_degraus <= 0 or espessura <= 0:
                    raise ValueError
            except ValueError:
                msg_var.set("Preencha valores numéricos válidos (> 0).")
                return
            self.resultado = (piso, espelho, n_degraus, espessura)
            root.destroy()

        def cancelar():
            self.resultado = None
            root.destroy()

        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(10, 0))
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


def desenhar_perfil_escada(dwg, x0, y0, piso, espelho, n_degraus, espessura):
    """
    Desenha o perfil em degraus (zigue-zague) de uma escada, a partir do
    ponto x0,y0 (canto inferior esquerdo do primeiro degrau), a linha
    diagonal (inclinação) ligando o primeiro ao último degrau, e a linha
    de espessura do degrau, paralela à diagonal, "espessura" cm abaixo dela.
    """
    draw = dwg.draw
    draw.level = 241     # nível observado no editor (ajuste se necessário)
    draw.color = 3       # verde

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

    # Linha de espessura do degrau: paralela à linha que liga a ponta do
    # primeiro degrau à ponta do último degrau (não mais ao ponto de início
    # e fim gerais), "espessura" cm por baixo dela. TQSGeo.ParallelLine
    # calcula a paralela à direita do sentido do vetor 1->2; como essa linha
    # sobe da esquerda pra direita, a distância positiva cai por baixo.
    xp1, yp1, xp2, yp2 = TQSGeo.ParallelLine(
        ponta_inicial[0], ponta_inicial[1], ponta_final[0], ponta_final[1], espessura
    )
    draw.Line(xp1, yp1, xp2, yp2)


def meucmd(eag, tqsjan):
    if not TKINTER_OK:
        TQSUtil.writef("ERRO: tkinter não está disponível neste Python do TQS.")
        return

    dlg = DialogoEscada()
    dados = dlg.pedir_dados()
    if dados is None:
        TQSUtil.writef("Operação cancelada.")
        return

    piso, espelho, n_degraus, espessura = dados

    icod, x0, y0 = eag.locate.GetPoint(tqsjan, "Ponto inicial da escada (canto inferior esquerdo)")
    if icod == -1:
        TQSUtil.writef("Operação cancelada.")
        return

    desenhar_perfil_escada(tqsjan.dwg, x0, y0, piso, espelho, n_degraus, espessura)
    tqsjan.ZoomTotal()

    TQSUtil.writef(
        "Escada gerada: %d degraus, piso=%.1f cm, espelho=%.1f cm, espessura=%.1f cm"
        % (n_degraus, piso, espelho, espessura)
    )
