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
        return <b key={index} className="text-neutral-100">{part.slice(2, -2)}</b>;
      }
      return <span key={index}>{part}</span>;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim() || !usuarioSeleccionado) {
      setError("Por favor, ingresa un mensaje y selecciona un usuario.");
      return;
    }

    setCargando(true);
    setError(null);
    setResultado(null);

    try {
      const API_URL = "http://127.0.0.1:8000/generar";
      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, usuario_id: parseInt(usuarioSeleccionado, 10) }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Fallo en la comunicación");
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
    <div className="space-y-8 px-30">
      {/* Cabecera */}
      <header className="space-y-1">
        <h1 className="text-4xl font-semibold text-white tracking-tight">Analizador de peticiones</h1>
        <p className="text-xl text-neutral-400">Configura tu consulta y optimiza costes.</p>
      </header>

      {/* Tarjeta Principal */}
      <div className="overflow-hidden rounded-md border border-neutral-800 bg-neutral-900 shadow-sm">
        <div className="h-1 w-full bg-gradient-to-r from-sky-400 via-teal-400 to-emerald-400" />

        <div className="px-6 py-5 border-b border-neutral-800">
          <h2 className="text-md font-semibold uppercase tracking-[0.15em] text-neutral-100">NUEVA PETICIÓN</h2>
        </div>

        <div className="p-6 space-y-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-md font-semibold tracking-[0.12em] text-neutral-400 mb-2">
                Usuario / Departamento
              </label>
              <select
                value={usuarioSeleccionado}
                onChange={(e) => setUsuarioSeleccionado(e.target.value)}
                className=" text-md w-full rounded-xl border border-neutral-700 bg-neutral-950 py-2.5 px-3 text-sm text-neutral-200 outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-400/30"
              >
                <option className="text-md" value="">Selecciona un usuario / departamento...</option>
                {usuarios.usuarios.map((u) => (
                  <option className="text-md" key={u.id} value={u.id}>{u.tipo_consumidor} (ID: {u.id})</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-md font-semibold tracking-[0.12em] text-neutral-400 mb-2">
                Mensaje o Prompt
              </label>
              <textarea
                rows="6"
                className="w-full p-3 bg-neutral-950 border border-neutral-700 rounded-md text-neutral-200 text-md outline-none focus:border-sky-400 focus:ring-1 focus:ring-sky-400/30"
                placeholder="Ej.: Escribe un script en Python para calcular el factorial..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
              />
            </div>

            <button
              type="submit"
              disabled={cargando}
              className="text-md w-full py-3 bg-neutral-800 hover:bg-neutral-700 text-white text-sm font-semibold uppercase tracking-wider transition-colors border border-neutral-700"
            >
              {cargando ? "Analizando..." : "Enviar Petición"}
            </button>
          </form>
        </div>
      </div>

      {/* Resultados */}
      {resultado && (
        <div className="space-y-6">
          <div className="bg-neutral-900 p-6 rounded-md border border-neutral-800">
            <h2 className="text-md font-semibold uppercase tracking-[0.15em] text-neutral-100 border-b border-neutral-800 pb-3 mb-4">Respuesta de la IA</h2>
            <div className="text-neutral-300 text-md whitespace-pre-wrap">{renderTextWithBold(resultado.respuesta_ia)}</div>
          </div>

          <h3 className="text-md font-semibold uppercase tracking-[0.15em] text-neutral-100 border-b border-neutral-800 pb-3 mt-6">FinOps Dashboard · Metadata</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Card Modelo */}
            <div className="border-t-4 border-teal-400 bg-neutral-900 p-4 border-x border-b">
              <p className="text-md text-neutral-500 uppercase tracking-wider">Modelo y Proveedor</p>
              <p className="text-md font-bold text-neutral-100 mt-1">{resultado.finops_metadata.ejecucion.modelo_usado}</p>
              <p className="text-md text-neutral-400">{resultado.finops_metadata.ejecucion.proveedor}</p>
            </div>
            {/* Card Enrutamiento */}
            <div className="border-t-4 border-teal-400 bg-neutral-900 p-4 border-x border-b">
              <p className="text-md text-neutral-500 uppercase tracking-wider">Enrutamiento (Complejidad)</p>
              <p className="text-md font-bold text-neutral-100 mt-1">{resultado.finops_metadata.enrutamiento.complejidad_detectada}</p>
              <p className="text-md text-neutral-400">{resultado.finops_metadata.enrutamiento.razonamiento_router}</p>
            </div>
            {/* Card Coste */}
            <div className="border-t-4 border-teal-400 bg-neutral-900 p-4 border-x border-b">
              <p className="text-md text-neutral-500 uppercase tracking-wider">Coste y Presupuesto</p>
              <p className="text-md font-bold text-neutral-100 mt-1">${resultado.finops_metadata.coste_real_usd.coste_total.toFixed(8)}</p>
              <p className="text-md text-neutral-400">Límite Depto: ${resultado.finops_metadata.limite_presupuesto_aplicado}</p>
            </div>
            {/* Card Consumo */}
            <div className="border-t-4 border-teal-400 bg-neutral-900 p-4 border-x border-b">
              <p className="text-md text-neutral-500 uppercase tracking-wider">Consumo (Tokens)</p>
              <p className="text-md font-bold text-neutral-100 mt-1">{resultado.finops_metadata.ejecucion.tokens_totales} totales</p>
              <p className="text-md text-neutral-400">In: {resultado.finops_metadata.ejecucion.tokens_input} | Out: {resultado.finops_metadata.ejecucion.tokens_output}</p>
            </div>
            {/*Latencia final*/}
            <div className="border-t-4 border-teal-400 bg-neutral-900 p-4 border-x border-b">
              <p className="text-md text-neutral-500 uppercase tracking-wider">Latencia (elección modelo)</p>
              <p className="text-md font-bold text-neutral-100 mt-1">{resultado.finops_metadata.latencia_ms.eleccion_de_modelo} ms</p>
            </div>
            {/* Latencia prediccion */}
            <div className="border-t-4 border-teal-400 bg-neutral-900 p-4 border-x border-b">
              <p className="text-md text-neutral-500 uppercase tracking-wider">Latencia (petición final)</p>
              <p className="text-md font-bold text-neutral-100 mt-1">{resultado.finops_metadata.latencia_ms.ejecucion_ia_y_db} ms</p>
            </div>
            {/* Ahorro estimado */}
            {resultado.finops_metadata.enrutamiento.complejidad_detectada === 'baja' ? (
              <div className="border-t-4 border-teal-400 bg-neutral-900 p-4 border-x border-b">
                <p className="text-md text-neutral-500 uppercase tracking-wider">Ahorro (Modelo Medio)</p>
                <p className="text-md font-bold text-neutral-100 mt-1">{resultado.finops_metadata.ahorro_usd["groq/llama-3.1-8b-instant"]}x más barato</p>
              </div>
            ) : null}
            {resultado.finops_metadata.enrutamiento.complejidad_detectada === 'baja' || resultado.finops_metadata.enrutamiento.complejidad_detectada === 'media' ? (
              <div className="border-t-4 border-teal-400 bg-neutral-900 p-4 border-x border-b">
                <p className="text-md text-neutral-500 uppercase tracking-wider">Ahorro (Modelo Alto)</p>
                <p className="text-md font-bold text-neutral-100 mt-1">{resultado.finops_metadata.ahorro_usd["groq/llama-3.3-70b-versatile"]}x más barato</p>
              </div>
            ) : null}
          </div>

          {/* Intervención */}
          {resultado.finops_metadata.enrutamiento.intervencion_finops && (
            <div className="border-l-4 border-red-500 bg-neutral-900 p-4 border-y border-r mt-4">
              <p className="text-md text-red-500 uppercase font-bold tracking-wider">Intervención FinOps Activa</p>
              <p className="text-md text-neutral-200 mt-1">{resultado.finops_metadata.enrutamiento.intervencion_finops}</p>
            </div>
          )}
        </div>
      )}
      {error && (
        <div className="bg-red-500 text-white p-4 rounded-md mt-6 shadow-md border border-red-700">
          <p className="text-lg font-semibold">Error:</p>
          <p>{error}</p>
        </div>
      )}
    </div>
  );
}