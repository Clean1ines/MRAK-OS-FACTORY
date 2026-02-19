window.state = {
    _pid: localStorage.getItem('selectedProjectId') || '',
    projects: [],
    models: ["llama-3.3-70b-versatile"],
    artifacts: [],
    parentData: {},

    setProjects(l) { this.projects = l; },
    
    setCurrentProjectId(id) { 
        this._pid = id; 
        localStorage.setItem('selectedProjectId', id);
    },
    
    getCurrentProjectId() { 
        // Если в переменной пусто, пробуем взять из селекта напрямую
        const s = document.getElementById('project-select');
        return this._pid || (s ? s.value : ''); 
    },

    setArtifacts(l) { 
        this.artifacts = l; 
        this.parentData = {};
        l.forEach(a => { this.parentData[a.id] = a.type; });
    },
    
    getArtifacts() { return this.artifacts; },
    getParentData() { return this.parentData; },
    getCurrentParentId() { return document.getElementById('parent-select')?.value; },
    
    getAllowedParentTypes(c) {
        const rules = {
            'BusinessRequirementPackage': ['ProductCouncilAnalysis'],
            'FunctionalRequirementPackage': ['BusinessRequirementPackage'],
            'SystemArchitecture': ['FunctionalRequirementPackage']
        };
        return rules[c] || ['ProductCouncilAnalysis']; // Возвращаем хоть что-то, чтобы список не был пустым
    },
    
    canGenerate(c, p) {
        return true; // Временно разрешаем всё, чтобы кнопка НЕ ИСЧЕЗАЛА
    }
};
