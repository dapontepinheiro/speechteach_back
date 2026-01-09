from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Dict, Optional
from datetime import datetime, timedelta
import uuid
import os
from jose import JWTError, jwt
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

from voice_chat import handle_voice_upload
from cadastro import cadastrar_usuario, autenticar_usuario
from stats import incrementar_estrelas, obter_estrelas, obter_stats_completas, atualizar_precisao_media, atualizar_melhor_precisao
from frases import atualizar_frase, buscar_frases_usuario, inicializar_frases_usuario, catalogo_frases
from ms_speech import sintetizar_frase

# ============================================================
# CONFIGURAÇÃO JWT
# ============================================================
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY não definida no .env")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 15

# Origens permitidas (deve ser definido em .env para dev e produção)
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()
]

# Esquema de segurança HTTP Bearer (auto_error=False para tratar manualmente)
security = HTTPBearer(auto_error=False)

app = FastAPI(title="SpeechTeach API", version="0.1.0")

# Allow frontend dev server (vite default: http://localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_https(request: Request, call_next):
    """Exige HTTPS em produção; libera localhost para desenvolvimento."""
    host = request.headers.get("host", "")
    is_local = host.startswith("localhost") or host.startswith("127.0.0.1")
    proto = request.headers.get("x-forwarded-proto") or request.url.scheme

    if not is_local and proto != "https":
        raise HTTPException(status_code=400, detail="HTTPS é obrigatório em produção")

    return await call_next(request)

# ============================================================
# SEGURANÇA: Headers de proteção HTTP
# ============================================================
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    return response

# In-memory stores (replace with real DB later)
USERS: Dict[str, Dict] = {}
STATS: Dict[str, Dict] = {}

class SignupPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=5, max_length=150, pattern=r"^.+@.+\..+$")
    password: str = Field(..., min_length=6, max_length=128)

class LoginPayload(BaseModel):
    email: str = Field(..., min_length=5, max_length=150, pattern=r"^.+@.+\..+$")
    password: str = Field(..., min_length=6, max_length=128)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: "UserPublic"

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

# ============================================================
# FUNÇÕES JWT
# ============================================================
def criar_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria um JWT access token com expiração"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def criar_refresh_token(data: dict) -> str:
    """Cria um JWT refresh token com expiração longa"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verificar_token(token: str) -> dict:
    """Verifica e decodifica um JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return {"user_id": user_id}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expirado ou inválido")


def _cookie_settings(request: Request) -> dict:
    secure = request.url.scheme == "https"
    samesite = "none" if secure else "lax"
    return {"secure": secure, "samesite": samesite}


def set_auth_cookies(response: Response, access_token: str, refresh_token: str, request: Request) -> None:
    settings = _cookie_settings(request)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=settings["secure"],
        samesite=settings["samesite"],
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings["secure"],
        samesite=settings["samesite"],
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )

async def obter_usuario_atual(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """Dependência para verificar autenticação via bearer token ou cookie"""
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(status_code=401, detail="Token não fornecido")

    payload = verificar_token(token)
    user_id = str(payload["user_id"]).strip()
    return user_id

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/quotes")
async def get_quotes():
    return catalogo_frases()

@app.post("/api/signup", response_model=TokenResponse)
async def signup(payload: SignupPayload, response: Response, request: Request):
    try:
        user_id = cadastrar_usuario(payload.name, payload.email, payload.password)
        # Armazena usuário em memória para os endpoints /api/user
        USERS[str(user_id)] = {"id": str(user_id), "name": payload.name.strip()}
        # initialize stats
        STATS[str(user_id)] = Stats(user_id=str(user_id)).dict()
        # Inicializa todas as frases com valores zerados
        inicializar_frases_usuario(user_id)
        
        # Cria tokens JWT
        access_token = criar_access_token({"sub": str(user_id)})
        refresh_token = criar_refresh_token({"sub": str(user_id)})
        
        set_auth_cookies(response, access_token, refresh_token, request)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {"id": str(user_id), "name": payload.name.strip()}
        }
    except ValueError as e:
        # Usuário já existe
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        # Outros erros (conexão, etc.)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/login", response_model=TokenResponse)
async def login(payload: LoginPayload, response: Response, request: Request):
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
        
        # Cria tokens JWT
        access_token = criar_access_token({"sub": user_id})
        refresh_token = criar_refresh_token({"sub": user_id})
        
        set_auth_cookies(response, access_token, refresh_token, request)
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {"id": user_id, "name": user_data['name']}
        }
    except ValueError as e:
        # Credenciais inválidas
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        # Outros erros (conexão, etc.)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/refresh-token")
async def refresh_token(response: Response, request: Request, token: Optional[str] = None):
    """Renova um access token usando um refresh token"""
    try:
        token_to_use = token or request.cookies.get("refresh_token")
        if not token_to_use:
            raise HTTPException(status_code=401, detail="Refresh token não fornecido")

        payload = jwt.decode(token_to_use, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Token não é um refresh token")
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token inválido")
        
        access_token = criar_access_token({"sub": user_id})
        refresh_token = token_to_use
        set_auth_cookies(response, access_token, refresh_token, request)
        return {"access_token": access_token, "token_type": "bearer"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expirado ou inválido")

@app.get("/api/user/{user_id}", response_model=UserPublic)
async def get_user(user_id: str, current_user: str = Depends(obter_usuario_atual)):
    if current_user != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    user = USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": user["id"], "name": user["name"]}

@app.get("/api/stats/{user_id}", response_model=Stats)
async def get_stats(user_id: str, current_user: str = Depends(obter_usuario_atual)):
    if current_user != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
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
    except Exception:
        data = STATS.get(user_id)
        if not data:
            raise HTTPException(status_code=404, detail="Stats not found")
        return data

class StatsUpdate(BaseModel):
    accuracy: Optional[float] = None
    phrases: Optional[int] = None
    streak: Optional[int] = None

@app.post("/api/stats/{user_id}", response_model=Stats)
async def update_stats(user_id: str, payload: StatsUpdate, current_user: str = Depends(obter_usuario_atual)):
    if current_user != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
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
async def update_stars(user_id: str, payload: StarsPayload, current_user: str = Depends(obter_usuario_atual)):
    if current_user != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
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
async def sync_accuracy(user_id: str, current_user: str = Depends(obter_usuario_atual)):
    if current_user != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
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
        raise HTTPException(status_code=500, detail=str(e))

class FrasePayload(BaseModel):
    id_frase: int
    texto_frase: str
    dificuldade: str
    serie: str
    estrelas: int
    precisao: int

@app.post("/api/frases/salvar")
async def salvar_frase_praticada(user_id: str, payload: FrasePayload, current_user: str = Depends(obter_usuario_atual)):
    if current_user != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
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
async def buscar_frases(user_id: str, current_user: str = Depends(obter_usuario_atual)):
    if current_user != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")
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
async def chat(msg: ChatMessage, current_user: str = Depends(obter_usuario_atual)):
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
    current_user: str = Depends(obter_usuario_atual),
):
    try:
        result = await handle_voice_upload(file, reference_text)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")


@app.get("/api/synthesize-speech")
async def synthesize_speech(text: str, current_user: str = Depends(obter_usuario_atual)):
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

