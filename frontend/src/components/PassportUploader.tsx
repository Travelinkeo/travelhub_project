import React, { useState } from 'react';
import { Upload, User, FileText, CheckCircle, AlertCircle } from 'lucide-react';

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

interface PassportUploaderProps {
  onDataExtracted?: (data: PassportData, passportId: number) => void;
  onClientCreated?: (clientId: number) => void;
}

export const PassportUploader: React.FC<PassportUploaderProps> = ({
  onDataExtracted,
  onClientCreated
}) => {
  const [isUploading, setIsUploading] = useState(false);
  const [extractedData, setExtractedData] = useState<PassportData | null>(null);
  const [passportId, setPassportId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCreatingClient, setIsCreatingClient] = useState(false);

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validar tipo de archivo
    if (!['image/jpeg', 'image/jpg', 'image/png'].includes(file.type)) {
      setError('Solo se permiten archivos JPG o PNG');
      return;
    }

    // Validar tamaño (máximo 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError('El archivo es demasiado grande (máximo 10MB)');
      return;
    }

    setIsUploading(true);
    setError(null);
    setExtractedData(null);

    try {
      const formData = new FormData();
      formData.append('passport_image', file);

      const token = localStorage.getItem('access_token');
      const response = await fetch('/api/passport/upload/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Error procesando imagen');
      }

      setExtractedData(result.data);
      setPassportId(result.passport_id);
      onDataExtracted?.(result.data, result.passport_id);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setIsUploading(false);
    }
  };

  const handleCreateClient = async () => {
    if (!passportId) return;

    setIsCreatingClient(true);
    setError(null);

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`/api/passport/${passportId}/create-client/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || 'Error creando cliente');
      }

      onClientCreated?.(result.client_id);
      alert(`Cliente ${result.action === 'created' ? 'creado' : 'actualizado'} exitosamente`);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error creando cliente');
    } finally {
      setIsCreatingClient(false);
    }
  };

  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'HIGH': return 'text-green-600 bg-green-100';
      case 'MEDIUM': return 'text-yellow-600 bg-yellow-100';
      case 'LOW': return 'text-red-600 bg-red-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getConfidenceText = (confidence: string) => {
    switch (confidence) {
      case 'HIGH': return 'Alta';
      case 'MEDIUM': return 'Media';
      case 'LOW': return 'Baja';
      default: return 'Desconocida';
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <div className="text-center mb-6">
        <FileText className="mx-auto h-12 w-12 text-blue-500 mb-4" />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Escanear Pasaporte
        </h2>
        <p className="text-gray-600">
          Sube una foto del pasaporte para extraer automáticamente los datos
        </p>
      </div>

      {/* Upload Area */}
      <div className="mb-6">
        <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-gray-300 border-dashed rounded-lg cursor-pointer bg-gray-50 hover:bg-gray-100">
          <div className="flex flex-col items-center justify-center pt-5 pb-6">
            <Upload className="w-8 h-8 mb-4 text-gray-500" />
            <p className="mb-2 text-sm text-gray-500">
              <span className="font-semibold">Click para subir</span> o arrastra la imagen
            </p>
            <p className="text-xs text-gray-500">PNG o JPG (máx. 10MB)</p>
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

      {/* Loading State */}
      {isUploading && (
        <div className="text-center py-4">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          <p className="mt-2 text-gray-600">Procesando imagen...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          <div className="flex items-center">
            <AlertCircle className="h-5 w-5 mr-2" />
            {error}
          </div>
        </div>
      )}

      {/* Extracted Data */}
      {extractedData && (
        <div className="bg-gray-50 rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">
              Datos Extraídos
            </h3>
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${getConfidenceColor(extractedData.confianza)}`}>
              Confianza: {getConfidenceText(extractedData.confianza)}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fecha de Nacimiento
              </label>
              <input
                type="text"
                value={extractedData.fecha_nacimiento || 'No detectada'}
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                readOnly
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Fecha de Vencimiento
              </label>
              <input
                type="text"
                value={extractedData.fecha_vencimiento || 'No detectada'}
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white"
                readOnly
              />
            </div>
          </div>

          {/* Create Client Button */}
          {extractedData.es_valido && (
            <div className="mt-6 text-center">
              <button
                onClick={handleCreateClient}
                disabled={isCreatingClient}
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
              >
                {isCreatingClient ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Creando Cliente...
                  </>
                ) : (
                  <>
                    <User className="h-5 w-5 mr-2" />
                    Crear/Actualizar Cliente
                  </>
                )}
              </button>
            </div>
          )}

          {!extractedData.es_valido && (
            <div className="mt-4 p-3 bg-yellow-100 border border-yellow-400 text-yellow-700 rounded">
              <AlertCircle className="h-5 w-5 inline mr-2" />
              Los datos extraídos están incompletos. Revisa manualmente antes de crear el cliente.
            </div>
          )}
        </div>
      )}
    </div>
  );
};