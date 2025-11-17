import './globals.css';
import React from 'react';
import ResponsiveLayout from '@/components/layout/ResponsiveLayout';
import { ThemeContextProvider } from '@/contexts/ThemeContext';
import { AuthProvider } from '@/contexts/AuthContext';
import ChatWidget from '@/components/chatbot/ChatWidget';
import RegisterSW from './register-sw';
import { Metadata, Viewport } from 'next';

export const metadata: Metadata = {
  title: 'TravelHub Dashboard',
  description: 'Portal de gestión para TravelHub',
  manifest: '/manifest.json',
  themeColor: '#0d47a1',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'TravelHub',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="h-full">
      <body className="h-full">
        <RegisterSW />
        <AuthProvider>
          <ThemeContextProvider>
            <ResponsiveLayout>
              {children}
            </ResponsiveLayout>
            <ChatWidget />
          </ThemeContextProvider>
        </AuthProvider>
      </body>
    </html>
  );
}