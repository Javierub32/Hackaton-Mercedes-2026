import { useState, useEffect } from 'react';

export default function GraficaGasto() {
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