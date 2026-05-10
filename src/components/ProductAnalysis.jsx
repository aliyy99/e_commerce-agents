import React from 'react';
import { motion } from 'framer-motion';
import { ExternalLink, ShieldCheck, AlertCircle, TrendingDown, ArrowUpRight } from 'lucide-react';

const ProductAnalysis = () => {
  const stores = [
    { name: 'Amazon', price: '$1,299.00', status: 'In Stock', color: 'text-orange-400' },
    { name: 'eBay', price: '$1,245.50', status: 'Limited', color: 'text-blue-400' },
    { name: 'Local Store', price: '$1,350.00', status: 'In Stock', color: 'text-emerald-400' },
  ];

  return (
    <div className="max-w-5xl mx-auto px-6 py-12 grid grid-cols-1 lg:grid-cols-3 gap-8">
      {/* Product Image & Info */}
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        className="lg:col-span-1 glass-card p-6 flex flex-col gap-6"
      >
        <div className="aspect-square bg-slate-50 rounded-xl overflow-hidden relative group border border-slate-100">
          <div className="absolute inset-0 flex items-center justify-center group-hover:scale-110 transition-transform duration-500">
            <img 
              src="https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&q=80&w=800" 
              alt="MacBook Pro" 
              className="w-full h-full object-cover"
            />
          </div>
          <div className="absolute top-4 right-4 p-2 bg-white/90 backdrop-blur-md rounded-lg shadow-sm border border-slate-200">
            <TrendingDown className="w-5 h-5 text-primary" />
          </div>
        </div>
        <div>
          <h3 className="text-xl font-display font-bold text-slate-900">MacBook Pro 14" M3</h3>
          <p className="text-sm text-slate-500 mt-1">Electronics • Premium Laptops</p>
        </div>
        
        <div className="space-y-4">
          <div className="flex justify-between items-end">
            <span className="text-sm text-slate-400">Analyst Trust Score</span>
            <span className="text-lg font-bold text-primary">94%</span>
          </div>
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
            <motion.div 
              className="h-full bg-primary"
              initial={{ width: 0 }}
              animate={{ width: '94%' }}
              transition={{ delay: 0.5, duration: 1.5 }}
            />
          </div>
          <p className="text-[11px] text-slate-400 flex items-center gap-1">
            <ShieldCheck className="w-3 h-3 text-primary" />
            Verified by Analyst Agent: 1.2k authentic reviews scanned.
          </p>
        </div>
      </motion.div>

      {/* Analysis Details */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="lg:col-span-2 space-y-8"
      >
        {/* Strategic Advice */}
        <div className="glass-card p-8 bg-gradient-to-br from-white to-primary/5 border-primary/20">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <span className="px-4 py-1 bg-primary text-white font-extrabold rounded-lg text-sm tracking-tighter">
                  AL (BUY)
                </span>
                <span className="text-slate-400 text-sm font-medium">Strategic Advice</span>
              </div>
              <h2 className="text-2xl font-display font-bold mb-3 text-slate-900">AI Öngörüsü (AI Insights)</h2>
              <p className="text-slate-600 text-sm leading-relaxed max-w-lg">
                Fiyat şu an 30 günlük ortalamanın %12 altında. Detective Agent, önümüzdeki 2 hafta içinde bir indirim beklemiyor. Mevcut stok seviyeleri kritik.
              </p>
            </div>
            <div className="flex flex-col items-center">
              <div className="text-4xl font-black text-primary mb-1">$1,245.50</div>
              <div className="text-xs text-slate-400 uppercase tracking-widest font-bold">Best Current Price</div>
            </div>
          </div>
        </div>

        {/* Price Table */}
        <div className="glass-card overflow-hidden">
          <div className="p-6 border-b border-slate-100">
            <h3 className="font-display font-bold flex items-center gap-2 text-slate-900">
              <ExternalLink className="w-4 h-4 text-primary" />
              Store Comparison
            </h3>
          </div>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="bg-slate-50 text-slate-500">
                <th className="p-4 font-semibold uppercase text-[10px] tracking-wider">Store</th>
                <th className="p-4 font-semibold uppercase text-[10px] tracking-wider">Availability</th>
                <th className="p-4 font-semibold uppercase text-[10px] tracking-wider">Price</th>
                <th className="p-4 font-semibold uppercase text-[10px] tracking-wider text-right">Link</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {stores.map((store) => (
                <tr key={store.name} className="hover:bg-slate-50 transition-colors">
                  <td className="p-4 font-bold">{store.name}</td>
                  <td className="p-4">
                    <span className="flex items-center gap-1.5 font-medium">
                      <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                      {store.status}
                    </span>
                  </td>
                  <td className={`p-4 font-bold text-slate-900`}>{store.price}</td>
                  <td className="p-4 text-right">
                    <button className="p-2 hover:bg-primary/10 rounded-lg text-primary transition-all">
                      <ArrowUpRight className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
};

export default ProductAnalysis;
