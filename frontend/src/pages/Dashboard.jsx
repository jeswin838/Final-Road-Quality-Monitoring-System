import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useLiveData } from '../context/LiveDataContext';
import GlassCard from '../components/GlassCard';
import { 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  TrendingUp, 
  BarChart3, 
  Map as MapIcon,
  ShieldAlert,
  Activity,
  ArrowUpRight,
  Zap,
  MapPin,
  Crosshair
} from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell
} from 'recharts';
import { motion } from 'framer-motion';
import { MapContainer, TileLayer, Marker, useMap } from 'react-leaflet';
import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

function LocationUpdater({ coords }) {
  const map = useMap();
  useEffect(() => {
    if (coords) {
      map.flyTo([coords.lat, coords.lng], 15);
    }
  }, [coords, map]);
  return null;
}

export default function Dashboard() {
  const { data } = useLiveData();
  const stats = data.stats || { total: 0, pending: 0, fixed: 0, history: [] };

  const [myLocation, setMyLocation] = useState(null);
  const [locating, setLocating] = useState(false);

  return (
    <div className="space-y-8 pb-10">
      {/* Top Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Total Hazards', value: stats.total, icon: ShieldAlert, color: 'text-accent', bg: 'bg-accent/10', trend: '+12%' },
          { label: 'Pending Action', value: stats.pending, icon: AlertCircle, color: 'text-warning', bg: 'bg-warning/10', trend: '+3%' },
          { label: 'Resolved (48h)', value: stats.fixed, icon: CheckCircle2, color: 'text-success', bg: 'bg-success/10', trend: '+18%' },
          { label: 'System Health', value: '98.4%', icon: Activity, color: 'text-purple-400', bg: 'bg-purple-500/10', trend: 'STABLE' },
        ].map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <GlassCard className="p-6 relative overflow-hidden group">
              <div className="flex justify-between items-start mb-4 relative z-10">
                <div className={`p-3 rounded-2xl ${stat.bg} ${stat.color}`}>
                  <stat.icon className="w-6 h-6" />
                </div>
                <div className="flex flex-col items-end">
                   <div className="flex items-center gap-1 text-[10px] font-black text-success bg-success/10 px-2 py-0.5 rounded-md">
                     <ArrowUpRight className="w-3 h-3" />
                     {stat.trend}
                   </div>
                </div>
              </div>
              <div className="relative z-10">
                <p className="text-[11px] font-black text-muted-text uppercase tracking-[0.2em] mb-1">{stat.label}</p>
                <p className="text-3xl font-black text-title tracking-tight">{stat.value}</p>
              </div>
              {/* Background Glow */}
              <div className={`absolute -right-4 -bottom-4 w-24 h-24 rounded-full blur-[40px] opacity-20 ${stat.bg}`} />
            </GlassCard>
          </motion.div>
        ))}
      </div>

      {/* Main Charts Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <GlassCard className="lg:col-span-2 p-8">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h3 className="text-xl font-black text-title flex items-center gap-2">
                <TrendingUp className="w-6 h-6 text-accent" />
                Detection Velocity
              </h3>
              <p className="text-xs text-muted-text font-bold uppercase tracking-widest mt-1">Hazard Identification Trends (30 Days)</p>
            </div>
            <div className="flex gap-2">
               <button className="px-3 py-1.5 rounded-lg bg-white/5 border border-white/5 text-[10px] font-bold text-gray-400 hover:text-white transition-all uppercase tracking-widest">Real-Time</button>
               <button className="px-3 py-1.5 rounded-lg bg-accent/20 border border-accent/30 text-[10px] font-black text-accent uppercase tracking-widest">Historical</button>
            </div>
          </div>
          
          <div className="h-[350px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={stats.history}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#38BDF8" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#38BDF8" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#ffffff05" vertical={false} />
                <XAxis 
                  dataKey="date" 
                  stroke="#94A3B8" 
                  fontSize={10} 
                  tickLine={false} 
                  axisLine={false}
                  tickFormatter={(val) => new Date(val).toLocaleDateString('en-US', { day: 'numeric', month: 'short' })}
                />
                <YAxis stroke="#94A3B8" fontSize={10} tickLine={false} axisLine={false} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'rgba(15, 23, 42, 0.95)', 
                    borderRadius: '16px', 
                    border: '1px solid rgba(255,255,255,0.1)',
                    boxShadow: '0 10px 30px rgba(0,0,0,0.5)'
                  }}
                  itemStyle={{ color: '#F8FAFC', fontWeight: 'bold', fontSize: '12px' }}
                  labelStyle={{ color: '#94A3B8', fontSize: '10px', marginBottom: '4px', textTransform: 'uppercase', fontWeight: '900' }}
                />
                <Area 
                  type="monotone" 
                  dataKey="count" 
                  stroke="#38BDF8" 
                  strokeWidth={4}
                  fillOpacity={1} 
                  fill="url(#colorValue)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </GlassCard>

        <div className="space-y-8">
          <GlassCard className="p-8">
            <h3 className="text-sm font-black text-title flex items-center gap-2 mb-6 uppercase tracking-widest">
              <Zap className="w-4 h-4 text-warning" />
              Resource Allocation
            </h3>
            <div className="space-y-6">
              {[
                { label: 'Workforce Active', val: 78, color: '#38BDF8' },
                { label: 'Materials Ready', val: 92, color: '#10B981' },
                { label: 'Budget Utilized', val: 45, color: '#F59E0B' },
              ].map(item => (
                <div key={item.label} className="space-y-2">
                  <div className="flex justify-between text-[11px] font-black uppercase tracking-widest">
                    <span className="text-muted-text">{item.label}</span>
                    <span className="text-title">{item.val}%</span>
                  </div>
                  <div className="h-2 bg-white/5 rounded-full overflow-hidden border border-white/5">
                    <motion.div 
                      initial={{ width: 0 }}
                      animate={{ width: `${item.val}%` }}
                      className="h-full rounded-full" 
                      style={{ backgroundColor: item.color }} 
                    />
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>

          <GlassCard className="p-8 border-l-4 border-l-warning bg-warning/5">
             <div className="flex items-start gap-4">
               <div className="p-3 rounded-2xl bg-warning/20 text-warning">
                 <AlertCircle className="w-6 h-6" />
               </div>
               <div>
                 <h4 className="text-sm font-black text-title uppercase tracking-widest">System Advisory</h4>
                 <p className="text-xs text-muted-text font-bold mt-1 leading-relaxed">
                   High hazard density detected in Dharmapuri East sector. AI recommends deploying 2 additional maintenance crews.
                 </p>
                 <button className="mt-4 text-[10px] font-black text-warning uppercase tracking-[0.2em] hover:underline">Dismiss Alert</button>
               </div>
             </div>
          </GlassCard>

          <GlassCard className="p-8 border-l-4 border-l-success bg-success/5 flex flex-col group">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h4 className="text-sm font-black text-title flex items-center gap-2 uppercase tracking-widest">
                  <MapPin className="w-4 h-4 text-success" />
                  Operator Location
                </h4>
                <p className="text-xs text-muted-text font-bold mt-1">Real-time telemetry tracking</p>
              </div>
              <button 
                onClick={() => {
                  setLocating(true);
                  if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(
                      (pos) => {
                        setMyLocation({ lat: pos.coords.latitude, lng: pos.coords.longitude });
                        setLocating(false);
                      },
                      (err) => {
                        console.error(err);
                        setLocating(false);
                      }
                    );
                  } else {
                    setLocating(false);
                  }
                }}
                disabled={locating}
                className="p-2 rounded-xl bg-success/20 text-success hover:bg-success/30 transition-colors"
                title="My Location"
              >
                {locating ? <Activity className="w-5 h-5 animate-pulse" /> : <Crosshair className="w-5 h-5" />}
              </button>
            </div>
            
            {myLocation ? (
              <div className="h-40 w-full rounded-2xl overflow-hidden border border-white/10 mt-2 relative z-0">
                <MapContainer center={[myLocation.lat, myLocation.lng]} zoom={15} zoomControl={false} style={{ height: '100%', width: '100%' }}>
                  <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />
                  <Marker position={[myLocation.lat, myLocation.lng]} />
                  <LocationUpdater coords={myLocation} />
                </MapContainer>
              </div>
            ) : (
              <div className="h-40 w-full rounded-2xl bg-white/5 border border-white/10 mt-2 flex flex-col items-center justify-center text-muted-text">
                 <MapIcon className="w-8 h-8 mb-2 opacity-20" />
                 <span className="text-[10px] font-black uppercase tracking-widest opacity-50">Location Unknown</span>
              </div>
            )}
            
            {myLocation && (
              <div className="mt-4 flex justify-between text-[10px] font-black uppercase tracking-widest text-success">
                <span>LAT: {myLocation.lat.toFixed(4)}</span>
                <span>LNG: {myLocation.lng.toFixed(4)}</span>
              </div>
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
