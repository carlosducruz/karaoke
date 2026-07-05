import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from PIL import Image, ImageTk
import vlc
import threading
import time
import os
import subprocess
import tempfile
import json
from datetime import datetime
import sys
import signal
from karaoke_youtube_downloader import YouTubeDownloaderWindow

try:
    import sounddevice as sd
    import numpy as np
    AUDIO_DISPONIVEL = True
except ImportError:
    AUDIO_DISPONIVEL = False
    print("AVISO: sounddevice ou NumPy não encontrados. V.U. meter desabilitado.")

try:
    from karaoke_evento import ModoEventoWindow
    from karaoke_database import KaraokeDatabase
    MODO_EVENTO_DISPONIVEL = True
except ImportError:
    MODO_EVENTO_DISPONIVEL = False
    print("AVISO: Módulos de evento não encontrados. Modo Evento desabilitado.")

# Funções auxiliares para verificar disponibilidade de ferramentas
def verificar_ffmpeg_instalado():
    """Verifica se ffmpeg e ffprobe estão disponíveis no sistema"""
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      capture_output=True, 
                      check=True,
                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def verificar_ffprobe_instalado():
    """Verifica se ffprobe está disponível no sistema"""
    try:
        subprocess.run(['ffprobe', '-version'], 
                      capture_output=True, 
                      check=True,
                      creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def mostrar_erro_ffmpeg():
    """Mostra mensagem de erro sobre ffmpeg não encontrado"""
    mensagem = """❌ FFMPEG NÃO ENCONTRADO

O programa precisa do FFmpeg instalado para funcionar.

📥 COMO INSTALAR:

Windows:
1. Baixe: https://www.gyan.dev/ffmpeg/builds/
2. Extraia o arquivo ZIP
3. Adicione a pasta 'bin' ao PATH do sistema
   Ou copie ffmpeg.exe e ffprobe.exe para:
   C:\\Windows\\System32\\

Ou use Chocolatey:
   choco install ffmpeg

Ou use Winget:
   winget install ffmpeg

Após instalar, reinicie o programa."""
    
    messagebox.showerror("FFmpeg Não Encontrado", mensagem)

class KaraokePlayer:
    
    def abrir_busca_catalogo(self):
        """Abre uma janela para buscar músicas/cantores/códigos no catálogo importado."""
        busca_win = tk.Toplevel(self.root)
        busca_win.title("Buscar no Catálogo")
        busca_win.geometry("800x500")
        busca_win.configure(bg="#222")

        # ... código anterior do método ...

        # Função quando clica em uma linha
        def on_double_click(event):
            selection = tree.selection()
            if not selection:
                return
                
            item = tree.item(selection[0])
            valores = item['values']
            codigo = str(valores[1])  # Código está na segunda coluna
            cantor = valores[0]
            musica = valores[2]
            
            # Buscar arquivo MP4
            arquivo_encontrado = self.buscar_arquivo_mp4(codigo)
            
            if arquivo_encontrado:
                # Se modo evento está ativo, adiciona à playlist com seleção de participante
                if self.modo_evento_ativo and MODO_EVENTO_DISPONIVEL:
                    if messagebox.askyesno(
                        "Adicionar à Playlist",
                        f"🎤 Cantor: {cantor}\n🎵 Música: {musica}\n🔢 Código: {codigo}\n\n"
                        f"📁 Arquivo: {os.path.basename(arquivo_encontrado)}\n\n"
                        "Deseja adicionar esta música à playlist do evento?"
                    ):
                        self.adicionar_musica_evento(arquivo_encontrado, cantor, musica, codigo)
                        busca_win.destroy()
                else:
                    # Modo normal: pergunta se deseja adicionar à playlist
                    resposta = messagebox.askyesno(
                        "Música Encontrada",
                        f"🎤 Cantor: {cantor}\n🎵 Música: {musica}\n🔢 Código: {codigo}\n\n"
                        f"📁 Arquivo: {os.path.basename(arquivo_encontrado)}\n\n"
                        "Deseja adicionar à playlist?"
                    )
                    
                    if resposta:
                        # Adiciona à playlist simples (sem evento)
                        self.adicionar_musica_playlist_simples(arquivo_encontrado, cantor, musica, codigo)
                        busca_win.destroy()
            else:
                messagebox.showerror(
                    "Arquivo Não Encontrado",
                    f"❌ Arquivo não encontrado!\n\n"
                    f"🎤 Cantor: {cantor}\n"
                    f"🎵 Música: {musica}\n"
                    f"🔢 Código: {codigo}\n\n"
                    f"📁 Procurando por: '{codigo}.mp4'\n"
                    f"📂 Pasta: {self.music_folder}\n\n"
                    "Verifique se o arquivo existe na pasta de músicas.",
                    parent=busca_win
                )

    def __init__(self, root):
        self.root = root
        self.root.title("Karaoke Player - MP4")
        self.root.geometry("1200x780")
        self.root.configure(bg="#1a1a1a")
        self.force_quit = False  # Adicione esta flag
        self.music_folder = r"D:/"

        # LOG INICIAL
        self.debug_log("=" * 60)
        self.debug_log("KARAOKE PLAYER INICIADO")
        self.debug_log(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.debug_log("=" * 60)
        
        # VERIFICAR SE FFMPEG ESTÁ INSTALADO
        if not verificar_ffprobe_instalado():
            self.debug_log("❌ ERRO: FFprobe não encontrado!")
            mostrar_erro_ffmpeg()
            self.root.destroy()
            return
        
        if not verificar_ffmpeg_instalado():
            self.debug_log("❌ ERRO: FFmpeg não encontrado!")
            mostrar_erro_ffmpeg()
            self.root.destroy()
            return
        
        self.debug_log("✓ FFmpeg e FFprobe encontrados")
        
        self.video_file = None
        self.processed_file = None
        self.pitch_shift = 0
        self.playback_speed = 1.0  # Velocidade de reprodução (1.0 = normal)
        self.is_playing = False
        self.duration = 0
        self.fps = 30
        self.width = 0
        self.height = 0
        self.processing_pitch = False
        
        # VLC instances
        self.vlc_instance = vlc.Instance('--no-xlib', '--no-video-title-show')
        self.player = self.vlc_instance.media_player_new()
        
        # Janela secundária para vídeo (segundo monitor)
        self.video_window = None
        self.video_frame_secondary = None
        
        # Modo Evento
        self.modo_evento_ativo = False
        self.evento_id_atual = None
        self.musica_atual_evento = None
        self.playlist_items = []
        self.selected_playlist_index = None
        
        # Sistema de áudio para V.U. meter e pontuação
        self.audio_stream = None
        self.audio_interface = None
        self.vu_running = False
        self.vu_level = 0
        self.samples_microfone = []  # Amostras do microfone para pontuação
        self.pontuacao_final = 0
        self.tempo_inicio_musica = 0  # Tempo de início para sincronização
        self.inicializar_audio()
        
        self.setup_ui()
        self.criar_janela_video_secundaria()
        self.update_timer()
    

 


        
    def criar_janela_video_secundaria(self):
        """Cria janela secundária para exibir vídeo (arrastável para segundo monitor)"""
        try:
            self.video_window = tk.Toplevel(self.root)
            self.video_window.title("Karaoke Player - Vídeo")
            self.video_window.configure(bg="black")
            
            # Cria janela em tamanho fixo que pode ser arrastada
            width = 800
            height = 600
            
            # Tenta posicionar próximo ao segundo monitor
            screen_width = self.root.winfo_screenwidth()
            x = screen_width - width - 50  # Posiciona na borda direita
            y = 50
            
            self.video_window.geometry(f"{width}x{height}+{x}+{y}")
            self.debug_log(f"📺 Janela de vídeo criada: {width}x{height}+{x}+{y}")
            
            # Frame para o vídeo VLC
            self.video_frame_secondary = tk.Frame(self.video_window, bg="black")
            self.video_frame_secondary.pack(fill=tk.BOTH, expand=True)
            
            # Protocolo de fechamento
            self.video_window.protocol("WM_DELETE_WINDOW", lambda: None)  # Ignora fechar pela janela
            
            # Adiciona texto de instrução
            label = tk.Label(
                self.video_frame_secondary,
                text="🎤 Aguardando vídeo...\n\nCarregue um arquivo MP4 no painel de controle\n\n💡 Arraste esta janela para o segundo monitor",
                font=("Arial", 16),
                bg="black",
                fg="white"
            )
            label.place(relx=0.5, rely=0.5, anchor="center")
            
            self.debug_log("✅ Janela secundária de vídeo criada")
            
        except Exception as e:
            self.debug_log(f"⚠️ Erro ao criar janela secundária: {e}")
            self.video_window = None
    
    def fechar_aplicacao(self, confirmar=True):
        """Fecha a aplicação com opção de confirmação e limpeza de recursos"""
        
        # Verificar se já está fechando
        if self.force_quit:
            self.debug_log("⚠️ Fechamento já em andamento, ignorando...")
            return
        
        # Confirmar com o usuário (se solicitado)
        if confirmar:
            from tkinter import messagebox
            resposta = messagebox.askyesno(
                "Fechar Karaoke Player",
                "Deseja realmente fechar o Karaoke Player?\n\n" +
                "✓ Reprodução será interrompida\n" +
                "✓ Arquivos temporários serão removidos\n" +
                "✓ Modo evento será salvo (se ativo)"
            )
            if not resposta:
                self.debug_log("ℹ️ Usuário cancelou o fechamento")
                return
        
        # Marcar como fechando
        self.force_quit = True
        self.debug_log("=" * 60)
        self.debug_log("🛑 FECHANDO KARAOKE PLAYER...")
        self.debug_log(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Mostrar status na interface
        try:
            self.status_label.config(text="🛑 Finalizando aplicação...", fg="#FF9800")
            self.root.update()
        except:
            pass
        
        # Sinalizar para threads pararem
        self.is_playing = False
        self.progress_animation_running = False
        
        # Parar player VLC
        if hasattr(self, 'player') and self.player:
            try:
                self.debug_log("⏹️ Parando player VLC...")
                self.player.stop()
                self.debug_log("✅ Player VLC parado")
            except Exception as e:
                self.debug_log(f"⚠️ Erro ao parar VLC: {e}")
        
        # Fechar janela secundária de vídeo
        if hasattr(self, 'video_window') and self.video_window:
            try:
                self.debug_log("🖼️ Fechando janela de vídeo...")
                self.video_window.destroy()
                self.debug_log("✅ Janela de vídeo fechada")
            except Exception as e:
                self.debug_log(f"⚠️ Erro ao fechar janela de vídeo: {e}")
        
        # Se estiver em modo evento, tentar salvar estado
        if hasattr(self, 'modo_evento_ativo') and self.modo_evento_ativo:
            self.debug_log("💾 Modo evento ativo - salvando estado...")
            try:
                if MODO_EVENTO_DISPONIVEL:
                    from karaoke_database import KaraokeDatabase
                    db = KaraokeDatabase()
                    # Marcar música atual como pausada
                    if self.musica_atual_evento:
                        tempo = self.player.get_time() / 1000.0 if self.player else 0
                        db.marcar_musica_pausada(self.musica_atual_evento['id'], tempo)
                    db.fechar_conexao()
                    self.debug_log("✅ Estado do evento salvo")
            except Exception as e:
                self.debug_log(f"⚠️ Erro ao salvar estado do evento: {e}")
        
        # Parar player VLC
        if hasattr(self, 'player') and self.player:
            try:
                self.debug_log("⏹️ Parando player VLC...")
                self.player.stop()
                self.debug_log("✅ Player VLC parado")
            except Exception as e:
                self.debug_log(f"⚠️ Erro ao parar VLC: {e}")
        
        # Parar qualquer processamento de pitch em andamento
        if hasattr(self, 'processing_pitch') and self.processing_pitch:
            self.debug_log("⚠️ Interrompendo processamento de pitch...")
            self.processing_pitch = False
        
        # Limpar arquivos temporários
        if hasattr(self, 'processed_file') and self.processed_file:
            if self.processed_file != getattr(self, 'video_file', None):
                try:
                    if os.path.exists(self.processed_file):
                        self.debug_log(f"🗑️ Removendo arquivo temporário: {self.processed_file}")
                        os.unlink(self.processed_file)
                        self.debug_log("✅ Arquivo temporário removido")
                except Exception as e:
                    self.debug_log(f"⚠️ Erro ao remover arquivo: {e}")
        
        # Fechar todas as janelas filhas (Toplevel)
        try:
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel):
                    try:
                        widget.destroy()
                    except:
                        pass
            self.debug_log("✅ Janelas filhas fechadas")
        except:
            pass
        
        # Parar V.U. meter e limpar recursos de áudio
        if hasattr(self, 'vu_running') and self.vu_running:
            try:
                self.parar_vu_meter()
                self.debug_log("✅ V.U. meter finalizado")
            except:
                pass
        
        if hasattr(self, 'audio_interface') and self.audio_interface:
            try:
                self.audio_interface.terminate()
                self.debug_log("✅ Interface de áudio finalizada")
            except:
                pass
        
        self.debug_log("=" * 60)
        self.debug_log("✅ KARAOKE PLAYER FINALIZADO COM SUCESSO")
        self.debug_log("=" * 60)
        
        # Destruir janela principal
        try:
            self.root.quit()
        except:
            pass
        
        try:
            self.root.destroy()
        except:
            pass
        
        # Forçar saída se necessário (último recurso)
        import os
        os._exit(0)

 
    def abrir_busca_catalogo(self):
        """Abre uma janela para buscar músicas/cantores/códigos no catálogo importado."""
        busca_win = tk.Toplevel(self.root)
        busca_win.title("Buscar no Catálogo")
        busca_win.geometry("800x500")
        busca_win.configure(bg="#222")

        # Consulta quantidade de músicas no catálogo
        try:
            db = KaraokeDatabase()
            total_musicas = len(db.buscar_catalogo())
        except Exception:
            total_musicas = 0

        header_text = f"Buscar no Catálogo  (Músicas disponíveis: {total_musicas})"
        tk.Label(busca_win, text=header_text, font=("Arial", 16, "bold"), bg="#222", fg="white").pack(pady=10)

        # Frame de busca
        search_frame = tk.Frame(busca_win, bg="#222")
        search_frame.pack(pady=5)
        
        tk.Label(search_frame, text="Termo:", bg="#222", fg="white", font=("Arial", 11)).pack(side=tk.LEFT)
        termo_var = tk.StringVar()
        termo_entry = tk.Entry(search_frame, textvariable=termo_var, font=("Arial", 12), width=30)
        termo_entry.pack(side=tk.LEFT, padx=8)

        # Botão buscar
        tk.Button(
            search_frame, 
            text="Buscar", 
            command=lambda: buscar(),
            bg="#2196F3", 
            fg="white", 
            font=("Arial", 10, "bold"), 
            padx=10, 
            pady=4
        ).pack(side=tk.LEFT, padx=8)

        # Frame de resultados
        result_frame = tk.Frame(busca_win, bg="#222")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Treeview
        columns = ("Código", "Cantor", "Música", "Início")
        tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=15)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100 if col == "Código" else 150)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(result_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Frame para botões
        btn_frame = tk.Frame(busca_win, bg="#222", pady=10)
        btn_frame.pack(fill=tk.X)

        # Função de busca
        def buscar():
            termo = termo_var.get().strip()
            db = KaraokeDatabase()
            try:
                resultados = db.buscar_catalogo(termo) if termo else db.buscar_catalogo()
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao buscar catálogo:\n{e}")
                return
            
            tree.delete(*tree.get_children())
            for row in resultados:
                tree.insert("", tk.END, values=row)

            # Função quando clica em uma linha
        def on_double_click(event):
            selection = tree.selection()
            if not selection:
                return
                
            item = tree.item(selection[0])
            valores = item['values']
            codigo = str(valores[1])  # Código está na segunda coluna
            cantor = valores[0]
            musica = valores[2]
            
            # Buscar arquivo MP4
            arquivo_encontrado = self.buscar_arquivo_mp4(codigo)
            
            if arquivo_encontrado:
                # Diálogo único com formulário completo
                nome_dialog = tk.Toplevel(busca_win)
                nome_dialog.title("Adicionar à Playlist")
                nome_dialog.geometry("450x280")
                nome_dialog.configure(bg="#222")
                nome_dialog.transient(busca_win)
                nome_dialog.grab_set()
                
                # Centralizar na tela
                nome_dialog.update_idletasks()
                x = (nome_dialog.winfo_screenwidth() // 2) - (450 // 2)
                y = (nome_dialog.winfo_screenheight() // 2) - (280 // 2)
                nome_dialog.geometry(f"450x280+{x}+{y}")
                
                # Título
                tk.Label(
                    nome_dialog,
                    text="🎵 Adicionar Música à Playlist",
                    bg="#222",
                    fg="#4CAF50",
                    font=("Arial", 14, "bold")
                ).pack(pady=(15, 10))
                
                # Frame de informações da música
                info_frame = tk.Frame(nome_dialog, bg="#333", relief=tk.RIDGE, bd=2)
                info_frame.pack(fill=tk.X, padx=20, pady=5)
                
                tk.Label(
                    info_frame,
                    text=f"🎤 Cantor: {cantor}",
                    bg="#333",
                    fg="white",
                    font=("Arial", 10),
                    anchor=tk.W
                ).pack(fill=tk.X, padx=10, pady=2)
                
                tk.Label(
                    info_frame,
                    text=f"🎵 Música: {musica}",
                    bg="#333",
                    fg="white",
                    font=("Arial", 10),
                    anchor=tk.W
                ).pack(fill=tk.X, padx=10, pady=2)
                
                tk.Label(
                    info_frame,
                    text=f"🔢 Código: {codigo}",
                    bg="#333",
                    fg="white",
                    font=("Arial", 10),
                    anchor=tk.W
                ).pack(fill=tk.X, padx=10, pady=2)
                
                # Campo de nome do participante
                tk.Label(
                    nome_dialog,
                    text="Nome do Participante (opcional):",
                    bg="#222",
                    fg="#BBB",
                    font=("Arial", 10, "italic")
                ).pack(pady=(15, 5))
                
                nome_var = tk.StringVar(value=cantor)
                nome_entry = tk.Entry(
                    nome_dialog,
                    textvariable=nome_var,
                    font=("Arial", 12),
                    width=35
                )
                nome_entry.pack(pady=5)
                nome_entry.focus_set()
                nome_entry.select_range(0, tk.END)
                
                def confirmar():
                    nome = nome_var.get().strip()
                    if not nome:
                        nome = cantor  # Usa o nome do cantor se vazio
                    
                    # Carrega o arquivo
                    self.video_file = arquivo_encontrado
                    self.processed_file = arquivo_encontrado
                    self.pitch_shift = 0
                    self.pitch_label.config(text="0")
                    self.file_label.config(text=f"{codigo} - {musica}")
                    self.show_first_frame()
                    self.status_label.config(text=f"✅ Música carregada: {musica}")
                    
                    # Adiciona à playlist do modo normal
                    if not self.modo_evento_ativo:
                        self.playlist_items.append({
                            'arquivo_path': arquivo_encontrado,
                            'participante_nome': nome,
                            'musica_nome': musica,
                            'tom_ajuste': 0,
                            'ja_tocou': False,
                            'ordem': len(self.playlist_items) + 1
                        })
                        self.atualizar_playlist_visual()
                    
                    nome_dialog.destroy()
                    busca_win.destroy()
                
                def cancelar():
                    nome_dialog.destroy()
                
                # Botões
                btn_frame = tk.Frame(nome_dialog, bg="#222")
                btn_frame.pack(pady=15)
                
                tk.Button(
                    btn_frame,
                    text="✓ Adicionar à Playlist",
                    command=confirmar,
                    bg="#4CAF50",
                    fg="white",
                    font=("Arial", 10, "bold"),
                    cursor="hand2",
                    width=18,
                    height=2
                ).pack(side=tk.LEFT, padx=5)
                
                tk.Button(
                    btn_frame,
                    text="✗ Cancelar",
                    command=cancelar,
                    bg="#f44336",
                    fg="white",
                    font=("Arial", 10, "bold"),
                    cursor="hand2",
                    width=12,
                    height=2
                ).pack(side=tk.LEFT, padx=5)
                
                nome_entry.bind("<Return>", lambda e: confirmar())
                nome_dialog.bind("<Escape>", lambda e: cancelar())
                    
            else:
                messagebox.showerror(
                    "Arquivo Não Encontrado",
                    f"❌ Arquivo não encontrado!\n\n"
                    f"🎤 Cantor: {cantor}\n"
                    f"🎵 Música: {musica}\n"
                    f"🔢 Código: {codigo}\n\n"
                    f"📁 Procurando por: '{codigo}.mp4'\n"
                    f"📂 Pasta: {self.music_folder}\n\n"
                    "Verifique se o arquivo existe na pasta de músicas.",
                    parent=busca_win
                )

        # Botão para carregar música selecionada
        tk.Button(
            btn_frame,
            text="🎵 Carregar Música Selecionada",
            command=lambda: on_double_click(None),
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=15,
            pady=8,
            cursor="hand2"
        ).pack(pady=5)

        # Botão Fechar
        tk.Button(
            btn_frame,
            text="Fechar",
            command=busca_win.destroy,
            bg="#666666",
            fg="white",
            font=("Arial", 10),
            padx=15,
            pady=5
        ).pack(pady=5)

        # Configurações
        tree.bind("<Double-1>", on_double_click)  # Duplo clique na linha
        termo_entry.bind("<Return>", lambda e: buscar())
        busca_win.bind("<Escape>", lambda e: busca_win.destroy())

        # Busca inicial
        buscar()
            
    def buscar_arquivo_mp4(self, codigo):
        """Busca arquivo MP4 na pasta de músicas selecionada e subpastas"""
        base_path = self.music_folder
        
        # Converte para string e completa com zeros à esquerda até ter 5 dígitos
        codigo_str = str(codigo).strip()
        
        # Se for numérico, completa com zeros
        if codigo_str.isdigit():
            codigo_formatado = codigo_str.zfill(5)
        else:
            codigo_formatado = codigo_str
        
        arquivo_nome = f"{codigo_formatado}.mp4"
        
        if not os.path.exists(base_path):
            messagebox.showwarning(
                "Pasta não encontrada",
                f"A pasta {base_path} não foi encontrada.\nVerifique se ela existe."
            )
            return None
            
        # Procura recursivamente
        for root, dirs, files in os.walk(base_path):
            for file in files:
                # Compara tanto o nome formatado quanto o original
                if file.lower() == arquivo_nome.lower() or \
                (codigo_str != codigo_formatado and file.lower() == f"{codigo_str}.mp4".lower()):
                    return os.path.join(root, file)
        
        return None

    def setup_ui(self):
        self.debug_log("Configurando interface...")

        # Menu horizontal superior (toolbar) - ocupa toda a largura da janela
        toolbar_outer = tk.Frame(self.root, bg="#23233a", bd=2, relief=tk.RIDGE, highlightbackground="#2196F3", highlightcolor="#2196F3", highlightthickness=1)
        toolbar_outer.pack(side=tk.TOP, fill=tk.X)

        toolbar_frame = tk.Frame(toolbar_outer, bg="#23233a")
        toolbar_frame.pack(fill=tk.X, padx=8, pady=6)

        tb_btn_width = 16
        tb_btn_height = 1
        tb_btn_padx = 4
        tb_btn_pady = 2

        tk.Button(
            toolbar_frame,
            text="🔎 Buscar no Catálogo",
            command=self.abrir_busca_catalogo,
            bg="#2196F3",
            fg="white",
            font=("Arial", 9, "bold"),
            cursor="hand2",
            width=tb_btn_width,
            height=tb_btn_height
        ).pack(side=tk.LEFT, padx=tb_btn_padx, pady=tb_btn_pady)

        tk.Button(
            toolbar_frame,
            text="📁 Tocar MP4 (Fura fila)",
            command=self.load_file,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 9, "bold"),
            cursor="hand2",
            width=tb_btn_width,
            height=tb_btn_height
        ).pack(side=tk.LEFT, padx=tb_btn_padx, pady=tb_btn_pady)

        tk.Button(
            toolbar_frame,
            text="📚 Importar Catálogo",
            command=self.carregar_catalogo,
            bg="#FF9800",
            fg="white",
            font=("Arial", 9, "bold"),
            cursor="hand2",
            width=tb_btn_width,
            height=tb_btn_height
        ).pack(side=tk.LEFT, padx=tb_btn_padx, pady=tb_btn_pady)

        if MODO_EVENTO_DISPONIVEL:
            tk.Button(
                toolbar_frame,
                text="🎉 MODO EVENTO",
                command=self.abrir_modo_evento,
                bg="#9C27B0",
                fg="white",
                font=("Arial", 9, "bold"),
                cursor="hand2",
                width=tb_btn_width,
                height=tb_btn_height
            ).pack(side=tk.LEFT, padx=tb_btn_padx, pady=tb_btn_pady)

        tk.Button(
            toolbar_frame,
            text="❌ Finalizar Evento",
            command=self.finalizar_evento_e_limpar_playlist,
            bg="#f44336",
            fg="white",
            font=("Arial", 9, "bold"),
            cursor="hand2",
            width=tb_btn_width,
            height=tb_btn_height
        ).pack(side=tk.LEFT, padx=tb_btn_padx, pady=tb_btn_pady)

        if MODO_EVENTO_DISPONIVEL:
            tk.Button(
                toolbar_frame,
                text="📋 Gerenciar Eventos",
                command=self.abrir_gerenciar_eventos,
                bg="#607D8B",
                fg="white",
                font=("Arial", 9, "bold"),
                cursor="hand2",
                width=tb_btn_width,
                height=tb_btn_height
            ).pack(side=tk.LEFT, padx=tb_btn_padx, pady=tb_btn_pady)

            tk.Button(
                toolbar_frame,
                text="📥 Baixar do YouTube",
                command=self.abrir_youtube_downloader,
                bg="#E91E63",
                fg="white",
                font=("Arial", 9, "bold"),
                cursor="hand2",
                width=tb_btn_width,
                height=tb_btn_height
            ).pack(side=tk.LEFT, padx=tb_btn_padx, pady=tb_btn_pady)

        # Container principal
        main_container = tk.Frame(self.root, bg="#1a1a1a")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # COLUNA ESQUERDA (70%)
        left_frame = tk.Frame(main_container, bg="#1a1a1a")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Vídeo (menor)
        video_frame = tk.Frame(left_frame, bg="#000000", width=380, height=170)
        video_frame.pack(padx=5, pady=5)
        video_frame.pack_propagate(False)

        self.video_label = tk.Label(
            video_frame, 
            bg="#000000", 
            text="🎬 Carregue um vídeo MP4", 
            fg="#666666", 
            font=("Arial", 12)
        )
        self.video_label.pack(expand=True)
        
        # Info
        info_frame = tk.Frame(left_frame, bg="#2d2d2d", pady=5)
        info_frame.pack(fill=tk.X, padx=5)
        
        self.file_label = tk.Label(
            info_frame, 
            text="Nenhum arquivo carregado", 
            bg="#2d2d2d", 
            fg="white",
            font=("Arial", 9)
        )
        self.file_label.pack()
        
        self.time_label = tk.Label(
            info_frame,
            text="00:00 / 00:00",
            bg="#2d2d2d",
            fg="#4CAF50",
            font=("Arial", 8, "bold")
        )
        self.time_label.pack()

        # Seletor de pasta de músicas e progresso na mesma linha
        pasta_progress_frame = tk.Frame(left_frame, bg="#1a1a1a")
        pasta_progress_frame.pack(fill=tk.X, padx=5, pady=(0, 8))
        
        # Lado esquerdo: Pasta de músicas
        pasta_frame = tk.Frame(pasta_progress_frame, bg="#1a1a1a")
        pasta_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        tk.Label(
            pasta_frame,
            text="Pasta de músicas:",
            bg="#1a1a1a",
            fg="#BBB",
            font=("Arial", 9, "italic")
        ).pack(side=tk.LEFT)
        self.music_folder_var = tk.StringVar(value=self.music_folder)
        pasta_entry = tk.Entry(pasta_frame, textvariable=self.music_folder_var, font=("Arial", 9), width=30, state="readonly", readonlybackground="#222", fg="#4CAF50")
        pasta_entry.pack(side=tk.LEFT, padx=6)
        tk.Button(
            pasta_frame,
            text="Selecionar Pasta",
            command=self.selecionar_pasta_musicas,
            bg="#2196F3",
            fg="white",
            font=("Arial", 9, "bold"),
            cursor="hand2",
            padx=8,
            pady=2
        ).pack(side=tk.LEFT)

        # Lado direito: Progresso (compacto)
        self.progress_frame = tk.Frame(pasta_progress_frame, bg="#232323", bd=1, relief=tk.SUNKEN, width=260)
        self.progress_frame.pack(side=tk.RIGHT, padx=(10, 0))
        self.progress_frame.pack_propagate(False)

        progress_inner = tk.Frame(self.progress_frame, bg="#232323")
        progress_inner.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        self.progress_label = tk.Label(
            progress_inner,
            text="",
            bg="#232323",
            fg="#00e676",
            font=("Arial", 8, "bold")
        )
        self.progress_label.pack()

        self.progress_canvas = tk.Canvas(
            progress_inner,
            width=250,
            height=15,
            bg="#333",
            highlightthickness=0
        )
        self.progress_canvas.pack()
        self.progress_bar = self.progress_canvas.create_rectangle(
            0, 0, 0, 15, fill="#00e676", width=0
        )
        self.progress_animation_running = False
        



        # Frame horizontal para pitch e controles de reprodução
        pitch_player_row = tk.Frame(left_frame, bg="#1a1a1a")
        pitch_player_row.pack(pady=(8, 16), fill=tk.X)

        # Altura e largura mínimas para controles de pitch e player
        control_height = 180  # altura aumentada para caber slider e botões de navegação
        pitch_width = int(410 * 1.1)   # 10% maior para acomodar duas colunas
        player_width = int(410 * 1.2)  # 20% maior

        # Pitch controls (à esquerda, personalizado)
        pitch_frame = tk.Frame(
            pitch_player_row,
            bg="#181828",
            bd=3,
            relief=tk.RIDGE,
            height=control_height,
            width=pitch_width,
            highlightbackground="#2196F3",
            highlightcolor="#2196F3",
            highlightthickness=2
        )
        pitch_frame.pack(side=tk.LEFT, padx=(0, 16), pady=2)
        pitch_frame.pack_propagate(False)

        # Espaçamento interno - Layout de duas colunas
        pitch_inner = tk.Frame(pitch_frame, bg="#181828")
        pitch_inner.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # COLUNA ESQUERDA: Controle de Tom
        left_column = tk.Frame(pitch_inner, bg="#181828")
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        tk.Label(
            left_column,
            text="Controle de Tom",
            bg="#181828",
            fg="#4CAF50",
            font=("Arial", 11, "bold")
        ).pack(anchor=tk.W)
        
        tk.Label(
            left_column,
            text="Ajuste em semitons",
            bg="#181828",
            fg="#BBB",
            font=("Arial", 8, "italic")
        ).pack(anchor=tk.W, pady=(0, 6))

        pitch_ctrl_frame = tk.Frame(left_column, bg="#181828")
        pitch_ctrl_frame.pack(pady=2, fill=tk.X)

        tk.Label(
            pitch_ctrl_frame,
            text="Semitons:",
            bg="#181828",
            fg="white",
            font=("Arial", 9, "bold")
        ).pack(side=tk.LEFT, padx=(0, 4))

        self.pitch_var = tk.IntVar(value=0)
        pitch_spin = tk.Spinbox(
            pitch_ctrl_frame,
            from_=-12,
            to=12,
            textvariable=self.pitch_var,
            width=3,
            font=("Arial", 14, "bold"),
            justify="center",
            bg="#222",
            fg="#4CAF50",
            insertbackground="#4CAF50",
            relief=tk.FLAT
        )
        pitch_spin.pack(side=tk.LEFT, padx=2)

        def aplicar_tom():
            novo_tom = self.pitch_var.get()
            if novo_tom != self.pitch_shift:
                self.change_pitch(novo_tom - self.pitch_shift)

        tk.Button(
            pitch_ctrl_frame,
            text="OK",
            command=aplicar_tom,
            bg="#2196F3",
            fg="white",
            font=("Arial", 9, "bold"),
            width=5,
            cursor="hand2",
            relief=tk.RAISED,
            activebackground="#1976D2"
        ).pack(side=tk.LEFT, padx=4)

        # Valor do tom destacado
        self.pitch_label = tk.Label(
            left_column,
            text="Tom: 0",
            bg="#222",
            fg="#00e676",
            font=("Arial", 12, "bold"),
            relief=tk.SUNKEN,
            bd=2,
            padx=8,
            pady=6
        )
        self.pitch_label.pack(pady=(8, 0), fill=tk.X)

        # COLUNA DIREITA: Controle de Velocidade
        right_column = tk.Frame(pitch_inner, bg="#181828")
        right_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        tk.Label(
            right_column,
            text="Velocidade",
            bg="#181828",
            fg="#4CAF50",
            font=("Arial", 11, "bold")
        ).pack(anchor=tk.W)
        
        tk.Label(
            right_column,
            text="Ajuste a velocidade",
            bg="#181828",
            fg="#BBB",
            font=("Arial", 8, "italic")
        ).pack(anchor=tk.W, pady=(0, 6))

        # Botões de velocidade em grid 2x2
        speed_grid = tk.Frame(right_column, bg="#181828")
        speed_grid.pack(pady=2)

        speed_btn_style = {
            "font": ("Arial", 9, "bold"),
            "cursor": "hand2",
            "width": 7,
            "height": 1,
            "bd": 1,
            "relief": tk.RAISED,
            "activebackground": "#1976D2"
        }

        # Linha 1
        speed_row1 = tk.Frame(speed_grid, bg="#181828")
        speed_row1.pack(pady=2)
        
        tk.Button(
            speed_row1,
            text="0.9x",
            command=lambda: self.change_speed(0.9),
            bg="#FF5722",
            fg="white",
            **speed_btn_style
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            speed_row1,
            text="1.0x",
            command=lambda: self.change_speed(1.0),
            bg="#4CAF50",
            fg="white",
            **speed_btn_style
        ).pack(side=tk.LEFT, padx=2)

        # Linha 2
        speed_row2 = tk.Frame(speed_grid, bg="#181828")
        speed_row2.pack(pady=2)
        
        tk.Button(
            speed_row2,
            text="1.05x",
            command=lambda: self.change_speed(1.05),
            bg="#2196F3",
            fg="white",
            **speed_btn_style
        ).pack(side=tk.LEFT, padx=2)

        tk.Button(
            speed_row2,
            text="1.10x",
            command=lambda: self.change_speed(1.10),
            bg="#9C27B0",
            fg="white",
            **speed_btn_style
        ).pack(side=tk.LEFT, padx=2)

        # Label mostrando velocidade atual
        self.speed_label = tk.Label(
            right_column,
            text="Velocidade: 1.0x",
            bg="#222",
            fg="#00e676",
            font=("Arial", 10, "bold"),
            relief=tk.SUNKEN,
            bd=2,
            padx=8,
            pady=6
        )
        self.speed_label.pack(pady=(8, 0), fill=tk.X)


        # Controles de reprodução (à direita do pitch, estilizado)
        player_frame = tk.Frame(
            pitch_player_row,
            bg="#181828",
            bd=3,
            relief=tk.RIDGE,
            height=control_height,
            width=player_width,
            highlightbackground="#2196F3",
            highlightcolor="#2196F3",
            highlightthickness=2
        )
        player_frame.pack(side=tk.LEFT, padx=(0, 16), pady=2)
        player_frame.pack_propagate(False)

        # Espaçamento interno - Layout vertical
        player_inner = tk.Frame(player_frame, bg="#181828")
        player_inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # Título e dica
        tk.Label(
            player_inner,
            text="Controle da Reprodução",
            bg="#181828",
            fg="#4CAF50",
            font=("Arial", 12, "bold")
        ).pack(anchor=tk.W)
        tk.Label(
            player_inner,
            text="O Botão próxima é apenas avançar para a próxima música na playlist.",
            bg="#181828",
            fg="#BBB",
            font=("Arial", 9, "italic")
        ).pack(anchor=tk.W, pady=(0, 6))

        # Frame para botões de reprodução
        btn_frame = tk.Frame(player_inner, bg="#181828")
        btn_frame.pack(fill=tk.X, pady=(0, 8))

        btn_style = {
            "font": ("Arial", 11, "bold"),
            "cursor": "hand2",
            "width": 10,
            "height": 2,
            "bd": 2,
            "relief": tk.RAISED,
            "activebackground": "#1976D2"
        }

        self.play_btn = tk.Button(
            btn_frame,
            text="▶ PLAY",
            command=self.play,
            bg="#4CAF50",
            fg="white",
            **btn_style
        )
        self.play_btn.pack(side=tk.LEFT, padx=5)

        self.pause_btn = tk.Button(
            btn_frame,
            text="⏸ PAUSA",
            command=self.pause,
            bg="#FF9800",
            fg="white",
            **btn_style
        )
        self.pause_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(
            btn_frame,
            text="⏹ PARAR",
            command=self.stop,
            bg="#f44336",
            fg="white",
            **btn_style
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Botão Próxima
        btn_proxima_style = btn_style.copy()
        btn_proxima_style["width"] = 13
        tk.Button(
            btn_frame,
            text="⏭ PRÓXIMA",
            command=self.tocar_proxima_musica,
            bg="#673AB7",
            fg="white",
            **btn_proxima_style
        ).pack(side=tk.LEFT, padx=5)

        # Frame para slider e botões de navegação
        nav_frame = tk.Frame(player_inner, bg="#181828")
        nav_frame.pack(fill=tk.X, pady=(8, 0))

        # Slider horizontal
        self.seek_slider = tk.Scale(
            nav_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            length=400,
            width=15,
            bg="#333",
            fg="#4CAF50",
            troughcolor="#222",
            highlightthickness=0,
            showvalue=False,
            command=lambda v: self.on_slider_change(v)
        )
        self.seek_slider.pack(fill=tk.X, padx=5, pady=(0, 5))
        
        # Flags para controle do slider
        self.is_seeking = False
        
        # Bind events para detectar quando usuário está arrastando
        self.seek_slider.bind("<ButtonPress-1>", lambda e: self.on_slider_press())
        self.seek_slider.bind("<ButtonRelease-1>", lambda e: self.on_slider_release())

        # Botões de navegação (horizontal)
        nav_btn_frame = tk.Frame(nav_frame, bg="#181828")
        nav_btn_frame.pack()

        nav_btn_style = {
            "font": ("Arial", 9, "bold"),
            "cursor": "hand2",
            "width": 6,
            "height": 1,
            "bd": 1,
            "bg": "#444",
            "fg": "white",
            "activebackground": "#555"
        }

        tk.Button(nav_btn_frame, text="⏮ -10s", command=lambda: self.seek_relative(-10), **nav_btn_style).pack(side=tk.LEFT, padx=3)
        tk.Button(nav_btn_frame, text="◀ -5s", command=lambda: self.seek_relative(-5), **nav_btn_style).pack(side=tk.LEFT, padx=3)
        tk.Button(nav_btn_frame, text="+5s ▶", command=lambda: self.seek_relative(5), **nav_btn_style).pack(side=tk.LEFT, padx=3)
        tk.Button(nav_btn_frame, text="+10s ⏭", command=lambda: self.seek_relative(10), **nav_btn_style).pack(side=tk.LEFT, padx=3)
        
        # Status ao lado dos botões de navegação
        self.status_label = tk.Label(
            nav_btn_frame,
            text="Pronto",
            bg="#181828",
            fg="#888888",
            font=("Arial", 8),
            padx=10
        )
        self.status_label.pack(side=tk.LEFT, padx=(15, 0))
        
        # ...progresso agora está abaixo do info_frame...
        
        # COLUNA DIREITA (30%) - Playlist
        right_frame = tk.Frame(main_container, bg="#2d2d2d", width=350)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5)
        right_frame.pack_propagate(False)
        
        # Header
        playlist_header = tk.Frame(right_frame, bg="#1a3a1a", pady=8)
        playlist_header.pack(fill=tk.X)
        
        tk.Label(
            playlist_header,
            text="🎵 PLAYLIST",
            bg="#1a3a1a",
            fg="white",
            font=("Arial", 12, "bold")
        ).pack()
        
        # Canvas com scroll
        canvas_frame = tk.Frame(right_frame, bg="#2d2d2d")
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.playlist_canvas = tk.Canvas(
            canvas_frame,
            bg="#2d2d2d",
            highlightthickness=0
        )
        scrollbar = tk.Scrollbar(
            canvas_frame,
            orient="vertical",
            command=self.playlist_canvas.yview
        )
        
        self.playlist_inner_frame = tk.Frame(self.playlist_canvas, bg="#2d2d2d")
        
        self.playlist_inner_frame.bind(
            "<Configure>",
            lambda e: self.playlist_canvas.configure(
                scrollregion=self.playlist_canvas.bbox("all")
            )
        )
        
        self.playlist_canvas.create_window(
            (0, 0),
            window=self.playlist_inner_frame,
            anchor="nw"
        )
        self.playlist_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.playlist_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Adiciona scroll com mouse wheel
        def on_mouse_wheel(event):
            self.playlist_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.playlist_canvas.bind_all("<MouseWheel>", on_mouse_wheel)
        
        # Mensagem vazia
        self.playlist_empty_label = tk.Label(
            self.playlist_inner_frame,
            text="Playlist vazia\n\nUse MODO EVENTO\nou carregue uma música",
            bg="#2d2d2d",
            fg="#666666",
            font=("Arial", 10),
            justify=tk.CENTER
        )
        self.playlist_empty_label.pack(pady=50)
        
        # V.U. METER - Adiciona após a playlist
        vu_outer_frame = tk.Frame(right_frame, bg="#1a1a1a", bd=2, relief=tk.RIDGE)
        vu_outer_frame.pack(fill=tk.X, pady=10, padx=5)
        
        vu_header = tk.Frame(vu_outer_frame, bg="#2d2d2d", pady=5)
        vu_header.pack(fill=tk.X)
        
        tk.Label(
            vu_header,
            text="🎤 MEDIDOR DE MICROFONE (V.U.)",
            bg="#2d2d2d",
            fg="white",
            font=("Arial", 10, "bold")
        ).pack()
        
        vu_content = tk.Frame(vu_outer_frame, bg="#1a1a1a")
        vu_content.pack(fill=tk.BOTH, padx=10, pady=10)
        
        # Canvas para o V.U. meter
        self.vu_canvas = tk.Canvas(
            vu_content,
            width=320,
            height=80,
            bg="#000000",
            highlightthickness=1,
            highlightbackground="#444"
        )
        self.vu_canvas.pack(pady=5)
        
        # Criar barras do V.U. (estéreo)
        self.vu_bar_left = self.vu_canvas.create_rectangle(
            10, 20, 10, 60, fill="#00ff00", width=0
        )
        self.vu_bar_right = self.vu_canvas.create_rectangle(
            10, 65, 10, 105, fill="#00ff00", width=0
        )
        
        # Labels dos canais
        self.vu_canvas.create_text(5, 40, text="L", fill="white", font=("Arial", 8, "bold"), anchor="w")
        self.vu_canvas.create_text(5, 85, text="R", fill="white", font=("Arial", 8, "bold"), anchor="w")
        
        # Marcações de nível
        for i, db in enumerate(["-40", "-20", "-10", "-5", "0"]):
            x = 10 + (i * 60)
            self.vu_canvas.create_line(x, 15, x, 110, fill="#333", width=1)
            self.vu_canvas.create_text(x, 5, text=db, fill="#888", font=("Arial", 7))
        
        # Label de nível numérico
        self.vu_label = tk.Label(
            vu_content,
            text="Nível: -∞ dB",
            bg="#1a1a1a",
            fg="#4CAF50",
            font=("Arial", 9, "bold")
        )
        self.vu_label.pack(pady=2)
        
        # Controle de sensibilidade/ganho
        sensitivity_frame = tk.Frame(vu_content, bg="#1a1a1a")
        sensitivity_frame.pack(pady=5, fill=tk.X)
        
        tk.Label(
            sensitivity_frame,
            text="Sensibilidade:",
            bg="#1a1a1a",
            fg="white",
            font=("Arial", 8)
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        self.vu_gain = tk.DoubleVar(value=3.0)  # Ganho padrão de 3x para voz
        self.vu_gain_slider = tk.Scale(
            sensitivity_frame,
            from_=1.0,
            to=10.0,
            resolution=0.5,
            orient=tk.HORIZONTAL,
            variable=self.vu_gain,
            bg="#333",
            fg="#4CAF50",
            troughcolor="#222",
            highlightthickness=0,
            length=180,
            width=12,
            showvalue=True,
            font=("Arial", 7)
        )
        self.vu_gain_slider.pack(side=tk.LEFT, padx=2)
        
        tk.Label(
            sensitivity_frame,
            text="(1x-10x)",
            bg="#1a1a1a",
            fg="#888",
            font=("Arial", 7)
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        # Botão para ligar/desligar V.U.
        self.vu_toggle_btn = tk.Button(
            vu_content,
            text="🎤 Ativar V.U. Meter",
            command=self.toggle_vu_meter,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 9, "bold"),
            cursor="hand2",
            padx=10,
            pady=5
        )
        self.vu_toggle_btn.pack(pady=5)
        
        self.debug_log("✓ Interface configurada")
    
    def selecionar_pasta_musicas(self):
        """Permite ao usuário selecionar a pasta de músicas."""
        pasta = filedialog.askdirectory(title="Selecione a pasta de músicas")
        if pasta:
            self.music_folder = pasta
            if hasattr(self, 'music_folder_var'):
                self.music_folder_var.set(self.music_folder)
            self.debug_log(f"Pasta de músicas alterada para: {self.music_folder}")
    
    def inicializar_audio(self):
        """Inicializa o sistema de áudio para captura do microfone"""
        if not AUDIO_DISPONIVEL:
            self.debug_log("⚠ sounddevice não disponível - V.U. meter desabilitado")
            return
        
        try:
            # sounddevice não precisa de inicialização de interface
            self.debug_log("✓ Sistema de áudio inicializado (sounddevice)")
        except Exception as e:
            self.debug_log(f"⚠ Erro ao inicializar áudio: {e}")
    
    def toggle_vu_meter(self):
        """Liga ou desliga o V.U. meter"""
        if self.vu_running:
            self.parar_vu_meter()
        else:
            self.iniciar_vu_meter()
    
    def iniciar_vu_meter(self):
        """Inicia a captura e exibição do V.U. meter"""
        if not AUDIO_DISPONIVEL:
            messagebox.showerror(
                "Erro",
                "sounddevice não está instalado!\n\n"
                "Instale com:\n"
                "pip install sounddevice numpy"
            )
            return
        
        try:
            # Configurações de áudio
            CHUNK = 1024
            CHANNELS = 2
            RATE = 44100
            
            self.vu_running = True
            
            # Callback para processar áudio
            def audio_callback(indata, frames, time_info, status):
                if status:
                    self.debug_log(f"⚠ Status do áudio: {status}")
                if self.vu_running:
                    self._processar_audio_vu_callback(indata.copy())
            
            # Abre stream de áudio com sounddevice
            self.audio_stream = sd.InputStream(
                channels=CHANNELS,
                samplerate=RATE,
                blocksize=CHUNK,
                callback=audio_callback,
                dtype=np.int16
            )
            
            self.audio_stream.start()
            
            self.vu_toggle_btn.config(
                text="⏹ Parar V.U. Meter",
                bg="#f44336"
            )
            
            self.debug_log("✓ V.U. meter ativado (sounddevice)")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir microfone:\n{e}")
            self.debug_log(f"❌ Erro ao abrir microfone: {e}")
    
    def parar_vu_meter(self):
        """Para a captura do V.U. meter"""
        self.vu_running = False
        
        if self.audio_stream:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            except:
                pass
            self.audio_stream = None
        
        # Reseta visual
        self.vu_canvas.coords(self.vu_bar_left, 10, 20, 10, 60)
        self.vu_canvas.coords(self.vu_bar_right, 10, 65, 10, 105)
        self.vu_label.config(text="Nível: -∞ dB")
        
        self.vu_toggle_btn.config(
            text="🎤 Ativar V.U. Meter",
            bg="#4CAF50"
        )
        
        self.debug_log("✓ V.U. meter desativado")
    
    def _processar_audio_vu_callback(self, audio_data):
        """Callback que processa o áudio do sounddevice e atualiza o V.U. meter"""
        try:
            # audio_data já vem como numpy array do sounddevice
            # Formato: (frames, channels) se estéreo, ou (frames,) se mono
            if len(audio_data.shape) == 2 and audio_data.shape[1] == 2:
                # Estéreo: pega cada canal
                left_channel = audio_data[:, 0]
                right_channel = audio_data[:, 1]
            elif len(audio_data.shape) == 1:
                # Mono: usa mesmo canal para L e R
                left_channel = audio_data
                right_channel = audio_data
            else:
                return
            
            if len(left_channel) > 0:
                    
                # Aplica ganho para aumentar sensibilidade
                gain = self.vu_gain.get()
                left_channel = left_channel.astype(np.float32) * gain
                right_channel = right_channel.astype(np.float32) * gain
                
                # Limita valores para evitar overflow
                left_channel = np.clip(left_channel, -32768, 32767)
                right_channel = np.clip(right_channel, -32768, 32767)
                
                # Calcula RMS (Root Mean Square) para cada canal
                rms_left = np.sqrt(np.mean(left_channel**2))
                rms_right = np.sqrt(np.mean(right_channel**2))
                
                # Armazena RMS médio para pontuação
                rms_avg = (rms_left + rms_right) / 2
                if hasattr(self, 'samples_microfone'):
                    self.samples_microfone.append(float(rms_avg))
                
                # Converte para dB (escala logarítmica)
                # Usa referência menor para voz (10.0 ao invés de 32768.0)
                if rms_left > 1:
                    db_left = 20 * np.log10(rms_left / 32768.0)
                else:
                    db_left = -60
                
                if rms_right > 1:
                    db_right = 20 * np.log10(rms_right / 32768.0)
                else:
                    db_right = -60
                
                # Limita valores
                db_left = max(-60, min(0, db_left))
                db_right = max(-60, min(0, db_right))
                
                # Atualiza visual na thread principal
                self.root.after(0, self._atualizar_vu_visual, db_left, db_right)
        
        except Exception as e:
            if self.vu_running:
                self.debug_log(f"Erro ao processar áudio: {e}")
    
    def _atualizar_vu_visual(self, db_left, db_right):
        """Atualiza o visual do V.U. meter (chamado na thread principal)"""
        if not self.vu_running:
            return
        
        # Converte dB para largura da barra (0 a 300 pixels)
        # -60dB = 0px, 0dB = 300px
        width_left = int((db_left + 60) * 5)
        width_right = int((db_right + 60) * 5)
        
        # Determina cor baseada no nível
        def get_color(db):
            if db > -6:  # Acima de -6dB (vermelho - clipping)
                return "#ff0000"
            elif db > -12:  # Entre -12 e -6dB (amarelo)
                return "#ffff00"
            else:  # Abaixo de -12dB (verde)
                return "#00ff00"
        
        color_left = get_color(db_left)
        color_right = get_color(db_right)
        
        # Atualiza barras
        self.vu_canvas.coords(self.vu_bar_left, 10, 20, 10 + width_left, 60)
        self.vu_canvas.itemconfig(self.vu_bar_left, fill=color_left)
        
        self.vu_canvas.coords(self.vu_bar_right, 10, 65, 10 + width_right, 105)
        self.vu_canvas.itemconfig(self.vu_bar_right, fill=color_right)
        
        # Atualiza label com valor médio
        db_avg = (db_left + db_right) / 2
        if db_avg <= -60:
            self.vu_label.config(text="Nível: -∞ dB")
        else:
            self.vu_label.config(text=f"Nível: {db_avg:.1f} dB")
    
    
    def adicionar_musica_playlist_simples(self, arquivo_path, cantor, musica, codigo):
        """Adiciona música à playlist simples (sem modo evento)"""
        # Cria item de playlist simples
        item = {
            'id': len(self.playlist_items) + 1,
            'ordem': len(self.playlist_items) + 1,
            'participante_nome': cantor,
            'participante_avatar': None,
            'musica_nome': musica,
            'arquivo_path': arquivo_path,
            'tom_ajuste': 0,
            'ja_tocou': False
        }
        
        self.playlist_items.append(item)
        self.atualizar_playlist_visual()
        
        messagebox.showinfo(
            "Adicionado",
            f"✅ Música adicionada à playlist!\n\n"
            f"🎤 {cantor}\n🎵 {musica}\n🔢 {codigo}"
        )
        
        self.debug_log(f"Música adicionada à playlist: {musica} - {cantor}")
    
    def adicionar_musica_evento(self, arquivo_path, cantor, musica, codigo):
        """Adiciona música ao evento com seleção de participante"""
        if not MODO_EVENTO_DISPONIVEL or not self.modo_evento_ativo:
            self.debug_log("Modo evento não ativo - música não adicionada ao evento")
            return
        
        try:
            from karaoke_evento import SelecionarParticipanteDialog
            import tkinter.simpledialog
            db = KaraokeDatabase()
            
            # Abre diálogo para selecionar participante
            dialog = SelecionarParticipanteDialog(self.root, self.evento_id_atual, db)
            self.root.wait_window(dialog.dialog)
            
            if dialog.participante_selecionado:
                participante = dialog.participante_selecionado
                
                # Pergunta sobre ajuste de tom
                tom_ajuste = 0
                if messagebox.askyesno("Tom", "Deseja ajustar o tom da música?"):
                    tom_str = tkinter.simpledialog.askstring(
                        "Ajuste de Tom",
                        "Digite o ajuste em semitons (-12 a +12):",
                        initialvalue="0"
                    )
                    if tom_str:
                        try:
                            tom_ajuste = int(tom_str)
                            tom_ajuste = max(-12, min(12, tom_ajuste))
                        except ValueError:
                            tom_ajuste = 0
                
                # Adiciona ao banco de dados do evento
                db.adicionar_musica_evento(
                    self.evento_id_atual,
                    participante['id'],
                    arquivo_path,
                    musica,
                    tom_ajuste
                )
                
                # Recarrega playlist
                self.carregar_playlist_evento(self.evento_id_atual)
                
                tom_texto = f"🎹 Tom: {tom_ajuste:+d}" if tom_ajuste != 0 else "🎹 Tom: normal"
                messagebox.showinfo(
                    "Adicionado",
                    f"✅ Música adicionada ao evento!\n\n"
                    f"🎤 Participante: {participante['nome']}\n"
                    f"🎵 Música: {musica}\n"
                    f"🔢 Código: {codigo}\n"
                    f"{tom_texto}"
                )
                
                self.debug_log(f"Música adicionada ao evento: {musica} - {participante['nome']}")
            else:
                self.debug_log("Seleção de participante cancelada")
                
        except ImportError:
            messagebox.showerror(
                "Erro",
                "Não foi possível importar o módulo de seleção de participante.\n"
                "Verifique se karaoke_evento.py está disponível."
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao adicionar música ao evento:\n{e}")
            self.debug_log(f"Erro ao adicionar música ao evento: {e}")
    
    def adicionar_musica_playlist_simples(self, arquivo_path, cantor, musica, codigo):
        """Adiciona música à playlist simples (sem modo evento)"""
        # Cria item de playlist simples
        item = {
            'id': len(self.playlist_items) + 1,
            'ordem': len(self.playlist_items) + 1,
            'participante_nome': cantor,
            'participante_avatar': None,
            'musica_nome': musica,
            'arquivo_path': arquivo_path,
            'tom_ajuste': 0,
            'ja_tocou': False
        }
        
        self.playlist_items.append(item)
        self.atualizar_playlist_visual()
        
        messagebox.showinfo(
            "Adicionado",
            f"✅ Música adicionada à playlist!\n\n"
            f"🎤 {cantor}\n🎵 {musica}\n🔢 {codigo}"
        )
        
        self.debug_log(f"Música adicionada à playlist: {musica} - {cantor}")
    
    def adicionar_musica_evento(self, arquivo_path, cantor, musica, codigo):
        """Adiciona música ao evento com seleção de participante"""
        if not MODO_EVENTO_DISPONIVEL or not self.modo_evento_ativo:
            messagebox.showerror("Erro", "Modo evento não está ativo!")
            return
        
        try:
            from karaoke_evento import SelecionarParticipanteDialog
            db = KaraokeDatabase()
            
            # Abre diálogo para selecionar participante
            dialog = SelecionarParticipanteDialog(self.root, self.evento_id_atual, db)
            self.root.wait_window(dialog.dialog)
            
            if dialog.participante_selecionado:
                participante = dialog.participante_selecionado
                
                # Pergunta sobre ajuste de tom
                tom_ajuste = 0
                if messagebox.askyesno("Tom", "Deseja ajustar o tom da música?"):
                    tom_str = tk.simpledialog.askstring(
                        "Ajuste de Tom",
                        "Digite o ajuste em semitons (-12 a +12):",
                        initialvalue="0"
                    )
                    if tom_str:
                        try:
                            tom_ajuste = int(tom_str)
                            tom_ajuste = max(-12, min(12, tom_ajuste))
                        except ValueError:
                            tom_ajuste = 0
                
                # Adiciona ao banco de dados do evento
                db.adicionar_musica_evento(
                    self.evento_id_atual,
                    participante['id'],
                    arquivo_path,
                    musica,
                    tom_ajuste
                )
                
                # Recarrega playlist
                self.carregar_playlist_evento(self.evento_id_atual)
                
                messagebox.showinfo(
                    "Adicionado",
                    f"✅ Música adicionada ao evento!\n\n"
                    f"🎤 Participante: {participante['nome']}\n"
                    f"🎵 Música: {musica}\n"
                    f"🔢 Código: {codigo}\n"
                    f"🎹 Tom: {tom_ajuste:+d}" if tom_ajuste != 0 else f"🎹 Tom: normal"
                )
                
                self.debug_log(f"Música adicionada ao evento: {musica} - {participante['nome']}")
            else:
                self.debug_log("Seleção de participante cancelada")
                
        except ImportError:
            messagebox.showerror(
                "Erro",
                "Não foi possível importar o módulo de seleção de participante.\n"
                "Verifique se karaoke_evento.py está disponível."
            )
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao adicionar música ao evento:\n{e}")
            self.debug_log(f"Erro ao adicionar música ao evento: {e}")
    
    def debug_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        try:
            with open("karaoke_debug.log", "a", encoding="utf-8") as f:
                f.write(log_message + "\n")
        except:
            pass
    
    def atualizar_playlist_visual(self):
        for widget in self.playlist_inner_frame.winfo_children():
            widget.destroy()
        
        if not self.playlist_items:
            self.playlist_empty_label = tk.Label(
                self.playlist_inner_frame,
                text="Playlist vazia",
                bg="#2d2d2d",
                fg="#666666",
                font=("Arial", 10)
            )
            self.playlist_empty_label.pack(pady=50)
            return
        
        for i, item in enumerate(self.playlist_items):
            self.criar_item_playlist(i, item)
    
    def criar_item_playlist(self, index, item):
        """Cria um card visual para um item da playlist com avatar, nome do participante e música"""
        is_selected = (index == self.selected_playlist_index)
        is_playing = (self.modo_evento_ativo and 
                    self.musica_atual_evento and 
                    item.get('id') == self.musica_atual_evento.get('id'))
        
        if is_playing:
            bg = "#1a5a1a"
        elif is_selected:
            bg = "#3a3a5a"
        elif item.get('ja_tocou'):
            bg = "#2a2a2a"
        else:
            bg = "#1a1a1a"
        
        # Frame principal do card
        frame = tk.Frame(self.playlist_inner_frame, bg=bg, relief=tk.RAISED, bd=2, cursor="hand2")
        frame.pack(fill=tk.X, pady=2, padx=3)
        
        def selecionar_e_tocar(event):
            self.selected_playlist_index = index
            self.atualizar_playlist_visual()
            self.tocar_musica_playlist(index)
        
        frame.bind("<Button-1>", selecionar_e_tocar)
        
        # Container horizontal principal
        main_container = tk.Frame(frame, bg=bg)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        main_container.bind("<Button-1>", selecionar_e_tocar)
        
        # COLUNA ESQUERDA: Número, Status e Avatar
        left_col = tk.Frame(main_container, bg=bg)
        left_col.pack(side=tk.LEFT, padx=(0, 8))
        left_col.bind("<Button-1>", selecionar_e_tocar)
        
        # Número da ordem
        num_label = tk.Label(
            left_col, 
            text=f"#{item.get('ordem', index+1)}", 
            bg=bg, 
            fg="#888" if item.get('ja_tocou') else "#FFA500", 
            font=("Arial", 10, "bold"),
            width=3
        )
        num_label.pack(pady=(0, 2))
        num_label.bind("<Button-1>", selecionar_e_tocar)
        
        # Status indicator
        if is_playing:
            status = "▶"
            cor_status = "#4CAF50"
        elif item.get('ja_tocou'):
            status = "✓"
            cor_status = "#666"
        else:
            status = "○"
            cor_status = "#FFA500"
        
        status_label = tk.Label(
            left_col, 
            text=status, 
            bg=bg, 
            fg=cor_status, 
            font=("Arial", 14, "bold")
        )
        status_label.pack(pady=(0, 5))
        status_label.bind("<Button-1>", selecionar_e_tocar)
        
        # Avatar
        avatar_frame = tk.Frame(left_col, bg=bg, width=50, height=50, relief=tk.SUNKEN, bd=1)
        avatar_frame.pack()
        avatar_frame.pack_propagate(False)
        avatar_frame.bind("<Button-1>", selecionar_e_tocar)
        
        try:
            if item.get('participante_avatar') and os.path.exists(item['participante_avatar']):
                from PIL import Image, ImageTk
                img = Image.open(item['participante_avatar'])
                img = img.resize((48, 48), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                avatar_label = tk.Label(avatar_frame, image=photo, bg=bg)
                avatar_label.image = photo  # Mantém referência
                avatar_label.pack(expand=True)
                avatar_label.bind("<Button-1>", selecionar_e_tocar)
            else:
                # Avatar padrão com inicial do nome
                inicial = item.get('participante_nome', '?')[0].upper()
                avatar_label = tk.Label(
                    avatar_frame,
                    text=inicial,
                    bg="#555",
                    fg="white",
                    font=("Arial", 20, "bold")
                )
                avatar_label.pack(expand=True, fill=tk.BOTH)
                avatar_label.bind("<Button-1>", selecionar_e_tocar)
        except Exception as e:
            # Fallback para avatar padrão
            inicial = item.get('participante_nome', '?')[0].upper()
            avatar_label = tk.Label(
                avatar_frame,
                text=inicial,
                bg="#555",
                fg="white",
                font=("Arial", 20, "bold")
            )
            avatar_label.pack(expand=True, fill=tk.BOTH)
            avatar_label.bind("<Button-1>", selecionar_e_tocar)
        
        # COLUNA DIREITA: Informações
        right_col = tk.Frame(main_container, bg=bg)
        right_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_col.bind("<Button-1>", selecionar_e_tocar)
        
        # Nome do participante
        participante_label = tk.Label(
            right_col,
            text=f"🎤 {item.get('participante_nome', 'Sem nome')}",
            bg=bg,
            fg="white" if not item.get('ja_tocou') else "#888",
            font=("Arial", 10, "bold" if is_selected or is_playing else "normal"),
            anchor=tk.W,
            justify=tk.LEFT
        )
        participante_label.pack(anchor=tk.W, fill=tk.X)
        participante_label.bind("<Button-1>", selecionar_e_tocar)
        
        # Nome da música
        musica_nome = item.get('musica_nome', os.path.basename(item.get('arquivo_path', 'Sem arquivo')))
        if len(musica_nome) > 30:
            musica_nome = musica_nome[:27] + "..."
        
        musica_label = tk.Label(
            right_col,
            text=f"🎵 {musica_nome}",
            bg=bg,
            fg="#4CAF50" if is_playing else ("#AAA" if not item.get('ja_tocou') else "#666"),
            font=("Arial", 9, "italic" if not is_selected else "normal"),
            anchor=tk.W,
            justify=tk.LEFT
        )
        musica_label.pack(anchor=tk.W, fill=tk.X, pady=(2, 0))
        musica_label.bind("<Button-1>", selecionar_e_tocar)
        
        # Informações adicionais (tom, arquivo, pontuação)
        info_adicional = []
        
        if item.get('tom_ajuste', 0) != 0:
            info_adicional.append(f"Tom: {item['tom_ajuste']:+d}")
        
        # Pontuação do V.U. meter (se já tocou)
        if item.get('ja_tocou') and item.get('pontuacao_vu', 0) > 0:
            pontos = item['pontuacao_vu']
            info_adicional.append(f"⭐ {pontos:.0f} pts")
        
        # Nome do arquivo (código ou nome curto)
        arquivo_nome = os.path.basename(item.get('arquivo_path', ''))
        if len(arquivo_nome) > 20:
            arquivo_nome = arquivo_nome[:17] + "..."
        info_adicional.append(f"📁 {arquivo_nome}")
        
        if info_adicional:
            info_text = " | ".join(info_adicional)
            info_label = tk.Label(
                right_col,
                text=info_text,
                bg=bg,
                fg="#666" if item.get('ja_tocou') else "#888",
                font=("Arial", 7),
                anchor=tk.W
            )
            info_label.pack(anchor=tk.W, pady=(2, 0))
            info_label.bind("<Button-1>", selecionar_e_tocar)
    
    def tocar_musica_playlist(self, index):
        """Toca uma música específica da playlist pelo índice"""
        if not self.playlist_items or index >= len(self.playlist_items):
            return
        
        item = self.playlist_items[index]
        
        # Se já está tocando esta música, apenas continua
        if self.modo_evento_ativo and self.musica_atual_evento and item['id'] == self.musica_atual_evento['id']:
            if not self.is_playing:
                self.play()
            return
        
        # Para a música atual se estiver tocando
        if self.is_playing:
            self.stop()
        
        # Atualiza índice selecionado
        self.selected_playlist_index = index
        self.atualizar_playlist_visual()
        
        # Feedback visual
        self.status_label.config(text=f"Carregando: {os.path.basename(item['arquivo_path'])}")
        
        # Se não está em modo evento, toca normalmente
        # Se está em modo evento, valida que a música pertence ao evento ativo
        if self.modo_evento_ativo and MODO_EVENTO_DISPONIVEL:
            # Verifica se a música pertence ao evento atual
            if 'evento_id' not in item or item.get('evento_id') != self.evento_id_atual:
                messagebox.showwarning("Aviso", "Esta música não pertence ao evento ativo.")
                return
        
        # Toca a música
        if MODO_EVENTO_DISPONIVEL and self.modo_evento_ativo:
            self.iniciar_modo_evento(self.evento_id_atual, item)
        else:
            # Fallback para modo normal
            self.video_file = item['arquivo_path']
            self.processed_file = item['arquivo_path']
            self.pitch_shift = item.get('tom_ajuste', 0)
            self.pitch_label.config(text=f"{self.pitch_shift:+d}" if self.pitch_shift != 0 else "0")
            self.file_label.config(text=f"🎤 {item['participante_nome']} - {os.path.basename(item['arquivo_path'])}")
            
            try:
                # Obtém informações do vídeo
                result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-print_format', 'json',
                    '-show_format', '-show_streams', self.video_file
                ], capture_output=True, text=True, check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                
                info = json.loads(result.stdout)
                for stream in info['streams']:
                    if stream['codec_type'] == 'video':
                        self.fps = eval(stream.get('r_frame_rate', '30/1'))
                        self.width = stream['width']
                        self.height = stream['height']
                        break
                self.duration = float(info['format']['duration'])
            except FileNotFoundError:
                self.debug_log("⚠️ FFprobe não encontrado")
                messagebox.showerror("Erro", "FFprobe não encontrado!")
                return
            except Exception as e:
                self.debug_log(f"⚠️ Erro ao obter informações do vídeo: {e}")
            
            # Processa tom se necessário
            if self.pitch_shift != 0:
                self.process_audio_with_pitch()
                self.root.after(1000, self._check_and_play)
            else:
                self.processed_file = self.video_file
                self.play()
    
    def tocar_musica_selecionada(self):
        """Toca a música atualmente selecionada na playlist"""
        if self.selected_playlist_index is not None:
            self.tocar_musica_playlist(self.selected_playlist_index)
        else:
            messagebox.showinfo("Seleção", "Nenhuma música selecionada na playlist.")
    
    def tocar_proxima_musica(self):
        """Toca a próxima música da playlist"""
        if not self.playlist_items:
            messagebox.showinfo("Playlist", "Playlist vazia.")
            return

        # Descobre o índice da música atualmente tocando
        idx = self.selected_playlist_index
        if idx is None:
            # Tenta encontrar a música tocando pelo modo evento
            if self.modo_evento_ativo and self.musica_atual_evento:
                for i, item in enumerate(self.playlist_items):
                    if item.get('id') == self.musica_atual_evento.get('id'):
                        idx = i
                        break
            else:
                idx = -1

        next_index = (idx + 1) % len(self.playlist_items)
        self.tocar_musica_playlist(next_index)
    
    def carregar_playlist_evento(self, evento_id):
        if not MODO_EVENTO_DISPONIVEL:
            return
        db = KaraokeDatabase()
        self.playlist_items = db.obter_playlist(evento_id)
        self.atualizar_playlist_visual()
    
    def abrir_youtube_downloader(self):
        """Abre janela para buscar e baixar vídeos do YouTube"""
        self.debug_log("📥 Abrindo YouTube Downloader...")
        YouTubeDownloaderWindow(self.root, self.music_folder)
        
    def abrir_modo_evento(self):
        if not MODO_EVENTO_DISPONIVEL:
            messagebox.showerror("Erro", "Módulos de evento não encontrados!")
            return
        self.debug_log("🎉 Abrindo Modo Evento...")
        ModoEventoWindow(self.root, self)
    
    def abrir_gerenciar_eventos(self):
        """Abre janela para gerenciar eventos existentes"""
        if not MODO_EVENTO_DISPONIVEL:
            messagebox.showerror("Erro", "Módulos de evento não encontrados!")
            return
        
        gerenciar_win = tk.Toplevel(self.root)
        gerenciar_win.title("Gerenciar Eventos")
        gerenciar_win.geometry("900x600")
        gerenciar_win.configure(bg="#222")
        gerenciar_win.transient(self.root)
        
        # Header
        tk.Label(
            gerenciar_win,
            text="📋 Gerenciar Eventos",
            font=("Arial", 16, "bold"),
            bg="#222",
            fg="white"
        ).pack(pady=15)
        
        # Frame de lista
        list_frame = tk.Frame(gerenciar_win, bg="#222")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        
        # Treeview
        columns = ("ID", "Nome", "Data Criação", "Status", "Participantes", "Músicas")
        tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=18)
        
        tree.heading("ID", text="ID")
        tree.heading("Nome", text="Nome do Evento")
        tree.heading("Data Criação", text="Data Criação")
        tree.heading("Status", text="Status")
        tree.heading("Participantes", text="Participantes")
        tree.heading("Músicas", text="Músicas")
        
        tree.column("ID", width=50, anchor="center")
        tree.column("Nome", width=250)
        tree.column("Data Criação", width=150, anchor="center")
        tree.column("Status", width=100, anchor="center")
        tree.column("Participantes", width=100, anchor="center")
        tree.column("Músicas", width=100, anchor="center")
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Função para carregar eventos
        def carregar_eventos():
            tree.delete(*tree.get_children())
            db = KaraokeDatabase()
            eventos = db.listar_todos_eventos()
            
            for evento in eventos:
                data_criacao = datetime.fromisoformat(evento['data_criacao']).strftime("%d/%m/%Y %H:%M")
                status = "✓ Finalizado" if evento['finalizado'] else "▶ Ativo"
                
                tree.insert("", "end", values=(
                    evento['id'],
                    evento['nome'],
                    data_criacao,
                    status,
                    evento['total_participantes'],
                    evento['total_musicas']
                ))
        
        # Função para excluir evento
        def excluir_evento():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Seleção Necessária", "Selecione um evento para excluir.")
                return
            
            item = tree.item(selection[0])
            evento_id = item['values'][0]
            evento_nome = item['values'][1]
            
            resposta = messagebox.askyesno(
                "Confirmar Exclusão",
                f"Deseja realmente excluir o evento?\n\n"
                f"📋 Evento: {evento_nome}\n"
                f"🆔 ID: {evento_id}\n\n"
                f"⚠️ ATENÇÃO: Esta ação não pode ser desfeita!\n"
                f"Todos os participantes e músicas serão excluídos.",
                icon='warning'
            )
            
            if resposta:
                try:
                    db = KaraokeDatabase()
                    db.excluir_evento(evento_id)
                    messagebox.showinfo("Sucesso", f"Evento '{evento_nome}' excluído com sucesso!")
                    carregar_eventos()
                except Exception as e:
                    messagebox.showerror("Erro", f"Erro ao excluir evento:\n{e}")
        
        # Função para carregar evento
        def carregar_evento():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Seleção Necessária", "Selecione um evento para carregar.")
                return
            
            item = tree.item(selection[0])
            evento_id = item['values'][0]
            evento_nome = item['values'][1]
            
            resposta = messagebox.askyesno(
                "Carregar Evento",
                f"Deseja carregar o evento?\n\n"
                f"📋 {evento_nome}\n"
                f"🆔 ID: {evento_id}\n\n"
                f"A playlist atual será substituída."
            )
            
            if resposta:
                self.modo_evento_ativo = True
                self.evento_id_atual = evento_id
                self.carregar_playlist_evento(evento_id)
                messagebox.showinfo("Sucesso", f"Evento '{evento_nome}' carregado!")
                gerenciar_win.destroy()
        
        # Botões de ação
        btn_frame = tk.Frame(gerenciar_win, bg="#222")
        btn_frame.pack(pady=15)
        
        tk.Button(
            btn_frame,
            text="🔄 Atualizar Lista",
            command=carregar_eventos,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            width=15,
            padx=10,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame,
            text="📂 Carregar Evento",
            command=carregar_evento,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            width=15,
            padx=10,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame,
            text="🗑️ Excluir Evento",
            command=excluir_evento,
            bg="#f44336",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            width=15,
            padx=10,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            btn_frame,
            text="✖ Fechar",
            command=gerenciar_win.destroy,
            bg="#666",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            width=15,
            padx=10,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        # Carregar eventos ao abrir
        carregar_eventos()
        
        # Duplo clique para carregar evento
        tree.bind("<Double-1>", lambda e: carregar_evento())
    
    def finalizar_evento_e_limpar_playlist(self):
        """Finaliza o evento atual e limpa a playlist"""
        if self.modo_evento_ativo or len(self.playlist_items) > 0:
            resposta = messagebox.askyesno(
                "Finalizar Evento e Limpar Playlist",
                "Deseja finalizar o evento atual e limpar a playlist?\n\n"
                "✓ Modo evento será desativado\n"
                "✓ Playlist será limpa\n"
                "✓ Reprodução será interrompida",
                parent=self.root
            )
            
            if resposta:
                # Parar reprodução
                self.stop()
                
                # Desativar modo evento
                self.modo_evento_ativo = False
                self.evento_id_atual = None
                self.musica_atual_evento = None
                
                # Limpar playlist
                self.playlist_items = []
                self.selected_playlist_index = None
                
                # Atualizar interface
                self.atualizar_playlist_visual()
                self.file_label.config(text="Nenhum arquivo carregado")
                self.status_label.config(text="✅ Evento finalizado e playlist limpa")
                
                self.debug_log("✅ Evento finalizado e playlist limpa")
                
                messagebox.showinfo(
                    "Sucesso",
                    "Evento finalizado e playlist limpa com sucesso!",
                    parent=self.root
                )
        else:
            messagebox.showinfo(
                "Informação",
                "Não há evento ativo ou playlist para limpar.",
                parent=self.root
            )
    
    def iniciar_modo_evento(self, evento_id, musica):
        self.modo_evento_ativo = True
        self.evento_id_atual = evento_id
        self.musica_atual_evento = musica
        self.carregar_playlist_evento(evento_id)
        
        self.file_label.config(text=f"🎤 {musica['participante_nome']} - {os.path.basename(musica['arquivo_path'])}")
        self.video_file = musica['arquivo_path']
        
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', self.video_file
            ], capture_output=True, text=True, check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            info = json.loads(result.stdout)
            for stream in info['streams']:
                if stream['codec_type'] == 'video':
                    self.fps = eval(stream.get('r_frame_rate', '30/1'))
                    self.width = stream['width']
                    self.height = stream['height']
                    break
            self.duration = float(info['format']['duration'])
        except FileNotFoundError:
            self.debug_log("⚠️ FFprobe não encontrado")
            messagebox.showerror("Erro", "FFprobe não encontrado!")
            return
        except Exception as e:
            self.debug_log(f"⚠️ Erro ao obter informações do vídeo: {e}")
        
        self.pitch_shift = musica['tom_ajuste']
        self.pitch_label.config(text=f"{self.pitch_shift:+d}" if self.pitch_shift != 0 else "0")
        
        if self.pitch_shift != 0:
            self.processed_file = None
            self.process_audio_with_pitch()
            self.root.after(1000, self._check_and_play)
        else:
            self.processed_file = self.video_file
            self.play()
    
    def _check_and_play(self):
        if self.processed_file and not self.processing_pitch:
            self.play()
        else:
            self.root.after(500, self._check_and_play)
    
    def finalizar_musica_evento(self):
        if not self.modo_evento_ativo or not MODO_EVENTO_DISPONIVEL:
            return
        
        db = KaraokeDatabase()
        tempo = self.player.get_time() / 1000.0 if self.player else 0
        
        # Passa a pontuação do V.U. meter (se disponível) para o banco de dados
        pontuacao_vu = getattr(self, 'pontuacao_final', None)
        db.marcar_musica_tocada(self.musica_atual_evento['id'], tempo, pontuacao_vu)
        
        self.carregar_playlist_evento(self.evento_id_atual)
        
        # Verifica se há próxima música
        proxima = db.obter_proxima_musica(self.evento_id_atual)
        if proxima:
            if messagebox.askyesno("Próxima", f"🎤 {proxima['participante_nome']}\n🎵 {os.path.basename(proxima['arquivo_path'])}\n\nIniciar?"):
                self.iniciar_modo_evento(self.evento_id_atual, proxima)
        else:
            messagebox.showinfo("Fim", "🎉 Evento finalizado!")
            self.modo_evento_ativo = False
            self.atualizar_playlist_visual()
    
    def load_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("MP4", "*.mp4"), ("Todos", "*.*")]
        )
        
        if path:
            try:
                result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-print_format', 'json',
                    '-show_format', '-show_streams', path
                ], capture_output=True, text=True, check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                
                info = json.loads(result.stdout)
                for stream in info['streams']:
                    if stream['codec_type'] == 'video':
                        self.fps = eval(stream.get('r_frame_rate', '30/1'))
                        self.width = stream['width']
                        self.height = stream['height']
                        break
                
                self.duration = float(info['format']['duration'])
                self.video_file = path
                self.processed_file = path
                self.pitch_shift = 0
                self.pitch_label.config(text="0")
                # Atualiza o pitch_var do Spinbox também, se existir
                if hasattr(self, 'pitch_var'):
                    self.pitch_var.set(0)
                
                self.file_label.config(text=os.path.basename(path))
                self.status_label.config(text="✓ Arquivo carregado!")
                self.debug_log(f"✓ Arquivo carregado: {os.path.basename(path)}")
                
                # AUTOPLAY: Iniciar reprodução automaticamente após carregar
                self.root.after(500, self.play)
                
            except FileNotFoundError as e:
                erro_msg = "❌ FFprobe não encontrado!\n\nO programa precisa do FFmpeg instalado."
                self.debug_log(f"❌ Erro FileNotFoundError: {e}")
                messagebox.showerror("Erro - FFmpeg Não Encontrado", erro_msg)
                mostrar_erro_ffmpeg()
            except subprocess.CalledProcessError as e:
                erro_msg = f"❌ Erro ao analisar o vídeo:\n{e.stderr if e.stderr else 'Erro desconhecido'}"
                self.debug_log(f"❌ Erro CalledProcessError: {e}")
                messagebox.showerror("Erro ao Processar Vídeo", erro_msg)
            except Exception as e:
                self.debug_log(f"❌ Erro ao carregar arquivo: {e}")
                messagebox.showerror("Erro", f"Erro ao carregar arquivo:\n\n{str(e)}")
    
    def show_first_frame(self):
        try:
            temp = tempfile.mktemp(suffix='.jpg')
            subprocess.run(['ffmpeg', '-i', self.video_file, '-vframes', '1', '-f', 'image2', temp], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            img = Image.open(temp)
            self.display_frame(img)
            os.unlink(temp)
        except FileNotFoundError:
            self.debug_log("⚠️ FFmpeg não encontrado para extrair frame")
        except Exception as e:
            self.debug_log(f"⚠️ Erro ao extrair primeiro frame: {e}")
    
    def show_progress(self, msg="Processando..."):
        self.progress_label.config(text=msg)
        self.progress_label.pack_configure()
        self.progress_canvas.itemconfig(self.progress_bar, fill="#00e676")
        self.progress_frame.lift()
        self.progress_animation_running = True
        self.animate_progress()
    
    def hide_progress(self):
        self.progress_animation_running = False
        self.progress_label.config(text="")
        self.progress_canvas.coords(self.progress_bar, 0, 0, 0, 18)
    
    def animate_progress(self):
        if not self.progress_animation_running:
            return
        w = self.progress_canvas.coords(self.progress_bar)[2]
        if w >= 250:
            d = -1
        elif w <= 0:
            d = 1
        else:
            d = getattr(self, '_pd', 1)
        self._pd = d
        w = max(0, min(250, w + d * 10))
        self.progress_canvas.coords(self.progress_bar, 0, 0, w, 15)
        if self.progress_animation_running:
            self.root.after(50, self.animate_progress)
    
    def change_pitch(self, steps):
        if not self.video_file or self.processing_pitch:
            return
        
        if self.is_playing:
            self.stop()
        
        self.root.config(cursor="wait")
        self.show_progress("Processando tom...")
        self.pitch_shift += steps
        # Atualiza o valor do Spinbox e label
        if hasattr(self, 'pitch_var'):
            self.pitch_var.set(self.pitch_shift)
        self.pitch_label.config(text=f"Tom: {self.pitch_shift:+d}" if self.pitch_shift != 0 else "Tom: 0")

        if self.pitch_shift != 0:
            self.process_audio_with_pitch()
        else:
            if self.processed_file != self.video_file:
                try:
                    os.unlink(self.processed_file)
                except:
                    pass
            self.processed_file = self.video_file
            self.root.config(cursor="")
            self.hide_progress()
    
    def change_speed(self, speed):
        """Altera a velocidade de reprodução do vídeo"""
        self.playback_speed = speed
        self.speed_label.config(text=f"Velocidade: {speed}x")
        
        # Se estiver tocando, aplica a nova velocidade
        if self.player and self.is_playing:
            try:
                self.player.set_rate(speed)
                self.debug_log(f"⚡ Velocidade alterada para: {speed}x")
            except Exception as e:
                self.debug_log(f"⚠️ Erro ao alterar velocidade: {e}")
        
        self.debug_log(f"Velocidade de reprodução definida para: {speed}x")
    
    def process_audio_with_pitch(self):
        self.processing_pitch = True
        
        def proc():
            try:
                temp = tempfile.mktemp(suffix='.mp4')
                ratio = 2 ** (self.pitch_shift / 12.0)
                tempo = 1.0 / ratio
                
                if 0.5 <= tempo <= 2.0:
                    filt = f'asetrate=44100*{ratio},aresample=44100,atempo={tempo}'
                else:
                    filt = f'asetrate=44100*{ratio},aresample=44100'
                
                subprocess.run([
                    'ffmpeg', '-y', '-i', self.video_file,
                    '-filter_complex', f'[0:a]{filt}[audio]',
                    '-map', '0:v', '-map', '[audio]',
                    '-c:v', 'copy', '-c:a', 'aac',
                    temp
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                
                if self.processed_file != self.video_file:
                    try:
                        os.unlink(self.processed_file)
                    except:
                        pass
                
                self.processed_file = temp
                self.root.after(0, self._pitch_ok)
            except:
                self.root.after(0, self._pitch_erro)
            finally:
                self.processing_pitch = False
        
        threading.Thread(target=proc, daemon=True).start()
    
    def _pitch_ok(self):
        self.status_label.config(text=f"✓ Tom: {self.pitch_shift:+d}")
        self.root.config(cursor="")
        self.hide_progress()
    
    def _pitch_erro(self):
        self.status_label.config(text="❌ Erro")
        self.root.config(cursor="")
        self.hide_progress()
        self.pitch_shift = 0
        self.pitch_label.config(text="0")
        self.processed_file = self.video_file
    
    def play(self):
        """Inicia reprodução do vídeo"""
        if not self.video_file:
            if self.modo_evento_ativo and self.playlist_items:
                if self.selected_playlist_index is None:
                    if MODO_EVENTO_DISPONIVEL:
                        db = KaraokeDatabase()
                        prox = db.obter_proxima_musica(self.evento_id_atual)
                        if prox:
                            self.iniciar_modo_evento(self.evento_id_atual, prox)
                else:
                    mus = self.playlist_items[self.selected_playlist_index]
                    if not mus['ja_tocou']:
                        self.iniciar_modo_evento(self.evento_id_atual, mus)
            return
        
        # Reproduz com VLC
        try:
            # Preparar mídia
            media = self.vlc_instance.media_new(self.processed_file)
            self.player.set_media(media)
            
            # Embutir VLC na janela secundária se disponível
            if self.video_window and self.video_frame_secondary:
                # Garantir que o frame está visível e atualizado
                self.video_window.update()
                self.video_frame_secondary.update_idletasks()
                
                # Limpar qualquer label de texto anterior
                for widget in self.video_frame_secondary.winfo_children():
                    widget.destroy()
                
                if os.name == 'nt':  # Windows
                    hwnd = self.video_frame_secondary.winfo_id()
                    self.player.set_hwnd(hwnd)
                    self.debug_log(f"🎬 VLC embutido na janela secundária (HWND: {hwnd})")
                else:  # Linux
                    xid = self.video_frame_secondary.winfo_id()
                    self.player.set_xwindow(xid)
                    self.debug_log(f"🎬 VLC embutido na janela secundária (XID: {xid})")
            
            self.player.play()
            self.is_playing = True
            
            # Aplicar velocidade de reprodução
            if hasattr(self, 'playback_speed'):
                self.root.after(100, lambda: self.player.set_rate(self.playback_speed))
                self.debug_log(f"⚡ Aplicando velocidade: {self.playback_speed}x")
            
            # Ativa V.U. meter automaticamente e reseta amostras
            if AUDIO_DISPONIVEL and not self.vu_running:
                self.samples_microfone = []
                self.tempo_inicio_musica = time.time()
                self.pontuacao_exibida = False  # Flag para controlar exibição única
                self.root.after(500, self.iniciar_vu_meter)
                self.debug_log("🎤 V.U. meter ativado automaticamente")
            elif self.vu_running:
                # Se já estava ativo, apenas reseta amostras
                self.samples_microfone = []
                self.tempo_inicio_musica = time.time()
                self.pontuacao_exibida = False  # Flag para controlar exibição única
                self.debug_log("🎤 Amostras resetadas para nova música")
            
            self.status_label.config(text="▶ Tocando")
            self.debug_log("▶ Play")
        except Exception as e:
            self.debug_log(f"❌ Erro ao reproduzir: {e}")
    
    def pause(self):
        """Pausa reprodução do vídeo"""
        if self.player and self.is_playing:
            self.player.pause()
            self.is_playing = False
            self.status_label.config(text="⏸ Pausado")
            self.debug_log("⏸ Pause")
    
    def stop(self):
        """Para reprodução do vídeo"""
        if self.player:
            self.player.stop()
            self.is_playing = False
            self.status_label.config(text="⏹ Parado")
            self.debug_log("⏹ Stop")
    
    def on_slider_press(self):
        """Chamado quando usuário clica no slider"""
        self.is_seeking = True
    
    def on_slider_release(self):
        """Chamado quando usuário solta o slider"""
        self.is_seeking = False
        # Aplica a posição escolhida
        if self.player and self.duration > 0:
            progress = self.seek_slider.get() / 100.0
            new_time = int(progress * self.duration * 1000)  # VLC usa milissegundos
            self.player.set_time(new_time)
            self.debug_log(f"⏩ Seek para: {new_time/1000:.1f}s")
    
    def on_slider_change(self, value):
        """Chamado quando o valor do slider muda"""
        # Atualiza o tempo exibido durante o arraste
        if self.is_seeking and self.duration > 0:
            progress = float(value) / 100.0
            current_time = progress * self.duration
            current_str = time.strftime('%M:%S', time.gmtime(current_time))
            duration_str = time.strftime('%M:%S', time.gmtime(self.duration))
            self.time_label.config(text=f"{current_str} / {duration_str}")
    
    def seek_relative(self, seconds):
        """Avança ou retrocede o vídeo em segundos"""
        if not self.player or not self.is_playing:
            return
        
        try:
            current_time = self.player.get_time()  # tempo em ms
            new_time = max(0, current_time + (seconds * 1000))  # adiciona segundos convertidos para ms
            
            # Não permite avançar além da duração
            if self.duration > 0:
                max_time = self.duration * 1000
                new_time = min(new_time, max_time)
            
            self.player.set_time(int(new_time))
            self.debug_log(f"⏩ Seek: {seconds:+d}s (novo tempo: {new_time/1000:.1f}s)")
            
            # Atualizar slider horizontal
            if hasattr(self, 'seek_slider') and self.duration > 0:
                progress = (new_time / 1000.0) / self.duration * 100.0
                self.seek_slider.set(progress)
                
        except Exception as e:
            self.debug_log(f"⚠️ Erro ao fazer seek: {e}")
    
    def mostrar_aguarde_pontuacao(self):
        """Exibe janela de aguarde enquanto calcula a pontuação"""
        # Determina janela pai (preferência para video_window)
        parent = self.video_window if (hasattr(self, 'video_window') and self.video_window and self.video_window.winfo_exists()) else self.root
        
        # Cria janela de aguarde
        self.aguarde_win = tk.Toplevel(parent)
        self.aguarde_win.title("Processando")
        self.aguarde_win.configure(bg="#1a1a1a")
        self.aguarde_win.transient(parent)
        self.aguarde_win.resizable(False, False)
        
        # Força a janela a ficar sempre no topo
        self.aguarde_win.attributes('-topmost', True)
        
        # Conteúdo
        tk.Label(
            self.aguarde_win,
            text="⏳",
            bg="#1a1a1a",
            font=("Arial", 40)
        ).pack(pady=(20, 10))
        
        tk.Label(
            self.aguarde_win,
            text="Calculando pontuação...",
            bg="#1a1a1a",
            fg="#4CAF50",
            font=("Arial", 14, "bold")
        ).pack()
        
        tk.Label(
            self.aguarde_win,
            text="Aguarde um momento",
            bg="#1a1a1a",
            fg="#888",
            font=("Arial", 10)
        ).pack(pady=(5, 20))
        
        # Atualiza para calcular tamanho
        self.aguarde_win.update_idletasks()
        
        # Centraliza na tela (método mais confiável)
        win_width = self.aguarde_win.winfo_reqwidth()
        win_height = self.aguarde_win.winfo_reqheight()
        screen_width = self.aguarde_win.winfo_screenwidth()
        screen_height = self.aguarde_win.winfo_screenheight()
        
        x = (screen_width - win_width) // 2
        y = (screen_height - win_height) // 2
        
        self.aguarde_win.geometry(f"{win_width}x{win_height}+{x}+{y}")
        self.aguarde_win.grab_set()
        
        self.debug_log(f"⏳ Janela de aguarde exibida em {x},{y} ({win_width}x{win_height})")
    
    def calcular_pontuacao(self):
        """Calcula pontuação baseada na atividade do microfone"""
        if not AUDIO_DISPONIVEL:
            return
        
        try:
            if len(self.samples_microfone) < 10:
                self.debug_log("⚠ Amostras insuficientes para calcular pontuação")
                self.pontuacao_final = 0
                return
            
            microfone = np.array(self.samples_microfone)
            
            # Normaliza valores (0-1)
            mic_norm = (microfone - np.min(microfone)) / (np.max(microfone) - np.min(microfone) + 1e-10)
            
            # Calcula métricas de qualidade vocal
            # 1. Consistência (menor variação = melhor)
            consistencia = 1 - np.std(mic_norm)
            
            # 2. Energia média (volume adequado)
            energia_media = np.mean(mic_norm)
            
            # 3. Continuidade (sem muitos silêncios)
            threshold = 0.1
            atividade = np.sum(mic_norm > threshold) / len(mic_norm)
            
            # Pontuação: 40% consistência + 30% energia + 30% atividade
            pontuacao_base = (consistencia * 0.4 + energia_media * 0.3 + atividade * 0.3) * 100
            
            # Limita entre 0 e 100
            self.pontuacao_final = max(0, min(100, pontuacao_base))
            
            self.debug_log(f"🎯 Pontuação calculada: {self.pontuacao_final:.1f}")
            self.debug_log(f"   Consistência: {consistencia:.2f}, Energia: {energia_media:.2f}, Atividade: {atividade:.2f}")
            
            # Fecha janela de aguarde se existir
            if hasattr(self, 'aguarde_win') and self.aguarde_win:
                try:
                    self.aguarde_win.destroy()
                except:
                    pass
            
            # Mostra resultado
            self.root.after(0, self.mostrar_pontuacao)
            
        except Exception as e:
            self.debug_log(f"❌ Erro ao calcular pontuação: {e}")
            self.pontuacao_final = 0
    
    def mostrar_pontuacao(self):
        """Exibe a pontuação em uma janela de diálogo"""
        pontos = int(self.pontuacao_final)
        
        # Determina emoji e mensagem baseado na pontuação
        if pontos >= 90:
            emoji = "🌟"
            mensagem = "PERFEITO!"
            cor = "#FFD700"
        elif pontos >= 75:
            emoji = "🎉"
            mensagem = "EXCELENTE!"
            cor = "#4CAF50"
        elif pontos >= 60:
            emoji = "👍"
            mensagem = "MUITO BOM!"
            cor = "#2196F3"
        elif pontos >= 40:
            emoji = "😊"
            mensagem = "BOM!"
            cor = "#FF9800"
        else:
            emoji = "💪"
            mensagem = "CONTINUE PRATICANDO!"
            cor = "#f44336"
        
        # Determina janela pai (preferência para video_window)
        parent = self.video_window if (hasattr(self, 'video_window') and self.video_window and self.video_window.winfo_exists()) else self.root
        
        # Cria janela de pontuação
        pontuacao_win = tk.Toplevel(parent)
        pontuacao_win.title("Pontuação Karaoke")
        pontuacao_win.configure(bg="#1a1a1a")
        pontuacao_win.transient(parent)
        pontuacao_win.resizable(False, False)
        
        # Força a janela a ficar sempre no topo
        pontuacao_win.attributes('-topmost', True)
        
        # Conteúdo
        tk.Label(
            pontuacao_win,
            text=emoji,
            bg="#1a1a1a",
            font=("Arial", 60)
        ).pack(pady=(20, 10))
        
        tk.Label(
            pontuacao_win,
            text=mensagem,
            bg="#1a1a1a",
            fg=cor,
            font=("Arial", 18, "bold")
        ).pack(pady=5)
        
        tk.Label(
            pontuacao_win,
            text=f"{pontos} pontos",
            bg="#1a1a1a",
            fg="white",
            font=("Arial", 32, "bold")
        ).pack(pady=10)
        
        # Barra de progresso visual
        progress_frame = tk.Frame(pontuacao_win, bg="#333", width=300, height=30)
        progress_frame.pack(pady=20)
        progress_frame.pack_propagate(False)
        
        progress_bar = tk.Frame(
            progress_frame,
            bg=cor,
            width=int(300 * pontos / 100),
            height=30
        )
        progress_bar.pack(side=tk.LEFT)
        
        # Botão fechar
        tk.Button(
            pontuacao_win,
            text="OK",
            command=pontuacao_win.destroy,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold"),
            cursor="hand2",
            padx=30,
            pady=10
        ).pack(pady=(0, 20))
        
        # Atualiza para calcular tamanho
        pontuacao_win.update_idletasks()
        
        # Centraliza na tela (método mais confiável)
        win_width = pontuacao_win.winfo_reqwidth()
        win_height = pontuacao_win.winfo_reqheight()
        screen_width = pontuacao_win.winfo_screenwidth()
        screen_height = pontuacao_win.winfo_screenheight()
        
        x = (screen_width - win_width) // 2
        y = (screen_height - win_height) // 2
        
        pontuacao_win.geometry(f"{win_width}x{win_height}+{x}+{y}")
        pontuacao_win.grab_set()
        
        self.debug_log(f"📊 Pontuação exibida: {pontos} - {mensagem} em {x},{y}")
        
        self.debug_log(f"📊 Pontuação exibida: {pontos} - {mensagem}")
    
    def update_timer(self):
        """Atualiza o timer da interface"""
        if self.is_playing and self.player and self.player.is_playing():
            try:
                current_time = self.player.get_time() / 1000.0  # Converte de ms para segundos
                current_str = time.strftime('%M:%S', time.gmtime(current_time))
                duration_str = time.strftime('%M:%S', time.gmtime(self.duration))
                self.time_label.config(text=f"{current_str} / {duration_str}")
                
                # Atualizar slider horizontal SOMENTE se usuário não estiver arrastando
                if hasattr(self, 'seek_slider') and self.duration > 0 and not self.is_seeking:
                    progress = (current_time / self.duration) * 100.0
                    self.seek_slider.set(progress)
                
                # Detectar fim da música (faltando menos de 0.5 segundo)
                if self.duration > 0 and (self.duration - current_time) < 0.5:
                    # Calcula pontuação apenas uma vez por música
                    if AUDIO_DISPONIVEL and len(self.samples_microfone) > 10 and not getattr(self, 'pontuacao_exibida', False):
                        self.pontuacao_exibida = True
                        self.debug_log(f"🎵 Música terminou - Calculando pontuação com {len(self.samples_microfone)} amostras")
                        # Mostra mensagem de aguarde
                        self.root.after(100, self.mostrar_aguarde_pontuacao)
                        # Calcula pontuação após pequeno delay
                        self.root.after(500, self.calcular_pontuacao)
                        
                        # Se estiver no modo evento, agenda finalização após exibir pontuação
                        if self.modo_evento_ativo and MODO_EVENTO_DISPONIVEL:
                            self.root.after(2000, self.finalizar_musica_evento)
            except:
                pass
        elif self.video_file and hasattr(self, 'time_label'):
            duration_str = time.strftime('%M:%S', time.gmtime(self.duration))
            self.time_label.config(text=f"00:00 / {duration_str}")
        
        if not self.force_quit:
            self.root.after(100, self.update_timer)


    def carregar_catalogo(self):
        """Limpa o catálogo e importa o CSV selecionado para o banco de dados."""
        try:
            from tkinter import filedialog, messagebox
            csv_path = filedialog.askopenfilename(
                title="Selecione o arquivo CSV do catálogo",
                filetypes=[("CSV", "*.csv"), ("Todos os arquivos", "*.*")]
            )
            if not csv_path:
                self.debug_log("[CATALOGO] Nenhum arquivo CSV selecionado.")
                return
            
            self.debug_log(f"[CATALOGO] CSV selecionado: {csv_path}")
            db = KaraokeDatabase()
            
            # Pergunta se deseja limpar o catálogo antes
            if messagebox.askyesno("Limpar Catálogo", 
                                "Deseja limpar o catálogo antes de importar?\n(Isso removerá todas as músicas do catálogo atual)"):
                self.debug_log("[CATALOGO] Limpando catálogo antes de importar.")
                db.limpar_catalogo()
            
            self.show_progress("Importando catálogo CSV...")
            self.root.update()
            
            # Importa o CSV
            num = db.importar_catalogo_csv(csv_path)
            
            self.hide_progress()
            self.debug_log(f"[CATALOGO] Importação concluída. {num} músicas importadas.")
            messagebox.showinfo("Catálogo", f"Catálogo CSV importado com sucesso!\n{num} músicas adicionadas.")
        
        except FileNotFoundError as e:
            self.debug_log(f"[CATALOGO] ERRO: {e}")
            messagebox.showerror("Erro", str(e))
        
        except Exception as e:
            self.debug_log(f"[CATALOGO] ERRO: {e}")
            self.hide_progress()
            messagebox.showerror("Erro", f"Erro ao importar catálogo CSV:\n{e}")


# NO FINAL DO ARQUIVO, modifique a parte principal:
if __name__ == "__main__":
    root = tk.Tk()
    app = KaraokePlayer(root)
    
    # Configurar protocolo para fechamento da janela (com confirmação)
    root.protocol("WM_DELETE_WINDOW", lambda: app.fechar_aplicacao(confirmar=True))
    
    # Tratar exceções não capturadas
    def handle_exception(exc_type, exc_value, exc_traceback):
        app.debug_log(f"❌ EXCEÇÃO NÃO CAPTURADA: {exc_type.__name__}: {exc_value}")
        app.fechar_aplicacao()
    
    import sys
    sys.excepthook = handle_exception
    
    # Tratar Ctrl+C no terminal também
    import signal
    def signal_handler(sig, frame):
        app.debug_log("⚠️ Sinal Ctrl+C recebido")
        app.fechar_aplicacao()
    
    try:
        signal.signal(signal.SIGINT, signal_handler)
    except:
        pass  # Pode não funcionar em todos os sistemas
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.fechar_aplicacao()
    except Exception as e:
        app.debug_log(f"❌ ERRO NO MAINLOOP: {e}")
        app.fechar_aplicacao()