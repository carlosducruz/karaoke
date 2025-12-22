import tkinter as tk
from tkinter import messagebox
import vlc
import threading
import time
import os
import subprocess
import tempfile
import json
import socket
import pickle
from datetime import datetime
import numpy as np

try:
    import pyaudio
    AUDIO_DISPONIVEL = True
except ImportError:
    AUDIO_DISPONIVEL = False
    print("AVISO: PyAudio não encontrado. Sistema de pontuação desabilitado.")

class KaraokePlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("Karaoke Player - MP4")
        self.root.geometry("900x850")  # Aumentado para acomodar todos os controles
        self.root.configure(bg="#1a1a1a")
        
        # FLAGS DE CONTROLE
        self.force_quit = False
        self.closing = False
        self.is_seeking = False  # Flag para controlar quando o usuário está arrastando o slider
        
        # SISTEMA DE PONTUAÇÃO
        self.pontuacao_ativa = False
        self.audio_interface = None
        self.mic_stream = None
        self.samples_musica = []
        self.samples_microfone = []
        self.pontuacao_final = 0
        self.inicializar_audio_pontuacao()
        
        # LOG INICIAL
        self.debug_log("=" * 60)
        self.debug_log("KARAOKE PLAYER INICIADO")
        self.debug_log(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.debug_log(f"Diretório atual: {os.getcwd()}")
        self.debug_log("=" * 60)
        
        # VLC instances
        self.vlc_instance = vlc.Instance('--no-xlib', '--no-video-title-show', '--no-embedded-video')
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
        self.processing_pitch = False
        
        # Servidor de socket para receber comandos
        self.socket_server = None
        self.server_thread = None
        self.porta = 5555
        self.iniciar_servidor()

        self.setup_ui()
        self.update_timer()
        
        # Posicionar no segundo monitor (se disponível)
        self.posicionar_segundo_monitor()
        
        # CONFIGURAR PROTOCOLO DE FECHAMENTO
        self.root.protocol("WM_DELETE_WINDOW", self.fechar_aplicacao)
        
        self.debug_log("✓ Interface gráfica configurada")
        self.debug_log("✓ Protocolo de fechamento configurado")
    
    def posicionar_segundo_monitor(self):
        """Move a janela para o segundo monitor se disponível"""
        try:
            # Aguarda a janela ser renderizada
            self.root.update_idletasks()
            
            # Obtém todas as telas
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Se a largura total for maior que a largura da janela, provavelmente há múltiplos monitores
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            # Tenta posicionar no segundo monitor (à direita do primeiro)
            # Assume que o segundo monitor está à direita
            x = screen_width  # Move para além do primeiro monitor
            y = 0
            
            self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
            # Maximiza a janela no segundo monitor
            self.root.state('zoomed')
            
            self.debug_log(f"📺 Janela posicionada no segundo monitor: {x}x{y}")
        except Exception as e:
            self.debug_log(f"⚠️ Não foi possível mover para segundo monitor: {e}")
    
    def iniciar_servidor(self):
        """Inicia servidor socket para receber comandos do painel de controle"""
        def servidor():
            try:
                self.debug_log(f"🔧 Iniciando servidor socket na porta {self.porta}...")
                self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.socket_server.bind(('127.0.0.1', self.porta))
                self.socket_server.listen(1)
                
                self.debug_log(f"✅ Servidor ouvindo na porta {self.porta}")
                
                while not self.force_quit:
                    try:
                        conn, addr = self.socket_server.accept()
                        self.debug_log(f"✅ Conexão recebida de {addr}")
                        
                        # Thread para processar comandos desta conexão
                        threading.Thread(
                            target=self.processar_comandos, 
                            args=(conn,), 
                            daemon=True
                        ).start()
                    except Exception as e:
                        if not self.force_quit:
                            self.debug_log(f"⚠️ Erro no servidor: {e}")
                        break
            except Exception as e:
                self.debug_log(f"❌ Erro ao iniciar servidor: {e}")
        
        self.server_thread = threading.Thread(target=servidor, daemon=True)
        self.server_thread.start()
    
    def processar_comandos(self, conn):
        """Processa comandos recebidos via socket"""
        try:
            while not self.force_quit:
                # Recebe o tamanho da mensagem
                size_bytes = conn.recv(4)
                if not size_bytes:
                    break
                
                size = int.from_bytes(size_bytes, 'big')
                
                # Recebe a mensagem completa
                data = b''
                while len(data) < size:
                    packet = conn.recv(size - len(data))
                    if not packet:
                        break
                    data += packet
                
                mensagem = pickle.loads(data)
                comando = mensagem.get('comando')
                dados = mensagem.get('dados')
                
                self.debug_log(f"📥 Comando recebido: {comando}")
                
                # Executa comando na thread principal (UI)
                self.root.after(0, lambda c=comando, d=dados: self.executar_comando(c, d))
                
        except Exception as e:
            if not self.force_quit:
                self.debug_log(f"⚠️ Erro ao processar comando: {e}")
        finally:
            conn.close()
    
    def executar_comando(self, comando, dados):
        """Executa comando recebido do painel de controle"""
        try:
            if comando == 'load':
                self.video_file = dados['path']
                self.processed_file = dados['path']
                self.duration = dados.get('duration', 0)
                self.fps = dados.get('fps', 30)
                self.width = dados.get('width', 640)
                self.height = dados.get('height', 480)
                self.pitch_shift = 0
                self.pitch_label.config(text="0")
                self.file_label.config(text=os.path.basename(dados['path']))
                self.embed_vlc_player()
                self.status_label.config(text="✓ Arquivo carregado")
                
            elif comando == 'play':
                self.play()
                
            elif comando == 'pause':
                self.pause()
                
            elif comando == 'stop':
                self.stop()
                
            elif comando == 'pitch':
                steps = dados.get('steps', 0)
                self.change_pitch(steps)
                
            elif comando == 'seek':
                # Navegar para posição específica (em segundos)
                new_time = dados.get('time', 0)
                if self.player and self.duration > 0:
                    self.player.set_time(int(new_time * 1000))
            
            elif comando == 'quit':
                self.debug_log("🛑 Comando de fechamento recebido")
                self.fechar_aplicacao()
                    
            self.debug_log(f"✅ Comando executado: {comando}")
        except Exception as e:
            self.debug_log(f"❌ Erro ao executar comando {comando}: {e}")
    
    def fechar_aplicacao(self):
        """Fecha a aplicação de forma limpa SEM confirmação"""
        if self.closing:
            self.debug_log("⚠️ Fechamento já em andamento, ignorando...")
            return
            
        self.closing = True
        self.force_quit = True
        
        self.debug_log("=" * 60)
        self.debug_log("🛑 INICIANDO FECHAMENTO DA APLICAÇÃO")
        self.debug_log(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.debug_log("=" * 60)
        
        # 1. PARAR REPRODUÇÃO IMEDIATAMENTE
        self.debug_log("1️⃣ Parando reprodução...")
        self.is_playing = False
        self.progress_animation_running = False
        
        # Parar sistema de pontuação
        if hasattr(self, 'pontuacao_ativa') and self.pontuacao_ativa:
            try:
                self.pontuacao_ativa = False
                if hasattr(self, 'mic_stream') and self.mic_stream:
                    self.mic_stream.stop_stream()
                    self.mic_stream.close()
                self.debug_log("✅ Sistema de pontuação finalizado")
            except Exception as e:
                self.debug_log(f"⚠️ Erro ao parar pontuação: {e}")
        
        # Limpar interface de áudio
        if hasattr(self, 'audio_interface') and self.audio_interface:
            try:
                self.audio_interface.terminate()
                self.debug_log("✅ Interface de áudio finalizada")
            except Exception as e:
                self.debug_log(f"⚠️ Erro ao finalizar áudio: {e}")
        
        # 2. PARAR PLAYER VLC
        if hasattr(self, 'player') and self.player:
            try:
                self.debug_log("2️⃣ Parando VLC player...")
                self.player.stop()
                time.sleep(0.1)  # Pequena pausa para garantir parada
                self.debug_log("✅ VLC parado")
            except Exception as e:
                self.debug_log(f"⚠️ Erro ao parar VLC: {e}")
        
        # 3. AGUARDAR THREAD (timeout muito curto)
        if hasattr(self, 'video_thread') and self.video_thread:
            if self.video_thread.is_alive():
                self.debug_log("3️⃣ Aguardando thread...")
                self.video_thread.join(timeout=0.5)
                if self.video_thread.is_alive():
                    self.debug_log("⚠️ Thread não terminou (normal, é daemon)")
                else:
                    self.debug_log("✅ Thread finalizada")
        
        # 4. LIMPAR ARQUIVOS TEMPORÁRIOS
        if hasattr(self, 'processed_file') and self.processed_file:
            if self.processed_file != getattr(self, 'video_file', None):
                try:
                    if os.path.exists(self.processed_file):
                        self.debug_log(f"4️⃣ Removendo arquivo temporário: {os.path.basename(self.processed_file)}")
                        os.unlink(self.processed_file)
                        self.debug_log("✅ Arquivo temporário removido")
                except Exception as e:
                    self.debug_log(f"⚠️ Erro ao remover arquivo: {e}")
        
        self.debug_log("=" * 60)
        self.debug_log("✅ FECHAMENTO CONCLUÍDO - DESTRUINDO JANELA")
        self.debug_log("=" * 60)
        
        # 5. DESTRUIR JANELA
        try:
            self.root.quit()
        except Exception as e:
            self.debug_log(f"⚠️ Erro ao quit: {e}")
        
        try:
            self.root.destroy()
        except Exception as e:
            self.debug_log(f"⚠️ Erro ao destruir janela: {e}")
        
        # Forçar saída se necessário (último recurso)
        self.debug_log("🔚 Forçando saída do programa")
        os._exit(0)

    def inicializar_audio_pontuacao(self):
        """Inicializa o sistema de áudio para pontuação"""
        if not AUDIO_DISPONIVEL:
            self.debug_log("⚠ PyAudio não disponível - Sistema de pontuação desabilitado")
            return
        
        try:
            self.audio_interface = pyaudio.PyAudio()
            self.debug_log("✓ Sistema de áudio inicializado para pontuação")
        except Exception as e:
            self.debug_log(f"⚠ Erro ao inicializar áudio: {e}")
            self.audio_interface = None
    
    def iniciar_captura_pontuacao(self):
        """Inicia captura de áudio para pontuação"""
        if not AUDIO_DISPONIVEL or not self.audio_interface:
            return
        
        try:
            # Configurações de áudio
            CHUNK = 2048
            FORMAT = pyaudio.paInt16
            CHANNELS = 1  # Mono para simplificar análise
            RATE = 22050  # Taxa reduzida para melhor performance
            
            self.mic_stream = self.audio_interface.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            self.pontuacao_ativa = True
            self.samples_musica = []
            self.samples_microfone = []
            
            # Thread para capturar microfone
            threading.Thread(target=self._capturar_microfone, args=(CHUNK,), daemon=True).start()
            
            # Thread para capturar áudio do player (simulado via análise de volume)
            threading.Thread(target=self._capturar_player_audio, daemon=True).start()
            
            self.debug_log("✓ Captura de áudio para pontuação iniciada")
            
        except Exception as e:
            self.debug_log(f"❌ Erro ao iniciar captura: {e}")
    
    def parar_captura_pontuacao(self):
        """Para captura e calcula pontuação"""
        self.pontuacao_ativa = False
        
        if self.mic_stream:
            try:
                self.mic_stream.stop_stream()
                self.mic_stream.close()
            except:
                pass
            self.mic_stream = None
        
        # Calcula pontuação
        if len(self.samples_musica) > 0 and len(self.samples_microfone) > 0:
            self.calcular_pontuacao()
        
        self.debug_log("✓ Captura de pontuação finalizada")
    
    def _capturar_microfone(self, chunk_size):
        """Thread que captura áudio do microfone"""
        while self.pontuacao_ativa and self.is_playing:
            try:
                data = self.mic_stream.read(chunk_size, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Calcula energia (RMS)
                rms = np.sqrt(np.mean(audio_data**2))
                self.samples_microfone.append(rms)
                
            except Exception as e:
                if self.pontuacao_ativa:
                    self.debug_log(f"Erro captura mic: {e}")
                break
    
    def _capturar_player_audio(self):
        """Thread que simula captura do áudio do player via análise de tempo"""
        # Como não temos acesso direto ao áudio do VLC, vamos criar uma
        # representação baseada no tempo de reprodução
        while self.pontuacao_ativa and self.is_playing:
            try:
                # Pega posição atual
                current_time = self.player.get_time() / 1000.0
                
                # Simula energia baseada em uma função senoidal
                # (em produção, isso seria o áudio real)
                energy = abs(np.sin(current_time * 2 * np.pi / 4)) * 1000
                self.samples_musica.append(energy)
                
                time.sleep(0.046)  # ~22050 Hz / 2048 chunk
                
            except Exception as e:
                if self.pontuacao_ativa:
                    self.debug_log(f"Erro captura player: {e}")
                break
    
    def calcular_pontuacao(self):
        """Calcula pontuação baseada na correlação entre áudio da música e microfone"""
        try:
            # Normaliza arrays para mesmo tamanho
            min_len = min(len(self.samples_musica), len(self.samples_microfone))
            
            if min_len < 10:
                self.debug_log("⚠ Amostras insuficientes para calcular pontuação")
                self.pontuacao_final = 0
                return
            
            musica = np.array(self.samples_musica[:min_len])
            microfone = np.array(self.samples_microfone[:min_len])
            
            # Normaliza valores (0-1)
            musica_norm = (musica - np.min(musica)) / (np.max(musica) - np.min(musica) + 1e-10)
            mic_norm = (microfone - np.min(microfone)) / (np.max(microfone) - np.min(microfone) + 1e-10)
            
            # Calcula correlação cruzada
            correlacao = np.correlate(musica_norm, mic_norm, mode='valid')[0]
            
            # Calcula diferença de energia média
            diff_energia = 1 - np.mean(np.abs(musica_norm - mic_norm))
            
            # Pontuação: 70% correlação + 30% energia
            pontuacao_base = (correlacao * 0.7 + diff_energia * 0.3) * 100
            
            # Limita entre 0 e 100
            self.pontuacao_final = max(0, min(100, pontuacao_base))
            
            self.debug_log(f"🎯 Pontuação calculada: {self.pontuacao_final:.1f}")
            
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
        
        # Cria janela de pontuação
        pontuacao_win = tk.Toplevel(self.root)
        pontuacao_win.title("Pontuação Karaoke")
        pontuacao_win.geometry("400x300")
        pontuacao_win.configure(bg="#1a1a1a")
        pontuacao_win.transient(self.root)
        pontuacao_win.grab_set()
        
        # Centraliza a janela
        pontuacao_win.update_idletasks()
        x = (pontuacao_win.winfo_screenwidth() // 2) - (400 // 2)
        y = (pontuacao_win.winfo_screenheight() // 2) - (300 // 2)
        pontuacao_win.geometry(f"400x300+{x}+{y}")
        
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
        ).pack(pady=20)
        
        self.debug_log(f"📊 Pontuação exibida: {pontos} - {mensagem}")
    
    def debug_log(self, message):
        """Salva mensagem de debug em arquivo"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        try:
            log_dir = os.path.dirname(os.path.abspath(__file__))
            if not log_dir:
                log_dir = os.getcwd()
                
            log_file = os.path.join(log_dir, "karaoke_debug.log")
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_message + "\n")
        except Exception as e:
            print(f"[ERRO LOG] Não foi possível salvar no arquivo: {e}")

    def setup_ui(self):
        """Configura a interface do usuário"""
        # Frame principal
        main_frame = tk.Frame(self.root, bg="#1a1a1a")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Container horizontal: vídeo + controles laterais
        video_and_controls_container = tk.Frame(main_frame, bg="#1a1a1a")
        video_and_controls_container.pack(fill=tk.BOTH, expand=True)
        
        # ===== COLUNA ESQUERDA: CONTROLES DE NAVEGAÇÃO =====
        left_controls = tk.Frame(video_and_controls_container, bg="#2d2d2d", width=200)
        left_controls.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_controls.pack_propagate(False)
        
        tk.Label(
            left_controls,
            text="⏯ NAVEGAÇÃO",
            bg="#2d2d2d",
            fg="#4CAF50",
            font=("Arial", 11, "bold")
        ).pack(pady=(10, 15))
        
        # Tempo atual
        self.current_time_label = tk.Label(
            left_controls,
            text="00:00",
            bg="#2d2d2d",
            fg="#4CAF50",
            font=("Arial", 14, "bold")
        )
        self.current_time_label.pack(pady=(0, 5))
        
        # Slider vertical de seek
        self.seek_slider = tk.Scale(
            left_controls,
            from_=100,
            to=0,
            orient=tk.VERTICAL,
            showvalue=False,
            bg="#2d2d2d",
            fg="#4CAF50",
            troughcolor="#1a1a1a",
            activebackground="#4CAF50",
            sliderrelief="raised",
            sliderlength=30,
            highlightthickness=0,
            bd=2,
            relief=tk.GROOVE,
            width=20,
            length=250
        )
        self.seek_slider.pack(pady=10)
        self.seek_slider.set(0)
        
        # Bind events para o slider
        self.seek_slider.bind("<ButtonPress-1>", self.on_seek_press)
        self.seek_slider.bind("<ButtonRelease-1>", self.on_seek_release)
        self.seek_slider.bind("<B1-Motion>", self.on_seek_drag)
        
        # Tempo total
        self.total_time_label = tk.Label(
            left_controls,
            text="00:00",
            bg="#2d2d2d",
            fg="white",
            font=("Arial", 10)
        )
        self.total_time_label.pack(pady=(5, 15))
        
        # Botões de navegação rápida
        nav_button_style = {
            "bg": "#555555",
            "fg": "white",
            "font": ("Arial", 10, "bold"),
            "cursor": "hand2",
            "width": 15,
            "pady": 8,
            "relief": tk.RAISED,
            "bd": 2
        }
        
        tk.Button(
            left_controls,
            text="⏪ -10s",
            command=lambda: self.seek_relative(-10),
            **nav_button_style
        ).pack(pady=3)
        
        tk.Button(
            left_controls,
            text="◀ -5s",
            command=lambda: self.seek_relative(-5),
            bg="#666666",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            width=15,
            pady=8,
            relief=tk.RAISED,
            bd=2
        ).pack(pady=3)
        
        tk.Button(
            left_controls,
            text="+5s ▶",
            command=lambda: self.seek_relative(5),
            bg="#666666",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            width=15,
            pady=8,
            relief=tk.RAISED,
            bd=2
        ).pack(pady=3)
        
        tk.Button(
            left_controls,
            text="+10s ⏩",
            command=lambda: self.seek_relative(10),
            **nav_button_style
        ).pack(pady=3)
        
        # ===== COLUNA DIREITA: VÍDEO E CONTROLES PRINCIPAIS =====
        right_container = tk.Frame(video_and_controls_container, bg="#1a1a1a")
        right_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Frame do vídeo (para o VLC)
        self.video_frame = tk.Frame(right_container, bg="#000000", width=680, height=380)
        self.video_frame.pack(pady=5)
        self.video_frame.pack_propagate(False)
        
        # Label inicial dentro do frame de vídeo
        self.video_label = tk.Label(
            self.video_frame, 
            bg="#000000", 
            text="🎬 Carregue um vídeo para a música começar ", 
            fg="#666666", 
            font=("Arial", 14)
        )
        self.video_label.pack(expand=True)
        
        # Frame de info
        info_frame = tk.Frame(main_frame, bg="#2d2d2d", pady=8)
        info_frame.pack(fill=tk.X, pady=(5, 0))
        
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
        self.time_label.pack(pady=(2, 0))
        
        # ===== CONTROLES DE NAVEGAÇÃO E SEEK =====
        # Container dedicado para controles de navegação
        navigation_container = tk.Frame(main_frame, bg="#1a1a1a", pady=10)
        navigation_container.pack(fill=tk.X, pady=(5, 0))
        
        # Barra de progresso do vídeo (seek slider)
        seek_frame = tk.Frame(navigation_container, bg="#1a1a1a")
        seek_frame.pack(fill=tk.X, padx=20, pady=(0, 5))
        # Barra de progresso do vídeo (seek slider)
        seek_frame = tk.Frame(navigation_container, bg="#1a1a1a")
        seek_frame.pack(fill=tk.X, padx=20, pady=(0, 5))
        
        # Labels de tempo
        self.current_time_label = tk.Label(
            seek_frame,
            text="00:00",
            bg="#1a1a1a",
            fg="#4CAF50",
            font=("Arial", 10, "bold"),
            width=6
        )
        self.current_time_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Slider de seek - VISÍVEL E DESTACADO
        self.seek_slider = tk.Scale(
            seek_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            showvalue=False,
            bg="#1a1a1a",
            fg="#4CAF50",
            troughcolor="#333333",
            activebackground="#4CAF50",
            sliderrelief="raised",
            sliderlength=25,
            highlightthickness=0,
            bd=2,
            relief=tk.GROOVE
        )
        self.seek_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.seek_slider.set(0)
        self.seek_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.seek_slider.set(0)
        
        # Bind events para o slider
        self.seek_slider.bind("<ButtonPress-1>", self.on_seek_press)
        self.seek_slider.bind("<ButtonRelease-1>", self.on_seek_release)
        self.seek_slider.bind("<B1-Motion>", self.on_seek_drag)
        
        self.total_time_label = tk.Label(
            seek_frame,
            text="00:00",
            bg="#1a1a1a",
            fg="#4CAF50",
            font=("Arial", 10, "bold"),
            width=6
        )
        self.total_time_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Botões de navegação rápida - DESTACADOS
        nav_buttons_frame = tk.Frame(navigation_container, bg="#1a1a1a")
        nav_buttons_frame.pack(pady=(5, 10))
        
        tk.Label(
            nav_buttons_frame,
            text="Navegação:",
            bg="#1a1a1a",
            fg="white",
            font=("Arial", 9, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Button(
            nav_buttons_frame,
            text="⏪ -10s",
            command=lambda: self.seek_relative(-10),
            bg="#555555",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15,
            pady=8,
            relief=tk.RAISED,
            bd=2
        ).pack(side=tk.LEFT, padx=3)
        
        tk.Button(
            nav_buttons_frame,
            text="◀ -5s",
            command=lambda: self.seek_relative(-5),
            bg="#666666",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15,
            pady=8,
            relief=tk.RAISED,
            bd=2
        ).pack(side=tk.LEFT, padx=3)
        
        tk.Button(
            nav_buttons_frame,
            text="+5s ▶",
            command=lambda: self.seek_relative(5),
            bg="#666666",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15,
            pady=8,
            relief=tk.RAISED,
            bd=2
        ).pack(side=tk.LEFT, padx=3)
        
        tk.Button(
            nav_buttons_frame,
            text="+10s ⏩",
            command=lambda: self.seek_relative(10),
            bg="#555555",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15,
            pady=8,
            relief=tk.RAISED,
            bd=2
        ).pack(side=tk.LEFT, padx=3)
        
        # Separador visual
        separator = tk.Frame(main_frame, bg="#333333", height=2)
        separator.pack(fill=tk.X, pady=(5, 10))
        
        # ===== CONTROLES PRINCIPAIS =====
        # Botão carregar
        load_btn = tk.Button(
            main_frame,
            text="📁 Carregar MP4",
            command=self.load_file,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=15,
            pady=8
        )
        load_btn.pack(pady=(0, 5))
        
        # Controle de tom
        pitch_frame = tk.Frame(right_container, bg="#1a1a1a")
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
        
        # Controles de reprodução principais
        player_frame = tk.Frame(right_container, bg="#1a1a1a", pady=10)
        player_frame.pack(pady=5)
        # Controles de reprodução principais
        player_frame = tk.Frame(main_frame, bg="#1a1a1a", pady=10)
        player_frame.pack(pady=5)
        
        buttons_container = tk.Frame(player_frame, bg="#1a1a1a")
        buttons_container.pack()
        
        btn_style = {
            "font": ("Arial", 12, "bold"),
            "cursor": "hand2",
            "width": 10,
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
        
        # Status bar (rodapé)
        status_frame = tk.Frame(right_container, bg="#1a1a1a")
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
        self.status_label = tk.Label(
            status_frame,
            text="Pronto - Aguardando arquivo MP4",
            bg="#1a1a1a",
            fg="#888888",
            font=("Arial", 9)
        )
        self.status_label.pack()
        
        # Barra de progresso (para processamento)
        self.progress_frame = tk.Frame(status_frame, bg="#1a1a1a")
        
        self.progress_label = tk.Label(
            self.progress_frame,
            text="Processando...",
            bg="#1a1a1a",
            fg="#4CAF50",
            font=("Arial", 8)
        )
        self.progress_label.pack()
        
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
        
        # Configurar cores do slider (após criação)
        self.seek_slider.config(troughcolor="#333333")
        
        # Atualizar a janela para garantir que o widget ID seja gerado
        self.root.update_idletasks()
    
    def embed_vlc_player(self):
        """Embute o player VLC no frame de vídeo"""
        if hasattr(self, 'video_label'):
            self.video_label.pack_forget()
        
        # Obtém o ID da janela do frame de vídeo
        win_id = self.video_frame.winfo_id()
        
        # Configura o player VLC para usar este frame
        if os.name == 'nt':  # Windows
            self.player.set_hwnd(win_id)
        else:  # Linux/Mac
            self.player.set_xwindow(win_id)
        
        self.debug_log(f"✓ VLC embutido no frame (ID: {win_id})")
    
    def on_seek_press(self, event):
        """Quando o usuário clica na barra de progresso"""
        self.is_seeking = True
        self.debug_log("🔘 Iniciando arraste da barra de progresso")
    
    def on_seek_drag(self, event):
        """Quando o usuário arrasta a barra de progresso"""
        if self.is_seeking and self.duration > 0:
            # Atualiza o tempo atual durante o arraste (ajustado para slider vertical)
            progress = (100 - self.seek_slider.get()) / 100.0
            current_time = progress * self.duration
            elapsed_str = time.strftime("%M:%S", time.gmtime(current_time))
            self.current_time_label.config(text=elapsed_str)
    
    def on_seek_release(self, event):
        """Quando o usuário solta a barra de progresso"""
        self.debug_log("🔘 Soltando barra de progresso")
        if self.duration > 0 and self.player:
            progress = (100 - self.seek_slider.get()) / 100.0  # Invertido para vertical
            new_time = int(progress * self.duration * 1000)  # VLC usa milissegundos
            
            was_playing = self.is_playing
            
            # Define a nova posição
            self.player.set_time(new_time)
            
            if was_playing:
                # Continua a reprodução
                self.player.play()
        
        self.is_seeking = False
    
    def seek_relative(self, seconds):
        """Avança/retrocede um número específico de segundos"""
        if not self.player or self.duration == 0:
            return
        
        current_time = self.player.get_time() / 1000.0  # Converter para segundos
        new_time = max(0, min(self.duration, current_time + seconds))
        
        was_playing = self.is_playing
        
        if was_playing:
            self.player.pause()
        
        self.player.set_time(int(new_time * 1000))
        
        # Atualiza o slider (invertido para vertical: 100 no topo = início, 0 embaixo = fim)
        progress = (new_time / self.duration) * 100
        self.seek_slider.set(100 - progress)
        
        # Atualiza o tempo exibido
        elapsed_str = time.strftime("%M:%S", time.gmtime(new_time))
        self.current_time_label.config(text=elapsed_str)
        
        if was_playing:
            self.player.play()
        
        self.debug_log(f"⏩ Navegação: {seconds:+d} segundos")
    
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
            self.debug_log(f"📂 Usuário selecionou arquivo: {file_path}")
            
            try:
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
                        break
                
                self.duration = float(info['format']['duration'])
                self.video_file = file_path
                self.processed_file = file_path
                self.pitch_shift = 0
                self.pitch_label.config(text="0")
                
                # Atualiza a barra de seek
                self.seek_slider.config(from_=0, to=100)
                self.seek_slider.set(0)
                
                # Atualiza labels de tempo
                duration_str = time.strftime("%M:%S", time.gmtime(self.duration))
                self.total_time_label.config(text=duration_str)
                self.current_time_label.config(text="00:00")
                self.time_label.config(text=f"00:00 / {duration_str}")
                
                filename = os.path.basename(file_path)
                self.file_label.config(text=f"🎵 {filename}")
                
                # Torna a barra de progresso visível
                self.seek_slider.config(state="normal")
                
                # Configura o VLC para usar o frame
                self.embed_vlc_player()
                
                self.status_label.config(text="✓ Arquivo carregado! Pronto para reproduzir")
                
                self.debug_log(f"✓ Vídeo carregado: {filename} ({duration_str})")
                
            except Exception as e:
                self.debug_log(f"❌ ERRO ao carregar: {e}")
                messagebox.showerror("Erro", f"Não foi possível carregar o vídeo:\n{str(e)}")
                
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
            
    def change_pitch(self, steps):
        if not self.video_file or self.processing_pitch:
            return
        
        was_playing = self.is_playing
        
        if was_playing:
            self.stop()
        
        self.root.config(cursor="wait")
        self.show_progress(f"Processando tom {self.pitch_shift:+d}...")
        self.root.update()
            
        self.pitch_shift += steps
        self.pitch_label.config(text=f"{self.pitch_shift:+d}" if self.pitch_shift != 0 else "0")
        
        if self.pitch_shift != 0:
            self.process_audio_with_pitch()
        else:
            if self.processed_file != self.video_file and os.path.exists(self.processed_file):
                try:
                    os.unlink(self.processed_file)
                except:
                    pass
                    
            self.processed_file = self.video_file
            self.status_label.config(text="Tom original restaurado")
            self.root.config(cursor="")
            self.hide_progress()
            
    def process_audio_with_pitch(self):
        """Processa o áudio com mudança de tom"""
        def process():
            try:
                self.processing_pitch = True
                temp_output = tempfile.mktemp(suffix='.mp4')
                
                semitones = self.pitch_shift
                pitch_ratio = 2 ** (semitones / 12.0)
                tempo_factor = 1.0 / pitch_ratio
                
                if 0.5 <= tempo_factor <= 2.0:
                    audio_filter = f'asetrate=44100*{pitch_ratio},aresample=44100,atempo={tempo_factor}'
                else:
                    audio_filter = f'asetrate=44100*{pitch_ratio},aresample=44100'
                
                subprocess.run([
                    'ffmpeg', '-y', '-i', self.video_file,
                    '-filter_complex', 
                    f'[0:a]{audio_filter}[audio]',
                    '-map', '0:v', '-map', '[audio]',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                    temp_output
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                
                if self.processed_file != self.video_file and os.path.exists(self.processed_file):
                    try:
                        os.unlink(self.processed_file)
                    except:
                        pass
                
                self.processed_file = temp_output
                self.root.after(0, self._update_ui_after_pitch_success)
                
            except Exception as e:
                self.debug_log(f"❌ ERRO no processamento de pitch: {e}")
                self.root.after(0, lambda: self._update_ui_after_pitch_error(str(e)))
                
            finally:
                self.processing_pitch = False
        
        thread = threading.Thread(target=process, daemon=True)
        thread.start()
    
    def _update_ui_after_pitch_success(self):
        """Atualiza a UI após sucesso no processamento"""
        self.status_label.config(text=f"✓ Tom ajustado em {self.pitch_shift:+d} semitom(s)")
        self.root.config(cursor="")
        self.hide_progress()
    
    def _update_ui_after_pitch_error(self, error_msg):
        """Atualiza a UI após erro no processamento"""
        self.status_label.config(text="❌ Erro ao processar áudio")
        self.root.config(cursor="")
        self.hide_progress()
        self.pitch_shift = 0
        self.pitch_label.config(text="0")
        self.processed_file = self.video_file
        messagebox.showerror("Erro", f"Não foi possível processar o áudio.\n{error_msg}")
        
    def play(self):
        if not self.video_file:
            return
        
        if self.player.get_state() == vlc.State.Paused:
            self.player.play()
            self.is_playing = True
            self.status_label.config(text="▶ Reproduzindo...")
            return
        
        # Carrega e reproduz a mídia
        media = self.vlc_instance.media_new(self.processed_file)
        self.player.set_media(media)
        self.player.play()
        self.is_playing = True
        self.status_label.config(text="▶ Reproduzindo...")
        
        # Inicia captura de áudio para pontuação
        if AUDIO_DISPONIVEL and self.audio_interface:
            self.root.after(500, self.iniciar_captura_pontuacao)  # Aguarda 500ms para player estabilizar
        
        # Aguarda um pouco para garantir que o player iniciou
        self.root.after(100, lambda: None)
    
    def pause(self):
        if self.is_playing:
            self.player.pause()
            self.is_playing = False
            self.status_label.config(text="⏸ Pausado")
            
    def stop(self):
        self.debug_log("⏹️ Parando reprodução...")
        
        # Para captura de pontuação antes de parar o player
        if self.pontuacao_ativa:
            self.parar_captura_pontuacao()
        
        # Marca como não tocando ANTES de parar
        self.is_playing = False
        
        # Para o player VLC
        try:
            self.player.stop()
        except Exception as e:
            self.debug_log(f"⚠️ Erro ao parar player: {e}")
        
        # Reseta a barra de progresso
        self.seek_slider.set(0)
        self.current_time_label.config(text="00:00")
        
        # Atualiza status apenas se não estiver fechando
        if not self.force_quit:
            try:
                self.status_label.config(text="⏹ Parado")
            except:
                pass
        
        self.debug_log("✅ Reprodução parada completamente")
        
    def update_timer(self):
        """Atualiza o timer de reprodução"""
        if self.force_quit:
            return
            
        try:
            if self.is_playing and self.player.get_state() == vlc.State.Playing:
                current_time = self.player.get_time() / 1000.0
                
                # Verifica se chegou ao fim da música
                if current_time > 0 and self.duration > 0 and current_time >= (self.duration - 0.5):
                    if self.pontuacao_ativa:
                        self.debug_log("🎵 Música finalizada - calculando pontuação...")
                        self.parar_captura_pontuacao()
                
                # Atualiza a barra de progresso (se não estiver sendo arrastada)
                # Slider vertical: 100 no topo = início (0%), 0 embaixo = fim (100%)
                if not self.is_seeking and self.duration > 0:
                    progress = (current_time / self.duration) * 100
                    self.seek_slider.set(100 - progress)  # Invertido para vertical
                
                elapsed_str = time.strftime("%M:%S", time.gmtime(current_time))
                duration_str = time.strftime("%M:%S", time.gmtime(self.duration))
                
                self.time_label.config(text=f"{elapsed_str} / {duration_str}")
                self.current_time_label.config(text=elapsed_str)
                
            elif self.video_file:
                duration_str = time.strftime("%M:%S", time.gmtime(self.duration))
                self.time_label.config(text=f"00:00 / {duration_str}")
        except Exception as e:
            self.debug_log(f"⚠️ Erro no update_timer: {e}")
        
        if not self.force_quit:
            self.root.after(100, self.update_timer)

if __name__ == "__main__":
    root = tk.Tk()
    app = KaraokePlayer(root)
    
    # Tratar Ctrl+C no terminal
    import signal
    def signal_handler(sig, frame):
        app.debug_log("⚠️ Sinal Ctrl+C recebido")
        app.fechar_aplicacao()
    
    try:
        signal.signal(signal.SIGINT, signal_handler)
    except:
        pass
    
    # Tratar exceções não capturadas
    import sys
    def handle_exception(exc_type, exc_value, exc_traceback):
        app.debug_log(f"❌ EXCEÇÃO NÃO CAPTURADA: {exc_type.__name__}: {exc_value}")
        if not app.force_quit:
            app.fechar_aplicacao()
    
    sys.excepthook = handle_exception
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        app.debug_log("⚠️ KeyboardInterrupt no mainloop")
        app.fechar_aplicacao()
    except Exception as e:
        app.debug_log(f"❌ ERRO NO MAINLOOP: {e}")
        if not app.force_quit:
            app.fechar_aplicacao()
    finally:
        app.debug_log("🏁 Mainloop finalizado")