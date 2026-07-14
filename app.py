import os
import logging
from dotenv import load_dotenv

# Set up logging configuration globally
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

# 1. Load environment variables before importing Config
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
else:
    load_dotenv()

from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from supabase import create_client, Client
from supabase.client import ClientOptions
from config import Config

# Ensure the model is downloaded before the Flask app starts
from download_model import download_model
download_model()
logger.info("📥 Model downloaded")

logger.info(f"RAILWAY_ENVIRONMENT = {os.getenv('RAILWAY_ENVIRONMENT')}")
IS_RAILWAY = os.getenv("RAILWAY_ENVIRONMENT") is not None
logger.info(f"IS_RAILWAY = {IS_RAILWAY}")

if IS_RAILWAY:
    logger.info("🚀 Railway detected")
    try:
        from routes.ai import load_model
        logger.info("🧠 Loading YOLO model...")
        m = load_model()
        if m:
            logger.info("🔥 Running warm-up inference...")
            import numpy as np
            import torch
            dummy = np.zeros((320, 320, 3), dtype=np.uint8)
            device = "cuda:0" if torch.cuda.is_available() else "cpu"
            m.predict(
                source=dummy, 
                imgsz=320, 
                device=device,
                half=torch.cuda.is_available(),
                verbose=False
            )
            logger.info("✅ YOLO warm-up completed")
    except Exception as e:
        logger.error(f"❌ YOLO warm-up failed: {e}")

Config.check_env()

# 2. Initialize Supabase Client safely with increased network timeouts
supabase: Client = None
if Config.SUPABASE_URL and Config.SUPABASE_KEY:
    try:
        options = ClientOptions(postgrest_client_timeout=45, storage_client_timeout=45)
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY, options=options)
        logger.info("[+] Supabase client initialized successfully with 45s timeout.")
    except Exception as e:
        logger.error(f"[!] Critical: Failed to initialize Supabase: {e}", exc_info=True)
else:
    logger.warning("[!] Supabase credentials missing. Database features will be disabled.")

bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__)
    app.secret_key = Config.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit
    
    # Enable CORS for all routes (important for deployment)
    CORS(app)
    
    bcrypt.init_app(app)

    # Ensure upload folder exists
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    # Register blueprints
    from routes.api   import api_bp
    from routes.pages import pages_bp
    app.register_blueprint(api_bp)
    app.register_blueprint(pages_bp)
    
    try:
        from routes.ai import ai_bp
        app.register_blueprint(ai_bp)
        print("✅ ai_bp loaded successfully")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ ai_bp failed to load: {e}")

    # Frontend serving disabled – backend‑only mode.
    @app.route('/health')
    def health():
        return {"status": "ok"}

    return app

# Global app instance for Gunicorn
app = create_app()

logger.info("🚀 Server ready")

if __name__ == "__main__":
    # Production run — debug=False prevents state loss from auto-reloader
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
