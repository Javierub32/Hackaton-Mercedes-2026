import { useState, useEffect } from 'react';

export default function Historial() {
  const [datos, setDatos] = useState({ historial: [], total_peticiones: 0 });
  const [usuarios, setUsuarios] = useState({ usuarios: [], total_usuarios: 0 });
  const [usuarioSeleccionado, setUsuarioSeleccionado] = useState('');

  useEffect(() => {
    fetch(`http://127.0.0.1:8000/usuarios`)
      .then(res => res.json())
      .then(data => setUsuarios(data))
      .catch(err => console.error("Error cargando usuarios:", err));
  }, []); 

  useEffect(() => {
    if (usuarioSeleccionado) {
      fetch(`http://127.0.0.1:8000/historial/${usuarioSeleccionado}`)
        .then(res => res.json())
        .then(data => setDatos(data))
        .catch(err => console.error("Error cargando historial:", err));
    }
  }, [usuarioSeleccionado]);

  return (
    <div className="space-y-6 px-30">
      <div className="space-y-2">
        <h1 className="text-4xl font-semibold text-white">Historial de Usuario</h1>
        <p className="text-xl text-neutral-400">Revisa el historial de peticiones de cada uno de los usuarios</p>
      </div>

      <div className="overflow-hidden rounded-md border border-neutral-800 bg-neutral-900 shadow-sm">
        <div className="h-1 w-full bg-gradient-to-r from-sky-400 via-teal-400 to-emerald-400" />
        
        <div className="flex flex-col gap-4 border-b border-neutral-800 px-6 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <h2 className="text-md font-semibold uppercase tracking-[0.15em] text-neutral-100">Registro de peticiones</h2>
            <p className="text-md text-neutral-500">{datos.total_peticiones} petición(es)</p>
          </div>
          
          <select 
            value={usuarioSeleccionado} 
            onChange={(e) => setUsuarioSeleccionado(e.target.value)}
            className="rounded-md border border-neutral-700 bg-neutral-950 py-2 pl-3 pr-9 text-md text-neutral-100 outline-none"
          >
            <option value="">Selecciona usuario...</option>
            {usuarios.usuarios.map((u) => (
              <option className="text-md" key={u.id} value={u.id}>{u.tipo_consumidor} (ID: {u.id})</option>
            ))}
          </select>
        </div>

        <table className="w-full text-left text-md">
          <thead>
            <tr className="border-b border-neutral-800 bg-neutral-950/60 text-[11px] uppercase tracking-[0.12em] text-neutral-500">
              <th className="text-md px-6 py-3 font-semibold">ID Petición</th>
              <th className="text-md px-6 py-3 font-semibold">Fecha</th>
              <th className="text-md px-6 py-3 font-semibold">Tokens</th>
              <th className="text-md px-6 py-3 text-right font-semibold">Coste (USD)</th>
            </tr>
          </thead>
          <tbody>
            {datos.historial.map((p, index) => (
              <tr key={index} className="border-b border-neutral-800 hover:bg-neutral-800/50">
                <td className="px-6 py-3 text-neutral-100">{p.identificador}</td>
                <td className="px-6 py-3 text-neutral-400">{p.dia}</td>
                <td className="px-6 py-3 text-neutral-200">{p.tokens}</td>
                <td className="px-6 py-3 text-right font-mono text-teal-300">${p.coste_usd.toFixed(8)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}