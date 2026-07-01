import { useState, useEffect } from 'react';

export default function Peticion() {
  const [prompt, setPrompt] = useState('');
  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);
  const [usuarios, setUsuarios] = useState({ usuarios: [], total_usuarios: 0 });
  const [usuarioSeleccionado, setUsuarioSeleccionado] = useState('');
  
  useEffect(() => {
    fetch(`http://127.0.0.1:8000/usuarios`)
      .then(res => res.json())
      .then(data => setUsuarios(data))
      .catch(err => console.error("Error cargando usuarios:", err));
  }, []); 

  const renderTextWithBold = (text) => {
  if (!text) return null;
  const parts = text.split(/(\*\*.*?\*\*)/g);
  
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <b key={index}>{part.slice(2, -2)}</b>;
    }
    return <span key={index}>{part}</span>;
  });
};

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validación inicial
    if (!prompt.trim() || !usuarioSeleccionado) {
      setError("Por favor, ingresa un mensaje y selecciona un usuario.");
      return;
    }

    setCargando(true);
    setError(null);
    setResultado(null);

    try {
      // 1. Apuntar a la URL correcta del servidor FastAPI
      const API_URL = "http://127.0.0.1:8000/generar";

      const response = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        // 2. Parsear el usuario_id a número entero (Int) para que Pydantic lo valide bien
        body: JSON.stringify({ 
          prompt: prompt, 
          usuario_id: parseInt(usuarioSeleccionado, 10) 
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Fallo en la comunicación con el servidor");
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
        <h1 className="text-4xl font-bold text-slate-900">AI FinOps Proxy</h1>
        <p className="text-slate-500">Ejecuta consultas optimizando costes según el departamento</p>
      </header>

      {/* Formulario */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <div className="flex items-center gap-2 mb-4">
          <label className="text-sm text-gray-600 font-medium">Seleccionar usuario:</label>
          <select
            value={usuarioSeleccionado}
            onChange={(e) => setUsuarioSeleccionado(e.target.value)}
            className="p-2 border border-gray-300 rounded-lg bg-gray-50 focus:ring-2 focus:ring-blue-500 outline-none flex-grow"
          >
            <option value="">Selecciona un usuario / departamento...</option>
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
              Mensaje o Prompt:
            </label>
            <textarea
              id="prompt"
              rows="4"
              className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all"
              placeholder="Ej: Escribe un script en Python para calcular el factorial..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={cargando}
            />
          </div>

          <button
            type="submit"
            disabled={cargando || !prompt || !usuarioSeleccionado}
            className={`w-full py-3 px-4 rounded-xl text-white font-semibold transition-all ${
              (cargando || !prompt || !usuarioSeleccionado)
                ? "bg-blue-300 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700 shadow-md hover:shadow-lg"
              }`}
          >
            {cargando ? "Enrutando y analizando con IA..." : "Enviar Petición"}
          </button>
        </form>
      </div>

      {/* Mensaje de Error */}
      {error && (
        <div className="bg-red-50 text-red-600 p-4 rounded-xl border border-red-200 mt-6">
          <strong>Error: </strong> {error}
        </div>
      )}

      {/* Resultados Estructurados FinOps */}
      {resultado && (
        <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 mt-6 animate-fade-in">
          <h2 className="text-xl font-bold mb-4 border-b pb-2">Respuesta de la IA</h2>
          
          <div className="bg-gray-50 p-4 rounded-lg mb-6 whitespace-pre-wrap text-gray-800 border border-gray-200">
            <td className="p-3">{renderTextWithBold(resultado.respuesta_ia)}</td>
          </div>

          <h3 className="text-lg font-bold mb-4 border-b pb-2 text-indigo-600">FinOps Dashboard (Metadata)</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
              <span className="text-xs text-blue-500 uppercase font-bold tracking-wider">Modelo y Proveedor</span>
              <p className="font-semibold text-lg mt-1">{resultado.finops_metadata.ejecucion.modelo_usado}</p>
              <p className="text-sm text-blue-800">{resultado.finops_metadata.ejecucion.proveedor}</p>
            </div>

            <div className="bg-purple-50 p-4 rounded-lg border border-purple-100">
              <span className="text-xs text-purple-500 uppercase font-bold tracking-wider">Enrutamiento (Complejidad)</span>
              <p className="font-semibold text-lg mt-1 capitalize">{resultado.finops_metadata.enrutamiento.complejidad_detectada}</p>
              <p className="text-sm text-purple-800">{resultado.finops_metadata.enrutamiento.razonamiento_router}</p>
            </div>

            <div className="bg-green-50 p-4 rounded-lg border border-green-100">
              <span className="text-xs text-green-500 uppercase font-bold tracking-wider">Coste y Presupuesto</span>
              <p className="font-semibold text-lg mt-1">${resultado.finops_metadata.coste_real_usd.coste_total.toFixed(8)}</p>
              <p className="text-sm text-green-800">Límite Depto: ${resultado.finops_metadata.limite_presupuesto_aplicado}</p>
            </div>

            <div className="bg-orange-50 p-4 rounded-lg border border-orange-100">
              <span className="text-xs text-orange-500 uppercase font-bold tracking-wider">Consumo (Tokens)</span>
              <p className="font-semibold text-lg mt-1">{resultado.finops_metadata.ejecucion.tokens_totales} totales</p>
              <p className="text-sm text-orange-800">In: {resultado.finops_metadata.ejecucion.tokens_input} | Out: {resultado.finops_metadata.ejecucion.tokens_output}</p>
            </div>
          </div>

          {/* Mostrar recuadro si FinOps hizo un Downgrade Forzoso */}
          {resultado.finops_metadata.enrutamiento.intervencion_finops && (
            <div className="bg-red-50 p-4 rounded-lg border-l-4 border-red-500 text-red-800">
              <span className="text-xs uppercase font-bold tracking-wider opacity-75">Intervención FinOps Activa</span>
              <p className="font-semibold mt-1">{resultado.finops_metadata.enrutamiento.intervencion_finops}</p>
            </div>
          )}
        </div>
      )}
    </>
  )
}