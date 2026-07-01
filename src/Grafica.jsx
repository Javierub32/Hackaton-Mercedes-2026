import { useState, useEffect } from 'react';

// ============================================================================
// 1. CÓDIGO DE TU COMPAÑERA
// ============================================================================
function GraficaGasto() {
  const [datos, setDatos] = useState([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    fetch(`http://127.0.0.1:8000/gasto-mensual`)
      .then(res => res.json())
      .then(data => {
        setDatos(data.gasto_mensual || []);
        setCargando(false);
      })
      .catch(err => {
        console.error("Error cargando los datos de la gráfica:", err);
        setCargando(false);
      });
  }, []);

  if (cargando) {
    return (
      <div className="w-full bg-neutral-900 border border-neutral-800 rounded-md p-6 flex justify-center items-center min-h-[250px]">
        <p className="text-neutral-500 text-sm uppercase tracking-wider animate-pulse">
          Cargando métricas...
        </p>
      </div>
    );
  }

  return (
    <div className="w-full bg-neutral-900 border border-neutral-800 rounded-md p-6 shadow-sm">
      <div className="border-b border-neutral-800 pb-3 mb-8 flex justify-between items-center">
        <h3 className="text-sm font-semibold uppercase tracking-[0.15em] text-neutral-100">
          Gasto mensual por usuario
        </h3>
      </div>

      <div className="relative flex justify-around items-end h-75 pt-2 pl-8">
        {datos.map((item) => {
          const altoBarra = item.porcentaje_gasto > 0 ? item.porcentaje_gasto : '2';

          return (
            <div key={item.id} className="flex flex-col items-center w-full max-w-[80px]">
              
              <span className="text-xs font-mono text-teal-400 mb-2">
                {item.porcentaje_gasto.toFixed(2)}%
              </span>
              
              <div className="w-full h-60 bg-neutral-950 rounded-t-md relative overflow-hidden border border-neutral-800 border-b-0">
                <div
                  className="absolute bottom-0 w-full bg-gradient-to-t from-sky-500 to-teal-400 transition-all duration-1000 ease-out rounded-t-sm"
                  style={{ height: altoBarra + '%' }}
                />
              </div>

              <span className="text-xs font-semibold text-neutral-400 uppercase tracking-wider mt-3 text-center w-full px-1">
                User {item.id}
              </span>
              <span className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider text-center w-full px-1"> 
                ({item.tipo_consumidor.replace('-', ' ')})
              </span>
              
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// 2. ANÁLISIS DE AHORRO (100% IDÉNTICO A LA LÓGICA DE TU HISTORIAL)
// ============================================================================
function AnalisisAhorro() {
  // Misma estructura de estados que usas en Historial.jsx
  const [usuarios, setUsuarios] = useState({ usuarios: [], total_usuarios: 0 });
  const [usuarioSeleccionado, setUsuarioSeleccionado] = useState('');
  
  // Guardamos los datos de ahorro directamente como vienen del fetch (una lista)
  const [datosAhorro, setDatosAhorro] = useState([]);

  // Fetch de usuarios calcado a tu Historial
  useEffect(() => {
    fetch(`http://127.0.0.1:8000/usuarios`)
      .then(res => res.json())
      .then(data => setUsuarios(data))
      .catch(err => console.error("Error cargando usuarios:", err));
  }, []); 

  // Fetch de datos calcado a tu Historial
  useEffect(() => {
    if (usuarioSeleccionado) {
      fetch(`http://127.0.0.1:8000/ahorro-mensual/${usuarioSeleccionado}`)
        .then(res => res.json())
        .then(data => setDatosAhorro(data))
        .catch(err => console.error("Error cargando ahorros:", err));
    } else {
      setDatosAhorro([]); // Si no hay usuario, limpiamos
    }
  }, [usuarioSeleccionado]);

  // Como database.py devuelve una lista [ { ahorro_mensual: X, porcentaje_ahorro: Y } ]
  // Nos quedamos de forma segura con el primer elemento (índice 0)
  const infoActual = datosAhorro && datosAhorro.length > 0 
    ? datosAhorro[0] 
    : { ahorro_mensual: 0, porcentaje_ahorro: 0 };

  // Buscamos el nombre del usuario para mostrarlo en el panel derecho
  const usuarioInfo = usuarios.usuarios.find(u => u.id.toString() === usuarioSeleccionado.toString());
  const nombreMostrar = usuarioInfo ? `${usuarioInfo.tipo_consumidor} (ID: ${usuarioInfo.id})` : 'Selecciona un usuario';

  // Variables para pintar el anillo SVG
  const porcentajeSeguro = Math.min(Math.max(infoActual.porcentaje_ahorro || 0, 0), 100);
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (porcentajeSeguro / 100) * circumference;

  return (
    <div className="overflow-hidden rounded-md border border-neutral-800 bg-neutral-900 shadow-sm mt-8">
      <div className="h-1 w-full bg-gradient-to-r from-emerald-400 via-teal-400 to-sky-400" />
      
      <div className="flex flex-col gap-4 border-b border-neutral-800 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-lg font-semibold uppercase tracking-[0.15em] text-neutral-100">
          Análisis de Ahorro
        </h2>
        
        {/* Desplegable IDÉNTICO a Historial.jsx */}
        <select 
          value={usuarioSeleccionado} 
          onChange={(e) => setUsuarioSeleccionado(e.target.value)}
          className="rounded-md border border-neutral-700 bg-neutral-950 py-2 pl-3 pr-9 text-md text-neutral-100 outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all cursor-pointer"
        >
          <option value="">Selecciona usuario...</option>
          {usuarios.usuarios.map((u) => (
            <option className="text-md" key={u.id} value={u.id}>
              {u.tipo_consumidor} (ID: {u.id})
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 p-8">
        
        {/* Anillo de progreso SVG */}
        <div className="flex flex-col items-center justify-center gap-6 border-b md:border-b-0 md:border-r border-neutral-800 pb-8 md:pb-0">
          <div className="relative flex items-center justify-center">
            <svg width="160" height="160" className="transform -rotate-90">
              <circle cx="80" cy="80" r={radius} stroke="currentColor" strokeWidth="20" fill="transparent" className="text-neutral-800" />
              <circle
                cx="80" cy="80" r={radius} stroke="currentColor" strokeWidth="20" fill="transparent"
                strokeDasharray={circumference} strokeDashoffset={strokeDashoffset}
                className="text-emerald-500 transition-all duration-1000 ease-in-out"
              />
            </svg>
            <div className="absolute flex flex-col items-center justify-center">
              <span className="text-2xl font-bold text-white">{porcentajeSeguro.toFixed(0)}%</span>
              <span className="text-xs text-neutral-400 uppercase tracking-widest mt-1">Ahorrado</span>
            </div>
          </div>

          <div className="flex flex-col gap-3 w-full max-w-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-sm bg-emerald-500" />
                <span className="text-neutral-300 text-sm">Ahorro logrado</span>
              </div>
              <span className="font-mono text-emerald-400">{porcentajeSeguro.toFixed(2)}%</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-sm bg-neutral-800 border border-neutral-600" />
                <span className="text-neutral-300 text-sm">Gasto realizado</span>
              </div>
              <span className="font-mono text-neutral-400">{(100 - porcentajeSeguro).toFixed(2)}%</span>
            </div>
          </div>
        </div>

        {/* Dato de Ahorro Central */}
        <div className="flex flex-col justify-center px-4">
          <h3 className="text-xl font-medium text-white mb-6 flex items-center justify-center md:justify-start gap-2">
            <span className="w-8 h-1 bg-emerald-500 rounded-full"></span>
            Balance de Ahorro
          </h3>
          
          <div className="space-y-6">
            <div className="bg-neutral-950/50 p-6 rounded-lg border border-neutral-800/50 flex flex-col items-center text-center">
              <p className="text-neutral-400 text-sm mb-1">Ahorro total acumulado este mes:</p>
              
              <p className={`text-lg mb-4 ${usuarioSeleccionado ? 'text-teal-300 font-semibold' : 'text-neutral-500 italic'}`}>
                {nombreMostrar}
              </p>
              
              <div className="flex flex-col items-center gap-1 mt-2">
                <span className="text-5xl font-bold font-mono text-emerald-400">
                  ${(infoActual.ahorro_mensual || 0).toFixed(4)}
                </span>
                <span className="text-sm text-neutral-500 uppercase tracking-widest mt-1">USD Ahorrados</span>
              </div>
            </div>

            {/* Mensaje inferior */}
            {usuarioSeleccionado !== '' && (
              <div className={`flex items-start gap-3 p-3 rounded-md border ${
                (infoActual.ahorro_mensual || 0) > 0 
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300/90' 
                  : 'bg-neutral-800/50 border-neutral-700 text-neutral-400'
              }`}>
                <div className="mt-0.5">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                    <path d="M7.002 11a1 1 0 1 1 2 0 1 1 0 0 1-2 0zM7.1 4.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 4.995z"/>
                  </svg>
                </div>
                <p className="text-sm">
                  {(infoActual.ahorro_mensual || 0) > 0 
                    ? `¡Buen trabajo! Este usuario ha ahorrado un total de $${infoActual.ahorro_mensual.toFixed(4)} USD respecto a su coste máximo permitido.`
                    : 'Este usuario no registra ahorros acumulados en este ciclo mensual.'}
                </p>
              </div>
            )}
          </div>
          
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// 3. COMPONENTE PRINCIPAL
// ============================================================================
export default function Gastos() {
  return (
    <div className="space-y-6 px-30">
      <div className="space-y-2 mb-8">
        <h1 className="text-4xl font-semibold text-white">Análisis de Gastos y Ahorro</h1>
        <p className="text-xl text-neutral-400">Revisa el gasto mensual y el impacto del ahorro por usuario</p>
      </div>

      <GraficaGasto />
      <AnalisisAhorro />
    </div>
  );
}