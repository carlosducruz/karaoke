# 🎬 Arquitetura do Karaoke Player

## 📐 Visão Geral

O sistema agora está dividido em **dois componentes** que se comunicam:

```
┌─────────────────────────┐                                      ┌─────────────────────────┐
│                         │ ◄──────────────────────────────────► │                         │
│   main.py               │                                      │   karaoke_player.py     │
│   (Painel de Controle)  │         Comandos:                    │   (Player de Vídeo)     │
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
- ✅ **ENVIA comandos** para o player

**Funcionalidades Principais:**
- Interface completa com playlist visual

---

### 2️⃣ **karaoke_player.py** - Player de Vídeo (Segundo Monitor)

**Responsabilidades:**
- ✅ Reprodução de vídeo com VLC
- ✅ **RECEBE comandos** do painel
- ✅ Controle de tom (pitch shift)
- ✅ Controle de velocidade  
- ✅ Barra de progresso (seek com botões de retrocessos e avanços)
- ✅ Abertura de segunda tela com o player


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
   - ✅ Inicia o `karaoke_player.py` em processo vinculado
   - ✅ Aguarda comandos

3. **No painel de controle (`main.py`):**
   - Carregue músicas
   - Use a busca no catálogo
   - Gerencie a playlist
   - Controle a reprodução

4. **No segundo monitor:**
   - O vídeo aparecerá automaticamente
   - Modo fullscreen/minimizado
   - Sem controles visíveis (controlado remotamente)

---

## 📝 Logs

Ambos os componentes geram logs detalhados:

- **main.py**: `karaoke_debug.log` (diretório do script)
- **karaoke_player.py**: `karaoke_debug.log` (diretório do script)

**Eventos Registrados:**
- 📤 Comandos gerais (main.py e karaoke_player.py)
---


**Desenvolvido para Karaoke Player v1.0**
*Arquitetura Desktop*
