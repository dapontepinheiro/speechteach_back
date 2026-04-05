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


def obter_stats_completas(user_id: int) -> dict:
    """Busca todas as estatísticas do usuário do banco.
    Retorna um dicionário com sequencia, estrelas, precisao, frases praticadas, melhor_precisao
    """
    conexao = None
    cursor = None
    try:
        conexao = conectar()
        if conexao is None:
            raise Exception('Não foi possível conectar ao banco')
        
        cursor = conexao.cursor()
        
        # Busca dados da tabela stats
        cursor.execute(
            'SELECT sequencia, estrelas, precisao, melhor_precisao FROM speech_teach.stats WHERE id_usuario = %s',
            (user_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            return {
                "streak": 0,
                "stars": 0,
                "accuracy": 0.0,
                "phrases": 0,
                "bestAccuracy": 0.0
            }
        
        # Conta quantas frases foram praticadas (estrelas > 0)
        cursor.execute(
            'SELECT COUNT(DISTINCT id_frase) FROM speech_teach.frases WHERE id_usuario = %s AND estrelas > 0',
            (user_id,)
        )
        phrases_row = cursor.fetchone()
        frases_praticadas = phrases_row[0] if phrases_row else 0
        
        resultado = {
            "streak": row[0] or 0,
            "stars": row[1] or 0,
            "accuracy": float(row[2]) if row[2] is not None else 0.0,
            "phrases": frases_praticadas,
            "bestAccuracy": float(row[3]) if row[3] is not None else 0.0
        }
        return resultado
        
    except Exception as e:
        print(f"[STATS] Erro ao obter stats completas: {e}")
        return {
            "streak": 0,
            "stars": 0,
            "accuracy": 0.0,
            "phrases": 0,
            "bestAccuracy": 0.0
        }
    finally:
        try:
            if conexao:
                if cursor:
                    cursor.close()
                conexao.close()
        except Exception as ex:
            print(f"[STATS] Erro ao fechar conexão: {ex}")


def calcular_melhor_precisao(user_id: int) -> float:
    """Calcula a melhor precisão do usuário dentre todas as frases praticadas.
    Busca o valor máximo da coluna 'melhor_precisao' da tabela frases.
    Retorna 0.0 se não houver frases praticadas com precisão registrada.
    """
    conexao = None
    cursor = None
    try:
        conexao = conectar()
        if conexao is None:
            raise Exception('Não foi possível conectar ao banco')
        
        cursor = conexao.cursor()
        
        # Busca a melhor precisão dentre todas as frases do usuário
        cursor.execute(
            '''
            SELECT MAX(melhor_precisao) 
            FROM speech_teach.frases 
            WHERE id_usuario = %s AND melhor_precisao IS NOT NULL
            ''',
            (user_id,)
        )
        
        row = cursor.fetchone()
        
        if not row or row[0] is None:
            return 0.0
        
        # Retorna como percentual (0-100)
        return round(float(row[0]), 2)
        
    except Exception as e:
        print(f"[STATS] Erro ao calcular melhor precisão: {e}")
        return 0.0
    finally:
        try:
            if conexao:
                if cursor:
                    cursor.close()
                conexao.close()
        except Exception as ex:
            print(f"[STATS] Erro ao fechar conexão: {ex}")


def atualizar_melhor_precisao(user_id: int) -> bool:
    """Calcula a melhor precisão do usuário e atualiza na tabela stats.
    Retorna True se atualizar com sucesso, False caso contrário.
    """
    conexao = None
    cursor = None
    committed = False
    try:
        # Calcula a melhor precisão
        melhor = calcular_melhor_precisao(user_id)
        
        conexao = conectar()
        if conexao is None:
            raise Exception('Não foi possível conectar ao banco')
        
        conexao.autocommit = False
        cursor = conexao.cursor()
        
        # Atualiza a melhor precisão na tabela stats
        cursor.execute(
            'UPDATE speech_teach.stats SET melhor_precisao = %s WHERE id_usuario = %s',
            (melhor, user_id)
        )
        
        conexao.commit()
        committed = True
        return True
        
    except Exception as e:
        print(f"[STATS] Erro ao atualizar melhor precisão: {e}")
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


def calcular_media_precisao(user_id: int) -> float:
    """Calcula a média de precisão do usuário a partir das frases finalizadas.
    Busca os dados da coluna 'melhor_precisao' da tabela frases e calcula a média,
    excluindo as frases com valor NULL.
    Retorna 0.0 se não houver frases praticadas com precisão registrada.
    """
    conexao = None
    cursor = None
    try:
        conexao = conectar()
        if conexao is None:
            raise Exception('Não foi possível conectar ao banco')
        
        cursor = conexao.cursor()
        
        # Busca todas as precisões não-nulas das frases do usuário
        cursor.execute(
            '''
            SELECT melhor_precisao 
            FROM speech_teach.frases 
            WHERE id_usuario = %s AND melhor_precisao IS NOT NULL
            ''',
            (user_id,)
        )
        
        precisoes = cursor.fetchall()
        
        if not precisoes or len(precisoes) == 0:
            return 0.0
        
        # Calcula a média - valores já estão em 0-100
        soma = sum(row[0] for row in precisoes)
        media = soma / len(precisoes)
        
        # Retorna como percentual (0-100)
        media_arredondada = round(media, 2)
        return media_arredondada
        
    except Exception as e:
        print(f"[STATS] Erro ao calcular média de precisão: {e}")
        return 0.0
    finally:
        try:
            if conexao:
                if cursor:
                    cursor.close()
                conexao.close()
        except Exception as ex:
            print(f"[STATS] Erro ao fechar conexão: {ex}")


def atualizar_precisao_media(user_id: int) -> bool:
    """Calcula a média de precisão do usuário e atualiza na tabela stats.
    Retorna True se atualizar com sucesso, False caso contrário.
    """
    conexao = None
    cursor = None
    committed = False
    try:
        # Calcula a média de precisão
        media = calcular_media_precisao(user_id)
        
        conexao = conectar()
        if conexao is None:
            raise Exception('Não foi possível conectar ao banco')
        
        conexao.autocommit = False
        cursor = conexao.cursor()
        
        # Atualiza a precisão na tabela stats
        cursor.execute(
            'UPDATE speech_teach.stats SET precisao = %s WHERE id_usuario = %s',
            (media, user_id)
        )
        
        conexao.commit()
        committed = True
        return True
        
    except Exception as e:
        print(f"[STATS] Erro ao atualizar precisão média: {e}")
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

