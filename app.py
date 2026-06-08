from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import google.generativeai as genai
from gtts import gTTS
import os
import sys
import speech_recognition as sr

app = FastAPI()

@app.get("/")
def read_root():
    print("[LOG] 누군가 홈페이지(/) 경로로 접속했습니다.", flush=True)
    return {"status": "healthy", "message": "ESP32 Voice API is running perfectly!"}

@app.post("/talk")
async def handle_voice(file: UploadFile = File(...)):
    print(f"\n[LOG] ==================== 새로운 요청 수신 ====================", flush=True)
    print(f"[LOG] 1단계: 클라이언트가 전송한 파일 이름: {file.filename}", flush=True)
    
    input_audio_path = "input.wav"
    output_audio_path = "output.mp3"
    
    try:
        with open(input_audio_path, "wb") as buffer:
            buffer.write(await file.read())
        print("[LOG] 2단계: 전송받은 음성 데이터를 'input.wav'로 성공적으로 저장함.", flush=True)
    except Exception as e:
        print(f"[ERROR] 2단계 파일 저장 실패! 에러내용: {e}", file=sys.stderr, flush=True)
        return {"error": "서버 내 파일 저장 실패"}

    r = sr.Recognizer()
    text = ""
    try:
        print("[LOG] 3단계: SpeechRecognition으로 'input.wav' 오디오 파일 분석 시작...", flush=True)
        with sr.AudioFile(input_audio_path) as source:
            audio = r.record(source)
            
        text = r.recognize_google(audio, language="ko-KR")
        print(f"[LOG] 4단계: 구글 STT 인식 결과 성공 [ {text} ]", flush=True)
    except sr.UnknownValueError:
        print("[ERROR] 4단계 구글 STT 실패: 음성을 전혀 인식하지 못함 (UnknownValueError)", file=sys.stderr, flush=True)
        text = "음성을 인식하지 못했습니다."
    except sr.RequestError as e:
        print(f"[ERROR] 4단계 구글 STT 실패: 네트워크/API 서비스 오류 {e}", file=sys.stderr, flush=True)
        text = "STT 서비스 오류가 발생했습니다."
    except Exception as e:
        print(f"[ERROR] 4단계 예상치 못한 STT 오류 발생 {e}", file=sys.stderr, flush=True)
        text = "음성 인식 처리 중 오류 발생."

    reply_text = ""
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            print("[ERROR] 5단계 경고: Render 환경변수에 'GEMINI_API_KEY'가 누락되었습니다!", file=sys.stderr, flush=True)
            raise ValueError("GEMINI_API_KEY 미설정")
            
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        
        print(f"[LOG] 5단계: 제미나이 모델에게 텍스트 전달 중...", flush=True)
        response = model.generate_content([
            text,
            "이 질문에 대해 친절하게 한국어 한 문장으로 답변해줘."
        ])
        reply_text = response.text
        print(f"[LOG] 6단계: Gemini 답변 생성 완료 [ {reply_text} ]", flush=True)
    except Exception as e:
        reply_text = "죄송해요, 질문을 이해하지 못했어요."
        print(f"[ERROR] 5~6단계 Gemini API 연동 실패 {e}", file=sys.stderr, flush=True)

    try:
        print("[LOG] 7단계: 답변 텍스트를 gTTS를 이용해 MP3 음성 파일로 굽는 중...", flush=True)
        tts = gTTS(text=reply_text, lang='ko')
        tts.save(output_audio_path)
        print("[LOG] 8단계: MP3 파일 생성 완료! 클라이언트로 오디오 데이터 전송합니다.", flush=True)
    except Exception as e:
        print(f"[ERROR] 7~8단계 gTTS 변환 및 저장 실패 {e}", file=sys.stderr, flush=True)
        return {"error": "TTS 변환 실패"}
    
    print("[LOG] ==================== 요청 처리 완료 ====================\n", flush=True)
    return FileResponse(output_audio_path, media_type="audio/mpeg")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)