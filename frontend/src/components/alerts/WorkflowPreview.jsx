import React from 'react';
import { Check, Clock, Play } from 'lucide-react';

const WORKFLOW_STAGES = [
  { id: 'Detected', label: 'Detected' },
  { id: 'Risk Assessed', label: 'Verified' },
  { id: 'Assigned', label: 'Assigned' },
  { id: 'Travelling', label: 'Travelling' },
  { id: 'Repair Started', label: 'Repairing' },
  { id: 'Verification Pending', label: 'Verification' },
  { id: 'Closed', label: 'Closed' }
];

export default function WorkflowPreview({ currentState }) {
  // Rough mapping from actual hazard maintenance_state to our visual pipeline
  // If state is not found, we highlight Detected by default or find index.
  const stateMap = {
    'Detected': 'Detected',
    'Risk Assessed': 'Risk Assessed',
    'Priority Assigned': 'Risk Assessed',
    'Assignment Recommended': 'Risk Assessed',
    'Pending Assignment': 'Risk Assessed',
    'Assigned': 'Assigned',
    'Worker Accepted': 'Assigned',
    'Travelling': 'Travelling',
    'Arrived': 'Travelling',
    'Inspection Started': 'Repair Started',
    'Repair Started': 'Repair Started',
    'Repair Completed': 'Verification Pending',
    'Verification Pending': 'Verification Pending',
    'Repair Verified': 'Closed',
    'Closed': 'Closed'
  };

  const mappedState = stateMap[currentState] || 'Detected';
  const currentIndex = WORKFLOW_STAGES.findIndex(s => s.id === mappedState);
  const activeIndex = currentIndex === -1 ? 0 : currentIndex;

  return (
    <div className="py-4">
      <div className="flex items-center justify-between relative">
        <div className="absolute left-0 right-0 top-1/2 -translate-y-1/2 h-0.5 bg-white/10 z-0" />
        
        {WORKFLOW_STAGES.map((stage, idx) => {
          const isCompleted = idx < activeIndex;
          const isActive = idx === activeIndex;
          const isPending = idx > activeIndex;
          
          return (
            <div key={stage.id} className="relative z-10 flex flex-col items-center gap-2">
              <div className={`
                w-6 h-6 rounded-full flex items-center justify-center text-[10px] border-2 transition-colors
                ${isCompleted ? 'bg-green-500 border-green-500 text-white' : ''}
                ${isActive ? 'bg-blue-500 border-blue-400 text-white animate-pulse shadow-[0_0_15px_rgba(59,130,246,0.5)]' : ''}
                ${isPending ? 'bg-black border-white/20 text-gray-500' : ''}
              `}>
                {isCompleted && <Check className="w-3 h-3" />}
                {isActive && <Play className="w-3 h-3 ml-0.5" />}
                {isPending && <Clock className="w-3 h-3" />}
              </div>
              <span className={`text-[9px] font-bold uppercase tracking-wider whitespace-nowrap absolute -bottom-5
                ${isActive ? 'text-blue-400' : 'text-gray-500'}
              `}>
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
