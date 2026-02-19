// js/state.js - Глобальное состояние приложения
window.mrakState = {
    currentProjectId: null,
    projects: [],
    models: ["llama3-70b-8192"], // Дефолтная модель, чтобы не было 'loading...'
    artifacts: [],
    parentData: {},
    currentArtifact: null,
    artifactCache: {},

    setProjects(list) { this.projects = list; },
    getProjects() { return this.projects; },
    
    setModels(list) { 
        if (list && list.length > 0) this.models = list; 
    },
    getModels() { return this.models; },

    getCurrentProjectId() { return this.currentProjectId; },
    setCurrentProjectId(id) { this.currentProjectId = id; },
    
    setArtifacts(list) { 
        this.artifacts = list; 
        this.parentData = {};
        list.forEach(a => { this.parentData[a.id] = a.type; });
    },
    getParentData() { return this.parentData; },
    
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
window.state = window.mrakState;
