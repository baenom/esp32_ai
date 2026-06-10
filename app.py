from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from google import genai
from gtts import gTTS
import os
import sys
import speech_recognition as sr

app = FastAPI()

client = genai.Client()

@app.get("/")
def read_root():
    return {"status": "healthy", "message": "New GenAI Client API is running!"}

@app.post("/talk")
async def handle_voice(file: UploadFile = File(...)):
    print(f"\n[LOG] ==================== 새로운 요청 수신 ====================", flush=True)
    
    input_audio_path = "input.wav"
    output_audio_path = "output.mp3"
    
    try:
        with open(input_audio_path, "wb") as buffer:
            buffer.write(await file.read())
        print("[LOG] 1단계: 음성 파일 저장 완료", flush=True)
    except Exception as e:
        print(f"[ERROR] 파일 저장 실패: {e}", file=sys.stderr, flush=True)
        return {"error": "File save failed"}

    r = sr.Recognizer()
    text = ""
    try:
        with sr.AudioFile(input_audio_path) as source:
            audio = r.record(source)
        text = r.recognize_google(audio, language="ko-KR")
        print(f"[LOG] 2단계: STT 성공 [ {text} ]", flush=True)
    except Exception as e:
        print(f"[ERROR] STT 오류 발생: {e}", file=sys.stderr, flush=True)
        text = "음성 인식에 실패했습니다."

    reply_text = ""
    try:
        print("[LOG] 3단계: Gemini-2.5-Flash 호출 중...", flush=True)
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[text, "너의 이름은 '김치피티'고 너는 내 비서야 이 질문에 대해 친절하게 한국어로 답변해줘."]
        )
        reply_text = response.text
        print(f"[LOG] 4단계: Gemini 답변 완료 [ {reply_text} ]", flush=True)
    except Exception as e:
        print(f"[ERROR] Gemini API 호출 실패: {e}", file=sys.stderr, flush=True)
        reply_text = "제미나이 엔진에서 답변을 생성하지 못했습니다."

    try:
        tts = gTTS(text=reply_text, lang='ko')
        tts.save(output_audio_path)
        print("[LOG] 5단계: MP3 변환 완료 및 전송", flush=True)
    except Exception as e:
        print(f"[ERROR] gTTS 에러: {e}", file=sys.stderr, flush=True)
        return {"error": "TTS conversion failed"}
    
    print("[LOG] ==================== 요청 처리 완료 ====================\n", flush=True)
    return FileResponse(output_audio_path, media_type="audio/mpeg")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)