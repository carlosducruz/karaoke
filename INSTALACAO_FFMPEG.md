# 🎬 Instalação do FFmpeg para Karaoke Player

O **Karaoke Player** precisa do **FFmpeg** instalado para processar vídeos e áudio.

## ✅ Verificar se já está instalado

Abra o PowerShell ou CMD e digite:

```powershell
ffmpeg -version
ffprobe -version
```

Se aparecer a versão, **já está instalado!** ✓

---

## 📥 Como Instalar no Windows

### Opção 1: Usando Winget (Recomendado - Windows 10/11)

```powershell
winget install ffmpeg
```

### Opção 2: Usando Chocolatey

```powershell
choco install ffmpeg
```

### Opção 3: Download Manual

1. **Baixar FFmpeg:**
   - Acesse: https://www.gyan.dev/ffmpeg/builds/
   - Baixe: **ffmpeg-release-essentials.zip**

2. **Extrair:**
   - Extraia o arquivo ZIP
   - Exemplo: `C:\ffmpeg`

3. **Adicionar ao PATH:**

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
   - Feche e reabra o PowerShell/CMD
   - Digite: `ffmpeg -version`

---

## 🔧 Solução de Problemas

### Erro: "O sistema não pode encontrar o arquivo especificado"

✅ **Solução:**
1. Verifique se instalou corretamente (teste com `ffmpeg -version`)
2. Reinicie o computador após instalar
3. Se usou instalação manual, certifique-se que adicionou ao PATH
4. Reinicie o Karaoke Player

### FFmpeg instalado mas não funciona

✅ **Solução:**
1. Feche **TODOS** os terminais/PowerShell abertos
2. Reinicie o Karaoke Player
3. Se ainda não funcionar, reinicie o computador

---

## 📌 Notas Importantes

- Após instalar o FFmpeg, **reinicie o Karaoke Player**
- O programa verifica automaticamente se o FFmpeg está disponível
- Mensagens de erro mais claras foram adicionadas para facilitar o diagnóstico

---

## 🆘 Ainda com problemas?

Se mesmo após seguir todos os passos o erro persistir:

1. Tire uma captura de tela do erro
2. Verifique o arquivo `karaoke_debug.log` na pasta do programa
3. Entre em contato com o suporte

---

**Desenvolvido para Karaoke Player v1.0**
