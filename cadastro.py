import os
from datetime import datetime, timedelta
import psycopg2

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def conectar():
    try:
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise RuntimeError("Variável DATABASE_URL não definida no .env")
        conexao = psycopg2.connect(db_url)
        return conexao
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return None
    
def verificar_usuario(email: str):
    """Verifica se um usuário já existe no banco de dados"""
    try:
        conexao = conectar()
        if conexao is None:
            return False
        
        cursor = conexao.cursor()
        comando = 'SELECT COUNT(*) FROM speech_teach.usuarios WHERE email = %s'
        cursor.execute(comando, (email.strip(),))
        resultado = cursor.fetchone()
        
        existe = resultado[0] > 0
        
        cursor.close()
        conexao.close()
        
        return existe
        
    except Exception as e:
        print(f'[VERIFICAR] Erro ao verificar usuário: {e}')
        return False

def cadastrar_usuario(user: str, email: str, senha: str):
    conexao = None
    cursor = None
    committed = False
    
    try:
        print(f"[CADASTRO] Tentando cadastrar usuário: {user} (Email: {email})")
        
        if verificar_usuario(email):
            raise ValueError(f'Usuário "{email}" já está cadastrado')
            
        conexao = conectar()
        if conexao is None:
            raise Exception('Não foi possível conectar ao banco')

        conexao.autocommit = False
        cursor = conexao.cursor()
        
        # Cria o usuário e devolve o id gerado
        comando_usuario = 'INSERT INTO speech_teach.usuarios (nome, email, senha) VALUES (%s, %s, %s) RETURNING id'
        valores_usuario = (user.strip(), email.strip(), (senha or '').strip())
        print(f"[CADASTRO] Executando INSERT para: {user.strip()}")
        cursor.execute(comando_usuario, valores_usuario)
        user_id = cursor.fetchone()[0]

        # Insere estatísticas iniciais (zeradas) vinculadas ao usuário
        comando_stats = (
            'INSERT INTO speech_teach.stats '
            '(id_usuario, sequencia, estrelas, precisao, frases, melhor_precisao, data_entrada, data_ultimo_login) '
            'VALUES (%s, %s, %s, %s, %s, %s, CURRENT_DATE, CURRENT_DATE)'
        )
        valores_stats = (user_id, 0, 0, 0.0, 0, 0.0)
        cursor.execute(comando_stats, valores_stats)

        conexao.commit()
        committed = True

        print(f'[CADASTRO] ✓ Usuário {user.strip()} cadastrado com sucesso no PostgreSQL! ID: {user_id}')
        return user_id
        
    except ValueError:
        # Re-levanta ValueError (usuário duplicado)
        raise
    except Exception as e:
        print(f'[ERRO] {e}')
        raise Exception(f'Erro ao cadastrar usuário: {str(e)}')
    finally:
        try:
            if conexao:
                if not committed and conexao.closed == 0:
                    conexao.rollback()
                if cursor:
                    cursor.close()
                conexao.close()
                print("[CADASTRO] Conexão PostgreSQL fechada")
        except Exception as ex:
            print(f"[CADASTRO] Erro ao fechar conexão: {ex}")

def autenticar_usuario(email: str, senha: str):
    """
    Autentica um usuário pelo email e senha.
    Atualiza o streak de acordo com a última data de login.
    Retorna um dicionário com id e name se sucesso.
    Levanta ValueError se credenciais inválidas.
    """
    conexao = None
    cursor = None
    committed = False
    
    try:
        print(f"[LOGIN] Tentando autenticar usuário: {email}")
        
        conexao = conectar()
        if conexao is None:
            raise Exception('Não foi possível conectar ao banco')

        conexao.autocommit = False
        cursor = conexao.cursor()
        
        comando = 'SELECT id, nome, senha FROM speech_teach.usuarios WHERE email = %s'
        cursor.execute(comando, (email.strip(),))
        resultado = cursor.fetchone()

        if not resultado:
            raise ValueError('Email não encontrado')
        
        if resultado[2] != (senha or '').strip():
            raise ValueError('Senha incorreta')
        
        user_id = resultado[0]
        user_name = resultado[1]
        
        # Atualiza o streak
        _atualizar_streak(cursor, user_id)
        conexao.commit()
        committed = True
        
        print(f'[LOGIN] ✓ Usuário {user_name} autenticado com sucesso!')
        return {
            'id': user_id,
            'name': user_name
        }
        
    except ValueError:
        raise
    except Exception as e:
        print(f'[LOGIN ERRO] {e}')
        raise Exception(f'Erro ao autenticar: {str(e)}')
    finally:
        try:
            if conexao:
                if not committed and conexao.closed == 0:
                    conexao.rollback()
                if cursor:
                    cursor.close()
                conexao.close()
                print("[LOGIN] Conexão PostgreSQL fechada")
        except Exception as ex:
            print(f"[LOGIN] Erro ao fechar conexão: {ex}")

def _atualizar_streak(cursor, user_id: int):
    """
    Atualiza o streak do usuário:
    - Se logou no mesmo dia: sem mudanças
    - Se é o dia seguinte ao último login: incrementa streak
    - Se passou mais de um dia: reseta streak para 1
    """
    try:
        # Busca sequencia e data_ultimo_login
        cursor.execute(
            'SELECT sequencia, data_ultimo_login FROM speech_teach.stats WHERE id_usuario = %s',
            (user_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            # Usuário novo, cria stats com streak 1
            return
        
        sequencia_atual = row[0] or 0
        data_ultimo_login = row[1]

        if data_ultimo_login is None:
            # Normaliza contas antigas sem data de login registrada
            nova_sequencia = max(sequencia_atual, 1)
            cursor.execute(
                'UPDATE speech_teach.stats SET sequencia = %s, data_ultimo_login = CURRENT_DATE WHERE id_usuario = %s',
                (nova_sequencia, user_id)
            )
            print(f"[STREAK] Usuário {user_id}: inicializou streak {nova_sequencia} com data_ultimo_login de hoje")
            return
        
        # Data de hoje
        hoje = datetime.now().date()
        
        # Se já logou hoje, não faz nada
        if data_ultimo_login == hoje:
            print(f"[STREAK] Usuário {user_id}: já logou hoje, mantendo streak {sequencia_atual}")
            return
        
        # Calcula a diferença de dias
        dias_diferenca = (hoje - data_ultimo_login).days
        
        if dias_diferenca == 1:
            # Logou no dia seguinte ao último: incrementa streak
            nova_sequencia = sequencia_atual + 1
            print(f"[STREAK] Usuário {user_id}: incrementou streak para {nova_sequencia}")
        else:
            # Passou mais de um dia: reseta para 1
            nova_sequencia = 1
            print(f"[STREAK] Usuário {user_id}: resetou streak para 1 (pulou {dias_diferenca} dias)")
        
        # Atualiza sequencia e data_ultimo_login
        cursor.execute(
            'UPDATE speech_teach.stats SET sequencia = %s, data_ultimo_login = CURRENT_DATE WHERE id_usuario = %s',
            (nova_sequencia, user_id)
        )

        print(f'[STREAK] ✓ Usuário {user_id} atualizou streak no PostgreSQL! Streak atual: {nova_sequencia}, data_ultimo_login: {hoje}')


    except Exception as e:
        print(f"[STREAK] Erro ao atualizar streak: {e}")