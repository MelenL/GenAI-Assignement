# css/custom_css.py

# JS helper: scroll the chatbot to the newest message
js_scroll_chat = """
async () => {
    // Wait a tiny bit for the new message to render
    await new Promise(r => setTimeout(r, 100));

    const chatbot = document.querySelector('#chatbot');
    if (chatbot) {
        const scrollable =
            chatbot.querySelector('.scroll-hide') ||
            chatbot.querySelector('.bubble-wrap') ||
            chatbot;

        if (scrollable) {
            scrollable.scrollTop = scrollable.scrollHeight;
        }
    }
}
"""

# CSS injected via gr.HTML(custom_css)
custom_css = """
<style>
/* ===== GLOBAL ===== */
.gradio-container {
    max-width: 1150px !important;
    margin: 0 auto !important;
    background: #030508 !important;
}

body {
    background: #030508;
    color: #e5e7eb;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* ===== TOP BAR ===== */
#top_bar {
    background: #05070b;
    border-bottom: 1px solid #111827;
    padding: 14px 22px 10px;
    margin-bottom: 16px;
}

#top_bar h2 {
    font-size: 14px;
    letter-spacing: 0.28em;
    text-transform: uppercase;
}

#top_bar h4 {
    font-size: 10px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #6b7280;
}

#top_bar [data-testid="dropdown"] {
    background: #030508;
    border-radius: 0;
    border: 1px solid #111827;
}

#top_bar button {
    border-radius: 0;
    background: transparent;
    border: 1px solid #ef4444;
    color: #ef4444;
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
}

/* ===== PANELS ===== */
.case-panel, .log-panel {
    background: #05070b;
    border-radius: 18px;
    border: 1px solid #111827;
    padding: 18px 22px;
    box-shadow: 0 26px 60px rgba(0,0,0,0.65);
}

/* ===== CASE HEADER (left) ===== */
#case_header h4 {
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #9ca3af;
    margin-bottom: 12px;
}

#case_header h1 {
    font-size: 36px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin: 0 0 4px 0;
    color: #f9fafb;
}

#case_header strong {
    font-size: 11px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #9ca3af;
}

#case_header p {
    margin-top: 10px;
    color: #d1d5db;
    line-height: 1.4;
}

/* Base audio button layout (no colors here) */
#audio_btn {
    width: 100%;
    justify-content: flex-start;
    margin-top: 14px;
    border-radius: 0;
    background: transparent;
    font-size: 11px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

/* ON state: primary variant -> red */
#audio_btn.primary {
    opacity: 1;
    color: #ef4444;
    border: 1px solid #ef4444;
}

/* OFF state: secondary variant -> grey */
#audio_btn.secondary {
    opacity: 0.8;
    color: #6b7280;
    border: 1px solid #374151;
}

/* Evidence image inside the same card */
#evidence_image {
    margin-top: 18px;
}

#evidence_image img {
    border-radius: 10px;
    box-shadow: 0 18px 45px rgba(0,0,0,0.7);
    width: 100%;
    object-fit: contain;
}

/* ===== INTERROGATION LOG (right) ===== */
#log_title h3 {
    font-size: 13px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #e5e7eb;
}

/* Right column layout */
#right_col {
    display: flex !important;
    flex-direction: column !important;
    height: 100% !important;
}

/* Chat area */
#chatbot {
    flex-grow: 1 !important;
    min-height: 380px !important;
    max-height: 380px;
    overflow-y: auto !important;
    margin-top: 10px;
    padding-right: 4px;
}

/* Chat bubbles – single dark card with one red left border */
#chatbot .message {
    background: #05070b !important;
    border-radius: 10px;
    border: 1px solid #111827;
    border-left: 3px solid #ef4444;
    padding: 10px 14px 10px 18px;
    margin-bottom: 10px;
}

/* Remove any extra inner boxes / borders / backgrounds */
#chatbot .message > div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* Text color inside bubbles */
#chatbot .message p,
#chatbot .message span,
#chatbot .message div {
    color: #e5e7eb !important;
    line-height: 1.4;
}

/* Hide scrollbar (optional) */
#chatbot *::-webkit-scrollbar { display: none; }
#chatbot * { -ms-overflow-style: none; scrollbar-width: none; }

/* Hide any default buttons inside the Chatbot (your Hint/Execute are not inside #chatbot) */
#chatbot button {
    display: none !important;
    visibility: hidden !important;
    width: 0px !important;
    height: 0px !important;
}

/* ===== QUESTION COMMAND BAR ===== */
#question_row {
    margin-top: 18px;
    align-items: center;
    border-top: 1px solid #111827;
    padding-top: 12px;
    column-gap: 8px;
}

/* keep the box white, but text dark */
#question_box textarea {
    background: #f9fafb !important;
    border-radius: 6px;
    border: 1px solid #111827;
    color: #111827 !important;
    padding: 8px 10px !important;
    font-size: 13px;
}

#question_box textarea::placeholder {
    color: #6b7280;
}

/* Hint + Execute buttons */
#hint_btn,
#ask_btn button {
    height: 32px;
    font-size: 10px;
    letter-spacing: 0.20em;
    text-transform: uppercase;
    border-radius: 4px;
}

/* subtle secondary button */
#hint_btn {
    background: transparent;
    border: 1px solid #4b5563;
    color: #9ca3af;
    padding: 0 10px;
}

/* main action */
#ask_btn button {
    background: #ef4444;
    border: 1px solid #b91c1c;
    color: #f9fafb;
    font-weight: 600;
    padding: 0 14px;
}

/* Invisible audio */
#invisible_audio {
    height: 0px !important;
    width: 0px !important;
    opacity: 0;
    overflow: hidden;
    position: absolute;
    z-index: -1;
}

/* Hide Gradio footer */
footer, .footer { display: none !important; }
</style>
"""
