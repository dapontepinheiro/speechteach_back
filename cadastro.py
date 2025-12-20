import os
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
            'INSERT INTO speech_teach.stats (id_usuario, sequencia, estrelas, precisao, frases, melhor_precisao, data_entrada) '
            'VALUES (%s, %s, %s, %s, %s, %s, CURRENT_DATE)'
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
    Retorna um dicionário com id e name se sucesso.
    Levanta ValueError se credenciais inválidas.
    """
    conexao = None
    cursor = None
    
    try:
        print(f"[LOGIN] Tentando autenticar usuário: {email}")
        
        conexao = conectar()
        if conexao is None:
            raise Exception('Não foi possível conectar ao banco')

        cursor = conexao.cursor()
        
        comando = 'SELECT id, nome, senha FROM speech_teach.usuarios WHERE email = %s'
        cursor.execute(comando, (email.strip(),))
        resultado = cursor.fetchone()

        if not resultado:
            raise ValueError('Email não encontrado')
        
        if resultado[2] != (senha or '').strip():
            raise ValueError('Senha incorreta')
        
        print(f'[LOGIN] ✓ Usuário {resultado[1]} autenticado com sucesso!')
        return {
            'id': resultado[0],
            'name': resultado[1]
        }
        
    except ValueError:
        raise
    except Exception as e:
        print(f'[LOGIN ERRO] {e}')
        raise Exception(f'Erro ao autenticar: {str(e)}')
    finally:
        try:
            if cursor:
                cursor.close()
            if conexao:
                conexao.close()
                print("[LOGIN] Conexão PostgreSQL fechada")
        except Exception as ex:
            print(f"[LOGIN] Erro ao fechar conexão: {ex}")