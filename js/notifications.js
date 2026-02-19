// notifications.js - уведомления

function showNotification(message, type = 'info') {
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '1000';
        document.body.appendChild(container);
    }
    const notification = document.createElement('div');
    notification.innerText = message;
    notification.style.background = type === 'error' ? '#f56565' : '#48bb78';
    notification.style.color = 'white';
    notification.style.padding = '10px 20px';
    notification.style.marginBottom = '10px';
    notification.style.borderRadius = '5px';
    notification.style.boxShadow = '0 2px 5px rgba(0,0,0,0.2)';
    container.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

window.notifications = { showNotification };
