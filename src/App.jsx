import { useState } from 'react';
import Header from './Header';
import Historial from './Historial';
import Peticion from './Peticion';

function App() {
  const [vista, setVista] = useState('analizador');

  return (
    <div className="min-h-screen w-full font-sans text-neutral-100 bg-neutral-950 p-6 md:p-8">
      <div className="flex flex-col h-full w-full gap-8">
        
        {/* Header (se ajusta automáticamente al ancho) */}
        <Header vista={vista} setVista={setVista} />
        {/* Main: Ocupa todo el espacio restante */}
        <main className="flex-1 w-full">
          {vista === 'analizador' ? <Peticion /> : <Historial />}
        </main>
      </div>
    </div>
  );
}

export default App;