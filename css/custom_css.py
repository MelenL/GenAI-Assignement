js_scroll_chat = """
(args) => { 
    setTimeout(() => { 
        const c = document.getElementById('chatbot').querySelector('.scroll-hide'); 
        if(c) c.scrollTop = c.scrollHeight; 
    }, 100); 
    return args; 
}
"""

custom_css = """
<style>
#right_col { display: flex !important; flex-direction: column !important; }
#chatbot { flex-grow: 1 !important; min-height: 500px !important; }
#chatbot *::-webkit-scrollbar { display: none; }
#chatbot * { -ms-overflow-style: none; scrollbar-width: none; }
#invisible_audio { height: 0px !important; width: 0px !important; opacity: 0; overflow: hidden; position: absolute; z-index: -1; }
</style>
"""