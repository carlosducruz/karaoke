# 🧪 Guia de Testes - Sistema de Karaoke Refatorado

## ⚡ Teste Rápido (Quick Start)

### 1. Verificar Pré-requisitos
```powershell
# Verificar Python
python --version

# Verificar FFmpeg
ffmpeg -version
ffprobe -version

# Verificar dependências Python
pip list | Select-String -Pattern "vlc|PIL|Pillow"
```

Se faltar FFmpeg, siga: **INSTALACAO_FFMPEG.md**

---

## 🎯 Testes Básicos

### Teste 1: Inicialização do Sistema
**Objetivo**: Verificar se ambos os componentes iniciam corretamente

**Passos:**
```powershell
cd c:\temp\Fabio\karaoke
python main.py
```

**Resultado Esperado:**
- ✅ Janela `main.py` abre (painel de controle)
- ✅ Janela `karaoke_player.py` abre automaticamente
- ✅ Player posiciona-se no segundo monitor (se disponível)
- ✅ Nenhum erro no console
- ✅ Arquivo `karaoke_debug.log` criado

**Verificar Logs:**
```powershell
Get-Content karaoke_debug.log -Tail 20
```

Deve conter:
```
🎬 Iniciando player externo...
✅ Player externo iniciado
🔌 Conectando ao player...
✅ Conectado ao player externo
```

---

### Teste 2: Comunicação Socket
**Objetivo**: Verificar se os comandos são transmitidos corretamente

**Passos:**
1. No `main.py`, clique em **"Selecionar Arquivo"**
2. Escolha um arquivo `.mp4`
3. Aguarde o processamento
4. Clique em **"▶ Play"**

**Resultado Esperado:**
- ✅ Vídeo aparece no player externo
- ✅ Status muda para "▶ Tocando" no painel
- ✅ Áudio reproduz corretamente
- ✅ Nenhum erro de socket

**Logs Esperados:**
```
📤 Enviando comando ao player: load
✅ Comando load enviado com sucesso
📤 Enviando comando ao player: play
✅ Comando play enviado com sucesso
```

---

### Teste 3: Controles de Reprodução
**Objetivo**: Testar todos os botões de controle

**Passos:**
1. Com vídeo carregado e tocando
2. Clique em **"⏸ Pause"** → vídeo deve pausar
3. Clique em **"▶ Play"** → vídeo deve retomar
4. Clique em **"⏹ Stop"** → vídeo deve parar

**Resultado Esperado:**
| Ação | Status Exibido | Comportamento Player |
|------|----------------|----------------------|
| Play | "▶ Tocando" | Vídeo toca |
| Pause | "⏸ Pausado" | Vídeo pausa |
| Stop | "⏹ Parado" | Vídeo para |

---

### Teste 4: Ajuste de Pitch
**Objetivo**: Verificar alteração de tom

**Passos:**
1. Com vídeo carregado
2. Ajuste o slider de pitch (ex: +2 ou -2)
3. Clique em "▶ Play"

**Resultado Esperado:**
- ✅ Áudio reproduz com tom alterado
- ✅ Mensagem no log: `🎵 Alterando pitch para: +2`
- ✅ Arquivo temporário criado: `temp_pitchX.mp4`

**Verificar:**
```powershell
Get-ChildItem $env:TEMP | Where-Object { $_.Name -like "*pitch*.mp4" }
```

---

### Teste 5: Multi-Monitor (Se Disponível)
**Objetivo**: Confirmar posicionamento automático

**Pré-requisito**: Dois monitores conectados

**Passos:**
1. Iniciar `main.py`
2. Observar onde as janelas abrem

**Resultado Esperado:**
- ✅ `main.py` abre no monitor principal
- ✅ `karaoke_player.py` abre no segundo monitor
- ✅ Player ocupa tela cheia no segundo monitor

**Se não funcionar:**
- Verifique resolução detectada nos logs
- Ajuste manualmente a geometria em `karaoke_player.py` → `posicionar_segundo_monitor()`

---

## 🐛 Testes de Robustez

### Teste 6: Fechamento Correto
**Objetivo**: Garantir limpeza adequada de recursos

**Passos:**
1. Com player aberto e vídeo tocando
2. Feche `main.py` clicando no **[X]**
3. Confirme fechamento na caixa de diálogo

**Resultado Esperado:**
- ✅ Confirmação aparece: "Deseja realmente sair?"
- ✅ Ao confirmar, `main.py` fecha
- ✅ `karaoke_player.py` também fecha automaticamente
- ✅ Nenhum processo órfão (verificar Task Manager)
- ✅ Arquivos temporários removidos

**Verificar Processos:**
```powershell
Get-Process | Where-Object { $_.ProcessName -like "*python*" }
```

---

### Teste 7: Reconexão após Erro
**Objetivo**: Testar resiliência da comunicação

**Passos:**
1. Inicie `main.py` (player externo inicia)
2. **Force o fechamento** do player externo (Task Manager)
3. No `main.py`, tente executar um comando (play/pause)

**Resultado Esperado:**
- ⚠️ Mensagem de erro aparece: "Player não conectado"
- ✅ `main.py` continua funcional
- ✅ Log registra: `❌ Erro ao enviar comando: [Broken pipe]`

**Solução Manual:**
- Reinicie `main.py` para reconectar

---

### Teste 8: Arquivo Inválido
**Objetivo**: Tratamento de erros de mídia

**Passos:**
1. Tente carregar arquivo não-vídeo (ex: `.txt`)
2. Ou arquivo corrompido

**Resultado Esperado:**
- ✅ Mensagem de erro clara
- ✅ Sistema não trava
- ✅ Logs registram exceção

---

## 📊 Verificação de Performance

### Teste 9: Uso de CPU/Memória
**Objetivo**: Garantir eficiência

**Passos:**
1. Abra Task Manager (Ctrl+Shift+Esc)
2. Inicie sistema com vídeo tocando
3. Observe uso de recursos

**Métricas Aceitáveis:**
| Componente | CPU | Memória |
|------------|-----|---------|
| main.py | < 5% | < 100 MB |
| karaoke_player.py | 10-30% | < 200 MB |
| **Total** | < 40% | < 300 MB |

**⚠️ Se exceder:**
- Verifique resolução do vídeo (4K consome mais)
- Teste com vídeo menor (720p)

---

## 🔍 Diagnóstico de Problemas

### Problema: Player não abre
**Soluções:**
1. Verificar se `karaoke_player.py` existe no mesmo diretório
2. Verificar logs: `Get-Content karaoke_debug.log -Tail 50`
3. Testar manualmente: `python karaoke_player.py`

### Problema: Vídeo não aparece
**Soluções:**
1. Verificar se VLC está instalado: `pip show python-vlc`
2. Testar codec: `ffprobe arquivo.mp4`
3. Verificar logs do player

### Problema: Socket recusa conexão
**Soluções:**
1. Verificar porta 5555 disponível: `netstat -an | Select-String 5555`
2. Desabilitar firewall temporariamente
3. Aguardar mais tempo na inicialização (aumentar `time.sleep(2)`)

### Problema: Segundo monitor não detectado
**Soluções:**
1. Verificar: `winfo_screenwidth()` nos logs
2. Ajustar manualmente geometria:
   ```python
   # Em karaoke_player.py → posicionar_segundo_monitor()
   screen_width = 1920  # Largura do monitor principal
   self.root.geometry(f"800x600+{screen_width}+0")
   ```

---

## ✅ Checklist de Validação Completa

### Funcionalidades Básicas
- [ ] Sistema inicia sem erros
- [ ] Player externo abre automaticamente
- [ ] Arquivo MP4 carrega com sucesso
- [ ] Play/Pause/Stop funcionam
- [ ] Ajuste de pitch funciona
- [ ] Timer exibe duração (mesmo que não atualize em tempo real)

### Multi-Monitor
- [ ] Player posiciona-se no segundo monitor (se disponível)
- [ ] Painel de controle fica no monitor principal

### Robustez
- [ ] Fechamento limpo (ambos processos encerram)
- [ ] Arquivos temporários são removidos
- [ ] Erros são tratados sem travar
- [ ] Logs registram todas as operações

### Performance
- [ ] Uso de CPU aceitável (< 40% total)
- [ ] Uso de memória aceitável (< 300 MB total)
- [ ] Vídeo reproduz sem engasgos

---

## 📞 Reportar Problemas

Se encontrar erros, forneça:
1. **Logs completos**: `karaoke_debug.log`
2. **Mensagens de erro**: Print do console
3. **Especificações**: Python version, FFmpeg version, SO
4. **Passos para reproduzir**: Descreva o que fez antes do erro

---

## 🎓 Testes Avançados (Opcional)

### Teste de Stress
```powershell
# Carregar vários vídeos em sequência sem fechar
# Verificar vazamento de memória no Task Manager
```

### Teste de Evento
1. Criar evento no banco de dados
2. Adicionar músicas à playlist
3. Executar playlist completa
4. Verificar pontuação salva

### Teste de Catálogo
1. Importar CSV com 1000+ músicas
2. Buscar músicas no catálogo
3. Verificar performance da busca

---

**✨ Boa sorte com os testes!**

Se tudo passar, o sistema está pronto para uso em produção! 🎤🎶
