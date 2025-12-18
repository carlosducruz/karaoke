import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from PIL import Image, ImageTk
import os
from karaoke_database import KaraokeDatabase

class ModoEventoWindow:
    """Janela do Modo Evento - Gerenciamento completo de evento de karaoke"""
    
    def __init__(self, parent, karaoke_player):
        self.parent = parent
        self.karaoke_player = karaoke_player
        self.db = KaraokeDatabase()
        
        self.window = tk.Toplevel(parent)
        self.window.title("Modo Evento - Karaoke")
        self.window.geometry("800x600")
        self.window.configure(bg="#1a1a1a")
        
        self.evento_atual = None
        self.avatars = {}  # Cache de avatares
        
        self.verificar_evento_ativo()
        
    def verificar_evento_ativo(self):
        """Verifica se há evento ativo ou cria novo"""
        evento = self.db.obter_evento_ativo()
        
        if evento:
            resposta = messagebox.askyesno(
                "Evento Ativo",
                f"Existe um evento ativo:\n\n'{evento['nome']}'\n\n"
                f"Deseja continuar este evento?",
                parent=self.window
            )
            
            if resposta:
                self.evento_atual = evento
                self.mostrar_tela_playlist()
            else:
                self.mostrar_tela_novo_evento()
        else:
            self.mostrar_tela_novo_evento()
    
    def mostrar_tela_novo_evento(self):
        """Tela para criar novo evento"""
        self.limpar_janela()
        
        frame = tk.Frame(self.window, bg="#1a1a1a")
        frame.pack(expand=True)
        
        tk.Label(
            frame,
            text="🎤 Criar Novo Evento de Karaoke",
            bg="#1a1a1a",
            fg="white",
            font=("Arial", 18, "bold")
        ).pack(pady=20)
        
        # Nome do evento
        tk.Label(
            frame,
            text="Nome do Evento:",
            bg="#1a1a1a",
            fg="white",
            font=("Arial", 12)
        ).pack(pady=10)
        
        self.nome_evento_entry = tk.Entry(
            frame,
            font=("Arial", 14),
            width=30
        )
        self.nome_evento_entry.pack(pady=10)
        self.nome_evento_entry.insert(0, "Karaoke Night")
        
        tk.Button(
            frame,
            text="Criar Evento",
            command=self.criar_evento,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold"),
            cursor="hand2",
            padx=20,
            pady=10
        ).pack(pady=20)
        
        tk.Button(
            frame,
            text="Voltar",
            command=self.window.destroy,
            bg="#666666",
            fg="white",
            font=("Arial", 10),
            cursor="hand2",
            padx=15,
            pady=5
        ).pack(pady=10)
    
    def criar_evento(self):
        """Cria um novo evento"""
        nome = self.nome_evento_entry.get().strip()
        
        if not nome:
            messagebox.showerror(
                "Erro",
                "Digite um nome para o evento!",
                parent=self.window
            )
            return
        
        evento_id = self.db.criar_evento(nome)
        self.evento_atual = {
            'id': evento_id,
            'nome': nome
        }
        
        messagebox.showinfo(
            "Sucesso",
            f"Evento '{nome}' criado com sucesso!",
            parent=self.window
        )
        
        self.mostrar_tela_participantes()
    
    def mostrar_tela_participantes(self):
        """Tela para adicionar participantes"""
        self.limpar_janela()
        
        # Header
        header = tk.Frame(self.window, bg="#2d2d2d", pady=10)
        header.pack(fill=tk.X)
        
        tk.Label(
            header,
            text=f"👥 Participantes - {self.evento_atual['nome']}",
            bg="#2d2d2d",
            fg="white",
            font=("Arial", 16, "bold")
        ).pack()
        
        # Lista de participantes
        list_frame = tk.Frame(self.window, bg="#1a1a1a")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Canvas com scrollbar
        canvas = tk.Canvas(list_frame, bg="#1a1a1a", highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.participantes_frame = tk.Frame(canvas, bg="#1a1a1a")
        
        self.participantes_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.participantes_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.atualizar_lista_participantes()
        
        # Botões
        btn_frame = tk.Frame(self.window, bg="#1a1a1a", pady=10)
        btn_frame.pack(fill=tk.X)
        
        tk.Button(
            btn_frame,
            text="➕ Adicionar Participante",
            command=self.adicionar_participante,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 12, "bold"),
            cursor="hand2",
            padx=15,
            pady=8
        ).pack(pady=5)
        
        tk.Button(
            btn_frame,
            text="▶ Continuar para Playlist",
            command=self.mostrar_tela_playlist,
            bg="#2196F3",
            fg="white",
            font=("Arial", 12, "bold"),
            cursor="hand2",
            padx=15,
            pady=8
        ).pack(pady=5)
    
    def atualizar_lista_participantes(self):
        """Atualiza a lista visual de participantes"""
        # Limpar frame
        for widget in self.participantes_frame.winfo_children():
            widget.destroy()
        
        participantes = self.db.obter_participantes(self.evento_atual['id'])
        
        if not participantes:
            tk.Label(
                self.participantes_frame,
                text="Nenhum participante adicionado ainda.\nClique em 'Adicionar Participante' para começar!",
                bg="#1a1a1a",
                fg="#888888",
                font=("Arial", 12),
                justify=tk.CENTER
            ).pack(pady=50)
            return
        
        for part in participantes:
            self.criar_card_participante(part)
    
    def criar_card_participante(self, participante):
        """Cria um card visual para o participante"""
        card = tk.Frame(
            self.participantes_frame,
            bg="#2d2d2d",
            relief=tk.RAISED,
            bd=2
        )
        card.pack(fill=tk.X, pady=5, padx=10)
        
        # Avatar
        avatar_label = tk.Label(card, bg="#2d2d2d")
        avatar_label.pack(side=tk.LEFT, padx=10, pady=10)
        
        if participante['avatar_path'] and os.path.exists(participante['avatar_path']):
            try:
                img = Image.open(participante['avatar_path'])
                img = img.resize((60, 60), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                avatar_label.config(image=photo)
                avatar_label.image = photo
                self.avatars[participante['id']] = photo
            except:
                avatar_label.config(
                    text="👤",
                    font=("Arial", 40),
                    fg="white"
                )
        else:
            avatar_label.config(
                text="👤",
                font=("Arial", 40),
                fg="white"
            )
        
        # Info
        info_frame = tk.Frame(card, bg="#2d2d2d")
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        tk.Label(
            info_frame,
            text=participante['nome'],
            bg="#2d2d2d",
            fg="white",
            font=("Arial", 14, "bold")
        ).pack(anchor=tk.W)
        
        tk.Label(
            info_frame,
            text=f"Pontuação: {participante['pontuacao']:.0f} pts",
            bg="#2d2d2d",
            fg="#4CAF50",
            font=("Arial", 11)
        ).pack(anchor=tk.W)

        # Botão Excluir Participante
        def excluir_participante():
            if messagebox.askyesno("Excluir Participante", f"Tem certeza que deseja excluir o participante '{participante['nome']}' e todas as suas músicas?", parent=self.window):
                self.db.remover_participante(participante['id'])
                self.atualizar_lista_participantes()

        excluir_btn = tk.Button(
            card,
            text="🗑 Excluir",
            command=excluir_participante,
            bg="#f44336",
            fg="white",
            font=("Arial", 9, "bold"),
            cursor="hand2",
            padx=10,
            pady=4
        )
        excluir_btn.pack(side=tk.RIGHT, padx=8, pady=4)
    def adicionar_participante(self):
        """Dialog para adicionar novo participante"""
        dialog = tk.Toplevel(self.window)
        dialog.title("Adicionar Participante")
        dialog.geometry("400x250")
        dialog.configure(bg="#1a1a1a")
        dialog.transient(self.window)
        dialog.grab_set()
        
        tk.Label(
            dialog,
            text="Nome do Participante:",
            bg="#1a1a1a",
            fg="white",
            font=("Arial", 11)
        ).pack(pady=10)
        
        nome_entry = tk.Entry(dialog, font=("Arial", 12), width=25)
        nome_entry.pack(pady=5)
        nome_entry.focus()
        
        avatar_path_var = tk.StringVar()
        
        def escolher_avatar():
            path = filedialog.askopenfilename(
                title="Escolher Avatar",
                filetypes=[
                    ("Imagens", "*.png *.jpg *.jpeg *.gif"),
                    ("Todos", "*.*")
                ],
                parent=dialog
            )
            if path:
                avatar_path_var.set(path)
                avatar_btn.config(text=f"✓ {os.path.basename(path)[:20]}")
        
        avatar_btn = tk.Button(
            dialog,
            text="📷 Escolher Avatar (opcional)",
            command=escolher_avatar,
            bg="#666666",
            fg="white",
            font=("Arial", 10),
            cursor="hand2",
            padx=10,
            pady=5
        )
        avatar_btn.pack(pady=10)
        
        def salvar():
            nome = nome_entry.get().strip()
            if not nome:
                messagebox.showerror("Erro", "Digite um nome!", parent=dialog)
                return
            
            avatar_path = avatar_path_var.get() or None
            self.db.adicionar_participante(
                self.evento_atual['id'],
                nome,
                avatar_path
            )
            
            self.atualizar_lista_participantes()
            dialog.destroy()
        
        tk.Button(
            dialog,
            text="Adicionar",
            command=salvar,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=20,
            pady=8
        ).pack(pady=15)
    
    def mostrar_tela_playlist(self):
        """Tela principal da playlist do evento"""
        self.limpar_janela()
        
        # Header
        header = tk.Frame(self.window, bg="#2d2d2d", pady=10)
        header.pack(fill=tk.X)
        
        tk.Label(
            header,
            text=f"🎵 Playlist - {self.evento_atual['nome']}",
            bg="#2d2d2d",
            fg="white",
            font=("Arial", 16, "bold")
        ).pack()
        
        # Playlist
        self.criar_area_playlist()
        
        # Botões de controle
        self.criar_controles_evento()
    
    def criar_area_playlist(self):
        """Cria a área da playlist"""
        list_frame = tk.Frame(self.window, bg="#1a1a1a")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        canvas = tk.Canvas(list_frame, bg="#1a1a1a", highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.playlist_frame = tk.Frame(canvas, bg="#1a1a1a")
        
        self.playlist_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.playlist_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.atualizar_playlist()
    
    def atualizar_playlist(self):
        """Atualiza a visualização da playlist"""
        for widget in self.playlist_frame.winfo_children():
            widget.destroy()
        
        playlist = self.db.obter_playlist(self.evento_atual['id'])
        
        if not playlist:
            tk.Label(
                self.playlist_frame,
                text="Playlist vazia.\nAdicione músicas para começar!",
                bg="#1a1a1a",
                fg="#888888",
                font=("Arial", 12)
            ).pack(pady=50)
            return
        
        for musica in playlist:
            self.criar_item_playlist(musica)
    
    def criar_item_playlist(self, musica):
        """Cria um item da playlist"""
        bg_color = "#2d2d2d" if not musica['ja_tocou'] else "#1a3a1a"
        
        item = tk.Frame(self.playlist_frame, bg=bg_color, relief=tk.RAISED, bd=1)
        item.pack(fill=tk.X, pady=2, padx=5)
        
        # Ordem
        tk.Label(
            item,
            text=f"#{musica['ordem']}",
            bg=bg_color,
            fg="#888888",
            font=("Arial", 10, "bold"),
            width=4
        ).pack(side=tk.LEFT, padx=5)
        
        # Status
        status_icon = "✓" if musica['ja_tocou'] else "▶"
        status_color = "#4CAF50" if musica['ja_tocou'] else "#FFA500"
        
        tk.Label(
            item,
            text=status_icon,
            bg=bg_color,
            fg=status_color,
            font=("Arial", 12, "bold"),
            width=2
        ).pack(side=tk.LEFT)
        
        # Info
        info_frame = tk.Frame(item, bg=bg_color)
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        nome_arquivo = os.path.basename(musica['arquivo_path'])
        tk.Label(
            info_frame,
            text=nome_arquivo[:40],
            bg=bg_color,
            fg="white",
            font=("Arial", 11)
        ).pack(anchor=tk.W)
        
        detalhes = f"🎤 {musica['participante_nome']}"
        if musica['tom_ajuste'] != 0:
            detalhes += f" | Tom: {musica['tom_ajuste']:+d}"
        
        tk.Label(
            info_frame,
            text=detalhes,
            bg=bg_color,
            fg="#888888",
            font=("Arial", 9)
        ).pack(anchor=tk.W)

        # Botão Excluir
        def excluir_musica():
            if messagebox.askyesno("Excluir Música", "Tem certeza que deseja excluir esta música da playlist?", parent=self.window):
                self.db.remover_musica_playlist(musica['id'])
                self.atualizar_playlist()

        excluir_btn = tk.Button(
            item,
            text="🗑 Excluir",
            command=excluir_musica,
            bg="#f44336",
            fg="white",
            font=("Arial", 9, "bold"),
            cursor="hand2",
            padx=10,
            pady=4
        )
        excluir_btn.pack(side=tk.RIGHT, padx=8, pady=4)
    def criar_controles_evento(self):
        """Cria os botões de controle do evento"""
        ctrl_frame = tk.Frame(self.window, bg="#1a1a1a", pady=10)
        ctrl_frame.pack(fill=tk.X)
        
        # Linha 1 de botões - Ações principais
        linha1_frame = tk.Frame(ctrl_frame, bg="#1a1a1a")
        linha1_frame.pack()
        
            
        tk.Button(
            linha1_frame,
            text="➕ Adicionar Música",
            command=self.adicionar_musica,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            linha1_frame,
            text="👥 Ver Participantes",
            command=self.mostrar_tela_participantes,
            bg="#2196F3",
            fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        # Linha 2 de botões - Controles de evento
        linha2_frame = tk.Frame(ctrl_frame, bg="#1a1a1a")
        linha2_frame.pack(pady=10)
        
        tk.Button(
            linha2_frame,
            text="▶ Iniciar Evento",
            command=self.iniciar_evento,
            bg="#2196F3",
            fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            linha2_frame,
            text="🏆 Ver Ranking",
            command=self.mostrar_ranking,
            bg="#FF9800",
            fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
        
        tk.Button(
            linha2_frame,
            text="❌ Finalizar Evento",
            command=self.finalizar_evento,
            bg="#f44336",
            fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=15,
            pady=8
        ).pack(side=tk.LEFT, padx=5)
    
    def adicionar_musica(self):
        """Dialog para adicionar música à playlist"""
        participantes = self.db.obter_participantes(self.evento_atual['id'])
        
        if not participantes:
            messagebox.showwarning(
                "Aviso",
                "Adicione participantes antes de criar a playlist!",
                parent=self.window
            )
            self.mostrar_tela_participantes()
            return
        
        dialog = tk.Toplevel(self.window)
        dialog.title("Adicionar Música")
        dialog.geometry("450x300")
        dialog.configure(bg="#1a1a1a")
        dialog.transient(self.window)
        dialog.grab_set()
        
        tk.Label(
            dialog,
            text="Participante:",
            bg="#1a1a1a",
            fg="white",
            font=("Arial", 11)
        ).pack(pady=10)
        
        participante_var = tk.StringVar()
        participante_combo = ttk.Combobox(
            dialog,
            textvariable=participante_var,
            values=[p['nome'] for p in participantes],
            state="readonly",
            font=("Arial", 11),
            width=30
        )
        participante_combo.pack(pady=5)
        participante_combo.current(0)
        
        arquivo_var = tk.StringVar()
        
        def escolher_arquivo():
            path = filedialog.askopenfilename(
                title="Escolher Música MP4",
                filetypes=[
                    ("Arquivos MP4", "*.mp4"),
                    ("Todos", "*.*")
                ],
                parent=dialog
            )
            if path:
                arquivo_var.set(path)
                arquivo_btn.config(text=f"✓ {os.path.basename(path)[:30]}")
        
        arquivo_btn = tk.Button(
            dialog,
            text="🎵 Escolher Arquivo MP4",
            command=escolher_arquivo,
            bg="#666666",
            fg="white",
            font=("Arial", 10),
            cursor="hand2",
            padx=10,
            pady=8
        )
        arquivo_btn.pack(pady=15)
        
        tom_frame = tk.Frame(dialog, bg="#1a1a1a")
        tom_frame.pack(pady=10)
        
        tk.Label(
            tom_frame,
            text="Tom:",
            bg="#1a1a1a",
            fg="white",
            font=("Arial", 10)
        ).pack(side=tk.LEFT, padx=5)
        
        tom_var = tk.IntVar(value=0)
        tom_spin = tk.Spinbox(
            tom_frame,
            from_=-12,
            to=12,
            textvariable=tom_var,
            width=5,
            font=("Arial", 11)
        )
        tom_spin.pack(side=tk.LEFT)
        
        def salvar():
            if not arquivo_var.get():
                messagebox.showerror("Erro", "Escolha um arquivo!", parent=dialog)
                return
            
            # Encontrar ID do participante
            nome_selecionado = participante_var.get()
            participante_id = None
            for p in participantes:
                if p['nome'] == nome_selecionado:
                    participante_id = p['id']
                    break
            
            self.db.adicionar_musica_playlist(
                self.evento_atual['id'],
                participante_id,
                arquivo_var.get(),
                tom_var.get()
            )
            
            self.atualizar_playlist()
            dialog.destroy()
        
        tk.Button(
            dialog,
            text="Adicionar à Playlist",
            command=salvar,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 11, "bold"),
            cursor="hand2",
            padx=20,
            pady=8
        ).pack(pady=15)
    
    def iniciar_evento(self):
        """Inicia a reprodução sequencial do evento"""
        proxima = self.db.obter_proxima_musica(self.evento_atual['id'])
        
        if not proxima:
            messagebox.showinfo(
                "Fim do Evento",
                "Todas as músicas já foram tocadas!\n\nVeja o ranking final.",
                parent=self.window
            )
            self.mostrar_ranking()
            return
        
        # Fechar janela de evento e iniciar no player principal
        self.window.destroy()
        
        # Configurar player para modo evento
        self.karaoke_player.iniciar_modo_evento(
            self.evento_atual['id'],
            proxima
        )
    
    def mostrar_ranking(self):
        """Mostra o ranking final"""
        ranking = self.db.obter_ranking(self.evento_atual['id'])
        
        rank_window = tk.Toplevel(self.window)
        rank_window.title("🏆 Ranking Final")
        rank_window.geometry("500x600")
        rank_window.configure(bg="#1a1a1a")
        rank_window.transient(self.window)
        
        tk.Label(
            rank_window,
            text="🏆 RANKING FINAL 🏆",
            bg="#1a1a1a",
            fg="#FFD700",
            font=("Arial", 20, "bold")
        ).pack(pady=20)
        
        for i, part in enumerate(ranking, 1):
            self.criar_card_ranking(rank_window, i, part)
        
        tk.Button(
            rank_window,
            text="Fechar",
            command=rank_window.destroy,
            bg="#666666",
            fg="white",
            font=("Arial", 11),
            cursor="hand2",
            padx=20,
            pady=8
        ).pack(pady=20)
    
    def criar_card_ranking(self, parent, posicao, participante):
        """Cria card do ranking"""
        # Cores por posição
        cores = {
            1: "#FFD700",  # Ouro
            2: "#C0C0C0",  # Prata
            3: "#CD7F32"   # Bronze
        }
        cor = cores.get(posicao, "#4CAF50")
        
        card = tk.Frame(parent, bg="#2d2d2d", relief=tk.RAISED, bd=2)
        card.pack(fill=tk.X, padx=20, pady=5)
        
        # Posição
        tk.Label(
            card,
            text=f"#{posicao}",
            bg="#2d2d2d",
            fg=cor,
            font=("Arial", 20, "bold"),
            width=3
        ).pack(side=tk.LEFT, padx=10)
        
        # Info
        info = tk.Frame(card, bg="#2d2d2d")
        info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(
            info,
            text=participante['nome'],
            bg="#2d2d2d",
            fg="white",
            font=("Arial", 16, "bold")
        ).pack(anchor=tk.W)
        
        tk.Label(
            info,
            text=f"{participante['pontuacao']:.0f} pontos",
            bg="#2d2d2d",
            fg=cor,
            font=("Arial", 14)
        ).pack(anchor=tk.W)
    
    def finalizar_evento(self):
        """Finaliza o evento atual"""
        resposta = messagebox.askyesnocancel(
            "Finalizar Evento",
            "Deseja finalizar este evento?\n\n"
            "Sim = Finalizar e salvar\n"
            "Não = Limpar e excluir tudo\n"
            "Cancelar = Voltar",
            parent=self.window
        )
        
        if resposta is None:  # Cancelar
            return
        elif resposta:  # Sim - Finalizar
            self.db.finalizar_evento(self.evento_atual['id'])
            messagebox.showinfo(
                "Evento Finalizado",
                "Evento finalizado e salvo com sucesso!",
                parent=self.window
            )
        else:  # Não - Limpar
            self.db.limpar_evento(self.evento_atual['id'])
            messagebox.showinfo(
                "Evento Removido",
                "Evento removido completamente do banco de dados.",
                parent=self.window
            )
        
        self.window.destroy()
    
    def limpar_janela(self):
        """Limpa todos os widgets da janela"""
        for widget in self.window.winfo_children():
            widget.destroy()