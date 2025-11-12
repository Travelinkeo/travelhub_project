import Link from 'next/link';

export default function BoletosLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4">
          <div className="flex space-x-8 py-4">
            <Link href="/boletos/dashboard" className="text-blue-600 hover:text-blue-800 font-medium">
              Dashboard
            </Link>
            <Link href="/boletos/buscar" className="text-gray-600 hover:text-gray-800">
              Buscar
            </Link>
            <Link href="/boletos/reportes" className="text-gray-600 hover:text-gray-800">
              Reportes
            </Link>
            <Link href="/boletos/anulaciones" className="text-gray-600 hover:text-gray-800">
              Anulaciones
            </Link>
          </div>
        </div>
      </nav>
      <main>{children}</main>
    </div>
  );
}
