import React from 'react';
import { ShieldAlert, AlertTriangle, Clock, Activity, ArrowRight, UserCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const priorityColors = {
  Emergency: "bg-red-500/20 text-red-400 border-red-500/30",
  Critical: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  High: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  Medium: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  Low: "bg-gray-500/20 text-gray-400 border-gray-500/30"
};

const priorityIcons = {
  Emergency: <ShieldAlert className="w-3 h-3" />,
  Critical: <AlertTriangle className="w-3 h-3" />,
  High: <AlertTriangle className="w-3 h-3" />,
  Medium: <Activity className="w-3 h-3" />,
  Low: <Clock className="w-3 h-3" />
};

export default function AlertList({ alerts, selectedId, onSelect }) {
  if (alerts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 border border-dashed border-white/10 rounded-2xl bg-white/[0.02]">
        <ShieldAlert className="w-12 h-12 text-gray-600 mb-3" />
        <h3 className="text-gray-400 font-bold uppercase tracking-wider text-sm">No Active Alerts</h3>
        <p className="text-xs text-gray-500 mt-1">All hazards handled in this view.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <AnimatePresence>
        {alerts.map((alert, idx) => {
          const isSelected = selectedId === alert.id;
          const priority = alert.priority || "Medium";
          const colorClass = priorityColors[priority] || priorityColors.Medium;
          const icon = priorityIcons[priority] || priorityIcons.Medium;
          
          return (
            <motion.div
              key={alert.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ delay: idx * 0.03 }}
              onClick={() => onSelect(alert)}
              className={`
                group relative overflow-hidden rounded-xl border p-3 cursor-pointer transition-all duration-200
                ${isSelected 
                  ? 'bg-white/10 border-white/30 shadow-lg' 
                  : 'bg-black/40 border-white/5 hover:bg-white/[0.08] hover:border-white/20'
                }
              `}
              style={{ maxHeight: '120px' }}
            >
              {isSelected && (
                <div className="absolute left-0 top-0 bottom-0 w-1 bg-blue-500" />
              )}
              
              <div className="flex justify-between items-start mb-2">
                 <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wider ${colorClass}`}>
                    {icon}
                    {priority}
                 </div>
                 <div className="flex items-center gap-2 text-[10px] font-bold text-gray-500">
                    <span>Risk {alert.risk_score || 0}</span>
                 </div>
              </div>

              <div className="mb-1 truncate pr-6">
                <h4 className="text-sm font-bold text-gray-200 truncate">{alert.road_name || alert.formatted_address || "Unknown Road"}</h4>
                <p className="text-xs text-gray-500 truncate">{alert.landmark || alert.village || "Unknown Location"}</p>
              </div>

              <div className="flex items-center gap-3 text-[10px] font-medium text-gray-400 mt-2">
                <span className="flex items-center gap-1"><Activity className="w-3 h-3 text-indigo-400" /> {alert.report_count || 1} Reports</span>
                <span className="flex items-center gap-1"><Clock className="w-3 h-3 text-orange-400" /> Wait: {alert.waiting_days || 0}d</span>
                <span className="flex items-center gap-1 ml-auto">
                   <UserCircle className="w-3 h-3 text-green-400" />
                   {alert.assigned_worker_name || "Not Assigned"}
                </span>
              </div>
              
              <ArrowRight className={`absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white transition-opacity ${isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-30'}`} />
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
