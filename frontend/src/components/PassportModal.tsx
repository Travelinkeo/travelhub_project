import React, { useState } from 'react';

interface PassportData {
  numero_pasaporte: string;
  nombres: string;
  apellidos: string;
  nacionalidad: string;
  fecha_nacimiento: string;
  fecha_vencimiento: string;
  sexo: string;
  confianza: 'HIGH' | 'MEDIUM' | 'LOW';
  es_valido: boolean;
}

interface PassportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onClientCreated: (clientId: number) => void;
}

export const PassportModal: React.FC<PassportModalProps> = ({
  isOpen,
  onClose,
  onClientCreated
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [extractedData, setExtractedData] = useState<PassportData | null>(null);
  const [passportId, setPassportId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!['image/jpeg', 'image/jpg', 'image/png'].includes(file.type)) {
      setError('Solo se permiten archivos JPG o PNG');
      return;
    }

    setIsUploading(true);
    setError(null);
    setExtractedData(null);

    try {
      const formData = new FormData();
      formData.append('passport_image', file);

      const response = await fetch('http://127.0.0.1:8000/api/passport/upload/', {
        method: 'POST',
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Error procesando imagen');
      }

      setExtractedData(result.data);
      setPassportId(result.passport_id);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setIsUploading(false);
    }
  };

  const handleCreateClient = async () => {
    if (!passportId) return;

    try {
      const response = await fetch(`http://127.0.0.1:8000/api/passport/${passportId}/create-client/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Error creando cliente');
      }

      onClientCreated(result.client_id);
      onClose();
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error creando cliente');
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">Escanear Pasaporte</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
          >
            ×
          </button>
        </div>

        <div className="p-6">
          <div className="mb-6">
            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <svg className="w-8 h-8 mb-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p className="mb-2 text-sm text-gray-500">
                  <span className="font-semibold">Click para subir</span> imagen de pasaporte
                </p>
                <p className="text-xs text-gray-500">PNG o JPG</p>
              </div>
              <input
                type="file"
                className="hidden"
                accept="image/*"
                onChange={handleFileUpload}
                disabled={isUploading}
              />
            </label>
          </div>

          {isUploading && (
            <div className="text-center py-4">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
              <p className="mt-2 text-gray-600">Procesando imagen...</p>
            </div>
          )}

          {error && (
            <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
              {error}
            </div>
          )}

          {extractedData && (
            <div className="bg-gray-50 rounded-lg p-6">
              <h3 className="text-lg font-semibold mb-4">Datos Extraídos</h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Número de Pasaporte
                  </label>
                  <input
                    type="text"
                    value={extractedData.numero_pasaporte}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                    readOnly
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nombres
                  </label>
                  <input
                    type="text"
                    value={extractedData.nombres}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                    readOnly
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Apellidos
                  </label>
                  <input
                    type="text"
                    value={extractedData.apellidos}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                    readOnly
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Nacionalidad
                  </label>
                  <input
                    type="text"
                    value={extractedData.nacionalidad}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                    readOnly
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3">
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-gray-600 border border-gray-300 rounded-md hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  onClick={handleCreateClient}
                  className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  Crear Cliente
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};