export const sampleProducts = [
  {
    id: 1,
    name: 'MacBook Pro 14" M3',
    image: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&q=80&w=800',
    description: 'Apple M3 Pro çipli, 18GB RAM ve 512GB SSD özellikli üst düzey dizüstü bilgisayar. Yüksek performans gerektiren işler için idealdir.',
    aiSummary: 'Fiyat şu an 30 günlük ortalamanın %12 altında. Mevcut stok seviyeleri kritik, önümüzdeki 2 hafta içinde bir indirim beklenmiyor.',
    strategy: 'AL',
    stores: [
      { name: 'Amazon', price: 1299.00, rating: 4.8, maxRating: 5, pros: ['Hızlı kargo', 'Güvenilir satıcı'], cons: ['Fiyat dalgalanması fazla'] },
      { name: 'Hepsiburada', price: 1350.00, rating: 4.6, maxRating: 5, pros: ['Taksit imkanı', 'Orijinal ürün'], cons: ['Kargo süresi uzun'] },
      { name: 'Trendyol', price: 1245.50, rating: 4.4, maxRating: 5, pros: ['Uygun fiyat', 'Kupon fırsatları'], cons: ['Müşteri hizmetleri yavaş'] }
    ]
  },
  {
    id: 2,
    name: 'Sony WH-1000XM5',
    image: 'https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?auto=format&fit=crop&q=80&w=800',
    description: 'Aktif gürültü engelleme (ANC) özellikli, yüksek çözünürlüklü kablosuz kulak üstü kulaklık. 30 saate kadar pil ömrü.',
    aiSummary: 'Genel piyasada fiyatlar stabil, ancak tatil döneminde ufak indirimler olabilir.',
    strategy: 'BEKLE',
    stores: [
      { name: 'Amazon', price: 348.00, rating: 4.7, maxRating: 5, pros: ['Global garanti', 'Hızlı iade'], cons: ['Stok bazen bitiyor'] },
      { name: 'Vatan', price: 380.00, rating: 4.5, maxRating: 5, pros: ['Mağazadan teslim', 'Deneme imkanı'], cons: ['Fiyat yüksek'] },
      { name: 'Mediamarkt', price: 365.00, rating: 4.6, maxRating: 5, pros: ['Ekstra garanti satışı', 'Geniş ağ'], cons: ['Kutu hasarı şikayetleri'] }
    ]
  },
  {
    id: 3,
    name: 'Dyson V15 Detect',
    image: 'https://images.unsplash.com/photo-1558317374-067fb5f30001?auto=format&fit=crop&q=80&w=800',
    description: 'Lazer toz algılama teknolojili, yüksek emiş gücüne sahip dikey şarjlı süpürge. Evcil hayvan sahipleri için özel başlıklar.',
    aiSummary: 'Şu anki fiyatlar en yüksek seviyelerde. Yakın zamanda yeni model duyurulabilir.',
    strategy: 'KAÇIN',
    stores: [
      { name: 'Dyson TR', price: 799.00, rating: 4.9, maxRating: 5, pros: ['Orijinal aksesuar', 'Doğrudan destek'], cons: ['İndirim nadir'] },
      { name: 'Amazon', price: 750.00, rating: 4.8, maxRating: 5, pros: ['Prime teslimat', 'Kolay iade'], cons: ['Kutu içeriği farklılıkları'] },
      { name: 'Teknosa', price: 780.00, rating: 4.4, maxRating: 5, pros: ['Mağaza iadesi', 'Taksit seçenekleri'], cons: ['Personel bilgisizliği'] }
    ]
  },
  {
    id: 4,
    name: 'Samsung Galaxy S24 Ultra',
    image: 'https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?auto=format&fit=crop&q=80&w=800',
    description: 'Snapdragon 8 Gen 3 işlemci, 200MP kamera ve S-Pen destekli amiral gemisi akıllı telefon. Yapay zeka özellikleri ile donatılmıştır.',
    aiSummary: 'Lansman dönemi bitti, fiyatlar oturdu. Mantıklı bir alım noktası.',
    strategy: 'AL',
    stores: [
      { name: 'Samsung', price: 1199.00, rating: 4.8, maxRating: 5, pros: ['Değişim kampanyası', 'Özel renkler'], cons: ['Aksesuar pahalı'] },
      { name: 'Hepsiburada', price: 1150.00, rating: 4.6, maxRating: 5, pros: ['Satıcı çeşitliliği', 'Hızlı kargo'], cons: ['Garantide bazen sorun'] },
      { name: 'Trendyol', price: 1120.00, rating: 4.7, maxRating: 5, pros: ['En iyi fiyat', 'Kılıf hediyesi'], cons: ['İade süreçleri uzun'] }
    ]
  },
  {
    id: 5,
    name: 'PlayStation 5',
    image: 'https://images.unsplash.com/photo-1606813907291-d86efa9b94db?auto=format&fit=crop&q=80&w=800',
    description: 'Sony\'nin yeni nesil oyun konsolu. Işın izleme, 4K çözünürlük, ultra hızlı SSD ve DualSense kontrolcü özellikleri.',
    aiSummary: 'Slim model çıktığı için eski kasalar tükenmek üzere, stoklar sınırlı.',
    strategy: 'BEKLE',
    stores: [
      { name: 'Amazon', price: 499.00, rating: 4.9, maxRating: 5, pros: ['Güvenilir paketleme', 'Prime hız'], cons: ['Hemen tükeniyor'] },
      { name: 'Vatan', price: 550.00, rating: 4.5, maxRating: 5, pros: ['Elden teslim', 'Taksit'], cons: ['Fiyatı en yüksek'] },
      { name: 'Mediamarkt', price: 530.00, rating: 4.6, maxRating: 5, pros: ['Oyun bundle fırsatları'], cons: ['Müşteri hizmetleri zayıf'] }
    ]
  },
  {
    id: 6,
    name: 'Apple Watch Series 9',
    image: 'https://images.unsplash.com/photo-1434493789847-2902a520c14c?auto=format&fit=crop&q=80&w=800',
    description: 'Kan oksijeni, EKG, düşme algılama özellikleri ile sağlık ve fitness takibinde lider. Yeni çift dokunuş jesti.',
    aiSummary: 'Fiyat stabil seyrediyor. İndirim yakalandığında alınabilir.',
    strategy: 'BEKLE',
    stores: [
      { name: 'Apple', price: 399.00, rating: 4.9, maxRating: 5, pros: ['Orijinal kordon seçenekleri', 'Apple Care'], cons: ['İndirim yok'] },
      { name: 'Amazon', price: 379.00, rating: 4.8, maxRating: 5, pros: ['Hızlı kargo', 'Ufak indirimler'], cons: ['Sınırlı renk seçenekleri'] },
      { name: 'Troy', price: 389.00, rating: 4.7, maxRating: 5, pros: ['Mağazadan destek', 'Taksit'], cons: ['İade süreçleri'] }
    ]
  }
];
