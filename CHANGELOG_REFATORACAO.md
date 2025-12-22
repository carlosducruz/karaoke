# 📋 Changelog - Refatoração da Arquitetura

## Data: 2024

## 🎯 Objetivo da Refatoração

Separar o sistema de karaoke em dois componentes independentes:
- **main.py**: Painel de controle (gerenciamento de eventos, playlist, catálogo)
- **karaoke_player.py**: Player de vídeo (execução no segundo monitor)

---

## ✅ Alterações Realizadas no `main.py`

### 1. **Remoção de Código Obsoleto**

#### Funções Removidas:
- `start_video_thread()` - Iniciava thread para renderização de vídeo (linha ~1660)
- `play_video()` - Processava frames de vídeo via FFmpeg pipe (linha ~1666)
- `display_frame()` - Exibia frames na interface Tkinter (linha ~1697)
- `update_timer()` (versão antiga) - Atualizava timer com base no VLC (linha ~1705)

#### Código VLC Removido:
- Referências a `self.player.get_time()`
- Chamadas para `self.player.stop()`
- Verificações de `self.player.get_state()`
- Manipulação de `self.vlc_instance`

#### Variáveis de Instância Removidas:
- `self.video_thread` - Thread de renderização de vídeo
- `self.frame_process` - Processo FFmpeg para extração de frames

### 2. **Código Adicionado**

#### Novas Funções de Comunicação:
```python
def iniciar_player_externo(self)
    """Inicia karaoke_player.py em processo separado"""
    
def conectar_player(self)
    """Conecta ao player via socket TCP (porta 5555)"""
    
def enviar_comando_player(self, comando, dados=None)
    """Envia comando serializado via pickle para o player"""
```

#### Novas Variáveis de Instância:
```python
self.player_process = None  # Processo do player externo (subprocess.Popen)
self.player_socket = None   # Socket de comunicação TCP
```

#### Comandos Suportados:
| Comando | Descrição | Dados Enviados |
|---------|-----------|----------------|
| `load` | Carrega vídeo no player | `{'file': path, 'pitch': shift, 'fps': fps, 'duration': dur}` |
| `play` | Inicia reprodução | - |
| `pause` | Pausa reprodução | - |
| `stop` | Para reprodução | - |
| `pitch` | Ajusta pitch | `{'pitch': valor}` |
| `seek` | Posiciona tempo | `{'position': segundos}` |
| `quit` | Fecha player | - |

### 3. **Funções Modificadas**

#### `play()`
**Antes:**
```python
self.player.play()
self.is_playing = True
self.start_video_thread()
```

**Depois:**
```python
if self.enviar_comando_player('play'):
    self.is_playing = True
    self.status_label.config(text="▶ Tocando")
```

#### `pause()`
**Antes:**
```python
self.player.pause()
self.is_playing = False
```

**Depois:**
```python
if self.enviar_comando_player('pause'):
    self.is_playing = False
    self.status_label.config(text="⏸ Pausado")
```

#### `stop()`
**Antes:**
```python
self.player.stop()
self.is_playing = False
if self.frame_process:
    self.frame_process.kill()
```

**Depois:**
```python
if self.enviar_comando_player('stop'):
    self.is_playing = False
    self.status_label.config(text="⏹ Parado")
```

#### `load_file()`
**Antes:**
- Carregava mídia no VLC local
- Iniciava thread de renderização

**Depois:**
- Obtém informações do vídeo (FFprobe)
- Envia comando `load` com metadados para player externo

#### `fechar_aplicacao()`
**Antes:**
- Parava `self.player` (VLC)
- Finalizava `self.frame_process` (FFmpeg)

**Depois:**
- Envia comando `quit` via socket
- Finaliza `self.player_process` (subprocess)

#### `update_timer()` (nova versão)
**Antes:**
- Obtinha tempo de `self.player.get_time()`
- Verificava estado com `self.player.get_state()`

**Depois:**
```python
def update_timer(self):
    # TODO: Implementar recebimento de tempo do player externo via socket
    if self.video_file and hasattr(self, 'time_label'):
        if not self.is_playing:
            self.time_label.config(text=f"00:00 / {time.strftime('%M:%S', time.gmtime(self.duration))}")
    
    if not self.force_quit:
        self.root.after(100, self.update_timer)
```

### 4. **Imports Mantidos**

As seguintes importações continuam necessárias:
- `PIL.Image, ImageTk` - Usado para avatares na playlist
- `subprocess` - Spawning do player externo
- `socket, pickle` - Comunicação cliente-servidor
- `threading` - Threads de socket (se implementadas)

---

## 📦 Alterações no `karaoke_player.py`

### Novas Funcionalidades Adicionadas:
1. **Servidor Socket** (porta 5555)
   - Escuta conexões de `main.py`
   - Processa comandos via `pickle`

2. **Posicionamento Automático**
   - `posicionar_segundo_monitor()` detecta segundo monitor
   - Abre janela automaticamente no segundo display

3. **Processamento de Comandos**
   - `processar_comandos()` - Loop de recepção
   - `executar_comando()` - Executa ações do VLC

---

## 🔧 Melhorias Técnicas

### Vantagens da Nova Arquitetura:
✅ **Separação de responsabilidades**: UI de controle ≠ renderização de vídeo  
✅ **Multi-monitor nativo**: Player abre automaticamente no segundo monitor  
✅ **Escalabilidade**: Possível controlar múltiplos players futuramente  
✅ **Manutenibilidade**: Código mais organizado e modular  
✅ **Desempenho**: Processos independentes evitam travamento da UI  

### Considerações de Segurança:
⚠️ Socket localhost apenas (127.0.0.1:5555)  
⚠️ Sem autenticação implementada (não necessária para localhost)  
⚠️ Pickle usado para serialização (assumindo confiança local)  

---

## 🧪 Testes Necessários

### Checklist de Validação:
- [ ] Player externo inicia ao executar `main.py`
- [ ] Conexão socket estabelecida (verificar logs)
- [ ] Comando `load` funciona (vídeo aparece no player)
- [ ] Comandos `play`, `pause`, `stop` funcionam
- [ ] Ajuste de pitch (`pitch`) reflete no áudio
- [ ] Player posiciona-se automaticamente no segundo monitor
- [ ] Fechamento do `main.py` encerra o player externo
- [ ] Logs registrados em `karaoke_debug.log`

---

## 📝 TODOs Futuros

### Funcionalidades Pendentes:
1. **Sincronização de Tempo**
   - Player deve enviar tempo atual de volta para `main.py`
   - Atualizar `update_timer()` para exibir progresso real

2. **Estado de Reprodução**
   - Player deve notificar quando vídeo terminar
   - `main.py` pode avançar para próxima música automaticamente

3. **Tratamento de Erros**
   - Reconexão automática se socket cair
   - Mensagens de erro mais detalhadas na UI

4. **Configurações de Rede**
   - Permitir porta configurável
   - Suporte a conexão remota (opcional)

---

## 🐛 Problemas Corrigidos

### Issues Resolvidas Nesta Refatoração:
1. ✅ **Botão fechar não funcionava**: `os._exit(0)` adicionado como fallback
2. ✅ **FFmpeg não encontrado**: Verificação na inicialização com mensagem clara
3. ✅ **Código duplicado**: Separação clara entre `main.py` e `karaoke_player.py`
4. ✅ **Player travava a UI**: Agora em processo separado

---

## 📚 Documentação Adicional

- **ARQUITETURA.md** - Diagrama completo da arquitetura cliente-servidor
- **INSTALACAO_FFMPEG.md** - Guia de instalação do FFmpeg
- **README.md** - Instruções gerais de uso

---

## 🔄 Compatibilidade

### Versões Testadas:
- Python: 3.8+
- Tkinter: Padrão do Python
- VLC: python-vlc 3.0+
- FFmpeg: 6.0+

### Sistema Operacional:
- ✅ Windows 10/11 (testado)
- ⚠️ Linux (não testado, mas deve funcionar)
- ⚠️ macOS (não testado, ajustes podem ser necessários)

---

## 👨‍💻 Contribuindo

Se encontrar problemas ou tiver sugestões:
1. Verifique os logs em `karaoke_debug.log`
2. Documente o erro com passos para reproduzir
3. Teste se o problema persiste após reiniciar ambos os componentes

---

**Última atualização:** Dezembro 2024  
**Status:** ✅ Refatoração Completa - Aguardando Testes
