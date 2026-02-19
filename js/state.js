// js/state.js - Глобальное состояние приложения
window.mrakState = {
    currentProjectId: null,
    projects: [],
    models: [],
    artifacts: [],
    parentData: {}, // Мапа ID -> Type
    currentArtifact: null,
    artifactCache: {},

    // Проекты
    setProjects(list) { this.projects = list; },
    getProjects() { return this.projects; },
    
    // Модели
    setModels(list) { this.models = list; },
    getModels() { return this.models; },

    // Текущий проект
    getCurrentProjectId() { return this.currentProjectId; },
    setCurrentProjectId(id) { this.currentProjectId = id; },
    
    // Артефакты и родители
    setArtifacts(list) { 
        this.artifacts = list; 
        this.parentData = {};
        list.forEach(a => { this.parentData[a.id] = a.type; });
    },
    getArtifacts() { return this.artifacts; },
    getParentData() { return this.parentData; },
    
    // Метод, который просил projectHandlers.js
    getCurrentParentId() {
        const select = document.getElementById('parent-select');
        return select ? select.value : null;
    },
    
    setCurrentArtifact(a) { this.currentArtifact = a; },
    getCurrentArtifact() { return this.currentArtifact; },

    setArtifactCache(parentId, type, data) {
        const key = `${parentId}_${type}`;
        this.artifactCache[key] = data;
    },
    getArtifactCache(parentId, type) {
        return this.artifactCache[`${parentId}_${type}`];
    },

    // ПРАВИЛА: Что можно генерировать
    canGenerate(childType, parentType) {
        const rules = {
            'BusinessRequirementPackage': ['ProductCouncilAnalysis'],
            'FunctionalRequirementPackage': ['BusinessRequirementPackage'],
            'CodePackage': ['FunctionalRequirementPackage', 'SystemArchitecture']
        };
        return rules[childType] ? rules[childType].includes(parentType) : false;
    },

    getAllowedParentTypes(childType) {
        const rules = {
            'BusinessRequirementPackage': ['ProductCouncilAnalysis'],
            'FunctionalRequirementPackage': ['BusinessRequirementPackage'],
            'CodePackage': ['FunctionalRequirementPackage', 'SystemArchitecture']
        };
        return rules[childType] || [];
    }
};

// Экспортируем для глобального доступа
window.state = window.mrakState;
