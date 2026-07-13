import React from 'react';
import { 
  X, 
  Clock, 
  MapPin, 
  ShieldAlert, 
  BarChart3, 
  Info, 
  Eye, 
  FileText,
  CameraOff,
  User,
  Cpu,
  Calendar
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import StatusBadge from './StatusBadge';

const SkeletonCard = () => (
  <div className="bg-white/5 border border-white/10 rounded-2xl p-4 flex flex-col md:flex-row gap-6 animate-pulse">
    <div className="w-full md:w-[220px] aspect-[16/9] bg-white/5 rounded-xl" />
    <div className="flex-1 space-y-4">
      <div className="flex justify-between items-center">
        <div className="h-4 w-24 bg-white/5 rounded" />
        <div className="h-4 w-32 bg-white/5 rounded" />
      </div>
      <div className="h-6 w-3/4 bg-white/5 rounded" />
      <div className="h-4 w-1/2 bg-white/5 rounded" />
      <div className="flex gap-2 pt-2">
        <div className="h-8 w-24 bg-white/5 rounded-lg" />
        <div className="h-8 w-24 bg-white/5 rounded-lg" />
      </div>
    </div>
  </div>
);

export default function ReportModal({ isOpen, onClose, reports, location, loading }) {
  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-background/80 backdrop-blur-md"
        />
        
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          className="relative w-full max-w-[1200px] bg-secondary/90 border border-white/10 backdrop-blur-2xl rounded-[2rem] shadow-[0_32px_64px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col max-h-[90vh]"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-8 border-b border-white/5">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-accent/10 flex items-center justify-center border border-accent/20">
                <ShieldAlert className="text-accent w-7 h-7" />
              </div>
              <div>
                <h3 className="text-2xl font-black text-white tracking-tight">Location Intelligence Reports</h3>
                <div className="flex items-center gap-4 mt-1">
                  <p className="text-xs text-gray-500 flex items-center gap-1.5 font-medium">
                    <MapPin className="w-3.5 h-3.5 text-accent" />
                    {location?.[0].toFixed(6)}, {location?.[1].toFixed(6)}
                  </p>
                  <div className="h-3 w-px bg-white/10" />
                  <p className="text-xs text-gray-500 font-medium">
                    {loading ? 'Analyzing...' : `${reports?.length || 0} Records Found`}
                  </p>
                </div>
              </div>
            </div>
            <button 
              onClick={onClose}
              className="p-3 hover:bg-white/5 rounded-2xl transition-all text-gray-400 hover:text-white border border-transparent hover:border-white/10 group"
            >
              <X className="w-6 h-6 group-hover:rotate-90 transition-transform duration-300" />
            </button>
          </div>

          {/* Content Area */}
          <div className="flex-1 overflow-y-auto p-8 custom-scrollbar">
            {loading ? (
              <div className="space-y-6">
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
              </div>
            ) : !reports || reports.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-32 text-center">
                <div className="w-24 h-24 rounded-3xl bg-white/5 flex items-center justify-center mb-6 border border-dashed border-white/10">
                  <Info className="w-10 h-10 text-gray-700" />
                </div>
                <h4 className="text-xl font-bold text-gray-300">No Historical Records Found</h4>
                <p className="text-sm text-gray-600 max-w-sm mt-3 leading-relaxed">
                  The AI system and citizen network have not yet documented specific evidence for this coordinate location.
                </p>
                <button 
                  onClick={onClose}
                  className="mt-8 btn btn-primary px-8 py-3"
                >
                  Return to Map
                </button>
              </div>
            ) : (
              <div className="space-y-6">
                {reports.map((report, idx) => (
                  <motion.div 
                    key={idx}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="group bg-white/[0.03] hover:bg-white/[0.06] border border-white/5 hover:border-accent/20 rounded-[1.5rem] overflow-hidden flex flex-col md:flex-row transition-all duration-300"
                  >
                    {/* Horizontal Thumbnail Side */}
                    <div className="w-full md:w-[213px] shrink-0 p-4">
                      <div className="relative aspect-[16/9] rounded-2xl overflow-hidden border border-white/10 group-hover:border-accent/30 transition-colors bg-black">
                        {report.image ? (
                           <img 
                            src={report.image} 
                            alt="Evidence" 
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" 
                          />
                        ) : (
                          <div className="w-full h-full flex flex-col items-center justify-center bg-white/5 text-gray-700">
                            <CameraOff className="w-10 h-10 mb-2 opacity-20" />
                            <span className="text-[10px] font-bold uppercase tracking-widest opacity-40">No Image Available</span>
                          </div>
                        )}
                        
                        <div className="absolute top-3 left-3">
                           <div className={`px-2 py-1 rounded-lg backdrop-blur-md border text-[10px] font-black uppercase tracking-tighter flex items-center gap-1.5 ${
                             report.source === 'ai' ? 'bg-accent/20 text-accent border-accent/30' : 'bg-purple-500/20 text-purple-400 border-purple-500/30'
                           }`}>
                             {report.source === 'ai' ? <Cpu className="w-3 h-3" /> : <User className="w-3 h-3" />}
                             {report.source} Verified
                           </div>
                        </div>

                        <div className="absolute bottom-3 right-3">
                          <StatusBadge status={report.status} />
                        </div>
                      </div>
                    </div>
                    
                    {/* Details Side */}
                    <div className="flex-1 p-6 flex flex-col min-w-0">
                      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
                        <div className="flex items-center gap-4">
                          <div className="flex flex-col">
                            <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Confidence</span>
                            <div className="flex items-center gap-2">
                              <span className="text-lg font-black text-white">{(report.confidence * 100).toFixed(0)}%</span>
                              <div className="w-24 h-1.5 bg-white/10 rounded-full overflow-hidden">
                                <motion.div 
                                  initial={{ width: 0 }}
                                  animate={{ width: `${report.confidence * 100}%` }}
                                  className={`h-full ${report.confidence > 0.7 ? 'bg-success' : report.confidence > 0.4 ? 'bg-warning' : 'bg-danger'}`}
                                />
                              </div>
                            </div>
                          </div>
                          
                          <div className="w-px h-10 bg-white/10 hidden sm:block" />

                          <div className="flex flex-col">
                            <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Severity</span>
                            <span className={`text-sm font-black uppercase tracking-tight ${
                              report.severity === 'high' ? 'text-danger' : 
                              report.severity === 'medium' ? 'text-warning' : 'text-success'
                            }`}>
                              {report.severity} Priority
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 border border-white/5 text-[11px] font-bold text-gray-400">
                          <Calendar className="w-3.5 h-3.5" />
                          {new Date(report.created_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </div>
                      
                      <div className="flex-1">
                        <p className="text-sm text-gray-300 leading-relaxed italic mb-4 line-clamp-2">
                          "{report.description || 'Hazard detected during autonomous road surface inspection. No manual description provided.'}"
                        </p>
                      </div>

                      <div className="mt-auto pt-6 border-t border-white/5 flex flex-wrap items-center justify-between gap-4">
                        <div className="flex items-center gap-3">
                           <span className="text-[10px] flex items-center gap-1.5 text-gray-500 font-bold uppercase tracking-tighter">
                             <MapPin className="w-3 h-3 text-accent" />
                             {report.latitude?.toFixed(5)}, {report.longitude?.toFixed(5)}
                           </span>
                        </div>

                        <div className="flex gap-2">
                          <button className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-bold text-gray-300 transition-all">
                            <FileText className="w-3.5 h-3.5" />
                            Details
                          </button>
                          <button 
                            onClick={() => window.open(report.image, '_blank')}
                            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-accent/10 hover:bg-accent/20 border border-accent/20 text-xs font-bold text-accent transition-all"
                          >
                            <Eye className="w-3.5 h-3.5" />
                            Full Image
                          </button>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
          
          {/* Footer */}
          <div className="px-8 py-4 border-t border-white/5 bg-black/40 flex items-center justify-between">
            <p className="text-[10px] font-bold text-gray-600 tracking-widest uppercase">
              Secure Intelligence Hub • Smart Road System v4.0
            </p>
            <div className="flex items-center gap-2">
               <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
               <span className="text-[10px] font-bold text-gray-500 uppercase">System Active</span>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
