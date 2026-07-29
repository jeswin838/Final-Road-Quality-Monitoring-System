import React from 'react';
import { ShieldAlert, AlertTriangle, Activity, Clock, MapPin, UserCircle, Wrench, FileText, CheckCircle2, Navigation, AlertCircle, CameraOff, TrendingUp, Shield, BarChart3, Truck, Hash } from 'lucide-react';
import WorkflowPreview from './WorkflowPreview';

export default function HazardDetailPanel({ hazard, onAssign, onTrack }) {
  if (!hazard) {
    return (
      <div className="h-full w-full flex flex-col items-center justify-center text-center p-8 bg-black/20 rounded-2xl border border-white/5">
        <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mb-4">
          <ShieldAlert className="w-8 h-8 text-gray-500" />
        </div>
        <h3 className="text-xl font-black text-gray-300 tracking-tight">No Hazard Selected</h3>
        <p className="text-sm text-gray-500 mt-2 max-w-sm">Select an alert from the list to view complete operational details, reasoning, and workflow status.</p>
      </div>
    );
  }

  // Backend reason mapping
  const reasons = hazard.reason_bundle?.reasons || [];
  const hasReasons = reasons.length > 0;
  
  // Backend recommendation mapping
  const recTeam = hazard.reason_bundle?.recommended_team || "No recommendation available";
  const recAction = hazard.reason_bundle?.recommended_action || "Awaiting assessment";
  const recEquip = (hazard.reason_bundle?.recommended_equipment || []).join(', ') || "N/A";
  const recTime = hazard.response_time || "N/A";
  const recVehicle = hazard.reason_bundle?.recommended_vehicle || "N/A";
  
  // Priority color
  const priorityColor = hazard.priority === 'Emergency' ? 'text-red-400 border-red-500/30 bg-red-500/10' :
                        hazard.priority === 'Critical' ? 'text-orange-400 border-orange-500/30 bg-orange-500/10' :
                        hazard.priority === 'High' ? 'text-amber-400 border-amber-500/30 bg-amber-500/10' :
                        'text-blue-400 border-blue-500/30 bg-blue-500/10';

  const mapLink = hazard.google_maps_url || `https://www.google.com/maps/search/?api=1&query=${hazard.latitude},${hazard.longitude}`;

  // Safe defaults
  const roadClass = hazard.road_class || "Unknown";
  const roadImportance = hazard.road_importance !== undefined ? `${hazard.road_importance} / 100` : "Unknown";
  const trafficImportance = hazard.traffic_importance || hazard.traffic_level || "Unknown";

  const pb = hazard.priority_breakdown || {};
  const rb = hazard.risk_breakdown || {};

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a]/80 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden relative shadow-2xl">
      {/* Background glow based on priority */}
      <div className={`absolute top-0 right-0 w-96 h-96 rounded-full blur-[120px] opacity-[0.15] pointer-events-none ${hazard.priority === 'Emergency' ? 'bg-red-500' : 'bg-blue-500'}`} />
      
      <div className="overflow-y-auto p-4 md:p-8 space-y-10 flex-1 custom-scrollbar z-10">
        
        {/* SECTION 1: Image & Location */}
        <div className="flex flex-col xl:flex-row gap-6">
          <div className="w-full xl:w-1/3 aspect-[16/10] xl:aspect-square bg-black/80 rounded-2xl overflow-hidden border border-white/10 relative shrink-0 shadow-lg group">
            {hazard.image_url ? (
               <img src={hazard.image_url} alt="Hazard" className="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" />
            ) : (
               <div className="w-full h-full flex flex-col items-center justify-center text-gray-600 bg-white/[0.02]">
                  <CameraOff className="w-12 h-12 mb-3 opacity-30" />
                  <span className="text-xs font-black uppercase tracking-widest text-gray-500">Placeholder Image</span>
               </div>
            )}
          </div>
          <div className="flex-1 flex flex-col justify-center">
            <h2 className="text-3xl md:text-4xl font-black text-white tracking-tight mb-3 leading-tight">
               {hazard.road_name || hazard.formatted_address || "Unknown Location"}
            </h2>
            <div className="flex flex-col gap-2 text-gray-400 mb-6 text-sm font-medium">
               <div className="flex items-center gap-2"><MapPin className="w-4 h-4 text-indigo-400 shrink-0" /> {hazard.landmark ? `${hazard.landmark}` : 'Unknown Landmark'}</div>
               <div className="flex items-center gap-2"><MapPin className="w-4 h-4 text-indigo-400 shrink-0 opacity-0" /> {hazard.village || "Unknown Village"}, {hazard.district || "Unknown District"}</div>
               <div className="flex items-center gap-2"><MapPin className="w-4 h-4 text-indigo-400 shrink-0 opacity-0" /> {hazard.formatted_address || "Unknown Address"}</div>
            </div>
            <a href={mapLink} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white text-xs font-bold uppercase tracking-wider px-5 py-3 rounded-xl transition-colors w-max">
               <Navigation className="w-4 h-4" /> Open in Google Maps
            </a>
          </div>
        </div>

        {/* SECTION 2: Hazard Summary */}
        <div>
          <h3 className="text-xs font-black text-gray-500 uppercase tracking-widest mb-4 border-b border-white/5 pb-2 flex items-center gap-2">
             <Activity className="w-4 h-4" /> Hazard Summary
          </h3>
          <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
            <div className={`p-4 rounded-xl border flex flex-col justify-center items-center text-center ${priorityColor}`}>
               <span className="text-[10px] font-bold uppercase tracking-widest mb-1 opacity-80">Priority</span>
               <span className="text-lg font-black">{hazard.priority || "Medium"}</span>
            </div>
            <div className="p-4 rounded-xl border border-white/10 bg-white/5 flex flex-col justify-center items-center text-center text-white">
               <span className="text-[10px] font-bold uppercase tracking-widest mb-1 text-gray-500">Risk Score</span>
               <span className="text-lg font-black text-indigo-400">{hazard.risk_score || 0}</span>
            </div>
            <div className="p-4 rounded-xl border border-white/10 bg-white/5 flex flex-col justify-center items-center text-center text-white">
               <span className="text-[10px] font-bold uppercase tracking-widest mb-1 text-gray-500">Waiting</span>
               <span className="text-lg font-black text-orange-400">{hazard.waiting_days || 0} Days</span>
            </div>
            <div className="p-4 rounded-xl border border-white/10 bg-white/5 flex flex-col justify-center items-center text-center text-white">
               <span className="text-[10px] font-bold uppercase tracking-widest mb-1 text-gray-500">Reports</span>
               <span className="text-lg font-black text-blue-400">{hazard.report_count || 1}</span>
            </div>
            <div className="p-4 rounded-xl border border-white/10 bg-white/5 flex flex-col justify-center items-center text-center text-white">
               <span className="text-[10px] font-bold uppercase tracking-widest mb-1 text-gray-500">Severity</span>
               <span className="text-lg font-black text-red-400">{hazard.severity || "Unknown"}</span>
            </div>
            <div className="p-4 rounded-xl border border-white/10 bg-white/5 flex flex-col justify-center items-center text-center text-white">
               <span className="text-[10px] font-bold uppercase tracking-widest mb-1 text-gray-500">Status</span>
               <span className="text-sm font-bold text-green-400 truncate w-full px-1">{hazard.maintenance_state || "Detected"}</span>
            </div>
          </div>
        </div>

        {/* Breakdown Row */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
           
           {/* SECTION 3: Priority Breakdown ("Calculated From") */}
           <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
              <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2"><BarChart3 className="w-4 h-4" /> Calculated Priority From</h3>
              <ul className="space-y-3">
                 <li className="flex justify-between items-center text-sm"><span className="text-gray-500">Risk Score</span> <span className="font-bold text-white">{pb.risk || hazard.risk_score || 0}</span></li>
                 <li className="flex justify-between items-center text-sm"><span className="text-gray-500">Road Importance</span> <span className="font-bold text-white">{pb.road || hazard.road_importance || 0}</span></li>
                 <li className="flex justify-between items-center text-sm"><span className="text-gray-500">Traffic Importance</span> <span className="font-bold text-white">{trafficImportance}</span></li>
                 <li className="flex justify-between items-center text-sm"><span className="text-gray-500">Waiting Time</span> <span className="font-bold text-white">{pb.waiting || hazard.waiting_days || 0} Days</span></li>
                 <li className="flex justify-between items-center text-sm"><span className="text-gray-500">Reports</span> <span className="font-bold text-white">{pb.reports || hazard.report_count || 1}</span></li>
                 {hazard.requires_emergency_team && (
                    <li className="flex justify-between items-center text-sm mt-4 pt-4 border-t border-white/10">
                       <span className="text-red-400 font-bold flex items-center gap-2"><ShieldAlert className="w-4 h-4" /> Emergency Required</span>
                       <CheckCircle2 className="w-4 h-4 text-red-400" />
                    </li>
                 )}
              </ul>
           </div>

           {/* SECTION 4: Risk Breakdown */}
           <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
              <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2"><TrendingUp className="w-4 h-4" /> Risk Score Breakdown</h3>
              <ul className="space-y-3">
                 <li className="flex justify-between items-center text-sm"><span className="text-gray-500">Severity</span> <span className="font-bold text-white">{rb.severity || 0}</span></li>
                 <li className="flex justify-between items-center text-sm"><span className="text-gray-500">Confidence</span> <span className="font-bold text-white">{rb.confidence || 0}</span></li>
                 <li className="flex justify-between items-center text-sm"><span className="text-gray-500">Reports</span> <span className="font-bold text-white">{rb.reports || 0}</span></li>
                 <li className="flex justify-between items-center text-sm"><span className="text-gray-500">Waiting</span> <span className="font-bold text-white">{rb.age || 0}</span></li>
                 <li className="flex justify-between items-center text-sm"><span className="text-gray-500">Road</span> <span className="font-bold text-white">{rb.road || 0}</span></li>
                 <li className="flex justify-between items-center text-sm"><span className="text-gray-500">Traffic</span> <span className="font-bold text-white">{rb.traffic || 0}</span></li>
              </ul>
           </div>

           {/* SECTION 5: Road Information */}
           <div className="bg-white/5 border border-white/10 rounded-2xl p-5">
              <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2"><MapPin className="w-4 h-4" /> Road Information</h3>
              <ul className="space-y-4">
                 <li>
                    <p className="text-xs text-gray-500 mb-1">Road Class</p>
                    <p className="font-bold text-white text-sm">{roadClass}</p>
                 </li>
                 <li>
                    <p className="text-xs text-gray-500 mb-1">Road Importance</p>
                    <p className="font-bold text-white text-sm">{roadImportance}</p>
                 </li>
                 <li>
                    <p className="text-xs text-gray-500 mb-1">Traffic Importance</p>
                    <p className="font-bold text-white text-sm">{trafficImportance}</p>
                 </li>
              </ul>
           </div>
        </div>

        {/* SECTION 6: Why Prioritized (Reasoning) */}
        <div>
          <h3 className="text-xs font-black text-gray-500 uppercase tracking-widest mb-4 border-b border-white/5 pb-2 flex items-center gap-2">
             <FileText className="w-4 h-4" /> Why this hazard is prioritized
          </h3>
          {hasReasons ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {reasons.map((r, i) => (
                <div key={i} className="flex items-start gap-3 bg-white/[0.03] border border-white/5 rounded-xl p-4">
                  <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 shrink-0 mt-1.5" />
                  <div>
                     <p className="text-sm font-medium text-gray-200 leading-snug">{r.message}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center gap-3 text-gray-500 italic text-sm p-5 bg-white/[0.02] rounded-xl border border-white/5">
              <AlertCircle className="w-5 h-5 opacity-50" />
              Awaiting Assessment
            </div>
          )}
        </div>

        {/* SECTION 7 & 8: Recommendation & Assignment Row */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
           {/* SECTION 7: Recommended Response */}
           <div className="bg-indigo-500/10 border border-indigo-500/20 rounded-2xl p-6 text-indigo-100 flex flex-col justify-between">
              <div>
                 <h3 className="text-xs font-black text-indigo-400 uppercase tracking-widest mb-4 flex items-center gap-2"><Shield className="w-4 h-4" /> Recommended Response</h3>
                 <div className="space-y-4">
                    <div>
                       <p className="text-[10px] font-bold uppercase tracking-widest text-indigo-500/80 mb-1">Recommended Team</p>
                       <p className="font-bold text-lg">{recTeam}</p>
                    </div>
                    <div>
                       <p className="text-[10px] font-bold uppercase tracking-widest text-indigo-500/80 mb-1">Recommended Vehicle</p>
                       <div className="flex items-center gap-2 mt-1">
                          <Truck className="w-4 h-4 text-indigo-400" />
                          <span className="text-sm font-bold">{recVehicle}</span>
                       </div>
                    </div>
                    <div>
                       <p className="text-[10px] font-bold uppercase tracking-widest text-indigo-500/80 mb-1">Required Equipment</p>
                       <div className="flex items-center gap-2 mt-1">
                          <Wrench className="w-4 h-4 text-indigo-400" />
                          <span className="text-sm font-bold">{recEquip}</span>
                       </div>
                    </div>
                    <div>
                       <p className="text-[10px] font-bold uppercase tracking-widest text-indigo-500/80 mb-1">Response Time</p>
                       <p className="text-sm font-bold">{recTime}</p>
                    </div>
                 </div>
              </div>
           </div>
           
           {/* SECTION 8: Assignment Status */}
           <div className="bg-white/5 border border-white/10 rounded-2xl p-6 flex flex-col justify-between">
              <div>
                 <h3 className="text-xs font-black text-gray-400 uppercase tracking-widest mb-4 flex items-center gap-2"><UserCircle className="w-4 h-4" /> Current Assignment</h3>
                 <div className="space-y-4">
                    <div>
                       <p className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-1">Assigned Worker</p>
                       <p className="font-bold text-lg text-white">{hazard.assigned_worker_name || "Not Assigned"}</p>
                    </div>
                    <div>
                       <p className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-1">Team</p>
                       <p className="font-bold text-sm text-gray-300">{hazard.assigned_team || hazard.worker_team || "Not Assigned"}</p>
                    </div>
                    <div>
                       <p className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-1">Vehicle</p>
                       <p className="font-bold text-sm text-gray-300">N/A</p>
                    </div>
                    <div>
                       <p className="text-[10px] font-bold uppercase tracking-widest text-gray-500 mb-1">ETA</p>
                       <p className="font-bold text-sm text-gray-300">N/A</p>
                    </div>
                 </div>
              </div>
           </div>
        </div>

        {/* SECTION 8 (Cont): Workflow Preview */}
        <div>
           <h3 className="text-xs font-black text-gray-500 uppercase tracking-widest mb-6 border-b border-white/5 pb-2">Lifecycle Tracking</h3>
           <div className="bg-black/40 border border-white/5 rounded-2xl p-6">
              <WorkflowPreview currentState={hazard.maintenance_state || 'Detected'} />
           </div>
        </div>
      </div>
      
      {/* SECTION 9: Quick Actions (Sticky Bottom) */}
      <div className="border-t border-white/10 bg-black/80 p-5 z-20 flex items-center justify-end gap-3 backdrop-blur-xl shrink-0">
         <button onClick={() => onTrack(hazard)} className="px-6 py-3 bg-white/5 hover:bg-white/10 border border-white/10 text-white text-sm font-bold rounded-xl transition-colors flex items-center gap-2">
            <Activity className="w-4 h-4" /> Open Tracking
         </button>
         <button onClick={() => onAssign(hazard)} className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 text-white shadow-[0_0_25px_rgba(79,70,229,0.4)] text-sm font-black rounded-xl transition-all flex items-center gap-2">
            <UserCircle className="w-4 h-4" /> Assign Worker
         </button>
      </div>
    </div>
  );
}
