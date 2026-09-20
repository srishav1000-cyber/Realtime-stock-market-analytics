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


* ## Proposed System Pipeline (Under Research)

```mermaid
flowchart TD
    A[Mock / Live Market Feed<br><i>Python Generator</i>] -->|Streaming JSON Ticks| B[Message Broker<br><i>Apache Kafka: 'stock-ticks'</i>]
    B -->|Subscribe & Stream| C[Stream Processing Engine<br><i>Python Volatility Tracker</i>]
    C -->|Breach Threshold Detected| D[Alerting Engine<br><i>Circuit Breaker Log / Console</i>]
    C -->|Persist Trade Data| E[(Relational Database<br><i>PostgreSQL</i>)]
    D -->|Log Trigger Events| E
    E -->|Read Query / Aggregate| F[Analytics Dashboard<br><i>PowerBI / Apache Superset</i>]

---

## 📚 Academic References & Theoretical Foundations

This project grounds its real-time streaming architecture and risk mechanics in established academic literature:

1. **Distributed Event Streaming:**
   * *Kreps, J., Narkhede, N., & Rao, J.* "Kafka: A Distributed Messaging System for Log Processing." *Proceedings of the 6th International Workshop on Networking Meets Databases (NetDB)*.
   * *Focus:* High-throughput log-structured message brokers for zero-loss trade tick ingestion.

2. **Stream Processing & Alert Thresholds:**
   * *Chandramouli, B., Maier, D., & Goldstein, J.* "High-Performance Complex Event Processing over Financial Data Streams." *IEEE International Conference on Data Engineering (ICDE)*.
   * *Focus:* Efficient sliding-window computation for real-time volatility tracking and circuit-breaker triggers.

3. **Market Microstructure & Circuit-Breaker Policies:**
   * *Subrahmanyam, A.* "Circuit Breakers and Market Volatility: A Survey." *Journal of Financial Markets*.
   * *Focus:* Mechanisms of exchange cooling periods and automated price-band tripwires.

4. **Time-Series Relational Persistence:**
   * *Stonebraker, M., et al.* "Benchmarking Streaming Data Ingestion in Relational Systems." *ACM SIGMOD*.
   * *Focus:* Mitigating write-lock overhead during continuous streaming ingestion into relational stores (PostgreSQL).
```
