import psycopg2
from cadastro import conectar
from typing import List, Dict, Optional

# Lista de todas as frases disponíveis no sistema
# Mantém sincronizado com frontend/src/data/quotes.ts
TODAS_FRASES = [
    {'texto': 'We stick together.', 'dificuldade': 'easy', 'serie': 'Stranger Things'},
    {'texto': 'The lights are flickering.', 'dificuldade': 'easy', 'serie': 'Stranger Things'},
    {'texto': 'Something is wrong in Hawkins.', 'dificuldade': 'medium', 'serie': 'Stranger Things'},
    {'texto': 'Stay away from the lab today.', 'dificuldade': 'medium', 'serie': 'Stranger Things'},
    {'texto': "If we face the unknown together, we won't break.", 'dificuldade': 'hard', 'serie': 'Stranger Things'},
    {'texto': 'Winter is coming.', 'dificuldade': 'easy', 'serie': 'Game of Thrones'},
    {'texto': 'A dragon is rising.', 'dificuldade': 'easy', 'serie': 'Game of Thrones'},
    {'texto': 'A Lannister always plays the game.', 'dificuldade': 'medium', 'serie': 'Game of Thrones'},
    {'texto': 'The North remembers its friends.', 'dificuldade': 'medium', 'serie': 'Game of Thrones'},
    {'texto': 'Power is a shadow; honor is the fire that guides me.', 'dificuldade': 'hard', 'serie': 'Game of Thrones'},
    {'texto': 'Get the suit on.', 'dificuldade': 'easy', 'serie': 'How I Met Your Mother'},
    {'texto': 'This is going to be epic.', 'dificuldade': 'easy', 'serie': 'How I Met Your Mother'},
    {'texto': 'We met at that little bar.', 'dificuldade': 'medium', 'serie': 'How I Met Your Mother'},
    {'texto': 'Sometimes timing changes everything.', 'dificuldade': 'medium', 'serie': 'How I Met Your Mother'},
    {'texto': "One day, you'll see why every detour led me here.", 'dificuldade': 'hard', 'serie': 'How I Met Your Mother'},
]


def inicializar_frases_usuario(user_id: int) -> bool:
    """
    Cria registros zerados de todas as frases para um novo usuário.
    Deve ser chamado ao cadastrar um novo usuário.
    """
    conexao = None
    cursor = None
    committed = False
    
    try:
        conexao = conectar()
        if conexao is None:
            raise Exception('Não foi possível conectar ao banco')
        
        conexao.autocommit = False
        cursor = conexao.cursor()
        
        # Insere todas as frases com estrelas = 0 e data_ultima_pratica = NULL
        for frase in TODAS_FRASES:
            cursor.execute(
                '''
                INSERT INTO speech_teach.frases 
                (id_usuario, texto_frase, dificuldade, serie, estrelas, data_ultima_pratica)
                VALUES (%s, %s, %s, %s, %s, NULL)
                ''',
                (user_id, frase['texto'], frase['dificuldade'], frase['serie'], 0)
            )
        
        conexao.commit()
        committed = True
        print(f"[FRASES] ✓ {len(TODAS_FRASES)} frases inicializadas para usuário {user_id}")
        return True
        
    except Exception as e:
        print(f"[FRASES] Erro ao inicializar frases: {e}")
        return False
        
    finally:
        try:
            if conexao:
                if not committed and conexao.closed == 0:
                    conexao.rollback()
                if cursor:
                    cursor.close()
                conexao.close()
        except Exception as e:
            print(f"[FRASES] Erro ao fechar conexão: {e}")


def salvar_frase(
    user_id: int,
    id_frase: int,
    texto_frase: str,
    dificuldade: str,
    serie: str,
    estrelas: int
) -> bool:
    """
    Salva ou atualiza uma frase praticada pelo usuário.
    Se a frase já existe, atualiza as estrelas e a data_ultima_pratica.
    """
    conexao = None
    cursor = None
    committed = False
    
    try:
        conexao = conectar()
        if conexao is None:
            raise Exception('Não foi possível conectar ao banco')
        
        conexao.autocommit = False
        cursor = conexao.cursor()
        
        # Verifica se já existe essa frase para esse usuário
        cursor.execute(
            '''
            SELECT id_frase FROM speech_teach.frases 
            WHERE id_usuario = %s AND id_frase = %s
            ''',
            (user_id, id_frase)
        )
        
        row = cursor.fetchone()
        
        if row:
            # Atualiza apenas as estrelas e a data
            cursor.execute(
                '''
                UPDATE speech_teach.frases 
                SET estrelas = %s, data_ultima_pratica = CURRENT_TIMESTAMP
                WHERE id_usuario = %s AND id_frase = %s
                ''',
                (estrelas, user_id, id_frase)
            )
        else:
            # Insere nova frase
            cursor.execute(
                '''
                INSERT INTO speech_teach.frases 
                (id_frase, id_usuario, texto_frase, dificuldade, serie, estrelas, data_ultima_pratica)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ''',
                (id_frase, user_id, texto_frase, dificuldade, serie, estrelas)
            )
        
        conexao.commit()
        committed = True
        return True
        
    except Exception as e:
        print(f"[FRASES] Erro ao salvar frase: {e}")
        return False
        
    finally:
        try:
            if conexao:
                if not committed and conexao.closed == 0:
                    conexao.rollback()
                if cursor:
                    cursor.close()
                conexao.close()
        except Exception as e:
            print(f"[FRASES] Erro ao fechar conexão: {e}")


def buscar_frases_usuario(user_id: int) -> List[Dict]:
    """
    Busca todas as frases praticadas por um usuário.
    Retorna uma lista de dicionários com id_frase e estrelas.
    """
    conexao = None
    cursor = None
    
    try:
        conexao = conectar()
        if conexao is None:
            raise Exception('Não foi possível conectar ao banco')
        
        cursor = conexao.cursor()
        cursor.execute(
            '''
            SELECT id_frase, estrelas 
            FROM speech_teach.frases 
            WHERE id_usuario = %s
            ''',
            (user_id,)
        )
        
        rows = cursor.fetchall()
        
        # Converte para dicionário {id_frase: estrelas}
        frases = [
            {"id_frase": row[0], "estrelas": row[1]}
            for row in rows
        ]
        
        return frases
        
    except Exception as e:
        print(f"[FRASES] Erro ao buscar frases: {e}")
        return []
        
    finally:
        try:
            if conexao:
                if cursor:
                    cursor.close()
                conexao.close()
        except Exception as e:
            print(f"[FRASES] Erro ao fechar conexão: {e}")


def atualizar_estrelas_frase(user_id: int, id_frase: int, estrelas: int) -> bool:
    """
    Atualiza apenas as estrelas de uma frase já praticada.
    """
    conexao = None
    cursor = None
    committed = False
    
    try:
        conexao = conectar()
        if conexao is None:
            raise Exception('Não foi possível conectar ao banco')
        
        conexao.autocommit = False
        cursor = conexao.cursor()
        
        cursor.execute(
            '''
            UPDATE speech_teach.frases 
            SET estrelas = %s, data_ultima_pratica = CURRENT_TIMESTAMP
            WHERE id_usuario = %s AND id_frase = %s
            ''',
            (estrelas, user_id, id_frase)
        )
        
        if cursor.rowcount == 0:
            return False  # Frase não encontrada
        
        conexao.commit()
        committed = True
        return True
        
    except Exception as e:
        print(f"[FRASES] Erro ao atualizar estrelas: {e}")
        return False
        
    finally:
        try:
            if conexao:
                if not committed and conexao.closed == 0:
                    conexao.rollback()
                if cursor:
                    cursor.close()
                conexao.close()
        except Exception as e:
            print(f"[FRASES] Erro ao fechar conexão: {e}")
