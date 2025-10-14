'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function AssistantPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirigir a la nueva página de Linkeo
    router.push('/chatbot');
  }, [router]);

  return (
    <div className="flex items-center justify-center h-screen">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-4">Redirigiendo a Linkeo...</h2>
        <p className="text-gray-600">El asistente ahora se llama Linkeo</p>
      </div>
    </div>
  );
}