from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import google.generativeai as genai
from gtts import gTTS
import os
import speech_recognition as sr



app = FastAPI()

api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

@app.post("/talk")
async def handle_voice(file: UploadFile = File(...)):
    r = sr.Recognizer()

    with sr.AudioFile("input.wav") as source:
        audio = r.record(source)

    try:
        text = r.recognize_google(audio, language="ko-KR")
        print("인식된 텍스트:", text)
    except sr.UnknownValueError:
        print("음성을 인식하지 못했습니다.")
    except sr.RequestError as e:
        print("API 서비스 오류;", e)
    
    try:
        response = model.generate_content([
            text,
            "이 오디오를 듣고 질문에 친절하게 한국어로 답변해줘."
        ])
        reply_text = response.text
        print(f"Gemini 답변: {reply_text}")
        
    except Exception as e:
        reply_text = "죄송해요, 음성을 이해하지 못했어요."
        print(f"에러 발생: {e}")

    output_audio_path = "output.mp3"
    tts = gTTS(text=reply_text, lang='ko')
    tts.save(output_audio_path)
    
    return FileResponse(output_audio_path, media_type="audio/mpeg")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)