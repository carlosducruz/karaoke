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

try:
    from karaoke_evento import ModoEventoWindow
    from karaoke_database import KaraokeDatabase
    MODO_EVENTO_DISPONIVEL = True
except ImportError:
    MODO_EVENTO_DISPONIVEL = False
    print("AVISO: Módulos de evento não encontrados. Modo Evento desabilitado.")

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
                resposta = messagebox.askyesno(
                    "Música Encontrada",
                    f"🎤 Cantor: {cantor}\n🎵 Música: {musica}\n🔢 Código: {codigo}\n\n"
                    f"📁 Arquivo: {os.path.basename(arquivo_encontrado)}\n\n"
                    "Deseja carregar e iniciar esta música?"  # TEXTO ALTERADO
                )
                
                if resposta:
                    # Carrega o arquivo
                    self.video_file = arquivo_encontrado
                    self.processed_file = arquivo_encontrado
                    self.pitch_shift = 0
                    self.pitch_label.config(text="0")
                    # Atualiza o pitch_var do Spinbox também, se existir
                    if hasattr(self, 'pitch_var'):
                        self.pitch_var.set(0)
                    
                    self.file_label.config(text=f"{codigo} - {musica}")
                    
                    # Obtém informações do vídeo
                    try:
                        result = subprocess.run([
                            'ffprobe', '-v', 'quiet', '-print_format', 'json',
                            '-show_format', '-show_streams', arquivo_encontrado
                        ], capture_output=True, text=True, check=True)
                        
                        info = json.loads(result.stdout)
                        for stream in info['streams']:
                            if stream['codec_type'] == 'video':
                                self.fps = eval(stream.get('r_frame_rate', '30/1'))
                                self.width = stream['width']
                                self.height = stream['height']
                                break
                        self.duration = float(info['format']['duration'])
                    except:
                        pass
                    
                    self.show_first_frame()
                    self.status_label.config(text=f"✓ {musica} carregada! Iniciando...")
                    busca_win.destroy()
                    
                    # Adiciona à playlist do modo normal COM NOME DA MÚSICA
                    if not self.modo_evento_ativo:
                        self.playlist_items.append({
                            'arquivo_path': arquivo_encontrado,
                            'participante_nome': cantor,
                            'musica_nome': musica,
                            'tom_ajuste': 0,
                            'ja_tocou': False,
                            'ordem': len(self.playlist_items) + 1
                        })
                        self.atualizar_playlist_visual()
                    
                    # AUTOPLAY: Inicia reprodução automaticamente
                    self.debug_log(f"🎬 Música do catálogo carregada - iniciando reprodução automática...")
                    self.root.after(500, self.play)
            else:
                messagebox.showerror(
                    "Arquivo não encontrado",
                    f"Não foi possível encontrar o arquivo para o código: {codigo}\n\n"
                    f"Procurando por: '{codigo}.mp4' em C:\\temp\\musicas"
                )

    def __init__(self, root):
        self.root = root
        self.root.title("Karaoke Player - MP4")
        self.root.geometry("1200x780")
        self.root.configure(bg="#1a1a1a")
        self.force_quit = False  # Adicione esta flag

        # LOG INICIAL
        self.debug_log("=" * 60)
        self.debug_log("KARAOKE PLAYER INICIADO")
        self.debug_log(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.debug_log("=" * 60)
        
        # VLC instances
        self.vlc_instance = vlc.Instance('--no-xlib')
        self.player = self.vlc_instance.media_player_new()
        
        self.video_file = None
        self.processed_file = None
        self.pitch_shift = 0
        self.is_playing = False
        self.duration = 0
        self.fps = 30
        self.width = 0
        self.height = 0
        self.video_thread = None
        self.frame_process = None
        self.processing_pitch = False
        
        # Modo Evento
        self.modo_evento_ativo = False
        self.evento_id_atual = None
        self.musica_atual_evento = None
        self.playlist_items = []
        self.selected_playlist_index = None
        
        self.setup_ui()
        self.update_timer()
 


        
    def fechar_aplicacao(self, confirmar=True):

        """Fecha a aplicação com opção de confirmação"""
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
                return
                
        """Fecha a aplicação de forma limpa, liberando todos os recursos"""
        if self.force_quit:
            return
            
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
        
        # Parar processo ffmpeg de vídeo
        if hasattr(self, 'frame_process') and self.frame_process:
            try:
                self.debug_log("🛑 Finalizando processo ffmpeg de vídeo...")
                self.frame_process.kill()
                if hasattr(self.frame_process, 'wait'):
                    self.frame_process.wait(timeout=1)
                self.debug_log("✅ Processo ffmpeg finalizado")
            except Exception as e:
                self.debug_log(f"⚠️ Erro ao parar ffmpeg: {e}")
        
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
                resposta = messagebox.askyesno(
                    "Música Encontrada",
                    f"🎤 Cantor: {cantor}\n🎵 Música: {musica}\n🔢 Código: {codigo}\n\n"
                    f"📁 Arquivo: {os.path.basename(arquivo_encontrado)}\n\n"
                    "Deseja carregar esta música?"
                )
                
                if resposta:
                    # Carrega o arquivo
                    self.video_file = arquivo_encontrado
                    self.processed_file = arquivo_encontrado
                    self.pitch_shift = 0
                    self.pitch_label.config(text="0")
                    self.file_label.config(text=f"{codigo} - {musica}")
                    self.show_first_frame()
                    self.status_label.config(text=f"✅ Música carregada: {musica}")
                    busca_win.destroy()
                    
                    # Adiciona à playlist do modo normal COM NOME DA MÚSICA
                    if not self.modo_evento_ativo:
                        self.playlist_items.append({
                            'arquivo_path': arquivo_encontrado,
                            'participante_nome': cantor,  # Nome do cantor
                            'musica_nome': musica,  # NOME DA MÚSICA
                            'tom_ajuste': 0,
                            'ja_tocou': False,
                            'ordem': len(self.playlist_items) + 1
                        })
                        self.atualizar_playlist_visual()
            else:
                messagebox.showerror( +
                    "Arquivo não encontrado",
                    f"Não foi possível encontrar o arquivo para o código: {codigo}\n\n"
                    f"Procurando por: '{codigo}.mp4' em C:\\temp\\musicas"
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
        """Busca arquivo MP4 na pasta C:\\temp\\musicas e subpastas"""
        base_path = r"C:\\temp\\musicas"
        
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
                f"A pasta C:\\temp\\musicas não foi encontrada.\nVerifique se ela existe."
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
        
        # Container principal
        main_container = tk.Frame(self.root, bg="#1a1a1a")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # COLUNA ESQUERDA (70%)
        left_frame = tk.Frame(main_container, bg="#1a1a1a")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Vídeo (menor)
        video_frame = tk.Frame(left_frame, bg="#000000", width=480, height=270)
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

        # Progresso (personalizado, sempre visível)
        self.progress_frame = tk.Frame(left_frame, bg="#232323", bd=1, relief=tk.SUNKEN)
        self.progress_frame.pack(fill=tk.X, padx=5, pady=(6, 10))

        self.progress_label = tk.Label(
            self.progress_frame,
            text="",
            bg="#232323",
            fg="#00e676",
            font=("Arial", 9, "bold")
        )
        self.progress_label.pack(pady=(2, 0))

        self.progress_canvas = tk.Canvas(
            self.progress_frame,
            width=260,
            height=18,
            bg="#333",
            highlightthickness=1,
            highlightbackground="#444"
        )
        self.progress_canvas.pack(pady=(2, 6))
        self.progress_bar = self.progress_canvas.create_rectangle(
            0, 0, 0, 18, fill="#00e676", width=0
        )
        self.progress_animation_running = False
        



        # Frame agrupador estilizado para os botões principais
        botoes_outer_frame = tk.Frame(left_frame, bg="#23233a", bd=3, relief=tk.RIDGE, highlightbackground="#2196F3", highlightcolor="#2196F3", highlightthickness=2)
        botoes_outer_frame.pack(pady=12, fill=tk.X)

        botoes_frame = tk.Frame(botoes_outer_frame, bg="#23233a")
        botoes_frame.pack(padx=10, pady=10, fill=tk.X)

        btn_width = 22
        btn_height = 2
        btn_padx = 8
        btn_pady = 8

        # Botões principais lado a lado, mesma altura
        if MODO_EVENTO_DISPONIVEL:
            tk.Button(
                botoes_frame,
                text="🎉 MODO EVENTO",
                command=self.abrir_modo_evento,
                bg="#9C27B0",
                fg="white",
                font=("Arial", 10, "bold"),
                cursor="hand2",
                width=btn_width,
                height=btn_height
            ).pack(side=tk.LEFT, padx=btn_padx, pady=btn_pady)


        tk.Button(
            botoes_frame,
            text="🔎 Buscar no Catálogo",
            command=self.abrir_busca_catalogo,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            width=btn_width,
            height=btn_height
        ).pack(side=tk.LEFT, padx=btn_padx, pady=btn_pady)

        tk.Button(
            botoes_frame,
            text="📁 Carregar Qualquer MP4",
            command=self.load_file,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            width=btn_width,
            height=btn_height
        ).pack(side=tk.LEFT, padx=btn_padx, pady=btn_pady)

        tk.Button(
            botoes_frame,
            text="📚 Importar Catálogo (CSV)",
            command=self.carregar_catalogo,
            bg="#FF9800",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            width=btn_width,
            height=btn_height
        ).pack(side=tk.LEFT, padx=btn_padx, pady=btn_pady)


        # Frame horizontal para pitch e controles de reprodução
        pitch_player_row = tk.Frame(left_frame, bg="#1a1a1a")
        pitch_player_row.pack(pady=(8, 16), fill=tk.X)

        # Altura e largura mínimas para controles de pitch e player
        control_height = 120  # altura aumentada para caber todos os controles
        pitch_width = int(410 * 0.8)   # 20% menor
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

        # Espaçamento interno
        pitch_inner = tk.Frame(pitch_frame, bg="#181828")
        pitch_inner.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        # Título e dica
        tk.Label(
            pitch_inner,
            text="Controle de Tom",
            bg="#181828",
            fg="#4CAF50",
            font=("Arial", 12, "bold")
        ).pack(anchor=tk.W)
        tk.Label(
            pitch_inner,
            text="Ajuste o tom da música selecionada em semitons.",
            bg="#181828",
            fg="#BBB",
            font=("Arial", 9, "italic")
        ).pack(anchor=tk.W, pady=(0, 6))

        pitch_ctrl_frame = tk.Frame(pitch_inner, bg="#181828")
        pitch_ctrl_frame.pack(pady=2, fill=tk.X)

        # Semitons label
        tk.Label(
            pitch_ctrl_frame,
            text="Semitons:",
            bg="#181828",
            fg="white",
            font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT, padx=(0, 6))

        self.pitch_var = tk.IntVar(value=0)
        pitch_spin = tk.Spinbox(
            pitch_ctrl_frame,
            from_=-12,
            to=12,
            textvariable=self.pitch_var,
            width=4,
            font=("Arial", 16, "bold"),
            justify="center",
            bg="#222",
            fg="#4CAF50",
            insertbackground="#4CAF50",
            relief=tk.FLAT
        )
        pitch_spin.pack(side=tk.LEFT, padx=4)

        # Valor do tom destacado
        self.pitch_label = tk.Label(
            pitch_ctrl_frame,
            text="0",
            bg="#222",
            fg="#00e676",
            font=("Arial", 18, "bold"),
            width=4,
            relief=tk.SUNKEN,
            bd=2
        )
        self.pitch_label.pack(side=tk.LEFT, padx=8)

        def aplicar_tom():
            novo_tom = self.pitch_var.get()
            if novo_tom != self.pitch_shift:
                self.change_pitch(novo_tom - self.pitch_shift)

        tk.Button(
            pitch_ctrl_frame,
            text=" OK ",
            command=aplicar_tom,
            bg="#2196F3",
            fg="white",
            font=("Arial", 11, "bold"),
            width=7,
            cursor="hand2",
            pady=7,
            relief=tk.RAISED,
            activebackground="#1976D2"
        ).pack(side=tk.LEFT, padx=8)

        # Dica de uso
        tk.Label(
            pitch_inner,
            text="Dica: Use valores negativos para abaixar e positivos para subir o tom.",
            bg="#181828",
            fg="#888",
            font=("Arial", 8, "italic")
        ).pack(anchor=tk.W, pady=(8, 0))


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

        # Espaçamento interno
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
            player_inner,
            text="▶ PLAY",
            command=self.play,
            bg="#4CAF50",
            fg="white",
            **btn_style
        )
        self.play_btn.pack(side=tk.LEFT, padx=5)

        self.pause_btn = tk.Button(
            player_inner,
            text="⏸ PAUSA",
            command=self.pause,
            bg="#FF9800",
            fg="white",
            **btn_style
        )
        self.pause_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(
            player_inner,
            text="⏹ PARAR",
            command=self.stop,
            bg="#f44336",
            fg="white",
            **btn_style
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        # Botão Próxima
        btn_proxima_style = btn_style.copy()
        btn_proxima_style["width"] = 13  # aumentar largura para caber "PRÓXIMA"
        tk.Button(
            player_inner,
            text="⏭ PRÓXIMA",
            command=self.tocar_proxima_musica,
            bg="#673AB7",
            fg="white",
            **btn_proxima_style
        ).pack(side=tk.LEFT, padx=5)
        
        # Status
        status_frame = tk.Frame(left_frame, bg="#1a1a1a")
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_label = tk.Label(
            status_frame,
            text="Pronto",
            bg="#1a1a1a",
            fg="#888888",
            font=("Arial", 8)
        )
        self.status_label.pack()
        
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
        
        self.debug_log("✓ Interface configurada")
    
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
        
        # Informações adicionais (tom, arquivo)
        info_adicional = []
        
        if item.get('tom_ajuste', 0) != 0:
            info_adicional.append(f"Tom: {item['tom_ajuste']:+d}")
        
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
        
        # Se não está em modo evento, ativa o modo evento
        if not self.modo_evento_ativo and MODO_EVENTO_DISPONIVEL:
            # Pede para ativar modo evento
            if messagebox.askyesno("Modo Evento", 
                                  "Esta música pertence a um evento.\n\nDeseja ativar o Modo Evento para tocar?"):
                # Aqui você pode precisar de uma lógica para encontrar/definir o evento_id
                # Por enquanto, vou assumir que o item tem evento_id
                if 'evento_id' in item:
                    self.modo_evento_ativo = True
                    self.evento_id_atual = item['evento_id']
                    self.iniciar_modo_evento(self.evento_id_atual, item)
                    return
            else:
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
                ], capture_output=True, text=True, check=True)
                
                info = json.loads(result.stdout)
                for stream in info['streams']:
                    if stream['codec_type'] == 'video':
                        self.fps = eval(stream.get('r_frame_rate', '30/1'))
                        self.width = stream['width']
                        self.height = stream['height']
                        break
                self.duration = float(info['format']['duration'])
            except:
                pass
            
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
    
    def abrir_modo_evento(self):
        if not MODO_EVENTO_DISPONIVEL:
            messagebox.showerror("Erro", "Módulos de evento não encontrados!")
            return
        self.debug_log("🎉 Abrindo Modo Evento...")
        ModoEventoWindow(self.root, self)
    
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
            ], capture_output=True, text=True, check=True)
            
            info = json.loads(result.stdout)
            for stream in info['streams']:
                if stream['codec_type'] == 'video':
                    self.fps = eval(stream.get('r_frame_rate', '30/1'))
                    self.width = stream['width']
                    self.height = stream['height']
                    break
            self.duration = float(info['format']['duration'])
        except:
            pass
        
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
        tempo = self.player.get_time() / 1000.0
        db.marcar_musica_tocada(self.musica_atual_evento['id'], tempo)
        pontos = db.calcular_pontuacao(self.musica_atual_evento['id'])
        
        self.carregar_playlist_evento(self.evento_id_atual)
        
        messagebox.showinfo("Pontuação", f"🎤 {self.musica_atual_evento['participante_nome']}\n\n⭐ {pontos} pontos!\n\nTempo: {tempo:.1f}s")
        
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
                ], capture_output=True, text=True, check=True)
                
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
                self.show_first_frame()
                self.status_label.config(text="✓ Carregado! Iniciando reprodução...")
                
                # AUTOPLAY: Iniciar reprodução automaticamente após carregar
                self.debug_log("🎬 Arquivo carregado - iniciando reprodução automática...")
                self.root.after(500, self.play)  # Aguarda 500ms e inicia o play
                
            except Exception as e:
                self.debug_log(f"❌ Erro ao carregar arquivo: {e}")
                messagebox.showerror("Erro", str(e))
    
    def show_first_frame(self):
        try:
            temp = tempfile.mktemp(suffix='.jpg')
            subprocess.run(['ffmpeg', '-i', self.video_file, '-vframes', '1', '-f', 'image2', temp], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            img = Image.open(temp)
            self.display_frame(img)
            os.unlink(temp)
        except:
            pass
    
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
        self.pitch_label.config(text=f"{self.pitch_shift:+d}" if self.pitch_shift != 0 else "0")

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
        
        if self.player.get_state() == vlc.State.Paused:
            self.player.play()
            self.is_playing = True
            self.start_video_thread()
            return
        
        media = self.vlc_instance.media_new(self.processed_file)
        self.player.set_media(media)
        self.player.play()
        self.is_playing = True
        self.start_video_thread()
    
    def start_video_thread(self):
        if self.video_thread and self.video_thread.is_alive():
            return
        self.video_thread = threading.Thread(target=self.play_video, daemon=True)
        self.video_thread.start()
    
    def play_video(self):
        cmd = ['ffmpeg', '-i', self.processed_file, '-f', 'image2pipe', '-pix_fmt', 'rgb24', '-vcodec', 'rawvideo', '-']
        self.frame_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**8)
        size = self.width * self.height * 3
        
        while self.is_playing:
            try:
                state = self.player.get_state()
                if state in [vlc.State.Ended, vlc.State.Stopped]:
                    if self.modo_evento_ativo:
                        self.root.after(0, self.finalizar_musica_evento)
                    else:
                        self.root.after(0, self.stop)
                    break
                
                raw = self.frame_process.stdout.read(size)
                if len(raw) != size:
                    break
                
                import array
                data = array.array('B', raw)
                img = Image.frombytes('RGB', (self.width, self.height), bytes(data))
                self.root.after(0, self.display_frame, img)
                time.sleep(1.0 / self.fps)
            except:
                break
        
        if self.frame_process:
            self.frame_process.kill()
            self.frame_process = None
    
    def display_frame(self, img):
        try:
            w, h = img.size
            # Ajustar para o novo tamanho do video_frame (480x270)
            scale = min(480/w, 270/h)
            nw = int(w * scale)
            nh = int(h * scale)
            img = img.resize((nw, nh), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image=img)
            self.video_label.imgtk = photo
            self.video_label.configure(image=photo, text="")
        except:
            pass
    
    def pause(self):
        if self.is_playing:
            self.player.pause()
            self.is_playing = False


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

    def stop(self):
        self.player.stop()
        self.is_playing = False
        if self.frame_process:
            self.frame_process.kill()
            self.frame_process = None
        if self.video_file:
            self.show_first_frame()
    
    def update_timer(self):
        if self.is_playing and self.player.get_state() == vlc.State.Playing:
            t = self.player.get_time() / 1000.0
            self.time_label.config(text=f"{time.strftime('%M:%S', time.gmtime(t))} / {time.strftime('%M:%S', time.gmtime(self.duration))}")
        elif self.video_file:
            self.time_label.config(text=f"00:00 / {time.strftime('%M:%S', time.gmtime(self.duration))}")
        self.root.after(100, self.update_timer)


# NO FINAL DO ARQUIVO, modifique a parte principal:
if __name__ == "__main__":
    root = tk.Tk()
    app = KaraokePlayer(root)
    
    # Configurar protocolo para fechamento da janela
    root.protocol("WM_DELETE_WINDOW", app.fechar_aplicacao)
    
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