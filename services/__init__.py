# ADDED: Service initializer
import os
from dotenv import load_dotenv
from groq_client import GroqClient
from prompt_loader import PromptLoader
from prompt_service import PromptService
from artifact_service import ArtifactService
from workflow_engine import WorkflowEngine
from services.llm_stream_service import LLMStreamService

load_dotenv()

# Global configuration maps
MODE_MAP = {
    "01_CORE": "SYSTEM_PROMPT_URL",
    "02_IDEA_CLARIFIER": "GH_URL_IDEA_CLARIFIER",
    "03_PRODUCT_COUNCIL": "GH_URL_PRODUCT_COUNCIL",
    "04_BUSINESS_REQ_GEN": "GH_URL_BUSINESS_REQ_GEN",
    "05_REQ_ENG_COUNCIL": "GH_URL_REQ_ENG_COUNCIL",
    "06_SYSTEM_REQ_GEN": "GH_URL_SYSTEM_REQ_GEN",
    "07_QA_COUNCIL": "GH_URL_QA_COUNCIL",
    "08_ARCHITECTURE_COUNCIL": "GH_URL_ARCHITECTURE_COUNCIL",
    "09_CODE_TASK_GEN": "GH_URL_CODE_TASK_GEN",
    "10_CODE_GEN": "GH_URL_CODE_GEN",
    "11_TEST_GEN": "GH_URL_TEST_GEN",
    "12_FAILURE_DETECTOR": "GH_URL_FAILURE_DETECTOR",
    "13_SELF_ANALYSIS_FACTORY": "GH_URL_SELF_ANALYSIS_FACTORY",
    "14_PROMPT_ENGINEERING_COUNCIL": "GH_URL_PROMPT_ENGINEERING_COUNCIL",
    "15_ALGORITHM_COUNCIL": "GH_URL_ALGORITHM_COUNCIL",
    "16_UI_UX_COUNCIL": "GH_URL_UI_UX_COUNCIL",
    "17_SOFT_ENG_COUNCIL": "GH_URL_SOFT_ENG_COUNCIL",
    "18_TRANSLATOR": "GH_URL_TRANSLATOR",
    "19_INTEGRATION_PLAN": "GH_URL_INTEGRATION_PLAN",
    "20_SECURITY_REQ_GEN": "GH_URL_SECURITY_REQ_GEN",
    "21_THREAT_MODELING_ASSISTANT": "GH_URL_THREAT_MODELING_ASSISTANT",
    "22_INFRASTRUCTURE_SPEC_GEN": "GH_URL_INFRASTRUCTURE_SPEC_GEN",
    "23_OBSERVABILITY_SPEC_GEN": "GH_URL_OBSERVABILITY_SPEC_GEN",
    "24_TECH_DESIGN_DOC_GEN": "GH_URL_TECH_DESIGN_DOC_GEN",
    "25_USER_DOC_GEN": "GH_URL_USER_DOC_GEN",
    "26_API_DOC_GEN": "GH_URL_API_DOC_GEN",
    "27_UAT_SCRIPT_GEN": "GH_URL_UAT_SCRIPT_GEN",
    "28_JIRA_ISSUE_FORMATTER": "GH_URL_JIRA_ISSUE_FORMATTER",
    "29_PROJECT_STATUS_REPORTER": "GH_URL_PROJECT_STATUS_REPORTER",
    "30_INCIDENT_POST_MORTEM_GEN": "GH_URL_INCIDENT_POST_MORTEM_GEN",
    "31_KNOWLEDGE_QUERY_ASSISTANT": "GH_URL_KNOWLEDGE_QUERY_ASSISTANT",
    "32_CHANGE_IMPACT_ANALYZER": "GH_URL_CHANGE_IMPACT_ANALYZER",
    "33_FEATURE_TO_USER_STORY_GEN": "GH_URL_FEATURE_TO_USER_STORY_GEN",
    "34_RESEARCH_METODOLOGY_GEN": "GH_URL_RESEARCH_METODOLOGY_GEN",
    "35_ANALYSIS_SUMMARIZER": "GH_URL_ANALYSIS_SUMMARIZER",
    "36_REQUIREMENT_SUMMARIZER": "GH_URL_REQUIREMENT_SUMMARIZER",
    "37_SYSTEM_REQUIREMENTS_SUMMARIZER": "GH_URL_SYSTEM_REQUIREMENTS_SUMMARIZER",
    "38_CODE_CONTEXT_SUMMARIZER": "GH_URL_CODE_CONTEXT_SUMMARIZER",
    "02sum_STATE_SYNTHESIZER": "GH_URL_STATE_SYNTHESIZER",
}

TYPE_TO_MODE = {
    "BusinessIdea": "02_IDEA_CLARIFIER",
    "ProductCouncilAnalysis": "03_PRODUCT_COUNCIL",
    "BusinessRequirementPackage": "04_BUSINESS_REQ_GEN",
    "ReqEngineeringAnalysis": "05_REQ_ENG_COUNCIL",
    "FunctionalRequirementPackage": "06_SYSTEM_REQ_GEN",
    "QAAnalysis": "07_QA_COUNCIL",
    "ArchitectureAnalysis": "08_ARCHITECTURE_COUNCIL",
    "AtomicTask": "09_CODE_TASK_GEN",
    "CodeArtifact": "10_CODE_GEN",
    "TestPackage": "11_TEST_GEN",
    "FailureReport": "12_FAILURE_DETECTOR",
    "SelfAnalysis": "13_SELF_ANALYSIS_FACTORY",
    "PromptEngineeringAnalysis": "14_PROMPT_ENGINEERING_COUNCIL",
    "AlgorithmAnalysis": "15_ALGORITHM_COUNCIL",
    "UIUXAnalysis": "16_UI_UX_COUNCIL",
    "SoftEngAnalysis": "17_SOFT_ENG_COUNCIL",
    "TranslationArtifact": "18_TRANSLATOR",
    "IntegrationPlan": "19_INTEGRATION_PLAN",
    "SecurityRequirements": "20_SECURITY_REQ_GEN",
    "ThreatModel": "21_THREAT_MODELING_ASSISTANT",
    "InfrastructureSpec": "22_INFRASTRUCTURE_SPEC_GEN",
    "ObservabilitySpec": "23_OBSERVABILITY_SPEC_GEN",
    "TechDesignDoc": "24_TECH_DESIGN_DOC_GEN",
    "UserDoc": "25_USER_DOC_GEN",
    "APISpec": "26_API_DOC_GEN",
    "UATScript": "27_UAT_SCRIPT_GEN",
    "JIRAIssues": "28_JIRA_ISSUE_FORMATTER",
    "StatusReport": "29_PROJECT_STATUS_REPORTER",
    "IncidentReport": "30_INCIDENT_POST_MORTEM_GEN",
    "KnowledgeQuery": "31_KNOWLEDGE_QUERY_ASSISTANT",
    "ImpactReport": "32_CHANGE_IMPACT_ANALYZER",
    "UserStories": "33_FEATURE_TO_USER_STORY_GEN",
    "ResearchMethodology": "34_RESEARCH_METODOLOGY_GEN",
}

# Initialize clients and services
gh_token = os.getenv("GITHUB_TOKEN")
groq_client = GroqClient()
prompt_loader = PromptLoader(gh_token)
prompt_service = PromptService(groq_client, prompt_loader, MODE_MAP)
artifact_service = ArtifactService(groq_client, prompt_loader, MODE_MAP, TYPE_TO_MODE)
workflow_engine = WorkflowEngine(artifact_service)
llm_stream_service = LLMStreamService(groq_client, prompt_loader)
