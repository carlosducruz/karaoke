# 🎬 Arquitetura do Karaoke Player

## 📐 Visão Geral

O sistema agora está dividido em **dois componentes** que se comunicam via socket:

```
┌─────────────────────────┐         Socket (porta 5555)         ┌─────────────────────────┐
│                         │ ◄──────────────────────────────────► │                         │
│   main.py               │                                      │   karaoke_player.py     │
│   (Painel de Controle)  │         Comandos:                   │   (Player de Vídeo)     │
│                         │         • load                       │                         │
│   Monitor Principal     │         • play                       │   Segundo Monitor       │
│                         │         • pause                      │   (Fullscreen)          │
│   • Playlist            │         • stop                       │                         │
│   • Busca Catálogo      │         • pitch                      │   • Exibe vídeo         │
│   • Controles           │         • seek                       │   • Controle de tom     │
│   • Banco de Dados      │         • quit                       │   • Barra de progresso  │
│                         │                                      │                         │
└─────────────────────────┘                                      └─────────────────────────┘
```

---

## 🔧 Componentes

### 1️⃣ **main.py** - Painel de Controle (Monitor Principal)

**Responsabilidades:**
- ✅ Interface de controle e gerenciamento
- ✅ Busca no catálogo de músicas
- ✅ Gerenciamento de playlist
- ✅ Modo Evento (participantes, avatares, pontuação)
- ✅ Banco de dados SQLite
- ✅ **ENVIA comandos** para o player via socket

**Funcionalidades Principais:**
- `iniciar_player_externo()` - Inicia o processo do player
- `conectar_player()` - Conecta via socket TCP
- `enviar_comando_player(comando, dados)` - Envia comandos
- Interface completa com playlist visual

**Não possui:**
- ❌ VLC player (removido)
- ❌ Renderização de vídeo
- ❌ Thread de vídeo

---

### 2️⃣ **karaoke_player.py** - Player de Vídeo (Segundo Monitor)

**Responsabilidades:**
- ✅ Reprodução de vídeo com VLC
- ✅ **RECEBE comandos** via socket do painel
- ✅ Controle de tom (pitch shift)
- ✅ Barra de progresso (seek)
- ✅ Posicionamento automático no segundo monitor

**Funcionalidades Principais:**
- `iniciar_servidor()` - Inicia servidor socket na porta 5555
- `processar_comandos(conn)` - Processa comandos recebidos
- `executar_comando(comando, dados)` - Executa ações no player
- `posicionar_segundo_monitor()` - Move janela para 2º monitor

**Comandos Aceitos:**
| Comando | Dados | Descrição |
|---------|-------|-----------|
| `load` | `{path, duration, fps, width, height}` | Carrega vídeo |
| `play` | - | Inicia reprodução |
| `pause` | - | Pausa reprodução |
| `stop` | - | Para reprodução |
| `pitch` | `{steps}` | Ajusta tom (+/- semitons) |
| `seek` | `{time}` | Navega para posição (segundos) |
| `quit` | - | Fecha o player |

---

## 🚀 Como Usar

### Inicialização

1. **Execute apenas o `main.py`:**
   ```bash
   python main.py
   ```

2. **O `main.py` automaticamente:**
   - ✅ Inicia o `karaoke_player.py` em processo separado
   - ✅ Move o player para o segundo monitor
   - ✅ Conecta via socket (porta 5555)
   - ✅ Aguarda comandos

3. **No painel de controle (`main.py`):**
   - Carregue músicas
   - Use a busca no catálogo
   - Gerencie a playlist
   - Controle a reprodução

4. **No segundo monitor:**
   - O vídeo aparecerá automaticamente
   - Modo fullscreen/maximizado
   - Sem controles visíveis (controlado remotamente)

---

## 🔌 Protocolo de Comunicação

### Formato das Mensagens

```python
# Estrutura da mensagem (serializada com pickle)
{
    'comando': 'play',  # Nome do comando
    'dados': {...}      # Dados opcionais (dict)
}
```

### Processo de Envio

1. Serializa mensagem com `pickle.dumps()`
2. Envia tamanho da mensagem (4 bytes, big-endian)
3. Envia mensagem serializada
4. Player processa e executa

### Exemplo de Código

```python
# No main.py (painel)
self.enviar_comando_player('load', {
    'path': '/caminho/video.mp4',
    'duration': 180.5,
    'fps': 30,
    'width': 1920,
    'height': 1080
})

# No karaoke_player.py (player)
def executar_comando(self, comando, dados):
    if comando == 'load':
        self.video_file = dados['path']
        self.duration = dados['duration']
        # ...
```

---

## 🖥️ Posicionamento Multi-Monitor

O player detecta automaticamente o segundo monitor:

```python
def posicionar_segundo_monitor(self):
    screen_width = self.root.winfo_screenwidth()
    x = screen_width  # Move para além do primeiro monitor
    y = 0
    self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    self.root.state('zoomed')  # Maximiza
```

**Como funciona:**
- Se `screen_width` > largura da janela → múltiplos monitores
- Posiciona em `x = screen_width` (início do 2º monitor)
- Maximiza a janela automaticamente

---

## ⚠️ Troubleshooting

### Player não inicia
✅ Verifique se `karaoke_player.py` está no mesmo diretório que `main.py`

### Porta já em uso
✅ Certifique-se de que não há outra instância rodando
✅ Mude a porta em ambos os arquivos (porta 5555)

### Player não aparece no segundo monitor
✅ Verifique configurações de exibição do Windows
✅ Conecte o segundo monitor antes de iniciar

### Comandos não funcionam
✅ Verifique logs em `karaoke_debug.log`
✅ Teste conexão: `telnet localhost 5555`

---

## 📝 Logs

Ambos os componentes geram logs detalhados:

- **main.py**: `karaoke_debug.log` (diretório do script)
- **karaoke_player.py**: `karaoke_debug.log` (diretório do script)

**Eventos Registrados:**
- 📤 Comandos enviados (main.py)
- 📥 Comandos recebidos (karaoke_player.py)
- ✅ Execução de comandos
- ❌ Erros de comunicação
- 🔌 Conexões e desconexões

---

## 🎯 Benefícios da Nova Arquitetura

1. **Separação de Responsabilidades**
   - Painel de controle independente do player
   - Fácil manutenção e debug

2. **Multi-Monitor Nativo**
   - Player automático no segundo monitor
   - Melhor experiência para eventos

3. **Escalabilidade**
   - Possibilidade de múltiplos players
   - Controle remoto via rede (futuro)

4. **Segurança**
   - Processos isolados
   - Crash de um não afeta o outro

5. **Performance**
   - Renderização de vídeo em processo separado
   - UI do painel mais responsiva

---

## 🔮 Evoluções Futuras

- [ ] Controle via rede (TCP/IP remoto)
- [ ] Múltiplos players simultâneos
- [ ] Interface web para controle
- [ ] Sincronização de tempo entre players
- [ ] Streaming de vídeo via rede

---

**Desenvolvido para Karaoke Player v2.0**
*Arquitetura Cliente-Servidor*
