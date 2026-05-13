import React from 'react';
import { motion } from 'framer-motion';
import { Bell, ArrowDown, ArrowUp, X } from 'lucide-react';

const trackedProducts = [
  { id: 1, name: 'Sony WH-1000XM5', price: '12,999 TL', change: '-850 TL', trend: 'down' },
  { id: 2, name: 'iPad Air M2', price: '24,499 TL', change: '+500 TL', trend: 'up' },
  { id: 3, name: 'Keychron K2 V2', price: '2,899 TL', change: 'Stable', trend: 'stable' },
];

const TrackingList = () => {
  return (
    <div className="fixed right-6 top-24 w-80 space-y-4 z-40 hidden xl:block">
      <div className="flex items-center justify-between px-2">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-widest flex items-center gap-2">
          <Bell className="w-3 h-3" />
          Price Tracking
        </h3>
        <span className="text-[10px] bg-primary/10 text-primary px-2 py-0.5 rounded-full font-bold">3 ACTIVE</span>
      </div>

      <div className="space-y-3">
        {trackedProducts.map((product) => (
          <motion.div
            key={product.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            whileHover={{ x: -5 }}
            className="glass-card p-4 flex items-center gap-4 group cursor-pointer"
          >
            <div className={`p-2 rounded-lg ${
              product.trend === 'down' ? 'bg-primary/10 text-primary' : 
              product.trend === 'up' ? 'bg-red-500/10 text-red-500' : 
              'bg-slate-50 text-slate-400'
            }`}>
              {product.trend === 'down' ? <ArrowDown className="w-4 h-4" /> : 
               product.trend === 'up' ? <ArrowUp className="w-4 h-4" /> : 
               <Bell className="w-4 h-4" />}
            </div>
            <div className="flex-1">
              <h4 className="text-sm font-semibold truncate text-slate-800">{product.name}</h4>
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-slate-900">{product.price}</span>
                <span className={`text-[10px] font-bold ${
                  product.trend === 'down' ? 'text-primary' : 
                  product.trend === 'up' ? 'text-red-500' : 
                  'text-slate-400'
                }`}>
                  {product.change}
                </span>
              </div>
            </div>
            <button className="opacity-0 group-hover:opacity-100 p-1 hover:bg-slate-100 rounded-md transition-all">
              <X className="w-3 h-3 text-slate-300" />
            </button>
          </motion.div>
        ))}
      </div>
    </div>
  );
};

export default TrackingList;
