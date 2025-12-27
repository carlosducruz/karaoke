# 🎬 Requisitos para executar o Karaoke Player

## 🔧 Instalação do VLC Player tocar o Karaoke Player

### Método 1: Pelo Site Oficial (Recomendado)
* Acesse o Site: Abra seu navegador e vá para videolan.org.
* Baixe o Arquivo: Clique no botão "Baixar VLC" (ou uma seta ao lado para escolher a versão 64-bit) para iniciar o download do instalador.
* Execute o Instalador: Após o download, clique no arquivo baixado (geralmente um .exe) para abrir o assistente de instalação.

Siga os Passos:
1. Selecione o idioma (Português do Brasil estará lá) e clique em OK.
2. Clique em "Próximo" na tela de boas-vindas.
3. Aceite a licença e clique em "Próximo".
4. Mantenha os componentes padrão e clique em "Próximo".
5. Escolha o local de instalação (o padrão é bom) e clique em "Instalar".
6. Finalize: Clique em "Concluir" e marque a opção para iniciar o VLC se desejar. 

### Método 2: Pela Microsoft Store

---

## 🔧 Instalação do FFmpeg para Karaoke Player

O **Karaoke Player** precisa do **FFmpeg** instalado para processar vídeos e áudio.

### ✅ Verificar se já está instalado

* Abra o PowerShell ou CMD e digite:

```powershell
ffmpeg -version
ffprobe -version
```

Se aparecer a versão, ** pare por aqui, pois já estão instalados!** ✓

---

### 📥 Como Instalar no Windows

#### Opção Principal: Usando Winget (Recomendado - Windows 10/11)

```powershell
winget install ffmpeg
```
 

#### Opção Manual: Download Manual

1. **Baixar FFmpeg:**
   - Acesse: https://www.gyan.dev/ffmpeg/builds/
   - Baixe: **ffmpeg-release-essentials.zip**

2. **Extrair:**
   - Extraia o arquivo ZIP
   - Exemplo: `C:\ffmpeg`

3. **Adicionar ao PATH do windows:**

   **Opção A - Copiar arquivos (mais fácil):**
   - Vá para: `C:\ffmpeg\bin\`
   - Copie `ffmpeg.exe` e `ffprobe.exe`
   - Cole em: `C:\Windows\System32\`

   **Opção B - Adicionar ao PATH do sistema:**
   - Pressione `Win + X` → **Sistema**
   - Clique em **Configurações avançadas do sistema**
   - Botão **Variáveis de Ambiente**
   - Em **Variáveis do sistema**, selecione **Path** → **Editar**
   - Clique em **Novo**
   - Digite: `C:\ffmpeg\bin`
   - **OK** em todas as janelas

4. **Testar:**
   - Feche e reabra o PowerShell ou Console (CMD)
   - Digite: `ffmpeg -version`

--- 
 
 
## 🔧 Obtenha codigo fonte e executável do Karaoke Player  

### Baixe do repositório GIT

#### Caso não tenha o git, instale conforme abaixo

* Passo a Passo
1. Download: Acesse o site oficial do Git para Windows: https://git-scm.com/download/win e baixe o instalador.
3. Execução: Abra o arquivo baixado (ex: Git-2.xx.x-64-bit.exe) e siga as instruções do assistente.
4. Configurações (Recomendado):
    - Componentes: As opções padrão são ótimas para a maioria dos usuários, mas você pode escolher o editor de texto padrão (como VS Code) ou adicionar atalhos.
    - PATH: Mantenha a opção que permite usar o Git no Prompt de Comando/PowerShell, pois é o mais comum.
    - Final de Linha: A opção padrão de "Checkout Windows, commit Unix" (CRLF) é geralmente a melhor para compatibilidade.
5. Finalização: Clique em Install e depois em Finish. 


#### Abra uma janela nova Console do Prompt de Comando

6. Baixe o código fonte e após entre na pasta karaoke

``` console
git clone https://github.com/carlosducruz/karaoke.git
cd karaoke
git pull

```

### 🚀 Executar  o Karaoke Player pelo executável (Opção Mais Simples)

* Abra o explorador de arquivos (no windows o Explorer) e acesse a pasta dist 
* Os arquivos KaraokePlayer.exe e karaoke_eventos.db e karaoke_debug.log (opcional) devem estar presentes
* Dê um duplo cliquem no KaraokePlayer.exe


### 🚀 Executar  o Karaoke Player pelo código fonte (Opção Avançada)
#### Caso necessário instale o python

* Método 1: Via Site Oficial (Recomendado para controle total)
1. Baixe o Instalador: Acesse www.python.org/downloads/windows/ e baixe o instalador executável para a versão mais recente (geralmente 64-bit).
2. Execute o Instalador: Dê um duplo clique no arquivo baixado.
3. Marque a Opção PATH: Na primeira janela do instalador, marque a caixa "Add python.exe to PATH". Isso é crucial para usar o Python facilmente.
4. Instale: Clique em "Install Now" (Instalar Agora) ou "Customize installation" (Instalar personalizado) e siga as instruções.
5. Desabilite Limite de Caminho (Opcional): No final, pode aparecer uma opção para desabilitar o limite de comprimento de caminho do Windows; habilite-a para evitar problemas futuros. 

Método 2: Via Microsoft Store (Mais Simples)
 

* Instale as libs mínimas para o Python, crie o ambiente inicial, ative-o e por fim instale todas as demais libs necessárias para o projeto

``` console

python -m pip install --upgrade pip setuptools wheel
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

``` 
 
* Ative o ambiente Python, caso não esteja ativo,  e Execute o aplicativo

``` console
venv\Scripts\activate
python main.py

```

### Caso queira gerar um novo executável

pyinstaller --onefile --windowed --icon=avatares/karaoke.ico --name=KaraokePlayer main.py