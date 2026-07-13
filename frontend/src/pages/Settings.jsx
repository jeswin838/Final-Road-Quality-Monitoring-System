import React, { useState } from 'react';
import GlassCard from '../components/GlassCard';
import { 
  Settings as SettingsIcon, 
  Cpu, 
  Bell, 
  Shield, 
  Database, 
  Smartphone,
  CheckCircle2,
  Save,
  RefreshCw,
  Sliders
} from 'lucide-react';
import { motion } from 'framer-motion';

export default function Settings() {
  const [sensitivity, setSensitivity] = useState(0.08);

  return (
    <div className="max-w-4xl mx-auto space-y-10 pb-32">
      <div className="border-b border-white/5 pb-8 flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-black text-title tracking-tight flex items-center gap-4">
             <SettingsIcon className="w-10 h-10 text-accent" />
             System Configuration
          </h2>
          <p className="text-sm text-muted-text font-bold uppercase tracking-widest mt-2">Fine-tune AI and operational parameters</p>
        </div>
        <button className="btn btn-primary px-8 shadow-[0_10px_30px_rgba(56,189,248,0.3)]">
           <Save className="w-4 h-4" />
           Apply Changes
        </button>
      </div>

      <div className="grid grid-cols-1 gap-8">
        <GlassCard className="p-10 border-white/10 bg-white/[0.03]">
           <div className="flex items-center gap-4 mb-10">
              <div className="p-4 rounded-2xl bg-accent/10 text-accent border border-accent/20">
                <Cpu className="w-7 h-7" />
              </div>
              <div>
                <h3 className="text-xl font-black text-title tracking-tight uppercase">AI Inference Engine</h3>
                <p className="text-xs text-muted-text font-bold uppercase tracking-widest mt-1">Computer Vision Sensitivity Tuning</p>
              </div>
           </div>

           <div className="space-y-10">
              <div className="space-y-6">
                <div className="flex justify-between items-end">
                   <div className="space-y-1">
                      <p className="text-sm font-black text-title uppercase tracking-widest flex items-center gap-2">
                        <Sliders className="w-4 h-4 text-accent" />
                        Confidence Threshold
                      </p>
                      <p className="text-xs text-muted-text font-medium">Minimum probability score for hazard validation.</p>
                   </div>
                   <span className="text-2xl font-black text-accent tracking-tighter">{(sensitivity * 100).toFixed(0)}%</span>
                </div>
                <input 
                  type="range" 
                  min="0.01" 
                  max="0.5" 
                  step="0.01" 
                  value={sensitivity}
                  onChange={(e) => setSensitivity(parseFloat(e.target.value))}
                  className="w-full h-2 bg-white/10 rounded-full appearance-none cursor-pointer accent-accent"
                />
                <div className="flex justify-between text-[10px] font-black text-gray-600 uppercase tracking-widest">
                   <span>High Sensitivity (0.01)</span>
                   <span>Balanced</span>
                   <span>Strict (0.50)</span>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-6 border-t border-white/5">
                 <div className="flex items-center justify-between p-4 rounded-2xl bg-white/[0.02] border border-white/5">
                    <div className="flex items-center gap-3">
                       <Smartphone className="w-5 h-5 text-gray-500" />
                       <span className="text-sm font-bold text-title">Edge Device Sync</span>
                    </div>
                    <div className="w-12 h-6 bg-accent/20 rounded-full p-1 relative cursor-pointer border border-accent/30">
                       <div className="w-4 h-4 bg-accent rounded-full absolute right-1" />
                    </div>
                 </div>
                 <div className="flex items-center justify-between p-4 rounded-2xl bg-white/[0.02] border border-white/5">
                    <div className="flex items-center gap-3">
                       <Bell className="w-5 h-5 text-gray-500" />
                       <span className="text-sm font-bold text-title">Auto-Alert System</span>
                    </div>
                    <div className="w-12 h-6 bg-accent/20 rounded-full p-1 relative cursor-pointer border border-accent/30">
                       <div className="w-4 h-4 bg-accent rounded-full absolute right-1" />
                    </div>
                 </div>
              </div>
           </div>
        </GlassCard>

        <GlassCard className="p-10 border-white/10 bg-white/[0.03]">
           <div className="flex items-center gap-4 mb-8">
              <div className="p-4 rounded-2xl bg-purple-500/10 text-purple-500 border border-purple-500/20">
                <Database className="w-7 h-7" />
              </div>
              <div>
                <h3 className="text-xl font-black text-title tracking-tight uppercase">Storage & Retention</h3>
                <p className="text-xs text-muted-text font-bold uppercase tracking-widest mt-1">Evidence Data Management</p>
              </div>
           </div>
           
           <div className="flex items-center justify-between p-6 rounded-2xl bg-white/[0.02] border border-white/5 group hover:border-accent/30 transition-all">
              <div className="flex items-center gap-4">
                 <div className="p-3 rounded-xl bg-white/5">
                    <RefreshCw className="w-5 h-5 text-gray-500" />
                 </div>
                 <div>
                    <p className="text-sm font-black text-title uppercase tracking-widest">Wipe Cache Files</p>
                    <p className="text-xs text-muted-text font-medium mt-1">Delete locally stored inference frames older than 48h.</p>
                 </div>
              </div>
              <button className="btn btn-secondary text-[10px] px-6">PURGE NOW</button>
           </div>
        </GlassCard>
      </div>
    </div>
  );
}
