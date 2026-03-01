import React, { useState, useEffect } from 'react';
import { BaseModal } from '../common/BaseModal';

interface EditNodeModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialPromptKey: string;
  initialConfig: Record<string, unknown>;
  onSave: (promptKey: string, config: Record<string, unknown>) => Promise<void>;
  isSaving?: boolean;
}

export const EditNodeModal: React.FC<EditNodeModalProps> = ({
  isOpen,
  onClose,
  initialPromptKey,
  initialConfig,
  onSave,
  isSaving = false,
}) => {
  const [promptKey, setPromptKey] = useState(initialPromptKey);
  const [configText, setConfigText] = useState(JSON.stringify(initialConfig, null, 2));
  const [error, setError] = useState('');

  useEffect(() => {
    if (isOpen) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setPromptKey(initialPromptKey);
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setConfigText(JSON.stringify(initialConfig, null, 2));
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setError('');
    }
  }, [isOpen, initialPromptKey, initialConfig]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!promptKey.trim()) {
      setError('Prompt key is required');
      return;
    }
    try {
      const config = JSON.parse(configText);
      await onSave(promptKey.trim(), config);
      onClose();
    } catch (err) {
      setError('Invalid JSON: ' + (err instanceof Error ? err.message : String(err)));
    }
  };

  return (
    <BaseModal isOpen={isOpen} onClose={onClose} title="Edit Node">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">
            Prompt Key *
          </label>
          <input
            type="text"
            value={promptKey}
            onChange={(e) => setPromptKey(e.target.value)}
            className="w-full bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded px-3 py-2 text-sm text-[var(--text-main)] outline-none focus:border-[var(--bronze-base)]"
            disabled={isSaving}
            autoFocus
          />
        </div>
        <div>
          <label className="block text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">
            Config (JSON)
          </label>
          <textarea
            value={configText}
            onChange={(e) => setConfigText(e.target.value)}
            rows={8}
            className="w-full bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] rounded px-3 py-2 text-sm text-[var(--text-main)] outline-none focus:border-[var(--bronze-base)] font-mono resize-vertical"
            disabled={isSaving}
          />
        </div>
        {error && <p className="text-[var(--accent-danger)] text-xs">{error}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 text-xs font-semibold rounded bg-[var(--ios-glass-dark)] border border-[var(--ios-border)] text-[var(--text-main)] hover:bg-[var(--ios-glass-bright)] transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSaving}
            className="px-3 py-1.5 text-xs font-semibold rounded bg-[var(--bronze-base)] text-black hover:bg-[var(--bronze-bright)] transition-colors disabled:opacity-30"
          >
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </form>
    </BaseModal>
  );
};
