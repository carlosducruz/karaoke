import sqlite3
import json
from datetime import datetime
import csv  

class KaraokeDatabase:
 

    def __init__(self, db_path="karaoke_eventos.db"):
        self.db_path = db_path
        self.init_database()

    def limpar_catalogo(self):
            """Remove todos os registros do catálogo de músicas."""
            self.criar_tabela_catalogo()
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM catalogo")
            conn.commit()
            conn.close()
        
    def criar_tabela_catalogo(self):
        """Cria a tabela do catálogo se não existir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS catalogo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cantor TEXT,
                cod TEXT,
                musica TEXT,
                inicio TEXT
            )
        """)
        conn.commit()
        conn.close()

      
    def adicionar_musica_playlist(self, evento_id, participante_id, arquivo_path, 
                                tom_ajuste=0, duracao_segundos=0, codigo_musica=None, musica_nome=None):
        """Adiciona uma música à playlist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Obter próxima ordem
        cursor.execute("""
            SELECT MAX(ordem) FROM playlist WHERE evento_id = ?
        """, (evento_id,))
        max_ordem = cursor.fetchone()[0]
        ordem = (max_ordem or 0) + 1
        
        cursor.execute("""
            INSERT INTO playlist (evento_id, participante_id, arquivo_path, 
                                tom_ajuste, ordem, duracao_segundos, musica_nome)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (evento_id, participante_id, arquivo_path, tom_ajuste, ordem, duracao_segundos, musica_nome))
        
        musica_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return musica_id
    
        
    def importar_catalogo_csv(self, csv_path):
        """Importa o catálogo do CSV para o banco de dados. Retorna número de músicas importadas."""
        import os
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {csv_path}")
        
        self.criar_tabela_catalogo()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        linhas = []
        linhas_importadas = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as csv_file:
                # Verifica se o arquivo tem BOM (Byte Order Mark)
                content = csv_file.read()
                has_bom = content.startswith('\ufeff')
                if has_bom:
                    content = content[1:]
                
                # Processa o conteúdo
                import io
                csv_reader = csv.reader(io.StringIO(content), delimiter=',')
                
                # Pula o cabeçalho
                next(csv_reader, None)
                
                for row_num, row in enumerate(csv_reader, 2):  # Começa da linha 2 (após cabeçalho)
                    if len(row) >= 4:
                        cantor = row[0].strip()
                        cod = str(row[1]).strip()
                        musica = row[2].strip()
                        inicio = row[3].strip()
                        
                        # Remove .0 do código se existir
                        if cod.endswith('.0'):
                            cod = cod[:-2]
                        
                        linhas.append((cantor, cod, musica, inicio))
                        linhas_importadas += 1
                    else:
                        print(f"[AVISO] Linha {row_num} ignorada - formato inválido: {row}")
        
        except UnicodeDecodeError:
            # Tenta com encoding diferente
            with open(csv_path, 'r', encoding='latin-1') as csv_file:
                csv_reader = csv.reader(csv_file, delimiter=',')
                next(csv_reader, None)  # Pula cabeçalho
                
                for row_num, row in enumerate(csv_reader, 2):
                    if len(row) >= 4:
                        cantor = row[0].strip()
                        cod = str(row[1]).strip()
                        musica = row[2].strip()
                        inicio = row[3].strip()
                        
                        if cod.endswith('.0'):
                            cod = cod[:-2]
                        
                        linhas.append((cantor, cod, musica, inicio))
                        linhas_importadas += 1
        
        # Logging: print detalhado para cada linha importada
        for idx, (cantor, cod, musica, inicio) in enumerate(linhas, 1):
            cursor.execute("INSERT INTO catalogo (cantor, cod, musica, inicio) VALUES (?, ?, ?, ?)", 
                        (cantor, cod, musica, inicio))
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{now}] Incluindo catálogo {idx}: cantor='{cantor}', cod='{cod}', musica='{musica}', inicio='{inicio}'")
        
        conn.commit()
        conn.close()
        return linhas_importadas

    # Mantenha o método buscar_catalogo existente para compatibilidade
    def buscar_catalogo(self, termo=None, limite=None):
        """Busca músicas/cantores/códigos no catálogo. Retorna lista de tuplas."""
        self.criar_tabela_catalogo()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if termo:
            cursor.execute("""
                SELECT cantor, cod, musica, inicio FROM catalogo
                WHERE cantor LIKE ? OR cod LIKE ? OR musica LIKE ?
                ORDER BY cantor, musica
            """, (f"%{termo}%", f"%{termo}%", f"%{termo}%"))
        else:
            if limite:
                cursor.execute("SELECT cantor, cod, musica, inicio FROM catalogo ORDER BY cantor, musica LIMIT ?", (limite,))
            else:
                cursor.execute("SELECT cantor, cod, musica, inicio FROM catalogo ORDER BY cantor, musica")
        rows = cursor.fetchall()
        conn.close()
        return rows

    # Adicione este método após o método buscar_catalogo

    def buscar_musica_por_codigo(self, codigo):
        """Busca uma música específica pelo código"""
        self.criar_tabela_catalogo()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT cantor, cod, musica, inicio FROM catalogo
            WHERE cod = ?
        """, (codigo,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'cantor': row[0],
                'cod': row[1],
                'musica': row[2],
                'inicio': row[3]
            }
        return None

    def remover_participante(self, participante_id):
        """Remove um participante e todas as suas músicas da playlist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Remove músicas da playlist desse participante
        cursor.execute("DELETE FROM playlist WHERE participante_id = ?", (participante_id,))
        # Remove o participante
        cursor.execute("DELETE FROM participantes WHERE id = ?", (participante_id,))
        conn.commit()
        conn.close()

    def remover_musica_playlist(self, musica_id):
        """Remove uma música da playlist pelo ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM playlist WHERE id = ?", (musica_id,))
        conn.commit()
        conn.close()
    
    def init_database(self):
        """Inicializa o banco de dados com as tabelas necessárias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabela de eventos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                data_criacao TEXT NOT NULL,
                data_finalizacao TEXT,
                status TEXT DEFAULT 'ativo',
                finalizado INTEGER DEFAULT 0
            )
        """)
        
        # Tabela de participantes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS participantes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evento_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                avatar_path TEXT,
                pontuacao REAL DEFAULT 0,
                ordem INTEGER,
                FOREIGN KEY (evento_id) REFERENCES eventos(id)
            )
        """)
        
        # Tabela de músicas da playlist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evento_id INTEGER NOT NULL,
                participante_id INTEGER NOT NULL,
                arquivo_path TEXT NOT NULL,
                tom_ajuste INTEGER DEFAULT 0,
                ordem INTEGER NOT NULL,
                ja_tocou INTEGER DEFAULT 0,
                duracao_segundos REAL,
                tempo_cantado REAL DEFAULT 0,
                musica_nome TEXT,
                pontuacao_vu REAL DEFAULT 0,
                FOREIGN KEY (evento_id) REFERENCES eventos(id),
                FOREIGN KEY (participante_id) REFERENCES participantes(id)
            )
        """)
        
        # Tabela do catálogo
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS catalogo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cantor TEXT,
                cod TEXT,
                musica TEXT,
                inicio TEXT
            )
        """)
        
        conn.commit()
        conn.close()
        
        # Executa migrations para adicionar colunas que possam estar faltando em bancos antigos
        self._executar_migrations()
    
    def _executar_migrations(self):
        """Executa migrations para adicionar colunas que possam estar faltando em bancos existentes"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Migration 1: Adicionar coluna musica_nome na playlist se não existir
            cursor.execute("PRAGMA table_info(playlist)")
            columns = [column[1] for column in cursor.fetchall()]
            
            if 'musica_nome' not in columns:
                cursor.execute("ALTER TABLE playlist ADD COLUMN musica_nome TEXT")
            
            if 'pontuacao_vu' not in columns:
                cursor.execute("ALTER TABLE playlist ADD COLUMN pontuacao_vu REAL DEFAULT 0")
                conn.commit()
                print("✅ Migration: Coluna 'musica_nome' adicionada à tabela playlist")
            
            # Adicione aqui futuras migrations conforme necessário
            # Migration 2: ...
            # Migration 3: ...
            
        except Exception as e:
            print(f"⚠️ Erro ao executar migrations: {e}")
        finally:
            conn.close()
    
    def listar_todos_eventos(self):
        """Lista todos os eventos do banco de dados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT e.id, e.nome, e.data_criacao, e.data_finalizacao, 
                   e.status, e.finalizado,
                   COUNT(DISTINCT p.id) as total_participantes,
                   COUNT(pl.id) as total_musicas
            FROM eventos e
            LEFT JOIN participantes p ON e.id = p.evento_id
            LEFT JOIN playlist pl ON e.id = pl.evento_id
            GROUP BY e.id
            ORDER BY e.data_criacao DESC
        """)
        
        eventos = []
        for row in cursor.fetchall():
            eventos.append({
                'id': row[0],
                'nome': row[1],
                'data_criacao': row[2],
                'data_finalizacao': row[3],
                'status': row[4],
                'finalizado': row[5] == 1,
                'total_participantes': row[6],
                'total_musicas': row[7]
            })
        
        conn.close()
        return eventos
    
    def excluir_evento(self, evento_id):
        """Exclui completamente um evento e todos os seus dados relacionados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Exclui na ordem correta para respeitar foreign keys
        cursor.execute("DELETE FROM playlist WHERE evento_id = ?", (evento_id,))
        cursor.execute("DELETE FROM participantes WHERE evento_id = ?", (evento_id,))
        cursor.execute("DELETE FROM eventos WHERE id = ?", (evento_id,))
        
        conn.commit()
        conn.close()
    
    def criar_evento(self, nome):
        """Cria um novo evento"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO eventos (nome, data_criacao, status)
            VALUES (?, ?, 'ativo')
        """, (nome, datetime.now().isoformat()))
        
        evento_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return evento_id
    
    def obter_evento_ativo(self):
        """Retorna o evento ativo atual"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, nome, data_criacao, status
            FROM eventos
            WHERE status = 'ativo' AND finalizado = 0
            ORDER BY id DESC
            LIMIT 1
        """)
        
        evento = cursor.fetchone()
        conn.close()
        
        if evento:
            return {
                'id': evento[0],
                'nome': evento[1],
                'data_criacao': evento[2],
                'status': evento[3]
            }
        return None
    
    def finalizar_evento(self, evento_id):
        """Finaliza um evento"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE eventos
            SET finalizado = 1, data_finalizacao = ?, status = 'finalizado'
            WHERE id = ?
        """, (datetime.now().isoformat(), evento_id))
        
        conn.commit()
        conn.close()
    
    def adicionar_participante(self, evento_id, nome, avatar_path=None, ordem=None):
        """Adiciona um participante ao evento"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if ordem is None:
            cursor.execute("""
                SELECT MAX(ordem) FROM participantes WHERE evento_id = ?
            """, (evento_id,))
            max_ordem = cursor.fetchone()[0]
            ordem = (max_ordem or 0) + 1
        
        cursor.execute("""
            INSERT INTO participantes (evento_id, nome, avatar_path, ordem)
            VALUES (?, ?, ?, ?)
        """, (evento_id, nome, avatar_path, ordem))
        
        participante_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return participante_id
    
    def obter_participantes(self, evento_id):
        """Lista todos os participantes de um evento"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, nome, avatar_path, pontuacao, ordem
            FROM participantes
            WHERE evento_id = ?
            ORDER BY ordem
        """, (evento_id,))
        
        participantes = []
        for row in cursor.fetchall():
            participantes.append({
                'id': row[0],
                'nome': row[1],
                'avatar_path': row[2],
                'pontuacao': row[3],
                'ordem': row[4]
            })
        
        conn.close()
        return participantes
     
    
    def obter_playlist(self, evento_id):
        """Obtém a playlist completa do evento"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.id, p.arquivo_path, p.tom_ajuste, p.ordem, p.ja_tocou,
                   p.duracao_segundos, p.tempo_cantado,
                   part.nome, part.avatar_path, part.id, p.evento_id, p.musica_nome,
                   p.pontuacao_vu
            FROM playlist p
            JOIN participantes part ON p.participante_id = part.id
            WHERE p.evento_id = ?
            ORDER BY p.ordem
        """, (evento_id,))
        
        playlist = []
        for row in cursor.fetchall():
            playlist.append({
                'id': row[0],
                'arquivo_path': row[1],
                'tom_ajuste': row[2],
                'ordem': row[3],
                'ja_tocou': row[4] == 1,
                'duracao_segundos': row[5],
                'tempo_cantado': row[6],
                'participante_nome': row[7],
                'participante_avatar': row[8],
                'participante_id': row[9],
                'evento_id': row[10],
                'musica_nome': row[11],
                'pontuacao_vu': row[12] if row[12] is not None else 0
            })
        
        conn.close()
        return playlist
    
    def obter_proxima_musica(self, evento_id):
        """Obtém a próxima música não tocada da playlist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT p.id, p.arquivo_path, p.tom_ajuste, p.ordem,
                   p.duracao_segundos, part.nome, part.avatar_path, part.id
            FROM playlist p
            JOIN participantes part ON p.participante_id = part.id
            WHERE p.evento_id = ? AND p.ja_tocou = 0
            ORDER BY p.ordem
            LIMIT 1
        """, (evento_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'arquivo_path': row[1],
                'tom_ajuste': row[2],
                'ordem': row[3],
                'duracao_segundos': row[4],
                'participante_nome': row[5],
                'participante_avatar': row[6],
                'participante_id': row[7]
            }
        return None
    
    def marcar_musica_tocada(self, musica_id, tempo_cantado, pontuacao_vu=None):
        """Marca uma música como tocada, registra o tempo cantado e a pontuação do V.U. meter"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if pontuacao_vu is not None:
            cursor.execute("""
                UPDATE playlist
                SET ja_tocou = 1, tempo_cantado = ?, pontuacao_vu = ?
                WHERE id = ?
            """, (tempo_cantado, pontuacao_vu, musica_id))
            
            # Atualizar pontuação do participante
            cursor.execute("""
                SELECT participante_id FROM playlist WHERE id = ?
            """, (musica_id,))
            participante_id = cursor.fetchone()[0]
            
            cursor.execute("""
                UPDATE participantes
                SET pontuacao = pontuacao + ?
                WHERE id = ?
            """, (pontuacao_vu, participante_id))
        else:
            cursor.execute("""
                UPDATE playlist
                SET ja_tocou = 1, tempo_cantado = ?
                WHERE id = ?
            """, (tempo_cantado, musica_id))
        
        conn.commit()
        conn.close()
    

    
    def obter_ranking(self, evento_id):
        """Obtém o ranking final dos participantes com avatar"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT nome, avatar_path, pontuacao
            FROM participantes
            WHERE evento_id = ?
            ORDER BY pontuacao DESC
        """, (evento_id,))
        
        ranking = []
        for i, row in enumerate(cursor.fetchall(), 1):
            ranking.append({
                'posicao': i,  # Adicionamos a posição aqui
                'nome': row[0],
                'avatar_path': row[1],  # Já está incluído!
                'pontuacao': row[2]
            })
        
        conn.close()
        return ranking
    
    def limpar_evento(self, evento_id):
        """Remove completamente um evento e seus dados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM playlist WHERE evento_id = ?", (evento_id,))
        cursor.execute("DELETE FROM participantes WHERE evento_id = ?", (evento_id,))
        cursor.execute("DELETE FROM eventos WHERE id = ?", (evento_id,))
        
        conn.commit()
        conn.close()
