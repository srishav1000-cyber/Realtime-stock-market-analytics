# Realtime Stock Market Analytics

A real-time data streaming pipeline designed to ingest stock market trades, detect high-volatility events, and trigger automated circuit-breaker alerts.

## Project Contributors
* Rishav Singh
* Pratima Bastola

*Both contributors work collaboratively across the entire stack: system design, Kafka streaming, PostgreSQL data modeling, and visualization.*

## Tech Stack
* Language: Python
* Streaming: Apache Kafka
* Storage: PostgreSQL
* Dashboard: PowerBI / Superset

## Week 1 Milestones Completed
* Collaboratively designed the end-to-end streaming architecture.
* Researched circuit-breaker logic parameters and thresholds.
* Finalized initial PostgreSQL schema for trade ingestion and alert logging.

* ## Tools & Technology Breakdown (Under Research)

```mermaid
flowchart LR
    subgraph Ingestion["Ingestion Layer"]
        P[Python 3.10+]:::tool -->|Simulate/Fetch Market Data| K[Apache Kafka]:::tool
    end

    subgraph Processing["Processing & Rules"]
        K -->|Stream Ticker Events| E[Python Engine]:::tool
        E -->|Evaluate Price Delta| CB[Circuit Breaker Logic]:::logic
    end

    subgraph Storage["Persistence Layer"]
        E -->|Bulk Ingestion| PG[(PostgreSQL)]:::tool
        CB -->|Store Breach Logs| PG
    end

    subgraph Visualization["Serving Layer"]
        PG -->|Live Dashboards & BI| BI[PowerBI / Superset]:::tool
    end

    classDef tool fill:#eef2ff,stroke:#6366f1,stroke-width:2px,color:#1e1b4b;
    classDef logic fill:#fef2f2,stroke:#ef4444,stroke-width:2px,color:#7f1d1d;
```

* ## Proposed System Pipeline (Under Research)

```mermaid
flowchart TD
    A[Mock / Live Market Feed<br><i>Python Generator</i>] -->|Streaming JSON Ticks| B[Message Broker<br><i>Apache Kafka: 'stock-ticks'</i>]
    B -->|Subscribe & Stream| C[Stream Processing Engine<br><i>Python Volatility Tracker</i>]
    C -->|Breach Threshold Detected| D[Alerting Engine<br><i>Circuit Breaker Log / Console</i>]
    C -->|Persist Trade Data| E[(Relational Database<br><i>PostgreSQL</i>)]
    D -->|Log Trigger Events| E
    E -->|Read Query / Aggregate| F[Analytics Dashboard<br><i>PowerBI / Apache Superset</i>]
```
