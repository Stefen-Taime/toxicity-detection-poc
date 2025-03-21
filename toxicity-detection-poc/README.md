# Real-time Toxicity Detection in Video Games

This POC (Proof of Concept) implements a real-time toxicity detection system for video games using open source technologies.

## Objective

Create a system capable of detecting and filtering toxic messages in video game chats in real time, while preserving the user experience and distinguishing friendly jokes from genuinely toxic behavior.

## Architecture

Our solution replaces the proprietary components mentioned in the original article with open source alternatives:

- **Apache Kafka** (replacing Confluent Cloud) for message transport
- **Apache Flink** for real-time processing
- **MLflow + Spark** (replacing Databricks) for in-depth analysis and model training
- **MinIO** (replacing cloud storage) for storing data and models
- **FastAPI** for service APIs
- **Streamlit** for the human moderation interface

## Features

1. Real-time message ingestion
2. Quick message classification (OK, Toxic, Requires Analysis)
3. In-depth analysis of ambiguous cases
4. Human intervention for complex cases
5. Continuous model training
6. Moderation and supervision interface

## Prerequisites

- Docker and Docker Compose
- Git (to clone this repository)

## Quick Start

```bash
git clone https://github.com/Stefen-Taime/toxicity-detection-poc.git
cd toxicity-detection-poc
docker-compose up --build
```

Access the demo interface: http://localhost:8501
moderation ui dashboard: http://localhost:8501
FastAPI documentation: http://localhost:8000/docs
MLflow UI: http://localhost:5000
MinIO Console: http://localhost:9001
Redpanda Console: http://localhost:8080
Flink Console: http://localhost:8081
## Structure du projet

See the ARCHITECTURE.md document for more details on the system design. [ARCHITECTURE.md](ARCHITECTURE.md)

# Run the pipeline
./setup_pipeline.sh