# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - TRANSPORTE FIDEDIGNO: PILAR, QUADRADO DA ÁREA E FERRO DE DENTRO (TQS EAG)
================================================================================
Autor: Ediglânthio Samuel Araújo Brandão
1. Abrir janela (tela) sobre o pilar na planta da laje.
2. A área do quadrado aberto se torna a área do quadrado em volta (perímetro com HD=26).
3. Capta toda a geometria do pilar e o ferro de dentro de forma 100% fidedigna.
4. Tela HTA mostra qual pilar e área foram selecionados.
5. Cola no ponto clicado o conjunto completo idêntico:
   - O quadrado da área em volta com HD=26;
   - O pilar em sua posição exata;
   - O ferro de dentro;
   - O título PUNÇÃO - ...
================================================================================
"""
import os
import re
import json
import math
import subprocess
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag


ARQUIVO_PILAR_COPIADO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ultimo_pilar_copiado.json")


def salvar_geometria_em_memoria(dados):
    """Salva os elementos capturados em JSON para transporte entre arquivos DWG."""
    try:
        with open(ARQUIVO_PILAR_COPIADO, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def carregar_geometria_em_memoria():
    """Carrega a geometria capturada da memória."""
    if os.path.exists(ARQUIVO_PILAR_COPIADO):
        try:
            with open(ARQUIVO_PILAR_COPIADO, "r", encoding="utf-8") as f:
                dados = json.load(f)
                if dados and dados.get("total_elementos", 0) > 0:
                    return dados
        except Exception:
            return None
    return None


# ==============================================================================
# ALGORITMO DE CLIPPING DE LINHAS PARA A JANELA (COHEN-SUTHERLAND)
# ==============================================================================

def clip_linha_na_janela(x1, y1, x2, y2, xmin, xmax, ymin, ymax):
    """
    Recorta linhas longas que cruzam a janela para que o ferro de dentro
    fique exatamente contido nos limites do quadrado aberto.
    """
    INSIDE = 0
    LEFT = 1
    RIGHT = 2
    BOTTOM = 4
    TOP = 8

    def _code(x, y):
        c = INSIDE
        if x < xmin:
            c |= LEFT
        elif x > xmax:
            c |= RIGHT
        if y < ymin:
            c |= BOTTOM
        elif y > ymax:
            c |= TOP
        return c

    c1 = _code(x1, y1)
    c2 = _code(x2, y2)
    aceita = False

    while True:
        if c1 == 0 and c2 == 0:
            aceita = True
            break
        elif (c1 & c2) != 0:
            break
        else:
            c_fora = c1 if c1 != 0 else c2
            x = 0.0
            y = 0.0
            dx = x2 - x1
            dy = y2 - y1

            if c_fora & TOP:
                x = x1 + dx * (ymax - y1) / dy if dy != 0 else x1
                y = ymax
            elif c_fora & BOTTOM:
                x = x1 + dx * (ymin - y1) / dy if dy != 0 else x1
                y = ymin
            elif c_fora & RIGHT:
                y = y1 + dy * (xmax - x1) / dx if dx != 0 else y1
                x = xmax
            elif c_fora & LEFT:
                y = y1 + dy * (xmin - x1) / dx if dx != 0 else y1
                x = xmin

            if c_fora == c1:
                x1, y1 = x, y
                c1 = _code(x1, y1)
            else:
                x2, y2 = x, y
                c2 = _code(x2, y2)

    if aceita:
        return x1, y1, x2, y2
    return None


# ==============================================================================
# CAPTURA DA JANELA (O TAMANHO DA JANELA DEFINE A ÁREA DO QUADRADO EM VOLTA)
# ==============================================================================

def capturar_janela_com_area(eag, tqsjan):
    """
    O usuário abre uma janela na tela sobre o pilar.
    - O retângulo da janela define exatamente a área do quadrado em volta.
    - Captura o pilar e o ferro de dentro contidos nela.
    """
    dwg = tqsjan.dwg

    prompt1 = "Abra a janela da area do pilar (Clique no 1º canto) [Esc para cancelar]:"
    icod1, x1, y1 = eag.locate.GetPoint(tqsjan, prompt1)
    if icod1 != 1:
        return None

    prompt2 = "Abra o retangulo ate o tamanho desejado da area e clique no 2º canto:"
    icod2, x2, y2 = eag.locate.GetSecondPoint(
        tqsjan, x1, y1,
        TQSEag.EAG_RUBLINEAR,
        TQSEag.EAG_RUBRET_NAOPREEN,
        prompt2
    )
    if icod2 != 1:
        return None

    xmin_j = min(x1, x2)
    xmax_j = max(x1, x2)
    ymin_j = min(y1, y2)
    ymax_j = max(y1, y2)

    # Centro de referência e dimensões exatas da janela aberta
    xc = (xmin_j + xmax_j) / 2.0
    yc = (ymin_j + ymax_j) / 2.0
    larg_area = round(xmax_j - xmin_j, 1)
    alt_area = round(ymax_j - ymin_j, 1)

    linhas = []
    polilinhas = []
    textos = []
    arcos = []
    circulos = []

    # Constantes reais do TQSDwg
    TIPO_LINE = getattr(TQSDwg, "DWGTYPE_LINE", 1)
    TIPO_TEXT = getattr(TQSDwg, "DWGTYPE_TEXT", 2)
    TIPO_POLYLINE = getattr(TQSDwg, "DWGTYPE_POLYLINE", 3)
    TIPO_CIRCLE = getattr(TQSDwg, "DWGTYPE_CIRCLE", 6)
    TIPO_ARC = getattr(TQSDwg, "DWGTYPE_ARC", 7)
    TIPO_CURVE = getattr(TQSDwg, "DWGTYPE_CURVE", 8)

    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break

            nivel = getattr(dwg.iterator, "level", 0)
            cor = getattr(dwg.iterator, "color", -1)
            estilo = getattr(dwg.iterator, "style", -1)

            # 1. LINHAS (pilar e ferro de dentro)
            if itipo == TIPO_LINE:
                try:
                    lx1 = float(dwg.iterator.x1)
                    ly1 = float(dwg.iterator.y1)
                    lx2 = float(dwg.iterator.x2)
                    ly2 = float(dwg.iterator.y2)

                    # Recorta exatamente nos limites da janela aberta
                    clipped = clip_linha_na_janela(lx1, ly1, lx2, ly2, xmin_j, xmax_j, ymin_j, ymax_j)
                    if clipped:
                        cx1, cy1, cx2, cy2 = clipped
                        if math.hypot(cx2 - cx1, cy2 - cy1) > 0.3:
                            linhas.append({
                                "dx1": cx1 - xc, "dy1": cy1 - yc,
                                "dx2": cx2 - xc, "dy2": cy2 - yc,
                                "nivel": nivel, "cor": cor, "estilo": estilo
                            })
                except Exception:
                    pass

            # 2. POLILINHAS E CURVAS (contorno do pilar e polilinhas da forma)
            elif itipo in (TIPO_POLYLINE, TIPO_CURVE):
                try:
                    npts = getattr(dwg.iterator, "xySize", 0)
                    if npts >= 2:
                        pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                        for i in range(len(pts) - 1):
                            p1, p2 = pts[i], pts[i + 1]
                            clipped = clip_linha_na_janela(p1[0], p1[1], p2[0], p2[1], xmin_j, xmax_j, ymin_j, ymax_j)
                            if clipped:
                                cx1, cy1, cx2, cy2 = clipped
                                if math.hypot(cx2 - cx1, cy2 - cy1) > 0.3:
                                    linhas.append({
                                        "dx1": cx1 - xc, "dy1": cy1 - yc,
                                        "dx2": cx2 - xc, "dy2": cy2 - yc,
                                        "nivel": nivel, "cor": cor, "estilo": estilo
                                    })
                except Exception:
                    pass

            # 3. TEXTOS (P10, 30/180, etc.)
            elif itipo == TIPO_TEXT:
                try:
                    tx = float(dwg.iterator.x1)
                    ty = float(dwg.iterator.y1)
                    if xmin_j <= tx <= xmax_j and ymin_j <= ty <= ymax_j:
                        txt = str(getattr(dwg.iterator, "text", "")).strip()
                        h_t = float(getattr(dwg.iterator, "textHeight", 8.0))
                        ang_t = float(getattr(dwg.iterator, "textAngle", 0.0))
                        textos.append({
                            "dx": tx - xc, "dy": ty - yc,
                            "h": h_t, "ang": ang_t,
                            "txt": txt, "nivel": nivel, "cor": cor
                        })
                except Exception:
                    pass

            # 4. ARCOS
            elif itipo == TIPO_ARC:
                try:
                    axc = float(dwg.iterator.xc)
                    ayc = float(dwg.iterator.yc)
                    raio = float(dwg.iterator.radius)
                    if xmin_j <= axc <= xmax_j and ymin_j <= ayc <= ymax_j:
                        arcos.append({
                            "dxc": axc - xc, "dyc": ayc - yc,
                            "raio": raio,
                            "aini": float(dwg.iterator.startAngle), "afim": float(dwg.iterator.endAngle),
                            "nivel": nivel, "cor": cor, "estilo": estilo
                        })
                except Exception:
                    pass

            # 5. CÍRCULOS
            elif itipo == TIPO_CIRCLE:
                try:
                    cxc = float(dwg.iterator.xc)
                    cyc = float(dwg.iterator.yc)
                    raio = float(dwg.iterator.radius)
                    if xmin_j <= cxc <= xmax_j and ymin_j <= cyc <= ymax_j:
                        circulos.append({
                            "dxc": cxc - xc, "dyc": cyc - yc,
                            "raio": raio,
                            "nivel": nivel, "cor": cor, "estilo": estilo
                        })
                except Exception:
                    pass

    except Exception:
        pass

    # Nome do pilar identificado a partir dos textos internos
    nome_pilar = "P10 - P13"
    padrao_pilar = re.compile(r"^P\s*[-.]?\s*(\d+)", re.IGNORECASE)
    melhor_dist = 1e9

    for t in textos:
        d = math.hypot(t["dx"], t["dy"])
        txt = t["txt"]
        if padrao_pilar.search(txt) and d < melhor_dist:
            melhor_dist = d
            nome_pilar = txt

    total = len(linhas) + len(textos) + len(arcos) + len(circulos)

    return {
        "nome": nome_pilar,
        "larg_area": larg_area,
        "alt_area": alt_area,
        "hd": 26.0,
        "total_elementos": total,
        "num_linhas": len(linhas),
        "num_textos": len(textos),
        "linhas": linhas,
        "textos": textos,
        "arcos": arcos,
        "circulos": circulos
    }


# ==============================================================================
# JANELA HTA DE CONFIRMAÇÃO DO PILAR E ÁREA SELECIONADOS
# ==============================================================================

def mostrar_tela_confirmacao(pilar):
    """
    Abre a tela HTA para o usuário visualizar o pilar e a área selecionados antes de colar.
    """
    caminho_script = os.path.dirname(os.path.abspath(__file__))
    hta_path = os.path.join(caminho_script, "dialogo_puncao.hta")
    json_path = os.path.join(caminho_script, "dados_puncao_temp.json")

    if os.path.exists(json_path):
        try:
            os.remove(json_path)
        except Exception:
            pass

    json_js = json_path.replace('\\', '\\\\')

    nome_p = pilar.get("nome", "P10 - P13") if pilar else "P10 - P13"
    larg_area = pilar.get("larg_area", 180.0) if pilar else 180.0
    alt_area = pilar.get("alt_area", 140.0) if pilar else 140.0
    hd_p = pilar.get("hd", 26.0) if pilar else 26.0
    num_lin = pilar.get("num_linhas", 0) if pilar else 0
    num_txt = pilar.get("num_textos", 0) if pilar else 0

    hta_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta http-equiv="x-ua-compatible" content="ie=edge" />
    <title>Pilar e Área de Punção - G3 Plugins</title>
    <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="TransportarPilar" BORDER="dialog" INNERBORDER="no" SCROLL="no" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: #f4f7f6;
            margin: 0;
            padding: 0;
            font-size: 12px;
            color: #212529;
        }}
        .topbar {{
            background: linear-gradient(135deg, #004d40 0%, #00796b 100%);
            color: #ffffff;
            padding: 12px 18px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.25);
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .topbar .icon {{
            width: 32px;
            height: 32px;
            background: rgba(255,255,255,0.18);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            font-weight: bold;
        }}
        .topbar h1 {{
            font-size: 15px;
            margin: 0;
            font-weight: 700;
            letter-spacing: 0.3px;
        }}
        .topbar p {{
            margin: 2px 0 0 0;
            font-size: 11px;
            color: #b2dfdb;
        }}
        .container {{
            padding: 14px 18px 10px 18px;
        }}
        .badge-status {{
            background: #e0f2f1;
            border-left: 4px solid #00796b;
            padding: 10px 14px;
            font-size: 12px;
            color: #004d40;
            border-radius: 0 6px 6px 0;
            margin-bottom: 12px;
            line-height: 1.5;
        }}
        .card {{
            background: #ffffff;
            border: 1px solid #b2dfdb;
            border-radius: 6px;
            padding: 14px;
            margin-bottom: 12px;
            box-shadow: 0 1px 4px rgba(0,77,64,0.06);
        }}
        .card h3 {{
            font-size: 11.5px;
            margin: 0 0 10px 0;
            color: #004d40;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #e0f2f1;
            padding-bottom: 5px;
            font-weight: 700;
        }}
        .item-info {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            border-bottom: 1px dashed #e0f2f1;
            font-size: 12px;
        }}
        .item-info:last-child {{
            border-bottom: none;
        }}
        .item-info .rotulo {{
            color: #546e7a;
            font-weight: 500;
        }}
        .item-info .valor {{
            color: #004d40;
            font-weight: 700;
        }}
        .campo {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 8px;
        }}
        .campo label {{
            font-weight: 500;
            color: #37474f;
            font-size: 11.5px;
        }}
        .campo input[type="text"] {{
            width: 100px;
            padding: 4px 6px;
            border: 1px solid #80cbc4;
            border-radius: 4px;
            font-size: 11.5px;
            text-align: right;
            background: #ffffff;
            color: #004d40;
            font-weight: 600;
        }}
        .btns {{
            display: flex;
            justify-content: flex-end;
            gap: 10px;
            padding: 8px 18px 16px 18px;
        }}
        button {{
            padding: 8px 18px;
            cursor: pointer;
            border: 1px solid #b2dfdb;
            border-radius: 5px;
            background: #fff;
            font-size: 12px;
            font-weight: 600;
            color: #004d40;
        }}
        button:hover {{ background: #e0f2f1; }}
        .btn-principal {{
            background: linear-gradient(135deg, #00796b 0%, #004d40 100%);
            color: #ffffff;
            border: none;
            font-weight: 700;
            box-shadow: 0 2px 4px rgba(0,77,64,0.35);
        }}
        .btn-principal:hover {{
            background: linear-gradient(135deg, #00695c 0%, #00332c 100%);
        }}
    </style>
    <script language="javascript">
        window.onload = function() {{
            window.resizeTo(480, 480);
            window.moveTo((screen.width - 480) / 2, (screen.height - 480) / 2);
        }};

        function responder(acao) {{
            var dados = {{
                acao: acao,
                nome_pilar: document.getElementById("nome_pilar").value || "{nome_p}",
                hd: parseFloat(document.getElementById("hd").value.replace(',', '.')) || {hd_p}
            }};

            try {{
                var fso = new ActiveXObject("Scripting.FileSystemObject");
                var a = fso.CreateTextFile("{json_js}", true);
                a.WriteLine(JSON.stringify(dados));
                a.Close();
            }} catch (e) {{
                alert("Erro ao salvar: " + e.message);
            }}

            window.close();
        }}
    </script>
</head>
<body>
    <div class="topbar">
        <div class="icon">P</div>
        <div>
            <h1>Armação de Punção</h1>
            <p>G3 Plugins - Ediglânthio Samuel Araújo Brandão - TQS</p>
        </div>
    </div>

    <div class="container">
        <!-- STATUS -->
        <div class="badge-status">
            <b>✓ Pilar Selecionado e Área Definida!</b><br>
            Pilar: <b>{nome_p}</b> &bull; Área do Quadrado: <b>{int(larg_area)}x{int(alt_area)} cm</b>
        </div>

        <!-- CONTEÚDO CAPTURADO -->
        <div class="card">
            <h3>Geometria e Área do Capitel</h3>
            <div class="campo" style="margin-bottom:8px;">
                <label>Título / Identificação:</label>
                <input type="text" id="nome_pilar" value="{nome_p}" style="width:130px; text-align:left;" />
            </div>
            <div class="item-info">
                <span class="rotulo">Dimensões da Área (Quadrado):</span>
                <span class="valor">{int(larg_area)} x {int(alt_area)} cm</span>
            </div>
            <div class="item-info">
                <span class="rotulo">Pilar e Ferro de Dentro:</span>
                <span class="valor">{num_lin} linhas capturadas</span>
            </div>
            <div class="item-info">
                <span class="rotulo">Textos Internos:</span>
                <span class="valor">{num_txt} textos</span>
            </div>
            <div class="campo">
                <label>Espessura HD (cm):</label>
                <input type="text" id="hd" value="{hd_p}" />
            </div>
        </div>
    </div>

    <div class="btns">
        <button onclick="responder('cancelar')">Cancelar</button>
        <button style="border-color:#00796b; color:#00796b;" onclick="responder('recopiar')">
            ⬚ Abrir Nova Janela
        </button>
        <button class="btn-principal" onclick="responder('colar')">
            Colar no Desenho
        </button>
    </div>
</body>
</html>
"""

    with open(hta_path, "w", encoding="utf-8") as f:
        f.write(hta_content)

    subprocess.call(["mshta.exe", hta_path])

    dados = None
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            dados = json.load(f)
        try:
            os.remove(json_path)
        except Exception:
            pass

    if os.path.exists(hta_path):
        try:
            os.remove(hta_path)
        except Exception:
            pass

    return dados


# ==============================================================================
# DESENHO FIDEDIGNO: QUADRADO DA ÁREA + PILAR + FERRO DE DENTRO
# ==============================================================================

def colar_desenho_fidedigno(dwg, x_alvo, y_alvo, pilar, config):
    """
    Desenha exatamente:
    1. O quadrado da área em volta (com o tamanho exato da janela aberta, cor 14 e rótulo HD=...);
    2. O pilar e o ferro de dentro na sua posição relativa exata;
    3. Os textos internos e o título PUNÇÃO - ...
    """
    draw = dwg.draw

    larg_area = float(pilar.get("larg_area", 180.0))
    alt_area = float(pilar.get("alt_area", 140.0))
    nome_p = config.get("nome_pilar", pilar.get("nome", "P10 - P13"))
    hd = float(config.get("hd", pilar.get("hd", 26.0)))

    # Coordenadas do quadrado delimitador (exatamente o tamanho da janela que o usuário abriu)
    box_x1 = x_alvo - larg_area / 2.0
    box_x2 = x_alvo + larg_area / 2.0
    box_y1 = y_alvo - alt_area / 2.0
    box_y2 = y_alvo + alt_area / 2.0

    # 1. AQUELE QUADRADO EM VOLTA (Área do pilar/capitel com cor 14 e HD=26)
    draw.level = 228
    draw.color = 14  # Laranja/Marrom
    draw.style = 0
    draw.Line(box_x1, box_y1, box_x2, box_y1)
    draw.Line(box_x2, box_y1, box_x2, box_y2)
    draw.Line(box_x2, box_y2, box_x1, box_y2)
    draw.Line(box_x1, box_y2, box_x1, box_y1)

    # Rótulo HD no canto inferior direito interno da área
    draw.level = 241
    draw.color = 3  # Verde
    txt_hd = f"HD={int(hd) if hd.is_integer() else hd}"
    draw.Text(box_x2 - 38.0, box_y1 + 8.0, 11.0, 0.0, txt_hd)

    # Título no topo
    draw.level = 245
    draw.color = 4  # Ciano
    draw.Text(box_x1 + 10.0, box_y2 - 18.0, 14.0, 0.0, f"PUNÇÃO - {nome_p}")

    # 2. PILAR E FERRO DE DENTRO (LINHAS CAPTURADAS)
    for l in pilar.get("linhas", []):
        try:
            draw.level = l["nivel"]
            draw.color = l["cor"]
            draw.style = l["estilo"]
            draw.Line(x_alvo + l["dx1"], y_alvo + l["dy1"], x_alvo + l["dx2"], y_alvo + l["dy2"])
        except Exception:
            pass

    # 3. ARCOS
    for a in pilar.get("arcos", []):
        try:
            draw.level = a["nivel"]
            draw.color = a["cor"]
            draw.style = a["estilo"]
            draw.Arc(x_alvo + a["dxc"], y_alvo + a["dyc"], a["raio"], a["aini"], a["afim"])
        except Exception:
            pass

    # 4. CÍRCULOS
    for c in pilar.get("circulos", []):
        try:
            draw.level = c["nivel"]
            draw.color = c["cor"]
            draw.style = c["estilo"]
            draw.Circle(x_alvo + c["dxc"], y_alvo + c["dyc"], c["raio"])
        except Exception:
            pass

    # 5. TEXTOS CAPTURADOS
    for t in pilar.get("textos", []):
        try:
            draw.level = t["nivel"]
            draw.color = t["cor"]
            draw.Text(x_alvo + t["dx"], y_alvo + t["dy"], t["h"], t["ang"], t["txt"])
        except Exception:
            pass


# ==============================================================================
# COMANDO: COPIAR PILAR DA PLANTA
# ==============================================================================

def cmd_copiar_pilar(eag, tqsjan):
    """
    Abre uma janela elástica na tela sobre o pilar.
    O retângulo aberto define a área do quadrado e capta o pilar e ferro de dentro.
    """
    try:
        pilar = capturar_janela_com_area(eag, tqsjan)
        if pilar and pilar.get("total_elementos", 0) > 0:
            salvar_geometria_em_memoria(pilar)
            try:
                msg = f"Sucesso! {pilar['total_elementos']} elementos ({pilar['nome']}) capturados com area de {int(pilar['larg_area'])}x{int(pilar['alt_area'])} cm!"
                eag.msg.Print(msg)
            except Exception:
                pass
        else:
            try:
                eag.msg.Print("Nenhum elemento identificado dentro da janela aberta.")
            except Exception:
                pass
    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass


# ==============================================================================
# COMANDO: TRANSPORTAR / COLAR PILAR
# ==============================================================================

def meucmd(eag, tqsjan):
    """
    1. Se não tiver pilar copiado, pede para abrir a janela agora.
    2. Abre a tela HTA mostrando o pilar e a área selecionados.
    3. Ao clicar em 'Colar', pede o clique na tela e desenha fidedigno:
       - O quadrado da área em volta com HD=...;
       - O pilar e o ferro de dentro;
       - O título PUNÇÃO - ...
    """
    try:
        dwg = tqsjan.dwg
        pilar = carregar_geometria_em_memoria()

        # Se não há pilar em memória, abre a janela agora
        if not pilar or pilar.get("total_elementos", 0) == 0:
            try:
                eag.msg.Print("Nenhum pilar em memoria. Abra a janela sobre o pilar na planta primeiro:")
            except Exception:
                pass

            pilar = capturar_janela_com_area(eag, tqsjan)
            if not pilar or pilar.get("total_elementos", 0) == 0:
                try:
                    eag.msg.Print("Operacao cancelada. Nenhum elemento capturado.")
                except Exception:
                    pass
                return

            salvar_geometria_em_memoria(pilar)

        # 1. Abre a tela HTA mostrando qual pilar e área foram capturados
        config = mostrar_tela_confirmacao(pilar)
        if not config:
            return

        acao = config.get("acao", "colar")

        # Se o usuário escolheu abrir uma nova janela
        if acao == "recopiar":
            pilar = capturar_janela_com_area(eag, tqsjan)
            if not pilar or pilar.get("total_elementos", 0) == 0:
                return

            salvar_geometria_em_memoria(pilar)
            config = mostrar_tela_confirmacao(pilar)
            if not config or config.get("acao") != "colar":
                return

        elif acao != "colar":
            return

        # 2. Pede o ponto para colar
        nome_p = config.get("nome_pilar", pilar.get("nome", "Pilar"))
        prompt_colar = f"Clique no ponto onde deseja COLAR o {nome_p} com o quadrado da area e o ferro de dentro [Esc para sair]:"
        icod, xc, yc = eag.locate.GetPoint(tqsjan, prompt_colar)
        if icod != 1:
            return

        # 3. Desenha fidedigno: o quadrado da área em volta + pilar + ferro de dentro
        colar_desenho_fidedigno(dwg, xc, yc, pilar, config)
        tqsjan.Regen()

        try:
            eag.msg.Print(f"Pronto! {nome_p} com o quadrado da area e o ferro de dentro colados com sucesso!")
        except Exception:
            pass

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except Exception:
            pass
    finally:
        try:
            tqsjan.Regen()
        except Exception:
            pass


if __name__ == "__main__":
    pass
