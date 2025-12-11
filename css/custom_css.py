# css/custom_css.py

# This simple function finds the chatbot's scrollable area and sets scrollTop to max
js_scroll_chat = """
async () => {
    // Wait a tiny bit for the new message to actually render in the DOM
    await new Promise(r => setTimeout(r, 100));

    // Select the chatbot container
    const chatbot = document.querySelector('#chatbot');
    
    if (chatbot) {
        // In newer Gradio versions, the scrollable part is often a child div
        // We try to find the standard class, or fallback to the element itself
        const scrollable = chatbot.querySelector('.scroll-hide') || chatbot.querySelector('.bubble-wrap') || chatbot;
        
        if (scrollable) {
            scrollable.scrollTop = scrollable.scrollHeight;
        }
    }
}
"""

custom_css = """
<style>
/* Force the right column to fill vertical space */
#right_col { 
    display: flex !important; 
    flex-direction: column !important; 
    height: 100% !important; 
}

/* Chatbot should grow to fill available space and have a fixed min-height */
#chatbot { 
    flex-grow: 1 !important; 
    min-height: 500px !important; 
    height: 500px !important; /* Important for overflow to work */
    overflow-y: auto !important; 
}

/* Hide Scrollbar (Optional - remove if you want to see it) */
#chatbot *::-webkit-scrollbar { display: none; }
#chatbot * { -ms-overflow-style: none; scrollbar-width: none; }

/* Invisible Audio Player */
#invisible_audio { 
    height: 0px !important; 
    width: 0px !important; 
    opacity: 0; 
    overflow: hidden; 
    position: absolute; 
    z-index: -1; 
}
</style>
"""