import { useState } from 'react';
import Header from './Header';
import Historial from './Historial';
import Peticion from './Peticion';
// IMPORTANTE: Lo importamos de tu archivo Grafica.jsx
import Gastos from './Grafica'; 

function App() {
  const [vista, setVista] = useState('analizador');

  return (
    <div className="min-h-screen w-full font-sans text-neutral-100 bg-neutral-950 p-6 md:p-8">
      <div className="flex flex-col h-full w-full gap-8">
        
        {/* Header controlado */}
        <Header vista={vista} setVista={setVista} />
        
        {/* Main con triple condición estricta */}
        <main className="flex-1 w-full">
          {vista === 'analizador' && <Peticion />}
          {vista === 'historial' && <Historial />}
          {/* Cambiado a 'grafica' para que coincida con el botón de tu Header */}
          {vista === 'grafica' && <Gastos />}
        </main>
        
      </div>
    </div>
  );
}

export default App;