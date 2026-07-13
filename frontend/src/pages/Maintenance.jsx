import React, { useState, useEffect } from 'react';
import axios from 'axios';
import GlassCard from '../components/GlassCard';
import StatusBadge from '../components/StatusBadge';
import { 
  Wrench, 
  User, 
  MapPin, 
  ClipboardList,
  Search,
  MoreVertical,
  CheckCircle2,
  Clock,
  Briefcase,
  Layers,
  ArrowUpRight
} from 'lucide-react';
import { motion } from 'framer-motion';

export default function Maintenance() {
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchAssignments = async () => {
      try {
        const res = await axios.get('/api/assignments');
        setAssignments(res.data);
      } catch (err) {
        console.error("Failed to fetch assignments", err);
      } finally {
        setLoading(false);
      }
    };
    fetchAssignments();
    const interval = setInterval(fetchAssignments, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-8 pb-20">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-4 border-b border-white/5 pb-6">
        <div>
          <h2 className="text-2xl font-black text-title flex items-center gap-3">
             <Wrench className="w-8 h-8 text-accent" />
             Maintenance Hub
          </h2>
          <p className="text-xs text-muted-text font-bold uppercase tracking-widest mt-1">Workforce Allocation & Repair Pipeline</p>
        </div>
        <button className="btn btn-primary px-8">
          <Wrench className="w-4 h-4" />
          Deploy Crew
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          { label: 'Pending Repairs', value: assignments.filter(a => a.status === 'Pending').length, icon: Clock, color: 'text-warning', bg: 'bg-warning/10' },
          { label: 'Active Deployments', value: assignments.filter(a => a.status === 'In Progress').length, icon: Briefcase, color: 'text-accent', bg: 'bg-accent/10' },
          { label: 'Resolved Tasks', value: assignments.filter(a => a.status === 'Fixed').length, icon: CheckCircle2, color: 'text-success', bg: 'bg-success/10' },
        ].map(stat => (
          <GlassCard key={stat.label} className="p-6 flex items-center justify-between group overflow-hidden">
            <div>
              <p className="text-[11px] font-black uppercase text-muted-text tracking-widest mb-1">{stat.label}</p>
              <p className="text-3xl font-black text-title tracking-tight">{stat.value}</p>
            </div>
            <div className={`p-4 rounded-2xl ${stat.bg} ${stat.color} transition-transform group-hover:scale-110`}>
               <stat.icon className="w-7 h-7" />
            </div>
            <div className={`absolute -right-4 -bottom-4 w-20 h-20 rounded-full blur-[40px] opacity-10 ${stat.bg}`} />
          </GlassCard>
        ))}
      </div>

      <GlassCard className="p-0 overflow-hidden border-white/10 shadow-[0_20px_50px_rgba(0,0,0,0.4)]">
        <div className="p-8 border-b border-white/5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 bg-white/[0.02]">
          <h3 className="text-sm font-black uppercase tracking-[0.2em] text-title flex items-center gap-3">
            <Layers className="w-5 h-5 text-accent" />
            Operations Queue
          </h3>
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input 
              type="text" 
              placeholder="Search by worker or ID..." 
              className="w-full pl-11 pr-4 py-3 bg-white/5 border border-white/5 rounded-2xl text-sm font-medium outline-none focus:border-accent/40 transition-all placeholder:text-gray-600"
            />
          </div>
        </div>

        <div className="overflow-x-auto custom-scrollbar">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-white/[0.03] text-[10px] font-black uppercase tracking-[0.2em] text-muted-text">
                <th className="px-8 py-5">Task Identifier</th>
                <th className="px-8 py-5">Assigned Expert</th>
                <th className="px-8 py-5">System Status</th>
                <th className="px-8 py-5">Geospatial Data</th>
                <th className="px-8 py-5 text-right">Management</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {assignments.map((item, idx) => (
                <motion.tr 
                  key={item.id} 
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="hover:bg-white/[0.04] transition-colors group"
                >
                  <td className="px-8 py-6">
                    <div className="flex flex-col">
                      <span className="text-xs font-black text-title">HZ-ID: {item.pothole_id}</span>
                      <span className="text-[10px] text-muted-text font-bold uppercase mt-0.5 tracking-tighter">Queue Reference #{item.id}</span>
                    </div>
                  </td>
                  <td className="px-8 py-6">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-accent/10 flex items-center justify-center text-xs text-accent font-black border border-accent/20">
                        {item.worker_name[0]}
                      </div>
                      <div className="flex flex-col">
                        <span className="text-xs font-bold text-title">{item.worker_name}</span>
                        <span className="text-[10px] text-muted-text font-bold uppercase tracking-tighter">Maintenance Specialist</span>
                      </div>
                    </div>
                  </td>
                  <td className="px-8 py-6">
                    <StatusBadge status={item.status} className="px-3 py-1 font-black text-[9px] tracking-widest" />
                  </td>
                  <td className="px-8 py-6">
                    <div className="flex flex-col gap-1.5">
                      <div className="flex items-center gap-1.5 text-[10px] text-muted-text font-black uppercase tracking-tighter">
                        <MapPin className="w-3 h-3 text-accent" />
                        {item.latitude?.toFixed(5)}, {item.longitude?.toFixed(5)}
                      </div>
                      <div className="h-1 w-24 bg-white/5 rounded-full overflow-hidden">
                         <div className="h-full bg-accent/40 w-full animate-pulse" />
                      </div>
                    </div>
                  </td>
                  <td className="px-8 py-6 text-right">
                    <button className="p-3 bg-white/5 hover:bg-white/10 rounded-xl text-gray-500 hover:text-title transition-all border border-transparent hover:border-white/10">
                      <MoreVertical className="w-5 h-5" />
                    </button>
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {assignments.length === 0 && !loading && (
          <div className="py-32 text-center">
            <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6">
               <Layers className="w-10 h-10 text-gray-700" />
            </div>
            <h3 className="text-lg font-black text-gray-400 tracking-tight">Operation Queue Clear</h3>
            <p className="text-xs text-gray-600 mt-2 font-bold uppercase tracking-widest">No Active Repair Tasks</p>
          </div>
        )}
      </GlassCard>
    </div>
  );
}
