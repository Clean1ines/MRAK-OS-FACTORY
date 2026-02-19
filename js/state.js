// js/state.js - управление состоянием приложения
window.mrakState = {
    currentProjectId: null,
    artifacts: [],
    parentData: {}, // Мапа ID -> Type
    currentArtifact: null,
    artifactCache: {},

    getCurrentProjectId() { return this.currentProjectId; },
    setCurrentProjectId(id) { this.currentProjectId = id; },
    
    setArtifacts(list) { 
        this.artifacts = list; 
        this.parentData = {};
        list.forEach(a => { this.parentData[a.id] = a.type; });
    },
    
    getParentData() { return this.parentData; },
    
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
window.state = window.mrakState;
