import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, CalendarClock, X } from 'lucide-react';

const TrackModal = ({ isOpen, product, onClose, onConfirm }) => {
  const [days, setDays] = useState(7);

  if (!isOpen || !product) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <motion.div 
            initial={{ opacity: 0 }} 
            animate={{ opacity: 1 }} 
            exit={{ opacity: 0 }} 
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" 
            onClick={onClose} 
          />
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: 20 }} 
            animate={{ opacity: 1, scale: 1, y: 0 }} 
            exit={{ opacity: 0, scale: 0.95, y: 20 }} 
            className="bg-white rounded-3xl shadow-2xl w-full max-w-md relative z-10 overflow-hidden"
          >
            <div className="p-6">
              <div className="flex justify-between items-start mb-6">
                <div className="flex gap-4 items-center">
                  <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary">
                    <Bell className="w-6 h-6 fill-current" />
                  </div>
                  <div>
                    <h3 className="text-xl font-black text-slate-900">Track Product</h3>
                    <p className="text-sm font-medium text-slate-500 line-clamp-1">{product.name}</p>
                  </div>
                </div>
                <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-full transition-colors">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4 mb-8">
                <label className="block text-sm font-bold text-slate-700">How long do you want to track this product?</label>
                <div className="flex items-center gap-3">
                  <CalendarClock className="w-5 h-5 text-slate-400" />
                  <input 
                    type="number" 
                    min="1"
                    max="365"
                    value={days} 
                    onChange={e => setDays(Number(e.target.value))} 
                    className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-slate-900 font-bold focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
                  />
                  <span className="font-bold text-slate-500">Days</span>
                </div>
              </div>

              <div className="flex gap-3">
                <button 
                  onClick={onClose} 
                  className="flex-1 px-4 py-3 rounded-xl font-bold text-slate-600 bg-slate-100 hover:bg-slate-200 transition-colors"
                >
                  Cancel
                </button>
                <button 
                  onClick={() => onConfirm(days)} 
                  className="flex-1 px-4 py-3 rounded-xl font-bold text-white bg-primary hover:bg-primary-hover shadow-sm transition-colors"
                >
                  Start Tracking
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default TrackModal;
