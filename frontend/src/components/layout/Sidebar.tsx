'use client';

import Link from 'next/link';
import { useState } from 'react';
import { IconButton } from '@mui/material';


interface SidebarProps {
  isOpen: boolean;
  onToggle: () => void;
}

const Sidebar = ({ isOpen, onToggle }: SidebarProps) => {
  const menuItems = [
    { name: 'Dashboard', path: '/' },
    {
      name: 'CRM',
      path: '/crm',
      subItems: [
        { name: 'Clientes', path: '/crm/clientes' },
        { name: 'Proveedores', path: '/crm/proveedores' },
      ],
    },
    {
      name: 'ERP',
      path: '/erp',
      subItems: [
        { name: 'Ventas', path: '/erp/ventas' },
        { name: 'Boletos Importados', path: '/erp/boletos-importados' },
        { name: 'Facturas de Clientes', path: '/erp/facturas-clientes' },
        { name: 'Cotizaciones', path: '/erp/cotizaciones' },
        { name: 'Liquidaciones', path: '/erp/liquidaciones' },
        { name: 'Pasaportes OCR', path: '/erp/pasaportes' },
        { name: 'Auditoría', path: '/erp/auditoria' },
      ],
    },
    {
      name: 'Reportes',
      path: '/reportes',
      subItems: [
        { name: 'Libro Diario', path: '/reportes/libro-diario' },
        { name: 'Balance', path: '/reportes/balance' },
        { name: 'Validación', path: '/reportes/validacion' },
      ],
    },
    {
      name: 'Comunicaciones',
      path: '/comunicaciones',
      subItems: [
        { name: 'Inbox Proveedores', path: '/comunicaciones/inbox' },
      ],
    },
    { name: 'Traductor', path: '/traductor' },
    { name: 'Linkeo (Chat)', path: '/chatbot' },
    { name: 'CMS', path: '/cms' },
  ];

  return (
    <>
      {/* Overlay para móvil */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden" 
          onClick={onToggle}
        />
      )}
      
      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-50
        w-64 h-screen bg-brand-primary text-brand-on-primary flex flex-col
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Header con logo */}
        <div className="p-6">
          <img src="/LOGO.svg" alt="Travelinkeo" className="h-12 w-auto" />
        </div>
        
        {/* Navegación */}
        <nav className="flex-1 px-4 py-4">
          <ul>
            {menuItems.map((item) => (
              <li key={item.name}>
                <Link
                  href={item.path}
                  className="block px-4 py-2 rounded-md hover:bg-brand-secondary transition-colors text-white"
                  onClick={() => window.innerWidth < 1024 && onToggle()}
                >
                  {item.name}
                </Link>
                {item.subItems && (
                  <ul className="pl-4 mt-2">
                    {item.subItems.map((subItem) => (
                      <li key={subItem.name}>
                        <Link
                          href={subItem.path}
                          className="block px-4 py-2 rounded-md text-sm hover:bg-brand-secondary transition-colors text-white"
                          onClick={() => window.innerWidth < 1024 && onToggle()}
                        >
                          {subItem.name}
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </nav>
        

      </aside>
    </>
  );
};

export default Sidebar;