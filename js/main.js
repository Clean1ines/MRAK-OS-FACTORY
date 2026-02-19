window.onload = async function() {
    console.log("Init sequence started");
    if (window.loadModels) await window.loadModels();
    if (window.loadProjects) await window.loadProjects();
    
    // Если проект уже выбран, грузим родителей
    if (state.getCurrentProjectId() && window.loadParents) {
        await window.loadParents();
    }
};
