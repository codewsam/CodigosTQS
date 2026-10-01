# -*- coding: utf-8 -*-
import os
import json
import math
import subprocess
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag


# ==============================================================================
# TABELA PADRÃO DE TRANSPASSE POR BITOLA (Norma / Prática G3)
# ==============================================================================
TABELA_TRANSPASSE = {
    6.3: 40.0,
    8.0: 50.0,
    10.0: 60.0,
    12.5: 70.0,
    16.0: 90.0,
    20.0: 110.0
}


# ==============================================================================
# INTERFACE GRÁFICA (HTA) - BITOLA E TRANSPASSE
# ==============================================================================
def pedir_dados_laje():
    """Abre janela para parâmetros da armação da faixa."""
    caminho_script = os.path.dirname(os.path.abspath(__file__))
    hta_path = os.path.join(caminho_script, "dialogo_laje.hta")
    json_path = os.path.join(caminho_script, "dados_laje_temp.json")

    if os.path.exists(json_path):
        try:
            os.remove(json_path)
        except:
            pass

    json_js = json_path.replace('\\', '\\\\')

    hta_content = f"""<!DOCTYPE html>
    <html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <meta http-equiv="x-ua-compatible" content="ie=edge" />
        <title>Armação de Faixa - G3 Plugins</title>
        <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="ArmarFaixa" BORDER="dialog" INNERBORDER="no" SCROLL="no" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Tahoma, sans-serif;
                background: #f7f4fa;
                margin: 0;
                padding: 0;
                font-size: 12.5px;
                color: #2b2736;
            }}
            .topbar {{
                background: linear-gradient(135deg, #6a1b9a 0%, #38006b 100%);
                color: #fff;
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
                font-size: 17px;
            }}
            .topbar h1 {{
                margin: 0;
                font-size: 15px;
                font-weight: 600;
                letter-spacing: 0.2px;
            }}
            .topbar p {{
                margin: 2px 0 0 0;
                font-size: 11px;
                color: #e1bee7;
            }}
            .container {{
                padding: 14px 18px 8px 18px;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }}
            .card {{
                background: #ffffff;
                border: 1px solid #e1bee7;
                border-radius: 8px;
                padding: 14px 16px;
                box-shadow: 0 1px 3px rgba(106,27,154,0.06);
            }}
            .card h3 {{
                margin: 0 0 12px 0;
                color: #4a148c;
                font-size: 12px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.4px;
                border-bottom: 1px solid #f3e5f5;
                padding-bottom: 5px;
            }}
            .campo {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 10px;
            }}
            .campo:last-child {{ margin-bottom: 0; }}
            label {{
                font-weight: 500;
                color: #42394d;
                font-size: 12.5px;
            }}
            input, select {{
                width: 140px;
                padding: 5px 8px;
                text-align: right;
                border: 1px solid #ceb3db;
                border-radius: 4px;
                background: #fdfbfe;
                font-size: 12.5px;
            }}
            select {{ text-align: left; width: 150px; }}
            input:focus, select:focus {{
                outline: none;
                border-color: #6a1b9a;
                box-shadow: 0 0 0 2px rgba(106,27,154,0.18);
                background: #fff;
            }}
            .info-box {{
                background: #f3e5f5;
                border: 1px solid #e1bee7;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 11px;
                color: #4a148c;
                line-height: 1.4;
            }}
            .btns {{
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                padding: 8px 18px 14px 18px;
            }}
            button {{
                padding: 8px 18px;
                cursor: pointer;
                border: 1px solid #ceb3db;
                border-radius: 5px;
                background: #f7f3fa;
                font-size: 12px;
                font-weight: 500;
                color: #4a148c;
            }}
            button:hover {{ background: #ece0f2; }}
            .btn-gerar {{
                background: linear-gradient(135deg, #6a1b9a 0%, #4a148c 100%);
                color: #fff;
                border: none;
                font-weight: 600;
                box-shadow: 0 1px 4px rgba(106,27,154,0.35);
            }}
            .btn-gerar:hover {{ background: linear-gradient(135deg, #5c1687 0%, #3b0e70 100%); }}
        </style>
        <script type="text/javascript">
            var tabelaTranspasse = {{
                "6.3": 40,
                "8.0": 50,
                "10.0": 60,
                "12.5": 70,
                "16.0": 90,
                "20.0": 110
            }};

            function atualizarTranspasse() {{
                var bit = document.getElementById('bitola').value;
                if (tabelaTranspasse[bit]) {{
                    document.getElementById('transpasse').value = tabelaTranspasse[bit];
                }}
            }}

            function initDialog() {{
                try {{
                    window.resizeTo(450, 420);
                    window.moveTo((screen.availWidth - 450) / 2, (screen.availHeight - 420) / 2);
                }} catch(e) {{}}
                atualizarTranspasse();
            }}

            function confirmar() {{
                try {{
                    var bit = parseFloat(document.getElementById('bitola').value) || 16.0;
                    var trans = parseFloat(document.getElementById('transpasse').value.replace(',', '.')) || (tabelaTranspasse[bit] || 90.0);
                    var modulo = parseFloat(document.getElementById('modulo').value.replace(',', '.')) || 65.0;

                    var fso = new ActiveXObject("Scripting.FileSystemObject");
                    var a = fso.CreateTextFile("{json_js}", true);

                    var jsonStr = '{{' +
                        '"bitola":' + bit +
                        ',"transpasse":' + trans +
                        ',"modulo":' + modulo +
                        '}}';

                    a.WriteLine(jsonStr);
                    a.Close();
                    window.close();
                }} catch (e) {{
                    alert("Erro ao salvar dados: " + e.message);
                }}
            }}
        </script>
    </head>
    <body onload="initDialog();">
        <div class="topbar">
            <div class="icon">▦</div>
            <div>
                <h1>Armação de Laje Nervurada</h1>
                <p>Plugin TQS &#9679 G3 Engenharia</p>
            </div>
        </div>

        <div class="container">
            <div class="card">
                <h3>Parâmetros do Ferro</h3>
                <div class="campo">
                    <label>Bitola da Barra (&Phi; mm):</label>
                    <select id="bitola" onchange="atualizarTranspasse()">
                        <option value="6.3">&Phi; 6.3 mm</option>
                        <option value="8.0">&Phi; 8.0 mm</option>
                        <option value="10.0">&Phi; 10.0 mm</option>
                        <option value="12.5">&Phi; 12.5 mm</option>
                        <option value="16.0" selected>&Phi; 16.0 mm</option>
                        <option value="20.0">&Phi; 20.0 mm</option>
                    </select>
                </div>
                <div class="campo">
                    <label>Transpasse entre Barras (cm):</label>
                    <input type="text" id="transpasse" value="90">
                </div>
                <div class="campo">
                    <label>Módulo da Nervura (cm):</label>
                    <input type="text" id="modulo" value="65">
                </div>
            </div>

            <div class="info-box">
                💡 <b>Como usar:</b> Após confirmar, clique em 2 pontos no desenho para definir
                a reta vertical (extensão das nervuras). O plugin conta automaticamente quantas
                nervuras cabem e coloca o ferro horizontal com o texto correto.
            </div>
        </div>

        <div class="btns">
            <button onclick="window.close()">Cancelar</button>
            <button class="btn-gerar" onclick="confirmar()">Definir Pontos no EAG</button>
        </div>
    </body>
    </html>
    """

    with open(hta_path, "w", encoding="utf-8-sig") as f:
        f.write(hta_content)

    subprocess.call(["mshta", hta_path])

    dados = None
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            dados = json.load(f)
        os.remove(json_path)

    if os.path.exists(hta_path):
        try:
            os.remove(hta_path)
        except:
            pass

    return dados


# ==============================================================================
# COTAGEM DE TRANSPASSE (ESCALA EM CENTÍMETROS)
# ==============================================================================
def desenhar_cota_transpasse(draw, x_ini, x_fim, y_barra, dist_t):
    """
    Desenha a cota de transpasse elegante e proporcional no DWG.
    """
    y_cota = y_barra + 7.0
    draw.level = 220
    draw.color = 1  # Linha de cota em vermelho
    draw.style = 0

    # Linha horizontal de cota
    draw.Line(x_ini, y_cota, x_fim, y_cota)

    # Linhas de chamada verticais
    draw.Line(x_ini, y_barra - 1.0, x_ini, y_cota + 2.0)
    draw.Line(x_fim, y_barra - 1.0, x_fim, y_cota + 2.0)

    # Ticks inclinados a 45 graus
    tick = 2.0
    draw.Line(x_ini - tick, y_cota - tick, x_ini + tick, y_cota + tick)
    draw.Line(x_fim - tick, y_cota - tick, x_fim + tick, y_cota + tick)

    # Texto da cota (Amarelo, altura proporcional 8.5cm)
    draw.color = 2  # Amarelo
    txt_val = f"{int(round(dist_t))}"
    tam_txt = 8.5
    larg_txt = len(txt_val) * (tam_txt * 0.72)
    xm = (x_ini + x_fim) / 2.0
    draw.Text(xm - larg_txt / 2.0, y_cota + 2.0, tam_txt, 0.0, txt_val)


# ==============================================================================
# DETECTAR CANAIS REAIS DE NERVURA (IGNORANDO MACIÇOS E CAPITÉIS)
# ==============================================================================
def detectar_canais_reais_entre_pontos(dwg, y_min, y_max, x_reta, modulo=65.0):
    """
    Varre o desenho e encontra APENAS as nervuras reais (espaços entre 5cm e 24cm
    entre fileiras de cubetas), ignorando totalmente as regiões maciças de pilares/capitéis.
    """
    from collections import Counter

    y_horiz = []
    linhas_201_horiz = []

    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break

            nivel = getattr(dwg.iterator, "level", 0)

            # Nível 201 (Borda/Viga)
            if nivel == 201:
                if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                    lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                    lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                    if abs(ly1 - ly2) <= 5.0 and abs(lx2 - lx1) >= 5.0:
                        linhas_201_horiz.append((ly1 + ly2) / 2.0)
                elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                    try:
                        npts = dwg.iterator.xySize
                        pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                        for i in range(len(pts)):
                            p_a = pts[i]
                            p_b = pts[(i + 1) % len(pts)]
                            if abs(p_a[1] - p_b[1]) <= 5.0 and abs(p_b[0] - p_a[0]) >= 5.0:
                                linhas_201_horiz.append((p_a[1] + p_b[1]) / 2.0)
                    except Exception:
                        pass
                continue

            if nivel >= 220:
                continue

            # Linhas horizontais de cubeta
            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                dy = abs(ly2 - ly1)
                dx = abs(lx2 - lx1)
                ym = (ly1 + ly2) / 2.0

                if dy <= 3.0 and dx >= 8.0:
                    if (y_min - 20.0) <= ym <= (y_max + 20.0):
                        y_horiz.append(round(ym, 1))

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    for i in range(len(pts)):
                        p_a = pts[i]
                        p_b = pts[(i + 1) % len(pts)]
                        dy = abs(p_b[1] - p_a[1])
                        dx = abs(p_b[0] - p_a[0])
                        ym = (p_a[1] + p_b[1]) / 2.0
                        if dy <= 3.0 and dx >= 8.0:
                            if (y_min - 20.0) <= ym <= (y_max + 20.0):
                                y_horiz.append(round(ym, 1))
                except Exception:
                    pass
    except Exception:
        pass

    if not y_horiz:
        # Fallback modular
        extensao = abs(y_max - y_min)
        qtd = max(int(round(extensao / modulo)), 1)
        return [], qtd

    # Agrupar níveis horizontais com tolerância de 3cm
    contagem = Counter(y_horiz)
    niveis_unicos = sorted(contagem.keys())

    picos_y = []
    for y in niveis_unicos:
        qtd = contagem[y]
        if not picos_y or abs(y - picos_y[-1]['y']) > 3.0:
            picos_y.append({'y': y, 'qtd': qtd})
        else:
            tot = picos_y[-1]['qtd'] + qtd
            picos_y[-1]['y'] = (picos_y[-1]['y'] * picos_y[-1]['qtd'] + y * qtd) / tot
            picos_y[-1]['qtd'] = tot

    niveis = sorted([p['y'] for p in picos_y if p['qtd'] >= 1])

    # ── IDENTIFICAR APENAS OS VÃOS DE NERVURA (5cm a 24cm) ──
    # Espaços maiores que 24cm (como maciços de pilares e capitéis) são sumariamente descartados!
    canais_reais = []
    for i in range(len(niveis) - 1):
        gap = niveis[i + 1] - niveis[i]
        if 5.0 <= gap <= 24.0:
            canal_meio = (niveis[i] + niveis[i + 1]) / 2.0
            if y_min - 10.0 <= canal_meio <= y_max + 10.0:
                canais_reais.append(canal_meio)

    # Checar bordo Nível 201
    if niveis:
        y_cubeta_inf = min(niveis)
        y_cubeta_sup = max(niveis)
        for y_201 in linhas_201_horiz:
            if y_201 <= y_cubeta_inf + 20.0 and y_min <= y_201 + 25.0:
                y_b_inf = (y_201 + y_cubeta_inf) / 2.0
                if not any(abs(y_b_inf - c) < 5.0 for c in canais_reais):
                    canais_reais.insert(0, y_b_inf)
            if y_201 >= y_cubeta_sup - 20.0 and y_max >= y_201 - 25.0:
                y_b_sup = (y_201 + y_cubeta_sup) / 2.0
                if not any(abs(y_b_sup - c) < 5.0 for c in canais_reais):
                    canais_reais.append(y_b_sup)

    canais_reais = sorted(list(set(round(c, 1) for c in canais_reais)))
    qtd_final = max(len(canais_reais), 1)

    try:
        TQSUtil.writef(f"\n[G3 Lajes] Deteccao Geometrica: {qtd_final} nervuras reais (macicos de pilar desconsiderados)\n")
    except:
        pass

    return canais_reais, qtd_final


# ==============================================================================
# ENCONTRAR LIMITES X A PARTIR DO NÍVEL 201 (CONTORNO DA LAJE)
# ==============================================================================
def coletar_linhas_nivel_201_dwg(dwg):
    """Varre todo o desenho em busca de linhas/polilinhas de contorno no Nível 201 (horizontais e verticais)."""
    linhas_201_horiz = []
    linhas_201_vert = []
    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break
            nivel = getattr(dwg.iterator, "level", 0)
            if nivel != 201:
                continue

            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                lx1 = dwg.iterator.x1
                ly1 = dwg.iterator.y1
                lx2 = dwg.iterator.x2
                ly2 = dwg.iterator.y2
                if abs(ly1 - ly2) <= 5.0 and abs(lx2 - lx1) >= 5.0:
                    linhas_201_horiz.append((min(lx1, lx2), (ly1 + ly2) / 2.0, max(lx1, lx2)))
                elif abs(lx1 - lx2) <= 5.0 and abs(ly1 - ly2) >= 5.0:
                    linhas_201_vert.append(((lx1 + lx2) / 2.0, min(ly1, ly2), max(ly1, ly2)))

            elif itipo == getattr(TQSDwg, "DWGTYPE_POLYLINE", 6) or itipo == getattr(TQSDwg, "DWGTYPE_CURVE", 2):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    for i in range(len(pts)):
                        p_a = pts[i]
                        p_b = pts[(i + 1) % len(pts)]
                        if abs(p_a[1] - p_b[1]) <= 5.0 and abs(p_b[0] - p_a[0]) >= 5.0:
                            linhas_201_horiz.append((min(p_a[0], p_b[0]), (p_a[1] + p_b[1]) / 2.0, max(p_a[0], p_b[0])))
                        elif abs(p_a[0] - p_b[0]) <= 5.0 and abs(p_b[1] - p_a[1]) >= 5.0:
                            linhas_201_vert.append(((p_a[0] + p_b[0]) / 2.0, min(p_a[1], p_b[1]), max(p_a[1], p_b[1])))
                except Exception:
                    pass
    except Exception:
        pass

    return linhas_201_horiz, linhas_201_vert


def encontrar_limites_x_201(dwg, y_ponto, x_ponto):
    """
    Determina os limites externos X (borda esquerda e borda direita) da laje
    para a cota Y informada, garantindo que a armadura se estenda de fora a fora.
    """
    linhas_201_horiz, linhas_201_vert = coletar_linhas_nivel_201_dwg(dwg)

    # 1. Encontrar a extensão horizontal real das cubetas/desenho na cota Y da barra
    xs_cubetas_y = []
    try:
        dwg.iterator.Begin()
        while True:
            itipo = dwg.iterator.Next()
            if itipo == 0 or itipo is None or itipo == getattr(TQSDwg, "DWGTYPE_EOF", 0):
                break
            nivel = getattr(dwg.iterator, "level", 0)
            if nivel >= 220:
                continue

            if itipo == getattr(TQSDwg, "DWGTYPE_LINE", 1):
                lx1, ly1 = dwg.iterator.x1, dwg.iterator.y1
                lx2, ly2 = dwg.iterator.x2, dwg.iterator.y2
                ym = (ly1 + ly2) / 2.0
                if abs(ym - y_ponto) <= 45.0 and abs(lx2 - lx1) >= 8.0:
                    xs_cubetas_y.extend([lx1, lx2])

            elif itipo in (getattr(TQSDwg, "DWGTYPE_POLYLINE", 6), getattr(TQSDwg, "DWGTYPE_CURVE", 2)):
                try:
                    npts = dwg.iterator.xySize
                    pts = [dwg.iterator.GetPolylinePt(i) for i in range(npts)]
                    for p in pts:
                        if abs(p[1] - y_ponto) <= 45.0:
                            xs_cubetas_y.append(p[0])
                except Exception:
                    pass
    except Exception:
        pass

    # 2. Filtrar linhas verticais do Nível 201 que cobrem a cota Y
    linhas_vert_cobrindo_y = []
    for x_lim, y_a, y_b in linhas_201_vert:
        if (min(y_a, y_b) - 60.0) <= y_ponto <= (max(y_a, y_b) + 60.0):
            linhas_vert_cobrindo_y.append(x_lim)

    # Se encontramos a extensão das cubetas nessa faixa Y
    if xs_cubetas_y:
        x_cub_min = min(xs_cubetas_y)
        x_cub_max = max(xs_cubetas_y)

        # Borda esquerda: linha 201 mais próxima do início da 1ª cubeta (à esquerda)
        candidatos_esq = [x for x in linhas_vert_cobrindo_y if x <= x_cub_min + 20.0]
        if candidatos_esq:
            x_left = max(candidatos_esq)  # A linha 201 mais externa colada na cubeta
        else:
            x_left = x_cub_min - 15.0

        # Borda direita: linha 201 mais externa que cobre toda a laje à direita
        candidatos_dir = [x for x in linhas_vert_cobrindo_y if x >= x_cub_max - 20.0]
        if candidatos_dir:
            x_right = min(candidatos_dir)  # A linha 201 mais externa colada na última cubeta
        else:
            x_right = x_cub_max + 15.0

        return x_left, x_right

    # Fallback se não achou cubetas específicas: pega os extremos de todas as verticais 201
    if linhas_vert_cobrindo_y:
        x_left = min(linhas_vert_cobrindo_y)
        x_right = max(linhas_vert_cobrindo_y)
        return x_left, x_right

    return None, None


# ==============================================================================
# GERAÇÃO DO FERRO HORIZONTAL COM RETA VERTICAL E CONTAGEM
# ==============================================================================
def processar_ferro_por_2pontos(dwg, x1, y1, x2, y2, dados):
    """
    A partir dos 2 pontos selecionados pelo usuário:
    1. Usa o X dos pontos como posição da reta vertical
    2. Usa o Y dos pontos como extensão vertical
    3. Detecta os canais reais de nervura (ignorando maciços de pilares)
    4. Procura os limites X no Nível 201 para definir o comprimento do ferro
    5. Divide em trechos comerciais se necessário (transpasse)
    6. Desenha tudo: reta vertical, ferro horizontal, texto de chamada
    """
    draw = dwg.draw

    bitola = float(dados.get("bitola", 16.0))
    transpasse_cm = float(dados.get("transpasse", TABELA_TRANSPASSE.get(bitola, 90.0)))
    comp_dobra = float(dados.get("dobra", 15.0))
    comp_max_barra = 1180.0  # 11.80m
    modulo = float(dados.get("modulo", 65.0))

    # ── Os 2 pontos definem a reta vertical ──
    x_reta = (x1 + x2) / 2.0
    y_p1 = min(y1, y2)
    y_p2 = max(y1, y2)

    extensao_vertical = y_p2 - y_p1
    if extensao_vertical < 10.0:
        return

    # ── Detectar canais reais (espaços vazios entre cubetas) ──
    canais_reais, qtd_nervuras = detectar_canais_reais_entre_pontos(dwg, y_p1, y_p2, x_reta, modulo)

    if canais_reais:
        # Travar a reta vertical exatamente no centro da 1ª e da última nervura real
        y_min_reta = min(canais_reais)
        y_max_reta = max(canais_reais)
        # Posicionar o ferro em uma nervura um pouco mais abaixo do topo (entre 1ª e 2ª fileira)
        if len(canais_reais) >= 2:
            y_barra = canais_reais[-2]
        else:
            y_barra = canais_reais[0]
    else:
        y_min_reta = y_p1
        y_max_reta = y_p2
        y_barra = y_max_reta - (0.5 * modulo)

    # ── Encontrar limites X no Nível 201 (comprimento do ferro) ──
    x_left_201, x_right_201 = encontrar_limites_x_201(dwg, y_barra, x_reta)

    if x_left_201 is None or x_right_201 is None:
        if x_left_201 is None:
            x_left_201 = x_reta - 500.0
        if x_right_201 is None:
            x_right_201 = x_reta + 500.0

    x_ini_ferro = x_left_201
    x_fim_ferro = x_right_201

    # ── Dividir em trechos comerciais (≤ 11.80m) com transpasse ──
    trechos_x = []
    x_curr = x_ini_ferro
    idx_t = 0

    while x_curr < x_fim_ferro:
        x_fim_t = min(x_curr + comp_max_barra, x_fim_ferro)
        trechos_x.append((x_curr, x_fim_t, idx_t))

        if x_fim_t >= x_fim_ferro:
            break
        x_curr = x_fim_t - transpasse_cm
        idx_t += 1

    # ── Desenhar cada trecho ──
    pos_num = 1

    for i_t, (xa_t, xb_t, idx_trecho) in enumerate(trechos_x):
        comp_trecho = xb_t - xa_t
        xm_trecho = (xa_t + xb_t) / 2.0

        # Alternar Y da barra nas emendas para ficarem paralelas
        off_y = 0.0
        if len(trechos_x) > 1:
            off_y = 1.5 if (idx_trecho % 2 == 1) else -1.5

        y_ferro = y_barra + off_y

        # Identificar pontas
        eh_ponta_esq = (i_t == 0)
        eh_ponta_dir = (i_t == len(trechos_x) - 1)

        # A) Barra horizontal
        draw.level = 220
        draw.color = 3  # Verde (Armadura)
        draw.style = 0
        draw.Line(xa_t, y_ferro, xb_t, y_ferro)

        # Dobras nas extremidades da laje
        if eh_ponta_esq and comp_dobra > 0:
            draw.Line(xa_t, y_ferro, xa_t, y_ferro - comp_dobra)

        if eh_ponta_dir and comp_dobra > 0:
            draw.Line(xb_t, y_ferro, xb_t, y_ferro - comp_dobra)

        # B) Cota de transpasse se for trecho posterior
        if i_t > 0:
            x_trans_ini = xa_t
            x_trans_fim = trechos_x[i_t - 1][1]
            dist_t = x_trans_fim - x_trans_ini
            if dist_t > 1.0:
                desenhar_cota_transpasse(draw, x_trans_ini, x_trans_fim, y_ferro, dist_t)

        # C) Reta vertical com setas (no local exato X onde o usuário desenhou)
        if i_t == 0 and qtd_nervuras > 1:
            draw.level = 220
            draw.color = 3  # Verde
            draw.style = 1  # Tracejado
            draw.Line(x_reta, y_min_reta, x_reta, y_max_reta)

            # Setas nas extremidades da reta vertical
            raio_seta = 5.0
            draw.style = 0
            draw.Line(x_reta, y_min_reta, x_reta - raio_seta, y_min_reta + raio_seta * 1.5)
            draw.Line(x_reta, y_min_reta, x_reta + raio_seta, y_min_reta + raio_seta * 1.5)
            draw.Line(x_reta, y_max_reta, x_reta - raio_seta, y_max_reta - raio_seta * 1.5)
            draw.Line(x_reta, y_max_reta, x_reta + raio_seta, y_max_reta - raio_seta * 1.5)

        # D) Texto de chamada do ferro (Amarelo)
        draw.level = 220
        draw.color = 2  # Amarelo
        draw.style = 0
        bitola_str = f"{bitola:g}"
        comp_total_barra = comp_trecho + (comp_dobra if eh_ponta_esq else 0.0) + (comp_dobra if eh_ponta_dir else 0.0)
        comp_int = int(round(comp_total_barra))
        pos_str = f"P{pos_num}"

        if qtd_nervuras > 1:
            prefixo = f"{qtd_nervuras}x1"
        else:
            prefixo = "1"

        txt_chamada = f"{prefixo} {pos_str} %% {bitola_str} C/NERV C={comp_int}"
        tam_txt = 8.5
        larg_txt = len(txt_chamada) * (tam_txt * 0.72)

        # Posicionado 12cm abaixo da barra para clareza
        draw.Text(xm_trecho - larg_txt / 2.0, y_ferro - 12.0, tam_txt, 0.0, txt_chamada)

        pos_num += 1


# ==============================================================================
# ENTRY POINT PRINCIPAL NO TQS EAG
# ==============================================================================
def meucmd(eag, tqsjan):
    """
    Comando acionado pelo menu TQS na aba G3 Plugins.

    Fluxo:
    1. Abre janela HTA para parâmetros (bitola, transpasse, módulo)
    2. Pede ao usuário para clicar 2 pontos (extensão vertical das nervuras)
    3. Conta nervuras, encontra limites X, desenha ferro + reta + texto
    """
    try:
        # 1. Parâmetros via HTA
        dados = pedir_dados_laje()
        if dados is None:
            return

        # 2. Primeiro ponto: topo (ou base) da extensão das nervuras
        icod1, x1, y1 = eag.locate.GetPoint(
            tqsjan,
            "Clique o PRIMEIRO ponto da extensão das nervuras"
        )
        if icod1 != 1:
            return

        # 3. Segundo ponto: com rubber band (linha elástica) a partir do primeiro
        icod2, x2, y2 = eag.locate.GetSecondPoint(
            tqsjan, x1, y1,
            TQSEag.EAG_RUBLINEAR,
            TQSEag.EAG_RUBRET_NAOPREEN,
            "Clique o SEGUNDO ponto (outra extremidade das nervuras)"
        )
        if icod2 != 1:
            return

        # 4. Processar e desenhar
        processar_ferro_por_2pontos(tqsjan.dwg, x1, y1, x2, y2, dados)
        tqsjan.Regen()

    except Exception as e:
        try:
            TQSUtil.ShowException(e)
        except:
            pass
