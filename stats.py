import psycopg2
from cadastro import conectar


def incrementar_estrelas(user_id: int, estrelas: int) -> bool:
    """Incrementa a quantidade de estrelas conquistadas para um usuário.
    Atualiza também a data_entrada para o dia atual.
    Retorna True se atualizar, False caso não encontre o usuário.
    """
    if estrelas <= 0:
        return True  # nada a fazer

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
            'SELECT estrelas FROM speech_teach.stats WHERE id_usuario = %s',
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False

        atuais = row[0] or 0
        novas = atuais + estrelas
        cursor.execute(
            'UPDATE speech_teach.stats SET estrelas = %s, data_entrada = CURRENT_DATE WHERE id_usuario = %s',
            (novas, user_id)
        )
        conexao.commit()
        committed = True
        return True
    except Exception as e:
        print(f"[STATS] Erro ao incrementar estrelas: {e}")
        return False
    finally:
        try:
            if conexao:
                if not committed and conexao.closed == 0:
                    conexao.rollback()
                if cursor:
                    cursor.close()
                conexao.close()
        except Exception as ex:
            print(f"[STATS] Erro ao fechar conexão: {ex}")


def obter_estrelas(user_id: int) -> int:
    """Busca o total de estrelas conquistadas de um usuário do banco.
    Retorna 0 se não encontrar o usuário.
    """
    conexao = None
    cursor = None
    try:
        conexao = conectar()
        if conexao is None:
            raise Exception('Não foi possível conectar ao banco')
        
        cursor = conexao.cursor()
        cursor.execute(
            'SELECT estrelas FROM speech_teach.stats WHERE id_usuario = %s',
            (user_id,)
        )
        row = cursor.fetchone()
        if not row:
            return 0
        return row[0] or 0
    except Exception as e:
        print(f"[STATS] Erro ao obter estrelas: {e}")
        return 0
    finally:
        try:
            if conexao:
                if cursor:
                    cursor.close()
                conexao.close()
        except Exception as ex:
            print(f"[STATS] Erro ao fechar conexão: {ex}")

