import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import GlassCard from '../components/GlassCard';
import { 
  Users, 
  Settings as SettingsIcon, 
  ShieldCheck, 
  Activity, 
  Lock,
  Eye,
  UserPlus,
  ArrowRight,
  Database,
  Cpu
} from 'lucide-react';
import { motion } from 'framer-motion';

export default function Admin() {
  return (
    <div className="max-w-6xl mx-auto space-y-10 pb-32">
      <div className="border-b border-white/5 pb-8">
        <h2 className="text-3xl font-black text-title tracking-tight flex items-center gap-4">
           <ShieldCheck className="w-10 h-10 text-accent" />
           System Administration
        </h2>
        <p className="text-sm text-muted-text font-bold uppercase tracking-widest mt-2">Global Infrastructure Control Panel</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <GlassCard className="p-8 border-l-4 border-l-accent flex flex-col group">
           <div className="p-4 rounded-2xl bg-accent/10 text-accent w-fit mb-6 group-hover:scale-110 transition-transform">
             <Users className="w-8 h-8" />
           </div>
           <h3 className="text-xl font-black text-title mb-2">User Management</h3>
           <p className="text-xs text-muted-text font-medium leading-relaxed mb-8">
             Configure access levels, audit security logs, and manage operational workforce credentials.
           </p>
           <button className="mt-auto btn btn-secondary w-full group/btn">
             Access Portal
             <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
           </button>
        </GlassCard>

        <GlassCard className="p-8 border-l-4 border-l-purple-500 flex flex-col group">
           <div className="p-4 rounded-2xl bg-purple-500/10 text-purple-500 w-fit mb-6 group-hover:scale-110 transition-transform">
             <Database className="w-8 h-8" />
           </div>
           <h3 className="text-xl font-black text-title mb-2">System Diagnostics</h3>
           <p className="text-xs text-muted-text font-medium leading-relaxed mb-8">
             Monitor database health, API latency, and real-time AI processing throughput metrics.
           </p>
           <button className="mt-auto btn btn-secondary w-full group/btn">
             View Health
             <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
           </button>
        </GlassCard>

        <GlassCard className="p-8 border-l-4 border-l-warning flex flex-col group">
           <div className="p-4 rounded-2xl bg-warning/10 text-warning w-fit mb-6 group-hover:scale-110 transition-transform">
             <Cpu className="w-8 h-8" />
           </div>
           <h3 className="text-xl font-black text-title mb-2">AI Node Control</h3>
           <p className="text-xs text-muted-text font-medium leading-relaxed mb-8">
             Configure computer vision model parameters and manage edge detection node deployment.
           </p>
           <button className="mt-auto btn btn-secondary w-full group/btn">
             Configure Nodes
             <ArrowRight className="w-4 h-4 group-hover/btn:translate-x-1 transition-transform" />
           </button>
        </GlassCard>
      </div>

      <GlassCard className="p-10 border-white/10 bg-white/[0.03]">
        <div className="flex items-center gap-6 mb-10">
           <div className="p-5 rounded-3xl bg-secondary border border-white/10 shadow-2xl">
             <Activity className="w-10 h-10 text-accent" />
           </div>
           <div>
             <h3 className="text-2xl font-black text-title tracking-tight">Security Audit Logs</h3>
             <p className="text-xs text-muted-text font-bold uppercase tracking-widest mt-1">Real-Time Access Monitoring</p>
           </div>
        </div>

        <div className="space-y-4">
          {[
            { action: 'Admin Login', user: 'System Root', time: '2 mins ago', icon: Lock },
            { action: 'Config Updated', user: 'AI Specialist', time: '45 mins ago', icon: SettingsIcon },
            { action: 'New Node Registered', user: 'Edge_Node_04', time: '2 hours ago', icon: Cpu },
          ].map((log, i) => (
            <div key={i} className="flex items-center justify-between p-5 rounded-2xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.05] transition-all">
               <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center text-muted-text">
                    <log.icon className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-sm font-black text-title">{log.action}</p>
                    <p className="text-[10px] text-muted-text font-bold uppercase tracking-tighter">Initiated by {log.user}</p>
                  </div>
               </div>
               <div className="text-right">
                  <span className="text-[11px] font-black text-gray-500 uppercase tracking-widest">{log.time}</span>
               </div>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
}
