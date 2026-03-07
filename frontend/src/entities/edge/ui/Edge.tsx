import React from 'react';
import { GraphEdge } from '@/entities/workflow/store/types';

interface EdgeProps {
  edge: GraphEdge;
  fromPos: { x: number; y: number };
  toPos: { x: number; y: number };
}

export const Edge: React.FC<EdgeProps> = ({ edge, fromPos, toPos }) => {
  const x1 = fromPos.x + 140; // смещение под размеры узла
  const y1 = fromPos.y + 50;
  const x2 = toPos.x;
  const y2 = toPos.y + 50;
  const cp1x = x1 + (x2 - x1) * 0.5;

  return (
    <path
      d={`M ${x1} ${y1} C ${cp1x} ${y1}, ${cp1x} ${y2}, ${x2} ${y2}`}
      stroke="var(--bronze-base)"
      strokeWidth="1.5"
      fill="none"
      filter="url(#glow-line)"
      markerEnd="url(#arrowhead)"
      opacity="0.6"
    />
  );
};