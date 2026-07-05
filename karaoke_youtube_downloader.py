import tkinter as tk
from tkinter import ttk, messagebox
import yt_dlp
import threading
import os
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageTk
import vlc

class YouTubeDownloaderWindow:
    def __init__(self, parent, music_folder, main_app=None):
        self.parent = parent
        self.music_folder = music_folder
        self.main_app = main_app
        self.videos_encontrados = []
        self.download_em_progresso = False
        self.busca_em_progresso = False
        self.cancelar_busca = False
        self.selected_video_index = None
        
        # Sincroniza chamadas ao yt_dlp para evitar conflitos entre threads
        self.ytdlp_lock = threading.Lock()

        # VLC para preview
        self.vlc_instance = vlc.Instance('--no-xlib', '--no-video-title-show')
        self.preview_player = None
        self.preview_stop_after = None
        
        # Criar janela
        self.window = tk.Toplevel(parent)
        self.window.title("🎬 Buscar e Baixar Vídeos do YouTube")
        self.window.geometry("1000x700")
        self.window.configure(bg="#1a1a1a")
        self.window.transient(parent)
        
        self.setup_ui()
    
    def setup_ui(self):
        # HEADER
        header_frame = tk.Frame(self.window, bg="#2d2d2d", pady=15)
        header_frame.pack(fill=tk.X)
        
        tk.Label(
            header_frame,
            text="🎬 Buscar Vídeos de Karaoke no YouTube",
            bg="#2d2d2d",
            fg="#4CAF50",
            font=("Arial", 16, "bold")
        ).pack()
        
        # BUSCA
        search_frame = tk.Frame(self.window, bg="#1a1a1a", pady=10)
        search_frame.pack(fill=tk.X, padx=20)
        
        # Primeira linha: busca e quantidade
        search_row1 = tk.Frame(search_frame, bg="#1a1a1a")
        search_row1.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(
            search_row1,
            text="🔎 Buscar por:",
            bg="#1a1a1a",
            fg="white",
            font=("Arial", 11, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            search_row1,
            textvariable=self.search_var,
            font=("Arial", 12),
            width=40,
            bg="#2d2d2d",
            fg="white",
            insertbackground="white"
        )
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind("<Return>", lambda e: self.buscar_videos())
        
        # Controle de quantidade
        tk.Label(
            search_row1,
            text="Quantidade:",
            bg="#1a1a1a",
            fg="white",
            font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=(20, 5))
        
        self.quantidade_var = tk.IntVar(value=5)
        quantidade_spin = tk.Spinbox(
            search_row1,
            from_=1,
            to=10,
            increment=1,
            textvariable=self.quantidade_var,
            width=5,
            font=("Arial", 11),
            bg="#2d2d2d",
            fg="white",
            buttonbackground="#77BB79",
            justify="center"
        )
        quantidade_spin.pack(side=tk.LEFT, padx=5)
        
        tk.Label(
            search_row1,
            text="vídeos",
            bg="#1a1a1a",
            fg="#888",
            font=("Arial", 9)
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        # Segunda linha: botões
        search_row2 = tk.Frame(search_frame, bg="#1a1a1a")
        search_row2.pack(fill=tk.X)
        
        self.buscar_btn = tk.Button(
            search_row2,
            text="🔍 Buscar",
            command=self.buscar_videos,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15,
            pady=8,
            width=12
        )
        self.buscar_btn.pack(side=tk.LEFT, padx=5)
        
        self.parar_btn = tk.Button(
            search_row2,
            text="⏹️ Parar Busca",
            command=self.parar_busca,
            bg="#f44336",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15,
            pady=8,
            width=12,
            state=tk.DISABLED
        )
        self.parar_btn.pack(side=tk.LEFT, padx=5)
        
        tk.Label(
            search_row2,
            text="💡 Dica: Use termos como 'karaoke', 'instrumental', 'playback'",
            bg="#1a1a1a",
            fg="#666",
            font=("Arial", 8, "italic")
        ).pack(side=tk.LEFT, padx=20)
        
        # URL DIRETA
        url_frame = tk.Frame(self.window, bg="#1a1a1a", pady=5)
        url_frame.pack(fill=tk.X, padx=20)
        
        tk.Label(
            url_frame,
            text="🔗 Ou cole a URL:",
            bg="#1a1a1a",
            fg="white",
            font=("Arial", 11, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.url_var = tk.StringVar()
        self.url_entry = tk.Entry(
            url_frame,
            textvariable=self.url_var,
            font=("Arial", 11),
            width=50,
            bg="#2d2d2d",
            fg="white",
            insertbackground="white"
        )
        self.url_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            url_frame,
            text="⬇️ Baixar URL",
            command=self.baixar_url_direta,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        # CONTAINER PRINCIPAL (esquerda: lista, direita: preview)
        main_container = tk.Frame(self.window, bg="#1a1a1a")
        main_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # ESQUERDA - LISTA DE RESULTADOS
        left_frame = tk.Frame(main_container, bg="#1a1a1a")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        tk.Label(
            left_frame,
            text="📋 Resultados da Busca",
            bg="#1a1a1a",
            fg="#4CAF50",
            font=("Arial", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 5))
        
        # Treeview
        list_container = tk.Frame(left_frame, bg="#1a1a1a")
        list_container.pack(fill=tk.BOTH, expand=True)
        
        columns = ("Título", "Canal", "Duração")
        self.tree = ttk.Treeview(
            list_container,
            columns=columns,
            show="headings",
            height=15
        )
        
        self.tree.heading("Título", text="Título")
        self.tree.heading("Canal", text="Canal")
        self.tree.heading("Duração", text="Duração")
        
        self.tree.column("Título", width=300)
        self.tree.column("Canal", width=150)
        self.tree.column("Duração", width=80, anchor="center")
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(list_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<<TreeviewSelect>>", self.on_video_select)
        self.tree.bind("<Double-1>", lambda e: self.baixar_video_selecionado())
        
        # DIREITA - PREVIEW
        right_frame = tk.Frame(main_container, bg="#2d2d2d", width=400, relief=tk.RIDGE, bd=2)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_frame.pack_propagate(False)
        
        tk.Label(
            right_frame,
            text="🎥 Preview do Vídeo",
            bg="#2d2d2d",
            fg="#4CAF50",
            font=("Arial", 12, "bold")
        ).pack(pady=10)
        
        # Frame do vídeo
        self.preview_frame = tk.Frame(right_frame, bg="#000000", width=310, height=164)
        self.preview_frame.pack(padx=11, pady=6)
        self.preview_frame.pack_propagate(False)
        
        self.preview_label = tk.Label(
            self.preview_frame,
            text="Selecione um vídeo\npara ver o preview",
            bg="#000000",
            fg="#666666",
            font=("Arial", 11)
        )
        self.preview_label.pack(expand=True)
        
        # Informações do vídeo
        info_frame = tk.Frame(right_frame, bg="#2d2d2d")
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.info_titulo = tk.Label(
            info_frame,
            text="",
            bg="#2d2d2d",
            fg="white",
            font=("Arial", 10, "bold"),
            wraplength=360,
            justify=tk.LEFT
        )
        self.info_titulo.pack(anchor=tk.W, pady=2)
        
        self.info_canal = tk.Label(
            info_frame,
            text="",
            bg="#2d2d2d",
            fg="#BBB",
            font=("Arial", 9),
            justify=tk.LEFT
        )
        self.info_canal.pack(anchor=tk.W, pady=2)
        
        self.info_duracao = tk.Label(
            info_frame,
            text="",
            bg="#2d2d2d",
            fg="#BBB",
            font=("Arial", 9),
            justify=tk.LEFT
        )
        self.info_duracao.pack(anchor=tk.W, pady=2)
                
        # Botões de baixar e preview lado a lado
        botoes_preview_frame = tk.Frame(right_frame, bg="#2d2d2d")
        botoes_preview_frame.pack(pady=(10, 5))

        tk.Button(
            botoes_preview_frame,
            text="⬇️ Baixar Selecionado",
            command=self.baixar_video_selecionado,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15,
            pady=10
        ).pack(side=tk.LEFT, padx=(0, 5))

        self.preview_btn = tk.Button(
            botoes_preview_frame,
            text="▶️ Preview (10s)",
            command=self.tocar_preview,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            state=tk.DISABLED,
            padx=20,
            pady=10
        )
        self.preview_btn.pack(side=tk.LEFT, padx=(5, 0))

        self.adicionar_lista_btn = tk.Button(
            botoes_preview_frame,
            text="➕ Adicionar à Lista",
            command=self.adicionar_a_lista,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            state=tk.DISABLED,
            padx=15,
            pady=10
        )
        self.adicionar_lista_btn.pack(side=tk.LEFT, padx=(5, 0))

        # Botão de stop (inicialmente escondido/desabilitado)
        self.stop_btn = tk.Button(
            right_frame,
            text="⏹️ Parar",
            command=self.parar_preview,
            bg="#f44336",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            state=tk.DISABLED,
            padx=20,
            pady=8
        )
        self.stop_btn.pack(pady=5)
        
        # BARRA DE PROGRESSO
        self.progress_frame = tk.Frame(self.window, bg="#1a1a1a")
        self.progress_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.progress_label = tk.Label(
            self.progress_frame,
            text="",
            bg="#1a1a1a",
            fg="#4CAF50",
            font=("Arial", 9, "bold")
        )
        self.progress_label.pack()
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='determinate',
            length=900
        )
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        # BOTÕES INFERIORES
        bottom_frame = tk.Frame(self.window, bg="#1a1a1a", pady=15)
        bottom_frame.pack(fill=tk.X, padx=20)

        tk.Label(
            bottom_frame,
            text=f"📂 Pasta destino: {self.music_folder}",
            bg="#1a1a1a",
            fg="#888",
            font=("Arial", 9)
        ).pack(side=tk.LEFT, padx=20)
        
        tk.Button(
            bottom_frame,
            text="❌ Fechar",
            command=self.fechar,
            bg="#666",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=20,
            pady=12
        ).pack(side=tk.RIGHT, padx=5)

    def buscar_videos(self):
        """Busca vídeos no YouTube"""
        if self.busca_em_progresso:
            messagebox.showwarning("Atenção", "Já há uma busca em andamento!")
            return
            
        termo = self.search_var.get().strip()
        if not termo:
            messagebox.showwarning("Atenção", "Digite um termo de busca!")
            return
        
        quantidade = self.quantidade_var.get()
        
        self.busca_em_progresso = True
        self.cancelar_busca = False
        self.buscar_btn.config(state=tk.DISABLED)
        self.parar_btn.config(state=tk.NORMAL)
        
        self.progress_label.config(text=f"🔍 Buscando {quantidade} vídeos: {termo}...")
        self.progress_bar.config(mode='indeterminate')
        self.progress_bar.start()
        
        def buscar():
            try:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': True,
                }
                
                with self.ytdlp_lock:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        # Verifica cancelamento antes de iniciar
                        if self.cancelar_busca:
                            self.window.after(0, lambda: self.progress_label.config(
                                text="⚠️ Busca cancelada pelo usuário"
                            ))
                            return
                        
                        resultado = ydl.extract_info(
                            f"ytsearch{quantidade}:{termo}",
                            download=False
                        )
                    
                    # Verifica cancelamento após busca
                    if self.cancelar_busca:
                        self.window.after(0, lambda: self.progress_label.config(
                            text="⚠️ Busca cancelada pelo usuário"
                        ))
                        return
                    
                    self.videos_encontrados = []
                    if 'entries' in resultado:
                        for video in resultado['entries']:
                            # Verifica cancelamento durante processamento
                            if self.cancelar_busca:
                                self.window.after(0, lambda: self.progress_label.config(
                                    text="⚠️ Busca cancelada pelo usuário"
                                ))
                                return
                            
                            duracao = video.get('duration', 0)
                            duracao_min = int(duracao // 60)  # Converte para int
                            duracao_sec = int(duracao % 60)   # Converte para int
                            
                            self.videos_encontrados.append({
                                'titulo': video.get('title', 'Sem título'),
                                'url': f"https://www.youtube.com/watch?v={video['id']}",
                                'duracao': duracao,
                                'duracao_str': f"{duracao_min}:{duracao_sec:02d}",
                                'canal': video.get('channel', 'Desconhecido'),
                                'thumbnail': video.get('thumbnail', ''),
                                'arquivo_local': None
                            })
                
                if not self.cancelar_busca:
                    self.window.after(0, self.atualizar_lista)
                
            except Exception as ex:
                error_msg = str(ex)
                if not self.cancelar_busca:
                    self.window.after(0, lambda msg=error_msg: messagebox.showerror(
                        "Erro",
                        f"Erro ao buscar vídeos:\n{msg}"
                    ))
            finally:
                self.window.after(0, self.finalizar_busca)
        
        threading.Thread(target=buscar, daemon=True).start()
    
    def parar_busca(self):
        """Para a busca em andamento"""
        if self.busca_em_progresso:
            self.cancelar_busca = True
            self.progress_label.config(text="⏹️ Parando busca...")
            self.parar_btn.config(state=tk.DISABLED)
    
    def finalizar_busca(self):
        """Finaliza o estado da busca"""
        self.busca_em_progresso = False
        self.cancelar_busca = False
        self.buscar_btn.config(state=tk.NORMAL)
        self.parar_btn.config(state=tk.DISABLED)
        self.parar_progress()
    
    def atualizar_lista(self):
        """Atualiza a lista de vídeos encontrados"""
        self.tree.delete(*self.tree.get_children())
        
        for video in self.videos_encontrados:
            self.tree.insert("", tk.END, values=(
                video['titulo'][:50] + "..." if len(video['titulo']) > 50 else video['titulo'],
                video['canal'],
                video['duracao_str']
            ))
        
        if self.videos_encontrados:
            self.progress_label.config(
                text=f"✅ {len(self.videos_encontrados)} vídeos encontrados"
            )
        else:
            self.progress_label.config(text="⚠️ Nenhum vídeo encontrado")
    
    def on_video_select(self, event):
        """Quando seleciona um vídeo na lista"""
        selection = self.tree.selection()
        if not selection:
            return
        
        index = self.tree.index(selection[0])
        if index >= len(self.videos_encontrados):
            return
        
        video = self.videos_encontrados[index]
        self.selected_video_index = index

        # Atualiza informações
        self.info_titulo.config(text=f"🎵 {video['titulo']}")
        self.info_canal.config(text=f"📺 Canal: {video['canal']}")
        self.info_duracao.config(text=f"⏱️ Duração: {video['duracao_str']}")

        self.adicionar_lista_btn.config(state=tk.NORMAL)

        arquivo_local = video.get('arquivo_local')
        if arquivo_local and os.path.exists(arquivo_local):
            self.preview_btn.config(state=tk.NORMAL, text="▶️ Preview (10s)")
            if not self.preview_label.winfo_ismapped():
                self.preview_label.pack(expand=True)
            self.preview_label.config(text="Clique para assistir ao preview")
        else:
            self.preview_btn.config(state=tk.DISABLED, text="▶️ Preview (10s)")
            # Garante que o label esteja visível informando o usuário
            if not self.preview_label.winfo_ismapped():
                self.preview_label.pack(expand=True)
            self.preview_label.config(text="Baixe o vídeo para habilitar o preview")

    def tocar_preview(self):
        """Toca preview de 10 segundos do vídeo selecionado"""
        selection = self.tree.selection()
        if not selection:
            return
        
        index = self.tree.index(selection[0])
        video = self.videos_encontrados[index]
        
        arquivo_local = video.get('arquivo_local')
        if not arquivo_local or not os.path.exists(arquivo_local):
            if messagebox.askyesno(
                "Preview indisponível",
                "É necessário baixar o vídeo para ver o preview. Deseja baixar agora?"
            ):
                self.baixar_video(video['url'], video['titulo'], video_item=video, auto_preview=True)
            return

        self.preview_label.config(text="⏳ Carregando preview...")
        self.preview_btn.config(state=tk.DISABLED, text="⏳ Carregando...")
        
        def carregar_preview():
            try:
                # Para player anterior se existir
                if self.preview_player:
                    self.preview_player.stop()

                # Cria novo player
                self.preview_player = self.vlc_instance.media_player_new()
                media = self.vlc_instance.media_new(arquivo_local)
                
                # Embute na janela
                self.window.update()
                if os.name == 'nt':
                    hwnd = self.preview_frame.winfo_id()
                    self.preview_player.set_hwnd(hwnd)
                else:
                    xid = self.preview_frame.winfo_id()
                    self.preview_player.set_xwindow(xid)
                
                self.preview_player.set_media(media)
                
                # Inicia reprodução
                self.preview_player.play()
                
                # Atualiza botões
                self.window.after(0, lambda: self.preview_label.pack_forget())
                self.window.after(0, lambda: self.atualizar_controles_preview(True))

                # Para automaticamente após 10 segundos de preview
                self._agendar_parada_preview()
                
            except Exception as ex:
                error_msg = str(ex)
                self.window.after(0, lambda msg=error_msg: messagebox.showerror(
                    "Erro",
                    f"Erro ao carregar preview:\n{msg}"
                ))
                self.window.after(0, lambda: self.atualizar_controles_preview(False))
                self.window.after(0, lambda: self.preview_label.config(
                    text="❌ Erro ao carregar"
                ))
        
        threading.Thread(target=carregar_preview, daemon=True).start()
    
    def _agendar_parada_preview(self):
        """Agenda parada automática do preview em 10 segundos."""
        self._cancelar_parada_preview()
        self.preview_stop_after = self.window.after(10000, self._parar_preview_automatico)

    def _cancelar_parada_preview(self):
        """Cancela parada automática agendada, se houver."""
        if self.preview_stop_after is not None:
            try:
                self.window.after_cancel(self.preview_stop_after)
            except Exception:
                pass
            self.preview_stop_after = None

    def _parar_preview_automatico(self):
        """Encerra o preview automaticamente caso ainda esteja tocando."""
        self.preview_stop_after = None
        if self.preview_player and self.preview_player.is_playing():
            self.parar_preview()


    def atualizar_controles_preview(self, playing):
        """Atualiza os controles do preview"""
        if playing:
            self.preview_btn.config(
                text="⏸️ Pausar",
                command=self.pausar_preview,
                bg="#FF9800",
                state=tk.NORMAL
            )
            
            # Adiciona botão de stop se não existir
            if not hasattr(self, 'stop_btn'):
                self.stop_btn = tk.Button(
                    self.right_frame,  # Você precisa referenciar o frame correto
                    text="⏹️ Parar",
                    command=self.parar_preview,
                    bg="#f44336",
                    fg="white",
                    font=("Arial", 10, "bold"),
                    cursor="hand2",
                    padx=15,
                    pady=8
                )
                self.stop_btn.pack(pady=5)
            else:
                self.stop_btn.config(state=tk.NORMAL)
        else:
            self.preview_btn.config(
                text="▶️ Tocar Preview",
                command=self.tocar_preview,
                bg="#4CAF50",
                state=tk.NORMAL
            )
            if hasattr(self, 'stop_btn'):
                self.stop_btn.config(state=tk.DISABLED)

    def pausar_preview(self):
        """Pausa ou retoma o preview"""
        if self.preview_player:
            if self.preview_player.is_playing():
                self.preview_player.pause()
                self.preview_btn.config(
                    text="▶️ Retomar",
                    command=self.retomar_preview,
                    bg="#4CAF50"
                )
            else:
                self.retomar_preview()

    def retomar_preview(self):
        """Retoma o preview pausado"""
        if self.preview_player:
            self.preview_player.play()
            self.preview_btn.config(
                text="⏸️ Pausar",
                command=self.pausar_preview,
                bg="#FF9800"
            )

    def parar_preview(self):
        """Para completamente o preview"""
        self._cancelar_parada_preview()
        if self.preview_player:
            self.preview_player.stop()
            self.preview_label.config(text="Preview parado")
            self.preview_label.pack(expand=True)
            self.preview_btn.config(
                text="▶️ Tocar Preview",
                command=self.tocar_preview,
                bg="#4CAF50"
            )
            if hasattr(self, 'stop_btn'):
                self.stop_btn.config(state=tk.DISABLED)
                
    def baixar_video_selecionado(self):
        """Baixa o vídeo selecionado"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Atenção", "Selecione um vídeo!")
            return
        
        index = self.tree.index(selection[0])
        video = self.videos_encontrados[index]
        
        self.baixar_video(video['url'], video['titulo'], video_item=video)

    def adicionar_a_lista(self):
        """Adiciona o vídeo selecionado como item da playlist de execução no main.py"""
        selection = self.tree.selection()
        if not selection:
            return

        index = self.tree.index(selection[0])
        video = self.videos_encontrados[index]

        if not self.main_app:
            messagebox.showerror("Erro", "Não foi possível adicionar: painel principal indisponível.")
            return

        arquivo_local = video.get('arquivo_local')
        if not arquivo_local or not os.path.exists(arquivo_local):
            if messagebox.askyesno(
                "Vídeo não baixado",
                "É necessário baixar o vídeo antes de adicioná-lo à lista. Deseja baixar agora?"
            ):
                self.baixar_video(video['url'], video['titulo'], video_item=video, auto_adicionar=True)
            return

        cantor = video.get('canal') or "YouTube"
        musica = video.get('titulo')
        self.main_app.debug_log(f"📥 Adicionando à lista de execução: {musica} ({cantor})")

        if self.main_app.modo_evento_ativo:
            self.main_app.adicionar_musica_evento(arquivo_local, cantor, musica, "YT")
        else:
            self.main_app.adicionar_musica_playlist_simples(arquivo_local, cantor, musica, "YT")

    def baixar_url_direta(self):
        """Baixa vídeo de uma URL direta"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Atenção", "Cole uma URL do YouTube!")
            return
        
        if 'youtube.com' not in url and 'youtu.be' not in url:
            messagebox.showerror("Erro", "URL inválida! Use uma URL do YouTube.")
            return
        
        self.baixar_video(url)
        
    def baixar_video(self, url, titulo=None, video_item=None, auto_preview=False, auto_adicionar=False):
        """Baixa um vídeo do YouTube"""
        if self.download_em_progresso:
            messagebox.showwarning("Aguarde", "Já há um download em progresso!")
            return
        
        self.download_em_progresso = True
        self.progress_bar.config(mode='determinate')
        self.progress_bar['value'] = 0
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    
                    if total > 0:
                        percent = (downloaded / total) * 100
                        self.window.after(0, lambda: self.progress_bar.config(value=percent))
                        
                        speed = d.get('speed', 0)
                        speed_str = f"{speed/1024/1024:.1f} MB/s" if speed else "..."
                        
                        self.window.after(0, lambda: self.progress_label.config(
                            text=f"⬇️ Baixando: {percent:.1f}% | Velocidade: {speed_str}"
                        ))
                except:
                    pass
            
            elif d['status'] == 'finished':
                self.window.after(0, lambda: self.progress_label.config(
                    text="✅ Download concluído!"
                ))
        
        def baixar():
            try:
                self.window.after(0, lambda: self.progress_label.config(
                    text="🔄 Preparando download..."
                ))
                
                ydl_opts = {
                    'format': 'bestvideo+bestaudio/best',
                    'outtmpl': str(Path(self.music_folder) / '%(title)s.%(ext)s'),
                    'progress_hooks': [progress_hook],
                    'merge_output_format': 'mp4',
                    'noplaylist': True,  # IMPORTANTE: não baixar playlists
                }
                
                with self.ytdlp_lock:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        arquivo = ydl.prepare_filename(info)
                        
                        # Se baixou vídeo e áudio separados, junta-los
                        if '_' in os.path.basename(arquivo):
                            # Remove o sufixo de arquivos separados
                            base_name = os.path.splitext(os.path.basename(arquivo))[0]
                            if base_name.endswith('.f' + info.get('format_id', '')):
                                base_name = base_name.rsplit('.', 1)[0]
                            arquivo = os.path.join(self.music_folder, base_name + '.mp4')
                
                def pos_download():
                    if video_item is not None:
                        video_item['arquivo_local'] = arquivo
                        if (self.selected_video_index is not None and
                                self.videos_encontrados[self.selected_video_index] is video_item):
                            self.preview_btn.config(state=tk.NORMAL, text="▶️ Preview (10s)")
                            if not self.preview_label.winfo_ismapped():
                                self.preview_label.pack(expand=True)
                            self.preview_label.config(text="Clique para assistir ao preview")
                        if auto_preview and video_item in self.videos_encontrados:
                            # Garante que o preview será iniciado assim que o download terminar
                            self.tocar_preview()
                        if auto_adicionar and video_item in self.videos_encontrados:
                            # Adiciona à lista de execução assim que o download terminar
                            self.adicionar_a_lista()

                self.window.after(0, lambda: messagebox.showinfo(
                    "Sucesso",
                    f"✅ Vídeo baixado com sucesso!\n\n"
                    f"📁 {os.path.basename(arquivo)}\n\n"
                    f"Local: {self.music_folder}"
                ))
                self.window.after(0, pos_download)
                self.window.after(0, lambda: self.progress_bar.config(value=100))
                
            except Exception as ex:
                error_msg = str(ex)
                self.window.after(0, lambda msg=error_msg: messagebox.showerror(
                    "Erro",
                    f"❌ Erro ao baixar vídeo:\n{msg}"
                ))
            
            finally:
                self.download_em_progresso = False
                self.window.after(0, self.parar_progress)
        
        threading.Thread(target=baixar, daemon=True).start()
        
    def parar_progress(self):
        """Para a barra de progresso"""
        self.progress_bar.stop()
        self.progress_bar.config(mode='determinate')
    
    def fechar(self):
        """Fecha a janela"""
        if self.preview_player:
            self.preview_player.stop()
        self.window.destroy()