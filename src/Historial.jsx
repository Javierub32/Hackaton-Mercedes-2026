import { useState, useEffect } from 'react';

export default function Historial() {
  const [datos, setDatos] = useState({ historial: [], total_peticiones: 0 });
  const [usuarios, setUsuarios] = useState({ usuarios: [], total_usuarios: 0 }); // Este es tu estado correcto
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
    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 mt-8">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold">Historial de Usuario</h2>
        
        <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600">Seleccionar usuario:</label>
            <select 
              value={usuarioSeleccionado} 
              onChange={(e) => setUsuarioSeleccionado(e.target.value)}
              className="p-2 border rounded-lg bg-gray-50 focus:ring-2 focus:ring-blue-500 outline-none"
            >
              <option value="">Selecciona un usuario...</option>
              {usuarios.usuarios.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.tipo_consumidor} (ID: {u.id})
                </option>
              ))}
            </select>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b text-gray-500 text-sm">
              <th className="p-3">ID Petición</th>
              <th className="p-3">Fecha</th>
              <th className="p-3">Tokens</th>
              <th className="p-3 text-right">Coste (USD)</th>
            </tr>
          </thead>
          <tbody>
            {/* Validamos que datos.historial exista antes de mapear */}
            {datos.historial && datos.historial.map((p, index) => (
              <tr key={index} className="border-b hover:bg-gray-50 transition-colors">
                <td className="p-3 font-medium">{p.identificador}</td>
                <td className="p-3 text-gray-600">{p.dia}</td>
                <td className="p-3">{p.tokens}</td>
                <td className="p-3 text-right font-mono">${p.coste_usd.toFixed(8)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}