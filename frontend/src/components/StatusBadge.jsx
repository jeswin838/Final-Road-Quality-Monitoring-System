import React from 'react';
import { cn } from './GlassCard';

export default function StatusBadge({ status, className }) {
  const s = (status || 'pending').toLowerCase();
  
  const styles = {
    pending: 'bg-warning/10 text-warning border-warning/20',
    approved: 'bg-success/10 text-success border-success/20',
    rejected: 'bg-danger/10 text-danger border-danger/20',
    fixed: 'bg-accent/10 text-accent border-accent/20',
    'in progress': 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  };

  return (
    <span className={cn(
      "px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border",
      styles[s] || styles.pending,
      className
    )}>
      {status}
    </span>
  );
}
