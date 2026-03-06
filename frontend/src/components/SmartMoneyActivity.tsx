import { RealTimeSignals } from '../types/market'
import { TrendingUp, TrendingDown, AlertTriangle, Activity } from 'lucide-react'

interface SmartMoneyActivityProps {
  signals?: RealTimeSignals
}

export default function SmartMoneyActivity({ signals }: SmartMoneyActivityProps) {

  const safeSignals = signals ?? {
    smart_money_signal: {
      signal: 'NO_ACTIVITY',
      action: 'WAIT_FOR_MARKET_DATA',
      activities: []
    }
  }

  const smartMoneySignal = safeSignals.smart_money_signal ?? {
    signal: 'NO_ACTIVITY',
    action: 'WAIT_FOR_MARKET_DATA',
    activities: []
  }

  const signal = smartMoneySignal.signal || 'NO_ACTIVITY'
  const action = smartMoneySignal.action || 'WAIT_FOR_MARKET_DATA'
  const activities = smartMoneySignal.activities ?? []

  const getSignalColor = (signal: string) => {
    if (signal.includes('BULLISH')) return 'text-green-400'
    if (signal.includes('BEARISH')) return 'text-red-400'
    return 'text-yellow-400'
  }

  const getSignalBgColor = (signal: string) => {
    if (signal.includes('BULLISH')) return 'bg-green-500/20 border-green-500/30'
    if (signal.includes('BEARISH')) return 'bg-red-500/20 border-red-500/30'
    return 'bg-yellow-500/20 border-yellow-500/30'
  }

  const getActivityIcon = (activity: string) => {
    if (activity.includes('BULLISH')) return <TrendingUp className="w-4 h-4" />
    if (activity.includes('BEARISH')) return <TrendingDown className="w-4 h-4" />
    if (activity.includes('TRAP')) return <AlertTriangle className="w-4 h-4" />
    return <Activity className="w-4 h-4" />
  }

  const getActivityColor = (activity: string) => {
    if (activity.includes('BULLISH')) return 'text-green-400 bg-green-500/20'
    if (activity.includes('BEARISH')) return 'text-red-400 bg-red-500/20'
    if (activity.includes('TRAP')) return 'text-yellow-400 bg-yellow-500/20'
    return 'text-gray-400 bg-gray-800'
  }

  const bullishCount = activities.filter(a => a.includes('BULLISH')).length
  const bearishCount = activities.filter(a => a.includes('BEARISH')).length

  return (
    <div className="metric-card">

      {/* Header */}

      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-semibold">Smart Money Activity</h3>

        <div className={`px-3 py-1 rounded-full border ${getSignalBgColor(signal)}`}>
          <span className={`text-sm font-medium ${getSignalColor(signal)}`}>
            {signal.replaceAll('_', ' ')}
          </span>
        </div>
      </div>

      {/* Main Signal */}

      <div className={`glass-morphism rounded-lg p-4 mb-6 border ${getSignalBgColor(signal)}`}>
        <div className="flex items-center justify-between">

          <div>
            <div className={`text-lg font-semibold ${getSignalColor(signal)}`}>
              {signal.replaceAll('_', ' ')}
            </div>

            <div className="text-sm text-muted-foreground">
              Recommended Action:
              <span className="font-medium ml-1">{action.replaceAll('_', ' ')}</span>
            </div>
          </div>

          <div className={`p-3 rounded-lg ${getSignalBgColor(signal)}`}>
            <div className={getSignalColor(signal)}>
              {getActivityIcon(signal)}
            </div>
          </div>

        </div>
      </div>

      {/* Activities */}

      <div className="space-y-3">
        <h4 className="text-sm font-medium text-muted-foreground">
          Detected Activities
        </h4>

        {activities.length === 0 ? (
          <div className="text-sm text-muted-foreground">
            No smart money activity detected
          </div>
        ) : (
          <div className="space-y-2">

            {activities.map((activity, index) => (

              <div
                key={index}
                className="flex items-center gap-3 p-2 rounded-lg glass-morphism"
              >

                <div className={`p-1.5 rounded ${getActivityColor(activity)}`}>
                  {getActivityIcon(activity)}
                </div>

                <div className="flex-1">
                  <div className="text-sm font-medium">
                    {activity.replaceAll('_', ' ')}
                  </div>
                </div>

              </div>

            ))}

          </div>
        )}

      </div>

      {/* Indicators */}

      <div className="mt-6 pt-6 border-t border-white/10">

        <h4 className="text-sm font-medium text-muted-foreground mb-3">
          Activity Indicators
        </h4>

        <div className="grid grid-cols-2 gap-4">

          <div className="text-center p-3 glass-morphism rounded-lg">
            <div className="text-2xl font-bold text-green-400">
              {bullishCount}
            </div>
            <div className="text-xs text-muted-foreground">
              Bullish Signals
            </div>
          </div>

          <div className="text-center p-3 glass-morphism rounded-lg">
            <div className="text-2xl font-bold text-red-400">
              {bearishCount}
            </div>
            <div className="text-xs text-muted-foreground">
              Bearish Signals
            </div>
          </div>

        </div>

      </div>

      {/* Interpretation */}

      <div className="mt-4 p-3 glass-morphism rounded-lg">

        <div className="text-xs text-muted-foreground">

          <div className="font-medium mb-1">
            Smart Money Interpretation
          </div>

          {signal.includes('BULLISH') && (
            <div>
              Institutional activity suggests bullish positioning with potential upside momentum.
            </div>
          )}

          {signal.includes('BEARISH') && (
            <div>
              Institutional activity suggests bearish positioning with potential downside pressure.
            </div>
          )}

          {signal.includes('MIXED') && (
            <div>
              Conflicting institutional signals detected. Wait for clearer confirmation.
            </div>
          )}

          {signal.includes('NO_ACTIVITY') && (
            <div>
              Minimal institutional activity detected. Market may be consolidating.
            </div>
          )}

        </div>

      </div>

    </div>
  )
}