// frontend/src/components/ios/WorkspacePage.tsx
import React, { useState, useEffect } from 'react';
import type { NodeData, EdgeData } from '../../hooks/useCanvasEngine';
import { IOSShell } from './IOSShell';
import { IOSCanvas } from './IOSCanvas';
import { client } from '../../api/client';
import { api } from '../../api/client';
import { validateWorkflowAcyclic } from '../../utils/graphUtils';
import { WorkflowHeader } from './WorkflowHeader';
import { NodeListPanel } from './NodeListPanel';
import { NodeModal } from './NodeModal';
import { useNodeValidation } from './useNodeValidation';

interface Workflow { id: string; name: string; description?: string; is_default?: boolean; created_at?: string; }
interface Project { id: string; name: string; description?: string; }

export const WorkspacePage: React.FC = () => {
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [edges, setEdges] = useState<EdgeData[]>([]);
  const [workflowName, setWorkflowName] = useState('');
  const [currentWorkflowId, setCurrentWorkflowId] = useState<string | null>(null);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  const [showNodeModal, setShowNodeModal] = useState(false);
  const [showNodeList, setShowNodeList] = useState(false);
  const [newNodePrompt, setNewNodePrompt] = useState('');
  const [newNodeTitle, setNewNodeTitle] = useState('');
  const { validateNodeUnique } = useNodeValidation(nodes);

  useEffect(() => { const s = localStorage.getItem('workspace_selected_project'); if (s) setSelectedProjectId(s); loadProjects(); }, []);
  useEffect(() => { if (selectedProjectId) { localStorage.setItem('workspace_selected_project', selectedProjectId); loadWorkflows(); } }, [selectedProjectId]);
  useEffect(() => { if (currentWorkflowId) loadWorkflows(); }, [currentWorkflowId]);

  const loadProjects = async () => { try { const r = await client.GET('/api/projects'); if (r.error) throw new Error(r.error.error||'Failed'); setProjects((r.data||[]).map((p:any)=>({id:p.id!,name:p.name!,description:p.description||''}))); if((r.data||[]).length>0&&!localStorage.getItem('workspace_selected_project')) setSelectedProjectId((r.data as Project[])[0].id); } catch(e:any){console.error(e);alert('Ошибка: '+e.message);} };
  const loadWorkflows = async () => { if(!selectedProjectId)return; try{const r=await client.GET('/api/workflows');if(r.error)throw new Error(r.error.error||'Failed');setWorkflows((r.data||[]).map((w:any)=>({id:w.id!,name:w.name!,description:w.description||'',is_default:w.is_default||false,created_at:w.created_at})));}catch(e:any){console.error(e);alert('Ошибка: '+e.message);} };
  const loadWorkflow = async (id:string)=>{try{const r=await client.GET('/api/workflows/{workflow_id}',{params:{path:{workflow_id:id}}});if(r.error)throw new Error(r.error.error||'Failed');const d:any=r.data;setNodes((d?.nodes||[]).map((n:any)=>({id:n.node_id||crypto.randomUUID(),node_id:n.node_id,prompt_key:n.prompt_key||'UNKNOWN',position_x:n.position_x||100,position_y:n.position_y||100,config:n.config||{}})));setEdges((d?.edges||[]).map((e:any)=>({id:e.id||crypto.randomUUID(),source_node:e.source_node,target_node:e.target_node})));setCurrentWorkflowId(id);setWorkflowName(d?.workflow?.name||'');}catch(e:any){console.error(e);alert('Ошибка: '+e.message);}};

  const handleSave = async () => { if(!workflowName.trim()||!selectedProjectId){alert('⚠️ Fill required fields');return;} if(!validateWorkflowAcyclic(nodes,edges).valid){alert('⚠️ Cycle detected - remove circular connections');return;} setLoading(true); try{const url=currentWorkflowId?`/api/workflows/${currentWorkflowId}`:'/api/workflows';const res=await fetch(url,{method:currentWorkflowId?'PUT':'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:workflowName,description:'Created in workspace editor',project_id:selectedProjectId,nodes:nodes.map(n=>({node_id:n.node_id,prompt_key:n.prompt_key,position_x:n.position_x,position_y:n.position_y,config:n.config})),edges:edges.map(e=>({source_node:e.source_node,target_node:e.target_node}))})});if(!res.ok)throw new Error((await res.json()).detail||`HTTP ${res.status}`);if(!currentWorkflowId)await loadWorkflows();alert(`✅ Workflow ${currentWorkflowId?'updated':'saved'}!`);}catch(e:any){console.error(e);alert('❌ '+e.message);}finally{setLoading(false);}};

  const handleDelete = async () => { if(!currentWorkflowId||!confirm(`Delete "${workflowName}"?`))return; try{await client.DELETE('/api/workflows/{workflow_id}',{params:{path:{workflow_id:currentWorkflowId}}});setNodes([]);setEdges([]);setCurrentWorkflowId(null);setWorkflowName('New Workflow');await loadWorkflows();alert('✅ Deleted');}catch(e:any){alert('❌ '+e.message);} };

  const handleAddCustomNode = (x:number,y:number)=>{setNewNodeTitle('');setNewNodePrompt('');setShowNodeModal(true);(window as any)._newNodePosition={x,y};};
  const confirmAddCustomNode = async () => { if(!newNodePrompt.trim()){alert('Enter prompt');return;} const title=newNodeTitle.trim()||'CUSTOM_PROMPT';const err=validateNodeUnique(title,newNodePrompt);if(err){alert(`⚠️ ${err}`);return;} const pos=(window as any)._newNodePosition;if(pos){setNodes(prev=>[...prev,{id:crypto.randomUUID(),node_id:crypto.randomUUID(),prompt_key:title,position_x:pos.x,position_y:pos.y,config:{custom_prompt:newNodePrompt}}]);} setShowNodeModal(false);setNewNodePrompt('');setNewNodeTitle('');};
  const addNodeFromList = (node:NodeData)=>{setNodes(prev=>[...prev,node]);setShowNodeList(false);};

  return (<IOSShell><div className="flex h-full">{sidebarOpen&&(<aside className="w-64 bg-[var(--ios-glass)] backdrop-blur-md border-r border-[var(--ios-border)] flex flex-col z-50"><div className="p-3 border-b border-[var(--ios-border)]"><label className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider block mb-1">Project</label><select value={selectedProjectId||''} onChange={(e)=>setSelectedProjectId(e.target.value||null)} className="w-full bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded px-2 py-1.5 text-xs text-[var(--text-main)] outline-none focus:border-[var(--bronze-base)]"><option value="">-- Select Project --</option>{projects.map(p=><option key={p.id}value={p.id}>{p.name}</option>)}</select></div><div className="h-12 flex items-center justify-between px-4 border-b border-[var(--ios-border)]"><span className="text-xs font-bold text-[var(--bronze-base)] uppercase tracking-wider">Workflows</span><button onClick={()=>setSidebarOpen(false)} className="text-[var(--text-muted)] hover:text-[var(--text-main)]"><svg className="w-4 h-4"viewBox="0 0 24 24"fill="none"stroke="currentColor"strokeWidth="2"><line x1="18"y1="6"x2="6"y2="18"/><line x1="6"y1="6"x2="18"y2="18"/></svg></button></div><div className="p-3 border-b border-[var(--ios-border)]"><button onClick={()=>{setNodes([]);setEdges([]);setCurrentWorkflowId(null);setWorkflowName('New Workflow');setShowNodeModal(true);}} disabled={!selectedProjectId} className="w-full px-3 py-2 text-xs font-semibold rounded bg-[var(--bronze-dim)] text-[var(--bronze-bright)] hover:bg-[var(--bronze-base)] hover:text-black transition-colors flex items-center justify-center gap-2 disabled:opacity-30"><svg className="w-3 h-3"viewBox="0 0 24 24"fill="none"stroke="currentColor"strokeWidth="2"><line x1="12"y1="5"x2="12"y2="19"/><line x1="5"y1="12"x2="19"y2="12"/></svg>New Workflow</button></div><div className="flex-1 overflow-y-auto p-2">{!selectedProjectId?<div className="text-[10px] text-[var(--accent-warning)] text-center py-4">⚠️ Select project</div>:workflows.length===0?<div className="text-[10px] text-[var(--text-muted)] text-center py-4">No workflows</div>:workflows.map(wf=><button key={wf.id} onClick={()=>loadWorkflow(wf.id)} className={`w-full text-left px-3 py-2 rounded mb-1 text-xs ${currentWorkflowId===wf.id?'bg-[var(--bronze-dim)] text-[var(--bronze-bright)]':'text-[var(--text-secondary)] hover:bg-[var(--ios-glass-bright)]'}`}><div className="font-semibold truncate">{wf.name}</div><div className="text-[9px] opacity-60 truncate">{wf.description||'No description'}</div></button>)}</div><div className="p-3 border-t border-[var(--ios-border)] text-[9px] text-[var(--text-muted)] text-center">{workflows.length} workflow{workflows.length!==1?'s':''}</div></aside>)}<div className="flex-1 flex flex-col"><WorkflowHeader sidebarOpen={sidebarOpen} onToggleSidebar={()=>setSidebarOpen(true)} workflowName={workflowName} onWorkflowNameChange={setWorkflowName} currentWorkflowId={currentWorkflowId} loading={loading} showNodeList={showNodeList} onToggleNodeList={()=>setShowNodeList(!showNodeList)} onDelete={handleDelete} onSave={handleSave} onLogout={async()=>{try{await api.auth.logout();window.location.href='/login';}catch(e){console.error(e);}}} canSave={!!selectedProjectId&&!!workflowName.trim()&&!loading}/><IOSCanvas nodes={nodes} edges={edges} onNodesChange={setNodes} onEdgesChange={setEdges} onAddCustomNode={handleAddCustomNode}/><NodeListPanel visible={showNodeList} onClose={()=>setShowNodeList(false)} nodes={nodes} onAddNode={addNodeFromList}/><NodeModal visible={showNodeModal} onClose={()=>setShowNodeModal(false)} title={newNodeTitle} onTitleChange={setNewNodeTitle} prompt={newNodePrompt} onPromptChange={setNewNodePrompt} onConfirm={confirmAddCustomNode} validationError={newNodeTitle.trim()?validateNodeUnique(newNodeTitle.trim(),newNodePrompt):null}/></div></div></IOSShell>);
};
