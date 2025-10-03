'use client';

import React from 'react';
import { PassportUploader } from '@/components/PassportUploader';

export default function PassportScannerPage() {
  const handleDataExtracted = (data: any, passportId: number) => {
    console.log('Datos extraídos:', data);
    console.log('ID del pasaporte:', passportId);
  };

  const handleClientCreated = (clientId: number) => {
    console.log('Cliente creado/actualizado:', clientId);
    // Aquí podrías redirigir al cliente o mostrar un mensaje
  };

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="container mx-auto px-4">
        <PassportUploader
          onDataExtracted={handleDataExtracted}
          onClientCreated={handleClientCreated}
        />
      </div>
    </div>
  );
}