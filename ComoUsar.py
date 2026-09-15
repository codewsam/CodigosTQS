# -*- coding: utf-8 -*-
"""
==============================================================================
G3 ENGENHARIA - GUIA DE UTILIZAÇÃO DOS PLUGINS TQS
Manual interativo com instruções detalhadas para Desenho e Armação de Escadas.
==============================================================================
"""
import os
import subprocess
from TQS import TQSUtil


def abrir_janela_como_usar():
    """Abre uma janela HTML moderna (HTA) explicando como utilizar todos os plugins."""
    caminho_script = os.path.dirname(os.path.abspath(__file__))
    hta_path = os.path.join(caminho_script, "como_usar_guia.hta")

    hta_content = """<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta http-equiv="x-ua-compatible" content="ie=edge" />
    <title>G3 Plugins - Manual de Utilização</title>
    <HTA:APPLICATION ID="oHTA" APPLICATIONNAME="G3PluginsGuia" BORDER="dialog" INNERBORDER="no" SCROLL="yes" SINGLEINSTANCE="yes" WINDOWSTATE="normal" CONTEXTMENU="no" />
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        
        body {
            font-family: 'Segoe UI', Tahoma, -apple-system, BlinkMacSystemFont, sans-serif;
            background: #f1f5f9;
            color: #1e293b;
            font-size: 13.5px;
            line-height: 1.55;
            padding-bottom: 24px;
        }

        /* TOPBAR */
        .topbar {
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
            color: #ffffff;
            padding: 16px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 12px rgba(0,0,0,0.18);
        }

        .topbar-title {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .topbar-icon {
            width: 36px;
            height: 36px;
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.25);
        }

        .topbar h1 {
            font-size: 18px;
            font-weight: 700;
            letter-spacing: 0.3px;
        }

        .topbar p {
            font-size: 11.5px;
            color: #93c5fd;
            margin-top: 2px;
        }

        .badge-ver {
            background: rgba(255,255,255,0.15);
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            border: 1px solid rgba(255,255,255,0.2);
        }

        /* CONTAINER */
        .container {
            max-width: 820px;
            margin: 18px auto 0 auto;
            padding: 0 20px;
        }

        /* TABS */
        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
            background: #e2e8f0;
            padding: 4px;
            border-radius: 10px;
        }

        .tab-btn {
            flex: 1;
            padding: 10px 14px;
            font-size: 13px;
            font-weight: 600;
            border: none;
            background: transparent;
            color: #475569;
            cursor: pointer;
            border-radius: 7px;
            transition: all 0.2s ease;
            text-align: center;
        }

        .tab-btn.active {
            background: #ffffff;
            color: #1d4ed8;
            box-shadow: 0 2px 5px rgba(0,0,0,0.08);
        }

        .tab-btn:hover:not(.active) {
            background: rgba(255,255,255,0.5);
            color: #0f172a;
        }

        /* TAB CONTENT */
        .tab-pane {
            display: none;
        }

        .tab-pane.active {
            display: block;
            animation: fadeIn 0.25s ease-in-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* CARDS */
        .card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 18px 20px;
            margin-bottom: 14px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        }

        .card-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid #f1f5f9;
        }

        .card-header .num {
            width: 24px;
            height: 24px;
            background: #2563eb;
            color: #fff;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 700;
        }

        .card-header h2 {
            font-size: 15px;
            font-weight: 700;
            color: #0f172a;
        }

        .step-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .step-item {
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }

        .step-badge {
            background: #eff6ff;
            color: #1d4ed8;
            font-weight: 700;
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 6px;
            border: 1px solid #bfdbfe;
            white-space: nowrap;
            margin-top: 1px;
        }

        .step-text {
            flex: 1;
        }

        .step-text strong {
            color: #0f172a;
        }

        /* CALLOUTS */
        .callout {
            padding: 12px 16px;
            border-radius: 8px;
            margin: 12px 0 6px 0;
            font-size: 12.5px;
            display: flex;
            gap: 10px;
            align-items: flex-start;
        }

        .callout-info {
            background: #f0f9ff;
            border-left: 4px solid #0284c7;
            color: #0369a1;
        }

        .callout-tip {
            background: #f0fdf4;
            border-left: 4px solid #16a34a;
            color: #15803d;
        }

        .callout-alert {
            background: #fffbeb;
            border-left: 4px solid #f59e0b;
            color: #b45309;
        }

        /* TABLE */
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 8px;
            font-size: 12.5px;
        }

        th, td {
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }

        th {
            background: #f8fafc;
            color: #475569;
            font-weight: 600;
        }

        /* FOOTER */
        .footer-btns {
            max-width: 820px;
            margin: 16px auto 0 auto;
            padding: 0 20px;
            display: flex;
            justify-content: flex-end;
        }

        .btn-close {
            background: #0f172a;
            color: #ffffff;
            border: none;
            padding: 9px 24px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        }

        .btn-close:hover {
            background: #1e293b;
        }
    </style>
    <script>
        window.resizeTo(880, 720);
        window.moveTo(
            Math.max(0, Math.floor((screen.availWidth - 880) / 2)),
            Math.max(0, Math.floor((screen.availHeight - 720) / 2))
        );

        function showTab(tabId, btn) {
            var panes = document.getElementsByClassName('tab-pane');
            for (var i = 0; i < panes.length; i++) {
                panes[i].className = 'tab-pane';
            }
            var btns = document.getElementsByClassName('tab-btn');
            for (var j = 0; j < btns.length; j++) {
                btns[j].className = 'tab-btn';
            }
            document.getElementById(tabId).className = 'tab-pane active';
            btn.className = 'tab-btn active';
        }
    </script>
</head>
<body>
    <div class="topbar">
        <div class="topbar-title">
            <div class="topbar-icon">📘</div>
            <div>
                <h1>Manual de Utilização - G3 Plugins</h1>
                <p>G3 Engenharia &#9679; Ediglânthio Samuel Araújo Brandão</p>
            </div>
        </div>
        <div class="badge-ver">Versão 1.0</div>
    </div>

    <div class="container">
        <!-- NAVEGAÇÃO POR ABAS -->
        <div class="tabs">
            <button class="tab-btn active" onclick="showTab('tab-desenhar', this)">📐 1. Desenhar Escada</button>
            <button class="tab-btn" onclick="showTab('tab-armar', this)">🏗️ 2. Armar Escada</button>
            <button class="tab-btn" onclick="showTab('tab-dicas', this)">💡 Futuro</button>
        </div>

        <!-- ABA 1: DESENHAR ESCADA -->
        <div id="tab-desenhar" class="tab-pane active">
            <div class="card">
                <div class="card-header">
                    <div class="num">1</div>
                    <h2>Como usar: Desenhar Escada</h2>
                </div>
                <p style="margin-bottom: 12px; color: #475569;">
                    Gera a geometria completa da escada em <strong>Corte</strong>, <strong>Planta Baixa</strong> com cotas completas e o <strong>Corte do 1º Lance isolado</strong>.
                </p>

                <ul class="step-list">
                    <li class="step-item">
                        <span class="step-badge">Passo 1</span>
                        <div class="step-text">
                            <strong>Abra o comando:</strong> No Editor Gráfico (EAG) do TQS, clique no menu superior <strong>G3 Plugins &gt; Desenhar Escada</strong>.
                        </div>
                    </li>
                    <li class="step-item">
                        <span class="step-badge">Passo 2</span>
                        <div class="step-text">
                            <strong>Configure os parâmetros na janela:</strong>
                        </div>
                    </li>
                    <li class="step-item">
                        <span class="step-badge">Passo 3</span>
                        <div class="step-text">
                            <strong>Inserção no desenho:</strong> Clique em <strong>Gerar Escada</strong> e, em seguida, <strong>dê um clique com o mouse no local desejado da área gráfica</strong> do TQS para posicionar o ponto inicial da escada.
                        </div>
                    </li>
                </ul>
            </div>
        </div>

        <!-- ABA 2: ARMAR ESCADA -->
        <div id="tab-armar" class="tab-pane">
            <div class="card">
                <div class="card-header">
                    <div class="num">2</div>
                    <h2>Como usar: Armar Escada (SmartRebar TQS)</h2>
                </div>

                <!-- Sub-seção CORTE -->
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; margin-bottom: 12px;">
                    <h3 style="font-size: 14px; color: #1e3a8a; margin-bottom: 8px;">A) Armação do Corte / Perfil</h3>
                    <ul class="step-list">
                        <li class="step-item">
                            <span class="step-badge">1</span>
                            <div class="step-text">No menu <strong>G3 Plugins &gt; Armar Escada</strong>, selecione a aba <strong>1. Corte / Perfil</strong>.</div>
                        </li>
                        <li class="step-item">
                            <span class="step-badge">2</span>
                            <div class="step-text">Defina a <strong>Bitola Principal</strong>, espaçamento, quantidade, cobrimento e armadura de distribuição.</div>
                        </li>
                        <li class="step-item">
                            <span class="step-badge">3</span>
                            <div class="step-text">Clique no botão azul <strong>&#9658; Escada</strong> e, em seguida, <strong>abra uma janela de seleção cobrindo o corte da escada</strong> na tela.</div>
                        </li>
                    </ul>
                </div>

                <!-- Sub-seção PLANTA -->
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px;">
                    <h3 style="font-size: 14px; color: #0284c7; margin-bottom: 8px;">B) Armação da Planta Baixa</h3>
                    <ul class="step-list">
                        <li class="step-item">
                            <span class="step-badge">1</span>
                            <div class="step-text">No menu <strong>G3 Plugins &gt; Armar Escada</strong>, selecione a aba <strong>2. Planta Baixa</strong>.</div>
                        </li>
                        <li class="step-item">
                            <span class="step-badge">2</span>
                            <div class="step-text">Defina bitola, espaçamento, cobrimento bilateral e dobras dos ferros tracejados.</div>
                        </li>
                        <li class="step-item">
                            <span class="step-badge">3</span>
                            <div class="step-text">Clique no botão verde <strong>&#9658; Planta Baixa</strong> e <strong>abra uma janela de seleção cobrindo a planta baixa da escada</strong> na tela.</div>
                        </li>
                    </ul>
                    <div class="callout callout-info">
                    <span>💡</span>
                    <div>
                        <strong>Janela de seleção:</strong> É você segurar com o botão esquerdo do mouse e ir arrastando ate formar uma área retangular.
                    </div>
                </div>
                </div>
            </div>
        </div>

        <!-- ABA 3: Futuro -->
        <div id="tab-dicas" class="tab-pane">
            <div class="card">
            </div>
        </div>
    </div>

    <!-- BOTAO FECHAR -->
    <div class="footer-btns">
        <button class="btn-close" onclick="window.close()">Fechar Manual</button>
    </div>
</body>
</html>
"""

    with open(hta_path, "w", encoding="utf-8-sig") as f:
        f.write(hta_content)

    subprocess.call(["mshta", hta_path])

    if os.path.exists(hta_path):
        try:
            os.remove(hta_path)
        except:
            pass


def meucmd(eag, tqsjan):
    """Comando acionado ao clicar em 'Como Usar' no menu do TQS."""
    abrir_janela_como_usar()


if __name__ == "__main__":
    abrir_janela_como_usar()
