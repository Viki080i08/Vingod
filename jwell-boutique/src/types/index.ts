export interface Product {
  id: string;
  name: string;
  description: string | null;
  brand: string | null;
  category: string;
  price: number;
  stock: number;
  images: string;
  nicotine: string | null;
  flavor: string | null;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface OrderItem {
  id: string;
  productId: string;
  quantity: number;
  price: number;
  product?: Product;
}

export interface Order {
  id: string;
  stripeSessionId: string | null;
  customerName: string;
  customerEmail: string;
  customerPhone: string | null;
  status: string;
  totalAmount: number;
  createdAt: string;
  updatedAt: string;
  items: OrderItem[];
}

export interface AnalyzedProduct {
  name: string;
  description: string;
  brand: string;
  category: string;
  price: number;
  nicotine: string;
  flavor: string;
  confidence: number;
}
