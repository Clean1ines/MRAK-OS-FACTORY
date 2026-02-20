// chatHandlers.js - отправка сообщений
console.log('[CHATHANDLERS] загрузка начата');

const input = document.getElementById('input');
const sendBtn = document.getElementById('send-btn');
const messagesDiv = document.getElementById('messages');
const scrollAnchor = document.getElementById('scroll-anchor');
const modelSelect = document.getElementById('model-select');
const statusText = document.getElementById('status-text');

window.start = async function start() {
    console.log('[CHATHANDLERS] start called');
    const prompt = input.value.trim();
    if (!prompt) return;
    const pid = state.getCurrentProjectId();
    if (!pid) {
        window.ui?.showNotification('Сначала выберите проект', 'error');
        return;
    }
    const mode = document.getElementById('mode-select').value;
    const model = modelSelect.value;

    input.value = '';
    input.style.height = '44px';
    input.disabled = true;
    sendBtn.disabled = true;
    statusText.innerText = 'NEURAL_LINK_ESTABLISHED...';

    const userDiv = document.createElement('div');
    userDiv.className = 'border-l-2 border-zinc-800 pl-6 text-sm text-zinc-400';
    userDiv.innerText = prompt;
    messagesDiv.appendChild(userDiv);

    const assistantDiv = document.createElement('div');
    assistantDiv.className = 'markdown-body streaming';
    messagesDiv.appendChild(assistantDiv);
    assistantDiv.dataset.originalPrompt = prompt;
    const toolbar = window.createMessageToolbar?.(assistantDiv);
    if (toolbar) messagesDiv.appendChild(toolbar);

    try {
        const res = await api.sendChatMessage(prompt, mode, model, pid);
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let raw = '';
        let metaDone = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            let chunk = decoder.decode(value);
            if (!metaDone && chunk.includes('__METADATA__')) {
                const parts = chunk.split('__');
                const meta = parts[2].split('|');
                document.getElementById('q-tokens').innerText = meta[0];
                document.getElementById('q-req').innerText = meta[1];
                chunk = parts.slice(3).join('__');
                metaDone = true;
            }
            raw += chunk;
            assistantDiv.innerHTML = marked.parse(raw);
            assistantDiv.dataset.rawMarkdown = raw;
            scrollAnchor.scrollIntoView({ behavior: 'smooth' });
        }
    } catch (e) {
        assistantDiv.innerHTML = `<span class="text-red-500">SYSTEM_ERROR: ${e.message}</span>`;
    } finally {
        assistantDiv.classList.remove('streaming');
        input.disabled = false;
        sendBtn.disabled = false;
        statusText.innerText = 'SYSTEM_READY';
        input.focus();
    }
};

if (sendBtn) {
    sendBtn.onclick = window.start;
}
if (input) {
    input.onkeydown = function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            window.start();
        }
    };
}

console.log('[CHATHANDLERS] загрузка завершена');
