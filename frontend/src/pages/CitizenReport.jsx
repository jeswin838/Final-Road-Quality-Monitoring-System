import React, { useState, useRef } from 'react';
import axios from 'axios';
import GlassCard from '../components/GlassCard';
import { 
  Camera, 
  MapPin, 
  Send, 
  CheckCircle2, 
  AlertCircle, 
  Info,
  Loader2,
  Image as ImageIcon,
  ShieldCheck,
  Zap,
  ArrowRight
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function CitizenReport() {
  const [image, setImage] = useState(null);
  const [imageFile, setImageFile] = useState(null);
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const fileInputRef = useRef(null);

  const handleCapture = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => setImage(reader.result);
      reader.readAsDataURL(file);
      
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition((pos) => {
          setLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude });
        });
      }
    }
  };

  const handleSubmit = async () => {
    if (!imageFile || !location) return;
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('image', imageFile);
      formData.append('description', description);
      formData.append('lat', location.lat);
      formData.append('lon', location.lon);
      formData.append('capture_source', 'upload');

      const analyzeRes = await axios.post('/user-report', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      await axios.post('/user-report/submit', analyzeRes.data);
      setSuccess(true);
    } catch (err) {
      console.error("Submission failed", err);
      alert("Processing failed: " + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="max-w-2xl mx-auto py-20 px-4">
        <GlassCard className="p-12 text-center border-success/20 bg-success/5 shadow-[0_20px_50px_rgba(16,185,129,0.15)]">
           <div className="w-24 h-24 bg-success/10 rounded-full flex items-center justify-center mx-auto mb-8 border-2 border-success/30">
              <CheckCircle2 className="w-12 h-12 text-success" />
           </div>
           <h2 className="text-3xl font-black text-title tracking-tight uppercase">Intelligence Logged</h2>
           <p className="text-muted-text font-medium mt-4 max-w-sm mx-auto leading-relaxed">
             Thank you for your contribution. Your evidence has been securely uploaded and is pending AI verification.
           </p>
           <button 
            onClick={() => window.location.reload()}
            className="mt-10 btn btn-primary px-10 shadow-[0_10px_30px_rgba(56,189,248,0.2)]"
           >
             File Another Report
           </button>
        </GlassCard>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-10 pb-32 px-4">
      <div className="text-center pt-8">
        <div className="inline-flex items-center gap-3 px-4 py-2 rounded-2xl bg-accent/10 border border-accent/20 text-accent text-[10px] font-black uppercase tracking-[0.2em] mb-6">
          <Zap className="w-4 h-4" />
          Community Safety Network
        </div>
        <h2 className="text-4xl font-black text-title tracking-tighter uppercase leading-none mb-3">Hazard Intelligence Feed</h2>
        <p className="text-muted-text font-bold uppercase tracking-widest text-xs">Help the AI mapping system identify road failures</p>
      </div>

      <GlassCard className="p-10 border-white/10 shadow-[0_32px_64px_rgba(0,0,0,0.4)]">
        <div className="space-y-10">
          {/* Evidence Capture Area */}
          <div className="space-y-4">
            <label className="text-[10px] font-black text-muted-text uppercase tracking-[0.3em] block">Hazard Evidence</label>
            <div 
              onClick={() => fileInputRef.current.click()}
              className={`aspect-video rounded-[32px] border-4 border-dashed transition-all cursor-pointer flex flex-col items-center justify-center overflow-hidden relative group ${
                image ? 'border-accent/40' : 'border-white/5 hover:border-accent/20 bg-white/[0.02] hover:bg-white/[0.04]'
              }`}
            >
              {image ? (
                <>
                  <img src={image} className="w-full h-full object-cover" alt="Capture preview" />
                  <div className="absolute inset-0 bg-black/50 backdrop-blur-sm opacity-0 group-hover:opacity-100 flex flex-col items-center justify-center transition-all">
                     <Camera className="w-12 h-12 text-white mb-2" />
                     <span className="text-xs font-black text-white uppercase tracking-widest">Replace Evidence</span>
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center gap-4">
                  <div className="w-20 h-20 rounded-3xl bg-white/5 flex items-center justify-center border border-white/10 group-hover:scale-110 transition-transform">
                    <Camera className="w-10 h-10 text-gray-600" />
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-black text-title uppercase tracking-widest">Initialize Camera</p>
                    <p className="text-[10px] text-muted-text font-bold uppercase tracking-widest mt-1">Capture High-Resolution Visuals</p>
                  </div>
                </div>
              )}
              <input 
                type="file" 
                accept="image/*" 
                capture="environment" 
                className="hidden" 
                ref={fileInputRef}
                onChange={handleCapture}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Metadata Info */}
            <div className="space-y-4">
               <label className="text-[10px] font-black text-muted-text uppercase tracking-[0.3em] block">Auto-Telemetry</label>
               <div className={`p-6 rounded-2xl border transition-all flex items-center gap-4 ${
                 location ? 'bg-success/5 border-success/20' : 'bg-white/5 border-white/5'
               }`}>
                  <div className={`p-3 rounded-xl ${location ? 'bg-success/20 text-success' : 'bg-white/10 text-gray-600'}`}>
                    <MapPin className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-[10px] font-black text-muted-text uppercase tracking-widest">GPS Resolution</p>
                    <p className="text-sm font-black text-title">
                      {location ? `${location.lat.toFixed(5)}, ${location.lon.toFixed(5)}` : 'Waiting for Signal...'}
                    </p>
                  </div>
               </div>
            </div>

            <div className="space-y-4">
               <label className="text-[10px] font-black text-muted-text uppercase tracking-[0.3em] block">Validation Status</label>
               <div className="p-6 rounded-2xl bg-white/5 border border-white/5 flex items-center gap-4">
                  <div className="p-3 rounded-xl bg-accent/10 text-accent">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-[10px] font-black text-muted-text uppercase tracking-widest">Network Privacy</p>
                    <p className="text-sm font-black text-title uppercase">Secure & Anonymous</p>
                  </div>
               </div>
            </div>
          </div>

          <div className="space-y-4">
            <label className="text-[10px] font-black text-muted-text uppercase tracking-[0.3em] block">Situational Context</label>
            <textarea 
              placeholder="Provide brief details about the hazard severity or specific road conditions..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-3xl p-6 text-sm font-medium text-title focus:border-accent/40 outline-none transition-all h-32 placeholder:text-gray-700 resize-none"
            />
          </div>

          <div className="pt-6">
            <button 
              disabled={!image || !location || loading}
              onClick={handleSubmit}
              className="w-full btn btn-primary py-5 text-sm tracking-[0.3em] shadow-[0_20px_40px_rgba(56,189,248,0.3)] hover:scale-[1.01] flex items-center justify-center gap-4"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  TRANSMITTING DATA...
                </>
              ) : (
                <>
                  <Send className="w-5 h-5" />
                  TRANSMIT EVIDENCE
                  <ArrowRight className="w-5 h-5 opacity-50 ml-2" />
                </>
              )}
            </button>
          </div>
        </div>
      </GlassCard>

      <div className="p-6 rounded-3xl bg-secondary/50 border border-white/5 flex items-start gap-4">
         <Info className="w-6 h-6 text-accent shrink-0" />
         <p className="text-[10px] text-muted-text font-bold uppercase tracking-widest leading-relaxed">
           Submitted reports are automatically scanned by the PotholePro AI engine for validation. Verified high-severity reports are prioritized for immediate crew deployment.
         </p>
      </div>
    </div>
  );
}
