from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()

DEFAULT_API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def configured_value(name: str, default: str = "") -> str:
    """Read a setting from Streamlit secrets, then environment variables."""
    try:
        secret_value = st.secrets.get(name)
    except (FileNotFoundError, KeyError):
        secret_value = None

    return str(secret_value or os.getenv(name, default))


def initialize_session_state() -> None:
    """Initialize per-user values once for the current Streamlit session."""
    defaults: dict[str, Any] = {
        "access_token": None,
        "username": None,
        "last_prediction": None,
        "last_inputs": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def response_error(response: requests.Response) -> str:
    """Extract a useful API error without exposing the raw response unnecessarily."""
    try:
        payload = response.json()
    except ValueError:
        return response.text or f"Request failed with HTTP {response.status_code}."

    detail = payload.get("detail", payload) if isinstance(payload, dict) else payload
    if isinstance(detail, list):
        return "; ".join(str(item.get("msg", item)) for item in detail)
    return str(detail)


def login(api_base_url: str, api_key: str, username: str, password: str) -> str:
    """Authenticate with the FastAPI backend and return its JWT."""
    response = requests.post(
        f"{api_base_url.rstrip('/')}/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    if not response.ok:
        raise RuntimeError(response_error(response))

    payload = response.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise RuntimeError(payload.get("error", "The API did not return an access token."))
    return str(access_token)


def predict_price(
    api_base_url: str,
    api_key: str,
    access_token: str,
    car_features: dict[str, Any],
) -> float:
    """Send car features to the protected FastAPI prediction endpoint."""
    response = requests.post(
        f"{api_base_url.rstrip('/')}/predict",
        headers={"token": access_token, "api-key": api_key},
        json=car_features,
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError(response_error(response))

    payload = response.json()
    return float(payload["predicted_price"])


st.set_page_config(
    page_title="Car price predictor",
    page_icon=":material/directions_car:",
    layout="centered",
)

initialize_session_state()

api_base_url = st.sidebar.text_input(
    "FastAPI base URL",
    value=configured_value("API_BASE_URL", DEFAULT_API_BASE_URL),
    help="Use http://localhost:8000 when the Docker Compose API is running locally.",
)
api_key = st.sidebar.text_input(
    "API key",
    value=configured_value("API_KEY"),
    type="password",
    help="This must match the API_KEY configured for FastAPI.",
)

with st.sidebar:
    st.divider()
    st.subheader("Authentication")

    if st.session_state.access_token:
        st.success(f"Signed in as {st.session_state.username}")
        if st.button("Sign out", icon=":material/logout:", width="stretch"):
            st.session_state.access_token = None
            st.session_state.username = None
            st.session_state.last_prediction = None
            st.rerun()
    else:
        with st.form("login_form", border=False):
            username = st.text_input("Username", value="admin")
            password = st.text_input("Password", type="password")
            submitted_login = st.form_submit_button(
                "Sign in",
                type="primary",
                icon=":material/login:",
                width="stretch",
            )

        if submitted_login:
            if not api_key:
                st.error("Enter the API key before signing in.")
            elif not password:
                st.error("Enter your password before signing in.")
            else:
                try:
                    st.session_state.access_token = login(
                        api_base_url,
                        api_key,
                        username,
                        password,
                    )
                    st.session_state.username = username
                    st.rerun()
                except (requests.RequestException, RuntimeError) as exc:
                    st.error(f"Sign-in failed: {exc}")

    st.divider()
    st.link_button(
        "Open FastAPI docs",
        f"{api_base_url.rstrip('/')}/docs",
        icon=":material/menu_book:",
        width="stretch",
    )


st.title("Car price predictor")
st.caption("Streamlit frontend for your protected FastAPI car-price model.")

if not st.session_state.access_token:
    st.info(
        "Sign in from the sidebar to submit a prediction.",
        title="Authentication required",
    )
    st.stop()


st.header("Enter vehicle details")
st.caption("The values are sent to the FastAPI `/predict` endpoint.")

with st.form("prediction_form", border=True):
    first_row = st.columns(2)
    company = first_row[0].text_input("Company", value="Maruti")
    year = first_row[1].number_input("Year", min_value=1950, max_value=2035, value=2014, step=1)

    second_row = st.columns(2)
    owner = second_row[0].text_input("Owner", value="First")
    fuel = second_row[1].text_input("Fuel", value="Diesel")

    third_row = st.columns(2)
    seller_type = third_row[0].text_input("Seller type", value="Individual")
    transmission = third_row[1].text_input("Transmission", value="Manual")

    st.subheader("Measurements")
    fourth_row = st.columns(2)
    km_driven = fourth_row[0].number_input("Kilometres driven", min_value=0.0, value=145500.0, step=1000.0)
    mileage_mpg = fourth_row[1].number_input("Mileage (mpg)", min_value=0.0, value=55.0, step=0.1)

    fifth_row = st.columns(2)
    engine_cc = fifth_row[0].number_input("Engine (cc)", min_value=0.0, value=1248.0, step=50.0)
    max_power_bhp = fifth_row[1].number_input("Max power (bhp)", min_value=0.0, value=74.0, step=1.0)

    sixth_row = st.columns(2)
    torque_nm = sixth_row[0].number_input("Torque (Nm)", min_value=0.0, value=190.0, step=10.0)
    seats = sixth_row[1].number_input("Seats", min_value=1.0, value=5.0, step=1.0)

    submitted_prediction = st.form_submit_button(
        "Estimate price",
        type="primary",
        icon=":material/calculate:",
        width="stretch",
    )

if submitted_prediction:
    inputs = {
        "company": company,
        "year": int(year),
        "owner": owner,
        "fuel": fuel,
        "seller_type": seller_type,
        "transmission": transmission,
        "km_driven": km_driven,
        "mileage_mpg": mileage_mpg,
        "engine_cc": engine_cc,
        "max_power_bhp": max_power_bhp,
        "torque_nm": torque_nm,
        "seats": seats,
    }

    try:
        with st.spinner("Requesting prediction from FastAPI..."):
            prediction = predict_price(
                api_base_url,
                api_key,
                st.session_state.access_token,
                inputs,
            )
        st.session_state.last_prediction = prediction
        st.session_state.last_inputs = inputs
    except (requests.RequestException, RuntimeError, KeyError, ValueError) as exc:
        st.error(f"Prediction failed: {exc}")


if st.session_state.last_prediction is not None:
    with st.container(border=True):
        st.subheader("Estimated selling price")
        st.metric("Predicted price", f"₹{st.session_state.last_prediction:,.2f}")
        st.caption("This estimate comes from the currently running FastAPI model.")
