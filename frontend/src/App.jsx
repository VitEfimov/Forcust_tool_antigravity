import React, { useState } from 'react'
import ModelStatus from './components/ModelStatus';
import AdvancedSimulationV2 from './components/AdvancedSimulationV2';
import ModelTraining from './components/ModelTraining';
import WalkForward from './components/WalkForward';
import './App.css';

import { LogProvider } from './context/LogContext';
import LogConsole from './components/LogConsole';

function App() {
  const [view, setView] = useState('models'); // Default to System Status

  return (
    <LogProvider>
      <div className="App">
        <div className="navbar">
          <a href="#" onClick={() => setView('models')}>System Status</a>
          <a href="#" onClick={() => setView('walk-forward')}>Walk-Forward</a>
          <a href="#" onClick={() => setView('simulation-v2')}>Advanced Simulation</a>
          <a href="#" onClick={() => setView('training')}>ML Training</a>
        </div>

        <div className="content">
          {view === 'models' && <ModelStatus />}
          {view === 'walk-forward' && <WalkForward />}
          {view === 'simulation-v2' && <AdvancedSimulationV2 />}
          {view === 'training' && <ModelTraining />}
        </div>

        <LogConsole />
      </div>
    </LogProvider>
  );
}

export default App
