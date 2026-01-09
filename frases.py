import psycopg2
from cadastro import conectar
from typing import List, Dict, Optional

# Catálogo sincronizado com frontend/src/data/quotes.ts
TODAS_FRASES = [
    {"id": 1, "show": "Stranger Things", "character": "Mike Wheeler", "line": "Friends don't lie.", "translation": "Amigos não mentem.", "difficulty": "easy", "tip": "Não pronuncie o T final de \"don't\"; \"lie\" é um ditongo aberto."},
    {"id": 2, "show": "Stranger Things", "character": "Lucas Sinclair", "line": "We're not kids anymore.", "translation": "Nós não somos mais crianças.", "difficulty": "easy", "tip": "Reduza \"we're\"; \"anymore\" soa \"éni-mór\"."},
    {"id": 3, "show": "Stranger Things", "character": "Dustin Henderson", "line": "She's our friend and she's crazy!", "translation": "Ela é nossa amiga e é maluca!", "difficulty": "easy", "tip": "Ligue \"and she's\" → \"anchis\"; entonação animada."},
    {"id": 4, "show": "Stranger Things", "character": "Hopper", "line": "You don't mess around with Jim.", "translation": "Você não mexe com o Jim.", "difficulty": "easy", "tip": "Reduza \"don't\" e ligue \"around with\" → \"arounwif\"."},
    {"id": 5, "show": "Stranger Things", "character": "Will Byers", "line": "I felt it everywhere.", "translation": "Eu senti isso em todo lugar.", "difficulty": "easy", "tip": "Ligue \"felt it\" → \"fél-tit\"; \"everywhere\" sem pronunciar o H."},
    {"id": 6, "show": "Stranger Things", "character": "Steve Harrington", "line": "I may be a pretty shitty boyfriend.", "translation": "Eu posso ser um namorado bem ruim.", "difficulty": "medium", "tip": "Entonação descontraída; \"pretty\" soa como \"príri\"."},
    {"id": 7, "show": "Stranger Things", "character": "Robin Buckley", "line": "I work best under pressure.", "translation": "Eu trabalho melhor sob pressão.", "difficulty": "medium", "tip": "Ligue \"best under\" → \"béstander\"; \"pressure\" soa \"préshur\"."},
    {"id": 8, "show": "Stranger Things", "character": "Mike Wheeler", "line": "No matter what happens, I'm here.", "translation": "Não importa o que aconteça, eu estou aqui.", "difficulty": "medium", "tip": "Entonação cai no final; ligue \"matter what\" → \"máter-wat\"."},
    {"id": 9, "show": "Stranger Things", "character": "Steve Harrington", "line": "You don't mess with the babysitter.", "translation": "Você não mexe com a babá.", "difficulty": "medium", "tip": "Reduza \"don't\"; \"babysitter\" com T rápido, som de D."},
    {"id": 10, "show": "Stranger Things", "character": "Robin Buckley", "line": "I talk faster when I'm nervous.", "translation": "Eu falo mais rápido quando fico nervosa.", "difficulty": "medium", "tip": "Reduza \"I'm\"; entonação sobe em \"faster\"."},
    {"id": 11, "show": "Stranger Things", "character": "Hopper", "line": "You did exactly what you were supposed to do.", "translation": "Você fez exatamente o que deveria ter feito.", "difficulty": "hard", "tip": "Reduza \"supposed to\" → \"supposta\"; ritmo contínuo."},
    {"id": 12, "show": "Stranger Things", "character": "Mike Wheeler", "line": "You're the most important thing to me.", "translation": "Você é a coisa mais importante pra mim.", "difficulty": "hard", "tip": "Reduza \"to me\" → \"tuh-me\"; entonação emocional."},
    {"id": 13, "show": "Stranger Things", "character": "Hopper", "line": "Make mistakes, learn from them.", "translation": "Cometa erros, aprenda com eles.", "difficulty": "hard", "tip": "Faça pausa após a vírgula; \"them\" com TH sonoro."},
    {"id": 14, "show": "Stranger Things", "character": "Nancy Wheeler", "line": "I don't want to be afraid anymore.", "translation": "Eu não quero mais sentir medo.", "difficulty": "hard", "tip": "Reduza \"want to\" → \"wanna\"; ligue \"afraid anymore\"."},
    {"id": 15, "show": "Stranger Things", "character": "Dustin Henderson", "line": "Nobody normal ever accomplished anything meaningful.", "translation": "Ninguém normal jamais realizou algo significativo.", "difficulty": "hard", "tip": "Dê ênfase em \"meaningful\"; ritmo bem cadenciado."},
    {"id": 16, "show": "Game of Thrones", "character": "Ned Stark", "line": "Winter is coming.", "translation": "O inverno está chegando.", "difficulty": "easy", "tip": "Pronuncie \"winter\" com T suave (som de D rápido); \"coming\" termina com som nasal."},
    {"id": 17, "show": "Game of Thrones", "character": "Catelyn Stark", "line": "All men must die.", "translation": "Todos os homens devem morrer.", "difficulty": "easy", "tip": "\"Must\" com som curto; \"die\" bem aberto."},
    {"id": 18, "show": "Game of Thrones", "character": "Jon Snow", "line": "The North remembers.", "translation": "O Norte se lembra.", "difficulty": "easy", "tip": "TH sonoro em \"the\"; \"remembers\" termina com som de Z."},
    {"id": 19, "show": "Game of Thrones", "character": "Tyrion Lannister", "line": "I drink and I know things.", "translation": "Eu bebo e sei das coisas.", "difficulty": "easy", "tip": "Dê pausa curta após \"drink\"; \"things\" com TH surdo."},
    {"id": 20, "show": "Game of Thrones", "character": "Jon Snow", "line": "The things I do for love.", "translation": "As coisas que eu faço por amor.", "difficulty": "easy", "tip": "TH sonoro em \"the\"; ligue \"do for\" → \"dúfor\"."},
    {"id": 21, "show": "Game of Thrones", "character": "Jon Snow", "line": "Love is the death of duty.", "translation": "O amor é a morte do dever.", "difficulty": "medium", "tip": "TH sonoro em \"the\"; \"duty\" soa como \"diúti\"."},
    {"id": 22, "show": "Game of Thrones", "character": "Jaime Lannister", "line": "There are no men like me.", "translation": "Não existem homens como eu.", "difficulty": "medium", "tip": "TH sonoro em \"there\"; \"like me\" soa quase como \"laik-mi\"."},
    {"id": 23, "show": "Game of Thrones", "character": "Bran Stark", "line": "Chaos is a ladder.", "translation": "O caos é uma escada.", "difficulty": "medium", "tip": "\"Chaos\" começa com som forte de K; \"ladder\" soa como \"lérder\"."},
    {"id": 24, "show": "Game of Thrones", "character": "Daenerys Targaryen", "line": "I will take what is mine.", "translation": "Eu vou tomar o que é meu.", "difficulty": "medium", "tip": "Reduza \"will\" para \"I'll\"; ligue \"what is\" → \"whatis\"."},
    {"id": 25, "show": "Game of Thrones", "character": "Jorah Mormont", "line": "There is no cure for being a coward.", "translation": "Não há cura para ser um covarde.", "difficulty": "medium", "tip": "TH sonoro em \"there\"; \"coward\" soa como \"cáuerd\"."},
    {"id": 26, "show": "Game of Thrones", "character": "Varys", "line": "Power resides where men believe it resides.", "translation": "O poder reside onde os homens acreditam que reside.", "difficulty": "hard", "tip": "Repita \"resides\" com mesma entonação."},
    {"id": 27, "show": "Game of Thrones", "character": "Cersei Lannister", "line": "When you play the game of thrones, you win or you die.", "translation": "Quando você joga o jogo dos tronos, você vence ou morre.", "difficulty": "hard", "tip": "Reduza \"you\" para \"ya\"; ligue \"win or\" → \"winner\"; \"thrones\" tem TH surdo."},
    {"id": 28, "show": "Game of Thrones", "character": "Hound", "line": "If you think this has a happy ending, you haven't been paying attention.", "translation": "Se você acha que isso tem um final feliz, não estava prestando atenção.", "difficulty": "hard", "tip": "Reduza \"you haven't\"; ritmo rápido."},
    {"id": 29, "show": "Game of Thrones", "character": "Arya Stark", "line": "Power is a shadow; honor is the fire that guides me.", "translation": "Poder é uma sombra; honra é o fogo que me guia.", "difficulty": "hard", "tip": "Pratique pausas naturais no ponto e vírgula."},
    {"id": 30, "show": "Game of Thrones", "character": "Tywin Lannister", "line": "Any man who must say, \"I am the king\", is no true king.", "translation": "Qualquer homem que precisa dizer \"eu sou o rei\" não é um verdadeiro rei.", "difficulty": "hard", "tip": "Entonação firme; ligue \"must say\" → \"mus-sei\"."},
    {"id": 31, "show": "How I Met Your Mother", "character": "Robin Scherbatsky", "line": "This is going to be epic.", "translation": "Isso vai ser épico.", "difficulty": "easy", "tip": "Reduza \"going to\" para \"gonna\"."},
    {"id": 32, "show": "How I Met Your Mother", "character": "Marshall Eriksen", "line": "We met at that little bar.", "translation": "A gente se conheceu naquele barzinho.", "difficulty": "easy", "tip": "Pratique o som de \"at that\" com TH suave."},
    {"id": 33, "show": "How I Met Your Mother", "character": "Barney Stinson", "line": "This is going to be legendary.", "translation": "Isso vai ser lendário.", "difficulty": "easy", "tip": "Reduza \"going to\" → \"gonna\"; ênfase em \"legendary\"."},
    {"id": 34, "show": "How I Met Your Mother", "character": "Ted Mosby", "line": "I'm serious about this.", "translation": "Estou falando sério sobre isso.", "difficulty": "easy", "tip": "Ênfase em \"serious\"; TH sonoro em \"this\"."},
    {"id": 35, "show": "How I Met Your Mother", "character": "Robin Scherbatsky", "line": "I didn't see that coming.", "translation": "Eu não vi isso chegando.", "difficulty": "easy", "tip": "Reduza \"did not\" → \"didn't\"; ritmo natural."},
    {"id": 36, "show": "How I Met Your Mother", "character": "Ted Mosby", "line": "Kids, I'm going to tell you an incredible story.", "translation": "Crianças, eu vou contar a vocês uma história incrível.", "difficulty": "medium", "tip": "Reduza \"going to\" → \"gonna\"; ligue \"tell you\"."},
    {"id": 37, "show": "How I Met Your Mother", "character": "Robin Scherbatsky", "line": "Sometimes timing changes everything.", "translation": "Às vezes, o timing muda tudo.", "difficulty": "medium", "tip": "Alongue o AI em \"timing\"; ritmo natural."},
    {"id": 38, "show": "How I Met Your Mother", "character": "Robin Scherbatsky", "line": "I'm not great at emotional stuff.", "translation": "Eu não sou boa com coisas emocionais.", "difficulty": "medium", "tip": "\"Emotional\" com ritmo em três sílabas."},
    {"id": 39, "show": "How I Met Your Mother", "character": "Barney Stinson", "line": "You can't design your life like a building.", "translation": "Você não pode projetar sua vida como um prédio.", "difficulty": "medium", "tip": "Não pronuncie o T de \"can't\"; ritmo contínuo."},
    {"id": 40, "show": "How I Met Your Mother", "character": "Robin Scherbatsky", "line": "This is way more complicated than I expected.", "translation": "Isso é bem mais complicado do que eu esperava.", "difficulty": "medium", "tip": "Ênfase em \"complicated\"; ritmo crescente."},
    {"id": 41, "show": "How I Met Your Mother", "character": "Marshall Eriksen", "line": "I guess that's just part of growing up.", "translation": "Acho que isso é apenas parte de crescer.", "difficulty": "hard", "tip": "Reduza \"that is\" → \"that's\"; ligue \"part of\"."},
    {"id": 42, "show": "How I Met Your Mother", "character": "Lily Aldrin", "line": "Love doesn't always make sense, but that's what makes it real.", "translation": "O amor nem sempre faz sentido, mas é isso que o torna real.", "difficulty": "hard", "tip": "Pause após a vírgula; ligue \"makes it\"."},
    {"id": 43, "show": "How I Met Your Mother", "character": "Ted Mosby", "line": "One day, you'll see why every detour led me here.", "translation": "Um dia, você vai entender por que cada desvio me trouxe até aqui.", "difficulty": "hard", "tip": "Use a contração em \"you'll\"; conecte \"led me\"."},
    {"id": 44, "show": "How I Met Your Mother", "character": "Ted Mosby", "line": "The great moments of your life won't necessarily be the things you plan.", "translation": "Os grandes momentos da sua vida não serão necessariamente os que você planeja.", "difficulty": "hard", "tip": "Frase longa: divida em blocos; ritmo estável."},
    {"id": 45, "show": "How I Met Your Mother", "character": "Ted Mosby", "line": "In the end, we all just want to be happy.", "translation": "No fim, todos nós só queremos ser felizes.", "difficulty": "hard", "tip": "Reduza \"want to\" → \"wanna\"; entonação descendente."},
]


def inicializar_frases_usuario(user_id: int) -> bool:
    conexao = None
    cursor = None
    committed = False
    
    try:
        conexao = conectar()
        if conexao is None:
            raise Exception('Não foi possível conectar ao banco')
        
        conexao.autocommit = False
        cursor = conexao.cursor()
        
        for frase in TODAS_FRASES:
            texto = frase.get('line') or frase.get('texto')
            dificuldade = frase.get('difficulty') or frase.get('dificuldade')
            serie = frase.get('show') or frase.get('serie')

            cursor.execute(
                '''
                INSERT INTO speech_teach.frases 
                (id_frase, id_usuario, texto_frase, dificuldade, serie, estrelas, data_ultima_pratica)
                VALUES (%s, %s, %s, %s, %s, %s, NULL)
                ''',
                (frase['id'], user_id, texto, dificuldade, serie, 0)
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


def catalogo_frases() -> List[Dict]:
    return [
        {
            "id": frase["id"],
            "show": frase.get("show") or frase.get("serie"),
            "character": frase.get("character", ""),
            "line": frase.get("line") or frase.get("texto"),
            "translation": frase.get("translation", ""),
            "difficulty": frase.get("difficulty") or frase.get("dificuldade"),
            "tip": frase.get("tip", ""),
        }
        for frase in TODAS_FRASES
    ]


def salvar_frase(
    user_id: int,
    id_frase: int,
    texto_frase: str,
    dificuldade: str,
    serie: str,
    estrelas: int
) -> bool:
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
            SELECT id_frase FROM speech_teach.frases 
            WHERE id_usuario = %s AND id_frase = %s
            ''',
            (user_id, id_frase)
        )
        
        row = cursor.fetchone()
        
        if row:
            cursor.execute(
                '''
                UPDATE speech_teach.frases 
                SET estrelas = %s, data_ultima_pratica = CURRENT_TIMESTAMP
                WHERE id_usuario = %s AND id_frase = %s
                ''',
                (estrelas, user_id, id_frase)
            )
        else:
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


def atualizar_frase(user_id: int, id_frase: int, estrelas: int, precisao: int) -> dict:
    conexao = None
    cursor = None
    committed = False
    
    try:
        conexao = conectar()
        if conexao is None:
            raise Exception('Não foi possível conectar ao banco')
        
        conexao.autocommit = False
        cursor = conexao.cursor()

        # Bloqueia a linha para comparar os valores atuais antes de atualizar
        cursor.execute(
            '''
            SELECT estrelas, melhor_precisao
            FROM speech_teach.frases
            WHERE id_usuario = %s AND id_frase = %s
            FOR UPDATE
            ''',
            (user_id, id_frase)
        )
        row = cursor.fetchone()
        if not row:
            return {"success": False, "stars_earned": 0}

        estrelas_atual, melhor_precisao_atual = row
        estrelas_atual = estrelas_atual or 0
        deve_atualizar_estrelas = estrelas > estrelas_atual
        deve_atualizar_precisao = melhor_precisao_atual is None or precisao > melhor_precisao_atual

        stars_earned = max(0, estrelas - estrelas_atual)

        if not (deve_atualizar_estrelas or deve_atualizar_precisao):
            conexao.commit()
            committed = True
            return {"success": True, "stars_earned": 0}

        novas_estrelas = estrelas if deve_atualizar_estrelas else estrelas_atual
        nova_melhor_precisao = precisao if deve_atualizar_precisao else melhor_precisao_atual

        cursor.execute(
            '''
            UPDATE speech_teach.frases 
            SET estrelas = %s, melhor_precisao = %s, data_ultima_pratica = CURRENT_TIMESTAMP
            WHERE id_usuario = %s AND id_frase = %s
            ''',
            (novas_estrelas, nova_melhor_precisao, user_id, id_frase)
        )
        
        conexao.commit()
        committed = True
        return {"success": True, "stars_earned": stars_earned}
        
    except Exception as e:
        print(f"[FRASES] Erro ao atualizar estrelas: {e}")
        return {"success": False, "stars_earned": 0}
        
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
