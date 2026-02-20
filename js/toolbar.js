// toolbar.js - функции для создания тулбара сообщений

window.createMessageToolbar = function(messageElement) {
    const toolbar = document.createElement("div");
    toolbar.className = "message-toolbar";

    const copyBtn = document.createElement("button");
    copyBtn.innerText = "Copy";
    copyBtn.onclick = async () => {
        try { await navigator.clipboard.writeText(messageElement.innerText); } catch (_) {
            const textarea = document.createElement("textarea");
            textarea.value = messageElement.innerText;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand("copy");
            document.body.removeChild(textarea);
        }
    };

    const editBtn = document.createElement("button");
    editBtn.innerText = "Edit";
    editBtn.onclick = () => {
        const raw = messageElement.dataset.rawMarkdown || messageElement.innerText;
        const editArea = document.createElement("textarea");
        editArea.value = raw;
        editArea.className = "w-full bg-transparent text-gray-200 p-2 border border-zinc-700 rounded";
        const saveBtn = document.createElement("button");
        saveBtn.innerText = "Save";
        saveBtn.className = "ml-2 p-1 bg-emerald-600/20 rounded";
        saveBtn.onclick = () => {
            const newRaw = editArea.value;
            messageElement.innerHTML = marked.parse(newRaw);
            messageElement.dataset.rawMarkdown = newRaw;
            editArea.remove();
            saveBtn.remove();
        };
        messageElement.appendChild(editArea);
        messageElement.appendChild(saveBtn);
    };

    const regenerateBtn = document.createElement("button");
    regenerateBtn.innerText = "Regenerate";
    regenerateBtn.onclick = async () => {
        const original = messageElement.dataset.originalPrompt;
        if (!original) return;
        input.value = original;
        input.style.height = "auto";
        await window.start();
    };

    const shareBtn = document.createElement("button");
    shareBtn.innerText = "Share";
    shareBtn.onclick = async () => {
        const shareText = `Shared Message:\n${messageElement.innerText}`;
        try { await navigator.clipboard.writeText(shareText); } catch (_) {
            const textarea = document.createElement("textarea");
            textarea.value = shareText;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand("copy");
            document.body.removeChild(textarea);
        }
    };

    toolbar.appendChild(copyBtn);
    toolbar.appendChild(editBtn);
    toolbar.appendChild(regenerateBtn);
    toolbar.appendChild(shareBtn);
    return toolbar;
};

// ===== ДИАГНОСТИКА TOOLBAR =====
console.log('[TOOLBAR] файл загружен');

const originalCreateMessageToolbar = window.createMessageToolbar;
if (originalCreateMessageToolbar) {
    window.createMessageToolbar = function(messageElement) {
        console.log('[TOOLBAR] createMessageToolbar', { messageId: messageElement?.id });
        return originalCreateMessageToolbar(messageElement);
    };
}
console.log('[TOOLBAR] файл загружен');
const originalCreateMessageToolbar = window.createMessageToolbar;
if (originalCreateMessageToolbar) {
    window.createMessageToolbar = function(messageElement) {
        console.log('[TOOLBAR] createMessageToolbar', { messageId: messageElement?.id });
        return originalCreateMessageToolbar(messageElement);
    };
}
