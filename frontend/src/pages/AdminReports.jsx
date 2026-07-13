import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useLiveData } from '../context/LiveDataContext';
import GlassCard from '../components/GlassCard';
import StatusBadge from '../components/StatusBadge';
import { 
  ClipboardList, 
  CheckCircle, 
  XCircle, 
  Eye, 
  MapPin, 
  Calendar,
  AlertCircle,
  Clock,
  User,
  CameraOff
} from 'lucide-react';
import { motion } from 'framer-motion';

export default function AdminReports() {
  const { data, loading: contextLoading } = useLiveData();
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (data.pending) {
      setReports(data.pending);
      setLoading(false);
    }
  }, [data.pending]);

  const handleAction = async (id, action) => {
    try {
      await axios.post('/api/pothole/action', { id, action });
      setReports(reports.filter(r => r.id !== id));
    } catch (err) {
      console.error("Action failed", err);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-8 pb-32">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6 pb-8 border-b border-white/5">
        <div>
          <h2 className="text-2xl font-black text-title tracking-tight flex items-center gap-3">
             <ClipboardList className="w-8 h-8 text-accent" />
             AI Detection Verification Queue
          </h2>
          <p className="text-sm text-muted-text font-bold uppercase tracking-widest mt-1">Pending AI Hazard Validations</p>
        </div>
        <div className="flex items-center gap-3">
           <div className="px-6 py-2.5 rounded-2xl bg-warning/10 border border-warning/20 text-warning text-xs font-black tracking-[0.2em]">
             {reports.length} PENDING VALIDATION
           </div>
        </div>
      </div>

      {loading ? (
        <div className="space-y-6">
          {[1, 2, 3].map(i => <div key={i} className="h-40 bg-white/5 rounded-[24px] animate-pulse border border-white/5" />)}
        </div>
      ) : (
        <div className="space-y-6">
          {reports.length === 0 ? (
            <div className="text-center py-40 bg-white/[0.02] rounded-[32px] border-2 border-dashed border-white/10">
              <div className="w-24 h-24 bg-success/10 rounded-full flex items-center justify-center mx-auto mb-8 border border-success/20">
                <CheckCircle className="w-12 h-12 text-success/50" />
              </div>
              <h3 className="text-xl font-black text-title tracking-tight uppercase">Queue Fully Processed</h3>
              <p className="text-xs text-muted-text mt-2 font-bold uppercase tracking-widest">No Active Reports Requiring Manual Review</p>
            </div>
          ) : (
            reports.map((report, idx) => (
              <motion.div
                key={report.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
              >
                <GlassCard className="p-0 overflow-hidden group hover:bg-white/[0.07] transition-all border-white/10 hover:border-accent/30 shadow-[0_20px_50px_rgba(0,0,0,0.3)]">
                  <div className="flex flex-col md:flex-row items-stretch">
                    {/* Thumbnail Side */}
                    <div className="w-full md:w-[280px] shrink-0 p-5">
                      <div className="relative aspect-[16/9] md:aspect-[4/3] rounded-2xl overflow-hidden border-2 border-white/10 bg-black shadow-inner">
                        {report.image_url ? (
                          <img src={report.image_url} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-700" alt="AI Detection" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center bg-white/5">
                            <CameraOff className="w-10 h-10 text-gray-700 opacity-20" />
                          </div>
                        )}
                        <div className="absolute top-4 left-4">
                          <StatusBadge status="pending" className="font-black text-[9px] tracking-widest px-3" />
                        </div>
                      </div>
                    </div>

                    {/* Intelligence Side */}
                    <div className="flex-1 p-8 flex flex-col min-w-0">
                      <div className="flex flex-wrap items-center justify-between gap-6 mb-6">
                         <div className="flex items-center gap-8">
                            <div className="flex flex-col">
                               <span className="text-[10px] font-black text-muted-text uppercase tracking-widest mb-1">Detection ID</span>
                               <div className="flex items-center gap-2.5">
                                  <div className="w-7 h-7 rounded-full bg-accent/20 flex items-center justify-center text-[10px] font-black text-accent border border-accent/30">
                                    {report.id.toString().slice(-1)}
                                  </div>
                                  <span className="text-sm font-black text-title">AI_{report.id}</span>
                               </div>
                            </div>
                            <div className="w-px h-10 bg-white/10" />
                            <div className="flex flex-col">
                               <span className="text-[10px] font-black text-muted-text uppercase tracking-widest mb-1">Geospatial Data</span>
                               <span className="text-xs font-bold text-muted-text flex items-center gap-1.5 group-hover:text-accent transition-colors">
                                 <MapPin className="w-4 h-4 text-accent" />
                                 {report.latitude.toFixed(6)}, {report.longitude.toFixed(6)}
                               </span>
                            </div>
                         </div>
                         <div className="px-4 py-2 rounded-xl bg-white/5 border border-white/5 text-[10px] font-black text-muted-text uppercase tracking-widest flex items-center gap-2.5">
                            <Calendar className="w-4 h-4 text-accent" />
                            {new Date(report.created_at).toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' })}
                         </div>
                      </div>

                      <div className="flex-1 bg-white/[0.02] p-4 rounded-xl border border-white/5 mb-6 flex gap-8">
                        <div>
                          <span className="text-[9px] font-black text-muted-text uppercase tracking-widest block mb-1">Severity</span>
                          <p className="text-sm font-bold text-white capitalize">
                            {report.severity || 'Unknown'}
                          </p>
                        </div>
                        <div>
                          <span className="text-[9px] font-black text-muted-text uppercase tracking-widest block mb-1">Confidence</span>
                          <p className="text-sm font-bold text-accent">
                            {report.confidence ? (report.confidence * 100).toFixed(1) + '%' : 'N/A'}
                          </p>
                        </div>
                      </div>

                      <div className="mt-auto pt-6 border-t border-white/5 flex items-center justify-end gap-4">
                         <button 
                          onClick={() => handleAction(report.id, 'reject')}
                          className="btn btn-secondary px-8 py-3 text-[11px] font-black tracking-widest hover:border-danger/40 hover:text-danger"
                        >
                          <XCircle className="w-4 h-4" />
                          REJECT
                        </button>
                        <button 
                          onClick={() => handleAction(report.id, 'approve')}
                          className="btn btn-primary px-10 py-3 text-[11px] font-black tracking-widest shadow-[0_10px_30px_rgba(56,189,248,0.3)]"
                        >
                          <CheckCircle className="w-4 h-4" />
                          VALIDATE
                        </button>
                      </div>
                    </div>
                  </div>
                </GlassCard>
              </motion.div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
