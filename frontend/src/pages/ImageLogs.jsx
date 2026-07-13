import React, { useState, useEffect } from 'react';
import axios from 'axios';
import GlassCard from '../components/GlassCard';
import StatusBadge from '../components/StatusBadge';
import { 
  Filter, 
  Search, 
  Maximize2, 
  Calendar,
  Layers,
  MapPin,
  Cpu,
  BarChart3,
  CameraOff,
  Clock,
  ArrowUpRight
} from 'lucide-react';
import { motion } from 'framer-motion';

export default function ImageLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await axios.get('/api/potholes?limit=40');
        setLogs(res.data);
      } catch (err) {
        console.error("Failed to fetch logs", err);
      } finally {
        setLoading(false);
      }
    };
    fetchLogs();
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-32">
      <div className="flex items-center justify-between border-b border-white/5 pb-6">
        <div>
           <h2 className="text-2xl font-black text-title flex items-center gap-3">
             <Layers className="w-8 h-8 text-accent" />
             Hazard Intelligence Logs
           </h2>
           <p className="text-sm text-muted-text font-bold uppercase tracking-widest mt-1">Universal Detection Registry</p>
        </div>
      </div>

      <GlassCard className="p-5 flex flex-col md:flex-row gap-6 items-center justify-between border-white/10 bg-white/[0.04] shadow-[0_20px_50px_rgba(0,0,0,0.3)]">
        <div className="flex items-center gap-4 w-full md:w-auto">
          <div className="relative flex-1 md:w-96">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input 
              type="text" 
              placeholder="Search by location, ID or analysis status..." 
              className="w-full pl-12 pr-4 py-3.5 bg-white/5 border border-white/5 rounded-2xl text-sm font-bold text-title focus:border-accent/50 outline-none transition-all placeholder:text-gray-600"
            />
          </div>
          <button className="p-3 rounded-2xl bg-white/5 border border-white/10 text-muted-text hover:text-title hover:bg-white/10 transition-all">
            <Filter className="w-5 h-5" />
          </button>
        </div>

        <div className="flex gap-4 w-full md:w-auto items-center">
          <div className="flex gap-2">
            <select className="px-6 py-3 text-[10px] font-black uppercase tracking-widest">
              <option className="bg-slate-900">All Types</option>
              <option className="bg-slate-900">Pothole</option>
              <option className="bg-slate-900">Crack</option>
            </select>
          </div>
          <div className="h-10 w-px bg-white/10 hidden md:block" />
          <div className="flex items-center gap-2.5 px-5 py-3 rounded-2xl bg-accent/15 border border-accent/20 text-accent text-[11px] font-black uppercase tracking-widest">
            <Activity className="w-4 h-4" />
            {logs.length} RECORDS
          </div>
        </div>
      </GlassCard>

      {loading ? (
        <div className="space-y-6">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-40 rounded-[24px] bg-white/5 animate-pulse border border-white/5" />
          ))}
        </div>
      ) : (
        <div className="space-y-6">
          {logs.map((log, idx) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0, x: -30 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.04 }}
            >
              <GlassCard className="p-0 overflow-hidden group hover:bg-white/[0.07] transition-all border-white/10 hover:border-accent/30 shadow-[0_20px_40px_rgba(0,0,0,0.3)]">
                <div className="flex flex-col md:flex-row items-stretch">
                  {/* Visual Analytics Side */}
                  <div className="w-full md:w-[260px] shrink-0 p-5">
                    <div className="relative aspect-[16/10] rounded-2xl overflow-hidden border-2 border-white/10 bg-black group-hover:border-accent/40 transition-colors">
                      {log.image_url ? (
                        <img 
                          src={log.image_url} 
                          className="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-110" 
                          alt="Detection Evidence" 
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center bg-white/5">
                          <CameraOff className="w-10 h-10 text-gray-700 opacity-20" />
                        </div>
                      )}
                      <div className="absolute top-3 left-3">
                        <StatusBadge status={log.status} className="font-black text-[9px] tracking-widest px-3" />
                      </div>
                    </div>
                  </div>

                  {/* Metadata Payload Side */}
                  <div className="flex-1 p-7 flex flex-col min-w-0">
                    <div className="flex flex-wrap items-center justify-between gap-6 mb-6">
                      <div className="flex items-center gap-8">
                        <div className="flex flex-col">
                          <span className="text-[10px] font-black text-muted-text uppercase tracking-widest mb-1">LOG ID</span>
                          <span className="text-base font-black text-title tracking-tight">#{log.id.toString().padStart(5, '0')}</span>
                        </div>
                        
                        <div className="w-px h-10 bg-white/10" />

                        <div className="flex flex-col">
                          <span className="text-[10px] font-black text-muted-text uppercase tracking-widest mb-1">Priority</span>
                          <span className={`text-sm font-black uppercase tracking-tight ${
                            log.severity === 'high' ? 'text-danger' : 
                            log.severity === 'medium' ? 'text-warning' : 'text-success'
                          }`}>
                            {log.severity} SEVERITY
                          </span>
                        </div>

                        <div className="w-px h-10 bg-white/10 hidden sm:block" />

                        <div className="hidden sm:flex flex-col">
                          <span className="text-[10px] font-black text-muted-text uppercase tracking-widest mb-1">Confidence</span>
                          <div className="flex items-center gap-3">
                            <span className="text-sm font-black text-title">{((log.confidence || 0.8) * 100).toFixed(0)}%</span>
                            <div className="w-20 h-1.5 bg-white/5 rounded-full overflow-hidden border border-white/5">
                              <div className="h-full bg-accent shadow-[0_0_10px_#38BDF8]" style={{ width: `${(log.confidence || 0.8) * 100}%` }} />
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2.5 px-4 py-2 rounded-xl bg-white/5 border border-white/5 text-[11px] font-black text-muted-text uppercase tracking-widest">
                        <Clock className="w-4 h-4 text-accent" />
                        {new Date(log.created_at).toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' })}
                      </div>
                    </div>

                    <div className="mt-auto pt-6 border-t border-white/5 flex flex-wrap items-center justify-between gap-6">
                      <div className="flex items-center gap-8">
                        <span className="text-[11px] flex items-center gap-2 text-muted-text font-black uppercase tracking-tighter hover:text-accent transition-colors">
                          <MapPin className="w-4 h-4 text-accent" />
                          {log.latitude.toFixed(6)}, {log.longitude.toFixed(6)}
                        </span>
                        <div className="flex items-center gap-2.5">
                           <div className="w-5 h-5 rounded-lg bg-accent/10 flex items-center justify-center border border-accent/20">
                             <Cpu className="w-3 h-3 text-accent" />
                           </div>
                           <span className="text-[10px] font-black text-muted-text uppercase tracking-widest">{log.source || 'AI'} VERIFIED</span>
                        </div>
                      </div>

                      <button className="btn btn-secondary px-6 py-2.5 text-[10px] font-black tracking-widest group/btn">
                        <Maximize2 className="w-4 h-4 group-hover/btn:scale-110 transition-transform" />
                        FULL ANALYSIS
                      </button>
                    </div>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
