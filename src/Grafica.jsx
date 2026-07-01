import { useState, useEffect } from 'react';

function GraficaGasto() {
  const [datos, setDatos] = useState([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    fetch(`http://127.0.0.1:8000/gasto-mensual`)
      .then(res => res.json())
      .then(data => {
        // SEGURIDAD 1: Forzamos estrictamente que sea un Array
        if (data && Array.isArray(data.gasto_mensual)) {
          setDatos(data.gasto_mensual);
        } else if (Array.isArray(data)) {
          setDatos(data);
        } else {
          setDatos([]);
        }
        setCargando(false);
      })
      .catch(err => {
        console.error("Error cargando los datos de la gráfica:", err);
        setDatos([]);
        setCargando(false);
      });
  }, []);
}

// ============================================================================
// 2. PANEL MIXTO: AHORROS (Izquierda) Y PREDICCIONES (Derecha)
// ============================================================================
function AnalisisMixto() {
  const [usuarios, setUsuarios] = useState([]);
  const [usuarioSeleccionado, setUsuarioSeleccionado] = useState('');
  
  const [datosAhorro, setDatosAhorro] = useState([]);
  const [datosGasto, setDatosGasto] = useState([]);

  // Fetch de Usuarios
  useEffect(() => {
    fetch(`http://127.0.0.1:8000/usuarios`)
      .then(res => res.json())
      .then(data => {
        if (data && Array.isArray(data.usuarios)) setUsuarios(data.usuarios);
        else if (Array.isArray(data)) setUsuarios(data);
      });
  }, []); 

  // Fetch de Ahorros
  useEffect(() => {
    if (usuarioSeleccionado) {
      fetch(`http://127.0.0.1:8000/ahorro-mensual/${usuarioSeleccionado}`)
        .then(res => res.json())
        .then(data => {
          console.log("📥 Datos crudos AHORRO desde FastAPI:", data); // ¡Míralo en F12!
          if (Array.isArray(data)) setDatosAhorro(data);
          else if (data && typeof data === 'object') setDatosAhorro([data]);
        });
    }
  }, [usuarioSeleccionado]);

  // Fetch de Gastos
  useEffect(() => {
    fetch(`http://127.0.0.1:8000/gasto-mensual`)
      .then(res => res.json())
      .then(data => {
        console.log("📥 Datos crudos GASTO desde FastAPI:", data); // ¡Míralo en F12!
        if (data && Array.isArray(data.gasto_mensual)) setDatosGasto(data.gasto_mensual);
        else if (Array.isArray(data)) setDatosGasto(data);
      });
  }, []);

  // --- PROCESAMIENTO INTELIGENTE (Busca múltiples nombres de variables por si acaso) ---
  const infoAhorro = datosAhorro.length > 0 ? datosAhorro[0] : {};
  
  // Extrae Ahorro
  const ahorro_mensual = Number(infoAhorro.ahorro_mensual || infoAhorro.ahorro || infoAhorro.total_ahorro) || 0;
  const porcentaje_ahorro = Number(infoAhorro.porcentaje_ahorro || infoAhorro.porcentaje) || 0;

  // Extrae Gasto
  const arrayGastoValido = Array.isArray(datosGasto) ? datosGasto : [];
  const infoGasto = arrayGastoValido.find(u => String(u.id) === String(usuarioSeleccionado)) || {};
  
  const gasto_mensual_actual = Number(infoGasto.gasto_mensual_actual || infoGasto.gasto_actual || infoGasto.coste_total) || 0;
  const limite_de_gasto = Number(infoGasto.limite_de_gasto || infoGasto.coste_maximo || infoGasto.limite_mensual || infoGasto.presupuesto) || 0;
  const porcentaje_gasto = Number(infoGasto.porcentaje_gasto || infoGasto.porcentaje_uso) || 0;

  // CÁLCULO PREDICCIÓN
  const hoy = new Date();
  const diaActual = hoy.getDate();
  const diasEnMes = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0).getDate();
  
  const prediccionEstimada = gasto_mensual_actual > 0 
    ? (gasto_mensual_actual / diaActual) * diasEnMes 
    : 0;

  const superaPresupuesto = limite_de_gasto > 0 && prediccionEstimada > limite_de_gasto;

  // CONFIGURACIÓN SVG
  const radius = 50;
  const circumference = 2 * Math.PI * radius;
  
  const porcentajeAhorroSeguro = Math.min(Math.max(porcentaje_ahorro, 0), 100);
  const strokeDashoffsetAhorro = circumference - (porcentajeAhorroSeguro / 100) * circumference;

  const porcentajeGastoSeguro = Math.min(Math.max(porcentaje_gasto, 0), 100);
  const strokeDashoffsetGasto = circumference - (porcentajeGastoSeguro / 100) * circumference;

  return (
    <div className="overflow-hidden rounded-md border border-neutral-800 bg-neutral-900 shadow-sm mt-8">
      <div className="h-1 w-full bg-gradient-to-r from-emerald-400 via-teal-400 to-rose-400" />
      
      <div className="flex flex-col gap-4 border-b border-neutral-800 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-lg font-semibold uppercase tracking-[0.15em] text-neutral-100">
          Métricas de Ahorro y Predicción
        </h2>
        
        <select 
          value={usuarioSeleccionado} 
          onChange={(e) => setUsuarioSeleccionado(e.target.value)}
          className="rounded-md border border-neutral-700 bg-neutral-950 py-2 pl-3 pr-9 text-md text-neutral-100 outline-none focus:border-teal-500 focus:ring-1 focus:ring-teal-500 transition-all cursor-pointer"
        >
          <option value="">Selecciona usuario...</option>
          {usuarios.map((u, i) => (
            <option className="text-md" key={u.id || i} value={u.id}>
              {u.tipo_consumidor || 'Usuario'} (ID: {u.id || i})
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2">
        
        {/* ================= AHORROS ================= */}
        <div className="flex flex-col border-b md:border-b-0 md:border-r border-neutral-800 p-8 gap-8 relative hover:bg-neutral-800/20 transition-colors">
          <div className="absolute top-4 left-6 flex items-center gap-2 opacity-50">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span className="text-xs uppercase tracking-widest text-emerald-400 font-semibold">/ahorro-mensual</span>
          </div>
          <h3 className="text-xl font-medium text-white text-center mt-4">Balance de Ahorro</h3>
          <div className="flex items-center justify-center">
            <div className="relative flex items-center justify-center">
              <svg width="140" height="140" className="transform -rotate-90">
                <circle cx="70" cy="70" r={radius} stroke="currentColor" strokeWidth="16" fill="transparent" className="text-neutral-800" />
                <circle cx="70" cy="70" r={radius} stroke="currentColor" strokeWidth="16" fill="transparent" strokeDasharray={circumference} strokeDashoffset={strokeDashoffsetAhorro} className="text-emerald-500 transition-all duration-1000 ease-in-out" />
              </svg>
              <div className="absolute flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-white">{porcentajeAhorroSeguro.toFixed(0)}%</span>
                <span className="text-[10px] text-neutral-400 uppercase tracking-widest mt-1">Ahorrado</span>
              </div>
            </div>
          </div>
          <div className="flex flex-col items-center text-center mt-2">
            <span className={`text-4xl font-bold font-mono ${usuarioSeleccionado ? 'text-emerald-400' : 'text-neutral-600'}`}>
              ${ahorro_mensual.toFixed(4)}
            </span>
            <span className="text-sm text-neutral-500 uppercase tracking-widest mt-2">USD Ahorrados este mes</span>
          </div>
        </div>

        {/* ================= PREDICCIONES ================= */}
        <div className="flex flex-col p-8 gap-8 relative hover:bg-neutral-800/20 transition-colors">
          <div className="absolute top-4 right-6 flex items-center gap-2 opacity-50">
            <span className="text-xs uppercase tracking-widest text-teal-400 font-semibold">/gasto-mensual</span>
            <span className="w-2 h-2 rounded-full bg-teal-500"></span>
          </div>
          <h3 className="text-xl font-medium text-white text-center mt-4">Predicción de Gasto</h3>
          <div className="flex items-center justify-center">
            <div className="relative flex items-center justify-center">
              <svg width="140" height="140" className="transform -rotate-90">
                <circle cx="70" cy="70" r={radius} stroke="currentColor" strokeWidth="16" fill="transparent" className="text-neutral-800" />
                <circle cx="70" cy="70" r={radius} stroke="currentColor" strokeWidth="16" fill="transparent" strokeDasharray={circumference} strokeDashoffset={strokeDashoffsetGasto} className={`${superaPresupuesto ? 'text-rose-500' : 'text-teal-400'} transition-all duration-1000 ease-in-out`} />
              </svg>
              <div className="absolute flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-white">{porcentajeGastoSeguro.toFixed(0)}%</span>
                <span className="text-[10px] text-neutral-400 uppercase tracking-widest mt-1">Consumido</span>
              </div>
            </div>
          </div>
          <div className="flex flex-col items-center text-center mt-2">
            <span className={`text-4xl font-bold font-mono ${!usuarioSeleccionado ? 'text-neutral-600' : (superaPresupuesto ? 'text-rose-400' : 'text-white')}`}>
              ${prediccionEstimada.toFixed(4)}
            </span>
            <span className="text-sm text-neutral-500 uppercase tracking-widest mt-2">USD Proyectados a fin de mes</span>
          </div>
          
          {usuarioSeleccionado !== '' && superaPresupuesto && limite_de_gasto > 0 && (
            <div className="absolute bottom-4 left-6 right-6 flex items-start gap-3 p-3 rounded-md bg-rose-500/10 border border-rose-500/20">
              <div className="text-rose-400 mt-0.5 animate-pulse">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                  <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                  <path d="M7.002 11a1 1 0 1 1 2 0 1 1 0 0 1-2 0zM7.1 4.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 4.995z"/>
                </svg>
              </div>
              <p className="text-xs text-rose-300/90 text-left">
                El ritmo de gasto actual causará que supere el límite mensual asignado de ${limite_de_gasto.toFixed(4)}.
              </p>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}

// ============================================================================
// 3. COMPONENTE PRINCIPAL MÁSTER
// ============================================================================
export default function Gastos() {
  return (
    <div className="space-y-6 px-30">
      
      <div className="space-y-2 mb-8">
        <h1 className="text-4xl font-semibold text-white">Análisis de Gastos y Ahorro</h1>
        <p className="text-xl text-neutral-400">Revisa el gasto mensual y el impacto del ahorro por usuario</p>
      </div>

      <GraficaGasto />
      <AnalisisMixto />

    </div>
  );
}