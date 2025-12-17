import tkinter as tk
from tkinter import filedialog, messagebox
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
    def __init__(self, root):
        self.root = root
        self.root.title("Karaoke Player - MP4")
        self.root.geometry("1200x780")
        self.root.configure(bg="#1a1a1a")
        
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
        
    def setup_ui(self):
        self.debug_log("Configurando interface...")
        
        # Container principal
        main_container = tk.Frame(self.root, bg="#1a1a1a")
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # COLUNA ESQUERDA (70%)
        left_frame = tk.Frame(main_container, bg="#1a1a1a")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Vídeo
        video_frame = tk.Frame(left_frame, bg="#000000", width=616, height=400)
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
        
        # Botão Modo Evento
        if MODO_EVENTO_DISPONIVEL:
            tk.Button(
                left_frame,
                text="🎉 MODO EVENTO",
                command=self.abrir_modo_evento,
                bg="#9C27B0",
                fg="white",
                font=("Arial", 11, "bold"),
                cursor="hand2",
                padx=15,
                pady=8
            ).pack(pady=5)
        
        # Botão Carregar
        tk.Button(
            left_frame,
            text="📁 Carregar MP4",
            command=self.load_file,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15,
            pady=6
        ).pack(pady=5)
        
        # Controle de tom
        pitch_frame = tk.Frame(left_frame, bg="#1a1a1a")
        pitch_frame.pack(pady=5)
        
        tk.Label(
            pitch_frame, 
            text="Tom:", 
            bg="#1a1a1a", 
            fg="white",
            font=("Arial", 9, "bold")
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            pitch_frame,
            text="🔽 -1",
            command=lambda: self.change_pitch(-1),
            bg="#f44336",
            fg="white",
            font=("Arial", 8, "bold"),
            width=5,
            cursor="hand2",
            pady=3
        ).pack(side=tk.LEFT, padx=2)
        
        self.pitch_label = tk.Label(
            pitch_frame,
            text="0",
            bg="#1a1a1a",
            fg="#4CAF50",
            font=("Arial", 14, "bold"),
            width=3
        )
        self.pitch_label.pack(side=tk.LEFT, padx=8)
        
        tk.Button(
            pitch_frame,
            text="🔼 +1",
            command=lambda: self.change_pitch(1),
            bg="#2196F3",
            fg="white",
            font=("Arial", 8, "bold"),
            width=5,
            cursor="hand2",
            pady=3
        ).pack(side=tk.LEFT, padx=2)
        
        # Controles
        player_frame = tk.Frame(left_frame, bg="#1a1a1a", pady=10)
        player_frame.pack(pady=10)
        
        btn_style = {
            "font": ("Arial", 11, "bold"),
            "cursor": "hand2",
            "width": 10,
            "height": 2
        }
        
        self.play_btn = tk.Button(
            player_frame,
            text="▶ PLAY",
            command=self.play,
            bg="#4CAF50",
            fg="white",
            **btn_style
        )
        self.play_btn.pack(side=tk.LEFT, padx=5)
        
        self.pause_btn = tk.Button(
            player_frame,
            text="⏸ PAUSA",
            command=self.pause,
            bg="#FF9800",
            fg="white",
            **btn_style
        )
        self.pause_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(
            player_frame,
            text="⏹ STOP",
            command=self.stop,
            bg="#f44336",
            fg="white",
            **btn_style
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Botões de controle da playlist
        playlist_controls = tk.Frame(left_frame, bg="#1a1a1a")
        playlist_controls.pack(pady=5)
        
        btn_style_playlist = {
            "font": ("Arial", 9, "bold"),
            "cursor": "hand2",
            "padx": 10,
            "pady": 5
        }
        
        tk.Button(
            playlist_controls,
            text="▶ Tocar Selecionada",
            command=self.tocar_musica_selecionada,
            bg="#2196F3",
            fg="white",
            **btn_style_playlist
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            playlist_controls,
            text="⏭ Próxima",
            command=self.tocar_proxima_musica,
            bg="#673AB7",
            fg="white",
            **btn_style_playlist
        ).pack(side=tk.LEFT, padx=2)
        
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
        
        # Progresso
        self.progress_frame = tk.Frame(status_frame, bg="#1a1a1a")
        self.progress_label = tk.Label(
            self.progress_frame,
            text="Processando...",
            bg="#1a1a1a",
            fg="#4CAF50",
            font=("Arial", 7)
        )
        self.progress_label.pack()
        
        self.progress_canvas = tk.Canvas(
            self.progress_frame,
            width=250,
            height=15,
            bg="#2d2d2d",
            highlightthickness=0
        )
        self.progress_canvas.pack(pady=3)
        self.progress_bar = self.progress_canvas.create_rectangle(
            0, 0, 0, 15, fill="#4CAF50", width=0
        )
        self.progress_animation_running = False
        
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
        is_selected = (index == self.selected_playlist_index)
        is_playing = (self.modo_evento_ativo and 
                     self.musica_atual_evento and 
                     item['id'] == self.musica_atual_evento['id'])
        
        if is_playing:
            bg = "#1a5a1a"
        elif is_selected:
            bg = "#3a3a5a"
        elif item['ja_tocou']:
            bg = "#2a2a2a"
        else:
            bg = "#1a1a1a"
        
        frame = tk.Frame(self.playlist_inner_frame, bg=bg, relief=tk.RAISED, bd=1, cursor="hand2")
        frame.pack(fill=tk.X, pady=1, padx=2)
        
        def selecionar_e_tocar(event):
            self.selected_playlist_index = index
            self.atualizar_playlist_visual()
            self.tocar_musica_playlist(index)
        
        frame.bind("<Button-1>", selecionar_e_tocar)
        
        # Número
        num = tk.Label(frame, text=f"#{item['ordem']}", bg=bg, fg="#888" if item['ja_tocou'] else "white", font=("Arial", 8, "bold"), width=3)
        num.pack(side=tk.LEFT, padx=3, pady=3)
        num.bind("<Button-1>", selecionar_e_tocar)
        
        # Status
        if is_playing:
            status = "▶"
            cor = "#4CAF50"
        elif item['ja_tocou']:
            status = "✓"
            cor = "#666"
        else:
            status = "○"
            cor = "#FFA500"
        
        st = tk.Label(frame, text=status, bg=bg, fg=cor, font=("Arial", 10, "bold"), width=2)
        st.pack(side=tk.LEFT, padx=2)
        st.bind("<Button-1>", selecionar_e_tocar)
        
        # Info
        info = tk.Frame(frame, bg=bg)
        info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=3)
        info.bind("<Button-1>", selecionar_e_tocar)
        
        nome = os.path.basename(item['arquivo_path'])
        if len(nome) > 25:
            nome = nome[:22] + "..."
        
        arq = tk.Label(info, text=nome, bg=bg, fg="white" if not item['ja_tocou'] else "#888", font=("Arial", 9, "bold" if is_selected else "normal"))
        arq.pack(anchor=tk.W)
        arq.bind("<Button-1>", selecionar_e_tocar)
        
        part = f"🎤 {item['participante_nome']}"
        if item['tom_ajuste'] != 0:
            part += f" | Tom: {item['tom_ajuste']:+d}"
        
        p = tk.Label(info, text=part, bg=bg, fg="#888" if item['ja_tocou'] else "#AAA", font=("Arial", 7))
        p.pack(anchor=tk.W)
        p.bind("<Button-1>", selecionar_e_tocar)
    
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
        
        if self.selected_playlist_index is None:
            next_index = 0
        else:
            next_index = (self.selected_playlist_index + 1) % len(self.playlist_items)
        
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
                self.file_label.config(text=os.path.basename(path))
                self.show_first_frame()
                self.status_label.config(text="✓ Pronto!")
            except Exception as e:
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
        self.progress_frame.pack()
        self.progress_animation_running = True
        self.animate_progress()
    
    def hide_progress(self):
        self.progress_animation_running = False
        self.progress_frame.pack_forget()
    
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
            scale = min(616/w, 400/h)
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

if __name__ == "__main__":
    root = tk.Tk()
    app = KaraokePlayer(root)
    root.mainloop()