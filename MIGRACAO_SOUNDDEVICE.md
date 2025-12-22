# Migração de PyAudio para sounddevice

## 🎯 Motivo da Mudança

O **PyAudio** frequentemente apresenta problemas de instalação no Windows, especialmente relacionados a:
- Compilação de bibliotecas C
- Dependências do PortAudio
- Incompatibilidades com diferentes versões do Python

O **sounddevice** é uma alternativa moderna que:
- ✅ Instala facilmente via pip
- ✅ Melhor compatibilidade multiplataforma
- ✅ API mais simples e pythônica
- ✅ Usa callbacks nativos (sem threads adicionais necessárias)
- ✅ Baseado em PortAudio (mesma base do PyAudio)

## 📦 Instalação

### Opção 1: Script Automático (Recomendado)
```powershell
.\instalar_sounddevice.ps1
```

### Opção 2: Manual
```bash
# Desinstalar PyAudio (se existir)
pip uninstall -y pyaudio

# Instalar sounddevice
pip install sounddevice numpy
```

### Opção 3: Via requirements.txt
```bash
pip install -r requirements.txt
```

## 🔧 Mudanças Técnicas

### Principais Diferenças

| Aspecto | PyAudio | sounddevice |
|---------|---------|-------------|
| Instalação | Problemática (requer compilação) | Simples (pip install) |
| API de Stream | `audio.open()` com polling | `InputStream()` com callback |
| Formato de Dados | Bytes (requires `frombuffer`) | NumPy array direto |
| Shape dos Dados | 1D interleaved [L,R,L,R...] | 2D shape (frames, channels) |
| Gerenciamento | `start_stream()` / `stop_stream()` | `start()` / `stop()` |
| Cleanup | `terminate()` necessário | Não necessário |

### Arquivos Modificados

1. **main.py**
   - Import: `import sounddevice as sd`
   - Removido: `pyaudio.PyAudio()` inicialização
   - Novo método: `_processar_audio_vu_callback()` 
   - Stream: `sd.InputStream()` com callback nativo
   - Dados: Array NumPy shape (frames, 2) para estéreo

2. **karaoke_player.py**
   - Import: `import sounddevice as sd`
   - Removido: `pyaudio.PyAudio()` inicialização
   - Callback integrado em `iniciar_captura_pontuacao()`
   - Removido método: `_capturar_microfone()` (substituído por callback)

3. **requirements.txt**
   - Removido: `pyaudio`
   - Adicionado: `sounddevice`

## 🎤 Funcionalidades Mantidas

Todas as funcionalidades continuam funcionando:

✅ V.U. meter (medidor de volume do microfone)  
✅ Captura estéreo (canais L/R)  
✅ Ajuste de sensibilidade (ganho 1x-10x)  
✅ Cálculo de RMS (Root Mean Square)  
✅ Conversão para dB (decibéis)  
✅ Indicadores visuais coloridos  
✅ Sistema de pontuação de karaoke  
✅ Ativação automática ao tocar música  
✅ Popup de pontuação ao final  

## 🔍 Detalhes da Implementação

### Formato de Dados - sounddevice

O sounddevice retorna dados em formato NumPy array com shape diferente:

**Estéreo (2 canais):**
```python
# PyAudio: array 1D interleaved
[L1, R1, L2, R2, L3, R3, ...]

# sounddevice: array 2D
[[L1, R1],
 [L2, R2],
 [L3, R3],
 ...]

# Acesso aos canais:
left_channel = audio_data[:, 0]   # Coluna 0
right_channel = audio_data[:, 1]  # Coluna 1
```

**Mono (1 canal):**
```python
# PyAudio: array 1D
[sample1, sample2, sample3, ...]

# sounddevice: array 1D (igual)
[sample1, sample2, sample3, ...]
```

### Callback vs Thread

**PyAudio (antiga forma):**
```python
# Thread manual necessária
def _processar_audio_vu(self, chunk_size):
    while self.vu_running:
        data = self.audio_stream.read(chunk_size)
        # processar...
        
threading.Thread(target=self._processar_audio_vu, args=(CHUNK,), daemon=True).start()
```

**sounddevice (nova forma):**
```python
# Callback nativo (mais eficiente)
def audio_callback(indata, frames, time_info, status):
    if self.vu_running:
        self._processar_audio_vu_callback(indata.copy())

stream = sd.InputStream(callback=audio_callback, ...)
stream.start()  # Callback é chamado automaticamente
```

## 🐛 Troubleshooting

### Erro: "sounddevice não encontrado"
```bash
pip install sounddevice
```

### Erro: "No Default Input Device"
- Verifique se há um microfone conectado
- No Windows: Configurações > Sistema > Som > Entrada
- Teste com: `python -m sounddevice`

### Erro: "PortAudio library not found"
No Windows isso é raro, mas se ocorrer:
```bash
# Reinstalar com --force
pip install --force-reinstall sounddevice
```

### Testar dispositivos disponíveis
```python
import sounddevice as sd
print(sd.query_devices())
```

## 📊 Performance

**Vantagens observadas:**

- ✅ Latência menor (callback direto vs polling)
- ✅ CPU usage mais eficiente
- ✅ Menos overhead de conversão de dados
- ✅ Melhor integração com NumPy

## 🚀 Próximos Passos

Após instalar e testar:

1. Execute o karaoke: `python main.py`
2. Carregue uma música
3. O V.U. meter será ativado automaticamente
4. Cante e veja sua pontuação ao final!

## 📝 Notas

- A migração é **100% compatível** com o código anterior
- Nenhuma funcionalidade foi perdida
- A qualidade do áudio permanece a mesma
- Os algoritmos de pontuação não foram alterados

---

**Desenvolvido por:** Fabio  
**Data da Migração:** Dezembro 2025  
**Biblioteca:** sounddevice 0.4.x  
