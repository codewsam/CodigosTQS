# -*- coding: utf-8 -*-
import os
import json
import math
import subprocess
from TQS import TQSUtil, TQSGeo, TQSDwg, TQSEag


# ==============================================================================
# INTERFACE GRÁFICA (HTA) - APENAS BITOLA E TRANSPASSE (TEMA ROXO)
# ==============================================================================
def pedir_dados_laje():
    """Abre janela simplificada com tema roxo para coletar bitola e transpasse."""
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
        <title>Armadura da Laje - G3 Plugins</title>
        <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="ArmarLaje" BORDER="dialog" INNERBORDER="no" SCROLL="no" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
        <style>
            * {{ box-sizing: border-box; }}
            body {{
                font-family: 'Segoe UI', Tahoma, sans-serif;
                background: #f5f2f9;
                margin: 0;
                padding: 0;
                font-size: 13px;
                color: #2b2736;
            }}
            .topbar {{
                background: linear-gradient(135deg, #6a1b9a 0%, #38006b 100%);
                color: #fff;
                padding: 14px 20px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.25);
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            .topbar .icon {{
                width: 30px;
                height: 30px;
                background: rgba(255,255,255,0.18);
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
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
                padding: 16px 20px;
            }}
            .card {{
                background: #ffffff;
                border: 1px solid #e1bee7;
                border-radius: 8px;
                padding: 14px 16px;
                box-shadow: 0 1px 4px rgba(106,27,154,0.06);
            }}
            .card h3 {{
                margin: 0 0 12px 0;
                color: #4a148c;
                font-size: 12.5px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.4px;
                border-bottom: 1px solid #f3e5f5;
                padding-bottom: 6px;
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
                width: 110px;
                padding: 5px 8px;
                text-align: right;
                border: 1px solid #ceb3db;
                border-radius: 5px;
                background: #fdfbfe;
                font-size: 12.5px;
                transition: border-color 0.15s, box-shadow 0.15s;
            }}
            select {{ text-align: left; width: 140px; }}
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
                padding: 9px 12px;
                font-size: 11.5px;
                color: #4a148c;
                margin-top: 12px;
                line-height: 1.4;
            }}
            .btns {{
                display: flex;
                justify-content: flex-end;
                gap: 10px;
                padding: 4px 20px 16px 20px;
            }}
            button {{
                padding: 8px 20px;
                cursor: pointer;
                border: 1px solid #ceb3db;
                border-radius: 6px;
                background: #f7f3fa;
                font-size: 12.5px;
                font-weight: 500;
                color: #4a148c;
                transition: background 0.15s;
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
            function initDialog() {{
                try {{
                    window.resizeTo(480, 390);
                    window.moveTo((screen.availWidth - 480) / 2, (screen.availHeight - 390) / 2);
                }} catch(e) {{}}
            }}

            function confirmar() {{
                try {{
                    var dados = {{
                        "bitola": parseFloat(document.getElementById('bitola').value) || 10.0,
                        "comp_max_barra": parseFloat(document.getElementById('comp_max_barra').value.replace(',', '.')) || 12.0,
                        "transpasse": parseFloat(document.getElementById('transpasse').value.replace(',', '.')) || 60.0
                    }};

                    var fso = new ActiveXObject("Scripting.FileSystemObject");
                    var a = fso.CreateTextFile("{json_js}", true);

                    var jsonStr = '{{"bitola":' + dados.bitola + 
                                  ',"comp_max_barra":' + dados.comp_max_barra + 
                                  ',"transpasse":' + dados.transpasse + '}}';

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
                <h3>Parâmetros da Barra</h3>
                <div class="campo">
                    <label>Bitola da Barra (&Phi; mm):</label>
                    <select id="bitola">
                        <option value="6.3">&Phi; 6.3 mm</option>
                        <option value="8.0">&Phi; 8.0 mm</option>
                        <option value="10.0" selected>&Phi; 10.0 mm</option>
                        <option value="12.5">&Phi; 12.5 mm</option>
                        <option value="16.0">&Phi; 16.0 mm</option>
                        <option value="20.0">&Phi; 20.0 mm</option>
                    </select>
                </div>
                <div class="campo">
                    <label>Comprimento Comercial Máx. (m):</label>
                    <input type="text" id="comp_max_barra" value="12.0">
                </div>
                <div class="campo">
                    <label>Transpasse entre Barras (cm):</label>
                    <input type="text" id="transpasse" value="60">
                </div>
            </div>

            <div class="info-box">
                ℹ️ <b>Como funciona:</b> Se o vão ultrapassar <b>12 metros</b>, o plugin dividirá automaticamente a armadura em barras emendadas com o <b>transpasse</b> configurado.
            </div>
        </div>

        <div class="btns">
            <button onclick="window.close()">Cancelar</button>
            <button class="btn-gerar" onclick="confirmar()">Avançar</button>
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
# DESENHO DA BARRA COM TRANSPASSE (LIMITE 12 METROS)
# ==============================================================================
def desenhar_ferro_com_transpasse(dwg, p1, p2, dados):
    """
    Desenha o ferro entre p1 e p2 no EAG. Se o comprimento for maior que 12m,
    cria as barras emendadas com o transpasse informado.
    """
    draw = dwg.draw

    # Nível do ferro no TQS (Nível 220 = Linha que representa o ferro)
    draw.level = 220
    draw.color = 3   # Verde padrão de armadura positiva
    draw.style = 0

    x1, y1 = p1
    x2, y2 = p2

    dx = x2 - x1
    dy = y2 - y1
    dist_total = math.hypot(dx, dy)

    if dist_total <= 1e-4:
        return

    ux = dx / dist_total
    uy = dy / dist_total

    # Vetor perpendicular para afastar as barras no transpasse
    perp_x = -uy
    perp_y = ux
    afastamento_transpasse = 3.0  # 3 cm de afastamento visual no desenho

    comp_max_cm = float(dados.get("comp_max_barra", 12.0)) * 100.0  # metros para cm (ex: 1200 cm)
    transpasse_cm = float(dados.get("transpasse", 60.0))

    # Caso simples: menor ou igual a 12 metros (não precisa de emenda)
    if dist_total <= comp_max_cm:
        draw.Line(x1, y1, x2, y2)
    else:
        # Precisa de emenda / transpasse
        comp_util_por_barra = comp_max_cm - transpasse_cm
        dist_atual = 0.0
        barra_idx = 0

        while dist_atual < dist_total:
            fim_barra = min(dist_atual + comp_max_cm, dist_total)

            # Alterna o lado do transpasse para visualização clara no CAD
            sinal = 1.0 if (barra_idx % 2 == 1) else 0.0
            off_x = sinal * perp_x * afastamento_transpasse
            off_y = sinal * perp_y * afastamento_transpasse

            bx1 = x1 + dist_atual * ux + off_x
            by1 = y1 + dist_atual * uy + off_y
            bx2 = x1 + fim_barra * ux + off_x
            by2 = y1 + fim_barra * uy + off_y

            draw.Line(bx1, by1, bx2, by2)

            if fim_barra >= dist_total:
                break

            dist_atual += comp_util_por_barra
            barra_idx += 1


# ==============================================================================
# ENTRY POINT PRINCIPAL NO TQS EAG
# ==============================================================================
def meucmd(eag, tqsjan):
    """Comando acionado pelo menu TQS na aba G3 Plugins."""
    dados = pedir_dados_laje()
    if dados is None:
        return

    # Pede o ponto inicial e final do alinhamento da nervura / ferro
    icod1, x1, y1 = eag.locate.GetPoint(tqsjan, "Clique no ponto inicial da barra / nervura")
    if icod1 == -1:
        return

    icod2, x2, y2 = eag.locate.GetPoint(tqsjan, "Clique no ponto final da barra / nervura")
    if icod2 == -1:
        return

    desenhar_ferro_com_transpasse(tqsjan.dwg, (x1, y1), (x2, y2), dados)

    tqsjan.ZoomTotal()
    tqsjan.Regen()
