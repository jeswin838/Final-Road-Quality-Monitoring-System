import React, { useState, useMemo } from 'react';
import { useLiveData } from '../context/LiveDataContext';
import AlertToolbar from '../components/alerts/AlertToolbar';
import AlertList from '../components/alerts/AlertList';
import HazardDetailPanel from '../components/alerts/HazardDetailPanel';
import { useNavigate } from 'react-router-dom';
import { BellRing, ChevronLeft, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Alerts() {
  const { data, loading, forceRefresh } = useLiveData();
  const alerts = data.alerts || [];
  
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedHazardId, setSelectedHazardId] = useState(null);
  
  const navigate = useNavigate();

  // Sort logic: Emergency -> Critical -> High -> Medium -> Low
  // Tie-breakers: Priority Score -> Waiting Days -> Report Count -> Created Time
  const sortedAlerts = useMemo(() => {
    const priorityWeights = { 'Emergency': 5, 'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1 };
    
    return [...alerts].sort((a, b) => {
      const pA = priorityWeights[a.priority || 'Medium'] || 2;
      const pB = priorityWeights[b.priority || 'Medium'] || 2;
      
      if (pA !== pB) return pB - pA;
      
      const scoreA = a.priority_score || 0;
      const scoreB = b.priority_score || 0;
      if (scoreA !== scoreB) return scoreB - scoreA;
      
      const waitA = a.waiting_days || 0;
      const waitB = b.waiting_days || 0;
      if (waitA !== waitB) return waitB - waitA;
      
      const rA = a.report_count || 1;
      const rB = b.report_count || 1;
      if (rA !== rB) return rB - rA;
      
      const timeA = new Date(a.created_at).getTime() || 0;
      const timeB = new Date(b.created_at).getTime() || 0;
      return timeB - timeA;
    }).filter(a => {
       if (!searchTerm) return true;
       const term = searchTerm.toLowerCase();
       return (
          (a.road_name || '').toLowerCase().includes(term) ||
          (a.landmark || '').toLowerCase().includes(term) ||
          (a.village || '').toLowerCase().includes(term) ||
          (a.district || '').toLowerCase().includes(term)
       );
    });
  }, [alerts, searchTerm]);

  const selectedHazard = sortedAlerts.find(a => a.id === selectedHazardId) || null;

  const handleAssign = (hazard) => {
     navigate('/maintenance'); // For now redirect to maintenance, could open modal if existed
  };

  const handleTrack = (hazard) => {
     navigate('/maintenance');
  };

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] overflow-hidden p-2 md:p-6 pb-24 md:pb-6 relative">
      
      {/* Header section */}
      <div className="flex items-center gap-4 mb-4 shrink-0">
        <div className="w-12 h-12 rounded-xl bg-danger/15 flex items-center justify-center border border-danger/20 shadow-[0_0_20px_rgba(244,63,94,0.1)]">
          <BellRing className="w-6 h-6 text-danger" />
        </div>
        <div>
          <h2 className="text-2xl font-black text-white tracking-tight">Road Operations Center</h2>
          <p className="text-xs text-gray-400 font-bold uppercase tracking-widest mt-0.5">Live Alert Decision Board</p>
        </div>
      </div>

      <AlertToolbar 
         searchTerm={searchTerm} 
         setSearchTerm={setSearchTerm} 
         onRefresh={forceRefresh} 
      />

      {/* Main Responsive Layout */}
      {/*
        Mobile (< 768px): List is full width. When item selected, Detail is full screen over it.
        Tablet (768px - 1024px): List is full width. When item selected, Detail is Slide-over drawer on the right.
        Laptop (1024px - 1280px): List is 30% left, Detail is 70% right.
        Desktop (1280px+): List is 35% left, Detail is 65% right.
      */}
      <div className="flex-1 flex gap-6 min-h-0 relative">
        
        {/* Left Panel (List) - Hidden on Mobile if an item is selected */}
        <div className={`
           w-full 
           lg:w-[30%] 
           xl:w-[35%] 
           flex flex-col min-h-0 bg-black/20 border border-white/5 rounded-2xl p-4 overflow-y-auto custom-scrollbar 
           ${selectedHazardId ? 'hidden md:flex' : 'flex'}
        `}>
           <AlertList 
              alerts={sortedAlerts} 
              selectedId={selectedHazardId} 
              onSelect={(hazard) => setSelectedHazardId(hazard.id)} 
           />
        </div>

        {/* Desktop / Laptop Right Panel */}
        <div className="hidden lg:flex lg:w-[70%] xl:w-[65%] min-h-0 relative">
           <HazardDetailPanel 
              hazard={selectedHazard} 
              onAssign={handleAssign}
              onTrack={handleTrack}
           />
        </div>

        {/* Mobile Full Screen OR Tablet Drawer Overlay */}
        <AnimatePresence>
          {selectedHazardId && (
            <motion.div 
               initial={{ x: '100%' }}
               animate={{ x: 0 }}
               exit={{ x: '100%' }}
               transition={{ type: 'spring', damping: 25, stiffness: 200 }}
               className="absolute inset-0 z-50 lg:hidden flex justify-end"
            >
               {/* Clickaway backdrop for Tablet */}
               <div className="absolute inset-0 bg-black/40 backdrop-blur-sm hidden md:block" onClick={() => setSelectedHazardId(null)} />
               
               {/* Drawer / Full screen content */}
               <div className="w-full md:w-3/4 h-full relative z-10">
                  {/* Close button */}
                  <button 
                     onClick={() => setSelectedHazardId(null)}
                     className="absolute top-4 left-4 md:-left-12 z-50 bg-black/80 p-2 rounded-full border border-white/10 text-white shadow-lg hover:bg-white/10 transition-colors"
                  >
                     <X className="w-6 h-6" />
                  </button>
                  
                  <div className="w-full h-full">
                     <HazardDetailPanel 
                        hazard={selectedHazard} 
                        onAssign={handleAssign}
                        onTrack={handleTrack}
                     />
                  </div>
               </div>
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
}
