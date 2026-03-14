# StrikeIQ System Architecture Diagrams

**Real-Time Options Analytics & AI-Driven Trading Intelligence Platform**

---

## 1️⃣ High-Level System Architecture

```mermaid
graph TB
    subgraph "External Data Sources"
        U[Upstox WebSocket Feed]
        API[Upstox REST API]
    end
    
    subgraph "Data Ingestion Layer"
        PD[Protobuf Decoder]
        MFE[MarketFeedEngine]
        TP[Tick Processor]
        TQ[Tick Queue]
    end
    
    subgraph "Market Processing Layer"
        OCB[OptionChainBuilder]
        MR[MessageRouter]
        CB[CandleBuilder]
        SE[SnapshotEngine]
    end
    
    subgraph "Analytics Layer"
        GE[GreeksEngine]
        IFE[InstitutionalFlowEngine]
        OHE[OIHeatmapEngine]
        STE[StructureEngine]
        RE[RegimeEngine]
        EME[ExpectedMoveEngine]
    end
    
    subgraph "Feature Engineering Layer"
        FB[FeatureBuilder]
        FV[Feature Vectors]
    end
    
    subgraph "AI/ML Layer"
        AIO[AIOrchestrator]
        PE[ProbabilityEngine]
        LE[LearningEngine]
        MLT[MLTrainingEngine]
    end
    
    subgraph "Strategy Layer"
        SRE[StrategyEngine]
        TDE[TradeDecisionEngine]
        SPE[StrategyPlanningEngine]
        SSE[StrikeSelectionEngine]
    end
    
    subgraph "Risk Management Layer"
        RKE[RiskEngine]
        PS[PositionSizing]
        SLE[StopLossEngine]
    end
    
    subgraph "Execution/Simulation Layer"
        PTE[PaperTradeEngine]
        ST[SignalTracker]
        OT[OutcomeTracker]
    end
    
    subgraph "Learning/Feedback Layer"
        LE2[LearningEngine]
        SOP[SignalOutcomeProcessor]
    end
    
    subgraph "Data Storage Layer"
        PG[(PostgreSQL)]
        R[(Redis Cache)]
    end
    
    subgraph "Real-Time Delivery Layer"
        AB[AnalyticsBroadcaster]
        WSM[WebSocketManager]
    end
    
    subgraph "Frontend"
        UI[React Dashboard]
        WS[WebSocket Client]
    end
    
    %% Data Flows
    U --> PD
    PD --> TQ
    TQ --> MFE
    MFE --> TP
    TP --> OCB
    TP --> CB
    OCB --> MR
    MR --> GE
    MR --> IFE
    MR --> OHE
    MR --> STE
    MR --> RE
    MR --> EME
    
    GE --> FB
    IFE --> FB
    OHE --> FB
    STE --> FB
    RE --> FB
    EME --> FB
    
    FB --> FV
    FV --> PE
    PE --> AIO
    AIO --> SRE
    SRE --> TDE
    TDE --> RKE
    RKE --> PTE
    
    PTE --> ST
    ST --> OT
    OT --> SOP
    SOP --> LE2
    LE2 --> MLT
    
    MR --> AB
    AIO --> AB
    SRE --> AB
    AB --> WSM
    WSM --> WS
    WS --> UI
    
    OCB --> PG
    SE --> PG
    PE --> PG
    AIO --> PG
    PTE --> PG
    
    FB --> R
    PE --> R
    AIO --> R
    
    classDef dataLayer fill:#e1f5fe
    classDef processingLayer fill:#f3e5f5
    classDef analyticsLayer fill:#e8f5e8
    classDef aiLayer fill:#fff3e0
    classDef strategyLayer fill:#fce4ec
    classDef riskLayer fill:#ffebee
    classDef storageLayer fill:#f1f8e9
    classDef deliveryLayer fill:#e0f2f1
    
    class U,API dataLayer
    class PD,MFE,TP,TQ processingLayer
    class OCB,MR,CB,SE processingLayer
    class GE,IFE,OHE,STE,RE,EME analyticsLayer
    class FB,FV aiLayer
    class AIO,PE,LE,MLT aiLayer
    class SRE,TDE,SPE,SSE strategyLayer
    class RKE,PS,SLE riskLayer
    class PTE,ST,OT riskLayer
    class LE2,SOP aiLayer
    class PG,R storageLayer
    class AB,WSM,WS,UI deliveryLayer
```

### Explanation
This high-level architecture shows the complete StrikeIQ system from data ingestion to frontend delivery. The flow moves from left to right through distinct layers, each with specific responsibilities. The color coding helps identify different functional areas: data sources (blue), processing (purple), analytics (green), AI/ML (orange), strategy (pink), risk (red), storage (light green), and delivery (teal).

---

## 2️⃣ Real-Time Data Flow Diagram

```mermaid
sequenceDiagram
    participant UF as Upstox Feed
    participant PD as Protobuf Decoder
    participant MFE as MarketFeedEngine
    participant OCB as OptionChainBuilder
    participant AB as AnalyticsBroadcaster
    participant UI as Frontend Dashboard
    
    Note over UF,UI: Real-Time Market Data Processing (Sub-second)
    
    loop Continuous Feed
        UF->>PD: Binary protobuf messages
        PD->>PD: Decode to structured data
        PD->>MFE: Parsed market ticks
        MFE->>MFE: Process & normalize ticks
        MFE->>OCB: Update option chain data
        OCB->>OCB: Build real-time option chain
        OCB->>AB: Chain update events
        AB->>AB: Broadcast to subscribers
        AB->>UI: WebSocket push
    end
    
    Note over UF,UI: Analytics Processing (Every 500ms)
    
    loop Analytics Updates
        OCB->>GE: Market data for Greeks
        OCB->>IFE: OI data for flow analysis
        OCB->>STE: Price data for structure
        GE->>AB: Greeks calculations
        IFE->>AB: Institutional flow signals
        STE->>AB: Structure analysis
        AB->>UI: Live analytics updates
    end
    
    Note over UF,UI: AI Processing (Every 1-2 seconds)
    
    loop AI Decision Pipeline
        FB->>PE: Feature vectors
        PE->>PE: XGBoost predictions
        PE->>AIO: Probability outputs
        AIO->>SRE: Strategy recommendations
        SRE->>AB: Trading signals
        AB->>UI: AI-powered insights
    end
```

### Explanation
This sequence diagram illustrates the real-time data flow through the StrikeIQ system. The process operates at different frequencies: market data updates continuously (sub-second), analytics calculations every 500ms, and AI decisions every 1-2 seconds. The diagram shows how raw market data flows through processing layers, gets enriched with analytics, and finally delivers AI-powered insights to the frontend via WebSocket connections.

---

## 3️⃣ AI Decision Pipeline

```mermaid
flowchart TD
    subgraph "Feature Generation"
        MD[Market Data]
        AD[Analytics Data]
        FB[FeatureBuilder]
        FV[Feature Vectors]
    end
    
    subgraph "ML Prediction"
        PE[ProbabilityEngine]
        XGB[XGBoost Model]
        PROB[Prediction Probabilities]
    end
    
    subgraph "AI Orchestration"
        AIO[AIOrchestrator]
        CONF[Confidence Scoring]
        RISK[Risk Assessment]
    end
    
    subgraph "Strategy Generation"
        SRE[StrategyEngine]
        STRAT[Trading Strategies]
        POS[Position Sizing]
    end
    
    subgraph "Decision Output"
        SIGNAL[Trading Signal]
        META[Metadata]
        UI[Dashboard Display]
    end
    
    MD --> FB
    AD --> FB
    FB --> FV
    FV --> PE
    PE --> XGB
    XGB --> PROB
    PROB --> AIO
    AIO --> CONF
    AIO --> RISK
    CONF --> SRE
    RISK --> SRE
    SRE --> STRAT
    STRAT --> POS
    POS --> SIGNAL
    SIGNAL --> META
    META --> UI
    
    %% Feature Details
    subgraph "Feature Categories"
        PCR[Put-Call Ratio]
        GAMMA[Gamma Exposure]
        OIV[OI Velocity]
        VOL[Volatility Regime]
        LIQ[Liquidity Zones]
        TREND[Trend Strength]
    end
    
    %% Strategy Types
    subgraph "Strategy Types"
        LC[Long Call]
        CS[Credit Spread]
        IC[Iron Condor]
        BT[Breakout Trade]
        MR[Mean Reversion]
    end
    
    FB --> PCR
    FB --> GAMMA
    FB --> OIV
    FB --> VOL
    FB --> LIQ
    FB --> TREND
    
    STRAT --> LC
    STRAT --> CS
    STRAT --> IC
    STRAT --> BT
    STRAT --> MR
    
    classDef featureBox fill:#e3f2fd
    classDef mlBox fill:#f1f8e9
    classDef aiBox fill:#fff3e0
    classDef strategyBox fill:#fce4ec
    classDef outputBox fill:#e0f2f1
    
    class MD,AD,FB,FV,PCR,GAMMA,OIV,VOL,LIQ,TREND featureBox
    class PE,XGB,PROB mlBox
    class AIO,CONF,RISK aiBox
    class SRE,STRAT,POS,LC,CS,IC,BT,MR strategyBox
    class SIGNAL,META,UI outputBox
```

### Explanation
The AI Decision Pipeline shows how raw market data transforms into actionable trading signals. The process starts with feature generation, where market and analytics data are converted into ML-ready feature vectors. These features feed into the XGBoost model for probability prediction, which then passes to the AI Orchestrator for confidence scoring and risk assessment. Finally, the Strategy Engine generates specific trading recommendations with appropriate position sizing.

---

## 4️⃣ ML Training Pipeline

```mermaid
flowchart LR
    subgraph "Data Collection"
        HMD[Historical Market Data]
        HSO[Historical Signal Outcomes]
        HF[Historical Features]
    end
    
    subgraph "Data Processing"
        DC[Data Cleaner]
        FS[Feature Selector]
        DS[Dataset Splitter]
        TR[Training Set]
        TE[Test Set]
        VAL[Validation Set]
    end
    
    subgraph "Model Training"
        XGB_TRAIN[XGBoost Training]
        HP[Hyperparameter Tuning]
        CV[Cross Validation]
        BM[Best Model]
    end
    
    subgraph "Model Evaluation"
        ME[Model Evaluation]
        PERF[Performance Metrics]
        ACC[Accuracy Score]
        PRE[Precision]
        REC[Recall]
        F1[F1 Score]
    end
    
    subgraph "Model Deployment"
        MDL[Model Registry]
        DEPLOY[Model Deployment]
        MON[Performance Monitoring]
        RETRAIN[Retraining Trigger]
    end
    
    HMD --> DC
    HSO --> DC
    HF --> DC
    DC --> FS
    FS --> DS
    DS --> TR
    DS --> TE
    DS --> VAL
    
    TR --> XGB_TRAIN
    VAL --> XGB_TRAIN
    XGB_TRAIN --> HP
    HP --> CV
    CV --> BM
    
    BM --> ME
    TE --> ME
    ME --> PERF
    PERF --> ACC
    PERF --> PRE
    PERF --> REC
    PERF --> F1
    
    BM --> MDL
    MDL --> DEPLOY
    DEPLOY --> MON
    MON --> RETRAIN
    RETRAIN --> DC
    
    %% Performance Metrics Details
    subgraph "Performance Metrics"
        ROC[ROC-AUC]
        LOSS[Log Loss]
        CALIB[Calibration Error]
        BIAS[Model Bias]
    end
    
    PERF --> ROC
    PERF --> LOSS
    PERF --> CALIB
    PERF --> BIAS
    
    classDef dataBox fill:#e3f2fd
    classDef processBox fill:#f3e5f5
    classDef trainBox fill:#e8f5e8
    classDef evalBox fill:#fff3e0
    classDef deployBox fill:#fce4ec
    
    class HMD,HSO,HF,DC,FS,DS,TR,TE,VAL dataBox
    class XGB_TRAIN,HP,CV,BM trainBox
    class ME,PERF,ACC,PRE,REC,F1,ROC,LOSS,CALIB,BIAS evalBox
    class MDL,DEPLOY,MON,RETRAIN deployBox
```

### Explanation
The ML Training Pipeline illustrates the complete machine learning lifecycle for StrikeIQ. It starts with data collection from historical market data, signal outcomes, and features. The data undergoes cleaning, feature selection, and splitting into training/validation/test sets. The XGBoost model is trained with hyperparameter tuning and cross-validation. Performance is evaluated using multiple metrics before the best model is deployed to production. Continuous monitoring triggers retraining when performance degrades.

---

## 5️⃣ Backend Module Structure

```mermaid
graph TB
    subgraph "Backend Application (FastAPI)"
        subgraph "app/"
            subgraph "analytics/"
                IFE[institutional_flow_engine.py]
                RE[regime_engine.py]
                STE[structure_engine.py]
                GE[greeks_engine.py]
                OHE[oi_heatmap_engine.py]
                EME[expected_move_engine.py]
            end
            
            subgraph "ai/"
                AIO[ai_orchestrator.py]
                PE[probability_engine.py]
                LE[learning_engine.py]
                ALE[adaptive_learning_engine.py]
                MLT[ml_training_engine.py]
            end
            
            subgraph "strategies/"
                SRE[strategy_engine.py]
                TDE[trade_decision_engine.py]
                SSE[strike_selection_engine.py]
                SPE[strategy_planning_engine.py]
                ASE[advanced_strategies_engine.py]
            end
            
            subgraph "risk/"
                RKE[risk_engine.py]
                SHE[stoploss_hunt_engine.py]
                PSE[position_sizing_engine.py]
            end
            
            subgraph "core/"
                subgraph "market_data/"
                    MFE[market_feed_engine.py]
                end
                subgraph "features/"
                    FB[feature_builder.py]
                end
                subgraph "infrastructure/"
                    AB[analytics_broadcaster.py]
                end
            end
            
            subgraph "services/"
                CPE[candle_pattern_engine.py]
                MBE[market_bias_engine.py]
                LAE[live_analytics_engine.py]
                PTE[paper_trade_engine.py]
                SSO[snapshot_engine.py]
            end
            
            subgraph "engines/"
                DSE[dealer_gamma_engine.py]
                GSE[gamma_squeeze_engine.py]
                LQE[liquidity_engine.py]
                OTE[options_trade_engine.py]
            end
        end
        
        subgraph "API Layer"
            WS[websocket_market_feed.py]
            APIV[api_endpoints.py]
            AUTH[auth_middleware.py]
        end
        
        subgraph "Database Layer"
            MODELS[database_models.py]
            MIGRATIONS[migrations/]
            QUERIES[database_queries.py]
        end
    end
    
    subgraph "External Dependencies"
        UPSTOX[upstox_client.py]
        REDIS[redis_client.py]
        CONFIG[config.py]
        LOGGER[logging_config.py]
    end
    
    %% Module Dependencies
    IFE --> FB
    RE --> FB
    STE --> FB
    GE --> FB
    OHE --> FB
    EME --> FB
    
    FB --> PE
    PE --> AIO
    AIO --> SRE
    SRE --> RKE
    RKE --> PTE
    
    MFE --> IFE
    MFE --> GE
    MFE --> STE
    
    AB --> WS
    WS --> UI
    
    classDef analyticsModule fill:#e8f5e8
    classDef aiModule fill:#fff3e0
    classDef strategyModule fill:#fce4ec
    classDef riskModule fill:#ffebee
    classDef coreModule fill:#e3f2fd
    classDef serviceModule fill:#f5f5f5
    classDef engineModule fill:#f9fbe7
    classDef apiModule fill:#e0f2f1
    classDef dbModule fill:#f1f8e9
    
    class IFE,RE,STE,GE,OHE,EME analyticsModule
    class AIO,PE,LE,ALE,MLT aiModule
    class SRE,TDE,SSE,SPE,ASE strategyModule
    class RKE,SHE,PSE riskModule
    class MFE,FB,AB coreModule
    class CPE,MBE,LAE,PTE,SSO serviceModule
    class DSE,GSE,LQE,OTE engineModule
    class WS,APIV,AUTH apiModule
    class MODELS,MIGRATIONS,QUERIES dbModule
```

### Explanation
This diagram shows the detailed backend module structure after the architecture cleanup. The modules are organized into logical layers with clear responsibilities. The color coding helps identify different functional areas: analytics (green), AI/ML (orange), strategies (pink), risk (red), core infrastructure (blue), services (gray), specialized engines (light green), API (teal), and database (light green). The arrows indicate key dependencies between modules.

---

## Architecture Summary

The StrikeIQ system architecture represents a production-grade, real-time options analytics platform with the following key characteristics:

### 🚀 **Performance Optimized**
- Sub-second market data processing
- Efficient WebSocket communication
- Redis caching for hot data
- AsyncIO for concurrent operations

### 🧠 **AI-Driven Intelligence**
- XGBoost-based probability predictions
- Real-time feature engineering
- Continuous learning and adaptation
- Multi-strategy decision orchestration

### 🛡️ **Risk-Aware Design**
- Comprehensive risk management
- Position sizing and stop-loss
- Paper trading simulation
- Outcome tracking and feedback

### 📊 **Real-Time Analytics**
- Live market structure analysis
- Institutional flow detection
- Options Greeks calculations
- Volatility regime identification

### 🔧 **Scalable Architecture**
- Modular component design
- Clear separation of concerns
- Easy to extend and maintain
- Production-ready deployment patterns

This architecture supports high-frequency market data processing while maintaining low latency for real-time trading insights, making it suitable for professional options trading applications.
