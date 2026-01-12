/**
 * AI English Speaking Partner - Core Logic
 * Handles: Mode switching, AI personalities, Voice integration, Chat UI
 */

// --- Global State ---
const state = {
    mode: 'chat', // 'chat', 'tutor', 'interview'
    userName: 'User',
    interviewStep: 1,
    totalInterviewQuestions: 5,
    isTyping: false,
    recognition: null,
    isRecording: false
};

// --- Configurations ---
const MODES = {
    chat: {
        title: "Friendly Chat",
        icon: "💬",
        badge: "Casual",
        welcome: "Hey there! I'm your friendly AI partner. Let's just chat about anything. How's your day going?",
        prompt: "You are a friendly, warm, and encouraging AI English partner. Chat naturally like a supportive friend. Do not correct grammar unless specifically asked. Focus on keeping the conversation flowing smoothly."
    },
    tutor: {
        title: "English Tutor",
        icon: "📘",
        badge: "Educational",
        welcome: "Hello! I'm your English Tutor. I'll help you improve your grammar and vocabulary while we talk. Ready to start?",
        prompt: "You are a professional English tutor. Always provide helpful but polite corrections when you notice a significant grammar mistake. Explain the correction briefly and provide one better way to say it. Keep the tone encouraging."
    },
    interview: {
        title: "Interview Prep",
        icon: "🎤",
        badge: "Professional",
        welcome: "Welcome to your dynamic mock interview. I can help you practice for any role. To get started, what position are we practicing for today?",
        prompt: "You are a professional interviewer. Ask one clear interview question at a time. Wait for the user to answer. After each answer, give very brief constructive feedback on how they can improve their response, then move to the next question. Maintain a formal but fair tone."
    }
};

// --- DOM Elements ---
const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const micBtn = document.getElementById('mic-btn');
const typingIndicator = document.getElementById('typing-indicator');
const modeTitle = document.getElementById('mode-title');
const modeIcon = document.getElementById('mode-icon');
const modeBadge = document.getElementById('mode-badge');
const interviewProgress = document.getElementById('interview-progress');
const questionCounter = document.getElementById('question-counter');
const progressFill = document.getElementById('progress-fill');
const grammarTip = document.getElementById('grammar-tip');
const tipText = document.getElementById('tip-text');

// --- Initialization ---
function init() {
    const params = new URLSearchParams(window.location.search);
    state.mode = params.get('mode') || 'chat';

    setupUIForMode();
    setupSpeech();

    // Event Listeners
    sendBtn.addEventListener('click', handleUserMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !state.isTyping) handleUserMessage();
    });

    // Initial AI welcome
    setTimeout(() => {
        setTyping(true);
        setTimeout(() => {
            addMessage(MODES[state.mode].welcome, 'ai');
            speak(MODES[state.mode].welcome);
            setTyping(false);
        }, 1000);
    }, 500);
}

// --- UI Logic ---
function setupUIForMode() {
    const config = MODES[state.mode];
    modeTitle.innerText = config.title;
    modeIcon.innerText = config.icon;
    modeBadge.innerText = config.badge;

    if (state.mode === 'interview') {
        interviewProgress.style.display = 'block';
        updateInterviewUI();
    }
}

function updateInterviewUI() {
    questionCounter.innerText = `Dynamic Interview Session`;
    // We'll use a slow indeterminate progress or just hide it
    progressFill.style.width = `100%`;
    progressFill.style.opacity = "0.5";
}

function setTyping(isTyping) {
    state.isTyping = isTyping;
    typingIndicator.style.display = isTyping ? 'flex' : 'none';
    userInput.disabled = isTyping;
    sendBtn.disabled = isTyping;
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('message', `${sender}-message`);
    msgDiv.innerText = text;
    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// --- Core Logic ---
async function handleUserMessage() {
    const text = userInput.value.trim();
    if (!text || state.isTyping) return;

    addMessage(text, 'user');
    userInput.value = '';

    setTyping(true);

    try {
        // Use actual API endpoint if available, otherwise use mock logic
        // This connects to the backend running on port 8000
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_message: text,
                mode: state.mode,
                session_id: "premium-user-" + state.mode
            })
        });

        const data = await response.json();

        // Handle Interview progression (simplified for dynamic flow)
        if (state.mode === 'interview') {
            state.interviewStep++;
            // If the AI detects its the end, we don't need to do anything special here as the prompt handles it
        }

        // Show AI reply
        addMessage(data.ai_reply, 'ai');
        speak(data.ai_reply);

        // Show Grammar Correction if in Tutor Mode
        if (state.mode === 'tutor' && data.grammar_correction) {
            showTip(data.grammar_correction);
        }

    } catch (err) {
        console.warn("Backend not detected, using fallback mock logic.");
        // Mock fallback for presentation
        setTimeout(() => {
            const fallbackMsg = "I'm having trouble connecting to my brain! Please make sure the backend server is running.";
            addMessage(fallbackMsg, 'ai');
            speak(fallbackMsg);
        }, 1500);
    } finally {
        setTyping(false);
    }
}

function showTip(text) {
    tipText.innerText = text;
    grammarTip.style.display = 'block';
    setTimeout(() => {
        grammarTip.style.display = 'none';
    }, 8000);
}

// --- Speech Logic ---
function setupSpeech() {
    if (!('webkitSpeechRecognition' in window)) {
        micBtn.style.display = 'none';
        return;
    }

    const recognition = new webkitSpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = false;

    recognition.onstart = () => {
        state.isRecording = true;
        micBtn.style.background = 'var(--accent-secondary)';
    };

    recognition.onend = () => {
        state.isRecording = false;
        micBtn.style.background = 'var(--glass-bg)';
    };

    recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        userInput.value = transcript;
        handleUserMessage();
    };

    micBtn.addEventListener('click', () => {
        if (state.isRecording) recognition.stop();
        else recognition.start();
    });
}

function speak(text) {
    if (!('speechSynthesis' in window)) return;

    const utter = new SpeechSynthesisUtterance(text);
    utter.rate = 1.0;
    utter.pitch = 1.1;

    // Find a nice voice
    const voices = window.speechSynthesis.getVoices();
    const voice = voices.find(v => v.lang.startsWith('en') && v.name.includes('Female')) || voices[0];
    if (voice) utter.voice = voice;

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utter);
}

// Run init
if (document.getElementById('chat-messages')) {
    init();
}
