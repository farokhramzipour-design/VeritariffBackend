
# Veritariff Backend

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Database Setup**:
    *   Ensure PostgreSQL is running.
    *   Create a database named `veritariff`.
    *   Update `.env` with your database credentials.

3.  **Google Login Setup**:
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a new project or select an existing one.
    *   Go to **APIs & Services** > **Credentials**.
    *   Click **Create Credentials** > **OAuth client ID**.
    *   Select **Web application**.
    
    ### Development (Localhost)
    *   **Authorized JavaScript origins**:
        *   `http://localhost`
        *   `http://localhost:3000`
        *   `http://localhost:8000`
    *   **Authorized redirect URIs**:
        *   `http://localhost:3000`
        *   `http://localhost:8000/docs/oauth2-redirect`
        *   `http://localhost:8000/api/v1/login/google/callback`

    ### Production (veritariffai.co)
    *   **Authorized JavaScript origins**:
        *   `https://veritariffai.co`
        *   `https://www.veritariffai.co`
    *   **Authorized redirect URIs**:
        *   `https://veritariffai.co`
        *   `https://www.veritariffai.co`
        *   `https://api.veritariffai.co/docs/oauth2-redirect`
        *   `https://api.veritariffai.co/api/v1/login/google/callback`

    *   Copy the **Client ID** and **Client Secret** and paste them into your `.env` file.

4.  **Run the App**:
    ```bash
    uvicorn main:app --reload
    ```

## API Documentation

*   **Swagger UI**: `http://localhost:8000/docs`
*   **ReDoc**: `http://localhost:8000/redoc`
# VeritariffBackend
