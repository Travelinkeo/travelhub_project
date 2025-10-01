import './globals.css';
import React from 'react';
import ResponsiveLayout from '@/components/Layout/ResponsiveLayout';
import { ThemeContextProvider } from '@/contexts/ThemeContext';

export const metadata = {
  title: 'TravelHub Dashboard',
  description: 'Portal de gestión para TravelHub',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className="h-full">
      <body className="h-full">
        <ThemeContextProvider>
          <ResponsiveLayout>
            {children}
          </ResponsiveLayout>
        </ThemeContextProvider>
      </body>
    </html>
  );
}