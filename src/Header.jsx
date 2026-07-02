function TabButton({ active, onClick, children }) {
  // Definimos las clases base y las condicionales
  const baseClasses = "rounded-full px-5 py-2 text-sm font-medium tracking-wide transition-all duration-300";
  const activeClasses = "bg-teal-600 text-white shadow-lg shadow-teal-900/20";
  const inactiveClasses = "text-neutral-400 hover:text-neutral-100 hover:bg-neutral-800";

  return (
    <button
      onClick={onClick}
      className={`${baseClasses} ${active ? activeClasses : inactiveClasses}`}
    >
      {children}
    </button>
  );
}

export default function Header({ vista, setVista }) {
  return (
    <header className="flex items-center justify-between pb-8 px-10 border-b border-neutral-800 mb-2">
      <div className="flex items-center gap-3">
        {/* Logo */}
        <div className="w-12 h-12 rounded-full bg-teal-500/20 flex items-center justify-center border border-teal-500/30">
          <div className="w-6 h-6 rounded-full bg-teal-400" />
        </div>
        <h1 className="text-4xl font-bold text-white tracking-tight">AI FinOps Proxy</h1>
      </div>

      {/* Navegación */}
      <div className="flex gap-2 bg-neutral-900 p-1 rounded-full border border-neutral-800">
        <TabButton active={vista === 'analizador'} onClick={() => setVista('analizador')}>
          <p className="text-neutral-100 text-md">Analizador</p>
        </TabButton>
        <TabButton active={vista === 'historial'} onClick={() => setVista('historial')}>
          <p className="text-neutral-100 text-md">Historial</p>
        </TabButton>
        <TabButton active={vista === 'grafica'} onClick={() => setVista('grafica')}>
          <p className="text-neutral-100 text-md">Gráfica</p>
        </TabButton>
      </div>
    </header>
  );
}