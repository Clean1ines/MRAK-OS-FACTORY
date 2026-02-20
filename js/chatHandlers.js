// chatHandlers.js - отправка сообщений
console.log('[CHATHANDLERS] загрузка начата');

(function() {
    const sendBtn = document.getElementById('send-btn');
    const input = document.getElementById('input');

    if (sendBtn) {
        const originalClick = sendBtn.onclick;
        sendBtn.onclick = async function(e) {
            console.log('[CHATHANDLERS] sendBtn onclick');
            if (originalClick) await originalClick(e);
        };
    }

    if (input) {
        const originalKeydown = input.onkeydown;
        input.onkeydown = function(e) {
            console.log('[CHATHANDLERS] input keydown', { key: e.key, shiftKey: e.shiftKey });
            if (originalKeydown) originalKeydown(e);
        };
    }

    console.log('[CHATHANDLERS] загрузка завершена');
})();
