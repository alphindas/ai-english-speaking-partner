import os
import uuid
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development convenience
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data Models ---
class ChatRequest(BaseModel):
    user_message: str
    mode: Optional[str] = "chat" # Default to chat
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    ai_reply: str
    grammar_correction: Optional[str] = None
    session_id: str

# --- In-memory Storage ---
# Structure: { session_id: [ {"role": "user", "parts": ["msg"]}, ... ] }
# We will limit to last 10 turns (20 messages)
conversations: Dict[str, List[Dict[str, str]]] = {}

# --- Gemini Configuration ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
model = None
TARGET_MODEL_NAME = ""

if GOOGLE_API_KEY:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        # listing available models to debug
        available_models = [m.name for m in genai.list_models()]
        print(f"Available models count: {len(available_models)}")
        
        # Priority list for models likely to have better quotas
        # Gemma 3 models are currently working well in this environment
        priority_models = [
            'models/gemma-3-27b-it',
            'models/gemma-3-12b-it',
            'models/gemma-3-4b-it',
            'models/gemini-2.0-flash', # Keeping as fallback
            'models/gemini-flash-latest'
        ]
        
        target_model = None
        for p in priority_models:
            if p in available_models:
                target_model = p
                break
        
        if not target_model:
             # Fallback: search for any gemma model first
             for m in available_models:
                 if 'gemma' in m and '-it' in m:
                     target_model = m
                     break
        
        if not target_model:
            target_model = available_models[0] if available_models else 'models/gemini-1.5-flash'
        
        print(f"Selected model: {target_model}")
        TARGET_MODEL_NAME = target_model
        model = genai.GenerativeModel(target_model)
        print("Model initialized successfully.")
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")
else:
    print("WARNING: GOOGLE_API_KEY not found. Running in MOCK mode.")

CHAT_PROMPT = """
You are a warm, supportive, and casual AI English conversation partner.
Speak like a friendly human, not a teacher. Encourage confidence and free expression.
Use simple, natural English. Keep responses conversational and engaging.
Ask follow-up questions to keep the chat flowing.
Do NOT correct grammar unless the user explicitly asks.
Avoid long explanations or lectures.
Do not evaluate or score the user. Do not act as a tutor or interviewer.
Do not mention being an AI or a language model.

Output your response in JSON format with two keys:
1. "ai_reply": Your conversational response. Keep it natural, somewhat concise (1-3 sentences), and supportive.
2. "grammar_correction": Return null unless the user asks for correction.
"""

INTERVIEW_PROMPT = """
You are an expert AI Job Interviewer. Your goal is to conduct a highly dynamic, realistic, and adaptive mock interview.

DYNAMIC FLOW RULES:
1. START: If the user's target job role is unknown, your first question MUST be to ask what position they are interviewing for.
2. ADAPT: Do NOT use fixed questions. Generate questions based on the user's target role, their previous answers, and the natural flow of a professional conversation.
3. DEPTH: Ask follow-up questions if an answer is vague or interesting. Challenge the user like a real interviewer would.
4. ONE AT A TIME: Ask ONLY one question at a time. Wait for the user's response.
5. LENGTH: Aim for a focused interview of about 5-8 questions. If you feel the interview has reached a natural conclusion, provide the FINAL EVALUATION.

FEEDBACK MECHANISM (After every user answer):
You MUST provide constructive feedback in the "grammar_correction" field using this EXACT format:
📝 Feedback: [Concise feedback on their answer's content and delivery]
⭐ Score: [X] / 10
💡 Improvement Tip: [One specific actionable suggestion]

RESPONSE STRUCTURE:
The "ai_reply" field should contain ONLY your next interview question or follow-up.

FINAL EVALUATION:
When the interview is complete (or the user wants to stop):
- "ai_reply" should contain a comprehensive summary:
  - Overall Performance Summary
  - Key Strengths & Areas for Improvement
  - Final Interview Score
  - 3 Actionable Tips for the real interview
- "grammar_correction" can be null for the final evaluation.

Output your response in JSON format with two keys:
1. "ai_reply": Your next question or the final evaluation.
2. "grammar_correction": The mandatory feedback/score/tip for the last answer (except for the start/end where it might be null).

Constraints:
- Maintain a professional, fair, and slightly challenging tone.
- Do not mention you are an AI. Stay in character as the interviewer.
"""

def manage_history(session_id: str, new_message: dict):
    if session_id not in conversations:
        conversations[session_id] = []
    
    conversations[session_id].append(new_message)
    
    # Keep only last 20 messages (10 turns)
    if len(conversations[session_id]) > 20:
        conversations[session_id] = conversations[session_id][-20:]

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    user_text = request.user_message
    mode = request.mode or "chat"
    
    # Add user message to history
    manage_history(session_id, {"role": "user", "parts": [user_text]})

    ai_reply = ""
    grammar_correction = None

    if model:
        try:
            # Select prompt based on mode
            system_prompt = INTERVIEW_PROMPT if mode == "interview" else CHAT_PROMPT
            
            context_str = "\n".join([f"{msg['role'].upper()}: {msg['parts'][0]}" for msg in conversations[session_id]])
            full_prompt = f"{system_prompt}\n\nConversation History:\n{context_str}\n\nRespond ONLY in valid JSON format."
            
            # Use JSON mode if possible (Gemini), otherwise standard (Gemma)
            gen_config = {}
            if 'gemini' in TARGET_MODEL_NAME.lower():
                gen_config["response_mime_type"] = "application/json"
            
            response = model.generate_content(full_prompt, generation_config=gen_config)
            
            # Robust JSON extraction
            import json
            text = response.text.strip()
            
            # For models like Gemma that might wrap JSON in backticks
            if "```json" in text:
                text = text.split("```json")[-1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[-1].split("```")[0].strip()
            
            data = json.loads(text)
            ai_reply = data.get("ai_reply", "I'm sorry, I didn't catch that.")
            grammar_correction = data.get("grammar_correction")

        except Exception as e:
            print(f"Error calling AI: {e}")
            ai_reply = f"I'm having trouble connecting to my brain right now. Error details: {str(e)}"
            grammar_correction = None
    else:
        # Mock Response
        ai_reply = f"[{mode.upper()} MODE] I heard you say: '{user_text}'. (MockAI Mode)"
        grammar_correction = "Mock feedback: Good effort!" if mode == "interview" else None

    # Update history with AI response
    manage_history(session_id, {"role": "model", "parts": [ai_reply]})

    return ChatResponse(
        ai_reply=ai_reply,
        grammar_correction=grammar_correction,
        session_id=session_id
    )

# Mount the frontend directory to serve static files
from fastapi.staticfiles import StaticFiles
# Mount to root, so index.html is served at /
# We use absolute path or relative to main.py
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    print(f"WARNING: Frontend directory not found at {frontend_path}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
