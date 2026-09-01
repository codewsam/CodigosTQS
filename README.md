

---

### 1. Requisitos no computador de quem vai testar
Para rodar programas em Python dentro do TQS, o outro computador precisa:
1. Ter o **TQS instalado** (a partir da versão V23/V24/V25).
2. Ter o **Python instalado** (versão 64 bits, recomendado 3.10 ou superior, marcada a opção *"Add Python to PATH"* na instalação).
3. O pacote de integração do TQS para Python instalado. Caso o TQS não tenha instalado automaticamente, a pessoa deve abrir o terminal/CMD na pasta `C:\TQSW\EXEC\Python` e executar:
   ```cmd
   pip install TQSPythonInterface-1.2.1-py310-none-any.whl
   ```
   *(O nome exato do arquivo `.whl` pode variar conforme a versão do TQS instalada nela).*

---

### 2. Quais arquivos você precisa enviar
Você deve enviar os seguintes arquivos:

1. **`MEUPLUGIN.py`** *(seu script com a lógica da escada e interface)*
2. **`diagrama_escada.png`** *(a imagem ilustrativa exibida na tela de entrada)*
3. **O arquivo de menu `.PYMEN`** que aciona o plugin.

---

### 3. Como configurar o menu (`.PYMEN`)
O TQS carrega extensões em Python através de arquivos com extensão `.PYMEN` salvos na pasta **`C:\TQSW\EXEC\Python`**.

- **Para aparecer em todos os editores gráficos do TQS:**  
  Crie ou edite o arquivo **`EAG.PYMEN`**
- **Para aparecer apenas no Editor de Formas:**  
  Crie ou edite o arquivo **`EAGFOR.PYMEN`**
- **Para aparecer no Editor de Armaduras:**  
  Crie ou edite o arquivo **`EAGFER.PYMEN`**

O conteúdo do arquivo `.PYMEN` deve ser:

```ini
[PYTHON]
MEUPLUGIN.PY

[CMD]
ID_ESCADA_CUSTOM,MEUPLUGIN.PY,meucmd
Inserir Escada Paramétrica

[MENU]
SUBMENU,Escadas G3
    MENUITEM,ID_ESCADA_CUSTOM,&Gerar Escada Paramétrica
FIMSUBMENU
```

---

### 4. Passo a passo para a outra pessoa instalar

1. **Copiar os arquivos:**  
   Colar o `MEUPLUGIN.py`, o `diagrama_escada.png` e o `EAG.PYMEN` (ou `EAGFOR.PYMEN`) dentro da pasta:
   ```
   C:\TQSW\EXEC\Python
   ```
2. **Abrir o TQS:**  
   Ao abrir qualquer desenho no Editor Gráfico (EAG), aparecerá no menu superior a nova aba/menu (ex: **`Escadas G3`** -> **`Gerar Escada Paramétrica`**).
3. Clicar no comando para abrir a tela e testar.
