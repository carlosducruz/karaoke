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

class KaraokePlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("Karaoke Player - MP4")
        self.root.geometry("900x780")
        self.root.configure(bg="#1a1a1a")
        
        # LOG INICIAL
        self.debug_log("=" * 60)
        self.debug_log("KARAOKE PLAYER INICIADO")
        self.debug_log(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.debug_log(f"Diretório atual: {os.getcwd()}")
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
        self.processing_pitch = False  # FLAG PARA CONTROLAR PROCESSAMENTO
        
        self.setup_ui()
        self.update_timer()
        
    def setup_ui(self):
        self.debug_log("Configurando interface gráfica...")
        
        # Frame do vídeo
        video_frame = tk.Frame(self.root, bg="#000000", width=880, height=450)
        video_frame.pack(padx=10, pady=5)
        video_frame.pack_propagate(False)
        
        self.video_label = tk.Label(
            video_frame, 
            bg="#000000", 
            text="🎬 Carregue um vídeo MP4 para começar", 
            fg="#666666", 
            font=("Arial", 14)
        )
        self.video_label.pack(expand=True)
        
        # Frame de info
        info_frame = tk.Frame(self.root, bg="#2d2d2d", pady=5)
        info_frame.pack(fill=tk.X, padx=10)
        
        self.file_label = tk.Label(
            info_frame, 
            text="Nenhum arquivo carregado", 
            bg="#2d2d2d", 
            fg="white",
            font=("Arial", 10)
        )
        self.file_label.pack()
        
        # Timer
        self.time_label = tk.Label(
            info_frame,
            text="00:00 / 00:00",
            bg="#2d2d2d",
            fg="#4CAF50",
            font=("Arial", 9, "bold")
        )
        self.time_label.pack()
        
        # Botão carregar
        load_btn = tk.Button(
            self.root,
            text="📁 Carregar MP4",
            command=self.load_file,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=15,
            pady=8
        )
        load_btn.pack(pady=10)
        
        # Controle de tom
        pitch_frame = tk.Frame(self.root, bg="#1a1a1a")
        pitch_frame.pack(pady=5)
        
        tk.Label(
            pitch_frame, 
            text="Controle de Tom:", 
            bg="#1a1a1a", 
            fg="white",
            font=("Arial", 10, "bold")
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            pitch_frame,
            text="🔽 -1",
            command=lambda: self.change_pitch(-1),
            bg="#f44336",
            fg="white",
            font=("Arial", 9, "bold"),
            width=6,
            cursor="hand2",
            pady=5
        ).pack(side=tk.LEFT, padx=3)
        
        self.pitch_label = tk.Label(
            pitch_frame,
            text="0",
            bg="#1a1a1a",
            fg="#4CAF50",
            font=("Arial", 16, "bold"),
            width=4
        )
        self.pitch_label.pack(side=tk.LEFT, padx=10)
        
        tk.Button(
            pitch_frame,
            text="🔼 +1",
            command=lambda: self.change_pitch(1),
            bg="#2196F3",
            fg="white",
            font=("Arial", 9, "bold"),
            width=6,
            cursor="hand2",
            pady=5
        ).pack(side=tk.LEFT, padx=3)
        
        # Nota sobre pitch shift
        tk.Label(
            pitch_frame,
            text="(requer reprocessamento)",
            bg="#1a1a1a",
            fg="#888888",
            font=("Arial", 8)
        ).pack(side=tk.LEFT, padx=5)
        
        # Controles de reprodução
        player_frame = tk.Frame(self.root, bg="#1a1a1a", pady=10)
        player_frame.pack(pady=10, fill=tk.X)
        
        buttons_container = tk.Frame(player_frame, bg="#1a1a1a")
        buttons_container.pack()
        
        btn_style = {
            "font": ("Arial", 14, "bold"),
            "cursor": "hand2",
            "width": 12,
            "height": 2
        }
        
        self.play_btn = tk.Button(
            buttons_container,
            text="▶ PLAY",
            command=self.play,
            bg="#4CAF50",
            fg="white",
            **btn_style
        )
        self.play_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.pause_btn = tk.Button(
            buttons_container,
            text="⏸ PAUSA",
            command=self.pause,
            bg="#FF9800",
            fg="white",
            **btn_style
        )
        self.pause_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        self.stop_btn = tk.Button(
            buttons_container,
            text="⏹ STOP",
            command=self.stop,
            bg="#f44336",
            fg="white",
            **btn_style
        )
        self.stop_btn.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Status
        status_frame = tk.Frame(self.root, bg="#1a1a1a")
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
        self.status_label = tk.Label(
            status_frame,
            text="Pronto - Aguardando arquivo MP4",
            bg="#1a1a1a",
            fg="#888888",
            font=("Arial", 9)
        )
        self.status_label.pack()
        
        # Barra de progresso (inicialmente oculta)
        self.progress_frame = tk.Frame(status_frame, bg="#1a1a1a")
        
        self.progress_label = tk.Label(
            self.progress_frame,
            text="Processando...",
            bg="#1a1a1a",
            fg="#4CAF50",
            font=("Arial", 8)
        )
        self.progress_label.pack()
        
        # Canvas para barra de progresso animada
        self.progress_canvas = tk.Canvas(
            self.progress_frame,
            width=300,
            height=20,
            bg="#2d2d2d",
            highlightthickness=0
        )
        self.progress_canvas.pack(pady=5)
        self.progress_bar = self.progress_canvas.create_rectangle(
            0, 0, 0, 20,
            fill="#4CAF50",
            width=0
        )
        self.progress_animation_running = False
        
        self.debug_log("✓ Interface gráfica configurada")
        
    def debug_log(self, message):
        """Salva mensagem de debug em arquivo"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_message = f"[{timestamp}] {message}"
        print(log_message)  # Também mostra no console
        
        # Salvar em arquivo
        try:
            # Usar diretório atual
            log_dir = os.path.dirname(os.path.abspath(__file__))
            if not log_dir:
                log_dir = os.getcwd()
                
            log_file = os.path.join(log_dir, "karaoke_debug.log")
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_message + "\n")
        except Exception as e:
            print(f"[ERRO LOG] Não foi possível salvar no arquivo: {e}")
        
    def load_file(self):
        file_path = filedialog.askopenfilename(
            title="Selecione um arquivo MP4",
            filetypes=[
                ("Arquivos MP4", "*.mp4"),
                ("Arquivos de Vídeo", "*.mp4 *.avi *.mkv *.mov"),
                ("Todos os arquivos", "*.*")
            ]
        )
        
        if file_path:
            self.debug_log(f"📁 Usuário selecionou arquivo: {file_path}")
            self.debug_log(f"📏 Tamanho do arquivo: {os.path.getsize(file_path) / (1024*1024):.2f} MB")
            
            self.status_label.config(text="Carregando informações do vídeo...")
            self.root.update()
            
            try:
                # Obter informações do vídeo
                self.debug_log("🔍 Executando ffprobe para obter metadados...")
                result = subprocess.run([
                    'ffprobe', '-v', 'quiet', '-print_format', 'json',
                    '-show_format', '-show_streams', file_path
                ], capture_output=True, text=True, check=True)
                
                info = json.loads(result.stdout)
                
                for stream in info['streams']:
                    if stream['codec_type'] == 'video':
                        self.fps = eval(stream.get('r_frame_rate', '30/1'))
                        self.width = stream['width']
                        self.height = stream['height']
                        self.debug_log(f"🎥 Resolução: {self.width}x{self.height}, FPS: {self.fps:.2f}")
                        break
                
                self.duration = float(info['format']['duration'])
                self.video_file = file_path
                self.processed_file = file_path  # Inicialmente usa o original
                self.pitch_shift = 0
                self.pitch_label.config(text="0")
                
                filename = os.path.basename(file_path)
                self.file_label.config(text=f"🎵 {filename}")
                
                self.debug_log(f"✅ Arquivo carregado com sucesso")
                self.debug_log(f"   Nome: {filename}")
                self.debug_log(f"   Duração: {self.duration:.2f}s ({self.duration/60:.2f}min)")
                self.debug_log(f"   Caminho: {file_path}")
                
                # Extrair e mostrar primeiro frame
                self.show_first_frame()
                
                self.status_label.config(text="✓ Arquivo carregado! Pronto para reproduzir")
                
            except subprocess.CalledProcessError as e:
                self.debug_log(f"❌ ERRO ffprobe: {e.stderr}")
                self.status_label.config(text=f"Erro ao carregar: {str(e)}")
                messagebox.showerror("Erro", f"Não foi possível analisar o vídeo.\nffprobe retornou erro.")
            except Exception as e:
                self.debug_log(f"❌ ERRO inesperado ao carregar: {type(e).__name__}: {str(e)}")
                self.status_label.config(text=f"Erro ao carregar: {str(e)}")
                messagebox.showerror("Erro", f"Não foi possível carregar o vídeo:\n{str(e)}")
                
    def show_first_frame(self):
        """Extrai e mostra o primeiro frame do vídeo"""
        self.debug_log("🖼️ Extraindo primeiro frame do vídeo...")
        try:
            temp_frame = tempfile.mktemp(suffix='.jpg')
            self.debug_log(f"   Arquivo temporário: {temp_frame}")
            
            subprocess.run([
                'ffmpeg', '-i', self.video_file, '-vframes', '1',
                '-f', 'image2', temp_frame
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            
            img = Image.open(temp_frame)
            self.display_frame(img)
            os.unlink(temp_frame)
            self.debug_log("✅ Primeiro frame extraído com sucesso")
            
        except Exception as e:
            self.debug_log(f"❌ Erro ao extrair primeiro frame: {e}")
            
    def show_progress(self, message="Processando..."):
        """Mostra a barra de progresso"""
        self.progress_label.config(text=message)
        self.progress_frame.pack()
        self.progress_animation_running = True
        self.animate_progress()
        
    def hide_progress(self):
        """Esconde a barra de progresso"""
        self.progress_animation_running = False
        self.progress_frame.pack_forget()
        
    def animate_progress(self):
        """Anima a barra de progresso"""
        if not self.progress_animation_running:
            return
            
        # Animação de "carregando" - vai e volta
        current_width = self.progress_canvas.coords(self.progress_bar)[2]
        
        if current_width >= 300:
            direction = -1
        elif current_width <= 0:
            direction = 1
        else:
            direction = getattr(self, '_progress_direction', 1)
            
        self._progress_direction = direction
        new_width = current_width + (direction * 10)
        new_width = max(0, min(300, new_width))
        
        self.progress_canvas.coords(self.progress_bar, 0, 0, new_width, 20)
        
        if self.progress_animation_running:
            self.root.after(50, self.animate_progress)
    
    def _restore_cursor(self):
        """Restaura o cursor e esconde o progresso"""
        self.debug_log("Restaurando cursor...")
        self.root.config(cursor="")
        self.hide_progress()
        self.root.update_idletasks()
        self.debug_log("✓ Cursor restaurado! Pronto para novo ajuste.")
            
    def change_pitch(self, steps):
        if not self.video_file:
            self.debug_log("⚠️ Tentativa de mudar tom sem arquivo carregado")
            return
        
        self.debug_log(f"🎵 Mudança de tom solicitada: {steps:+d} (atual: {self.pitch_shift})")
        
        # Verificar se já está processando
        if self.processing_pitch:
            self.debug_log("⚠️ Processamento de tom já em andamento, ignorando")
            self.status_label.config(text="⏳ Aguarde o processamento atual terminar...")
            return
        
        was_playing = self.is_playing
        
        if was_playing:
            self.debug_log("⏹ Parando reprodução para processar tom...")
            self.stop()
        
        # MUDAR CURSOR PARA AGUARDE
        self.root.config(cursor="wait")
        self.show_progress(f"Processando tom {self.pitch_shift:+d}...")
        self.root.update()
            
        novo_tom = self.pitch_shift + steps
        self.debug_log(f"🎚️ Tom atual: {self.pitch_shift} -> Novo tom: {novo_tom}")
        self.pitch_shift = novo_tom
        self.pitch_label.config(text=f"{self.pitch_shift:+d}" if self.pitch_shift != 0 else "0")
        
        # Reprocessar áudio com novo pitch
        if self.pitch_shift != 0:
            self.debug_log(f"🔊 Processando áudio com tom {self.pitch_shift:+d} semitons...")
            self.process_audio_with_pitch()
        else:
            # Limpar arquivo temporário anterior
            if self.processed_file != self.video_file and os.path.exists(self.processed_file):
                try:
                    self.debug_log(f"🗑️ Removendo arquivo temporário: {self.processed_file}")
                    os.unlink(self.processed_file)
                except Exception as e:
                    self.debug_log(f"⚠️ Não foi possível remover arquivo temporário: {e}")
                    
            self.processed_file = self.video_file
            self.status_label.config(text="Tom original restaurado")
            self.debug_log("🔄 Tom resetado para original")
            
            # RESTAURAR CURSOR E ESCONDER BARRA DE PROGRESSO
            self.root.config(cursor="")
            self.hide_progress()
            
    def process_audio_with_pitch(self):
        """Processa o áudio com mudança de tom mantendo velocidade"""
        self.status_label.config(text="⏳ Processando áudio com novo tom...")
        self.root.update()
        
        def process():
            try:
                self.processing_pitch = True
                self.debug_log(f"🎛️ Iniciando processamento de pitch shift: {self.pitch_shift} semitons")
                
                # Criar arquivo temporário
                temp_output = tempfile.mktemp(suffix='.mp4')
                self.debug_log(f"📄 Arquivo temporário de saída: {temp_output}")
                
                # Calcular pitch shift em semitons
                semitones = self.pitch_shift
                pitch_ratio = 2 ** (semitones / 12.0)
                self.debug_log(f"📊 Pitch ratio calculado: {pitch_ratio:.4f}")
                
                tempo_factor = 1.0 / pitch_ratio
                self.debug_log(f"⏱️ Fator de tempo necessário: {tempo_factor:.4f}")
                
                # Construir filtro de áudio
                if 0.5 <= tempo_factor <= 2.0:
                    audio_filter = f'asetrate=44100*{pitch_ratio},aresample=44100,atempo={tempo_factor}'
                    self.debug_log(f"🔧 Usando filtro simples (1 atempo): {audio_filter}")
                elif tempo_factor < 0.5:
                    num_stages = int(-1 * semitones / 12) + 1
                    tempo_filters = ','.join([f'atempo=0.5' for _ in range(num_stages)])
                    final_tempo = tempo_factor / (0.5 ** num_stages)
                    if final_tempo < 0.5:
                        final_tempo = 0.5
                    if final_tempo > 2.0:
                        final_tempo = 2.0
                    audio_filter = f'asetrate=44100*{pitch_ratio},aresample=44100,{tempo_filters},atempo={final_tempo}'
                    self.debug_log(f"🔧 Usando filtro complexo ({num_stages} atempo=0.5): {audio_filter}")
                else:
                    num_stages = int(semitones / 12) + 1
                    tempo_filters = ','.join([f'atempo=2.0' for _ in range(num_stages)])
                    final_tempo = tempo_factor / (2.0 ** num_stages)
                    if final_tempo < 0.5:
                        final_tempo = 0.5
                    if final_tempo > 2.0:
                        final_tempo = 2.0
                    audio_filter = f'asetrate=44100*{pitch_ratio},aresample=44100,{tempo_filters},atempo={final_tempo}'
                    self.debug_log(f"🔧 Usando filtro complexo ({num_stages} atempo=2.0): {audio_filter}")
                
                # Processar vídeo com novo áudio
                self.debug_log("🚀 Executando ffmpeg para processar áudio...")
                start_time = time.time()
                
                subprocess.run([
                    'ffmpeg', '-y', '-i', self.video_file,
                    '-filter_complex', 
                    f'[0:a]{audio_filter}[audio]',
                    '-map', '0:v', '-map', '[audio]',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                    temp_output
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                
                process_time = time.time() - start_time
                self.debug_log(f"✅ Processamento ffmpeg concluído em {process_time:.2f}s")
                
                # Limpar arquivo temporário anterior
                if self.processed_file != self.video_file and os.path.exists(self.processed_file):
                    try:
                        os.unlink(self.processed_file)
                        self.debug_log(f"🗑️ Arquivo temporário anterior removido: {self.processed_file}")
                    except Exception as e:
                        self.debug_log(f"⚠️ Não foi possível remover arquivo anterior: {e}")
                
                self.processed_file = temp_output
                self.debug_log(f"✅ Áudio processado com sucesso! Tom: {self.pitch_shift:+d} semitons")
                
                # ATUALIZAÇÃO NA THREAD PRINCIPAL - CORRIGIDO O CURSOR
                self.root.after(0, self._update_ui_after_pitch_success)
                
            except subprocess.CalledProcessError as e:
                error_msg = str(e)
                self.debug_log(f"❌ ERRO no ffmpeg durante processamento de pitch")
                self.debug_log(f"   Detalhes: {error_msg}")
                
                # ATUALIZAÇÃO NA THREAD PRINCIPAL - CORRIGIDO O CURSOR
                self.root.after(0, lambda: self._update_ui_after_pitch_error(
                    "ffmpeg", error_msg
                ))
                
            except Exception as e:
                error_msg = str(e)
                self.debug_log(f"❌ ERRO inesperado no processamento de pitch: {type(e).__name__}: {error_msg}")
                
                # ATUALIZAÇÃO NA THREAD PRINCIPAL - CORRIGIDO O CURSOR
                self.root.after(0, lambda: self._update_ui_after_pitch_error(
                    "geral", error_msg
                ))
                
            finally:
                self.processing_pitch = False
                self.debug_log("🏁 Processamento de pitch finalizado")
        
        thread = threading.Thread(target=process)
        thread.daemon = True
        thread.start()
    
    def _update_ui_after_pitch_success(self):
        """Atualiza a UI após sucesso no processamento de pitch"""
        self.status_label.config(
            text=f"✓ Tom ajustado em {self.pitch_shift:+d} semitom(s) - velocidade mantida"
        )
        self.root.config(cursor="")  # RESTAURAR CURSOR
        self.hide_progress()  # ESCONDER BARRA DE PROGRESSO
    
    def _update_ui_after_pitch_error(self, error_type, error_msg):
        """Atualiza a UI após erro no processamento de pitch"""
        self.status_label.config(text="❌ Erro ao processar áudio")
        self.root.config(cursor="")  # RESTAURAR CURSOR
        self.hide_progress()  # ESCONDER BARRA DE PROGRESSO
        self.pitch_shift = 0
        self.pitch_label.config(text="0")
        self.processed_file = self.video_file
        
        if error_type == "ffmpeg":
            messagebox.showerror(
                "Erro", 
                f"Não foi possível processar o áudio.\nErro no ffmpeg.\n\nO tom foi resetado para o original."
            )
        else:
            messagebox.showerror(
                "Erro", 
                f"Não foi possível processar o áudio.\nErro: {error_msg}\n\nO tom foi resetado para o original."
            )
        
    def play(self):
        if not self.video_file:
            self.debug_log("⚠️ Tentativa de reprodução sem arquivo carregado")
            return
        
        self.debug_log(f"▶️ Iniciando reprodução. Tom atual: {self.pitch_shift:+d}")
        
        # Se estiver pausado, apenas retomar
        if self.player.get_state() == vlc.State.Paused:
            self.debug_log("⏯️ Retomando reprodução pausada")
            self.player.play()
            self.is_playing = True
            self.status_label.config(text="▶ Reproduzindo...")
            self.start_video_thread()
            return
        
        # Carregar mídia
        media = self.vlc_instance.media_new(self.processed_file)
        self.player.set_media(media)
        
        # Iniciar reprodução
        self.player.play()
        self.is_playing = True
        
        self.status_label.config(text="▶ Reproduzindo...")
        self.debug_log("🎵 VLC iniciado, iniciando thread de vídeo...")
        
        # Iniciar thread de exibição de vídeo
        self.start_video_thread()
        
    def start_video_thread(self):
        """Inicia thread para exibir frames do vídeo"""
        self.debug_log("🎬 Iniciando thread de extração de vídeo...")
        
        if self.video_thread and self.video_thread.is_alive():
            self.debug_log("⚠️ Thread de vídeo já está em execução")
            return
            
        self.video_thread = threading.Thread(target=self.play_video)
        self.video_thread.daemon = True
        self.video_thread.start()
        self.debug_log("✅ Thread de vídeo iniciada")
        
    def play_video(self):
        """Extrai e exibe frames do vídeo em tempo real"""
        self.debug_log(f"🎞️ Thread de vídeo iniciada - Resolução: {self.width}x{self.height}, FPS: {self.fps:.2f}")
        
        # Criar pipe do ffmpeg para extrair frames
        cmd = [
            'ffmpeg', '-i', self.processed_file,
            '-f', 'image2pipe', '-pix_fmt', 'rgb24',
            '-vcodec', 'rawvideo', '-'
        ]
        
        self.debug_log(f"🔄 Comando ffmpeg: {' '.join(cmd)}")
        
        self.frame_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=10**8
        )
        
        frame_size = self.width * self.height * 3
        self.debug_log(f"📐 Tamanho do frame: {frame_size} bytes")
        
        frame_count = 0
        start_time = time.time()
        
        while self.is_playing:
            try:
                # Verificar se ainda está tocando
                player_state = self.player.get_state()
                if player_state in [vlc.State.Ended, vlc.State.Stopped]:
                    self.debug_log("⏹️ VLC terminou a reprodução, parando thread de vídeo")
                    self.root.after(0, self.stop)
                    break
                
                # Ler frame do pipe
                raw_frame = self.frame_process.stdout.read(frame_size)
                
                if len(raw_frame) != frame_size:
                    self.debug_log(f"⚠️ Frame incompleto: {len(raw_frame)} bytes (esperado: {frame_size})")
                    break
                
                frame_count += 1
                
                # Converter para imagem PIL
                import array
                frame_data = array.array('B', raw_frame)
                img = Image.frombytes('RGB', (self.width, self.height), bytes(frame_data))
                
                self.root.after(0, self.display_frame, img)
                
                # Log a cada 30 frames
                if frame_count % 30 == 0:
                    elapsed = time.time() - start_time
                    fps_actual = frame_count / elapsed
                    self.debug_log(f"📊 Vídeo: {frame_count} frames, FPS real: {fps_actual:.2f}")
                
                # Controlar timing baseado no FPS
                time.sleep(1.0 / self.fps)
                    
            except Exception as e:
                self.debug_log(f"❌ Erro na thread de vídeo: {type(e).__name__}: {str(e)}")
                break
        
        elapsed = time.time() - start_time
        self.debug_log(f"🏁 Thread de vídeo finalizada. Total: {frame_count} frames em {elapsed:.2f}s")
        
        if self.frame_process:
            self.debug_log("🛑 Finalizando processo ffmpeg...")
            self.frame_process.kill()
            try:
                self.frame_process.wait(timeout=1)
            except:
                pass
            self.frame_process = None
            self.debug_log("✅ Processo ffmpeg finalizado")
            
    def display_frame(self, img):
        """Exibe um frame PIL Image no label"""
        try:
            width, height = img.size
            max_width = 880
            max_height = 450
            
            scale = min(max_width/width, max_height/height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk, text="")
            
        except Exception as e:
            self.debug_log(f"❌ Erro ao exibir frame: {type(e).__name__}: {str(e)}")
            
    def pause(self):
        if self.is_playing:
            self.debug_log("⏸️ Pausando reprodução...")
            self.player.pause()
            self.is_playing = False
            self.status_label.config(text="⏸ Pausado")
            self.debug_log("✅ Reprodução pausada")
            
    def stop(self):
        self.debug_log("⏹️ Parando reprodução...")
        
        self.player.stop()
        self.is_playing = False
        
        # Parar thread de vídeo
        if self.frame_process:
            self.debug_log("🛑 Parando processo ffmpeg...")
            self.frame_process.kill()
            try:
                self.frame_process.wait(timeout=1)
            except:
                pass
            self.frame_process = None
            self.debug_log("✅ Processo ffmpeg parado")
        
        # Mostrar primeiro frame
        if self.video_file:
            self.show_first_frame()
            
        self.status_label.config(text="⏹ Parado")
        self.debug_log("✅ Reprodução parada completamente")
        
    def update_timer(self):
        """Atualiza o timer de reprodução"""
        if self.is_playing and self.player.get_state() == vlc.State.Playing:
            current_time = self.player.get_time() / 1000.0  # ms para segundos
            
            elapsed_str = time.strftime("%M:%S", time.gmtime(current_time))
            duration_str = time.strftime("%M:%S", time.gmtime(self.duration))
            self.time_label.config(text=f"{elapsed_str} / {duration_str}")
        elif self.video_file:
            duration_str = time.strftime("%M:%S", time.gmtime(self.duration))
            self.time_label.config(text=f"00:00 / {duration_str}")
        
        self.root.after(100, self.update_timer)
        
    def __del__(self):
        self.debug_log("🧹 Finalizando Karaoke Player...")
        if self.player:
            self.player.stop()
        if self.frame_process:
            self.frame_process.kill()
        self.debug_log("👋 Karaoke Player finalizado")

if __name__ == "__main__":
    root = tk.Tk()
    app = KaraokePlayer(root)
    root.mainloop()