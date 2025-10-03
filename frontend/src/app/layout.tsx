import './globals.css';
import React from 'react';
import ResponsiveLayout from '@/components/Layout/ResponsiveLayout';
import { ThemeContextProvider } from '@/contexts/ThemeContext';
import { AuthProvider } from '@/contexts/AuthContext';

export const metadata = {
  title: 'TravelHub Dashboard',
  description: 'Portal de gestión para TravelHub',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="h-full">
      <body className="h-full">
        <AuthProvider>
          <ThemeContextProvider>
            <ResponsiveLayout>
              {children}
            </ResponsiveLayout>
          </ThemeContextProvider>
        </AuthProvider>
      </body>
    </html>
  );
}