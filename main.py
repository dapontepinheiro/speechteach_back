from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Optional
import uuid
from voice_chat import handle_voice_upload
from cadastro import cadastrar_usuario, autenticar_usuario
from stats import incrementar_estrelas, obter_estrelas, obter_stats_completas, atualizar_precisao_media, atualizar_melhor_precisao
from frases import atualizar_frase, buscar_frases_usuario, inicializar_frases_usuario
from ms_speech import sintetizar_frase

app = FastAPI(title="SpeechTeach API", version="0.1.0")

# Allow frontend dev server (vite default: http://localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores (replace with real DB later)
USERS: Dict[str, Dict] = {}
STATS: Dict[str, Dict] = {}

class SignupPayload(BaseModel):
    name: str
    email: str
    password: Optional[str] = None

class LoginPayload(BaseModel):
    email: str
    password: str

class UserPublic(BaseModel):
    id: str
    name: str

class Stats(BaseModel):
    user_id: str
    accuracy: float = 0.0
    phrases: int = 0
    streak: int = 0
    stars: int = 0
    bestAccuracy: float = 0.0

class ChatMessage(BaseModel):
    prompt: str

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/signup", response_model=UserPublic)
async def signup(payload: SignupPayload):
    try:
        # cadastrar_usuario agora retorna o ID gerado pelo banco
        user_id = cadastrar_usuario(payload.name, payload.email, payload.password)
        # Armazena usuário em memória para os endpoints /api/user
        USERS[str(user_id)] = {"id": str(user_id), "name": payload.name.strip()}
        # initialize stats
        STATS[str(user_id)] = Stats(user_id=str(user_id)).dict()
        # Inicializa todas as frases com valores zerados
        inicializar_frases_usuario(user_id)
        return {"id": str(user_id), "name": payload.name.strip()}
    except ValueError as e:
        # Usuário já existe
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        # Outros erros (conexão, etc.)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/login", response_model=UserPublic)
async def login(payload: LoginPayload):
    try:
        user_data = autenticar_usuario(payload.email, payload.password)
        # Armazena usuário em memória se ainda não existir
        user_id = str(user_data['id'])
        if user_id not in USERS:
            USERS[user_id] = {"id": user_id, "name": user_data['name']}
        if user_id not in STATS:
            STATS[user_id] = Stats(user_id=user_id).dict()
        
        # Atualiza a precisão média ao fazer login
        atualizar_precisao_media(int(user_id))
        atualizar_melhor_precisao(int(user_id))
        
        return {"id": user_id, "name": user_data['name']}
    except ValueError as e:
        # Credenciais inválidas
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        # Outros erros (conexão, etc.)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/{user_id}", response_model=UserPublic)
async def get_user(user_id: str):
    user = USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user["id"], "name": user["name"]}

@app.get("/api/stats/{user_id}", response_model=Stats)
async def get_stats(user_id: str):
    try:
        # Busca as stats completas do banco de dados
        stats_data = obter_stats_completas(int(user_id))
        
        return {
            "user_id": user_id,
            "accuracy": stats_data["accuracy"],
            "phrases": stats_data["phrases"],
            "streak": stats_data["streak"],
            "stars": stats_data["stars"],
            "bestAccuracy": stats_data["bestAccuracy"]
        }
    except Exception as e:
        print(f"[API] Erro ao obter stats: {e}")
        data = STATS.get(user_id)
        if not data:
            raise HTTPException(status_code=404, detail="Stats not found")
        return data

class StatsUpdate(BaseModel):
    accuracy: Optional[float] = None
    phrases: Optional[int] = None
    streak: Optional[int] = None

@app.post("/api/stats/{user_id}", response_model=Stats)
async def update_stats(user_id: str, payload: StatsUpdate):
    data = STATS.get(user_id)
    if not data:
        raise HTTPException(status_code=404, detail="Stats not found")
    for field, value in payload.dict(exclude_none=True).items():
        data[field] = value
    STATS[user_id] = data
    return data

class StarsPayload(BaseModel):
    stars: int

@app.post("/api/stats/{user_id}/stars")
async def update_stars(user_id: str, payload: StarsPayload):
    try:
        if payload.stars <= 0:
            return {"ok": True, "message": "no-op"}
        ok = incrementar_estrelas(int(user_id), payload.stars)
        if not ok:
            raise HTTPException(status_code=404, detail="Stats not found")
        
        # Busca o novo valor de estrelas do banco
        stars = obter_estrelas(int(user_id))
        
        # Atualiza também o store em memória
        if user_id in STATS:
            STATS[user_id]["stars"] = stars
        
        return {"ok": True, "stars": stars}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stats/{user_id}/sync-accuracy")
async def sync_accuracy(user_id: str):
    """Sincroniza a precisão média do usuário e retorna o valor atualizado"""
    try:
        # Atualiza a precisão média no banco
        atualizar_precisao_media(int(user_id))
        
        # Busca as stats atualizadas
        stats_data = obter_stats_completas(int(user_id))
        
        return {
            "ok": True,
            "accuracy": stats_data["accuracy"]
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id")
    except Exception as e:
        print(f"[API] Erro ao sincronizar precisão: {e}")
        raise HTTPException(status_code=500, detail=str(e))

class FrasePayload(BaseModel):
    id_frase: int
    texto_frase: str
    dificuldade: str
    serie: str
    estrelas: int
    precisao: int

@app.post("/api/frases/salvar")
async def salvar_frase_praticada(user_id: str, payload: FrasePayload):
    """Salva ou atualiza uma frase praticada pelo usuário, e adiciona apenas a diferença de estrelas"""
    try:
        # Atualiza a frase e obtém a quantidade de estrelas efetivamente conquistadas
        result = atualizar_frase(
            user_id=int(user_id),
            id_frase=payload.id_frase,
            estrelas=payload.estrelas,
            precisao=payload.precisao
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=500, detail="Failed to save phrase")
        
        # Incrementa apenas a diferença de estrelas conquistadas
        stars_earned = result.get("stars_earned", 0)
        if stars_earned > 0:
            ok = incrementar_estrelas(int(user_id), stars_earned)
            if not ok:
                raise HTTPException(status_code=500, detail="Failed to update stars")
        
        # Atualiza a precisão média do usuário
        atualizar_precisao_media(int(user_id))
        
        # Atualiza a melhor precisão do usuário
        atualizar_melhor_precisao(int(user_id))
        
        return {"ok": True, "stars_earned": stars_earned}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/frases/{user_id}")
async def buscar_frases(user_id: str):
    """Busca todas as frases praticadas por um usuário"""
    try:
        frases = buscar_frases_usuario(int(user_id))
        # Converte para formato {id_frase: estrelas}
        result = {frase["id_frase"]: frase["estrelas"] for frase in frases}
        return result
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(msg: ChatMessage):
    prompt = msg.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Empty prompt")
    return {
        "reply": "(mock) Você disse: '" + prompt + "'. Tente reformular usando o passado simples.",
    }

@app.post("/api/analyze-pronunciation")
async def analyze_pronunciation(
    file: UploadFile = File(...),
    reference_text: str = Form(...),
):
    try:
        result = await handle_voice_upload(file, reference_text)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")


@app.get("/api/synthesize-speech")
async def synthesize_speech(text: str):
    """
    Sintetiza um texto em áudio usando Azure Text-to-Speech.
    
    Args:
        text: Texto a ser convertido em áudio
        
    Returns:
        StreamingResponse com áudio em formato WAV
    """
    try:
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="Texto vazio")
        
        # Sintetiza o texto
        audio_data = sintetizar_frase(text.strip())
        
        # Retorna o áudio como stream
        return StreamingResponse(
            iter([audio_data]),
            media_type="audio/wav",
            headers={"Content-Disposition": "inline; filename=audio.wav"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error synthesizing speech: {str(e)}")

