import React from 'react';
import type { Priority } from '../types';

interface PriorityBadgeProps {
  priority: Priority;
}

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({ priority }) => {
  return (
    <span className={`badge badge-priority-${priority}`}>
      {priority}
    </span>
  );
};
