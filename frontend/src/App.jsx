import React, { useState } from 'react'
import Dashboard from './components/Dashboard';
import MarketOverview from './components/MarketOverview';
import ModelStatus from './components/ModelStatus';
import Watchlist from './components/Watchlist';
import AdvancedSimulationV2 from './components/AdvancedSimulationV2';
import ModelTraining from './components/ModelTraining';
import WalkForward from './components/WalkForward';
import './App.css';

import { LogProvider } from './context/LogContext';
import LogConsole from './components/LogConsole';

function App() {
  const [view, setView] = useState('dashboard');

  return (
    <LogProvider>
      <div className="App">
        <div className="navbar">
          <a href="#" onClick={() => setView('dashboard')}>Dashboard</a>
          <a href="#" onClick={() => setView('overview')}>Market Overview</a>
          <a href="#" onClick={() => setView('watchlist')}>My Watchlist</a>
          <a href="#" onClick={() => setView('simulation-v2')}>Advanced Simulation</a>
          <a href="#" onClick={() => setView('walk-forward')}>Walk-Forward</a>
          <a href="#" onClick={() => setView('training')}>ML Training</a>
          <a href="#" onClick={() => setView('models')}>System Status</a>
        </div>

        <div className="content">
          {view === 'dashboard' && <Dashboard />}
          {view === 'overview' && <MarketOverview />}
          {view === 'watchlist' && <Watchlist />}
          {view === 'simulation-v2' && <AdvancedSimulationV2 />}
          {view === 'walk-forward' && <WalkForward />}
          {view === 'training' && <ModelTraining />}
          {view === 'models' && <ModelStatus />}
        </div>

        <LogConsole />
      </div>
    </LogProvider>
  );
}

export default App

