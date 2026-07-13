import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useLiveData } from '../context/LiveDataContext';
import GlassCard from '../components/GlassCard';
import StatusBadge from '../components/StatusBadge';
import { 
  AlertTriangle, 
  ShieldAlert, 
  BellRing, 
  Clock, 
  MapPin, 
  ChevronRight,
  Filter,
  Activity,
  Zap,
  ArrowUpRight,
  CameraOff
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Alerts() {
  const { data, loading: contextLoading } = useLiveData();
  const alerts = data.alerts || [];
  const loading = contextLoading && alerts.length === 0;

  return (
    <div className="max-w-5xl mx-auto space-y-8 pb-32">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 border-b border-white/5 pb-8">
        <div className="flex items-center gap-5">
          <div className="w-16 h-16 rounded-[24px] bg-danger/15 flex items-center justify-center border-2 border-danger/20 relative shadow-[0_0_30px_rgba(244,63,94,0.2)]">
            <BellRing className="w-8 h-8 text-danger animate-bounce" />
            <div className="absolute -top-1 -right-1 w-5 h-5 bg-danger rounded-full border-4 border-background flex items-center justify-center text-[8px] font-black text-white">!</div>
          </div>
          <div>
            <h2 className="text-2xl font-black text-title tracking-tight">Active High-Priority Alerts</h2>
            <div className="flex items-center gap-3 mt-1">
              <p className="text-xs text-muted-text font-bold uppercase tracking-widest">Real-Time Threat Intelligence</p>
              <div className="h-3 w-px bg-white/10" />
              <div className="flex items-center gap-1.5">
                 <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                 <span className="text-[10px] font-black text-success uppercase">System Live</span>
              </div>
            </div>
          </div>
        </div>
        <div className="flex gap-3 w-full sm:w-auto">
          <button className="flex-1 sm:flex-none btn btn-secondary px-6">
            <Filter className="w-4 h-4" />
            Priority
          </button>
          <button className="flex-1 sm:flex-none btn btn-secondary px-6">
            <Zap className="w-4 h-4" />
            History
          </button>
        </div>
      </div>

      {loading ? (
        <div className="space-y-6">
          {[1, 2, 3].map(i => <div key={i} className="h-32 bg-white/5 rounded-[24px] animate-pulse border border-white/5" />)}
        </div>
      ) : (
        <div className="space-y-6">
          <AnimatePresence>
          {alerts.length === 0 ? (
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center py-40 bg-white/[0.02] rounded-[32px] border-2 border-dashed border-white/10"
            >
              <ShieldAlert className="w-16 h-16 text-gray-700 mx-auto mb-6" />
              <h3 className="text-xl font-black text-gray-400 tracking-tight uppercase">Operations Normal</h3>
              <p className="text-xs text-gray-600 mt-2 font-bold uppercase tracking-widest">No Critical Hazards in Current Sector</p>
            </motion.div>
          ) : (
            alerts.map((alert, idx) => (
              <motion.div
                key={alert.id}
                initial={{ opacity: 0, x: -30 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 30 }}
                transition={{ delay: idx * 0.1, type: 'spring', damping: 20 }}
              >
                <GlassCard className="p-0 overflow-hidden border-l-[8px] border-l-danger hover:bg-white/[0.07] transition-all cursor-pointer group shadow-[0_20px_40px_rgba(0,0,0,0.3)]">
                  <div className="flex flex-col md:flex-row items-stretch">
                    {/* Visual Preview */}
                    <div className="w-full md:w-[240px] shrink-0 p-5">
                      <div className="relative aspect-[16/10] rounded-2xl overflow-hidden border-2 border-white/10 group-hover:border-danger/40 transition-colors bg-black shadow-inner">
                        {alert.image ? (
                          <img src={alert.image} className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110" alt="Alert" />
                        ) : (
                          <div className="w-full h-full flex flex-col items-center justify-center text-gray-700 bg-white/5">
                            <CameraOff className="w-10 h-10 mb-2 opacity-20" />
                            <span className="text-[10px] font-black uppercase tracking-widest opacity-40">No Signal</span>
                          </div>
                        )}
                        <div className="absolute top-3 left-3">
                           <StatusBadge status="approved" className="bg-danger/20 text-danger border-danger/30 font-black text-[9px] px-3" />
                        </div>
                      </div>
                    </div>
                    
                    {/* Intelligence Payload */}
                    <div className="flex-1 p-6 flex flex-col min-w-0">
                      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
                        <div className="flex items-center gap-6">
                           <div className="flex flex-col">
                             <span className="text-[10px] font-black text-muted-text uppercase tracking-widest mb-1">Threat Class</span>
                             <h4 className="text-base font-black text-title truncate tracking-tight uppercase">Critical Road Surface Failure</h4>
                           </div>
                           <div className="w-px h-10 bg-white/10 hidden sm:block" />
                           <div className="flex flex-col">
                             <span className="text-[10px] font-black text-muted-text uppercase tracking-widest mb-1">Impact Radius</span>
                             <span className="text-sm font-black text-danger uppercase tracking-tight">HIGH PRIORITY</span>
                           </div>
                        </div>
                        
                        <div className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/5 text-[11px] font-black text-muted-text uppercase tracking-widest">
                          <Clock className="w-4 h-4 text-accent" />
                          {alert.last_seen}
                        </div>
                      </div>

                      <div className="mt-auto pt-5 border-t border-white/5 flex flex-wrap items-center justify-between gap-6">
                        <div className="flex items-center gap-6">
                          <span className="text-[11px] flex items-center gap-2 text-muted-text font-black uppercase tracking-tighter hover:text-accent transition-colors">
                            <MapPin className="w-4 h-4 text-accent" />
                            {alert.latitude.toFixed(6)}, {alert.longitude.toFixed(6)}
                          </span>
                          <div className="flex items-center gap-3">
                             <span className="text-[11px] font-black text-muted-text uppercase">Risk Score</span>
                             <div className="w-24 h-2 bg-white/5 rounded-full overflow-hidden border border-white/5">
                               <motion.div 
                                 initial={{ width: 0 }}
                                 animate={{ width: '92%' }}
                                 className="h-full bg-danger shadow-[0_0_10px_#F43F5E]" 
                               />
                             </div>
                             <span className="text-[11px] font-black text-danger">92%</span>
                          </div>
                        </div>

                        <button className="flex items-center gap-3 px-6 py-2.5 rounded-2xl bg-white/5 hover:bg-accent/10 border border-white/10 hover:border-accent/30 text-xs font-black text-muted-text hover:text-accent transition-all group/btn uppercase tracking-widest">
                          Analyze
                          <ChevronRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
                        </button>
                      </div>
                    </div>
                  </div>
                </GlassCard>
              </motion.div>
            ))
          )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
