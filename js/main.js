// main.js - инициализация приложения

(function() {
    // Убедимся, что все модули загружены (api, state, ui, handlers, toolbar)
    // Загружаем начальные данные
    window.onload = async function() {
        await window.loadModels();
        await window.loadProjects();
        if (state.getCurrentProjectId()) await window.loadParents();
    };

    // Экспонируем глобальные функции, если их ещё нет
    // (они уже объявлены в handlers.js, но дублирование не повредит)
})();
