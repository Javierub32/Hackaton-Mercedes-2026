import { useState } from 'react';
import Historial from './Historial';
import Peticion from './Peticion';

function App() {
  const [vista, setVista] = useState('analizador');

  return (
    <div className="min-h-screen p-8 font-sans text-gray-800">
      <div className="max-w-3xl mx-auto space-y-8">
        
        {/* Menú de Navegación */}
        <div className="flex gap-4 justify-center mb-8">
          <button 
            onClick={() => setVista('analizador')}
            className={`px-6 py-2 rounded-full font-semibold transition-all ${
              vista === 'analizador' ? 'bg-blue-600 text-white shadow-md' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Analizador
          </button>
          <button 
            onClick={() => setVista('historial')}
            className={`px-6 py-2 rounded-full font-semibold transition-all ${
              vista === 'historial' ? 'bg-blue-600 text-white shadow-md' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            Historial
          </button>
        </div>

        {vista === 'analizador' ? (
          <Peticion />
        ) : (
          <Historial />
        )}

      </div>
    </div>
  );
}

export default App;