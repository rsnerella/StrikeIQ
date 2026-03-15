// Component visibility debug script
// Run this in browser console to check if components are rendering

console.log("=== DASHBOARD COMPONENT VISIBILITY CHECK ===");

// Check if components are in DOM
setTimeout(() => {
  const components = [
    { name: 'MemoizedStrategyPlan', selector: () => document.querySelector('[data-testid="strategy-plan"]') },
    { name: 'MemoizedAIPanel', selector: () => document.querySelector('[data-testid="ai-panel"]') },
    { name: 'ChartIntelligencePanel', selector: () => document.querySelector('[data-testid="chart-intelligence"]') },
    { name: 'InstitutionalFlowPanel', selector: () => document.querySelector('[data-testid="institutional-flow"]') },
    { name: 'BiasPanel', selector: () => document.querySelector('[data-testid="bias-panel"]') },
    { name: 'SignalMatrixPanel', selector: () => document.querySelector('[data-testid="signal-matrix"]') },
    { name: 'TradeSetupPanel', selector: () => document.querySelector('[data-testid="trade-setup"]') },
    { name: 'VolatilityRegimePanel', selector: () => document.querySelector('[data-testid="volatility-regime"]') },
    { name: 'LiquidityVacuumPanel', selector: () => document.querySelector('[data-testid="liquidity-vacuum"]') },
    { name: 'MemoizedOIHeatmap', selector: () => document.querySelector('#oi-heatmap') }
  ];

  console.log("Checking component visibility...");
  
  components.forEach(({ name, selector }) => {
    const element = selector();
    if (element) {
      const isVisible = element.offsetParent !== null;
      const hasContent = element.innerHTML.length > 100; // Some content
      const displayStyle = window.getComputedStyle(element).display;
      
      console.log(`${name}:`, {
        visible: isVisible,
        hasContent,
        display: displayStyle,
        innerHTML: element.innerHTML.substring(0, 100) + '...'
      });
    } else {
      console.log(`${name}: NOT FOUND IN DOM`);
    }
  });
  
  // Check wsStore data
  if (typeof window !== 'undefined' && window.__ZUSTAND_STORE__) {
    const store = window.__ZUSTAND_STORE__;
    console.log("Store state:", {
      lastUpdate: store.getState().lastUpdate,
      chartAnalysis: store.getState().chartAnalysis,
      marketAnalysis: store.getState().marketAnalysis,
      hasChartData: !!store.getState().chartAnalysis,
      hasMarketData: !!store.getState().marketAnalysis
    });
  } else {
    console.log("Store not accessible");
  }
  
  console.log("=== END VISIBILITY CHECK ===");
}, 2000);
