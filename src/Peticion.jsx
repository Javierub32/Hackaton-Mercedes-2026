import { useState, useEffect } from 'react';
export default function Peticion() {
  const [prompt, setPrompt] = useState('');
  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);
  const [usuarios, setUsuarios] = useState({ usuarios: [], total_usuarios: 0 }); // Este es tu estado correcto
  const [usuarioSeleccionado, setUsuarioSeleccionado] = useState('');
  
    useEffect(() => {
      fetch(`http://127.0.0.1:8000/usuarios`)
        .then(res => res.json())
        .then(data => setUsuarios(data))
        .catch(err => console.error("Error cargando usuarios:", err));
    }, []); 

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setCargando(true);
    setError(null);
    setResultado(null);

    try {
      const API_URL = "https://javierub-hackathon.hf.space/generar";

      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ "prompt": prompt, "usuario_id": usuarioSeleccionado ? usuarioSeleccionado : " " }),
      });

      if (!response.ok) {
        throw new Error("Fallo en la comunicación con el servidor");
      }

      const data = await response.json();
      setResultado(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setCargando(false);
    }
  };

  return (
    <>
      {/* Cabecera */}
      <header className="text-center space-y-2">
        <h1 className="text-4xl font-bold text-slate-900">Asistente de Taller IA</h1>
        <p className="text-slate-500">Analiza reportes de clientes instantáneamente</p>
      </header>

      {/* Formulario */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">

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
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-2">
              Mensaje o email del cliente:
            </label>
            <textarea
              id="prompt"
              rows="4"
              className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
              placeholder="Ej: Hola, mi Clase C está echando humo blanco por el capó..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={cargando}
            />
          </div>

          <button
            type="submit"
            disabled={cargando || !prompt}
            className={`w-full py-3 px-4 rounded-xl text-white font-semibold transition-all ${cargando
                ? "bg-blue-300 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700 shadow-md hover:shadow-lg"
              }`}
          >
            {cargando ? "Analizando con IA..." : "Analizar Reporte"}
          </button>
        </form>
      </div>

      {/* Mensaje de Error */}
      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded-xl border border-red-200">
          <strong>Error: </strong> {error}
        </div>
      )}

      {/* Resultados Estructurados */}
      {resultado && (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 animate-fade-in">
          <h2 className="text-xl font-bold mb-4 border-b pb-2">Diagnóstico Estructurado</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div className="bg-gray-50 p-4 rounded-lg">
              <span className="text-xs text-gray-500 uppercase font-bold tracking-wider">Modelo Afectado</span>
              <p className="font-semibold text-lg">{resultado.modelo_coche}</p>
            </div>

            <div className="bg-gray-50 p-4 rounded-lg">
              <span className="text-xs text-gray-500 uppercase font-bold tracking-wider">Pieza / Sistema</span>
              <p className="font-semibold text-lg">{resultado.pieza_afectada}</p>
            </div>

            <div className={`p-4 rounded-lg border-l-4 ${resultado.nivel_urgencia === 'Alta' ? 'bg-red-50 border-red-500 text-red-800' : 'bg-yellow-50 border-yellow-500 text-yellow-800'}`}>
              <span className="text-xs uppercase font-bold tracking-wider opacity-75">Nivel de Urgencia</span>
              <p className="font-semibold text-lg">{resultado.nivel_urgencia}</p>
            </div>

            <div className={`p-4 rounded-lg border-l-4 ${resultado.requiere_grua ? 'bg-orange-50 border-orange-500 text-orange-800' : 'bg-green-50 border-green-500 text-green-800'}`}>
              <span className="text-xs uppercase font-bold tracking-wider opacity-75">¿Requiere Grúa?</span>
              <p className="font-semibold text-lg">{resultado.requiere_grua ? 'Sí, solicitar inmediatamente' : 'No es necesaria'}</p>
            </div>
          </div>

          <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
            <span className="text-xs text-blue-500 uppercase font-bold tracking-wider">Resumen Técnico para el Mecánico</span>
            <p className="mt-1 text-blue-900">{resultado.resumen_tecnico}</p>
          </div>
        </div>
      )}
    </>
  )
}