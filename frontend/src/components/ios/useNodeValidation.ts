// frontend/src/components/ios/useNodeValidation.ts
// ADDED: Hook for node validation logic (SRP extraction)

import { useCallback } from 'react';
import type { NodeData } from '../../hooks/useCanvasEngine';

export interface ValidationOptions {
  excludeCustomPrompt?: boolean;
}

export const useNodeValidation = (nodes: NodeData[]) => {
  const validateNodeUnique = useCallback((
    title: string, 
    prompt: string, 
    options: ValidationOptions = {}
  ): string | null => {
    const { excludeCustomPrompt = true } = options;
    
    const duplicateTitle = nodes.find(n => 
      n.prompt_key.toLowerCase() === title.toLowerCase() && 
      (excludeCustomPrompt ? n.prompt_key !== 'CUSTOM_PROMPT' : true)
    );
    
    if (duplicateTitle) {
      return `Node with name "${title}" already exists`;
    }

    const duplicateContent = nodes.find(n => 
      n.config?.custom_prompt === prompt
    );
    
    if (duplicateContent) {
      return `Node with identical prompt already exists`;
    }

    return null;
  }, [nodes]);

  return { validateNodeUnique };
};
