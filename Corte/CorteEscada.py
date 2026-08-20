from TQS import TQSUtil, TQSGeo
import os

try:
    import tkinter as tk
    from tkinter import ttk
    # Para lidar com imagens mais complexas (como PNG) no Tkinter,
    # às vezes precisamos da biblioteca PIL (Pillow).
    # Ela já costuma vir instalada no ambiente Python do TQS moderno.
    from PIL import Image, ImageTk

    TKINTER_OK = True
except Exception:
    TKINTER_OK = False


class DialogoEscada:
    """Caixa de diálogo para os dados da escada, com diagrama explicativo."""

    def __init__(self):
        self.resultado = None
        # Nome do arquivo de imagem que criamos (deve estar na mesma pasta do script)
        self.nome_imagem = "diagrama_escada.png"

    def pedir_dados(self):
        root = tk.Tk()
        root.title("Dados da Escada - Plugin TQS")
        root.attributes("-topmost", True)
        root.resizable(False, False)

        # Usar um estilo mais moderno para os widgets
        style = ttk.Style(root)
        style.theme_use('clam')  # 'clam', 'alt', 'default', 'classic'

        # Frame principal que conterá tudo
        main_frm = ttk.Frame(root, padding=15)
        main_frm.pack(fill=tk.BOTH, expand=True)

        # --- Coluna 1: Imagem/Diagrama ---
        # Tenta carregar a imagem. Se não conseguir, cria um espaço vazio.
        imagem_tk = None
        erro_imagem = False
        try:
            # Caminho absoluto da imagem para garantir que seja encontrada
            caminho_script = os.path.dirname(os.path.abspath(__file__))
            caminho_imagem = os.path.join(caminho_script, self.nome_imagem)

            # Carrega e redimensiona a imagem usando PIL
            img_original = Image.open(caminho_imagem)
            # Redimensiona para um tamanho que não ocupe toda a tela (ex: largura 400px)
            largura_desejada = 400
            w_percent = (largura_desejada / float(img_original.size[0]))
            h_size = int((float(img_original.size[1]) * float(w_percent)))
            img_redimensionada = img_original.resize((largura_desejada, h_size), Image.Resampling.LANCZOS)

            imagem_tk = ImageTk.PhotoImage(img_redimensionada)

            lbl_imagem = ttk.Label(main_frm, image=imagem_tk)
            lbl_imagem.image = imagem_tk  # Mantém uma referência para evitar garbage collection
            lbl_imagem.grid(row=0, column=0, rowspan=10, padx=(0, 20), sticky="nw")
        except FileNotFoundError:
            TQSUtil.writef(f"AVISO: Arquivo de imagem '{self.nome_imagem}' não encontrado na pasta do script.")
            ttk.Label(main_frm, text="[Diagrama não encontrado]", foreground="gray").grid(row=0, column=0, rowspan=10,
                                                                                          padx=(0, 20))
            erro_imagem = True
        except Exception as e:
            TQSUtil.writef(f"ERRO ao carregar imagem: {e}")
            ttk.Label(main_frm, text="[Erro ao carregar diagrama]", foreground="red").grid(row=0, column=0, rowspan=10,
                                                                                           padx=(0, 20))
            erro_imagem = True

        # --- Coluna 2: Campos de Entrada ---
        # Define os campos: (chave_no_dicionario, rotulo_exibido, valor_padrao)
        # Chave 'Passo' corrigida para 'piso' conforme erro anterior.
        campos = [
            ("piso", "Passo (largura do degrau, cm):", "29"),
            ("espelho", "Espelho (altura do degrau, cm):", "17.9"),
            ("n_degraus", "Número de degraus:", "12"),
            ("patamar_partida", "Patamar de partida (cm):", "150"),
            ("patamar_chegada", "Patamar de chegada (cm):", "150"),
            ("espessura", "Espessura da viga (cm):", "15"),
            ("viga_largura", "Largura da viga (cm):", "20"),
            ("viga_altura", "Altura da viga (cm):", "40"),
        ]

        # Container para os campos de entrada para melhor organização
        inputs_frm = ttk.Frame(main_frm)
        inputs_frm.grid(row=0, column=1, sticky="nsew")

        variaveis = {}
        for i, (chave, rotulo, valor_padrao) in enumerate(campos):
            ttk.Label(inputs_frm, text=rotulo).grid(row=i, column=0, sticky="w", pady=5)
            var = tk.StringVar(value=valor_padrao)
            ttk.Entry(inputs_frm, textvariable=var, width=15).grid(row=i, column=1, pady=5, padx=(10, 0))
            variaveis[chave] = var

        # --- Área de Mensagens de Erro ---
        msg_var = tk.StringVar(value="")
        lbl_erro = ttk.Label(inputs_frm, textvariable=msg_var, foreground="red", wraplength=200)
        lbl_erro.grid(row=len(campos), column=0, columnspan=2, pady=(10, 0), sticky="w")

        # --- Botões de Ação ---
        def confirmar():
            try:
                dados = {}
                for chave, _, _ in campos:
                    texto = variaveis[chave].get().replace(",", ".")
                    if chave == "n_degraus":
                        dados[chave] = int(texto)
                    else:
                        dados[chave] = float(texto)

                # Validação básica: todos os valores devem ser maiores que zero
                if any(v <= 0 for v in dados.values()):
                    raise ValueError
            except ValueError:
                msg_var.set("Erro: Preencha todos os campos com valores numéricos válidos e maiores que 0.")
                return

            self.resultado = dados
            root.destroy()

        def cancelar():
            self.resultado = None
            root.destroy()

        btn_frame = ttk.Frame(inputs_frm)
        btn_frame.grid(row=len(campos) + 1, column=0, columnspan=2, pady=(20, 0), sticky="e")

        ttk.Button(btn_frame, text="Gerar Escada", command=confirmar, default="active").grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=cancelar).grid(row=0, column=1, padx=5)

        # Atalhos de teclado
        root.bind("<Return>", lambda e: confirmar())
        root.bind("<Escape>", lambda e: cancelar())

        # Centralizar a janela na tela
        root.update_idletasks()
        w, h = root.winfo_width(), root.winfo_height()
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

        root.mainloop()
        return self.resultado


# --- As funções 'desenhar_perfil_escada' e 'meucmd' permanecem iguais ---
# (Opcional: Você pode colar o resto do seu código original aqui para ter o script completo)

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
    pass


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
