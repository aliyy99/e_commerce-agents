import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, X, ArrowRight, ImageIcon } from 'lucide-react';

const VisionMatchModal = ({
  isOpen,
  brand,
  suggestedModels = [],
  detected,
  uploadedImage,
  onConfirm,
  onClose,
}) => {
  const [customModel, setCustomModel] = useState('');

  if (!isOpen) return null;

  const handlePick = (model) => {
    setCustomModel('');
    onConfirm(model);
  };

  const handleCustomSubmit = (e) => {
    e?.preventDefault?.();
    const trimmed = customModel.trim();
    if (!trimmed) return;
    const finalQuery = brand && !trimmed.toLowerCase().includes(brand.toLowerCase())
      ? `${brand} ${trimmed}`
      : trimmed;
    onConfirm(finalQuery);
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 20 }}
          transition={{ type: 'spring', damping: 22, stiffness: 240 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-white rounded-3xl shadow-2xl w-full max-w-2xl overflow-hidden border border-slate-100"
        >
          <div className="px-8 py-6 border-b border-slate-100 flex items-start gap-4">
            <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary shrink-0">
              <Sparkles className="w-6 h-6" />
            </div>
            <div className="flex-1 min-w-0">
              <h2 className="text-xl font-display font-black text-slate-900">
                We detected <span className="text-primary">{brand}</span> in your image
              </h2>
              <p className="text-sm text-slate-500 mt-1">
                We couldn't pinpoint the exact model. Pick one from the list, or type the model name yourself.
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="px-8 py-6 space-y-6">
            {uploadedImage && (
              <div className="flex items-center gap-3 text-xs text-slate-500">
                <div className="relative w-14 h-14 rounded-xl overflow-hidden border border-slate-200 bg-slate-50 shrink-0">
                  <img src={uploadedImage} alt="Uploaded" className="w-full h-full object-cover" />
                </div>
                <div>
                  <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-1">Detected from</p>
                  <p className="font-semibold text-slate-700 flex items-center gap-1.5">
                    <ImageIcon className="w-3.5 h-3.5" /> Your uploaded image
                    {detected?.confidence != null && (
                      <span className="ml-2 px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-[10px] font-bold">
                        Confidence: {(detected.confidence * 100).toFixed(0)}%
                      </span>
                    )}
                  </p>
                </div>
              </div>
            )}

            {suggestedModels.length > 0 && (
              <div>
                <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-3">
                  Pick a model
                </p>
                <div className="flex flex-wrap gap-2">
                  {suggestedModels.map((m) => (
                    <button
                      key={m}
                      onClick={() => handlePick(m)}
                      className="px-4 py-2 rounded-xl border border-slate-200 bg-white text-sm font-semibold text-slate-700 hover:border-primary hover:bg-primary/5 hover:text-primary transition-all"
                    >
                      {m}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div className="relative">
              <div className="absolute inset-y-0 left-0 flex items-center pr-3">
                <div className="h-px bg-slate-200 flex-1" />
              </div>
            </div>

            <form onSubmit={handleCustomSubmit}>
              <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-3">
                Or specify the model
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={customModel}
                  onChange={(e) => setCustomModel(e.target.value)}
                  placeholder={`e.g. ${suggestedModels[0] || 'Galaxy S24 Ultra'}`}
                  className="flex-1 px-4 py-3 rounded-xl border border-slate-200 bg-white text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:border-primary transition-colors"
                />
                <button
                  type="submit"
                  disabled={!customModel.trim()}
                  className={`px-5 rounded-xl font-bold text-sm flex items-center gap-2 transition-all ${
                    customModel.trim()
                      ? 'bg-primary text-white hover:bg-primary-hover shadow-sm'
                      : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                  }`}
                >
                  Confirm <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </form>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default VisionMatchModal;
