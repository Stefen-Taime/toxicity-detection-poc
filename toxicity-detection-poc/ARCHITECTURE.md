# Real-Time Toxicity Detection System Architecture

## Overview

This architecture replaces proprietary solutions (Confluent Cloud and Databricks) with open-source alternatives while retaining the essential functionalities of the original system.

![System Architecture](./docs/images/architecture.png)

## Main Components

### 1. Message Ingestion (Ingestion Proxy)
- **Service**: `game-message-proxy`
- **Technology**: FastAPI
- **Role**: Receives messages from game servers and publishes them to Kafka/Redpanda

### 2. Message Transport
- **Service**: `redpanda` (alternative to Apache Kafka)
- **Technology**: Redpanda (Kafka API compatible)
- **Role**: Store and forward messages between system components
- **Topics**:
  - `raw-messages`: Incoming raw messages
  - `classified-messages`: Messages with preliminary classification
  - `nlp-analysis-required`: Messages requiring deeper analysis
  - `nlp-analysis-results`: Results of deeper analysis
  - `moderation-required`: Messages requiring human intervention
  - `moderation-results`: Human moderation outcomes
  - `final-decisions`: Final decisions on messages
  - `model-training-data`: Data for model training

### 3. Fast Classification
- **Service**: `fast-classifier`
- **Technology**: Apache Flink
- **Role**: Quickly classify messages into three categories (OK, Toxic, Needs Review)
- **Model**: Lightweight model optimized for speed (TensorFlow Lite)

### 4. Deep Analysis
- **Service**: `deep-analyzer`
- **Technology**: Spark (alternative to Databricks)
- **Role**: Deeply analyze ambiguous messages with context
- **Model**: More complex NLP model (Transformer-based)

### 5. Data Storage
- **Service**: `minio`
- **Technology**: MinIO (S3 compatible)
- **Role**: Store ML models, training data, and logs

### 6. Model Management
- **Service**: `mlflow`
- **Technology**: MLflow
- **Role**: Track experiments, manage model versions, orchestrate deployments

### 7. Moderation Interface
- **Service**: `moderation-ui`
- **Technology**: Html5, Css, Js
- **Role**: UI for human moderators

### 8. Decision Manager
- **Service**: `decision-manager`
- **Technology**: Python (FastAPI)
- **Role**: Apply moderation rules and publish final decisions

### 9. Game Simulator (for POC)
- **Service**: `game-simulator`
- **Technology**: Python
- **Role**: Simulate in-game conversations for system testing

## Data Flow

1. Game messages are sent to the ingestion proxy.
2. The proxy publishes them to the `raw-messages` topic in Redpanda.
3. The fast classifier (Flink) consumes and classifies messages:
   - "OK" messages → `classified-messages` (tag: OK)
   - "Toxic" messages → `classified-messages` (tag: Toxic)
   - Ambiguous messages → `nlp-analysis-required`
4. Deep analysis service processes ambiguous messages and publishes results to `nlp-analysis-results`.
5. If undecidable, messages are forwarded to `moderation-required`.
6. Human moderators review and submit outcomes to `moderation-results`.
7. The decision manager combines all input and publishes final decisions to `final-decisions`.
8. Decisions and feedback are used to improve models via `model-training-data`.

## Architecture Benefits

1. **High Availability**: All components can be horizontally scaled.
2. **Low Latency**: Fast classification for most messages.
3. **Adaptability**: Models improve over time from feedback.
4. **Open Source**: No dependency on proprietary services.
5. **Component Isolation**: Each service can evolve independently.

## Performance Considerations

- The fast classifier is optimized to process thousands of messages per second.
- Deep analysis handles edge cases without slowing the main flow.
- Human moderation is minimized through continuous model improvement.

---

