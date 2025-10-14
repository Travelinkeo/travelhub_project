'use client';

import { useState } from 'react';
import ItineraryTranslator from '@/components/translator/ItineraryTranslator';
import PriceCalculator from '@/components/translator/PriceCalculator';
import BatchTranslator from '@/components/translator/BatchTranslator';
import '@/components/translator/translator.css';

export default function TranslatorPage() {
  const [activeTab, setActiveTab] = useState('translator');

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold">Traductor de Itinerarios</h1>
        <p className="text-gray-600 mt-2">
          Traduce itinerarios de diferentes sistemas GDS y calcula precios de boletos
        </p>
      </div>

      <div className="mb-6">
        <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
          <button
            onClick={() => setActiveTab('translator')}
            className={`px-4 py-2 rounded-md transition-colors ${
              activeTab === 'translator'
                ? 'bg-white shadow text-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Traductor
          </button>
          <button
            onClick={() => setActiveTab('calculator')}
            className={`px-4 py-2 rounded-md transition-colors ${
              activeTab === 'calculator'
                ? 'bg-white shadow text-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Calculadora
          </button>
          <button
            onClick={() => setActiveTab('batch')}
            className={`px-4 py-2 rounded-md transition-colors ${
              activeTab === 'batch'
                ? 'bg-white shadow text-blue-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Lote
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        {activeTab === 'translator' && <ItineraryTranslator />}
        {activeTab === 'calculator' && <PriceCalculator />}
        {activeTab === 'batch' && <BatchTranslator />}
      </div>
    </div>
  );
}