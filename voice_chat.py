"""
Voice Chat Module - Processa áudio do usuário e avalia pronúncia
Função: Receber arquivo de áudio, validar, salvar temporariamente e chamar ms_speech.avaliar_pronuncia
"""
import os
import tempfile
import shutil
import glob
from fastapi import UploadFile, HTTPException
from ms_speech import avaliar_pronuncia

# Tenta localizar o ffmpeg de forma portátil antes do import do pydub
def _resolve_ffmpeg_path() -> str | None:
    ffmpeg_bin = (os.getenv("FFMPEG_BIN") or "").strip()
    if ffmpeg_bin and os.path.isfile(ffmpeg_bin):
        return ffmpeg_bin

    ffmpeg_from_path = shutil.which("ffmpeg")
    if ffmpeg_from_path:
        return ffmpeg_from_path

    # Fallback para instalações comuns via Winget no Windows
    winget_root = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages")
    if os.path.isdir(winget_root):
        package_dirs = glob.glob(os.path.join(winget_root, "Gyan.FFmpeg*"))
        for package_dir in package_dirs:
            matches = glob.glob(
                os.path.join(package_dir, "**", "bin", "ffmpeg.exe"),
                recursive=True,
            )
            if matches:
                return matches[0]

    return None


ffmpeg_executable = _resolve_ffmpeg_path()
if ffmpeg_executable:
    ffmpeg_dir = os.path.dirname(ffmpeg_executable)
    os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")


class VoiceProcessor:
    SUPPORTED_FORMATS = {'audio/wav', 'audio/mpeg', 'audio/mp3', 'audio/webm', 'audio/ogg'}
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
    async def validate_audio_file(self, file: UploadFile) -> None:
        print('flag validate_audio_file')
        contents = await file.read()
        file_size = len(contents)
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Arquivo de áudio vazio")
        
        if file_size > self.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"Arquivo muito grande. Tamanho máximo: {self.MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        await file.seek(0)
        
        if file.content_type not in self.SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=415,
                detail=f"Formato não suportado. Formatos aceitos: {', '.join(self.SUPPORTED_FORMATS)}"
            )
    
    async def save_temp_audio(self, file: UploadFile) -> str:
        file_extension = self._get_file_extension(file.filename or 'audio.wav')
        temp_path = os.path.join(
            self.temp_dir,
            f"voice_chat_{os.urandom(8).hex()}{file_extension}"
        )
        
        contents = await file.read()
        with open(temp_path, 'wb') as f:
            f.write(contents)
        
        return temp_path
    
    def _get_file_extension(self, filename: str) -> str:
        if '.' in filename:
            return '.' + filename.rsplit('.', 1)[1].lower()
        return '.wav'
    
    def _convert_to_wav(self, input_path: str) -> str:
        try:
            if not ffmpeg_executable:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "FFmpeg não encontrado. Instale FFmpeg e adicione ao PATH, "
                        "ou configure FFMPEG_BIN no .env com o caminho completo do ffmpeg.exe"
                    ),
                )

            from pydub import AudioSegment
            AudioSegment.converter = ffmpeg_executable
            AudioSegment.ffmpeg = ffmpeg_executable
            print(f'Convertendo áudio: {input_path}')
            audio = AudioSegment.from_file(input_path)
            
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            
            wav_path = input_path.rsplit('.', 1)[0] + '_converted.wav'
            audio.export(wav_path, format='wav')
            print(f'Áudio convertido com sucesso')
            
            return wav_path
        except Exception as e:
            print(f'Erro na conversão: {str(e)}')
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao converter áudio: {str(e)}"
            )
    
    async def process_audio(self, file: UploadFile, reference_text: str) -> dict:
        await self.validate_audio_file(file)
        temp_path = await self.save_temp_audio(file)
        wav_path = None
        
        try:
            wav_path = self._convert_to_wav(temp_path)
            
            resultado = avaliar_pronuncia(wav_path, reference_text)
            return resultado
        except HTTPException:
            raise
        except Exception as e:
            print(f'Erro ao processar áudio: {str(e)}')
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Erro ao processar áudio: {str(e)}"
            )
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if wav_path and os.path.exists(wav_path):
                os.remove(wav_path)


voice_processor = VoiceProcessor()


async def handle_voice_upload(file: UploadFile, reference_text: str) -> dict:
    return await voice_processor.process_audio(file, reference_text)
