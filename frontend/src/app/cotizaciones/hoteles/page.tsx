'use client';

import { useState, useEffect } from 'react';

interface ResultadoHotel {
  hotel: string;
  destino: string;
  regimen: string;
  comision: number;
  total_sin_comision: number;
  comision_monto: number;
  total_neto: number;
  desglose: Array<{
    tipo_habitacion: string;
    ocupacion: string;
    precio_noche: number;
    noches: number;
    subtotal: number;
    temporada: string;
  }>;
  politica_ninos: string;
  check_in: string;
  check_out: string;
}

export default function CotizadorHoteles() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('demo');
  const [password, setPassword] = useState('demo2025');
  const [destino, setDestino] = useState('Isla Margarita');
  const [nombreHotel, setNombreHotel] = useState('');
  const [fechaEntrada, setFechaEntrada] = useState('');
  const [fechaSalida, setFechaSalida] = useState('');
  const [tipoHab, setTipoHab] = useState('DBL');
  const [resultados, setResultados] = useState<ResultadoHotel[]>([]);
  const [todosHoteles, setTodosHoteles] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [noches, setNoches] = useState(0);

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      setIsAuthenticated(true);
      cargarHoteles();
    }
  }, []);

  const cargarHoteles = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('http://127.0.0.1:8000/api/hoteles-tarifario/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setTodosHoteles(data.results || data);
      }
    } catch (err) {
      console.error('Error cargando hoteles:', err);
    }
  };

  const login = async () => {
    try {
      const response = await fetch('http://127.0.0.1:8000/api/auth/jwt/obtain/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (!response.ok) throw new Error('Credenciales incorrectas');

      const data = await response.json();
      localStorage.setItem('auth_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      setIsAuthenticated(true);
      setError('');
    } catch (err) {
      setError('Error al iniciar sesión');
    }
  };

  const cotizar = async () => {
    if (!fechaEntrada || !fechaSalida) {
      setError('Selecciona fechas de entrada y salida');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const token = localStorage.getItem('auth_token');
      const body: any = {
        fecha_entrada: fechaEntrada,
        fecha_salida: fechaSalida,
        habitaciones: [{ tipo: tipoHab, adultos: 2, ninos: 0 }]
      };
      
      if (destino) body.destino = destino;
      if (nombreHotel) body.nombre_hotel = nombreHotel;

      const response = await fetch('http://127.0.0.1:8000/api/hoteles-tarifario/cotizar/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(body)
      });

      if (!response.ok) throw new Error('Error en cotización');

      const data = await response.json();
      setResultados(data.hoteles);
      setNoches(data.noches);
      
      if (data.hoteles.length === 0) {
        setError('No se encontraron hoteles con tarifas para las fechas seleccionadas');
      }
    } catch (err) {
      setError('Error al cotizar. Verifica tu conexión.');
    } finally {
      setLoading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="bg-white rounded-lg shadow p-8 max-w-md w-full">
          <h1 className="text-2xl font-bold mb-6">Iniciar Sesión</h1>
          
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Usuario</label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg" />
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Contraseña</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border rounded-lg" />
          </div>

          {error && <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded text-red-700">{error}</div>}

          <button onClick={login}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700">
            Iniciar Sesión
          </button>

          <p className="mt-4 text-sm text-gray-600 text-center">
            Usuario demo: demo / demo2025
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Cotizador de Hoteles</h1>
          <button onClick={() => { localStorage.clear(); setIsAuthenticated(false); }}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900">
            Cerrar Sesión
          </button>
        </div>

        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-2">Destino</label>
              <select value={destino} onChange={(e) => setDestino(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg">
                <option value="">Todos los destinos</option>
                <option value="Caracas">Caracas</option>
                <option value="Isla Margarita">Isla Margarita</option>
                <option value="Los Roques">Los Roques</option>
                <option value="Maiquetia">Maiquetia</option>
                <option value="Morrocoy">Morrocoy</option>
                <option value="Canaima">Canaima</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Nombre del Hotel</label>
              <input type="text" value={nombreHotel} onChange={(e) => setNombreHotel(e.target.value)}
                placeholder="Buscar por nombre..."
                className="w-full px-4 py-2 border rounded-lg" />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">

            <div>
              <label className="block text-sm font-medium mb-2">Entrada</label>
              <input type="date" value={fechaEntrada} onChange={(e) => setFechaEntrada(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg" />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Salida</label>
              <input type="date" value={fechaSalida} onChange={(e) => setFechaSalida(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg" />
            </div>
          </div>

          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Tipo de Habitación</label>
            <select value={tipoHab} onChange={(e) => setTipoHab(e.target.value)}
              className="px-4 py-2 border rounded-lg">
              <option value="SGL">Simple</option>
              <option value="DBL">Doble</option>
              <option value="TPL">Triple</option>
            </select>
          </div>

          {error && <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded text-red-700">{error}</div>}

          <button onClick={cotizar} disabled={loading}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 disabled:bg-gray-400">
            {loading ? 'Cotizando...' : 'Buscar Hoteles'}
          </button>
        </div>

        {todosHoteles.length > 0 && resultados.length === 0 && (
          <div className="bg-white rounded-lg shadow p-6 mb-8">
            <h2 className="text-xl font-bold mb-4">Hoteles Disponibles ({todosHoteles.length})</h2>
            <p className="text-gray-600 mb-4">Selecciona fechas para ver tarifas</p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {todosHoteles.map((hotel, i) => (
                <div key={i} className="border rounded-lg p-4">
                  <h3 className="font-bold">{hotel.nombre}</h3>
                  <p className="text-sm text-gray-600">{hotel.destino}</p>
                  <span className="inline-block mt-2 px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                    {hotel.regimen}
                  </span>
                  <p className="text-xs text-gray-500 mt-2">Comisión: {hotel.comision}%</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {resultados.length > 0 && (
          <div>
            <h2 className="text-2xl font-bold mb-4">{resultados.length} Hoteles con Tarifas ({noches} noches)</h2>

            <div className="space-y-4">
              {resultados.map((hotel, i) => (
                <div key={i} className="bg-white rounded-lg shadow p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl font-bold">{hotel.hotel}</h3>
                      <p className="text-gray-600">{hotel.destino}</p>
                      <span className="inline-block mt-2 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                        {hotel.regimen}
                      </span>
                    </div>
                    <div className="text-right">
                      <p className="text-3xl font-bold text-blue-600">${hotel.total_sin_comision.toFixed(2)}</p>
                      <p className="text-sm text-gray-500">Total</p>
                    </div>
                  </div>

                  {hotel.desglose.length > 0 && (
                    <div className="border-t pt-4 mb-4">
                      <h4 className="font-semibold mb-2">Desglose:</h4>
                      {hotel.desglose.map((item, j) => (
                        <div key={j} className="flex justify-between text-sm text-gray-600 mb-1">
                          <span>{item.tipo_habitacion} ({item.ocupacion})</span>
                          <span>{item.moneda === 'EUR' ? '€' : '$'}{item.precio_noche.toFixed(2)}/noche × {item.noches} = {item.moneda === 'EUR' ? '€' : '$'}{item.subtotal.toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="border-t pt-4 mb-4">
                    <div className="flex justify-between text-sm mb-1">
                      <span>Comisión ({hotel.comision}%):</span>
                      <span className="text-green-600 font-semibold">${hotel.comision_monto.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span>Neto proveedor:</span>
                      <span className="font-semibold">${hotel.total_neto.toFixed(2)}</span>
                    </div>
                  </div>

                  <div className="border-t pt-4 text-sm text-gray-600">
                    <p><strong>Check-in:</strong> {hotel.check_in}</p>
                    <p><strong>Check-out:</strong> {hotel.check_out}</p>
                  </div>

                  <button className="mt-4 w-full bg-green-600 text-white py-2 rounded-lg font-semibold hover:bg-green-700">
                    Reservar
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
