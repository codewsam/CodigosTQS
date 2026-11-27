# -*- coding: utf-8 -*-
"""
================================================================================
G3 PLUGINS - FORMAS (TQS EAG) — TELA PRINCIPAL & HUB DE COMANDOS
================================================================================
Ponto central do modulo de Formas. Abre a interface principal moderna (tema azul
claro e branco) e delega a execucao para os modulos dedicados:
  - linha_de_corte.py         : Linha de Corte ($CORTEA / 2 pontos)
  - inversoes.py              : Inversoes (VIGA INVERTIDA / LAJE REBAIXADA)
  - corrigir_vazios.py        : Corrigir Vazio e Indicador de Laje
  - mudanca_secao_pilares.py  : Detalhe Mudanca de Secao Pilares (1:25)
  - cotas_helper.py           : Criar Cotas e Arredondar Valor Cota
  - organizar.py              : Organizar sobreposicoes gerais
  - anti_sobreposicao.py      : Organizar Pilares e setas de chamada
================================================================================
"""
import os
import json
import base64
import importlib
import subprocess

import linha_de_corte
import inversoes
import corrigir_vazios
import mudanca_secao_pilares
import cotas_helper
import anti_sobreposicao
import organizar

# Re-exports de compatibilidade
LIMITE_SEM_SETA_INVERSAO_VIGA = inversoes.LIMITE_SEM_SETA_INVERSAO_VIGA
encontrar_pares_de_corte = linha_de_corte.encontrar_pares_de_corte
coletar_contexto_inversoes = inversoes.coletar_contexto_inversoes
_agrupar_bolinhas_vigas = inversoes._agrupar_bolinhas_vigas
_calcular_melhor_posicao_inversao_viga = inversoes._calcular_melhor_posicao_inversao_viga
_formatar_valor_cm = inversoes._formatar_valor_cm


def cmd_linha_de_corte(eag, tqsjan):
    """Cria automaticamente (ou por 2 pontos) as linhas de corte."""
    importlib.reload(linha_de_corte)
    linha_de_corte.cmd_linha_de_corte(eag, tqsjan)


def cmd_inversoes(eag, tqsjan):
    """Converte bolinhas de desnivel/inversao de vigas (11) e lajes (13)."""
    importlib.reload(anti_sobreposicao)
    importlib.reload(linha_de_corte)
    importlib.reload(inversoes)
    inversoes.cmd_inversoes(eag, tqsjan)


def cmd_criar_cotas(eag, tqsjan):
    """Abre a janela de cotagem automatica da planta de formas."""
    importlib.reload(cotas_helper)
    cotas_helper.cmd_criar_cotas(eag, tqsjan)


def cmd_corrigir_vazios(eag, tqsjan):
    """Corrige vazios em X (241 -> 210), apaga indicadores de laje (240) e fecha shafts (237)."""
    importlib.reload(corrigir_vazios)
    corrigir_vazios.cmd_corrigir_vazios(eag, tqsjan)


def cmd_organizar(eag, tqsjan):
    """Organiza textos de vigas, secoes, bolinhas, pilares e cotas na planta de formas."""
    importlib.reload(anti_sobreposicao)
    importlib.reload(organizar)
    organizar.cmd_organizar(eag, tqsjan)


def cmd_organizar_pilar(eag, tqsjan):
    """Organiza exclusivamente textos de pilares sobrepostos."""
    importlib.reload(anti_sobreposicao)
    anti_sobreposicao.cmd_organizar_pilar(eag, tqsjan)


def cmd_inverter_e_organizar(eag, tqsjan):
    """
    Executa em sequencia os comandos Inversoes e Organizar.
    Mantem o limite maximo de deslocamento de pilares sobrepostos (75 cm).
    """
    chave = "G3_MAX_DESLOC_PILAR"
    valor_anterior = os.environ.get(chave)
    os.environ[chave] = "75.0"
    try:
        cmd_inversoes(eag, tqsjan)
        cmd_organizar(eag, tqsjan)
    finally:
        if valor_anterior is None:
            os.environ.pop(chave, None)
        else:
            os.environ[chave] = valor_anterior


def cmd_corrigir_sobreposicao(eag, tqsjan):
    """Alias de compatibilidade para cmd_organizar."""
    cmd_organizar(eag, tqsjan)


def cmd_detalhe_mudanca_secao_pilares(eag, tqsjan):
    """Gera o quadro lateral de detalhe de mudanca de secao de pilares (escala 1:25)."""
    importlib.reload(cotas_helper)
    importlib.reload(mudanca_secao_pilares)
    mudanca_secao_pilares.cmd_detalhe_mudanca_secao_pilares(eag, tqsjan)


def abrir_tela_formas():
    """
    Exibe a janela principal moderna de Formas (tema azul claro e branco):
      - Esquerda superior: marca G3 Engenharia + cartao limpo de detalhes
      - Direita: menu de ferramentas com selecao multipla (1 ou varias de uma vez)
      - Rodape inferior: credito Ediglanthio Samuel Araujo Brandao (esquerda) e
        botoes Fechar + Executar (direita)
    Retorna lista de chaves das acoes selecionadas ou [] se cancelado.
    """
    pasta_temp = os.environ.get("TEMP", os.path.dirname(os.path.abspath(__file__)))
    hta_path = os.path.join(pasta_temp, "g3_formas_hub.hta")
    json_path = os.path.join(pasta_temp, "g3_formas_hub.json")
    json_js = json_path.replace("\\", "\\\\")

    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo_g3.png")
    brand_mark_html = '<div class="brand-mark-fallback">G3</div>'
    if os.path.exists(logo_path):
        try:
            with open(logo_path, "rb") as f_logo:
                b64_logo = base64.b64encode(f_logo.read()).decode("ascii")
            brand_mark_html = (
                '<div class="brand-mark">'
                '<img src="data:image/png;base64,' + b64_logo + '" alt="G3 Engenharia" />'
                '</div>'
            )
        except Exception:
            pass

    if os.path.exists(json_path):
        try:
            os.remove(json_path)
        except Exception:
            pass

    hta_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta http-equiv="x-ua-compatible" content="ie=edge" />
    <title>G3 Engenharia — F&ocirc;rmas</title>
    <HTA:APPLICATION
        ID="oHTA"
        APPLICATIONNAME="G3FormasHub"
        BORDER="dialog"
        MAXIMIZEBUTTON="no"
        MINIMIZEBUTTON="no"
        INNERBORDER="no"
        SCROLL="no"
        SINGLEINSTANCE="yes"
        WINDOWSTATE="normal"
        CONTEXTMENU="no"
    />
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        html, body {{
            width: 100%;
            height: 100%;
            overflow: hidden;
            font-family: 'Segoe UI', Tahoma, -apple-system, sans-serif;
            background: linear-gradient(145deg, #dff0ff 0%, #eef7ff 50%, #ffffff 100%);
            color: #1e293b;
            user-select: none;
        }}

        .page {{
            display: flex;
            flex-direction: column;
            width: 100%;
            height: 100%;
        }}

        .shell {{
            display: flex;
            flex: 1;
            min-height: 0;
        }}

        /* COLUNA ESQUERDA — MARCA + PREVIEW */
        .left-pane {{
            flex: 1;
            padding: 32px 32px 24px 34px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }}

        .brand-row {{
            display: flex;
            align-items: center;
        }}

        .brand-mark {{
            width: 52px;
            height: 52px;
            border-radius: 13px;
            background: #ffffff;
            border: 1px solid rgba(59, 130, 246, 0.18);
            padding: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 6px 16px rgba(30, 64, 175, 0.08);
            margin-right: 13px;
            flex-shrink: 0;
        }}

        .brand-mark img {{
            width: 100%;
            height: 100%;
            display: block;
        }}

        .brand-mark-fallback {{
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%);
            color: #ffffff;
            font-size: 16px;
            font-weight: 700;
            letter-spacing: -0.02em;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.22);
            margin-right: 13px;
            flex-shrink: 0;
        }}

        .brand-text h1 {{
            font-size: 19px;
            font-weight: 700;
            letter-spacing: -0.02em;
            line-height: 1.15;
            color: #0f172a;
        }}

        .brand-text span {{
            display: block;
            font-size: 12px;
            font-weight: 500;
            color: #3b82f6;
            margin-top: 2px;
        }}

        .hero-copy {{
            margin-top: 28px;
            margin-bottom: 24px;
        }}

        .hero-pill {{
            display: inline-block;
            font-size: 10.5px;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: #1d4ed8;
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid rgba(59, 130, 246, 0.22);
            padding: 4px 11px;
            border-radius: 999px;
            margin-bottom: 12px;
        }}

        .hero-copy h2 {{
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.025em;
            line-height: 1.2;
            color: #0f172a;
        }}

        .hero-copy p {{
            font-size: 13px;
            line-height: 1.6;
            color: #475569;
            margin-top: 8px;
        }}

        /* CARD DE DETALHES LIMPO (SEM TAGS) */
        .preview-card {{
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid rgba(59, 130, 246, 0.16);
            border-radius: 14px;
            padding: 20px 22px;
            box-shadow: 0 8px 24px rgba(30, 64, 175, 0.06);
            min-height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            transition: all 0.2s ease-out;
        }}

        .preview-top {{
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }}

        .preview-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #38bdf8;
            margin-right: 9px;
            flex-shrink: 0;
        }}

        .preview-title {{
            font-size: 14.5px;
            font-weight: 700;
            letter-spacing: -0.01em;
            color: #0f172a;
        }}

        .preview-desc {{
            font-size: 12.8px;
            line-height: 1.55;
            color: #475569;
        }}

        /* COLUNA DIREITA — ABAS ESTILO PASTA + CONTEUDO */
        .right-menu {{
            width: 385px;
            background: #ffffff;
            border-left: 1px solid rgba(59, 130, 246, 0.14);
            display: flex;
            flex-direction: column;
            box-shadow: -8px 0 28px rgba(30, 64, 175, 0.04);
        }}

        /* ABAS ESTILO PASTA / FICHARIO */
        .folder-tabs {{
            display: flex;
            align-items: flex-end;
            background: #e8f3ff;
            padding: 14px 20px 0 20px;
            border-bottom: 1px solid rgba(59, 130, 246, 0.20);
            flex-shrink: 0;
        }}

        .folder-tab {{
            position: relative;
            top: 1px;
            background: #d8ebff;
            color: #475569;
            border: 1px solid rgba(59, 130, 246, 0.18);
            border-bottom: 1px solid rgba(59, 130, 246, 0.20);
            border-radius: 10px 10px 0 0;
            padding: 9px 18px 8px 18px;
            margin-right: 6px;
            font-size: 12.5px;
            font-weight: 600;
            letter-spacing: -0.01em;
            cursor: pointer;
            transition: all 0.18s ease-out;
        }}

        .folder-tab:hover {{
            background: #eef6ff;
            color: #1d4ed8;
        }}

        .folder-tab.active {{
            background: #ffffff;
            color: #1d4ed8;
            border-color: rgba(59, 130, 246, 0.22);
            border-bottom-color: #ffffff;
            padding-top: 10px;
            padding-bottom: 9px;
            box-shadow: 0 -2px 8px rgba(30, 64, 175, 0.04);
        }}

        .tab-body {{
            flex: 1;
            padding: 16px 24px 18px 24px;
            display: flex;
            flex-direction: column;
            min-height: 0;
        }}

        .tab-pane {{
            display: none;
            flex-direction: column;
            flex: 1;
        }}

        .tab-pane.active {{
            display: flex;
        }}

        .menu-header-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 2px 10px 2px;
            border-bottom: 1px solid #f1f5f9;
            margin-bottom: 12px;
        }}

        .menu-header {{
            font-size: 10.5px;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #64748b;
        }}

        .empty-state {{
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 28px 22px;
            background: #f8fbff;
            border: 1px dashed rgba(59, 130, 246, 0.28);
            border-radius: 14px;
        }}

        .empty-icon {{
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: #eff6ff;
            border: 1px solid #dbeafe;
            color: #3b82f6;
            font-size: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 12px;
        }}

        .empty-title {{
            font-size: 14px;
            font-weight: 600;
            color: #0f172a;
            margin-bottom: 6px;
        }}

        .empty-desc {{
            font-size: 12px;
            line-height: 1.5;
            color: #64748b;
            max-width: 240px;
        }}

        .btn-toggle-all {{
            background: transparent;
            border: none;
            color: #2563eb;
            font-size: 11.5px;
            font-weight: 600;
            cursor: pointer;
            padding: 2px 6px;
            border-radius: 6px;
            transition: all 0.15s ease-out;
        }}

        .btn-toggle-all:hover {{
            background: #eff6ff;
            color: #1d4ed8;
        }}

        .menu-list {{
            display: flex;
            flex-direction: column;
            flex: 1;
        }}

        .menu-item {{
            display: flex;
            align-items: center;
            width: 100%;
            text-align: left;
            background: #f8fbff;
            border: 1.5px solid #e2eefc;
            border-radius: 12px;
            padding: 12px 14px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.18s ease-out;
        }}

        .menu-item:hover {{
            background: #f0f7ff;
            border-color: #93c5fd;
        }}

        .menu-item.selected {{
            background: #eff6ff;
            border-color: #3b82f6;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.10);
        }}

        .item-icon {{
            width: 36px;
            height: 36px;
            border-radius: 9px;
            background: #ffffff;
            border: 1px solid #dbeafe;
            color: #2563eb;
            font-size: 15px;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 12px;
            flex-shrink: 0;
            transition: all 0.18s ease-out;
        }}

        .menu-item.selected .item-icon {{
            background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%);
            border-color: transparent;
            color: #ffffff;
        }}

        .item-body {{
            flex: 1;
            min-width: 0;
        }}

        .item-title {{
            font-size: 13.5px;
            font-weight: 600;
            color: #0f172a;
            line-height: 1.25;
        }}

        .item-sub {{
            font-size: 11.5px;
            color: #64748b;
            margin-top: 2px;
            line-height: 1.25;
        }}

        .item-check {{
            width: 22px;
            height: 22px;
            border-radius: 7px;
            border: 1.5px solid #cbd5e1;
            background: #ffffff;
            color: transparent;
            font-size: 13px;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-left: 10px;
            flex-shrink: 0;
            transition: all 0.18s ease-out;
        }}

        .menu-item.selected .item-check {{
            background: #2563eb;
            border-color: #2563eb;
            color: #ffffff;
        }}

        /* BARRA INFERIOR — CREDITO A ESQUERDA + BOTOES A DIREITA */
        .bottom-bar {{
            height: 62px;
            background: rgba(255, 255, 255, 0.94);
            border-top: 1px solid rgba(59, 130, 246, 0.14);
            padding: 0 24px 0 34px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
        }}

        .author-credit {{
            font-size: 12px;
            color: #64748b;
            font-weight: 500;
        }}

        .author-credit strong {{
            color: #1e3a8a;
            font-weight: 600;
        }}

        .footer-actions {{
            display: flex;
            align-items: center;
        }}

        .btn-close {{
            background: #ffffff;
            color: #475569;
            border: 1px solid #cbd5e1;
            border-radius: 9px;
            padding: 9px 18px;
            font-size: 12.5px;
            font-weight: 600;
            cursor: pointer;
            margin-right: 10px;
            transition: all 0.18s ease-out;
        }}

        .btn-close:hover {{
            background: #f1f5f9;
            color: #0f172a;
            border-color: #94a3b8;
        }}

        .btn-run {{
            background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%);
            color: #ffffff;
            border: none;
            border-radius: 9px;
            padding: 9px 22px;
            font-size: 12.5px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 14px rgba(37, 99, 235, 0.25);
            transition: all 0.18s ease-out;
        }}

        .btn-run:hover {{
            background: linear-gradient(135deg, #0ea5e9 0%, #1d4ed8 100%);
            box-shadow: 0 6px 18px rgba(37, 99, 235, 0.32);
        }}

        .btn-run.disabled {{
            background: #cbd5e1;
            color: #f8fafc;
            box-shadow: none;
            cursor: default;
        }}
    </style>
    <script language="javascript">
        var ordemFerramentas = [
            "linha_de_corte",
            "corrigir_vazios",
            "inverter_e_organizar",
            "mudanca_secao_pilares",
            "criar_cotas"
        ];

        var ferramentas = {{
            "linha_de_corte": {{
                titulo: "Linha de Corte",
                desc: "Conecta automaticamente todos os pares de marcadores de corte ($CORTEA) no desenho ou permite tra\u00e7ar manualmente por 2 pontos."
            }},
            "criar_cotas": {{
                titulo: "Criar Cotas",
                desc: "Abre o painel de cotagem para Cota de Pilar (quadrados/capit\u00e9is e contorno lateral), Cota Geral em 3 camadas e Cotar Detalhe."
            }},
            "corrigir_vazios": {{
                titulo: "Corrigir Vazio e Indicador de Laje",
                desc: "Corrige as linhas em X de vazios, remove setas de dire\u00e7\u00e3o de laje e cria o fechamento dos shafts."
            }},
            "inverter_e_organizar": {{
                titulo: "Inverter e Organizar",
                desc: "Converte bolinhas de viga e laje mantendo a orienta\u00e7\u00e3o original, puxa seta quando necess\u00e1rio e resolve sobreposi\u00e7\u00f5es."
            }},
            "mudanca_secao_pilares": {{
                titulo: "Detalhe Mudan\u00e7a de Se\u00e7\u00e3o Pilares",
                desc: "Detecta pilares com redu\u00e7\u00e3o de se\u00e7\u00e3o, agrupa pilares id\u00eanticos e desenha o quadro lateral ampliado em escala 1:25 j\u00e1 cotado."
            }}
        }};

        var selecionadas = {{}};
        var ultimaFerramenta = "linha_de_corte";

        function initDialog() {{
            try {{
                var w = 860, h = 560;
                window.resizeTo(w, h);
                window.moveTo(
                    Math.max(0, Math.floor((screen.availWidth - w) / 2)),
                    Math.max(0, Math.floor((screen.availHeight - h) / 2))
                );
            }} catch (e) {{}}
            mostrarPreview("linha_de_corte");
            atualizarBotaoExecutar();
        }}

        function trocarAba(aba) {{
            var tabF = document.getElementById("tab-ferramentas");
            var tabT = document.getElementById("tab-tabelas");
            var paneF = document.getElementById("pane-ferramentas");
            var paneT = document.getElementById("pane-tabelas");

            if (aba === "tabelas") {{
                tabF.className = "folder-tab";
                tabT.className = "folder-tab active";
                paneF.className = "tab-pane";
                paneT.className = "tab-pane active";
                document.getElementById("prev-title").innerText = "Tabelas";
                document.getElementById("prev-desc").innerText = "Se\u00e7\u00e3o dedicada \u00e0s tabelas de f\u00f4rmas. As op\u00e7\u00f5es ser\u00e3o adicionadas em breve.";
            }} else {{
                tabF.className = "folder-tab active";
                tabT.className = "folder-tab";
                paneF.className = "tab-pane active";
                paneT.className = "tab-pane";
                mostrarPreview(ultimaFerramenta);
            }}
        }}

        function mostrarPreview(acao) {{
            var info = ferramentas[acao];
            if (!info) return;
            ultimaFerramenta = acao;
            document.getElementById("prev-title").innerText = info.titulo;
            document.getElementById("prev-desc").innerText = info.desc;
        }}

        function alternarItem(acao, el) {{
            selecionadas[acao] = !selecionadas[acao];
            el.className = selecionadas[acao] ? "menu-item selected" : "menu-item";
            mostrarPreview(acao);
            atualizarBotaoExecutar();
        }}

        function alternarTodas() {{
            var qtd = contarSelecionadas();
            var marcar = (qtd < ordemFerramentas.length);
            for (var i = 0; i < ordemFerramentas.length; i++) {{
                var k = ordemFerramentas[i];
                selecionadas[k] = marcar;
                var el = document.getElementById("btn-" + k);
                if (el) {{
                    el.className = marcar ? "menu-item selected" : "menu-item";
                }}
            }}
            atualizarBotaoExecutar();
        }}

        function contarSelecionadas() {{
            var n = 0;
            for (var i = 0; i < ordemFerramentas.length; i++) {{
                if (selecionadas[ordemFerramentas[i]]) n++;
            }}
            return n;
        }}

        function atualizarBotaoExecutar() {{
            var n = contarSelecionadas();
            var btn = document.getElementById("btn-executar");
            var btnAll = document.getElementById("btn-toggle-all");
            if (n === 0) {{
                btn.innerText = "Executar";
                btn.className = "btn-run disabled";
            }} else if (n === 1) {{
                btn.innerText = "Executar (1)";
                btn.className = "btn-run";
            }} else {{
                btn.innerText = "Executar (" + n + ")";
                btn.className = "btn-run";
            }}
            btnAll.innerText = (n === ordemFerramentas.length) ? "Limpar sele\u00e7\u00e3o" : "Selecionar tudo";
        }}

        function confirmarExecucao() {{
            var lista = [];
            for (var i = 0; i < ordemFerramentas.length; i++) {{
                var k = ordemFerramentas[i];
                if (selecionadas[k]) {{
                    lista.push('"' + k + '"');
                }}
            }}
            if (lista.length === 0) {{
                return;
            }}
            try {{
                var fso = new ActiveXObject("Scripting.FileSystemObject");
                var f = fso.CreateTextFile("{json_js}", true);
                f.WriteLine('{{"acoes":[' + lista.join(",") + ']}}');
                f.Close();
                window.close();
            }} catch (e) {{
                alert("Erro ao iniciar ferramenta(s): " + e.message);
            }}
        }}

        function executarUnica(acao) {{
            try {{
                var fso = new ActiveXObject("Scripting.FileSystemObject");
                var f = fso.CreateTextFile("{json_js}", true);
                f.WriteLine('{{"acoes":["' + acao + '"]}}');
                f.Close();
                window.close();
            }} catch (e) {{
                alert("Erro ao iniciar ferramenta: " + e.message);
            }}
        }}

        function onKeyDown(ev) {{
            var e = ev || window.event;
            if (!e) return;
            if (e.keyCode === 27) {{
                window.close();
            }} else if (e.keyCode === 13) {{
                confirmarExecucao();
            }}
        }}
    </script>
</head>
<body onload="initDialog();" onkeydown="onKeyDown(event);">
    <div class="page">
        <div class="shell">
            <!-- LADO ESQUERDO: MARCA G3 ENGENHARIA + PREVIEW -->
            <div class="left-pane">
                <div>
                    <div class="brand-row">
                        {brand_mark_html}
                        <div class="brand-text">
                            <h1>G3 Engenharia</h1>
                            <span>M&oacute;dulo de F&ocirc;rmas &bull; TQS EAG</span>
                        </div>
                    </div>

                    <div class="hero-copy">
                        <span class="hero-pill">Central de F&ocirc;rmas</span>
                        <p>Selecione uma ou mais ferramentas no menu ao lado e clique em <strong>Executar</strong> (ou d&ecirc; duplo clique em uma op&ccedil;&atilde;o para rodar direto).</p>
                    </div>
                </div>

                <div class="preview-card">
                    <div class="preview-top">
                        <span class="preview-dot"></span>
                        <div id="prev-title" class="preview-title">Linha de Corte</div>
                    </div>
                    <div id="prev-desc" class="preview-desc"></div>
                </div>
            </div>

            <!-- LADO DIREITO: ABAS ESTILO PASTA (FERRAMENTAS / TABELAS) -->
            <div class="right-menu">
                <div class="folder-tabs">
                    <button id="tab-ferramentas" class="folder-tab active" onclick="trocarAba('ferramentas')">Ferramentas de F&ocirc;rmas</button>
                    <button id="tab-tabelas" class="folder-tab" onclick="trocarAba('tabelas')">Tabelas</button>
                </div>

                <div class="tab-body">
                    <!-- ABA 1: FERRAMENTAS DE FORMAS -->
                    <div id="pane-ferramentas" class="tab-pane active">
                        <div class="menu-header-row">
                            <div class="menu-header">Selecione 1 ou mais op&ccedil;&otilde;es</div>
                            <button id="btn-toggle-all" class="btn-toggle-all" onclick="alternarTodas()">Selecionar tudo</button>
                        </div>
                        <div class="menu-list">
                            <button id="btn-linha_de_corte" class="menu-item"
                                onmouseover="mostrarPreview('linha_de_corte')"
                                onclick="alternarItem('linha_de_corte', this)"
                                ondblclick="executarUnica('linha_de_corte')">
                                <div class="item-icon">&#9986;</div>
                                <div class="item-body">
                                    <div class="item-title">Linha de Corte</div>
                                    <div class="item-sub">Conecta marcadores de corte</div>
                                </div>
                                <div class="item-check">&#10003;</div>
                            </button>

                            <button id="btn-criar_cotas" class="menu-item"
                                onmouseover="mostrarPreview('criar_cotas')"
                                onclick="alternarItem('criar_cotas', this)"
                                ondblclick="executarUnica('criar_cotas')">
                                <div class="item-icon">&#8660;</div>
                                <div class="item-body">
                                    <div class="item-title">Criar Cotas</div>
                                    <div class="item-sub">Geral, pilares, contorno e detalhes</div>
                                </div>
                                <div class="item-check">&#10003;</div>
                            </button>

                            <button id="btn-corrigir_vazios" class="menu-item"
                                onmouseover="mostrarPreview('corrigir_vazios')"
                                onclick="alternarItem('corrigir_vazios', this)"
                                ondblclick="executarUnica('corrigir_vazios')">
                                <div class="item-icon">&#10006;</div>
                                <div class="item-body">
                                    <div class="item-title">Corrigir Vazio e Indicador</div>
                                    <div class="item-sub">Vazios, indicadores de laje e shafts</div>
                                </div>
                                <div class="item-check">&#10003;</div>
                            </button>

                            <button id="btn-inverter_e_organizar" class="menu-item"
                                onmouseover="mostrarPreview('inverter_e_organizar')"
                                onclick="alternarItem('inverter_e_organizar', this)"
                                ondblclick="executarUnica('inverter_e_organizar')">
                                <div class="item-icon">&#8635;</div>
                                <div class="item-body">
                                    <div class="item-title">Inverter e Organizar</div>
                                    <div class="item-sub">Bolinhas e anti-sobreposi&ccedil;&atilde;o</div>
                                </div>
                                <div class="item-check">&#10003;</div>
                            </button>

                            <button id="btn-mudanca_secao_pilares" class="menu-item"
                                onmouseover="mostrarPreview('mudanca_secao_pilares')"
                                onclick="alternarItem('mudanca_secao_pilares', this)"
                                ondblclick="executarUnica('mudanca_secao_pilares')">
                                <div class="item-icon">&#9635;</div>
                                <div class="item-body">
                                    <div class="item-title">Mudan&ccedil;a de Se&ccedil;&atilde;o Pilares</div>
                                    <div class="item-sub">Quadro lateral ampliado 1:25</div>
                                </div>
                                <div class="item-check">&#10003;</div>
                            </button>
                        </div>
                    </div>

                    <!-- ABA 2: TABELAS -->
                    <div id="pane-tabelas" class="tab-pane">
                        <div class="empty-state">
                            <div class="empty-icon">&#9638;</div>
                            <div class="empty-title">Tabelas de F&ocirc;rmas</div>
                            <div class="empty-desc">Espa&ccedil;o pronto para receber as op&ccedil;&otilde;es de tabelas.</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- RODAPE INFERIOR -->
        <div class="bottom-bar">
            <div class="author-credit">Desenvolvido por <strong>Ediglanthio Samuel Araujo Brand&atilde;o</strong></div>
            <div class="footer-actions">
                <button class="btn-close" onclick="window.close()">Fechar</button>
                <button id="btn-executar" class="btn-run disabled" onclick="confirmarExecucao()">Executar</button>
            </div>
        </div>
    </div>
</body>
</html>"""

    try:
        with open(hta_path, "w", encoding="utf-8-sig") as f:
            f.write(hta_content)

        subprocess.call(["mshta", hta_path])

        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                dados = json.load(f)
            acoes = dados.get("acoes")
            if isinstance(acoes, list):
                return acoes
            acao_unica = dados.get("acao")
            return [acao_unica] if acao_unica else []
        return []
    finally:
        for p in (json_path, hta_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


def meucmd(eag, tqsjan):
    """Entry point principal de Formas: abre a tela moderna e executa 1 ou mais ferramentas selecionadas."""
    acoes = abrir_tela_formas()
    if not acoes:
        return

    mapa_acoes = {
        "linha_de_corte": cmd_linha_de_corte,
        "criar_cotas": cmd_criar_cotas,
        "corrigir_vazios": cmd_corrigir_vazios,
        "inverter_e_organizar": cmd_inverter_e_organizar,
        "mudanca_secao_pilares": cmd_detalhe_mudanca_secao_pilares,
    }
    for acao in acoes:
        fn = mapa_acoes.get(acao)
        if fn is not None:
            fn(eag, tqsjan)


if __name__ == "__main__":
    print("Acoes selecionadas:", abrir_tela_formas())
