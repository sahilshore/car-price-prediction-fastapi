# Car price prediction platform

A production-style car price prediction project with:

- A FastAPI backend for authentication, prediction, metrics, Redis caching, and model serving.
- A Streamlit frontend for signing in and submitting vehicle details through a browser UI.
- A scikit-learn regression pipeline trained on the car-details dataset.
- Docker Compose services for the API, Redis, Prometheus, and Grafana.

The application estimates a vehicle's selling price from its company, age, ownership, fuel type, seller type, transmission, mileage, engine, power, torque, and seat count.

## Platform overview

~~~mermaid
flowchart LR
    User[User browser]
    UI[Streamlit frontend<br/>localhost:8501]
    API[FastAPI backend<br/>localhost:8000]
    Model[scikit-learn pipeline<br/>model.joblib]
    Redis[(Redis cache<br/>localhost:6379)]
    Prom[Prometheus<br/>localhost:9090]
    Grafana[Grafana<br/>localhost:3000]

    User --> UI
    UI -->|POST /login| API
    UI -->|POST /predict<br/>token + api-key headers| API
    API --> Model
    API --> Redis
    Prom -->|scrapes /metrics| API
    Grafana --> Prom
~~~

## Frontend UI flow

The Streamlit screen keeps connection settings and authentication in the sidebar, while the vehicle form and prediction result stay in the main area.

~~~mermaid
flowchart TB
    subgraph Sidebar[Sidebar]
        URL[FastAPI base URL]
        Key[API key]
        Login[Username + password]
        Docs[Open FastAPI docs]
    end

    subgraph Main[Main content]
        Form[Vehicle details form]
        Submit[Estimate price]
        Result[Predicted price card]
    end

    URL --> Login
    Key --> Login
    Login -->|JWT access token| Form
    Form --> Submit
    Submit -->|authenticated API request| Result
    Docs --> API[FastAPI /docs]
~~~

## Request flow

~~~mermaid
sequenceDiagram
    participant U as Streamlit user
    participant S as Streamlit UI
    participant F as FastAPI
    participant R as Redis
    participant M as Model pipeline

    U->>S: Enter credentials
    S->>F: POST /login
    F-->>S: JWT access token
    U->>S: Submit vehicle features
    S->>F: POST /predict with token and api-key
    F->>R: Look up cached features
    alt Cached result exists
        R-->>F: Cached price
    else New input
        F->>M: Predict price
        M-->>F: Predicted price
        F->>R: Cache prediction
    end
    F-->>S: predicted_price
    S-->>U: Display estimate
~~~

## Project structure

~~~text
car-price-prediction-fastapi/
├── app/
│   ├── api/
│   │   ├── routes_auth.py       # POST /login
│   │   └── routes_predict.py    # POST /predict
│   ├── cache/
│   │   └── redis_cache.py       # Redis read/write helpers
│   ├── core/
│   │   ├── config.py            # Environment-backed settings
│   │   ├── dependencies.py      # API-key and JWT dependencies
│   │   └── security.py          # JWT creation and verification
│   ├── services/
│   │   └── model_service.py     # Model loading and prediction
│   └── main.py                  # FastAPI application entrypoint
├── app/models/model.joblib      # Trained scikit-learn pipeline
├── data/car-details.csv         # Training dataset
├── training/
│   ├── train_model.py           # Model training script
│   └── train_utils.py           # Training paths
├── streamlit_app.py             # Browser frontend entrypoint
├── streamlit_requirements.txt   # Frontend-only dependencies
├── Dockerfile                   # FastAPI image
├── docker-compose.yml            # API, Redis, Prometheus, Grafana
└── prometheus.yml               # Metrics scrape configuration
~~~

## Quick start

### 1. Start the backend services

From the project root:

~~~powershell
docker compose up --build
~~~

For detached mode:

~~~powershell
docker compose up --build -d
~~~

Check the services:

~~~powershell
docker compose ps
docker compose logs api
~~~

The API should be available at [http://localhost:8000](http://localhost:8000).

### 2. Install frontend dependencies

The Streamlit frontend has its own dependency file so the API image does not need to install the UI stack.

~~~powershell
.\.venv\Scripts\python.exe -m pip install -r streamlit_requirements.txt
~~~

### 3. Run the Streamlit frontend

Open a second terminal in the project root:

~~~powershell
.\.venv\Scripts\streamlit.exe run streamlit_app.py
~~~

Open [http://localhost:8501](http://localhost:8501).

The frontend connects to `http://localhost:8000` by default. You can change the FastAPI URL and API key from the sidebar.

## Demo authentication

The current backend uses demo credentials defined in [app/api/routes_auth.py](app/api/routes_auth.py):

~~~text
Username: admin
Password: admin
API key: demo-key
~~~

Change these values before deploying outside a local demonstration. The API key and JWT secret are configured through [`.env`](.env) and the Docker Compose environment.

## API reference

| Method | Endpoint | Purpose | Authentication |
|---|---|---|---|
| `GET` | `/` | API health response | None |
| `GET` | `/docs` | Interactive Swagger documentation | None |
| `GET` | `/openapi.json` | OpenAPI schema | None |
| `GET` | `/metrics` | Prometheus metrics | None |
| `POST` | `/login` | Create a JWT access token | None |
| `POST` | `/predict` | Predict a vehicle price | `token` and `api-key` headers |

### Login request

~~~json
{
  "username": "admin",
  "password": "admin"
}
~~~

### Prediction request

~~~json
{
  "company": "Maruti",
  "year": 2014,
  "owner": "First",
  "fuel": "Diesel",
  "seller_type": "Individual",
  "transmission": "Manual",
  "km_driven": 145500,
  "mileage_mpg": 55.0,
  "engine_cc": 1248.0,
  "max_power_bhp": 74.0,
  "torque_nm": 190.0,
  "seats": 5.0
}
~~~

Required headers:

~~~text
token: <JWT returned by /login>
api-key: <configured API key>
~~~

Example response:

~~~json
{
  "predicted_price": "503473.93"
}
~~~

## Configuration

The backend reads these values from [`.env`](.env) and Docker Compose:

| Variable | Purpose | Local example |
|---|---|---|
| `API_KEY` | API-key authentication for `/predict` | `demo-key` |
| `JWT_SECRET_KEY` | Secret used to sign JWT tokens | `secret` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379` in Docker |
| `MODEL_PATH` | Serialized model location | `app/models/model.joblib` |
| `API_BASE_URL` | Optional Streamlit backend URL | `http://localhost:8000` |

Do not commit real passwords, API keys, or JWT secrets. The checked-in values are only suitable for local development.

## Model and training

The model is a scikit-learn `Pipeline` containing:

1. Numeric median imputation.
2. Numeric standardization.
3. Categorical imputation.
4. One-hot encoding with unknown-category support.
5. A `RandomForestRegressor`.

The runtime and model artifact must use compatible scikit-learn versions. The project pins scikit-learn `1.3.2` and the current model was retrained with that version.

To retrain inside the API image:

~~~powershell
docker compose run --rm --no-deps api python -m training.train_model
~~~

Then rebuild the API image:

~~~powershell
docker compose up --build -d api
~~~

## Monitoring services

| Service | URL | Purpose |
|---|---|---|
| FastAPI | [localhost:8000](http://localhost:8000) | API and model serving |
| Swagger | [localhost:8000/docs](http://localhost:8000/docs) | Interactive API testing |
| Redis | `localhost:6379` | Prediction cache |
| Prometheus | [localhost:9090](http://localhost:9090) | Metrics collection |
| Grafana | [localhost:3000](http://localhost:3000) | Metrics dashboards |

Prometheus scrapes the Compose service hostname `api:8000`, while users access the API through the published host port `8000`.

## Troubleshooting

### `localhost:8000` refuses the connection

The API container has probably exited. Check:

~~~powershell
docker compose ps -a
docker compose logs api
~~~

Confirm that `MODEL_PATH` points to `app/models/model.joblib`, then rebuild:

~~~powershell
docker compose up --build
~~~

### Streamlit cannot connect to FastAPI

Confirm that the backend is running at [http://localhost:8000](http://localhost:8000), then check the FastAPI base URL in the Streamlit sidebar. When Streamlit runs on the host, use `http://localhost:8000`; when both apps run inside Compose, use the service hostname `http://api:8000`.

### Prediction fails after changing the model

Retrain the model with the same scikit-learn version used by the API image:

~~~powershell
docker compose run --rm --no-deps api python -m training.train_model
docker compose up --build -d api
~~~

### View the API manually

Open [http://localhost:8000/docs](http://localhost:8000/docs) and test `/login` first. Copy the returned JWT into the `token` header when testing `/predict`.

## Verification checklist

The current project has been verified with:

- FastAPI startup inside Docker Compose.
- Redis, Prometheus, and Grafana services running.
- `GET /`, `/docs`, and `/metrics` returning `200`.
- Successful login and authenticated prediction requests.
- Streamlit `AppTest` with zero app exceptions.
- Streamlit agent API health check returning `ok` and an initial snapshot with zero exceptions.
