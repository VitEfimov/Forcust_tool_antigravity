import React, { useState } from 'react'
import ModelStatus from './components/ModelStatus';
import AdvancedSimulationV2 from './components/AdvancedSimulationV2';
import ModelTraining from './components/ModelTraining';
import WalkForward from './components/WalkForward';
import MarketOverview from './components/MarketOverview';
import DailyBriefing from './components/DailyBriefing';
import './App.css';

import { LogProvider } from './context/LogContext';
import LogConsole from './components/LogConsole';
import Analytics from './components/Analytics';
import Watchlist from './components/Watchlist';

function App() {
  const [view, setView] = useState('models'); // Default to System Status

  return (
    <LogProvider>
      <div className="App">
        <div className="navbar">
          <a href="#" onClick={() => setView('models')}>System Status</a>
          <a href="#" onClick={() => setView('market')}>Market Overview</a>
          <a href="#" onClick={() => setView('briefing')}>Daily Briefing</a>
          <a href="#" onClick={() => setView('walk-forward')}>Walk-Forward</a>
          <a href="#" onClick={() => setView('simulation-v2')}>Advanced Simulation</a>
          <a href="#" onClick={() => setView('training')}>ML Training</a>
          <a href="#" onClick={() => setView('analytics')}>Analytics</a>
          <a href="#" onClick={() => setView('wishlist')}>Wishlist</a>
        </div>

        <div className="content">
          {view === 'models' && <ModelStatus />}
          {view === 'market' && <MarketOverview />}
          {view === 'briefing' && <DailyBriefing />}
          {view === 'walk-forward' && <WalkForward />}
          {view === 'simulation-v2' && <AdvancedSimulationV2 />}
          {view === 'training' && <ModelTraining />}
          {view === 'analytics' && <Analytics />}
          {view === 'wishlist' && <Watchlist />}
        </div>

        <LogConsole />
      </div>
    </LogProvider>
  );
}

export default App
