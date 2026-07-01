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
                {Number(item.porcentaje_gasto).toFixed(2)}%
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
                {item.tipo_consumidor ? `(${item.tipo_consumidor.replace('-', ' ')})` : ''}
              </span>
              
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ============================================================================
// 2. AHORRO Y PREDICCIÓN (Con fetch integrado y predicción centrada)
// ============================================================================
function AhorroYPrediccion() {
  const [usuarioSeleccionado, setUsuarioSeleccionado] = useState('');
  const [usuarios, setUsuarios] = useState({ usuarios: [], total_usuarios: 0 });
  
  // Estados para los datos de las APIs
  const [datosAhorro, setDatosAhorro] = useState(null);
  const [datosPrediccion, setDatosPrediccion] = useState(null);

  // 1. Petición inicial de usuarios
  useEffect(() => {
    fetch(`http://127.0.0.1:8000/usuarios`)
      .then(res => res.json())
      .then(data => setUsuarios(data))
      .catch(err => console.error("Error cargando usuarios:", err));
  }, []); 

  // 2. Efecto para disparar los endpoints cuando se selecciona un usuario
  useEffect(() => {
    if (usuarioSeleccionado) {
      // Petición AHORRO (Lado Izquierdo)
      fetch(`http://127.0.0.1:8000/ahorro/${usuarioSeleccionado}`)
        .then(res => res.json())
        .then(data => setDatosAhorro(data))
        .catch(err => console.error("Error cargando ahorro:", err));

      // Petición PREDICCIÓN (Lado Derecho)
      fetch(`http://127.0.0.1:8000/prediccion/${usuarioSeleccionado}`)
        .then(res => res.json())
        .then(data => setDatosPrediccion(data))
        .catch(err => console.error("Error cargando predicción:", err));
    } else {
      setDatosAhorro(null);
      setDatosPrediccion(null);
    }
  }, [usuarioSeleccionado]);

  // --- EXTRACCIÓN DE DATOS ---
  // Ahorro (Izquierda)
  const infoAhorro = datosAhorro?.ahorros_mensuales?.[0] || { ahorro_mensual: 0, porcentaje_ahorro: 0 };
  const ahorroMensual = infoAhorro.ahorro_mensual || 0;
  const porcentajeAhorro = Math.min(Math.max(infoAhorro.porcentaje_ahorro || 0, 0), 100);

  // Predicción (Derecha)
  const prediccionEstimada = datosPrediccion?.proyeccion_fin_de_mes_usd || 0;
  const alertaPrediccion = datosPrediccion?.alerta || 'Sin datos';

  // Cálculos de la gráfica de anillo (Ahora representa el porcentaje de AHORRO)
  const radius = 60;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (porcentajeAhorro / 100) * circumference;

  return (
    <div className="overflow-hidden rounded-md border border-neutral-800 bg-neutral-900 shadow-sm mt-8">
      <div className="h-1 w-full bg-gradient-to-r from-sky-400 via-teal-400 to-emerald-400" />
      
      <div className="flex flex-col gap-4 border-b border-neutral-800 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-lg font-semibold uppercase tracking-[0.15em] text-neutral-100">
          Ahorro y Predicción
        </h2>
        
        {/* Desplegable idéntico al de Historial */}
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
        
        {/* LADO IZQUIERDO: Gráfico Circular de AHORRO */}
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
              <span className="text-2xl font-bold text-white">{porcentajeAhorro.toFixed(0)}%</span>
              <span className="text-[10px] text-neutral-400 uppercase tracking-widest mt-1">Ahorrado</span>
            </div>
          </div>

          <div className="flex flex-col gap-3 w-full max-w-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-sm bg-emerald-500" />
                <span className="text-neutral-300 text-sm">Dinero ahorrado</span>
              </div>
              <span className="font-mono text-emerald-400">${ahorroMensual.toFixed(4)}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-sm bg-neutral-800 border border-neutral-600" />
                <span className="text-neutral-300 text-sm">Gasto realizado</span>
              </div>
              <span className="font-mono text-neutral-400">{(100 - porcentajeAhorro).toFixed(0)}%</span>
            </div>
          </div>
        </div>

        {/* LADO DERECHO: Predicción de Gasto CENTRADA */}
        <div className="flex flex-col justify-center px-4 relative">
          <h3 className="text-xl font-medium text-white mb-6 flex items-center justify-center md:justify-start gap-2">
            <span className="w-8 h-1 bg-teal-500 rounded-full"></span>
            Predicción de Gasto
          </h3>
          
          <div className="space-y-6">
            <div className={`p-6 rounded-lg border flex flex-col items-center text-center transition-colors ${
              alertaPrediccion === 'Peligro' 
                ? 'bg-rose-500/10 border-rose-500/30' 
                : 'bg-neutral-950/50 border-neutral-800/50'
            }`}>
              
              {/* Etiqueta de mes o estado si hay datos */}
              {usuarioSeleccionado && (
                <span className={`text-xs uppercase tracking-widest font-semibold mb-2 ${
                  alertaPrediccion === 'Peligro' ? 'text-rose-400 animate-pulse' : 'text-sky-400'
                }`}>
                  Estado: {alertaPrediccion}
                </span>
              )}

              {/* Contenedor del precio centrado */}
              <div className="flex flex-col items-center gap-1 mt-2">
                <span className={`text-5xl font-bold font-mono ${
                  alertaPrediccion === 'Peligro' ? 'text-rose-400' : 'text-white'
                }`}>
                  ${prediccionEstimada.toFixed(4)}
                </span>
                <span className="text-sm text-neutral-500 uppercase tracking-widest mt-1">
                  USD estimados fin de mes
                </span>
              </div>

            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// 3. COMPONENTE PRINCIPAL (Gastos / Grafica)
// ============================================================================
export default function Gastos() {
  return (
    <div className="space-y-6 px-30">
      
      {/* Títulos generales de la vista */}
      <div className="space-y-2 mb-8">
        <h1 className="text-4xl font-semibold text-white">Análisis de Gastos</h1>
        <p className="text-xl text-neutral-400">Analiza el gasto mensual, ahorro y predicciones por usuario</p>
      </div>
<AhorroYPrediccion />
      <GraficaGasto />
      

    </div>
  );
}