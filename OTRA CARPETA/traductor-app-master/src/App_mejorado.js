import './App_mejorado.css';
import { useState } from 'react';
import airlinesData from './airlines.json';
import airportsData from './airports.json';

export default function App() {
  const [itinerary, setItinerary] = useState('');
  const [output, setOutput] = useState('');
  const [selectedSystem, setSelectedSystem] = useState('SABRE');
  const [cantidad1, setCantidad1] = useState('');
  const [cantidad2, setCantidad2] = useState('');
  const [cantidad3, setCantidad3] = useState('');
  const [porcentaje, setPorcentaje] = useState('');
  const [resultadoCalculadora, setResultadoCalculadora] = useState('');

  // Función para obtener logo de aerolínea usando API gratuita
  const getAirlineLogo = (airlineCode) => {
    // Usar API gratuita de logos de aerolíneas
    return `https://images.kiwi.com/airlines/64x64/${airlineCode}.png`;
  };

  // Función mejorada para obtener información de aeropuerto
  const getAirportInfo = (code) => {
    const airport = airportsData.find(a => a.code === code);
    return {
      name: airport?.name || code,
      code: code
    };
  };

  // Función mejorada para obtener información de aerolínea
  const getAirlineInfo = (code) => {
    const airline = airlinesData.find(a => a.code === code);
    return {
      name: airline?.name || `Aerolínea ${code}`,
      code: code,
      logo: getAirlineLogo(code)
    };
  };

  // Función para calcular duración de vuelo
  const calculateFlightDuration = (depTime, arrTime, sameDay = true) => {
    const depHour = parseInt(depTime.substring(0, 2));
    const depMin = parseInt(depTime.substring(2, 4));
    let arrHour = parseInt(arrTime.substring(0, 2));
    const arrMin = parseInt(arrTime.substring(2, 4));

    if (!sameDay) arrHour += 24;

    const depMinutes = depHour * 60 + depMin;
    const arrMinutes = arrHour * 60 + arrMin;
    const duration = arrMinutes - depMinutes;

    const hours = Math.floor(duration / 60);
    const minutes = duration % 60;

    return `${hours}h ${minutes}m`;
  };

  const parseItinerary = () => {
    try {
      const airlines = airlinesData.reduce((acc, airline) => {
        acc[airline.code] = airline.name;
        return acc;
      }, {});

      const airports = airportsData.reduce((acc, airport) => {
        acc[airport.code] = airport.name;
        return acc;
      }, {});

      let output = '';
      if (selectedSystem === 'SABRE') {
        output = parseSabreEnhanced(itinerary, airlines, airports);
      } else if (selectedSystem === 'Amadeus') {
        output = parseAmadeusEnhanced(itinerary, airlines, airports);
      } else if (selectedSystem === 'KIU') {
        output = parseKiuEnhanced(itinerary, airlines, airports);
      }
      setOutput(output);
    } catch (error) {
      console.error('Error al procesar el itinerario:', error);
      setOutput('<div class="error-card">❌ Error al procesar el itinerario. Verifique el formato.</div>');
    }
  };

  const calcularMonto = () => {
    const cant1 = parseFloat(cantidad1) || 0;
    const cant2 = parseFloat(cantidad2) || 0;
    const cant3 = parseFloat(cantidad3) || 0;
    const pct = parseFloat(porcentaje) || 0;

    if (cant1 === 0 && cant2 === 0 && cant3 === 0) {
      alert('Por favor, ingresa al menos un valor válido.');
      return;
    }

    const sumaTotal = cant1 + cant2 + cant3;
    const montoPorcentaje = sumaTotal * (pct / 100);
    const montoFinal = sumaTotal + montoPorcentaje;

    setResultadoCalculadora(`
      <div class="pricing-result">
        <div class="pricing-breakdown">
          <div class="pricing-item">
            <span>Tarifa Base:</span>
            <span>$${cant1.toFixed(2)}</span>
          </div>
          <div class="pricing-item">
            <span>Fee Consolidador:</span>
            <span>$${cant2.toFixed(2)}</span>
          </div>
          <div class="pricing-item">
            <span>Fee Interno:</span>
            <span>$${cant3.toFixed(2)}</span>
          </div>
          <div class="pricing-item subtotal">
            <span>Subtotal:</span>
            <span>$${sumaTotal.toFixed(2)}</span>
          </div>
          <div class="pricing-item">
            <span>Margen (${pct}%):</span>
            <span>$${montoPorcentaje.toFixed(2)}</span>
          </div>
          <div class="pricing-item total">
            <span>💰 PRECIO FINAL:</span>
            <span>$${montoFinal.toFixed(2)} USD</span>
          </div>
        </div>
      </div>
    `);
  };

  const copiarAlPortapapeles = () => {
    const parser = new DOMParser();
    const itineraryText = parser.parseFromString(output, 'text/html').body.textContent || '';
    const pricingText = parser.parseFromString(resultadoCalculadora, 'text/html').body.textContent || '';
    
    const textoACopiar = `
🎫 ITINERARIO DE VUELO
${itineraryText}

💰 COTIZACIÓN
${pricingText}

📞 Para más información contacta con nosotros
    `.trim();

    navigator.clipboard.writeText(textoACopiar)
      .then(() => alert('✅ ¡Texto copiado al portapapeles!'))
      .catch(() => alert('❌ Error al copiar. Inténtalo de nuevo.'));
  };

  const formatDate = (dateStr) => {
    const months = {
      JAN: 'enero', FEB: 'febrero', MAR: 'marzo', APR: 'abril',
      MAY: 'mayo', JUN: 'junio', JUL: 'julio', AUG: 'agosto',
      SEP: 'septiembre', OCT: 'octubre', NOV: 'noviembre', DEC: 'diciembre'
    };
    const day = dateStr.slice(0, 2);
    const monthCode = dateStr.slice(2, 5).toUpperCase();
    return `${day} de ${months[monthCode] || monthCode}`;
  };

  const formatTime = (timeStr) => {
    return timeStr.replace(/(\d{2})(\d{2})(\+\d)?/, "$1:$2");
  };

  // Parser SABRE mejorado con diseño visual
  const parseSabreEnhanced = (itinerary, airlinesData, airportsData) => {
    const flights = itinerary.split('\n').filter(line => line.trim() !== '');
    let output = '<div class="itinerary-container">';
    
    flights.forEach((flight, index) => {
      const match = flight.match(/^\s*(\d+)\s*([A-Z0-9]{2})\s*(\d+\s*[A-Z]*)\s+(\d{2}[A-Z]{3})\s+\w\s+(\w{3})(\w{3})\W.*?\s+(\d{4})\s+(\d{4})\s+(\d{2}[A-Z]{3})?.*$/);
      
      if (!match) {
        output += `<div class="error-card">❌ Formato incorrecto: "${flight}"</div>`;
        return;
      }

      const airlineCode = match[2];
      const flightNumber = match[3].trim();
      const departureDate = formatDate(match[4]);
      const originCode = match[5];
      const destCode = match[6];
      const departureTime = formatTime(match[7]);
      const arrivalTime = formatTime(match[8]);
      const arrivalDate = match[9] ? formatDate(match[9]) : departureDate;
      const isNextDay = match[9] && match[9] !== match[4];

      const airline = getAirlineInfo(airlineCode);
      const origin = getAirportInfo(originCode);
      const destination = getAirportInfo(destCode);
      const duration = calculateFlightDuration(match[7], match[8], !isNextDay);

      output += `
        <div class="flight-card">
          <div class="flight-header">
            <div class="airline-info">
              <img src="${airline.logo}" alt="${airline.name}" class="airline-logo" 
                   onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCA2NCA2NCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0IiByeD0iOCIgZmlsbD0iIzM3NDE1MSIvPgo8dGV4dCB4PSIzMiIgeT0iMzgiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZm9udC13ZWlnaHQ9ImJvbGQiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj4ke2FpcmxpbmVDb2RlfTwvdGV4dD4KPHN2Zz4='">
              <div class="flight-details">
                <h3 class="flight-number">${airlineCode} ${flightNumber}</h3>
                <p class="airline-name">${airline.name}</p>
              </div>
            </div>
            <div class="flight-duration">
              <span class="duration-badge">⏱️ ${duration}</span>
            </div>
          </div>
          
          <div class="route-container">
            <div class="airport departure">
              <div class="airport-code">${origin.code}</div>
              <div class="airport-name">${origin.name}</div>
              <div class="flight-time">
                <span class="time">${departureTime}</span>
                <span class="date">${departureDate}</span>
              </div>
            </div>
            
            <div class="flight-path">
              <div class="flight-line"></div>
              <div class="plane-icon">✈️</div>
            </div>
            
            <div class="airport arrival">
              <div class="airport-code">${destination.code}</div>
              <div class="airport-name">${destination.name}</div>
              <div class="flight-time">
                <span class="time">${arrivalTime}</span>
                <span class="date">${arrivalDate}${isNextDay ? ' (+1)' : ''}</span>
              </div>
            </div>
          </div>
          
          ${index < flights.length - 1 ? '<div class="connection-indicator">🔄 Conexión</div>' : ''}
        </div>
      `;
    });

    output += '</div>';
    return output;
  };

  // Parser Amadeus mejorado
  const parseAmadeusEnhanced = (itinerary, airlinesData, airportsData) => {
    const flights = itinerary.split('\n').filter(line => line.trim() !== '');
    let output = '<div class="itinerary-container amadeus-theme">';

    flights.forEach((flight, index) => {
      const match = flight.match(/^\s*(\d+)\s*([A-Z]{2})\s*(\d+[A-Z]*)\s+([A-Z])\s+([A-Z0-9]{5})\s+\w\s+(\w{3})(\w{3})\s+\S+(?:\s+\d+)?\s+(\d{4})\s+(\d{4})(?:\+(\d))?.*$/);
      
      if (!match) {
        output += `<div class="error-card">❌ Formato incorrecto: "${flight}"</div>`;
        return;
      }

      const airlineCode = match[2];
      const flightNumber = match[3];
      const departureDate = formatDate(match[5]);
      const originCode = match[6];
      const destCode = match[7];
      const departureTime = formatTime(match[8]);
      const arrivalTime = formatTime(match[9]);
      const isNextDay = match[10];

      const airline = getAirlineInfo(airlineCode);
      const origin = getAirportInfo(originCode);
      const destination = getAirportInfo(destCode);
      const duration = calculateFlightDuration(match[8], match[9], !isNextDay);

      output += `
        <div class="flight-card amadeus-card">
          <div class="flight-header">
            <div class="airline-info">
              <img src="${airline.logo}" alt="${airline.name}" class="airline-logo" 
                   onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCA2NCA2NCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0IiByeD0iOCIgZmlsbD0iIzAwOEI4QiIvPgo8dGV4dCB4PSIzMiIgeT0iMzgiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZm9udC13ZWlnaHQ9ImJvbGQiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj4ke2FpcmxpbmVDb2RlfTwvdGV4dD4KPHN2Zz4='">
              <div class="flight-details">
                <h3 class="flight-number">${airlineCode} ${flightNumber}</h3>
                <p class="airline-name">${airline.name}</p>
              </div>
            </div>
            <div class="flight-duration">
              <span class="duration-badge amadeus-badge">⏱️ ${duration}</span>
            </div>
          </div>
          
          <div class="route-container">
            <div class="airport departure">
              <div class="airport-code">${origin.code}</div>
              <div class="airport-name">${origin.name}</div>
              <div class="flight-time">
                <span class="time">${departureTime}</span>
                <span class="date">${departureDate}</span>
              </div>
            </div>
            
            <div class="flight-path amadeus-path">
              <div class="flight-line"></div>
              <div class="plane-icon">✈️</div>
            </div>
            
            <div class="airport arrival">
              <div class="airport-code">${destination.code}</div>
              <div class="airport-name">${destination.name}</div>
              <div class="flight-time">
                <span class="time">${arrivalTime}</span>
                <span class="date">${departureDate}${isNextDay ? ' (+1)' : ''}</span>
              </div>
            </div>
          </div>
          
          ${index < flights.length - 1 ? '<div class="connection-indicator amadeus-connection">🔄 Conexión</div>' : ''}
        </div>
      `;
    });

    output += '</div>';
    return output;
  };

  // Parser KIU mejorado
  const parseKiuEnhanced = (itinerary, airlinesData, airportsData) => {
    const flights = itinerary.split('\n').filter(line => line.trim() !== '');
    let output = '<div class="itinerary-container kiu-theme">';

    flights.forEach((flight, index) => {
      const match = flight.match(/^\s*(\d+)\s+([A-Z0-9]{2})\s*(\d+\s*[A-Z]*)\s+(\d{2}[A-Z]{3})\s+\w{2}\s+(\w{3})(\w{3})\s+.*?\s+(\d{4})\s+(\d{4})(\d{2}[A-Z]{3})?.*$/);
      
      if (!match) {
        output += `<div class="error-card">❌ Formato incorrecto: "${flight}"</div>`;
        return;
      }

      const airlineCode = match[2].trim();
      const flightNumber = match[3].replace(/\s+/g, '');
      const departureDate = formatDate(match[4]);
      const originCode = match[5];
      const destCode = match[6];
      const departureTime = formatTime(match[7]);
      const arrivalTime = formatTime(match[8]);
      const arrivalDate = match[9] ? formatDate(match[9]) : departureDate;
      const isNextDay = match[9] && match[9] !== match[4];

      const airline = getAirlineInfo(airlineCode);
      const origin = getAirportInfo(originCode);
      const destination = getAirportInfo(destCode);
      const duration = calculateFlightDuration(match[7], match[8], !isNextDay);

      output += `
        <div class="flight-card kiu-card">
          <div class="flight-header">
            <div class="airline-info">
              <img src="${airline.logo}" alt="${airline.name}" class="airline-logo" 
                   onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQiIGhlaWdodD0iNjQiIHZpZXdCb3g9IjAgMCA2NCA2NCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjY0IiBoZWlnaHQ9IjY0IiByeD0iOCIgZmlsbD0iIzBEMUU0MCIvPgo8dGV4dCB4PSIzMiIgeT0iMzgiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZm9udC13ZWlnaHQ9ImJvbGQiIGZpbGw9IndoaXRlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj4ke2FpcmxpbmVDb2RlfTwvdGV4dD4KPHN2Zz4='">
              <div class="flight-details">
                <h3 class="flight-number">${airlineCode} ${flightNumber}</h3>
                <p class="airline-name">${airline.name}</p>
              </div>
            </div>
            <div class="flight-duration">
              <span class="duration-badge kiu-badge">⏱️ ${duration}</span>
            </div>
          </div>
          
          <div class="route-container">
            <div class="airport departure">
              <div class="airport-code">${origin.code}</div>
              <div class="airport-name">${origin.name}</div>
              <div class="flight-time">
                <span class="time">${departureTime}</span>
                <span class="date">${departureDate}</span>
              </div>
            </div>
            
            <div class="flight-path kiu-path">
              <div class="flight-line"></div>
              <div class="plane-icon">✈️</div>
            </div>
            
            <div class="airport arrival">
              <div class="airport-code">${destination.code}</div>
              <div class="airport-name">${destination.name}</div>
              <div class="flight-time">
                <span class="time">${arrivalTime}</span>
                <span class="date">${arrivalDate}${isNextDay ? ' (+1)' : ''}</span>
              </div>
            </div>
          </div>
          
          ${index < flights.length - 1 ? '<div class="connection-indicator kiu-connection">🔄 Conexión</div>' : ''}
        </div>
      `;
    });

    output += '</div>';
    return output;
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>🎫 Traductor de Itinerarios Aéreos</h1>
        <p>Convierte texto de consola GDS en itinerarios profesionales</p>
      </header>

      <div className="main-content">
        {/* Sección del Traductor */}
        <div className="translator-section">
          <div className="input-section">
            <div className="gds-selector">
              <label>Sistema GDS:</label>
              <select
                value={selectedSystem}
                onChange={(e) => setSelectedSystem(e.target.value)}
                className="gds-select"
              >
                <option value="SABRE">🔴 SABRE</option>
                <option value="Amadeus">🟢 Amadeus</option>
                <option value="KIU">🔵 KIU</option>
              </select>
            </div>
            
            <textarea
              value={itinerary}
              onChange={(e) => setItinerary(e.target.value)}
              placeholder={`Pega aquí el texto del itinerario de ${selectedSystem}...`}
              className="itinerary-input"
              rows="8"
            />
            
            <button onClick={parseItinerary} className="translate-btn">
              🚀 Traducir Itinerario
            </button>
          </div>

          <div className="output-section">
            <div dangerouslySetInnerHTML={{ __html: output }} />
          </div>
        </div>

        {/* Sección de Calculadora */}
        <div className="calculator-section">
          <h2>💰 Calculadora de Precios</h2>
          <div className="calculator-grid">
            <div className="input-group">
              <label>Tarifa Base (USD)</label>
              <input
                type="number"
                value={cantidad1}
                onChange={(e) => setCantidad1(e.target.value)}
                placeholder="0.00"
                className="price-input"
              />
            </div>
            
            <div className="input-group">
              <label>Fee Consolidador (USD)</label>
              <input
                type="number"
                value={cantidad2}
                onChange={(e) => setCantidad2(e.target.value)}
                placeholder="0.00"
                className="price-input"
              />
            </div>
            
            <div className="input-group">
              <label>Fee Interno (USD)</label>
              <input
                type="number"
                value={cantidad3}
                onChange={(e) => setCantidad3(e.target.value)}
                placeholder="0.00"
                className="price-input"
              />
            </div>
            
            <div className="input-group">
              <label>Margen (%)</label>
              <input
                type="number"
                value={porcentaje}
                onChange={(e) => setPorcentaje(e.target.value)}
                placeholder="0"
                className="price-input"
              />
            </div>
          </div>
          
          <button onClick={calcularMonto} className="calculate-btn">
            🧮 Calcular Precio Final
          </button>
          
          <div dangerouslySetInnerHTML={{ __html: resultadoCalculadora }} />
        </div>

        {/* Botones de Acción */}
        <div className="action-buttons">
          <button onClick={copiarAlPortapapeles} className="copy-btn">
            📋 Copiar Todo al Portapapeles
          </button>
          
          <button 
            onClick={() => window.print()} 
            className="print-btn"
          >
            🖨️ Imprimir Itinerario
          </button>
        </div>
      </div>
    </div>
  );
}