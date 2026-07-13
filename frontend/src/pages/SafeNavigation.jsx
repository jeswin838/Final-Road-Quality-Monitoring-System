import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import axios from 'axios';
import { useLiveData } from '../context/LiveDataContext';
import GlassCard from '../components/GlassCard';
import ReportModal from '../components/ReportModal';
import { 
  Navigation, 
  MapPin, 
  ShieldCheck, 
  AlertTriangle, 
  Search,
  Crosshair,
  Info,
  Clock,
  BarChart3,
  CheckCircle2,
  Cpu,
  User,
  Maximize2,
  Wrench,
  CameraOff
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Fix for default marker icons in Leaflet + Vite
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const createPotholeIcon = (color) => L.divIcon({
  className: 'custom-pothole-icon',
  html: `<div style="background-color: ${color}; width: 14px; height: 14px; border: 3px solid white; border-radius: 50%; box-shadow: 0 0 15px ${color};"></div>`,
  iconSize: [14, 14],
  iconAnchor: [7, 7]
});

const startIcon = L.divIcon({
  className: 'nav-icon',
  html: `<div class="bg-success w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-black border-2 border-white shadow-2xl">A</div>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16]
});

const endIcon = L.divIcon({
  className: 'nav-icon',
  html: `<div class="bg-danger w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-black border-2 border-white shadow-2xl">B</div>`,
  iconSize: [32, 32],
  iconAnchor: [16, 16]
});

export default function SafeNavigation() {
  const { data } = useLiveData();
  const potholes = data.map || [];

  const [start, setStart] = useState(null);
  const [end, setEnd] = useState(null);
  const [route, setRoute] = useState(null);
  const [routeData, setRouteData] = useState(null);
  const [loadingRoute, setLoadingRoute] = useState(false);
  const [clickMode, setClickMode] = useState('start'); // 'start' or 'end'
  
  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalReports, setModalReports] = useState([]);
  const [modalLocation, setModalLocation] = useState(null);
  const [loadingReports, setLoadingReports] = useState(false);

  const MapClickHandler = () => {
    useMapEvents({
      click(e) {
        const coords = [e.latlng.lat, e.latlng.lng];
        if (clickMode === 'start') {
          setStart(coords);
          setClickMode('end');
        } else {
          setEnd(coords);
        }
      },
    });
    return null;
  };

  const findSafeRoute = async () => {
    if (!start || !end) return;
    setLoadingRoute(true);
    try {
      const res = await axios.post('/api/safe-route', { start, end });
      setRoute(res.data.route);
      setRouteData(res.data);
    } catch (err) {
      console.error("Routing failed", err);
    } finally {
      setLoadingRoute(false);
    }
  };

  const openReports = async (lat, lon) => {
    setModalLocation([lat, lon]);
    setIsModalOpen(true);
    setLoadingReports(true);
    setModalReports([]);
    try {
      const res = await axios.get(`/api/location-reports?lat=${lat}&lon=${lon}`);
      setModalReports(res.data);
    } catch (err) {
      console.error("Failed to fetch reports", err);
      setModalReports([]);
    } finally {
      setLoadingReports(false);
    }
  };

  return (
    <div className="h-[calc(100vh-120px)] flex gap-8 relative p-2">
      {/* Left Control Panel */}
      <div className="w-[380px] flex flex-col gap-6 z-10 shrink-0">
        <GlassCard className="p-6 space-y-6">
          <div>
            <h3 className="text-lg font-black text-title flex items-center gap-3">
              <Navigation className="w-6 h-6 text-accent" />
              Intelligent Routing
            </h3>
            <p className="text-[11px] text-muted-text font-bold uppercase tracking-widest mt-1">Hazard-Aware Pathfinding</p>
          </div>
          
          <div className="space-y-4">
            <div 
              onClick={() => setClickMode('start')}
              className={`p-4 rounded-2xl border-2 transition-all cursor-pointer group ${
                clickMode === 'start' ? 'bg-accent/10 border-accent/40 shadow-[0_0_15px_rgba(56,189,248,0.1)]' : 'bg-white/5 border-white/5 hover:border-white/10'
              }`}
            >
              <label className="text-[10px] uppercase font-black text-muted-text mb-2 block tracking-tighter">Departure Point</label>
              <div className="flex items-center gap-3">
                <MapPin className={`w-5 h-5 ${start ? 'text-success' : 'text-gray-600'}`} />
                <span className="text-sm font-bold text-body">
                  {start ? `${start[0].toFixed(5)}, ${start[1].toFixed(5)}` : 'Select on map...'}
                </span>
              </div>
            </div>

            <div 
              onClick={() => setClickMode('end')}
              className={`p-4 rounded-2xl border-2 transition-all cursor-pointer group ${
                clickMode === 'end' ? 'bg-accent/10 border-accent/40 shadow-[0_0_15px_rgba(56,189,248,0.1)]' : 'bg-white/5 border-white/5 hover:border-white/10'
              }`}
            >
              <label className="text-[10px] uppercase font-black text-muted-text mb-2 block tracking-tighter">Target Destination</label>
              <div className="flex items-center gap-3">
                <MapPin className={`w-5 h-5 ${end ? 'text-danger' : 'text-gray-600'}`} />
                <span className="text-sm font-bold text-body">
                  {end ? `${end[0].toFixed(5)}, ${end[1].toFixed(5)}` : 'Select on map...'}
                </span>
              </div>
            </div>
          </div>

          <button 
            disabled={!start || !end || loadingRoute}
            onClick={findSafeRoute}
            className="w-full btn btn-primary py-4 text-xs tracking-[0.2em] shadow-[0_8px_32px_rgba(56,189,248,0.3)] hover:scale-[1.02]"
          >
            {loadingRoute ? 'PROCESSING...' : 'FIND SAFE PATH'}
          </button>
        </GlassCard>

        <AnimatePresence>
          {routeData && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
            >
              <GlassCard className="p-6 space-y-6 border-l-[6px] border-l-accent overflow-hidden relative">
                <div className="absolute top-0 right-0 p-6 opacity-10">
                   <ShieldCheck className="w-20 h-20 text-accent" />
                </div>
                
                <div className="flex items-center justify-between relative z-10">
                  <span className={`px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest ${
                    routeData.safety === 'safe' ? 'bg-success/20 text-success border border-success/30' : 
                    routeData.safety === 'moderate' ? 'bg-warning/20 text-warning border border-warning/30' : 'bg-danger/20 text-danger border border-danger/30'
                  }`}>
                    {routeData.safety} ANALYSIS
                  </span>
                  <div className="flex flex-col items-end">
                    <span className="text-[10px] font-black text-muted-text uppercase">Risk Index</span>
                    <span className="text-xl font-black text-title">{routeData.risk_score}%</span>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 relative z-10">
                  <div className="bg-white/5 p-4 rounded-2xl border border-white/5">
                    <p className="text-[10px] text-muted-text font-black uppercase mb-1">Obstacles</p>
                    <p className="text-2xl font-black text-title">{routeData.potholes_on_path}</p>
                  </div>
                  <div className="bg-white/5 p-4 rounded-2xl border border-white/5">
                    <p className="text-[10px] text-muted-text font-black uppercase mb-1">Avoided</p>
                    <p className="text-2xl font-black text-title tracking-tighter">{routeData.avoided_potholes}</p>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Map View */}
      <div className="flex-1 rounded-[32px] overflow-hidden border border-glass-border shadow-[0_32px_64px_rgba(0,0,0,0.4)] z-0 relative">
        <MapContainer 
          center={[12.1326, 78.1944]} 
          zoom={14} 
          zoomControl={false}
          style={{ height: '100%', width: '100%' }}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; CARTO'
          />
          <MapClickHandler />
          
          {start && <Marker position={start} icon={startIcon} />}
          {end && <Marker position={end} icon={endIcon} />}
          
          {route && (
            <Polyline 
              positions={route} 
              pathOptions={{ 
                color: routeData?.safety === 'safe' ? '#10B981' : 
                       routeData?.safety === 'moderate' ? '#F59E0B' : '#F43F5E', 
                weight: 8,
                opacity: 0.9,
                lineCap: 'round',
                lineJoin: 'round',
                dashArray: '1, 12'
              }} 
            />
          )}

          {potholes.map((p) => (
            <Marker 
              key={p.id} 
              position={[p.latitude, p.longitude]} 
              icon={createPotholeIcon(
                p.severity === 'high' ? '#F43F5E' : 
                p.severity === 'medium' ? '#F59E0B' : '#10B981'
              )}
            >
              <Popup>
                <div className="flex flex-col gap-0">
                  {/* Popup Top: Image & Badge */}
                  <div className="relative aspect-video w-full bg-black">
                    {p.image ? (
                      <img src={p.image} className="w-full h-full object-cover" alt="Hazard" />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center text-gray-700 bg-white/5">
                        <CameraOff className="w-8 h-8 mb-1 opacity-20" />
                        <span className="text-[8px] font-black uppercase tracking-widest opacity-40">No Image</span>
                      </div>
                    )}
                    <div className="absolute top-3 left-3">
                      <span className={`px-2 py-1 rounded-md text-[9px] font-black uppercase tracking-tighter backdrop-blur-md border ${
                        p.severity === 'high' ? 'bg-danger/20 text-danger border-danger/40' : 'bg-warning/20 text-warning border-warning/40'
                      }`}>
                        {p.severity} PRIORITY
                      </span>
                    </div>
                  </div>

                  {/* Popup Middle: Metadata */}
                  <div className="p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-[10px] font-black text-muted-text uppercase tracking-widest block">IDENTIFIER</span>
                        <span className="text-sm font-black text-title">HZ-ID: {p.id.toString().padStart(4, '0')}</span>
                      </div>
                      <div className="text-right">
                        <span className="text-[10px] font-black text-muted-text uppercase tracking-widest block">REPORTS</span>
                        <span className="text-sm font-black text-title">{p.report_count || 1} Hits</span>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 py-3 border-y border-white/5">
                      <div className="flex items-center gap-2">
                        <Clock className="w-3.5 h-3.5 text-accent" />
                        <span className="text-[10px] font-bold text-body">{p.last_seen}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <BarChart3 className="w-3.5 h-3.5 text-accent" />
                        <span className="text-[10px] font-bold text-body">{(p.confidence || 0.85 * 100).toFixed(0)}% Conf.</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Cpu className="w-3.5 h-3.5 text-accent" />
                        <span className="text-[10px] font-bold text-body uppercase">{p.source || 'AI'} SOURCE</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-success" />
                        <span className="text-[10px] font-bold text-success uppercase">ACTIVE</span>
                      </div>
                    </div>

                    {/* Popup Bottom: Actions */}
                    <div className="grid grid-cols-2 gap-3 pt-1">
                      <button 
                        onClick={() => openReports(p.latitude, p.longitude)}
                        className="btn btn-primary px-0 py-2.5 text-[10px] tracking-widest"
                      >
                        <Maximize2 className="w-3.5 h-3.5" /> REPORTS
                      </button>
                      <button 
                        className="btn btn-secondary px-0 py-2.5 text-[10px] tracking-widest border-white/10"
                      >
                        <Wrench className="w-3.5 h-3.5" /> FIXED
                      </button>
                    </div>
                  </div>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>

        {/* Floating Controls */}
        <div className="absolute top-6 right-6 z-[1000] flex flex-col gap-3">
          <button 
            onClick={() => {
              setStart(null);
              setEnd(null);
              setRoute(null);
              setRouteData(null);
            }}
            className="w-12 h-12 bg-secondary/90 backdrop-blur-xl border border-white/10 rounded-2xl flex items-center justify-center text-muted-text hover:text-title hover:scale-105 transition-all shadow-2xl"
          >
            <Crosshair className="w-6 h-6" />
          </button>
        </div>
      </div>

      <ReportModal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        reports={modalReports} 
        location={modalLocation}
        loading={loadingReports}
      />
    </div>
  );
}
